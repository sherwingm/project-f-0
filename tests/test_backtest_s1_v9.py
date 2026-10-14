"""S1 v9 option backtest: the open-price fill and the group summary's pass rule."""
import numpy as np
import pandas as pd

from scanner import backtest_s1_v6 as v6
from scanner import backtest_s1_v9 as v9


def test_open_prices_make_the_engine_fill_the_open_plus_a_tick():
    p = pd.DataFrame({"TckrSymb": ["X"], "XpryDt": ["2025-01-30"], "StrkPric": [100.0], "OptnTp": ["CE"],
                      "OpnPric": [4.0], "HghPric": [6.0], "LwPric": [3.5], "ClsPric": [5.5], "TtlTradgVol": [80],
                      "TtlTrfVal": [4.2e6], "NewBrdLotQty": [500]})
    q = v6.day1_quotes(v9.open_prices(p), "X", "2025-01-30")[100.0]
    assert v6.fill_at(q, 50) == (4.05, "close")
    assert v6.fill_at(q, 100) is None                              # the day's contracts still decide liquidity


def test_summary_pass_rule():
    dates = [f"{y}-03-{d:02d}" for y in range(2021, 2027) for d in range(1, 11)]
    g = pd.DataFrame({"entry_date": dates, "net_pct": np.tile(np.linspace(-20, 60, 10), 6), "net": 100.0,
                      "premium_rs": 5000.0, "excluded": ""})
    s = v9.summary(g, {"cell": "x"})
    assert s["n"] == 60 and s["mean_pct"] == 20.0 and s["years_pos"] >= 5
    assert v9.summary(g.head(40), {"cell": "y"})["PASS"] == ""     # N < 50
