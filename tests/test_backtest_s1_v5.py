"""S1 v5: the Rs 10,000-30,000 band sizing and the flat-slippage recomputation."""
import pandas as pd
import pytest

from scanner import backtest_s1_v5 as v5


def test_band_sizer_one_lot_inside_the_band():
    assert v5.band_sizer(20.0, 500, 0.02, 0.02) == (1, None, None)            # Rs 10,000: inside
    assert v5.band_sizer(60.0, 500, 0.02, 0.02) == (1, None, None)            # Rs 30,000: inside
    assert v5.band_sizer(19.99, 500, 0.02, 0.02)[2] == "premium_below_band"
    assert v5.band_sizer(60.01, 500, 0.02, 0.02)[2] == "premium_above_band"
    assert v5.band_sizer(20.0, 0, 0.02, 0.02)[0] == 0


def test_flat_slippage_recomputes_net():
    t = pd.DataFrame({"entry_price": [20.0], "exit_price": [30.0], "qty": [500], "charges": [100.0],
                      "slippage": [0.0], "net": [0.0], "net_pct": [0.0], "premium_rs": [10000.0], "excluded": [""]})
    r = v5.with_flat_slippage(t, 0.02).iloc[0]
    assert r["slippage"] == pytest.approx(0.02 * 500 * 50) and r["net"] == pytest.approx(5000 - 100 - 500)
    assert r["net_pct"] == pytest.approx(44.0)


def test_equity_curve_drawdown():
    t = pd.DataFrame({"entry_date": ["2021-01-04", "2021-02-01"], "exit_date": ["2021-01-20", "2021-02-20"],
                      "net": [-1000.0, 3000.0], "excluded": ["", ""]})
    curve, dd, pct = v5.equity_curve(t)
    assert list(curve["cumulative_rs"]) == [-1000.0, 2000.0] and dd == -1000.0 and pct == -0.2
