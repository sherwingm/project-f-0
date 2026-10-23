"""S3 regime inputs known before an entry: NIFTY daily bars from the 1-minute spot, Wilder's ADX(14), EMA(20), the
trading-day calendar, and Black-Scholes delta for strike choice.

Every value for a day D is computed from bars up to D-1's close (`prev_*`), so a filter at D's entry minute never
sees D's own close.
"""
from __future__ import annotations

import math
from datetime import date
from functools import lru_cache

import numpy as np
import pandas as pd

from index_data import load as L
from scanner.fade_preopen_entry import R, _n, iv

MIN_BARS = 60                                    # a real session has ~375 one-minute bars


@lru_cache(maxsize=2)
def daily(index: str = "NIFTY50") -> pd.DataFrame:
    s = L.spot_1m(date(2021, 10, 1), date(2026, 12, 31), index)
    s["d"] = s["timestamp"].dt.date
    n = s.groupby("d")["close"].transform("size")
    s = s[n >= MIN_BARS]                         # drops stray rows such as a one-bar Saturday (2025-08-23)
    d = s.groupby("d").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
    d["ema20"] = d["close"].ewm(span=20, adjust=False).mean()
    d["adx14"] = adx(d, 14)
    return d


def adx(d: pd.DataFrame, n: int = 14) -> pd.Series:
    """Wilder's ADX: +DM / −DM and true range smoothed with alpha 1/n."""
    h, lo, c = d["high"], d["low"], d["close"]
    up, dn = h.diff(), -lo.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([h - lo, (h - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
    a = 1 / n
    atr = tr.ewm(alpha=a, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, index=d.index).ewm(alpha=a, adjust=False).mean() / atr
    ndi = 100 * pd.Series(ndm, index=d.index).ewm(alpha=a, adjust=False).mean() / atr
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi)
    return dx.ewm(alpha=a, adjust=False).mean()


def trading_days(index: str = "NIFTY50") -> list[date]:
    return list(daily(index).index)


def prev_value(day: date, col: str, index: str = "NIFTY50") -> float | None:
    d = daily(index)
    before = d[d.index < day]
    return float(before[col].iloc[-1]) if len(before) else None


def days_before(expiry: date, k: int, index: str = "NIFTY50") -> date | None:
    """The trading day k sessions before `expiry` (k = 1: the session before the expiry day)."""
    td = [x for x in trading_days(index) if x < expiry]
    return td[-k] if len(td) >= k else None


def years_to(at: pd.Timestamp, expiry: date) -> float:
    end = pd.Timestamp(expiry.isoformat() + " 15:30", tz=at.tz)
    return max((end - at).total_seconds(), 60.0) / (365 * 24 * 3600)


def delta(side: str, s: float, k: float, t: float, v: float) -> float:
    d1 = (math.log(s / k) + (R + v * v / 2) * t) / (v * math.sqrt(t))
    return _n(d1) if side == "CE" else _n(d1) - 1


def strike_by_delta(chain: pd.DataFrame, side: str, s: float, at: pd.Timestamp, expiry: date, target: float,
                    lo: float = 0.10, hi: float = 0.25, step: int = 50) -> tuple[float, float] | None:
    """The out-of-the-money strike whose |delta| (from its own implied vol at `at`) is closest to `target`, if within
    [lo, hi]. Returns (strike, |delta|) or None."""
    t = years_to(at, expiry)
    ks = sorted(chain.loc[chain["option_type"] == side, "strike"].unique())
    ks = [k for k in ks if (k > s if side == "CE" else k < s)]
    best = None
    for k in ks:
        px = L.price_at(chain, k, side, at, stale=3)
        if px is None or px <= 0:
            continue
        v = iv(side, px, s, k, t)
        if not v:
            continue
        dl = abs(delta(side, s, k, t, v))
        if lo <= dl <= hi and (best is None or abs(dl - target) < abs(best[1] - target)):
            best = (float(k), dl)
    return best
