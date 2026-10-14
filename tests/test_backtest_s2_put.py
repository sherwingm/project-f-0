"""S2 step 2: the downward put walk, the tie to the higher strike, and the exit order."""
from scanner import backtest_s2_put as s2p
from scanner.backtest_s1_v6 import Quote

KS = [90.0, 95.0, 100.0, 105.0, 110.0]


def q(k, close, contracts=200, lot=500):
    return Quote(k, float(contracts), 0.0, lot, close)


def test_nearest_strike_tie_goes_higher():
    assert s2p.put_strike(KS, 102.5) == 105.0 and s2p.put_strike(KS, 101.0) == 100.0


def test_walk_down_takes_the_first_affordable_liquid_put():
    quotes = {100.0: q(100.0, 20.0), 95.0: q(95.0, 12.0, contracts=30), 90.0: q(90.0, 6.0)}   # 10,025 / thin / 3,025
    qq, px, _, walked = s2p.walk_put(KS, 100.0, quotes)
    assert qq.strike == 90.0 and px == 6.05 and walked == 2


def test_walk_never_goes_up_and_stops_below_600():
    assert s2p.walk_put(KS, 100.0, {105.0: q(105.0, 5.0)}) == "walk_no_liquid_strike_in_band"
    assert s2p.walk_put(KS, 100.0, {100.0: q(100.0, 1.0, lot=500)}) == "lottery_refused"
    assert s2p.walk_put(KS, 100.0, {100.0: q(100.0, 2.4, lot=200)}) == "walk_below_band"        # Rs 490
    assert s2p.walk_put([], 100.0, {}) == "no_strike_or_expiry"


def test_exit_order_stop_time_t_minus_1():
    v5, v3, ns = s2p.VARIANTS
    assert s2p.exit_step(2, 4.9, 10.0, 15, v5) == "0_stop"
    assert s2p.exit_step(2, 4.9, 10.0, 15, ns) is None                    # no stop
    assert s2p.exit_step(5, 12.0, 10.0, 15, v5) == "1_time" and s2p.exit_step(4, 12.0, 10.0, 15, v5) is None
    assert s2p.exit_step(3, 12.0, 10.0, 15, v3) == "1_time"
    assert s2p.exit_step(2, 12.0, 10.0, 1, v5) == "2_t_minus_1"
