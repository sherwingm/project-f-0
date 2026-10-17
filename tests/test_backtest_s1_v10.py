import math
from datetime import date

from scanner import backtest_s1_v10 as B
from scanner.backtest_s1_v10 import Q


def q(k, contracts=100, lot=100, op=10.0, cl=10.0, turnover=math.nan):
    return Q(k, contracts, turnover, lot, op, cl)


def test_start_strike_ties_and_period():
    assert B.start_strike([100.0, 110.0], 105.0, "CE") == 100.0           # a tie: the lower call
    assert B.start_strike([100.0, 110.0], 105.0, "PE") == 110.0           # a tie: the higher put
    assert B.period_of("2025-06-30") == "2025 H1" and B.period_of("2026-09-25") == "2026 Q3"


def test_entry_is_open_plus_a_tick_and_needs_50_contracts():
    assert B.entry_price(q(100.0, op=9.0), "open") == (9.05, "open")
    assert B.entry_price(q(100.0, contracts=49), "open") is None
    assert B.entry_price(q(100.0, op=0.0), "open") is None                # no opening trade
    # VWAP = turnover / (contracts x lot) - strike = 20000*... : (100+8) x 100 x 100 / (100 x 100) - 100 = 8
    assert B.entry_price(q(100.0, turnover=108.0 * 100 * 100), "vwap") == (8.05, "vwap")


def test_put_walk_goes_down_call_walk_goes_up_and_skips_dear_lots():
    quotes = {110.0: q(110.0, op=90.0, lot=100), 100.0: q(100.0, op=20.0, lot=100), 90.0: q(90.0, op=9.0, lot=100)}
    got = B.walk([90.0, 100.0, 110.0], 105.0, "PE", quotes, "open")       # 105 is a tie: 110 (put: the higher)
    assert got[0].strike == 100.0 and got[1] == 20.05 and got[3] == 1     # 110 costs Rs 9,005 > 8,000: skipped
    calls = {100.0: q(100.0, op=90.0), 110.0: q(110.0, op=7.0), 120.0: q(120.0, op=3.0)}
    got = B.walk([100.0, 110.0, 120.0], 105.0, "CE", calls, "open")       # tie: 100 (call: the lower)
    assert got[0].strike == 110.0 and got[3] == 1
    assert B.walk([100.0], 100.0, "CE", {100.0: q(100.0, op=1.0)}, "open") == "premium_below_2"
    assert B.walk([100.0], 100.0, "CE", {100.0: q(100.0, op=5.0, lot=100)}, "open") == "walk_below_band"
    assert B.walk([100.0], 100.0, "CE", {100.0: q(100.0, contracts=10)}, "open") == "walk_no_liquid_strike_in_band"


def test_carry_step_stop_trail_and_t_minus_1():
    assert B.carry_step(16.0, 20.0, 20.0, 9) == (20.0, "stop")             # <= 0.80 x 20
    assert B.carry_step(17.0, 20.0, 20.0, 9) == (20.0, None)
    assert B.carry_step(30.0, 20.0, 20.0, 9) == (30.0, None)               # a new peak
    assert B.carry_step(22.0, 20.0, 30.0, 9) == (30.0, "trail")            # 22 <= 0.75 x 30 = 22.5
    assert B.carry_step(25.0, 20.0, 30.0, 1) == (30.0, "t_minus_1")


class FakeBhav:
    def __init__(self, days):
        self.days = days

    def day(self, d):
        return self.days.get(d)


def day(c, fut=100.0):
    return {"opt": {("X", "2026-01-29", 100.0, "PE"): c}, "futs": {("X", "2026-01-29"): fut}}


def test_path_e1_is_day0_close_and_e2_trails():
    s = [f"2026-01-{d:02d}" for d in (5, 6, 7, 8, 9)]
    cal = [date.fromisoformat(x) for x in s]
    bh = FakeBhav({s[0]: day(10.0), s[1]: day(14.0), s[2]: day(15.0), s[3]: day(11.0), s[4]: day(12.0)})
    p = B._path("X", "PE", "2026-01-29", 100.0, 10.0, 0, s, cal, bh, None)
    assert p["e1"]["price"] == 9.95 and p["e1"]["excluded"] == ""
    # peak 15 on 7 Jan; 11 <= 0.75 x 15 = 11.25 on 8 Jan -> trail
    assert (p["e2"]["reason"], p["e2"]["date"], p["e2"]["price"], p["e2"]["held"]) == ("trail", s[3], 10.95, 3)


def test_path_without_an_exit_is_excluded_and_a_missing_contract_is_counted():
    s = ["2026-01-05", "2026-01-06"]
    cal = [date.fromisoformat(x) for x in s]
    p = B._path("X", "PE", "2026-01-29", 100.0, 10.0, 0, s, cal, FakeBhav({s[0]: day(10.0), s[1]: day(10.5)}), None)
    assert p["e2"]["excluded"] == "no_exit_in_data" and p["e1"]["excluded"] == ""
    p = B._path("X", "PE", "2026-01-29", 100.0, 10.0, 0, s, cal, FakeBhav({s[0]: {"opt": {}, "futs": {}}}), None)
    assert p["e1"]["excluded"] == p["e2"]["excluded"] == "contract_changed"


def test_period_of_other_windows_uses_half_years():
    assert B.period_of("2022-03-15") == "2022 H1" and B.period_of("2024-07-01") == "2024 H2"
