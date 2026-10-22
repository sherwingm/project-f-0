"""Intraday quotes for the whole universe: underlying LTP/day change and nearest-expiry futures OI.

Provider = anything with quote(keys) -> {key: {...}}. KiteProvider wraps Kite Connect's /quote
(500 instruments per call, includes open_interest; rate limit 1 call/second), so the entire
universe (210 equities + 210 futures = 420 keys) is one request every POLL_SECONDS.
Live OI change is measured against the previous close's futures OI from the EOD scan, so the
page can show "OI +2.1% vs close" next to the EOD numbers.

Live label: every poll applies the EOD label rule (scanner.classify) to live inputs: the live price change,
today's volume so far against the 20-day average scaled to the time of day (pro rata over the 375-minute
session, the first 15 minutes floored), the live all-expiry futures OI change, and the live PCR (the EOD PCR
until the chain sweep reaches the stock). Descriptive, like the EOD label; the model never sees live data.
Opening snapshot: the first poll between 09:30 and 10:30 IST on a session day writes every stock's live label
to <snapshot_dir>/<date>.json (GET /api/live/snapshot), which a GitHub workflow commits for scoring.
Intraday history: every poll appends one tick per stock (and per watched option) to an in-memory buffer, cleared
at the day's first poll; server/candles.py turns it into chart candles. Kotak has no candle API, so the chart
covers only the time this server has been polling (a sleeping or restarted server leaves a gap).
"""
from __future__ import annotations

import logging
import math
import random
import threading
import time
import json
import zlib
from collections import deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scanner.classify import classify

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
MARKET_OPEN, MARKET_CLOSE = (9, 15), (15, 30)
SESSION_MINUTES = 375                 # 09:15 -> 15:30
MIN_ELAPSED_MINUTES = 15              # pro-rata volume floor, so 09:16 does not give absurd ratios
SNAPSHOT_FROM, SNAPSHOT_UNTIL = (9, 30), (10, 30)
HISTORY_TICKS = 2400                  # per instrument; one tick at most every HISTORY_EVERY s fills ~2,250 a session
HISTORY_EVERY = 10                    # seconds between chart ticks (the feed itself runs every second when streaming)
WATCH_MINUTES, WATCH_MAX = 30, 3      # options of an opened stock are polled for 30 min, at most 3 stocks at once
# fields of a quote passed through to /api/live (equity as is, the near future with a fut_ prefix)
QUOTE_FIELDS = ("atp", "ltq", "buy_qty", "sell_qty", "wk52_high", "wk52_low", "lower_circuit", "upper_circuit")


def live_label(row: dict, eod: dict, now: datetime) -> dict:
    """The EOD label rule on live inputs (see the module docstring)."""
    elapsed = (now.hour * 60 + now.minute) - (MARKET_OPEN[0] * 60 + MARKET_OPEN[1])
    frac = min(1.0, max(MIN_ELAPSED_MINUTES, elapsed) / SESSION_MINUTES)
    vol, avg = row.get("volume"), eod.get("avg_volume_20d")
    vr = round(vol / (avg * frac), 2) if vol and avg else None
    pcr = row.get("live_pcr") if row.get("live_pcr") is not None else eod.get("pcr")
    c = classify({"price_change_pct": row.get("chg_pct"), "volume_ratio": vr,
                  "oi_change_pct": row.get("fut_oi_chg_pct"), "pcr": pcr})
    return {"live_label": c["label"], "live_reasons": c["reasons"], "live_volume_ratio": vr,
            "live_label_pcr": "live" if row.get("live_pcr") is not None else "eod"}


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
    """Random-walk quotes around the EOD closes, with synthetic 5-level depth, for local testing
    without a broker. Option premiums are stable per contract (seeded from the trading symbol)
    and wobble a few percent per call, so paper positions mark to something plausible."""
    TICK = 0.01                          # NSE stock-option tick since 2025-11-03

    def __init__(self, closes: dict[str, float], fut_oi: dict[str, int], lot_sizes: dict[str, int] | None = None):
        self.closes, self.fut_oi, self.rng = closes, fut_oi, random.Random(1)
        self.lot_sizes = {k: v for k, v in (lot_sizes or {}).items() if v}

    def quote(self, keys: list[str]) -> dict[str, dict]:
        out = {}
        for k in keys:
            sym = k.split(":")[1]
            if k.startswith("NSE:"):
                c = self.closes.get(sym)
                if c:
                    ltp = round(c * (1 + self.rng.uniform(-0.03, 0.03)), 2)
                    out[k] = {"last_price": ltp, "volume": self.rng.randint(10_000, 5_000_000),
                              "ohlc": {"open": c, "high": round(max(c, ltp) * 1.01, 2), "low": round(min(c, ltp) * 0.99, 2),
                                       "close": c},
                              "atp": round((c + ltp) / 2, 2), "ltq": self.rng.randint(1, 500),
                              "buy_qty": self.rng.randint(1_000, 90_000), "sell_qty": self.rng.randint(1_000, 90_000),
                              "wk52_high": round(c * 1.3, 2), "wk52_low": round(c * 0.7, 2), "timestamp": _now(),
                              "depth": self._depth(ltp, 0.0002, 50, 5_000)}
            else:
                base = self._base(sym)
                if base and k.endswith("FUT"):
                    out[k] = self._future(base)
                    out["PCR:" + base] = {"pcr": round(self.rng.uniform(0.4, 1.6), 2), "call_oi": self.rng.randint(10_000, 900_000),
                                          "put_oi": self.rng.randint(10_000, 900_000), "pcr_ts": datetime.now(IST).strftime("%H:%M:%S")}
                elif base:
                    out[k] = self._option(sym, base)
        return out

    def history(self, key: str, tf: int, day: str) -> list[dict]:
        """Synthetic candles for a weekday (KotakProvider.history's shape): a gentle walk from the close."""
        d = date.fromisoformat(day)
        sym = key.split(":", 1)[1]
        base = self.closes.get(sym) or (self._option(sym, self._base(sym))["last_price"] if self._base(sym) else None)
        if not base or d.weekday() >= 5 or d > datetime.now(IST).date():
            return []
        rng, out, px = random.Random(f"{key}{tf}{day}"), [], base
        t = int(datetime(d.year, d.month, d.day, 9, 15, tzinfo=IST).timestamp())
        end = int(datetime(d.year, d.month, d.day, 15, 30, tzinfo=IST).timestamp())
        while t < end:
            o, px = px, round(px * (1 + rng.uniform(-0.003, 0.003)), 2)
            out.append({"time": t, "open": o, "high": max(o, px), "low": min(o, px), "close": px,
                        "volume": float(rng.randint(1_000, 90_000)), "atp": None})
            t += tf * 60
        return out

    def quote_one(self, tradingsymbol: str) -> dict:
        ts = tradingsymbol.split(":", 1)[1] if ":" in tradingsymbol else tradingsymbol
        base = self._base(ts)
        if not base:
            raise ValueError(f"{ts}: unknown underlying")
        q = self._future(base) if ts.endswith("FUT") else self._option(ts, base)
        return {**q, "tradingsymbol": ts, "lot_size": self.lot_sizes.get(base)}

    def _base(self, ts: str) -> str | None:
        return next((s for s in sorted(self.closes, key=len, reverse=True) if ts.startswith(s)), None)

    def _future(self, base: str) -> dict:
        oi, lot = self.fut_oi.get(base) or 1_000_000, self.lot_sizes.get(base, 1)
        ltp = round(self.closes[base] * 1.004 * (1 + self.rng.uniform(-0.01, 0.01)), 2)
        return {"last_price": ltp, "open_interest": int(oi * (1 + self.rng.uniform(-0.05, 0.08))),
                "volume": self.rng.randint(1_000, 900_000), "atp": round(self.closes[base] * 1.004, 2),
                "ohlc": {"close": round(self.closes[base] * 1.002, 2)},
                "timestamp": _now(), "depth": self._depth(ltp, 0.0003, lot, lot * 20)}

    def _option(self, ts: str, base: str) -> dict:
        lot = self.lot_sizes.get(base, 1)
        stable = 0.5 + (zlib.crc32(ts.encode()) % 6000) / 100            # 0.50 to 60.49, same every run
        ltp = max(self.TICK, round(stable * (1 + self.rng.uniform(-0.04, 0.04)) / self.TICK) * self.TICK)
        return {"last_price": round(ltp, 2), "open_interest": self.rng.randint(20, 400) * lot, "volume": self.rng.randint(0, 5000),
                "atp": round(stable, 2), "ohlc": {"close": round(stable * 1.02, 2)},
                "timestamp": _now(), "depth": self._depth(ltp, 0.01, lot, lot * 10)}

    def _depth(self, ltp: float, half_spread: float, min_qty: int, max_qty: int) -> dict:
        t, step = self.TICK, max(1, min_qty)
        bid = max(t, math.floor(ltp * (1 - half_spread) / t + 1e-9) * t)
        ask = max(bid + t, math.ceil(ltp * (1 + half_spread) / t - 1e-9) * t)

        def qty() -> int:
            return step * self.rng.randint(1, max(1, max_qty // step))

        return {"bid": [(round(bid - i * t, 2), qty()) for i in range(5) if bid - i * t > 0],
                "ask": [(round(ask + i * t, 2), qty()) for i in range(5)]}


def _now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


class LiveFeed:
    def __init__(self, provider, scan: dict, poll_seconds: int = 30, fut_tradingsymbols: dict[str, str] | None = None,
                 fast_seconds: float | None = None,
                 poll_always: bool = False):
        self.provider, self.poll_seconds, self.poll_always = provider, poll_seconds, poll_always
        self.fast_seconds = fast_seconds
        self._last_tick = 0.0
        self.lock = threading.Lock()
        self.quotes: dict[str, dict] = {}
        self.updated_at: str | None = None
        self.error: str | None = None
        self.hooks: list = []              # called with the feed after every successful poll (paper ledger marks)
        self.snapshot_dir: Path | None = None   # set by the app: the 09:30 opening snapshot is written there
        # intraday ticks: symbol -> deque[(epoch, ltp, volume, atp, fut_ltp, fut_oi, fut_volume, fut_atp)] and
        # option key -> deque[(epoch, ltp, volume, atp, oi)]; both cleared at the first poll of a new day
        self.history: dict[str, deque] = {}
        self.opt_history: dict[str, deque] = {}
        self.opt_quotes: dict[str, dict] = {}   # latest quote of each watched option key
        self.watch: dict[str, tuple[float, list[str]]] = {}   # symbol -> (expires epoch, option keys)
        self._day: str | None = None
        self._stop = threading.Event()
        self.reload(scan, fut_tradingsymbols or {})

    def reload(self, scan: dict, fut_tradingsymbols: dict[str, str | list[str]]) -> None:
        """fut_tradingsymbols: {symbol: near future} or {symbol: [near, next, far]}. With the full list, fut_oi is
        the OI summed over every expiry, like the EOD scan's fut_oi, and fut_oi_chg_pct compares the two; with the
        near contract alone, fut_oi_chg_pct is left out (near-month OI against an all-expiry total is not a
        change: it reads -60 % or worse as the month's contract rolls off)."""
        self.eod = {s["symbol"]: s for s in scan["stocks"]}
        self.fut_all = {sym: ["NFO:" + t for t in ([ts] if isinstance(ts, str) else ts)]
                        for sym, ts in fut_tradingsymbols.items() if ts}
        self.fut_keys = {sym: keys[0] for sym, keys in self.fut_all.items()}
        self.keys = ["NSE:" + s for s in self.eod] + [k for keys in self.fut_all.values() for k in keys]

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
            done = time.monotonic()
            while not self._stop.wait(min(1.0, self.interval())):    # re-checked each second: the stream may resume
                if time.monotonic() - done >= self.interval() - 0.05:
                    break

    def interval(self) -> float:
        """fast_seconds while the provider streams (server/upstox_stream.py), else poll_seconds."""
        streaming = getattr(self.provider, "streaming", None)
        if self.fast_seconds and streaming is not None and streaming():
            return self.fast_seconds
        return self.poll_seconds

    def watch_options(self, symbol: str, keys: list[str], now: float | None = None) -> None:
        """Poll these option keys (NFO:<tradingsymbol>) with every poll for WATCH_MINUTES, so their intraday chart
        fills; at most WATCH_MAX stocks at once (the oldest is dropped)."""
        now = now or time.time()
        with self.lock:
            self.watch = {s: w for s, w in self.watch.items() if w[0] > now and s != symbol}
            while len(self.watch) >= WATCH_MAX:
                del self.watch[min(self.watch, key=lambda s: self.watch[s][0])]
            self.watch[symbol] = (now + WATCH_MINUTES * 60, list(keys))

    def watched_keys(self, now: float | None = None) -> list[str]:
        now = now or time.time()
        with self.lock:
            return sorted({k for exp, keys in self.watch.values() if exp > now for k in keys})

    def poll_once(self, now: datetime | None = None) -> None:
        opt_keys = self.watched_keys()
        raw = self.provider.quote(self.keys + opt_keys)
        now = now or datetime.now(IST)
        fresh: dict[str, dict] = {}
        for sym, e in self.eod.items():
            q = raw.get("NSE:" + sym)
            if not q:
                continue
            ohlc = q.get("ohlc") or {}
            prev = ohlc.get("close") or e["close"]
            ltp = q.get("last_price")
            row = {"ltp": ltp, "chg": round(ltp - prev, 2) if ltp and prev else None,
                   "chg_pct": round((ltp / prev - 1) * 100, 2) if ltp and prev else None,
                   "volume": q.get("volume"), "prev_close": prev, "ts": q.get("timestamp") or now.strftime("%Y-%m-%d %H:%M:%S"),
                   "open": ohlc.get("open"), "high": ohlc.get("high"), "low": ohlc.get("low"),
                   "depth": q.get("depth"), **{k: q.get(k) for k in QUOTE_FIELDS}}
            f = raw.get(self.fut_keys.get(sym, ""))
            if f:
                keys = self.fut_all.get(sym, [])
                ois = [(raw.get(k) or {}).get("open_interest") for k in keys]
                whole = len(keys) > 1 and all(v is not None for v in ois)
                oi, oi_eod = (sum(ois) if whole else None), e.get("fut_oi")
                fprev = (f.get("ohlc") or {}).get("close")
                row.update({"fut_ltp": f.get("last_price"), "fut_oi": oi if whole else f.get("open_interest"),
                            "fut_oi_near": f.get("open_interest"), "fut_oi_all_expiries": whole,
                            "fut_oi_chg_pct": round((oi / oi_eod - 1) * 100, 2) if whole and oi and oi_eod else None,
                            "oi_ts": f.get("oi_ts") or f.get("timestamp"), "fut_depth": f.get("depth"),
                            "fut_volume": f.get("volume"), "fut_atp": f.get("atp"), "fut_prev_close": fprev,
                            "fut_chg_pct": round((f["last_price"] / fprev - 1) * 100, 2) if f.get("last_price") and fprev else None,
                            "fut_tradingsymbol": self.fut_keys[sym].split(":", 1)[1]})
            p = raw.get("PCR:" + sym)          # providers that sweep option chains add exact live PCR
            if p:
                row.update({"live_pcr": p.get("pcr"), "live_call_oi": p.get("call_oi"), "live_put_oi": p.get("put_oi"), "pcr_ts": p.get("pcr_ts")})
            row.update(live_label(row, e, now))
            fresh[sym] = row
        opts = {k: raw[k] for k in opt_keys if raw.get(k)}
        with self.lock:
            self.quotes, self.updated_at, self.error = fresh, now.strftime("%H:%M:%S"), None
            self._record(fresh, opts, now)
        try:
            self._maybe_snapshot(fresh, now)
        except OSError as exc:
            log.warning("opening snapshot not written: %s", exc)
        for hook in list(self.hooks):
            try:
                hook(self)
            except Exception as exc:  # noqa: BLE001 - a hook must never stop the feed
                log.warning("live poll hook %s failed: %s", getattr(hook, "__name__", hook), exc)

    def _maybe_snapshot(self, fresh: dict, now: datetime) -> Path | None:
        """The first poll between SNAPSHOT_FROM and SNAPSHOT_UNTIL on a weekday writes <date>.json once."""
        if self.snapshot_dir is None or now.weekday() >= 5 or not fresh:
            return None
        if not (SNAPSHOT_FROM <= (now.hour, now.minute) <= SNAPSHOT_UNTIL):
            return None
        path = Path(self.snapshot_dir) / f"{now.date().isoformat()}.json"
        if path.exists():
            return None
        rows = [{"symbol": sym, "label": r.get("live_label"), "ltp": r.get("ltp"), "chg_pct": r.get("chg_pct"),
                 "volume_ratio": r.get("live_volume_ratio"), "oi_chg_pct": r.get("fut_oi_chg_pct"),
                 "pcr": r.get("live_pcr"), "pcr_source": r.get("live_label_pcr")} for sym, r in sorted(fresh.items())]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"date": now.date().isoformat(), "taken_at": now.strftime("%H:%M:%S"),
                                    "rule": "scanner.classify on live inputs; volume pro rata to the time of day",
                                    "rows": rows}), encoding="utf-8")
        log.info("opening snapshot %s written (%d stocks, %s)", path.name, len(rows), now.strftime("%H:%M:%S"))
        return path

    def _record(self, fresh: dict, opts: dict, now: datetime) -> None:
        """Append this poll to the intraday buffers (caller holds the lock); a new day starts them empty."""
        day = now.date().isoformat()
        if day != self._day:
            self._day, self.history, self.opt_history, self._last_tick = day, {}, {}, 0.0
        self.opt_quotes.update(opts)
        t = int(now.timestamp())
        if t - self._last_tick < HISTORY_EVERY:
            return
        self._last_tick = t
        for sym, r in fresh.items():
            if r.get("ltp"):
                self.history.setdefault(sym, deque(maxlen=HISTORY_TICKS)).append(
                    (t, r["ltp"], r.get("volume"), r.get("atp"), r.get("fut_ltp"), r.get("fut_oi_near"),
                     r.get("fut_volume"), r.get("fut_atp")))
        for k, q in opts.items():
            if q.get("last_price"):
                self.opt_history.setdefault(k, deque(maxlen=HISTORY_TICKS)).append(
                    (t, q["last_price"], q.get("volume"), q.get("atp"), q.get("open_interest")))

    def ticks(self, symbol: str) -> list[tuple]:
        with self.lock:
            return list(self.history.get(symbol, ()))

    def option_ticks(self, key: str) -> list[tuple]:
        with self.lock:
            return list(self.opt_history.get(key, ()))

    def snapshot(self) -> dict:
        with self.lock:
            return {"updated_at": self.updated_at, "market_open": market_open(), "error": self.error,
                    "poll_seconds": self.poll_seconds, "quotes": dict(self.quotes)}
