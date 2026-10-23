from datetime import date

import pandas as pd
import pytest

from scanner.s3_p1 import gate, half_means, max_drawdown, summary

HALVES = ((date(2025, 1, 1), date(2025, 1, 31)), (date(2025, 2, 1), date(2025, 2, 28)))


def trades(pcts, rs=None, start=date(2025, 1, 2)):
    days = pd.date_range(start, periods=len(pcts), freq="2D").date
    rs = rs if rs is not None else [p * 10 for p in pcts]
    return pd.DataFrame({"day": days, "net_pct_premium": pcts, "net_rs": rs, "reason": ["time"] * len(pcts)})


def test_max_drawdown_counts_from_zero():
    assert max_drawdown([100, -50, -80, 40]) == -130
    assert max_drawdown([-30, 10]) == -30


def test_half_means_split_by_date():
    t = trades([1.0] * 15 + [-2.0] * 15)
    a, b = half_means(t, HALVES)
    assert a > 0 and b < 0


def test_gate_needs_enough_trades():
    g = gate(trades([5.0] * 10), trades([4.0] * 10), [], HALVES)
    assert g["pass"] is False and g["checks"] == {"at least 30 trades": False}


def test_gate_passes_a_clean_series_and_fails_on_a_big_worst_day():
    good = trades([10.0, 12.0, 8.0] * 10)
    assert gate(good, good, [good], HALVES)["pass"]
    bad = good.copy()
    bad.loc[5, "net_rs"] = -10_000          # one day bigger than an average month
    g = gate(bad, bad, [good], HALVES)
    assert not g["checks"]["worst day smaller than the average month"]


def test_summary_win_rate():
    s = summary(trades([10.0, -5.0, 3.0, -1.0]))
    assert s["win"] == pytest.approx(0.5) and s["n"] == 4
