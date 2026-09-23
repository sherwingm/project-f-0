"""Intraday quotes for the whole universe: underlying LTP/day change and nearest-expiry futures OI.

Provider = anything with quote(keys) -> {key: {...}}. KiteProvider wraps Kite Connect's /quote
(500 instruments per call, includes open_interest; rate limit 1 call/second), so the entire
universe (210 equities + 210 futures = 420 keys) is one request every POLL_SECONDS.
Live OI change is measured against the previous close's futures OI from the EOD scan, so the
page can show "OI +2.1% vs close" next to the EOD numbers.
"""
from __future__ import annotations

import logging
import random
import threading
import time
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
MARKET_OPEN, MARKET_CLOSE = (9, 15), (15, 30)


def market_open(now: datetime | None = None) -> bool:
    now = now or datetime.now(IST)
    if now.weekday() >= 5:
        return False
    hm = (now.hour, now.minute)
    return MARKET_OPEN <= hm <= MARKET_CLOSE


class KiteProvider:
    def __init__(self, api_key: str, access_token: str):
        from kiteconnect import KiteConnect
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)

    def quote(self, keys: list[str]) -> dict[str, dict]:
        out = {}
        for i in range(0, len(keys), 500):
            out.update(self.kite.quote(keys[i:i + 500]))
            if i + 500 < len(keys):
                time.sleep(1.1)  # quote endpoint: 1 request/second
        return out


class FakeProvider:
    """Random-walk quotes around the EOD closes, for local testing without a broker."""
    def __init__(self, closes: dict[str, float], fut_oi: dict[str, int]):
        self.closes, self.fut_oi, self.rng = closes, fut_oi, random.Random(1)

    def quote(self, keys: list[str]) -> dict[str, dict]:
        out = {}
        for k in keys:
            sym = k.split(":")[1]
            if k.startswith("NSE:"):
                c = self.closes.get(sym)
                if c:
                    out[k] = {"last_price": round(c * (1 + self.rng.uniform(-0.03, 0.03)), 2), "volume": self.rng.randint(10_000, 5_000_000),
                              "ohlc": {"open": c, "high": c * 1.02, "low": c * 0.98, "close": c}, "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")}
            else:
                base = next((s for s in sorted(self.closes, key=len, reverse=True) if k.startswith("NFO:" + s)), None)
                if base and k.endswith("FUT"):
                    oi = self.fut_oi.get(base) or 1_000_000
                    out[k] = {"last_price": round(self.closes[base] * 1.004, 2), "open_interest": int(oi * (1 + self.rng.uniform(-0.05, 0.08))), "volume": 0}
                    out["PCR:" + base] = {"pcr": round(self.rng.uniform(0.4, 1.6), 2), "call_oi": self.rng.randint(10_000, 900_000),
                                          "put_oi": self.rng.randint(10_000, 900_000), "pcr_ts": datetime.now(IST).strftime("%H:%M:%S")}
                elif base:
                    out[k] = {"last_price": round(self.rng.uniform(0.5, 60), 2), "open_interest": self.rng.randint(500, 90_000), "volume": self.rng.randint(0, 5000)}
        return out


class LiveFeed:
    def __init__(self, provider, scan: dict, poll_seconds: int = 30, fut_tradingsymbols: dict[str, str] | None = None,
                 poll_always: bool = False):
        self.provider, self.poll_seconds, self.poll_always = provider, poll_seconds, poll_always
        self.lock = threading.Lock()
        self.quotes: dict[str, dict] = {}
        self.updated_at: str | None = None
        self.error: str | None = None
        self._stop = threading.Event()
        self.reload(scan, fut_tradingsymbols or {})

    def reload(self, scan: dict, fut_tradingsymbols: dict[str, str]) -> None:
        self.eod = {s["symbol"]: s for s in scan["stocks"]}
        self.fut_keys = {sym: "NFO:" + ts for sym, ts in fut_tradingsymbols.items()}
        self.keys = ["NSE:" + s for s in self.eod] + list(self.fut_keys.values())

    def start(self) -> None:
        threading.Thread(target=self._loop, name="live-feed", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            if self.poll_always or market_open():
                try:
                    self.poll_once()
                except Exception as exc:  # noqa: BLE001 - keep polling; surface the error on the page
                    self.error = f"{type(exc).__name__}: {exc}"
                    log.warning("live poll failed: %s", exc)
            self._stop.wait(self.poll_seconds)

    def poll_once(self) -> None:
        raw = self.provider.quote(self.keys)
        now = datetime.now(IST)
        fresh: dict[str, dict] = {}
        for sym, e in self.eod.items():
            q = raw.get("NSE:" + sym)
            if not q:
                continue
            prev = (q.get("ohlc") or {}).get("close") or e["close"]
            ltp = q.get("last_price")
            row = {"ltp": ltp, "chg_pct": round((ltp / prev - 1) * 100, 2) if ltp and prev else None,
                   "volume": q.get("volume"), "prev_close": prev, "ts": q.get("timestamp") or now.strftime("%Y-%m-%d %H:%M:%S")}
            f = raw.get(self.fut_keys.get(sym, ""))
            if f:
                oi, oi_eod = f.get("open_interest"), e.get("fut_oi")
                row.update({"fut_ltp": f.get("last_price"), "fut_oi": oi,
                            "fut_oi_chg_pct": round((oi / oi_eod - 1) * 100, 2) if oi and oi_eod else None,
                            "oi_ts": f.get("oi_ts")})
            p = raw.get("PCR:" + sym)          # providers that sweep option chains add exact live PCR
            if p:
                row.update({"live_pcr": p.get("pcr"), "live_call_oi": p.get("call_oi"), "live_put_oi": p.get("put_oi"), "pcr_ts": p.get("pcr_ts")})
            fresh[sym] = row
        with self.lock:
            self.quotes, self.updated_at, self.error = fresh, now.strftime("%H:%M:%S"), None

    def snapshot(self) -> dict:
        with self.lock:
            return {"updated_at": self.updated_at, "market_open": market_open(), "error": self.error,
                    "poll_seconds": self.poll_seconds, "quotes": dict(self.quotes)}
