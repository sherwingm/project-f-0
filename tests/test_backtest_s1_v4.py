"""S1 v4: the pre-registered rules on hand-checkable numbers."""
import pytest

from scanner import backtest_s1_v4 as v4
from server import charges as ch


def test_strong_sector_for_arm_b():
    assert v4.strong_sector((1.0, 2.0, False))
    assert not v4.strong_sector((1.0, -2.0, False))
    assert not v4.strong_sector((1.0, 2.0, True))                           # below its 50-session average
    assert not v4.strong_sector(None)


def test_call_strike_nearest_with_the_lower_on_a_tie():
    assert v4.call_strike([90, 100, 110], 104.0) == 100.0
    assert v4.call_strike([90, 100, 110], 105.0) == 100.0
    assert v4.call_strike([90, 100, 110], 106.0) == 110.0
    assert v4.call_strike([], 100.0) is None


def test_exit_rules_in_order_and_the_5_session_variant():
    assert v4.exit_reason(5.0, 10.0, 25.0, 20, 3, 20) == "1_stop"
    assert v4.exit_reason(11.0, 10.0, 11.0, 2, 5, 20) == "2_expiry"
    assert v4.exit_reason(11.0, 10.0, 11.0, 5, 6, 5) == "3_time"
    assert v4.exit_reason(11.0, 10.0, 11.0, 5, 6, 20) is None
    assert v4.exit_reason(14.0, 10.0, 20.0, 3, 10, 20) == "4_trailing"
    assert v4.exit_reason(15.0, 10.0, 20.0, 3, 10, 20) is None
    assert v4.exit_reason(14.0, 10.0, 19.0, 3, 10, 20) is None               # never doubled


def test_position_and_cooldown():
    h = [(100, 110)]
    assert v4.blocked(h, 105) and v4.blocked(h, 120) and not v4.blocked(h, 121)
    assert not v4.blocked([], 5)


def test_net_of_charges_and_slippage():
    c, s, n = v4.net_of(10.0, 15.0, 500, 0.02)
    assert c == pytest.approx(ch.leg("CE", "BUY", 500, 10.0)["total"] + ch.leg("CE", "SELL", 500, 15.0)["total"], abs=0.01)
    assert s == pytest.approx(0.02 * 500 * 25.0)
    assert n == pytest.approx(5.0 * 500 - c - s, abs=0.01)
    c0, _, n0 = v4.net_of(10.0, 0.0, 500, 0.01)                            # worthless: no sell order
    assert c0 == pytest.approx(ch.leg("CE", "BUY", 500, 10.0)["total"], abs=0.01) and n0 < -5000


def test_gate_on_the_test_window():
    import pandas as pd
    t = pd.DataFrame({"arm": ["A"] * 3, "variant": [20] * 3, "entry_date": ["2021-03-01", "2023-03-01", "2024-03-01"],
                      "net": [100.0, 50.0, -20.0], "net_pct": [10.0, 5.0, -2.0], "premium_rs": [1000.0] * 3,
                      "excluded": [""] * 3, "exit_reason": ["3_time"] * 3})
    g = {r["test"]: r["result"] for r in v4.gate(t, "A")}
    assert g["net mean > 0 after costs (% of premium)"] == "pass" and g["positive in 2023-24 (mean %)"] == "pass"
    assert g["N >= 200"] == "fail" and g["OVERALL"] == "FAIL"
    assert {r["test"]: r["result"] for r in v4.gate(t, "B")}["OVERALL"] == "FAIL"
