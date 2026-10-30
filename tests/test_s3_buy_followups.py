"""S3 buy follow-ups (strategies/S3_buy_followups_2026-10-30.md): R2 market switch, F3a spot outcomes, F4 max up."""
from datetime import date

import numpy as np
import pandas as pd

from index_data import load as L
from scanner import s3_buy4 as B
from scanner import s3_buy_maxup as M
from scanner import s3_g1_spot as F


def _bars(day: str, closes, highs=None, lows=None, start="09:15"):
    ts = pd.date_range(f"{day} {start}", periods=len(closes), freq="min", tz="Asia/Kolkata")
    c = np.asarray(closes, float)
    return pd.DataFrame({"timestamp": ts, "open": c, "high": np.asarray(highs if highs is not None else c, float),
                         "low": np.asarray(lows if lows is not None else c, float), "close": c})


def test_sensex_switch_rounds_to_100_and_restores_nifty():
    closes = [1000.0] * 45 + [1130.0] * 6                     # breakout at 10:00 to 1130
    spot = _bars("2025-03-03", closes, highs=[1001.0] * 45 + [1130.0] * 6, lows=[999.0] * 51)
    chain = pd.DataFrame({"timestamp": spot["timestamp"], "strike": 1100.0, "option_type": "CE", "close": 10.0,
                          "volume": 100})
    try:
        B.use(B.R2)
        assert (B.U["underlying"], B.U["index"], B.U["lot"], B.U["prefix"]) == ("SENSEX", "SENSEX", 20, "R2_")
        assert B.b1_signal(spot, chain, 15, None)[2] == 1100     # 1130 → nearest 100
    finally:
        B.use(B.NIFTY)
    assert B.U == B.NIFTY
    assert B.b1_signal(spot, chain, 15, None)[2] == 1150         # NIFTY step 50


def test_spot_outcome_signed_by_gap_direction():
    closes = [100.0] * 15 + [100.0] + [99.0] * 100 + [98.0] * 260   # 09:15 .. 15:30
    g = _bars("2023-03-03", closes, highs=[c + 0.2 for c in closes], lows=[c - 0.2 for c in closes])
    ent = pd.Timestamp(L.at(date(2023, 3, 3), 9, 30))
    dn = F.outcome(g, ent, -1)                                   # a down gap: the fall is follow-through
    assert dn["entry"] == 100.0 and round(dn["follow_pct"], 6) == 2.0
    assert round(dn["max_fav_pct"], 6) == round((1 - 97.8 / 100) * 100, 6)
    up = F.outcome(g, ent, 1)
    assert round(up["follow_pct"], 6) == -2.0 and up["max_adv_pct"] < 0
    assert abs(F.welch_t(pd.Series([1.0, 1.1, 0.9, 1.0]), pd.Series([0.0, 0.1, -0.1, 0.0])) - 17.32) < 0.01   # 1 / sqrt(2 * 0.02 / 3 / 4)


def test_max_up_held_vs_any_time_and_stale_minutes():
    day = date(2025, 3, 3)
    ts = pd.date_range("2025-03-03 09:30", periods=8, freq="min", tz="Asia/Kolkata")
    ce = pd.DataFrame({"timestamp": ts, "strike": 100.0, "option_type": "CE",
                       "close": [10.0, 11.0, 12.0, 11.0, 10.0, 9.0, 15.0, 9.0]})
    pe = pd.DataFrame({"timestamp": ts, "strike": 100.0, "option_type": "PE",
                       "close": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]})
    chain = pd.concat([ce, pe], ignore_index=True)
    legs = [("B", 100.0, "CE", 10.0, 9.0), ("B", 100.0, "PE", 10.0, 10.0)]
    m = M.max_up(chain, legs, L.at(day, 9, 30), L.at(day, 9, 35), L.at(day, 15, 29))
    assert m["max_up_held_pct"] == 10.0 and m["peak_held_at"].endswith("09:32")    # (12 + 10) / 20 - 1
    assert m["max_up_any_pct"] == 25.0 and m["peak_any_at"].endswith("09:36")      # (15 + 10) / 20 - 1
    gap = chain[~((chain["option_type"] == "PE") & (chain["timestamp"] > ts[0]))]  # the put stops trading
    far = pd.concat([gap, pd.DataFrame({"timestamp": [ts[0] + pd.Timedelta(minutes=45)], "strike": [100.0],
                                         "option_type": ["CE"], "close": [30.0]})], ignore_index=True)
    m2 = M.max_up(far, legs, L.at(day, 9, 30), L.at(day, 15, 0), L.at(day, 15, 29))
    assert m2["max_up_any_pct"] == 25.0          # 09:36 counts (put mark 6 min old); the 10:15 print (+100 %) does not
