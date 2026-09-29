"""S1 v2: each pre-registered rule on hand-checkable numbers, then synthetic trades end to end."""
import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from scanner import backtest_s1 as s1
from server import charges as ch


def test_leave_one_out_sector_drops_the_stock_and_needs_three_peers():
    r = [np.array([0.01, 0.02]), np.array([0.03, np.nan]), np.array([0.05, 0.04]), np.array([0.07, 0.06])]
    total, count = s1.peer_sums(r, 2)
    assert list(count) == [4, 3]
    loo = s1.leave_one_out(total, count, r[0])
    assert loo[0] == pytest.approx((0.03 + 0.05 + 0.07) / 3)
    assert math.isnan(loo[1])                                   # only 2 others on day 1
    loo1 = s1.leave_one_out(total, count, r[1])                 # the stock has no return on day 1: all 3 others
    assert loo1[1] == pytest.approx((0.02 + 0.04 + 0.06) / 3)


def test_sector_filter_on_the_leave_one_out_level():
    bench = np.full(80, 100.0)
    falling = np.full(80, -0.004)                               # the sector loses 0.4 % a day, NIFTY 500 flat
    st = s1.sector_state(falling, bench, 79)
    assert st[0] == pytest.approx(((1 - 0.004) ** 21 - 1) * 100) and st[1] == pytest.approx(((1 - 0.004) ** 63 - 1) * 100)
    assert st[2] and s1.sector_weak(st)
    bounce = falling.copy()
    bounce[-1] = 0.2                                            # +20 % today: above its 50-session average
    assert not s1.sector_weak(s1.sector_state(bounce, bench, 79))
    assert not s1.sector_weak(s1.sector_state(-falling, bench, 79))
    assert s1.sector_state(falling, bench, 62) is None           # needs 63 sessions of returns
    gap = falling.copy()
    gap[40] = np.nan
    assert s1.sector_state(gap, bench, 79) is None


def test_day0_is_the_first_full_session_after_the_filing():
    cal = ["2026-09-24", "2026-09-25", "2026-09-28"]
    assert s1.day0_index(cal, "2026-09-25", "09:10") == 1        # before the open: that day
    assert s1.day0_index(cal, "2026-09-25", "09:15") == 2        # at or after the open: the next session
    assert s1.day0_index(cal, "2026-09-25", "17:45") == 2
    assert s1.day0_index(cal, "2026-09-26", "08:00") == 2        # a Saturday filing: Monday
    assert s1.day0_index(cal, "2026-09-25", None) == 2           # no time: treated as after the open
    assert s1.day0_index(cal, "2026-09-28", "18:00") is None


def test_abnormal_return_and_the_technical_trigger():
    close = np.array([100.0, 97.0])
    loo = np.array([np.nan, 0.005])
    assert s1.abnormal_pct(close, loo, 1) == pytest.approx(-3.5)
    stock = np.linspace(110, 95, 40)                             # below its 20-DMA, 1M about -5 %
    flat = np.zeros(40)
    assert s1.technical(stock, flat, 39)
    assert not s1.technical(np.linspace(95, 110, 40), flat, 39)
    assert not s1.technical(stock, np.full(40, -0.01), 39)       # the sector fell more (1M about -19 %)


def test_choose_spread_expiry_long_and_short_strikes():
    cal = [d.date() for d in pd.bdate_range("2026-09-01", "2026-12-31")]
    d = date(2026, 9, 25)
    strikes = [900.0, 920.0, 930.0, 940.0, 950.0, 960.0, 980.0, 1000.0, 1020.0]
    chain = {(e, k): (10.0, 1e6, 500) for e in ("2026-09-29", "2026-10-27", "2026-11-24") for k in strikes}
    # 2026-10-27 is 22 sessions after 25 Sep, 2026-11-24 is 42: the first with >= 25 is November
    assert s1.choose_spread(chain, cal, d, 1005.0) == ("2026-11-24", 1000.0, 940.0)    # short band 934.65..954.75
    assert s1.choose_spread(chain, cal, d, 1010.0) == ("2026-11-24", 1020.0, 950.0)    # tie 1000/1020: the higher
    assert s1.choose_spread(chain, cal, d, 1100.0) is None                              # nothing in 1023..1045
    assert s1.choose_spread({("2026-10-27", 1000.0): (1, 1, 1)}, cal, d, 1000.0) is None


def test_choose_put_naked():
    d = date(2026, 9, 25)
    chain = {("2026-09-29", 1000.0): 0, ("2026-10-27", 1000.0): 0, ("2026-10-27", 980.0): 0, ("2026-10-27", 1020.0): 0}
    assert s1.choose_put(chain, d, 1005.0) == ("2026-10-27", 1000.0)
    assert s1.choose_put(chain, d, 1060.0) is None


def test_exit_rules_in_order():
    assert s1.exit_reason(5, 10, 5, 0, 20) == "1_stop"
    assert s1.exit_reason(5, 10, 25, 20, 3) == "1_stop"                  # several hold: the first in order
    assert s1.exit_reason(11, 10, 11, 3, 5) == "2_expiry"
    assert s1.exit_reason(11, 10, 11, 20, 6) == "3_20_sessions"
    assert s1.exit_reason(14, 10, 20, 5, 10) == "4_trailing"              # peak 2x, now 0.7x of the peak
    assert s1.exit_reason(15, 10, 20, 5, 10) is None                     # 0.75x of the peak: kept
    assert s1.exit_reason(13, 10, 19, 5, 10) is None                     # never reached 2x: no trailing
    assert s1.exit_reason(5.01, 10, 5.01, 0, 6) is None


def test_lot_from_open_interest():
    rows = pd.DataFrame({"OpnIntrst": [3000, 4500, 0, 1500]})
    assert s1._lot_from_oi(rows) == 1500


# ---------------------------------------------------------------- synthetic market
def _synthetic(results_time="18:00"):
    cal = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2026-03-02", periods=130)]
    n = len(cal)
    sig = 100
    idx = pd.to_datetime(cal)
    peers = {f"P{j}": pd.Series(1000 * np.cumprod(np.r_[1, np.full(n - 1, 1 - 0.003 + 0.0005 * j)]), index=idx)
             for j in range(3)}                                          # a falling sector of three peers
    stock_px = 1000 * np.cumprod(np.r_[1, np.full(n - 1, 1 - 0.002)])
    stock_px[sig:] *= 0.95                                               # day 0: -5 % on results
    stock = {"ABC": pd.Series(stock_px, index=idx), **peers}
    sector_of = {s: "nifty metal" for s in stock}
    bench = pd.Series(np.full(n, 100.0), index=idx)
    expiries = ("2026-08-27", "2026-09-24")                             # signal 2026-07-20: 28 and 47 sessions away
    state = {"long": 40.0, "short": 16.0}

    def bhav(d):
        i = cal.index(d)
        spot = float(stock_px[i])
        rows = [dict(TckrSymb="ABC", FinInstrmTp="STF", XpryDt=e, StrkPric=0, OptnTp=None, ClsPric=spot,
                     OpnIntrst=1e6, UndrlygPric=spot, NewBrdLotQty=250, TtlTradgVol=500) for e in expiries]
        long_c, short_c = (40.0, 16.0) if i <= sig + 1 else (state["long"], state["short"])
        for e in expiries:
            for k in np.arange(700.0, 900.0, 10.0):
                c = long_c if k in (780.0, 770.0) else short_c if k == 730.0 else 5.0
                rows.append(dict(TckrSymb="ABC", FinInstrmTp="STO", XpryDt=e, StrkPric=k, OptnTp="PE", ClsPric=c,
                                 OpnIntrst=1e6, UndrlygPric=spot, NewBrdLotQty=250, TtlTradgVol=500))
        return pd.DataFrame(rows)

    def opens(d):
        return pd.DataFrame([dict(TckrSymb="ABC", XpryDt=e, StrkPric=k, OptnTp="PE", OpnPric=p)
                             for e in expiries for k, p in ((780.0, 40.0), (770.0, 40.0), (730.0, 16.0))])

    inp = s1.Inputs(cal=cal, bhav=bhav, opens=opens, stock=stock, sector_of=sector_of, bench=bench,
                    results=[("ABC", cal[sig - 1], results_time)])
    return inp, cal, sig, state, stock_px


def test_the_synthetic_signal_fires_on_day_0():
    inp, cal, sig, _, px = _synthetic()
    m = s1.Market(inp)
    sigs = s1.results_signals(m, inp.results)
    assert list(sigs) == [sig] and sigs[sig]["ABC"] == pytest.approx((0.998 * 0.95 - 1 + 0.0025) * 100)
    assert s1.sector_weak(m.state("ABC", sig))


def test_spread_trade_end_to_end_with_the_stop():
    inp, cal, sig, state, px = _synthetic()
    spot = px[sig]                                                       # 777.7: long 780, short band 723.3..738.8
    out = s1.run(inp, cal[sig], cal[sig], arms=("S1v2",))
    assert len(out["S1v2"][0]) == 0                                      # entry is the next session
    state["long"], state["short"] = 20.0, 10.0                           # value 10 <= 0.5 x 24.1
    trades, skips = s1.run(inp, cal[sig], cal[sig + 4], arms=("S1v2",))["S1v2"]
    t = trades.iloc[0]
    assert (t["signal_date"], t["entry_date"], t["long_k"], t["short_k"]) == (cal[sig], cal[sig + 1], 780.0, 730.0)
    assert spot * 0.93 <= 730 <= spot * 0.95 and t["expiry"] == "2026-08-27"
    assert (t["long_in"], t["short_in"], t["debit"], t["qty"]) == (40.05, 15.95, 24.1, 250)
    assert t["exit_date"] == cal[sig + 2] and t["exit_reason"] == "1_stop" and t["held"] == 1
    assert (t["long_out"], t["short_out"]) == (19.95, 10.05)
    charges = (ch.leg("PE", "BUY", 250, 40.05)["total"] + ch.leg("PE", "SELL", 250, 15.95)["total"]
               + ch.leg("PE", "SELL", 250, 19.95)["total"] + ch.leg("PE", "BUY", 250, 10.05)["total"])
    slip = 0.02 * 250 * (40.05 + 15.95 + 19.95 + 10.05)
    gross = 250 * ((19.95 - 40.05) - (10.05 - 15.95))
    assert t["net"] == pytest.approx(gross - charges - slip, abs=0.02)
    assert t["net_pct"] == pytest.approx(t["net"] / (24.1 * 250) * 100, abs=0.001)


def test_trailing_exit_cooldown_and_ban():
    inp, cal, sig, state, _ = _synthetic()
    state["long"], state["short"] = 70.0, 15.0                           # value 55 >= 2 x 24.1: armed, peak 55
    trades, _ = s1.run(inp, cal[sig], cal[sig + 3], arms=("S1v2",))["S1v2"]
    assert trades.empty
    inp2, cal, sig, state2, _ = _synthetic()
    base = inp2.bhav

    def bhav(d):                                                         # value 55, then 35 < 0.75 x 55
        state2["long"], state2["short"] = (70.0, 15.0) if cal.index(d) <= sig + 2 else (50.0, 15.0)
        return base(d)
    inp2.bhav = bhav
    trades, _ = s1.run(inp2, cal[sig], cal[sig + 4], arms=("S1v2",))["S1v2"]
    assert trades.iloc[0]["exit_reason"] == "4_trailing" and trades.iloc[0]["exit_date"] == cal[sig + 3]
    inp3, cal, sig, _, _ = _synthetic()
    inp3.ban = {cal[sig + 1]: {"ABC"}}                                   # in ban on the entry day
    trades, skips = s1.run(inp3, cal[sig], cal[sig + 3], arms=("S1v2",))["S1v2"]
    assert trades.empty and skips["in_ban_on_entry_day"] == 1


def test_a_filing_before_the_open_moves_day_0():
    inp, cal, sig, _, _ = _synthetic(results_time="08:30")              # day 0 = the filing day, sig - 1: no drop
    m = s1.Market(inp)
    assert s1.results_signals(m, inp.results) == {}


def test_naked_arm_and_debit_bounds():
    inp, cal, sig, state, _ = _synthetic()
    state["long"], state["short"] = 20.0, 10.0
    out = s1.run(inp, cal[sig], cal[sig + 4], arms=("S1alt",))
    t = out["S1alt"][0].iloc[0]
    assert t["structure"] == "naked" and (t["expiry"], t["long_k"], t["debit"]) == ("2026-09-24", 770.0, 40.05)
    assert t["exit_reason"] == "1_stop" and t["short_in"] == 0
    inp, cal, sig, state, _ = _synthetic()
    inp.opens = lambda d: pd.DataFrame([dict(TckrSymb="ABC", XpryDt="2026-08-27", StrkPric=780.0, OptnTp="PE", OpnPric=60.0),
                                        dict(TckrSymb="ABC", XpryDt="2026-08-27", StrkPric=730.0, OptnTp="PE", OpnPric=16.0)])
    _, skips = s1.run(inp, cal[sig], cal[sig + 2], arms=("S1v2",))["S1v2"]
    assert skips["debit_outside_2000_8000"] == 1                         # 44.1 x 250 = 11,025


def test_metrics_and_periods():
    t = pd.DataFrame({"entry_date": ["2021-03-01", "2021-03-01", "2023-05-02", "2025-01-10"],
                      "net": [100.0, -50.0, 200.0, -10.0], "debit_rs": [1000.0] * 4,
                      "net_pct": [10.0, -5.0, 20.0, -1.0], "excluded": [""] * 4, "rel63": [-20, -5, -5, -5],
                      "exit_reason": ["4_trailing", "1_stop", "3_20_sessions", "1_stop"]})
    s = s1.summarise(t)
    a = s[(s["group"] == "all")].set_index("period")
    assert a.loc["all", "n"] == 4 and a.loc["all", "hit_rate_pct"] == 50.0 and a.loc["all", "net_per_1000"] == 60.0
    assert a.loc["2021-22", "n"] == 2 and a.loc["2021-22", "mean_pct"] == 2.5 and a.loc["all", "mean_rs"] == 60.0
    assert a.loc["all", "exit_1_stop_pct"] == 50.0 and a.loc["2023-24", "exit_3_20_sessions_pct"] == 100.0
    e = s[s["group"] != "all"].set_index("period")
    assert e.loc["all", "n"] == 1
