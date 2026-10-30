"""Signal rules of the S3 buy pods (scanner/s3_buy4.py) on small synthetic frames."""
from datetime import date

import numpy as np
import pandas as pd

from scanner import s3_buy4 as B


def _spot(day: str, closes, opens=None, highs=None, lows=None):
    ts = pd.date_range(f"{day} 09:15", periods=len(closes), freq="min", tz="Asia/Kolkata")
    c = np.asarray(closes, float)
    o = np.asarray(opens if opens is not None else c, float)
    return pd.DataFrame({"timestamp": ts, "open": o, "high": np.asarray(highs if highs is not None else c, float),
                         "low": np.asarray(lows if lows is not None else c, float), "close": c})


def test_fomc_maps_to_next_session_and_missing_events_listed():
    ses = [date(2025, 1, 29), date(2025, 1, 30), date(2025, 1, 31), date(2025, 2, 3)]
    old = B.RBI, B.BUDGET, B.FOMC_US, B.US_ELECTION
    try:
        B.RBI, B.BUDGET, B.FOMC_US, B.US_ELECTION = [date(2025, 1, 31)], [date(2025, 2, 1)], [date(2025, 1, 29)], []
        evs, missing = B.events(ses)
    finally:
        B.RBI, B.BUDGET, B.FOMC_US, B.US_ELECTION = old
    assert (date(2025, 1, 30), "FOMC") in evs and (date(2025, 1, 31), "RBI") in evs
    assert missing == [(date(2025, 2, 1), "Budget")]


def test_gap_needs_size_and_confirmation():
    up = _spot("2025-03-03", [101.0] * 20, opens=[100.6] + [101.0] * 19)        # +0.6 % gap, closes above the open
    sg = B.g1_signal(up, 100.0, 0.5, 15)
    assert sg[0] == "CE" and sg[1].strftime("%H:%M") == "09:30"
    fade = _spot("2025-03-03", [100.4] * 20, opens=[100.6] + [100.4] * 19)      # gap up, then below the open: no trade
    assert B.g1_signal(fade, 100.0, 0.5, 15) is None
    assert B.g1_signal(fade, 100.0, 0.5, None)[0] == "CE"                       # the baseline ignores the confirmation
    assert B.g1_signal(up, 100.0, 0.7, 15) is None                              # gap too small


def test_breakout_needs_option_volume():
    closes = [100.0] * 45 + [130.0] + [130.0] * 5                               # breakout at 10:00 (minute 45)
    spot = _spot("2025-03-03", closes, highs=[101.0] * 45 + [130.0] * 6, lows=[99.0] * 51)
    ts = spot["timestamp"]
    chain = pd.DataFrame({"timestamp": ts, "strike": 150.0, "option_type": "CE", "close": 10.0,
                          "volume": [100] * 45 + [150] + [100] * 5})
    spot["close"] = spot["close"] + 20                                         # spot near strike 150 at the breakout
    spot.loc[:44, "close"] = 120.0
    spot["high"] = [121.0] * 45 + [150.0] * 6
    spot["low"] = [119.0] * 51
    assert B.b1_signal(spot, chain, 15, 2.0) is None                           # 150 < 2 x median 100
    chain.loc[45, "volume"] = 250
    side, t, k = B.b1_signal(spot, chain, 15, 2.0)
    assert side == "CE" and t.strftime("%H:%M") == "10:00" and k == 150
    assert B.b1_signal(spot, chain.assign(volume=0), 15, None)[0] == "CE"      # baseline: no volume test


def test_quiet_rule_does_not_see_the_day_itself():
    idx = [date(2024, 1, 1) + pd.Timedelta(days=i) for i in range(260)]
    idx = [d.date() if hasattr(d, "date") else d for d in idx]
    rng = np.r_[1.0 + (np.arange(254) % 10) * 0.2, np.full(6, 0.5)]
    d = pd.DataFrame({"high": 100 + rng / 2, "low": 100 - rng / 2, "close": 100.0}, index=idx)
    q = B.quiet_days(d, 5, 20)
    assert bool(q.iloc[-1])
    d2 = d.copy()
    d2.iloc[-1, d2.columns.get_loc("high")] = 150.0                           # the day's own bar: no effect
    assert bool(B.quiet_days(d2, 5, 20).iloc[-1])
    d3 = d.copy()
    d3.iloc[-2, d3.columns.get_loc("high")] = 150.0                           # the day before: it counts
    assert not bool(B.quiet_days(d3, 5, 20).iloc[-1])
