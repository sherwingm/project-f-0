"""S1 v6: the strike walk (Rs 600-8,000 per lot), the decay / T-2 exits, the holdout guard and the gate wiring."""
from datetime import date, timedelta

import pandas as pd
import pytest

from scanner import backtest_s1_v6 as v6

STRIKES = [95.0, 100.0, 105.0, 110.0, 115.0]


def q(k, close, contracts=100, lot=500, turnover=0.0):
    return v6.Quote(k, float(contracts), turnover, lot, close)


def test_walk_takes_the_at_the_money_call_when_it_fits():
    qq, px, src, walked = v6.walk_strike(STRIKES, 100.0, {100.0: q(100.0, 10.0)}, 50)
    assert (qq.strike, px, src, walked) == (100.0, 10.05, "close", 0)


def test_walk_skips_an_expensive_at_the_money_call():
    quotes = {100.0: q(100.0, 20.0), 105.0: q(105.0, 12.0), 110.0: q(110.0, 6.0)}   # Rs 10,025 / 6,025 / ...
    qq, px, _, walked = v6.walk_strike(STRIKES, 101.0, quotes, 50)
    assert qq.strike == 105.0 and px * qq.lot == pytest.approx(6025.0) and walked == 1


def test_walk_skips_a_thin_strike_and_honours_the_contract_minimum():
    quotes = {100.0: q(100.0, 20.0), 105.0: q(105.0, 12.0, contracts=30), 110.0: q(110.0, 6.0)}
    assert v6.walk_strike(STRIKES, 100.0, quotes, 50)[0].strike == 110.0
    assert v6.walk_strike(STRIKES, 100.0, quotes, 20)[0].strike == 105.0


def test_walk_skips_a_strike_with_no_day1_row():
    assert v6.walk_strike(STRIKES, 100.0, {105.0: q(105.0, 8.0)}, 50)[0].strike == 105.0


def test_walk_stops_below_the_band_and_refuses_lottery_premiums():
    assert v6.walk_strike(STRIKES, 100.0, {100.0: q(100.0, 2.5, lot=200)}, 50) == "walk_below_band"   # Rs 510
    assert v6.walk_strike(STRIKES, 100.0, {100.0: q(100.0, 1.5, lot=1000)}, 50) == "lottery_refused"
    assert v6.walk_strike(STRIKES, 100.0, {100.0: q(100.0, 0.55, lot=1000)}, 50) == "lottery_refused"


def test_walk_with_nothing_in_the_band():
    quotes = {k: q(k, 40.0) for k in STRIKES}                                          # all Rs 20,025
    assert v6.walk_strike(STRIKES, 100.0, quotes, 50) == "walk_no_liquid_strike_in_band"
    assert v6.walk_strike([], 100.0, {}, 50) == "no_strike_or_expiry"


def test_walk_never_walks_down():
    quotes = {95.0: q(95.0, 10.0), 100.0: q(100.0, 20.0)}
    assert v6.walk_strike(STRIKES, 100.0, quotes, 50) == "walk_no_liquid_strike_in_band"


def test_fill_uses_vwap_from_notional_turnover():
    k, prem, contracts, lot = 105.0, 10.0, 100, 500
    qq = v6.Quote(k, contracts, (k + prem) * contracts * lot, lot, 11.0, 9.0, 12.0)
    assert v6.fill_at(qq, 50) == (10.05, "vwap")
    assert v6.fill_at(qq, 101) is None


def test_decay_exits_after_n_sessions_without_a_new_high():
    best, stall, reasons = 10.0, 0, []
    for c in (11.0, 10.5, 10.8, 10.9):                     # new high, then three closes at or below it
        best, stall, r = v6.decay_step(c, best, stall, 15, 3)
        reasons.append(r)
    assert reasons == [None, None, None, "1_decay"] and best == 11.0


def test_decay_keeps_holding_while_making_new_highs():
    best, stall = 10.0, 0
    for c in (10.5, 10.4, 10.3, 11.0, 10.9, 10.8, 12.0):
        best, stall, r = v6.decay_step(c, best, stall, 15, 3)
        assert r is None
    assert best == 12.0 and stall == 0


def test_decay_counts_closes_below_entry():
    best, stall, r = 10.0, 0, None
    for c in (9.0, 8.0, 7.0):
        best, stall, r = v6.decay_step(c, best, stall, 15, 3)
    assert r == "1_decay" and best == 10.0


def test_t_minus_2_exit():
    assert v6.decay_step(12.0, 10.0, 0, 2, 3)[2] == "2_t_minus_2"
    assert v6.decay_step(12.0, 10.0, 0, 3, 3)[2] is None


def test_holdout_guard():
    d, cal = date(2024, 12, 2), []
    while d <= date(2024, 12, 31):
        if d.weekday() < 5:
            cal.append(d)
        d += timedelta(days=1)
    assert not v6.reads_holdout(cal, "2024-12-31", "2024-12-26")
    assert not v6.reads_holdout(cal, "2024-12-31", "2025-01-02")    # T-2 = 31 Dec
    assert v6.reads_holdout(cal, "2024-12-31", "2025-01-03")
    assert v6.reads_holdout(cal, "2024-12-31", "2025-01-30")


def _trades(nets, variant=v6.PRIMARY, arm="B"):
    n = len(nets)
    return pd.DataFrame({"arm": [arm] * n, "variant": [variant] * n,
                         "entry_date": [f"202{1 + 2 * (i % 2)}-03-{i % 28 + 1:02d}" for i in range(n)],
                         "net": nets, "net_pct": [x / 50 for x in nets], "premium_rs": [5000.0] * n,
                         "excluded": [""] * n, "exit_reason": ["1_decay"] * n, "held": [4] * n})


def test_metrics_reports_v6_exit_reasons():
    row = v6.metrics(_trades([100.0, -50.0]))
    assert row["exit_1_decay_pct"] == 100.0 and row["exit_2_t_minus_2_pct"] == 0.0 and row["mean_held"] == 4.0
    assert not any(k in row for k in ("exit_1_stop_pct", "exit_4_trailing_pct"))


def test_gate_reads_only_the_primary_variant():
    t = pd.concat([_trades([100.0] * 3), _trades([-100.0] * 300, variant="d5_c50")], ignore_index=True)
    g = {r["test"]: r for r in v6.gate(t, "B")}
    assert g["N >= 200"]["value"] == 3 and g["OVERALL"]["result"] == "FAIL"
    assert v6.gate(t, "A")[-1]["result"] == "FAIL"
