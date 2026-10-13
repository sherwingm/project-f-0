"""S1 v7: the near-expiry expiry rule, the near-expiry strike walk (>= 500 contracts, Rs 600-3,000), the exit order
(stop, 5-session decay, T-1), the holdout guard and the gate wiring."""
from datetime import date, timedelta

import pandas as pd

from scanner import backtest_s1_v6 as v6
from scanner import backtest_s1_v7 as v7

STRIKES = [95.0, 100.0, 105.0, 110.0, 115.0]
PRIMARY = v7.VARIANTS[0]


def weekdays(a: date, b: date) -> list[date]:
    out, d = [], a
    while d <= b:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


CAL = weekdays(date(2024, 1, 1), date(2024, 3, 29))
EXPIRIES = ["2024-01-25", "2024-02-29", "2024-03-28"]


def day_with(n_left: int) -> date:
    """The session with `n_left` sessions after it up to and including 25 Jan 2024."""
    i = CAL.index(date(2024, 1, 25))
    return CAL[i - n_left]


def q(k, close, contracts=1000, lot=100):
    return v6.Quote(k, float(contracts), 0.0, lot, close)


def test_expiry_keeps_the_current_monthly_down_to_three_sessions():
    assert v7.choose_expiry(EXPIRIES, CAL, day_with(10)) == ("2024-01-25", False, 10)
    assert v7.choose_expiry(EXPIRIES, CAL, day_with(9)) == ("2024-01-25", True, 9)
    assert v7.choose_expiry(EXPIRIES, CAL, day_with(3)) == ("2024-01-25", True, 3)
    exp, near, _ = v7.choose_expiry(EXPIRIES, CAL, day_with(2))
    assert (exp, near) == ("2024-02-29", False)


def test_old_expiry_variant_skips_near_expiry():
    exp, near, _ = v7.choose_expiry(EXPIRIES, CAL, day_with(5), near_ok=False)
    assert (exp, near) == ("2024-02-29", False)


def test_near_expiry_takes_a_liquid_at_the_money_call_in_band():
    qq, px, _, walked = v7.walk(STRIKES, 100.0, {100.0: q(100.0, 20.0)}, True, PRIMARY)    # Rs 2,005
    assert (qq.strike, walked) == (100.0, 0) and px == 20.05


def test_near_expiry_skips_a_thin_at_the_money_call():
    quotes = {100.0: q(100.0, 20.0, contracts=400), 105.0: q(105.0, 12.0, contracts=600)}
    assert v7.walk(STRIKES, 100.0, quotes, True, PRIMARY)[0].strike == 105.0
    assert v7.walk(STRIKES, 100.0, quotes, True, v7.VARIANTS[1])[0].strike == 100.0      # near_c50


def test_near_expiry_walks_past_a_lot_above_3000():
    quotes = {100.0: q(100.0, 45.0), 105.0: q(105.0, 25.0)}                               # Rs 4,505 / 2,505
    assert v7.walk(STRIKES, 100.0, quotes, True, PRIMARY)[0].strike == 105.0
    assert v7.walk(STRIKES, 100.0, quotes, False, PRIMARY)[0].strike == 100.0             # normal: <= 8,000


def test_near_expiry_stops_below_600():
    assert v7.walk(STRIKES, 100.0, {100.0: q(100.0, 5.0)}, True, PRIMARY) == "walk_below_band"   # Rs 505


def test_exit_order_stop_first():
    assert v7.exit_step(5.0, 10.0, 10.0, 0, 15)[2] == "0_stop"                           # exactly 50 %
    assert v7.exit_step(5.1, 10.0, 10.0, 0, 15)[2] is None
    assert v7.exit_step(4.0, 10.0, 10.0, 0, 1)[2] == "0_stop"                            # before T-1
    assert v7.exit_step(4.0, 10.0, 10.0, 0, 15, stop=None)[2] is None                    # no_stop


def test_decay_needs_five_sessions():
    best, stall, reasons = 10.0, 0, []
    for c in (11.0, 10.5, 10.8, 10.9, 10.7, 10.6):                    # a new high, then five without
        best, stall, r = v7.exit_step(c, 10.0, best, stall, 15)
        reasons.append(r)
    assert reasons == [None, None, None, None, None, "1_decay"]


def test_last_exit_is_t_minus_1():
    assert v7.exit_step(12.0, 10.0, 10.0, 0, 1)[2] == "2_t_minus_1"
    assert v7.exit_step(12.0, 10.0, 10.0, 0, 2)[2] is None


def test_holdout_guard_at_t_minus_1():
    cal = weekdays(date(2024, 12, 2), date(2024, 12, 31))
    assert not v7.reads_holdout(cal, "2024-12-31", "2025-01-01")       # T-1 = 31 Dec
    assert v7.reads_holdout(cal, "2024-12-31", "2025-01-02")


def test_v6_defaults_unchanged():
    assert v6.walk_strike(STRIKES, 100.0, {100.0: q(100.0, 45.0)}, 50)[0].strike == 100.0   # Rs 4,505 in 600-8,000
    assert v6.decay_step(12.0, 10.0, 0, 2, 3)[2] == "2_t_minus_2"


def _trades(nets, variant=v7.PRIMARY, arm="B"):
    n = len(nets)
    return pd.DataFrame({"arm": [arm] * n, "variant": [variant] * n,
                         "entry_date": [f"202{1 + 2 * (i % 2)}-03-{i % 28 + 1:02d}" for i in range(n)],
                         "net": nets, "net_pct": [x / 50 for x in nets], "premium_rs": [5000.0] * n,
                         "excluded": [""] * n, "exit_reason": ["0_stop", "1_decay"] * (n // 2) + ["1_decay"] * (n % 2),
                         "held": [4] * n})


def test_metrics_reports_v7_exit_reasons():
    row = v7.metrics(_trades([100.0, -50.0]))
    assert row["exit_0_stop_pct"] == 50.0 and row["exit_1_decay_pct"] == 50.0 and row["exit_2_t_minus_1_pct"] == 0.0


def test_gate_reads_only_the_primary_variant():
    t = pd.concat([_trades([100.0] * 3), _trades([-100.0] * 300, variant="no_stop")], ignore_index=True)
    g = {r["test"]: r for r in v7.gate(t, "B")}
    assert g["N >= 200"]["value"] == 3 and g["OVERALL"]["result"] == "FAIL"
