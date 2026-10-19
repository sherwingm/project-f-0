"""Upstox read-only live data: LTP, futures OI and exact PCR for the whole F&O universe, on the
free API with a 1-year Analytics Token. The token is read-only by construction: Upstox issues it
without the OAuth flow and it cannot place, modify or cancel orders, so this provider has no
order path at all.

Setup: account.upstox.com/developer/apps → Analytics tab → Generate Token → UPSTOX_ANALYTICS_TOKEN.
No daily login, no static IP, no subscription.

Endpoints used (all in the Analytics Token's supported list):
    GET /v2/market-quote/quotes?instrument_key=k1,k2,...   full quotes, up to 500 keys, includes oi
    GET /v2/option/chain?instrument_key=NSE_EQ|ISIN&expiry_date=YYYY-MM-DD
                                                           every strike: ltp, oi, prev_oi, volume, greeks.iv
    https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz   instrument master
Rate limits (docs, 2026-10-19): 50/s, 500/min, 2,000 per 30 min per user; RateLimiter holds less. A poll spends
2 full-quote calls (500 keys each, with 5-level depth) plus UPSTOX_CHAIN_CALLS_PER_POLL option-chain calls
(default 12) on a rolling sweep of the universe, so at a 30 s poll every stock's PCR and per-strike OI refresh
roughly every nine minutes while LTP, depth and futures OI refresh every poll, at about 840 calls per 30 minutes.
The paper fill engine prices options with quote_one / quote_many (full quotes with depth), the live charts use
history() (v3 candles), and futures() lists every live futures contract, as server/kotak.py does.
"""
from __future__ import annotations

import gzip
import io
import json
import logging
import re
import tempfile
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from urllib.parse import quote as urlquote

import requests

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
BASE = "https://api.upstox.com/v2"
BASE_V3 = "https://api.upstox.com/v3"
QUOTE_BATCH = 500                                 # full market quote: up to 500 instrument keys a call
DEPTH_LEVELS = 5
HISTORY_TODAY_TTL = 60.0                          # seconds a partial day's candles are reused
INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
KEY_RE = re.compile(r"^(?P<sym>.+?)(?P<yy>\d{2})(?P<mon>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
                    r"(?:(?P<strike>\d+(?:\.\d+)?)(?P<side>CE|PE)|(?P<fut>FUT))$")


class RateLimiter:
    """Sliding windows per second, minute and 30 minutes. Upstox documents 50/s, 500/min and 2,000 per 30 min per
    user (read 2026-10-19); the server holds 40/s, 400/min and 1,500/30 min so the GitHub jobs on the same token keep
    about 500 per 30 minutes."""

    def __init__(self, per_second=40, per_minute=400, per_30min=1500):
        self.limits = ((1, per_second), (60, per_minute), (1800, per_30min))
        self.calls: deque[float] = deque()
        self.lock = threading.Lock()

    def wait(self) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                while self.calls and now - self.calls[0] > 1800:
                    self.calls.popleft()
                blocked = 0.0
                for window, cap in self.limits:
                    n = sum(1 for t in self.calls if now - t < window)
                    if n >= cap:
                        oldest = next(t for t in self.calls if now - t < window)
                        blocked = max(blocked, window - (now - oldest) + 0.05)
                if not blocked:
                    self.calls.append(now)
                    return
            time.sleep(min(blocked, 5.0))


class UpstoxProvider:
    """quote(keys) -> {key: {...}} in the shape LiveFeed expects.

    keys:  NSE:<SYMBOL>                    equity: last_price, volume, prev close (from net_change)
           NFO:<SYMBOL><YY><MON>FUT        near future: last_price, open_interest
           NFO:<SYMBOL><YY><MON><K>CE/PE   options: last_price, open_interest, volume, iv (from the chain)
    Extra keys the provider adds on its own:
           PCR:<SYMBOL>                    {"pcr", "call_oi", "put_oi", "pcr_ts"} from the rolling chain sweep
    """

    def __init__(self, token: str, chain_calls_per_poll: int = 12, timeout: int = 20):
        self.token, self.timeout = token, timeout
        self.chain_calls_per_poll = max(0, chain_calls_per_poll)
        self.limiter = RateLimiter()
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "Authorization": f"Bearer {token}"})
        self._eq: dict[str, dict] = {}        # symbol -> {"key": "NSE_EQ|ISIN", "isin": ...}
        self._fo: dict[tuple, dict] = {}      # (symbol, type, yy, MON, strike|None) -> {"key", "expiry", "lot_size"}
        self._loaded = False
        self._chains: dict[str, dict] = {}    # symbol -> {"expiry", "ts", "strikes": {(strike, side): {...}}, "pcr"...}
        self._cursor = 0
        self._hist: dict[tuple, tuple[float, list]] = {}

    # ---- instrument master --------------------------------------------------------------
    def load_instruments(self) -> None:
        if self._loaded:
            return
        # streamed to a temp file and parsed object by object: the whole file is ~40 MB of JSON (~140 MB as Python
        # objects at peak), too much next to the live server on a small host; only NSE_EQ / NSE_FO rows are kept
        with tempfile.TemporaryFile() as tmp:
            with self.session.get(INSTRUMENTS_URL, timeout=60, stream=True) as r:
                r.raise_for_status()
                for part in r.iter_content(1 << 20):
                    tmp.write(part)
            tmp.seek(0)
            gz = tmp.read(2) == b"\x1f\x8b"
            tmp.seek(0)
            fh = gzip.open(tmp, "rt", encoding="utf-8") if gz else io.TextIOWrapper(tmp, encoding="utf-8")
            self._ingest_instruments(_stream_rows(fh))

    def _ingest_instruments(self, rows: list[dict]) -> None:
        for r in rows:
            seg, typ = r.get("segment"), r.get("instrument_type")
            if seg == "NSE_EQ" and typ == "EQ":
                self._eq[str(r.get("trading_symbol"))] = {"key": r["instrument_key"], "isin": r.get("isin")}
            elif seg == "NSE_FO" and typ in ("FUT", "CE", "PE") and r.get("underlying_symbol"):
                exp = r.get("expiry")
                if exp is None:
                    continue
                d = datetime.fromtimestamp(int(exp) / 1000, tz=IST).date() if isinstance(exp, (int, float)) else datetime.strptime(str(exp)[:10], "%Y-%m-%d").date()
                strike = float(r["strike_price"]) if typ != "FUT" and r.get("strike_price") is not None else None
                k = (str(r["underlying_symbol"]), typ, d.strftime("%y"), MONTHS[d.month - 1], strike)
                # stock derivatives expire monthly; keep the earliest expiry for a (symbol, yy, MON) just in case
                cur = self._fo.get(k)
                if cur is None or d.isoformat() < cur["expiry"]:
                    self._fo[k] = {"key": r["instrument_key"], "expiry": d.isoformat(), "lot_size": r.get("lot_size")}
        self._loaded = True
        log.info("Upstox instruments: %d equities, %d NSE F&O contracts", len(self._eq), len(self._fo))

    def _fo_key(self, parsed: dict) -> dict | None:
        strike = float(parsed["strike"]) if parsed.get("strike") else None
        typ = "FUT" if parsed.get("fut") else parsed["side"]
        return self._fo.get((parsed["sym"], typ, parsed["yy"], parsed["mon"], strike))

    # ---- Provider interface ---------------------------------------------------------------
    def quote(self, keys: list[str]) -> dict[str, dict]:
        self.load_instruments()
        out: dict[str, dict] = {}
        eq_keys: dict[str, str] = {}      # instrument_key -> our key
        fut_keys: dict[str, str] = {}
        opt_groups: dict[tuple[str, str], list[tuple[float, str, str]]] = {}   # (sym, expiry) -> [(strike, side, ourkey)]
        for k in keys:
            if k.startswith("NSE:"):
                e = self._eq.get(k[4:])
                if e:
                    eq_keys[e["key"]] = k
            elif k.startswith("NFO:"):
                m = KEY_RE.match(k[4:])
                if not m:
                    continue
                p = m.groupdict()
                fo = self._fo_key(p)
                if not fo:
                    continue
                if p.get("fut"):
                    fut_keys[fo["key"]] = k
                else:
                    opt_groups.setdefault((p["sym"], fo["expiry"]), []).append((float(p["strike"]), p["side"], k))

        for chunk in _chunks(list(eq_keys) + list(fut_keys), QUOTE_BATCH):
            data = self._get("/market-quote/quotes", {"instrument_key": ",".join(chunk)})
            for entry in (data or {}).values():
                tok = entry.get("instrument_token")
                ours = eq_keys.get(tok) or fut_keys.get(tok)
                if ours:                                  # Kotak's shape: depth, ATP, previous close, OI on futures
                    out[ours] = _parse_full(entry, fo=tok in fut_keys)

        # rolling chain sweep over every stock we have a future for: exact PCR + per-strike OI
        futs = sorted({KEY_RE.match(k[4:]).group("sym") for k in fut_keys.values()})
        self._sweep_chains(futs)
        for sym in futs:
            c = self._chains.get(sym)
            if c:
                out["PCR:" + sym] = {"pcr": c["pcr"], "call_oi": c["call_oi"], "put_oi": c["put_oi"], "pcr_ts": c["ts"]}

        # options asked for explicitly (an open strike table, a watched contract): full quotes with depth, then the
        # chain only for what the quotes did not return
        opt_keys = {}
        for (sym, expiry), wanted in opt_groups.items():
            for strike, side, ours in wanted:
                m = KEY_RE.match(ours[4:])
                fo = self._fo_key(m.groupdict()) if m else None
                if fo:
                    opt_keys[fo["key"]] = ours
        for chunk in _chunks(list(opt_keys), QUOTE_BATCH):
            data = self._get("/market-quote/quotes", {"instrument_key": ",".join(chunk)})
            for entry in (data or {}).values():
                ours = opt_keys.get(entry.get("instrument_token"))
                if ours:
                    out[ours] = _parse_full(entry, fo=True)
        for (sym, expiry), wanted in opt_groups.items():
            wanted = [w for w in wanted if w[2] not in out]
            if not wanted:
                continue
            c = self._chains.get(sym)
            if not c or c["expiry"] != expiry or time.time() - c["epoch"] > 120:
                c = self._fetch_chain(sym, expiry)
            if not c:
                continue
            for strike, side, ours in wanted:
                row = c["strikes"].get((strike, side))
                if row:
                    out[ours] = row
        return out

    def quote_one(self, tradingsymbol: str) -> dict:
        """One F&O contract on demand (the paper fill engine), in server/kotak.py's shape: last_price, volume,
        open_interest, timestamp, 5-level depth, atp, plus lot_size, expiry and tradingsymbol."""
        got = self.quote_many([tradingsymbol])
        if tradingsymbol not in got:
            raise RuntimeError(f"Upstox: no quote for {tradingsymbol}")
        return got[tradingsymbol]

    def quote_many(self, tradingsymbols: list[str]) -> dict[str, dict]:
        """quote_one for many contracts, up to QUOTE_BATCH per call. {tradingsymbol as asked: quote}; a contract
        missing from the instrument master or the reply is left out."""
        self.load_instruments()
        want: dict[str, tuple[str, dict]] = {}
        for t in tradingsymbols:
            ts = t.split(":", 1)[1] if ":" in t else t
            m = KEY_RE.match(ts)
            fo = self._fo_key(m.groupdict()) if m else None
            if fo:
                want[fo["key"]] = (t, fo)
        out: dict[str, dict] = {}
        for chunk in _chunks(list(want), QUOTE_BATCH):
            data = self._get("/market-quote/quotes", {"instrument_key": ",".join(chunk)})
            for entry in (data or {}).values():
                hit = want.get(entry.get("instrument_token"))
                if hit:
                    t, fo = hit
                    out[t] = {**_parse_full(entry, fo=True), "tradingsymbol": t.split(":", 1)[-1],
                              "lot_size": int(fo["lot_size"] or 0), "expiry": fo["expiry"]}
        return out

    def futures(self, symbols, today: str | None = None) -> dict[str, list[str]]:
        """{symbol: [near, next, far futures tradingsymbols]} expiring today or later (as KotakProvider.futures)."""
        self.load_instruments()
        today = today or datetime.now(IST).date().isoformat()
        by: dict[str, list[tuple[str, str]]] = {}
        for (sym, typ, yy, mon, _k), v in self._fo.items():
            if typ == "FUT" and v["expiry"] >= today:
                by.setdefault(sym, []).append((v["expiry"], f"{sym}{yy}{mon}FUT"))
        return {s: [ts for _, ts in sorted(by[s])] for s in symbols if s in by}

    def history(self, key: str, tf: int, day: str) -> list[dict]:
        """tf-minute candles of `key` (NSE:<SYMBOL> or NFO:<tradingsymbol>) on `day` (ISO) from Upstox's v3
        historical API (today: its intraday endpoint), in server/candles.py's shape like KotakProvider.history.
        A past day is cached for the process's life, today for HISTORY_TODAY_TTL seconds."""
        self.load_instruments()
        if key.startswith("NSE:"):
            ik = (self._eq.get(key[4:]) or {}).get("key")
        else:
            m = KEY_RE.match(key.split(":", 1)[-1])
            ik = (self._fo_key(m.groupdict()) or {}).get("key") if m else None
        if not ik:
            return []
        ck = (key, int(tf), day)
        hit = self._hist.get(ck)
        today = datetime.now(IST).date().isoformat()
        if hit and (day < today or time.monotonic() - hit[0] < HISTORY_TODAY_TTL):
            return hit[1]
        k = urlquote(ik, safe="")
        path = (f"/historical-candle/intraday/{k}/minutes/{int(tf)}" if day >= today
                else f"/historical-candle/{k}/minutes/{int(tf)}/{day}/{day}")
        data = self._get(path, {}, base=BASE_V3) or {}
        out = []
        for r in data.get("candles") or []:
            if not isinstance(r, (list, tuple)) or len(r) < 5:
                continue
            t = datetime.fromisoformat(str(r[0]))
            if t.date().isoformat() != day:
                continue
            out.append({"time": int(t.timestamp()), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
                        "close": float(r[4]), "volume": float(r[5]) if len(r) > 5 and r[5] is not None else None,
                        "atp": None})
        out.sort(key=lambda c: c["time"])                 # Upstox lists the newest first
        self._hist[ck] = (time.monotonic(), out)
        return out

    # ---- chains -----------------------------------------------------------------------------
    def _sweep_chains(self, symbols: list[str]) -> None:
        if not symbols or not self.chain_calls_per_poll:
            return
        n = min(len(symbols), self.chain_calls_per_poll)
        for i in range(n):
            sym = symbols[(self._cursor + i) % len(symbols)]
            fo = next((v for (s, t, *_), v in self._fo.items() if s == sym and t == "FUT"), None)
            if not fo:
                continue
            try:
                self._fetch_chain(sym, self._nearest_expiry(sym))
            except Exception as exc:  # noqa: BLE001 - one chain must not stall the sweep
                log.warning("option chain %s: %s", sym, exc)
        self._cursor = (self._cursor + n) % len(symbols)

    def _nearest_expiry(self, sym: str) -> str:
        today = datetime.now(IST).date().isoformat()
        exps = sorted(v["expiry"] for (s, t, *_), v in self._fo.items() if s == sym and t == "FUT" and v["expiry"] >= today)
        return exps[0] if exps else sorted(v["expiry"] for (s, t, *_), v in self._fo.items() if s == sym and t == "FUT")[-1]

    def _fetch_chain(self, sym: str, expiry: str) -> dict | None:
        e = self._eq.get(sym)
        if not e:
            return None
        data = self._get("/option/chain", {"instrument_key": e["key"], "expiry_date": expiry})
        if not data:
            return None
        strikes: dict[tuple[float, str], dict] = {}
        call_oi = put_oi = 0.0
        for row in data:
            k = float(row.get("strike_price"))
            for side, leg in (("CE", row.get("call_options") or {}), ("PE", row.get("put_options") or {})):
                md = leg.get("market_data") or {}
                gk = leg.get("option_greeks") or {}
                oi = float(md.get("oi") or 0)
                strikes[(k, side)] = {"last_price": md.get("ltp"), "open_interest": int(oi), "prev_oi": md.get("prev_oi"),
                                      "volume": md.get("volume"), "iv": gk.get("iv")}
                if side == "CE":
                    call_oi += oi
                else:
                    put_oi += oi
        chain = {"expiry": expiry, "strikes": strikes, "call_oi": int(call_oi), "put_oi": int(put_oi),
                 "pcr": round(put_oi / call_oi, 2) if call_oi > 0 else None,
                 "spot": next((r.get("underlying_spot_price") for r in data if r.get("underlying_spot_price")), None),
                 "ts": datetime.now(IST).strftime("%H:%M:%S"), "epoch": time.time()}
        self._chains[sym] = chain
        return chain

    # ---- http -------------------------------------------------------------------------------
    def _get(self, path: str, params: dict, base: str = None):
        self.limiter.wait()
        r = self.session.get((base or BASE) + path, params=params, timeout=self.timeout)
        if r.status_code == 401:
            raise PermissionError("Upstox rejected the Analytics Token (401): regenerate it on the Developer Apps page")
        if r.status_code == 429:
            raise RuntimeError("Upstox rate limit hit (429): lower UPSTOX_CHAIN_CALLS_PER_POLL or raise POLL_SECONDS")
        r.raise_for_status()
        body = r.json()
        if body.get("status") != "success":
            raise RuntimeError(f"Upstox error: {body.get('errors') or body}")
        return body.get("data")


def _chunks(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def _stream_rows(fh, chunk: int = 1 << 20):
    """The objects of a top-level JSON array, read `chunk` characters at a time (memory: one chunk plus one row)."""
    dec, buf, started = json.JSONDecoder(), "", False
    while True:
        data = fh.read(chunk)
        buf += data
        i = 0
        if not started:
            j = buf.find("[")
            if j < 0:
                if not data:
                    return
                continue
            i, started = j + 1, True
        while True:
            while i < len(buf) and buf[i] in " \r\n\t,":
                i += 1
            if i >= len(buf):
                break
            if buf[i] == "]":
                return
            try:
                obj, i2 = dec.raw_decode(buf, i)
            except ValueError:                            # the row continues in the next chunk
                break
            yield obj
            i = i2
        buf = buf[i:]
        if not data:
            return


def _num(v):
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _pos(v):
    f = _num(v)
    return f if f and f > 0 else None


def _int(v):
    f = _num(v)
    return None if f is None else int(f)


def _depth(raw) -> dict:
    """Upstox depth {"buy": [{quantity, price, orders}], "sell": [...]} -> {"bid": [(price, qty)], "ask": [...]},
    best level first, empty levels (price or quantity 0) dropped, at most DEPTH_LEVELS (as server/kotak.py)."""
    raw = raw if isinstance(raw, dict) else {}

    def side(levels, best_high: bool) -> list[tuple[float, int]]:
        out = []
        for lv in levels if isinstance(levels, list) else []:
            px, qty = _num((lv or {}).get("price")), _int((lv or {}).get("quantity"))
            if px and px > 0 and qty and qty > 0:
                out.append((px, qty))
        out.sort(key=lambda x: -x[0] if best_high else x[0])
        return out[:DEPTH_LEVELS]

    return {"bid": side(raw.get("buy"), True), "ask": side(raw.get("sell"), False)}


def _ts(v) -> str | None:
    """Upstox's quote time (epoch ms in last_trade_time, or an ISO string in timestamp) -> 'YYYY-MM-DD HH:MM:SS' IST."""
    if v in (None, "", 0, "0"):
        return None
    try:
        n = float(v)
        return datetime.fromtimestamp(n / 1000 if n > 1e11 else n, tz=IST).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(str(v)).astimezone(IST).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def _parse_full(e: dict, fo: bool) -> dict:
    """One full market quote (GET /v2/market-quote/quotes) in server/kotak.py's _parse_quote shape. The previous
    close is last_price - net_change (Upstox's ohlc is today's bar)."""
    ltp = _num(e.get("last_price"))
    d = {"last_price": ltp, "volume": _int(e.get("volume")),
         "timestamp": _ts(e.get("last_trade_time")) or _ts(e.get("timestamp")), "depth": _depth(e.get("depth")),
         "atp": _pos(e.get("average_price")), "ltq": None,
         "buy_qty": _int(e.get("total_buy_quantity")), "sell_qty": _int(e.get("total_sell_quantity")),
         "lower_circuit": _pos(e.get("lower_circuit_limit")), "upper_circuit": _pos(e.get("upper_circuit_limit"))}
    o = e.get("ohlc") or {}
    prev = round(ltp - float(e["net_change"]), 2) if ltp is not None and _num(e.get("net_change")) is not None else None
    ohlc = {"open": _pos(o.get("open")), "high": _pos(o.get("high")), "low": _pos(o.get("low")), "close": prev}
    if any(ohlc.values()):
        d["ohlc"] = ohlc
    if fo:
        d["open_interest"] = _int(e.get("oi"))
    return d
