from scanner import backtest_s1_v10 as bt
from scanner import strike_distance_study as S

STRIKES = [90.0, 95.0, 100.0, 105.0, 110.0]


def q(k, close, lot=100, contracts=500):
    return bt.Q(k, contracts, contracts * lot * (k + close), lot, close, close, close * 0.9, close * 1.1)


def test_otm_sign():
    assert S.otm_pct(95, 100, "PE") == 5.0 and S.otm_pct(105, 100, "CE") == 5.0
    assert S.otm_pct(105, 100, "PE") == -5.0


def test_baseline_walks_out_until_the_lot_fits_and_the_variants_differ():
    # puts: 100 costs 100 x 100 = Rs 10,000 (over the ceiling), 95 costs Rs 5,000, 90 costs Rs 2,000
    quotes = {100.0: q(100, 100.0), 95.0: q(95, 50.0), 90.0: q(90, 20.0)}
    base = S.ORIG_WALK(STRIKES, 100.0, "PE", quotes, "open")
    assert base[0].strike == 95.0 and base[3] == 1
    assert S.walk_capped(3.0)(STRIKES, 100.0, "PE", quotes, "open") == "no_strike_within_cap"
    assert S.walk_capped(5.0)(STRIKES, 100.0, "PE", quotes, "open")[0].strike == 95.0
    assert S.walk_closer(STRIKES, 100.0, "PE", quotes, "open")[0].strike == 100.0     # breaks the ceiling on purpose
    assert S.walk_atm(STRIKES, 100.0, "PE", quotes, "open")[0].strike == 100.0


def test_closer_is_the_same_trade_when_the_baseline_is_already_at_the_money():
    quotes = {105.0: q(105, 30.0, lot=100), 100.0: q(100, 60.0, lot=100)}
    assert S.ORIG_WALK(STRIKES, 101.0, "CE", quotes, "open")[3] == 0
    assert S.walk_closer(STRIKES, 101.0, "CE", quotes, "open")[0].strike == 100.0


def test_atm_skips_an_illiquid_start_strike():
    quotes = {110.0: q(110, 10.0), 105.0: q(105, 20.0, contracts=10)}               # 105 has too few contracts
    assert S.walk_atm(STRIKES, 104.0, "CE", quotes, "open")[0].strike == 110.0
