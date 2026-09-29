"""S1 weak-sector put: each rule on hand-checkable numbers, then one synthetic trade end to end."""
import math

import numpy as np
import pandas as pd
import pytest

from scanner import backtest_s1 as s1
from server import charges as ch


def test_sector_weak_needs_both_relative_returns_negative_and_a_close_below_the_50_dma():
    bench = np.full(80, 100.0)
    falling = np.linspace(120, 90, 80)                          # down 25 %, bench flat
    assert s1.sector_weak(falling, bench, 79)
    rising = np.linspace(90, 120, 80)
    assert not s1.sector_weak(rising, bench, 79)
    bounce = falling.copy()
    bounce[-1] = 130                                            # above its 50-DMA today
    assert not s1.sector_weak(bounce, bench, 79)
    assert not s1.sector_weak(falling, bench, 40)               # not enough history for 3 months


def test_weak_stock_and_results_miss():
    sector = np.full(40, 100.0)
    stock = np.linspace(110, 95, 40)                            # below its 20-DMA, 1M worse than a flat sector
    assert s1.weak_stock(stock, sector, 39)
    assert not s1.weak_stock(np.linspace(95, 110, 40), sector, 39)
    nifty = np.full(40, 100.0)
    s = np.full(40, 100.0)
    s[31:] = 97.0                                               # T = 30: close T-1 = 100, close T+1 = 97 -> -3 %
    assert s1.results_miss(s, nifty, [30], 35)                  # within 15 sessions
    assert not s1.results_miss(s, nifty, [30], 30)              # T+1 not yet known on T
    assert not s1.results_miss(s, nifty, [30], 45)              # older than 15 sessions
    s2 = np.full(40, 100.0)
    s2[31:] = 99.0                                              # -1 %: not a miss
    assert not s1.results_miss(s2, nifty, [30], 35)


def test_choose_put_takes_the_next_month_and_the_strike_nearest_the_money_within_3pct():
    chain = {("2026-09-29", 1000.0): (5, 1e6, 500), ("2026-10-27", 1000.0): (30, 1e6, 500),
             ("2026-10-27", 980.0): (20, 1e6, 500), ("2026-10-27", 960.0): (12, 1e6, 500),
             ("2026-10-27", 1020.0): (45, 1e6, 500), ("2026-11-24", 990.0): (40, 1e6, 500)}
    assert s1.choose_put(chain, "2026-09-25", 1005.0) == ("2026-10-27", 1000.0)     # 975.85..1005: 980 and 1000
    assert s1.choose_put(chain, "2026-09-25", 1030.0) == ("2026-10-27", 1020.0)     # 999.1..1030: 1000 and 1020
    assert s1.choose_put(chain, "2026-09-25", 1060.0) is None                         # 1028.2..1060: none listed
    assert s1.choose_put({("2026-09-29", 1000.0): (5, 1e6, 500)}, "2026-09-25", 1000) is None


def test_exit_rules_in_order():
    assert s1.exit_reason(90, 91, 10, 10, 1, 20) == "stock_at_1m_low"
    assert s1.exit_reason(95, 91, 25, 10, 1, 20) == "premium_2.5x"
    assert s1.exit_reason(95, 91, 5, 10, 1, 20) == "premium_0.5x"
    assert s1.exit_reason(95, 91, 11, 10, 10, 20) == "10_sessions"
    assert s1.exit_reason(95, 91, 11, 10, 3, 5) == "5_sessions_to_expiry"
    assert s1.exit_reason(95, 91, 11, 10, 3, 6) is None
    assert s1.exit_reason(90, 91, 25, 10, 10, 1) == "stock_at_1m_low"               # several: the first in order
    assert s1.exit_reason(95, math.nan, 11, 10, 3, 6) is None


def _synthetic():
    cal = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2026-05-01", periods=110)]
    n = len(cal)
    sig, entry_i = 100, 101
    sector = pd.Series(np.linspace(100, 90, n), index=pd.to_datetime(cal))          # weak all along (1M about -2 %)
    flat = pd.Series(np.full(n, 100.0), index=pd.to_datetime(cal))
    stock_px = np.linspace(1200, 1000, n)                                          # below its 20-DMA, 1M about -4 %
    stock_px[sig - 4:] = stock_px[sig - 5] + np.arange(1, n - sig + 5)             # a small bounce: no fresh low
    stock_px[entry_i + 2] = 900.0                                                  # a new 1-month low 2 sessions in
    stock = pd.Series(stock_px, index=pd.to_datetime(cal))
    expiries = ("2026-09-29", "2026-10-27")

    def bhav(d):
        i = cal.index(d)
        spot = float(stock_px[i])
        rows = [dict(TckrSymb="ABC", FinInstrmTp="STF", XpryDt=e, StrkPric=0, OptnTp=None, ClsPric=spot,
                     OpnIntrst=1e6, UndrlygPric=spot, NewBrdLotQty=500) for e in expiries]
        prem = 20.0 if i <= entry_i else 60.0                                      # the put triples after the drop
        k = 1000.0 if spot >= 1000 else 900.0
        for e in expiries:
            rows.append(dict(TckrSymb="ABC", FinInstrmTp="STO", XpryDt=e, StrkPric=1000.0, OptnTp="PE", ClsPric=prem,
                             OpnIntrst=1e6, UndrlygPric=spot, NewBrdLotQty=500))
        return pd.DataFrame(rows)

    def opens(d):
        return pd.DataFrame([dict(TckrSymb="ABC", XpryDt="2026-10-27", StrkPric=1000.0, OptnTp="PE", OpnPric=21.0)])

    inp = s1.Inputs(cal=cal, bhav=bhav, opens=opens, stock={"ABC": stock}, sector_of={"ABC": "nifty metal"},
                    sector={"nifty metal": sector}, bench=flat, nifty=flat)
    return inp, cal, sig, entry_i


def test_one_trade_end_to_end():
    inp, cal, sig, entry_i = _synthetic()
    trades, skips = s1.run(inp, cal[sig], cal[sig])                                  # one signal day only
    assert len(trades) == 0 and skips["still_open_at_end"] == 0                      # entry is the next session
    trades, skips = s1.run(inp, cal[sig], cal[entry_i + 5])
    t = trades.iloc[0]
    assert (t["signal_date"], t["entry_date"], t["expiry"], t["strike"]) == (cal[sig], cal[entry_i], "2026-10-27", 1000.0)
    assert t["entry_price"] == 21.05 and t["exit_date"] == cal[entry_i + 1] and t["exit_reason"] == "premium_2.5x"
    buy, sell = ch.leg("PE", "BUY", 500, 21.05)["total"], ch.leg("PE", "SELL", 500, 59.95)["total"]
    assert t["exit_price"] == 59.95 and t["net"] == pytest.approx(59.95 * 500 - sell - (21.05 * 500 + buy), abs=0.01)
    assert t["trigger"] == "weak_stock" and t["excluded"] == ""


def test_a_stock_at_its_1_month_low_on_the_entry_close_exits_that_day():
    inp, cal, sig, entry_i = _synthetic()
    px = np.linspace(1200, 1000, len(cal))                                          # a new low every session
    inp.stock = {"ABC": pd.Series(px, index=pd.to_datetime(cal))}
    trades, _ = s1.run(inp, cal[sig], cal[entry_i + 3])
    t = trades.iloc[0]
    assert t["entry_date"] == t["exit_date"] == cal[entry_i] and t["exit_reason"] == "stock_at_1m_low"


def test_ban_lottery_and_oi_refusals():
    inp, cal, sig, entry_i = _synthetic()
    inp.ban = {cal[sig]: {"ABC"}}
    trades, skips = s1.run(inp, cal[sig], cal[entry_i])
    assert len(trades) == 0 and skips["in_ban"] == 1
    inp, cal, sig, entry_i = _synthetic()
    inp.opens = lambda d: pd.DataFrame([dict(TckrSymb="ABC", XpryDt="2026-10-27", StrkPric=1000.0, OptnTp="PE", OpnPric=1.5)])
    trades, skips = s1.run(inp, cal[sig], cal[entry_i])
    assert skips["lottery_refused"] == 1


def test_summary_per_period():
    t = pd.DataFrame({"entry_date": ["2021-03-01", "2021-03-01", "2023-05-02", "2025-01-10"],
                      "net": [100.0, -50.0, 200.0, -10.0], "cost": [1000.0, 1000.0, 1000.0, 1000.0],
                      "net_return_pct": [10.0, -5.0, 20.0, -1.0], "excluded": ["", "", "", ""],
                      "exit_reason": ["premium_2.5x", "premium_0.5x", "10_sessions", "premium_0.5x"]})
    s = s1.summarise(t).set_index("period")
    assert s.loc["all", "n"] == 4 and s.loc["all", "hit_rate_pct"] == 50.0 and s.loc["all", "net_per_1000"] == 60.0
    assert s.loc["2021-22", "n"] == 2 and s.loc["2021-22", "mean_net_return_pct"] == 2.5
    assert s.loc["all", "exit_premium_0.5x_pct"] == 50.0 and s.loc["2023-24", "exit_10_sessions_pct"] == 100.0
