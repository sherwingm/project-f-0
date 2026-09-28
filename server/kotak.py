"""Kotak Neo adapter on the official `kotakneoapi` SDK (pip install kotakneoapi pyotp).

Two independent parts:

KotakProvider (live data, read-only)
    Needs only KOTAK_CONSUMER_KEY. Kotak's quotes(), option_chain(), expiries() and scrip_master()
    authenticate with the consumer key alone (no TOTP session), so a data-only deployment holds
    nothing that can trade.
      quotes()        50 instruments per call, 25 calls/second: LTP, volume, open_int, previous close,
                      5-level depth (also for one contract on demand: quote_one)
      option_chain()  one underlying per call: every strike's LTP, OI and OI change -> exact PCR
    Each poll: LTP + futures OI for the whole universe in ~10 quote calls, plus a rolling sweep of
    KOTAK_CHAIN_CALLS_PER_POLL option chains for live PCR / strike OI (default 12: at a 30 s poll the
    universe's PCR refreshes about every 9 minutes; each row shows when its PCR was read).

KotakBroker (real orders; only used with ORDERS=true PAPER=false BROKER=kotak)
    Needs mobile, UCC, TOTP secret and MPIN: totp_login() gives a view token, totp_validate() the
    trade token. Contracts resolve against Kotak's scrip master (trading symbol, lot size, token).
    Order placement has not been run against a live account: use paper mode first, then one lot.

Scrip master (Kotak CSV, "transformed" format): pSymbol = token, pSymbolName = underlying,
pTrdSymbol = trading symbol (RELIANCE26SEPFUT / RELIANCE26SEP1300CE / RELIANCE-EQ),
pOptionType = CE | PE | XX(futures), pInstType = FUTSTK | OPTSTK | ..., lLotSize,
"dStrikePrice;" = strike x 100 (the column really is named with a semicolon),
pExpiryDate = seconds with Kotak's epoch offset: unix = pExpiryDate + 315511200 (as the SDK does).
"""
from __future__ import annotations

import io
import logging
import os
import re
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from server.broker import Broker, OrderRequest

log = logging.getLogger(__name__)

# The SDK logs Kotak's error bodies, and Kotak echoes the consumer key back in them
# ("Consumer key '<key>' is invalid"), so its console and file logs would print and store the key.
# Both are off unless the operator opts in with NEO_LOG_LEVEL / NEO_LOG_FILE_ENABLED; our own
# errors carry the (redacted) message instead. Must run before neo_api_client is imported.
os.environ.setdefault("NEO_LOG_LEVEL", "NOLOG")
os.environ.setdefault("NEO_LOG_FILE_ENABLED", "false")
_SECRETS: set[str] = set()


def redact(text) -> str:
    """Replace every registered Kotak credential in ``text`` with <redacted>."""
    out = str(text)
    for s in sorted(_SECRETS, key=len, reverse=True):
        out = out.replace(s, "<redacted>")
    return out


IST = timezone(timedelta(hours=5, minutes=30))
EPOCH_OFFSET = 315511200          # Kotak scrip-master expiry epoch -> unix (per the SDK's own conversion)
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
KEY_RE = re.compile(r"^(?P<sym>.+?)(?P<yy>\d{2})(?P<mon>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
                    r"(?:(?P<strike>\d+(?:\.\d+)?)(?P<side>CE|PE)|(?P<fut>FUT))$")


# ---------------------------------------------------------------- session
class KotakSession:
    """One NeoAPI client for the whole server. Data calls need no login; trading calls get a
    TOTP + MPIN session on first use and again after a 403 / session error."""

    def __init__(self, consumer_key: str, mobile: str | None = None, ucc: str | None = None,
                 totp_secret: str | None = None, mpin: str | None = None, environment: str = "prod"):
        if not consumer_key:
            raise ValueError("KOTAK_CONSUMER_KEY is required (Neo app -> More -> Trade API -> Generate application)")
        self.consumer_key, self.mobile, self.ucc, self.totp_secret, self.mpin = consumer_key, mobile, ucc, totp_secret, mpin
        _SECRETS.update(s for s in (consumer_key, mobile, ucc, totp_secret, mpin) if s and len(s) >= 4)
        self.environment = environment
        self._client = None
        self._trade_ready = False
        self.lock = threading.Lock()

    def client(self):
        with self.lock:
            if self._client is None:
                from neo_api_client import NeoAPI
                self._client = NeoAPI(consumer_key=self.consumer_key, environment=self.environment)
            return self._client

    @property
    def can_trade(self) -> bool:
        return bool(self.mobile and self.ucc and self.totp_secret and self.mpin)

    def login_view(self) -> dict:
        """Step 1 of Kotak's flow: TOTP -> view token. Returns the response data."""
        if not (self.mobile and self.ucc and self.totp_secret):
            raise ValueError("KOTAK_MOBILE, KOTAK_UCC and KOTAK_TOTP_SECRET are needed to log in")
        import pyotp
        r = self.client().totp_login(mobile_number=self.mobile, ucc=self.ucc, totp=pyotp.TOTP(self.totp_secret).now())
        _raise_if_error(r, "totp_login")
        return r.get("data", r)

    def login_trade(self) -> dict:
        """Steps 1 + 2: TOTP then MPIN -> trade token. Required before any order call."""
        self.login_view()
        if not self.mpin:
            raise ValueError("KOTAK_MPIN is needed for trading calls")
        r = self.client().totp_validate(mpin=self.mpin)
        _raise_if_error(r, "totp_validate")
        with self.lock:
            self._trade_ready = True
        return r.get("data", r)

    def trade_client(self):
        if not self._trade_ready:
            self.login_trade()
        return self.client()

    def trade_call(self, method: str, *args, **kwargs):
        r = getattr(self.trade_client(), method)(*args, **kwargs)
        if _is_session_error(r):
            log.warning("Kotak session error on %s; logging in again", method)
            self.login_trade()
            r = getattr(self.client(), method)(*args, **kwargs)
        _raise_if_error(r, method)
        return r


def _is_session_error(r) -> bool:
    if not isinstance(r, dict):
        return False
    txt = str(r.get("error") or r.get("Error") or r.get("message") or "").lower()
    return "session" in txt or "re-login" in txt or "403" in txt or "invalid token" in txt


def _raise_if_error(r, what: str) -> None:
    if isinstance(r, dict) and (r.get("error") or r.get("Error")):
        err = r.get("error") or r.get("Error")
        if err is True:                      # Kotak's REST errors: {"error": true, "message": "..."}
            err = r.get("message") or r.get("errMsg") or r
        raise RuntimeError(redact(f"Kotak {what}: {err}"))
    if isinstance(r, dict) and str(r.get("stat", "")).lower() == "not_ok":
        raise RuntimeError(redact(f"Kotak {what}: {r.get('errMsg') or r.get('emsg') or r}"))


class RateLimiter:
    """Kotak documents 25 requests/second on market data; the per-minute cap is not published,
    so we also hold a conservative 200/min."""

    def __init__(self, per_second: int = 20, per_minute: int = 200):
        self.per_second, self.per_minute = per_second, per_minute
        self.calls: deque[float] = deque()
        self.lock = threading.Lock()

    def wait(self) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                while self.calls and now - self.calls[0] > 60:
                    self.calls.popleft()
                last_sec = sum(1 for t in self.calls if now - t < 1)
                if len(self.calls) < self.per_minute and last_sec < self.per_second:
                    self.calls.append(now)
                    return
                sleep = 0.06 if last_sec >= self.per_second else max(0.05, 60 - (now - self.calls[0]))
            time.sleep(min(sleep, 2.0))


# ---------------------------------------------------------------- scrip master
class ScripMaster:
    """Kotak's daily instrument files for nse_cm and nse_fo, mapped to our symbol convention."""

    def __init__(self, session: KotakSession):
        self.s = session
        self.eq: dict[str, dict] = {}                 # SYMBOL -> {"token", "tradingsymbol"}
        self.fo: dict[tuple, dict] = {}               # (SYMBOL, "FUT"|"CE"|"PE", expiry ISO, strike|None) -> {...}
        self.fo_by_symbol: dict[str, dict] = {}       # tradingsymbol -> the same record
        self.loaded = False

    def load(self) -> None:
        if self.loaded:
            return
        listing = self.s.client().scrip_master()
        _raise_if_error(listing, "scrip_master")
        paths = listing.get("filesPaths", []) if isinstance(listing, dict) else []
        cm = next((p for p in paths if p.endswith("nse_cm-v1.csv") or p.endswith("/nse_cm.csv")), None)
        fo = next((p for p in paths if p.endswith("/nse_fo.csv")), None)
        if not (cm and fo):
            raise RuntimeError(f"scrip master listing has no nse_cm/nse_fo files: {paths}")
        self.ingest_cm(_read_csv(cm))
        self.ingest_fo(_read_csv(fo))
        self.loaded = True
        log.info("Kotak scrip master: %d equities, %d NSE F&O contracts", len(self.eq), len(self.fo))

    def ingest_cm(self, df: pd.DataFrame) -> None:
        df = df.rename(columns=lambda c: str(c).strip())
        for r in df.to_dict("records"):
            trd = str(r.get("pTrdSymbol", "")).strip()
            if trd.endswith("-EQ"):
                self.eq[trd[:-3]] = {"token": str(r.get("pSymbol")).strip(), "tradingsymbol": trd}

    def ingest_fo(self, df: pd.DataFrame) -> None:
        df = df.rename(columns=lambda c: str(c).strip())
        strike_col = next((c for c in df.columns if c.startswith("dStrikePrice")), None)
        for r in df.to_dict("records"):
            inst = str(r.get("pInstType", "")).strip()
            if inst not in ("FUTSTK", "OPTSTK"):
                continue
            sym = str(r.get("pSymbolName", "")).strip()
            opt = str(r.get("pOptionType", "")).strip().upper()
            typ = "FUT" if inst == "FUTSTK" or opt == "XX" else opt
            if typ not in ("FUT", "CE", "PE"):
                continue
            try:
                exp = datetime.fromtimestamp(int(float(r["pExpiryDate"])) + EPOCH_OFFSET, tz=IST).date().isoformat()
            except (KeyError, ValueError, TypeError):
                continue
            strike = None
            if typ != "FUT" and strike_col is not None and pd.notna(r.get(strike_col)):
                strike = float(r[strike_col]) / 100.0
            rec = {"token": str(r.get("pSymbol")).strip(), "tradingsymbol": str(r.get("pTrdSymbol", "")).strip(),
                   "lot_size": int(float(r.get("lLotSize") or 0)), "expiry": exp, "symbol": sym, "type": typ, "strike": strike}
            self.fo[(sym, typ, exp, strike)] = rec
            self.fo_by_symbol[rec["tradingsymbol"]] = rec

    def expiries(self, sym: str) -> list[str]:
        return sorted({k[2] for k in self.fo if k[0] == sym and k[1] == "FUT"})

    def resolve_key(self, parsed: dict) -> dict | None:
        """Our key convention (SYMBOL + YY + MON + [strike + CE/PE | FUT]) -> scrip-master record."""
        typ = "FUT" if parsed.get("fut") else parsed["side"]
        strike = float(parsed["strike"]) if parsed.get("strike") else None
        for exp in self.expiries(parsed["sym"]):
            d = datetime.strptime(exp, "%Y-%m-%d")
            if d.strftime("%y") == parsed["yy"] and MONTHS[d.month - 1] == parsed["mon"]:
                return self.fo.get((parsed["sym"], typ, exp, strike))
        return None


def _read_csv(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content), low_memory=False)


# ---------------------------------------------------------------- live data
# Kotak's quotes call refuses 50 instruments ("Please set the Neo symbol max value to 50"); 49 is accepted.
QUOTE_BATCH = 49
# option_chain answers "Rate limit exceeded" to calls 0.25 s apart and not to calls 1 s apart (checked 2026-09-28)
CHAIN_MIN_INTERVAL = 1.0


class KotakProvider:
    """quote(keys) -> {key: {...}} in the shape LiveFeed expects.

    keys:  NSE:<SYMBOL>                    equity: last_price, volume, ohlc.close (= previous close)
           NFO:<SYMBOL><YY><MON>FUT        near future: last_price, open_interest
           NFO:<SYMBOL><YY><MON><K>CE/PE   options: last_price, open_interest, volume (from the chain)
    Adds:  PCR:<SYMBOL>                    {"pcr", "call_oi", "put_oi", "pcr_ts"} from the rolling chain sweep
    """

    def __init__(self, session: KotakSession, chain_calls_per_poll: int = 12, chain_strikes: int = 60):
        self.s = session
        self.master = ScripMaster(session)
        self.limiter = RateLimiter()
        self.chain_calls_per_poll = max(0, chain_calls_per_poll)
        self.chain_strikes = chain_strikes          # per side; Kotak wants a multiple of 10
        self._chains: dict[str, dict] = {}
        self._cursor = 0
        self._last_chain = 0.0

    def quote(self, keys: list[str]) -> dict[str, dict]:
        self.master.load()
        out: dict[str, dict] = {}
        tok_to_key: dict[tuple[str, str], str] = {}         # (segment, token) -> our key
        opt_wanted: dict[tuple[str, str], list[tuple[str, str]]] = {}   # (sym, expiry) -> [(tradingsymbol, ourkey)]
        futs: list[str] = []
        for k in keys:
            if k.startswith("NSE:"):
                e = self.master.eq.get(k[4:])
                if e:
                    tok_to_key[("nse_cm", e["token"])] = k
            elif k.startswith("NFO:"):
                m = KEY_RE.match(k[4:])
                if not m:
                    continue
                p = m.groupdict()
                rec = self.master.resolve_key(p)
                if not rec:
                    continue
                tok_to_key[("nse_fo", rec["token"])] = k      # options too: the quote carries their depth
                if p.get("fut"):
                    futs.append(p["sym"])
                else:
                    opt_wanted.setdefault((p["sym"], rec["expiry"]), []).append((rec["tradingsymbol"], k))

        # LTP / volume / OI / previous close / 5-level depth in batches of QUOTE_BATCH
        items = [{"instrument_token": t, "exchange_segment": seg} for (seg, t) in tok_to_key]
        for batch in _chunks(items, QUOTE_BATCH):
            for q in self._quotes(batch):
                key = tok_to_key.get((str(q.get("exchange", "")).lower(), str(q.get("exchange_token", ""))))
                if key:
                    out[key] = _parse_quote(q, fo=key.startswith("NFO:"))

        # rolling option-chain sweep -> exact live PCR per stock
        self._sweep(sorted(set(futs)))
        for sym in set(futs):
            c = self._chains.get(sym)
            if c:
                out["PCR:" + sym] = {"pcr": c["pcr"], "call_oi": c["call_oi"], "put_oi": c["put_oi"], "pcr_ts": c["ts"]}

        # options asked for explicitly (an open strike table): fresh cache or fetch now
        for (sym, expiry), wanted in opt_wanted.items():
            c = self._chains.get(sym)
            if not c or c["expiry"] != expiry or time.time() - c["epoch"] > 120:
                try:
                    c = self._fetch_chain(sym, expiry)
                except Exception as exc:  # noqa: BLE001
                    log.warning("option chain %s %s: %s", sym, expiry, exc)
                    continue
            if not c:
                continue
            for ts, ourkey in wanted:
                row = c["strikes"].get(ts)
                if row:                                   # chain adds prev OI / OI change; the quote's own fields win
                    out[ourkey] = {**row, **{k: v for k, v in out.get(ourkey, {}).items() if v is not None}}
        return out

    def quote_one(self, tradingsymbol: str) -> dict:
        """One F&O contract on demand (the fill engine's options are not in the polling universe):
        last_price, volume, open_interest, timestamp and 5-level depth, plus the contract's
        lot size and expiry from the scrip master. Accepts RELIANCE26SEP1300CE or NFO:RELIANCE26SEP1300CE."""
        self.master.load()
        ts = tradingsymbol.split(":", 1)[1] if ":" in tradingsymbol else tradingsymbol
        rec = self.master.fo_by_symbol.get(ts)
        if rec is None:
            m = KEY_RE.match(ts)
            rec = self.master.resolve_key(m.groupdict()) if m else None
        if rec is None:
            raise ValueError(f"{ts} is not in Kotak's NSE F&O scrip master")
        rows = [q for q in self._quotes([{"instrument_token": rec["token"], "exchange_segment": "nse_fo"}])
                if str(q.get("exchange_token", "")) == rec["token"]]
        if not rows:
            raise RuntimeError(f"Kotak quotes: no quote returned for {ts}")
        return {**_parse_quote(rows[0], fo=True), "tradingsymbol": rec["tradingsymbol"],
                "lot_size": rec["lot_size"], "expiry": rec["expiry"]}

    def _quotes(self, batch: list[dict]) -> list[dict]:
        self.limiter.wait()
        resp = self.s.client().quotes(instrument_tokens=batch, quote_type="all")
        rows = resp if isinstance(resp, list) else (resp.get("data") if isinstance(resp, dict) else None)
        if not isinstance(rows, list):
            raise RuntimeError(redact(f"Kotak quotes: unexpected response {str(resp)[:200]}"))
        return rows

    # ---- chains
    def _sweep(self, symbols: list[str]) -> None:
        if not symbols or not self.chain_calls_per_poll:
            return
        n = min(len(symbols), self.chain_calls_per_poll)
        for i in range(n):
            sym = symbols[(self._cursor + i) % len(symbols)]
            try:
                self._fetch_chain(sym, self._nearest_expiry(sym))
            except Exception as exc:  # noqa: BLE001 - one chain must not stall the sweep
                log.warning("option chain %s: %s", sym, exc)
        self._cursor = (self._cursor + n) % len(symbols)

    def _nearest_expiry(self, sym: str) -> str | None:
        today = datetime.now(IST).date().isoformat()
        exps = [e for e in self.master.expiries(sym) if e >= today]
        return exps[0] if exps else None

    def _fetch_chain(self, sym: str, expiry: str | None) -> dict | None:
        self.limiter.wait()
        wait = CHAIN_MIN_INTERVAL - (time.monotonic() - self._last_chain)
        if wait > 0:
            time.sleep(wait)
        self._last_chain = time.monotonic()
        resp = self.s.client().option_chain(exchange="nse_fo", underlying=sym, expiry=expiry,
                                            instrument_type="option", count=self.chain_strikes)
        _raise_if_error(resp, f"option_chain {sym}")
        # the live API answers {call, put, common_data, ...} at the top level with short keys (inst, oi.cur,
        # oi.prev, oi.chg, quote.vol, quote.pc; seen 2026-09-28); the documented shape wraps it in "data" with
        # long keys (instrument, openInterest.current, ...). Both are read.
        resp = resp or {}
        data = resp.get("data") if isinstance(resp.get("data"), dict) else resp
        strikes: dict[str, dict] = {}
        call_oi = put_oi = 0.0
        for side in ("call", "put"):
            for leg in data.get(side) or []:
                inst = leg.get("instrument") or leg.get("inst") or {}
                q, oi = leg.get("quote") or {}, leg.get("openInterest") or leg.get("oi") or {}
                ts = str(inst.get("symbol", "")).strip()
                cur = _f(_first(oi, "current", "cur")) or 0.0
                strikes[ts] = {"last_price": _f(q.get("ltp")), "open_interest": int(cur),
                               "prev_oi": _i(_first(oi, "previous", "prev")), "oi_change": _i(_first(oi, "change", "chg")),
                               "volume": _i(_first(q, "volume", "vol")), "prev_close": _f(_first(q, "prevClose", "pc"))}
                if side == "call":
                    call_oi += cur
                else:
                    put_oi += cur
        common = data.get("common_data") or {}
        chain = {"expiry": common.get("expiryDt") or expiry, "strikes": strikes, "call_oi": int(call_oi), "put_oi": int(put_oi),
                 "pcr": round(put_oi / call_oi, 2) if call_oi > 0 else None,
                 "lot_size": _i(common.get("mktLot")), "ts": datetime.now(IST).strftime("%H:%M:%S"), "epoch": time.time()}
        self._chains[sym] = chain
        return chain


def _first(d: dict, *keys):
    """The first of `keys` present in d (live and documented payloads name the same field differently)."""
    return next((d[k] for k in keys if k in d), None)


# ---------------------------------------------------------------- orders
class KotakBroker(Broker):
    """Real orders through Kotak Neo (NRML, DAY validity). Contracts come from Kotak's scrip
    master, so trading symbols and lot sizes are the broker's. Not yet run against a live
    account: paper first, then one lot."""
    name = "kotak"
    paper = False

    def __init__(self, session: KotakSession):
        self.s = session
        self.master = ScripMaster(session)

    def resolve(self, req: OrderRequest, lot_size: int) -> dict:
        self.master.load()
        key = (req.symbol, req.instrument, req.expiry, float(req.strike) if req.instrument != "FUT" and req.strike is not None else None)
        rec = self.master.fo.get(key)
        if not rec:
            raise ValueError(f"no NSE F&O contract on Kotak for {req.symbol} {req.instrument} {req.expiry} {req.strike or ''}")
        lot = rec["lot_size"] or lot_size
        return {"tradingsymbol": rec["tradingsymbol"], "quantity": req.lots * lot, "lot_size": lot,
                "exchange": "NSE", "segment": "nse_fo", "exchange_token": rec["token"]}

    def margin(self, req: OrderRequest, resolved: dict, ref_price: float | None) -> float | None:
        try:
            r = self.s.trade_call("margin_required", exchange_segment="nse_fo", price=str(req.price or ref_price or 0),
                                  order_type="L" if req.order_type == "LIMIT" else "MKT", product="NRML",
                                  quantity=str(resolved["quantity"]), instrument_token=resolved["exchange_token"],
                                  transaction_type="B" if req.side == "BUY" else "S")
            d = r.get("data", r) if isinstance(r, dict) else {}
            for k in ("totMrgnReq", "totalMarginRequired", "reqdMargin", "requiredMargin", "margin"):
                if d.get(k) is not None:
                    return float(d[k])
        except Exception as exc:  # noqa: BLE001
            log.warning("margin check failed: %s", exc)
        return None

    def place(self, req: OrderRequest, resolved: dict, ref_price: float | None) -> dict:
        r = self.s.trade_call("place_order", exchange_segment="nse_fo", product="NRML",
                              price=str(req.price) if req.order_type == "LIMIT" else "0",
                              order_type="L" if req.order_type == "LIMIT" else "MKT",
                              quantity=str(resolved["quantity"]), validity="DAY",
                              trading_symbol=resolved["tradingsymbol"],
                              transaction_type="B" if req.side == "BUY" else "S", tag="FOS")
        from dataclasses import asdict
        d = r.get("data", r) if isinstance(r, dict) else {}
        return {"order_id": d.get("nOrdNo") or d.get("orderId") or d.get("order_id"),
                "placed_at": datetime.now(IST).isoformat(timespec="seconds"),
                "status": d.get("stat") or d.get("status") or "SENT", "paper": False, "remark": d.get("stCode") or d.get("errMsg"),
                **asdict(req), **resolved}

    def orders(self) -> list[dict]:
        r = self.s.trade_call("order_report")
        rows = r.get("data", []) if isinstance(r, dict) else []
        return [{"order_id": o.get("nOrdNo"), "placed_at": o.get("ordDtTm") or o.get("orderTime"), "status": o.get("ordSt") or o.get("status"),
                 "paper": False, "tradingsymbol": o.get("trdSym") or o.get("tradingSymbol"), "side": o.get("trnsTp"),
                 "quantity": _i(o.get("qty")), "order_type": o.get("prcTp"), "price": _f(o.get("prc")),
                 "fill_price": _f(o.get("avgPrc")), "status_message": o.get("rejRsn") or o.get("remark")} for o in rows]

    def positions(self) -> list[dict]:
        r = self.s.trade_call("positions")
        rows = r.get("data", []) if isinstance(r, dict) else []
        out = []
        for p in rows:
            buy = (_i(p.get("flBuyQty")) or 0) + (_i(p.get("cfBuyQty")) or 0)
            sell = (_i(p.get("flSellQty")) or 0) + (_i(p.get("cfSellQty")) or 0)
            qty = buy - sell
            if qty:
                out.append({"tradingsymbol": p.get("trdSym"), "quantity": qty,
                            "avg_price": _f(p.get("buyAmt") or 0) / buy if qty > 0 and buy else (_f(p.get("sellAmt") or 0) / sell if sell else None),
                            "pnl": None})
        return out


# ---------------------------------------------------------------- helpers
DEPTH_LEVELS = 5


def _parse_quote(q: dict, fo: bool) -> dict:
    d = {"last_price": _f(q.get("ltp")), "volume": _i(q.get("last_volume")),
         "timestamp": _ts(q.get("lstup_time")), "depth": _depth(q.get("depth"))}
    if fo:
        d["open_interest"] = _i(q.get("open_int"))
    else:
        prev = _f((q.get("ohlc") or {}).get("close"))
        if prev:
            d["ohlc"] = {"close": prev}
    return d


def _depth(raw) -> dict:
    """Kotak depth {"buy": [{price, quantity, orders}], "sell": [...]} (strings) ->
    {"bid": [(price, qty), ...], "ask": [...]}, floats/ints, best level first, empty levels dropped."""
    raw = raw if isinstance(raw, dict) else {}

    def side(levels, best_high: bool) -> list[tuple[float, int]]:
        out = []
        for lv in levels if isinstance(levels, list) else []:
            px, qty = _f((lv or {}).get("price")), _i((lv or {}).get("quantity"))
            if px and px > 0 and qty and qty > 0:
                out.append((px, qty))
        out.sort(key=lambda x: -x[0] if best_high else x[0])
        return out[:DEPTH_LEVELS]

    return {"bid": side(raw.get("buy"), True), "ask": side(raw.get("sell"), False)}


_SHARED: KotakSession | None = None


def shared_session(settings) -> KotakSession:
    global _SHARED
    if _SHARED is None:
        _SHARED = KotakSession(settings.kotak_consumer_key, settings.kotak_mobile or None, settings.kotak_ucc or None,
                               settings.kotak_totp_secret or None, settings.kotak_mpin or None)
    return _SHARED


def _f(v):
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _i(v):
    f = _f(v)
    return None if f is None else int(f)


def _ts(v):
    try:
        return datetime.fromtimestamp(int(float(v)), tz=IST).strftime("%Y-%m-%d %H:%M:%S") if v else None
    except (TypeError, ValueError, OSError):
        return None


def _chunks(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]
