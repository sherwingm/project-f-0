"""Groww Trading API adapter: a live-quote Provider and an order Broker, both on the official
`growwapi` SDK (pip install growwapi pyotp). Groww's API is one flat subscription
(₹499 + GST/month as of Sept 2026) that covers orders, live quotes with open interest, the option
chain with Greeks, and historical candles.

Login (TOTP flow, works headless; the TOTP key does not expire):
    GROWW_TOTP_TOKEN + GROWW_TOTP_SECRET  ->  GrowwAPI.get_access_token(api_key=token, totp=now)
or paste a token generated on the Groww Cloud API Keys page into GROWW_ACCESS_TOKEN.

Rate limits that shape the live loop (all "Live Data" calls share one budget: 10/s, 300/min):
    get_ltp / get_ohlc    up to 50 instruments per call, no OI
    get_quote             ONE instrument per call, includes open_interest and oi_day_change
    get_option_chain      one underlying + expiry per call, every strike with LTP, OI and Greeks
    GrowwFeed (WebSocket) LTP and depth only, no OI
So each poll fetches LTP for every stock and every near future in ~10 batched calls, and refreshes
futures OI for a rolling slice of the universe with single-instrument quotes; with the default
GROWW_OI_CALLS_PER_POLL=60 and a 30 s poll the whole universe's OI is refreshed about every
two minutes while staying under the per-minute limit. Strike tables use the option-chain call.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

from server.broker import Broker, OrderRequest

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))


# ---------------------------------------------------------------- session / login
def groww_access_token(totp_token: str | None, totp_secret: str | None, access_token: str | None) -> str:
    """Return a usable access token: the pasted one if given, else generate via the TOTP flow."""
    if access_token:
        return access_token
    if totp_token and totp_secret:
        import pyotp
        from growwapi import GrowwAPI
        return GrowwAPI.get_access_token(api_key=totp_token, totp=pyotp.TOTP(totp_secret).now())
    raise ValueError("set GROWW_ACCESS_TOKEN, or GROWW_TOTP_TOKEN + GROWW_TOTP_SECRET")


class GrowwSession:
    """Holds the SDK client and re-logs in once if a call fails with an authentication error
    (Groww access tokens are issued per day; the TOTP key itself does not expire)."""

    def __init__(self, totp_token: str | None, totp_secret: str | None, access_token: str | None):
        self.totp_token, self.totp_secret, self.static_token = totp_token, totp_secret, access_token
        self._client = None
        self.lock = threading.Lock()

    def client(self):
        with self.lock:
            if self._client is None:
                from growwapi import GrowwAPI
                self._client = GrowwAPI(groww_access_token(self.totp_token, self.totp_secret, self.static_token))
            return self._client

    def refresh(self) -> None:
        with self.lock:
            self._client = None
        self.client()

    def call(self, method: str, *args, **kwargs):
        try:
            return getattr(self.client(), method)(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            if _is_auth_error(exc) and (self.totp_token and self.totp_secret):
                log.warning("Groww auth error on %s (%s); regenerating access token", method, exc)
                self.refresh()
                return getattr(self.client(), method)(*args, **kwargs)
            raise


def _is_auth_error(exc: Exception) -> bool:
    name = type(exc).__name__
    return name in ("GrowwAPIAuthenticationException", "GrowwAPIAuthorisationException") or "401" in str(exc)


class RateLimiter:
    """Sliding-window limiter for Groww's Live Data budget (10 per second, 300 per minute)."""

    def __init__(self, per_second: int = 10, per_minute: int = 300):
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
                sleep = 0.11 if last_sec >= self.per_second else max(0.05, 60 - (now - self.calls[0]))
            time.sleep(min(sleep, 2.0))


def _chunks(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


# ---------------------------------------------------------------- live quotes
class GrowwProvider:
    """quote(keys) -> {key: {...}} in the shape LiveFeed expects (Kite-like field names).

    keys:  NSE:<SYMBOL>                   equity
           NFO:<SYMBOL><YY><MON>FUT       near future  (LTP every poll, OI on a rolling sweep)
           NFO:<SYMBOL><YY><MON><K>CE/PE  options      (served from get_option_chain)
    """

    def __init__(self, session: GrowwSession, oi_calls_per_poll: int = 60):
        self.s = session
        self.limiter = RateLimiter()
        self.oi_calls_per_poll = max(0, oi_calls_per_poll)
        self._oi: dict[str, dict] = {}      # futures tradingsymbol -> {"open_interest", "oi_day_change", "ts"}
        self._cursor = 0
        self._instruments = None

    # ---- instruments (for options -> underlying/expiry lookup)
    def instruments(self):
        if self._instruments is None:
            df = self.s.call("get_all_instruments")
            df = df[(df["exchange"] == "NSE") & (df["segment"] == "FNO")]
            self._instruments = df.set_index("trading_symbol")[["underlying_symbol", "expiry_date", "instrument_type"]].to_dict("index")
        return self._instruments

    # ---- Provider interface
    def quote(self, keys: list[str]) -> dict[str, dict]:
        g = self.s.client()
        eq = [k[4:] for k in keys if k.startswith("NSE:")]
        fut = [k[4:] for k in keys if k.startswith("NFO:") and k.endswith("FUT")]
        opt = [k[4:] for k in keys if k.startswith("NFO:") and k[-2:] in ("CE", "PE")]
        out: dict[str, dict] = {}

        for batch in _chunks(eq, 50):
            for sym, ltp in self._ltp(g.SEGMENT_CASH, batch).items():
                out["NSE:" + sym] = {"last_price": ltp}          # no prev close here: LiveFeed falls back to the EOD close

        for batch in _chunks(fut, 50):
            for ts, ltp in self._ltp(g.SEGMENT_FNO, batch).items():
                out["NFO:" + ts] = {"last_price": ltp}

        self._sweep_oi(g, fut)
        for ts in fut:
            cached = self._oi.get(ts)
            if cached:
                out.setdefault("NFO:" + ts, {}).update(cached)

        for (underlying, expiry), symbols in self._group_options(opt).items():
            self.limiter.wait()
            chain = self.s.call("get_option_chain", exchange=g.EXCHANGE_NSE, underlying=underlying, expiry_date=expiry)
            wanted = set(symbols)
            for _strike, sides in (chain.get("strikes") or {}).items():
                for side in ("CE", "PE"):
                    row = sides.get(side) or {}
                    ts = row.get("trading_symbol")
                    if ts in wanted:
                        out["NFO:" + ts] = {"last_price": row.get("ltp"), "open_interest": row.get("open_interest"),
                                            "volume": row.get("volume"), "iv": (row.get("greeks") or {}).get("iv")}
        return out

    # ---- helpers
    def _ltp(self, segment: str, symbols: list[str]) -> dict[str, float]:
        self.limiter.wait()
        r = self.s.call("get_ltp", segment=segment, exchange_trading_symbols=tuple("NSE_" + s for s in symbols)) or {}
        found = {}
        for s in symbols:
            v = r.get("NSE_" + s)
            if v is None and len(symbols) == 1 and "ltp" in r:
                v = r["ltp"]
            if v is not None:
                found[s] = float(v)
        return found

    def _sweep_oi(self, g, fut: list[str]) -> None:
        if not fut or not self.oi_calls_per_poll:
            return
        n = min(len(fut), self.oi_calls_per_poll)
        for i in range(n):
            ts = fut[(self._cursor + i) % len(fut)]
            self.limiter.wait()
            try:
                q = self.s.call("get_quote", trading_symbol=ts, exchange=g.EXCHANGE_NSE, segment=g.SEGMENT_FNO) or {}
            except Exception as exc:  # noqa: BLE001 - one bad contract must not stall the sweep
                log.warning("get_quote %s failed: %s", ts, exc)
                continue
            self._oi[ts] = {"open_interest": q.get("open_interest"), "oi_day_change": q.get("oi_day_change"),
                            "oi_day_change_pct": q.get("oi_day_change_percentage"),
                            "oi_ts": datetime.now(IST).strftime("%H:%M:%S")}
            if q.get("last_price") is not None:
                self._oi[ts]["last_price"] = q["last_price"]
        self._cursor = (self._cursor + n) % len(fut)

    def _group_options(self, opt: list[str]) -> dict[tuple[str, str], list[str]]:
        if not opt:
            return {}
        inst = self.instruments()
        groups: dict[tuple[str, str], list[str]] = {}
        for ts in opt:
            meta = inst.get(ts)
            if not meta:
                continue
            groups.setdefault((str(meta["underlying_symbol"]), str(meta["expiry_date"])[:10]), []).append(ts)
        return groups


# ---------------------------------------------------------------- orders
class GrowwBroker(Broker):
    """Groww Trading API. Contracts are resolved against Groww's instrument file so the exact
    tradingsymbol, lot size and exchange token come from the broker, never from a naming guess."""
    name = "groww"
    paper = False

    def __init__(self, session: GrowwSession):
        self.s = session
        self._instruments: dict[tuple, dict] | None = None

    def instruments(self) -> dict[tuple, dict]:
        if self._instruments is None:
            df = self.s.call("get_all_instruments")
            df = df[(df["exchange"] == "NSE") & (df["segment"] == "FNO")]
            m: dict[tuple, dict] = {}
            for r in df.to_dict("records"):
                typ = str(r["instrument_type"])
                strike = float(r["strike_price"]) if typ in ("CE", "PE") else None
                m[(str(r["underlying_symbol"]), typ, str(r["expiry_date"])[:10], strike)] = r
            self._instruments = m
        return self._instruments

    def resolve(self, req: OrderRequest, lot_size: int) -> dict:
        key = (req.symbol, req.instrument, req.expiry, req.strike if req.instrument != "FUT" else None)
        i = self.instruments().get(key)
        if not i:
            raise ValueError(f"no NSE F&O contract on Groww for {req.symbol} {req.instrument} {req.expiry} {req.strike or ''}")
        lot = int(i["lot_size"]) or lot_size
        return {"tradingsymbol": i["trading_symbol"], "quantity": req.lots * lot, "lot_size": lot,
                "exchange": "NSE", "segment": "FNO", "exchange_token": str(i["exchange_token"])}

    def margin(self, req: OrderRequest, resolved: dict, ref_price: float | None) -> float | None:
        g = self.s.client()
        try:
            r = self.s.call("get_order_margin_details", segment=g.SEGMENT_FNO, orders=[{
                "trading_symbol": resolved["tradingsymbol"], "transaction_type": req.side,
                "quantity": resolved["quantity"], "price": req.price or ref_price or 0,
                "order_type": req.order_type, "product": g.PRODUCT_NRML, "exchange": g.EXCHANGE_NSE}])
            return float(r["total_requirement"]) if r and r.get("total_requirement") is not None else None
        except Exception as exc:  # noqa: BLE001
            log.warning("margin check failed: %s", exc)
            return None

    def place(self, req: OrderRequest, resolved: dict, ref_price: float | None) -> dict:
        g = self.s.client()
        ref_id = f"FOS-{int(time.time())}"                      # 8–20 alphanumerics, ≤ 2 hyphens
        r = self.s.call("place_order", trading_symbol=resolved["tradingsymbol"], quantity=resolved["quantity"],
                        validity=g.VALIDITY_DAY, exchange=g.EXCHANGE_NSE, segment=g.SEGMENT_FNO,
                        product=g.PRODUCT_NRML, order_type=req.order_type, transaction_type=req.side,
                        price=req.price if req.order_type == "LIMIT" else 0.0, order_reference_id=ref_id)
        from dataclasses import asdict
        return {"order_id": r.get("groww_order_id"), "placed_at": datetime.now(IST).isoformat(timespec="seconds"),
                "status": r.get("order_status", "SENT"), "paper": False, "remark": r.get("remark"),
                "order_reference_id": ref_id, **asdict(req), **resolved}

    def orders(self) -> list[dict]:
        g = self.s.client()
        r = self.s.call("get_order_list", segment=g.SEGMENT_FNO, page=0, page_size=25) or {}
        return [{"order_id": o.get("groww_order_id"), "placed_at": o.get("created_at"), "status": o.get("order_status"),
                 "paper": False, "tradingsymbol": o.get("trading_symbol"), "side": o.get("transaction_type"),
                 "quantity": o.get("quantity"), "order_type": o.get("order_type"), "price": o.get("price"),
                 "fill_price": o.get("average_fill_price"), "status_message": o.get("remark")}
                for o in r.get("order_list", [])]

    def positions(self) -> list[dict]:
        g = self.s.client()
        r = self.s.call("get_positions_for_user", segment=g.SEGMENT_FNO) or {}
        return [{"tradingsymbol": p.get("trading_symbol"), "quantity": p.get("quantity"), "avg_price": p.get("net_price"),
                 "pnl": p.get("realised_pnl")} for p in r.get("positions", []) if p.get("quantity")]


_SHARED: GrowwSession | None = None


def shared_session(settings) -> GrowwSession:
    """One login for the whole server: the live feed and the broker reuse the same access token."""
    global _SHARED
    if _SHARED is None:
        _SHARED = GrowwSession(settings.groww_totp_token or None, settings.groww_totp_secret or None,
                               settings.groww_access_token or None)
    return _SHARED
