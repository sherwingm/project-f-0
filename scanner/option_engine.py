"""The option backtest engine for every S1 version from v3 on: entry fills, the expiry rule, the test / holdout split.

Entry fill (one leg, on the entry day):
- the contract must have traded >= 50 contracts that day, otherwise no fill;
- base price = the day's premium VWAP = turnover / (contracts x lot) - strike (NSE reports option turnover as
  notional, (strike + premium) x quantity, in both the old and the UDiFF bhavcopy); if that is unavailable (no
  turnover or lot, or outside the day's low-high range) the day's close;
- plus one tick (Rs 0.05) for a buy, minus one tick for a sell.

Expiry: the current monthly expiry if >= 10 sessions remain after the signal day (expiry day included), else the
next monthly. Monthly = the last listed expiry of each calendar month.

Day data: `scanner.nse_fo.download_fo_prices` (cached as data/cache/fo_prices_YYYYMMDD.csv).
"""
from __future__ import annotations

import math
from datetime import date

from .backtest_cheap_options import sessions_to

TICK = 0.05
MIN_ENTRY_CONTRACTS = 50
MIN_SESSIONS_CURRENT = 10
TEST_WINDOW = ("2021-01-01", "2024-12-31")             # DECISIONS.md: every S1 version is tested here
HOLDOUT_START = "2025-01-01"                            # evaluated once, only for a version that passed the gate
TEST_PERIODS = (("2021-22", "2021-01-01", "2022-12-31"), ("2023-24", "2023-01-01", "2024-12-31"))


def window(holdout: bool = False, last_session: str = "9999-12-31") -> tuple[str, str]:
    """The test window, or (holdout=True) the holdout to the last session."""
    return (HOLDOUT_START, last_session) if holdout else TEST_WINDOW


def split_of(day: str) -> str:
    return "holdout" if day >= HOLDOUT_START else "test"


def split_statement(evaluated: tuple[str, str], holdout_used: bool = False) -> str:
    """The line every report carries."""
    s = (f"Test window {TEST_WINDOW[0]} to {TEST_WINDOW[1]}; holdout {HOLDOUT_START} onward. "
         f"This report covers {evaluated[0]} to {evaluated[1]}; ")
    return s + ("the holdout is included (evaluated once, after the gate passed)." if holdout_used
                else "the holdout is untouched.")


def premium_vwap(turnover: float, contracts: float, lot: float, strike: float,
                 low: float | None = None, high: float | None = None) -> float | None:
    """The day's premium VWAP per share from notional turnover; None if it cannot be computed or falls outside
    the day's low-high range (by more than a tick)."""
    vals = (turnover, contracts, lot, strike)
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in vals) or contracts <= 0 or lot <= 0 \
            or turnover <= 0:
        return None
    v = turnover / (contracts * lot) - strike
    if v <= 0:
        return None
    if low is not None and high is not None and not (math.isnan(low) or math.isnan(high)) and high > 0:
        if not low - TICK <= v <= high + TICK:
            return None
    return v


def entry_fill(contracts: float, turnover: float, lot: float, strike: float, close: float,
               low: float | None = None, high: float | None = None, side: str = "BUY") -> tuple[float, str] | None:
    """(fill price, 'vwap' or 'close') for one leg on the entry day, or None when it traded < 50 contracts."""
    if contracts is None or (isinstance(contracts, float) and math.isnan(contracts)) or contracts < MIN_ENTRY_CONTRACTS:
        return None
    v = premium_vwap(turnover, contracts, lot, strike, low, high)
    base, source = (v, "vwap") if v is not None else (close, "close")
    if base is None or (isinstance(base, float) and math.isnan(base)) or base <= 0:
        return None
    px = base + TICK if side.upper() == "BUY" else max(base - TICK, 0.0)
    return round(px, 2), source


def monthly(expiries) -> list[str]:
    """The last listed expiry of each calendar month, sorted (ISO dates)."""
    last: dict[str, str] = {}
    for e in sorted({str(e)[:10] for e in expiries}):
        last[e[:7]] = e
    return sorted(last.values())


def choose_expiry(expiries, cal_dates: list[date], d: date) -> str | None:
    """Current monthly expiry if >= 10 sessions remain after signal day d, else the next monthly."""
    ahead = [e for e in monthly(expiries) if e > d.isoformat()]
    if not ahead:
        return None
    if sessions_to(cal_dates, d, date.fromisoformat(ahead[0])) >= MIN_SESSIONS_CURRENT:
        return ahead[0]
    return ahead[1] if len(ahead) > 1 else None
