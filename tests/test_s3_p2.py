from datetime import date

import pandas as pd

from index_data import load as L
from scanner.s3_engine import simulate
from scanner.s3_p2 import PRIMARY, spec

DAY = date(2025, 3, 27)


def test_primary_spec_is_the_registered_trade():
    s = spec(*PRIMARY)
    assert [(lg.side, lg.opt, lg.offset) for lg in s.legs] == [("BUY", "CE", 0), ("BUY", "PE", 0)]
    assert s.entry == (14, 45) and s.exit == (15, 25) and s.stop is None and s.target is None


def test_long_straddle_time_exit_is_a_debit_with_1pct_exit_slippage():
    rows = [dict(timestamp=L.at(DAY, h, m), strike=23500.0, option_type=o, close=c, volume=5, oi=1, source="upstox")
            for o, path in (("CE", {(14, 45): 30, (15, 25): 70}), ("PE", {(14, 45): 30, (15, 25): 1}))
            for (h, m), c in path.items()]
    r = simulate(pd.DataFrame(rows), 23510.0, DAY, spec(*PRIMARY), lot=75)
    assert r["kind"] == "debit" and r["reason"] == "time" and r["exit_at"] == "15:25"
    # bought 30.15 + 30.15 (0.5 %); sold 69.30 + 0.99 (1 % after 15:00)
    assert abs(r["gross_rs"] - (69.3 + 0.99 - 60.3) * 75) < 0.01
