"""S3 V1 cheap-options straddle (scanner/s3_v1.py): realized vol and ATM implied vol."""
import math
from datetime import date

import pandas as pd

from scanner import s3_v1 as V
from scanner.fade_preopen_entry import bs


def test_rv_uses_only_the_sessions_before(monkeypatch):
    days = [date(2025, 1, d) for d in range(1, 8)]
    var = pd.Series([0.0001] * 6 + [1.0], index=days)                  # the entry day's own huge variance
    V.day_var.cache_clear()
    monkeypatch.setattr(V, "day_var", lambda: var)
    assert abs(V.rv(days[-1], 5) - math.sqrt(252 * 0.0001)) < 1e-12
    assert V.rv(days[3], 5) is None                                     # only 3 sessions before


def test_atm_iv_recovers_the_vol_in_the_prices(monkeypatch):
    at = pd.Timestamp("2025-01-06 14:45")
    ex = date(2025, 1, 9)
    t = V.years_to(at, ex)
    px = {o: bs(o, 23510, 23500, t, 0.14) for o in ("CE", "PE")}
    monkeypatch.setattr(V.L, "price_at", lambda chain, k, opt, a, stale=3: px[opt] if k == 23500 else None)
    assert abs(V.atm_iv(pd.DataFrame(), 23510, at, ex) - 0.14) < 1e-4


def test_move_ratio_is_one_when_the_price_implies_the_recent_pace(monkeypatch):
    days = [date(2025, 1, d) for d in range(1, 7)]
    var = pd.Series([0.0001] * 6, index=days)                          # 1 % a session
    monkeypatch.setattr(V, "day_var", lambda: var)
    at = V.L.at(date(2025, 1, 7), 15, 30)                               # nothing left today; 2 sessions to expiry
    ex = date(2025, 1, 9)
    v = math.sqrt(0.0001 * 2 / V.years_to(at, ex))
    assert abs(V.move_ratio(v, at, ex, 2, 5) - 1) < 1e-9
