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
Rate limits: 25/s, 250/min, 1000 per 30 min. A poll spends 2 quote calls plus
UPSTOX_CHAIN_CALLS_PER_POLL option-chain calls (default 12) on a rolling sweep of the universe, so at a
30 s poll every stock's PCR and per-strike OI refresh roughly every nine minutes while LTP and
futures OI refresh every poll, at about 840 calls per 30 minutes.
"""
from __future__ import annotations

import gzip
import io
import json
import logging
import re
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

import requests

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
BASE = "https://api.upstox.com/v2"
INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
KEY_RE = re.compile(r"^(?P<sym>.+?)(?P<yy>\d{2})(?P<mon>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
                    r"(?:(?P<strike>\d+(?:\.\d+)?)(?P<side>CE|PE)|(?P<fut>FUT))$")


class RateLimiter:
    """Sliding windows for 25/s, 250/min and 1000/30 min."""

    def __init__(self, per_second=25, per_minute=250, per_30min=1000):
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

    # ---- instrument master --------------------------------------------------------------
    def load_instruments(self) -> None:
        if self._loaded:
            return
        r = self.session.get(INSTRUMENTS_URL, timeout=60)
        r.raise_for_status()
        raw = gzip.decompress(r.content) if r.content[:2] == b"\x1f\x8b" else r.content
        rows = json.loads(raw)
        self._ingest_instruments(rows)

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

        for chunk in _chunks(list(eq_keys) + list(fut_keys), 500):
            data = self._get("/market-quote/quotes", {"instrument_key": ",".join(chunk)})
            for entry in (data or {}).values():
                tok = entry.get("instrument_token")
                ours = eq_keys.get(tok) or fut_keys.get(tok)
                if not ours:
                    continue
                q = {"last_price": entry.get("last_price"), "volume": entry.get("volume"), "timestamp": entry.get("timestamp")}
                if tok in fut_keys:
                    q["open_interest"] = entry.get("oi")
                elif entry.get("last_price") is not None and entry.get("net_change") is not None:
                    q["ohlc"] = {"close": round(float(entry["last_price"]) - float(entry["net_change"]), 2)}
                out[ours] = q

        # rolling chain sweep over every stock we have a future for: exact PCR + per-strike OI
        futs = sorted({KEY_RE.match(k[4:]).group("sym") for k in fut_keys.values()})
        self._sweep_chains(futs)
        for sym in futs:
            c = self._chains.get(sym)
            if c:
                out["PCR:" + sym] = {"pcr": c["pcr"], "call_oi": c["call_oi"], "put_oi": c["put_oi"], "pcr_ts": c["ts"]}

        # options asked for explicitly (an open strike table): serve from a fresh cache or fetch now
        for (sym, expiry), wanted in opt_groups.items():
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
    def _get(self, path: str, params: dict):
        self.limiter.wait()
        r = self.session.get(BASE + path, params=params, timeout=self.timeout)
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
