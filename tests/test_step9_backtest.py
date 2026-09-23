"""Step 9: the cheap-option backtest on three sessions of synthetic bhavcopies (no network).

Stock ABC, lot 100, expiry on the third session. Mon 21 Sep: the 110 call closes at Rs 1.00, the 90 put at Rs 0.50.
Wed 23 Sep (expiry, 2 sessions later): the call closes at Rs 3.00, the put at Rs 0.05, ABC at Rs 114.
By hand, with one tick (0.05) against each trade:
    call cost   1.05 x 100 = 105.00 + buy charges 23.65 (20 brokerage, 0.04 NSE, 3.61 GST)    = 128.65
    (a) exit    2.95 x 100 = 295.00 - sell charges 24.16 (20 + 0.44 STT + 0.10 NSE + 3.62 GST) = 270.84 -> x 2.105
    (b) expiry  intrinsic 114 - 110 = 4 -> 400.00 - exercise STT 0.60                        = 399.40 -> x 3.105
    put         0.55 x 100 = 55.00 + 23.61 = 78.61; exit price 0.05 - 0.05 = 0 lapses; intrinsic 0 -> x 0
"""
from datetime import date

import pandas as pd
import pytest

from scanner.backtest_cheap_options import Inputs, print_table, run, sessions_to, summarise
from scanner.classify import BULLISH
from server import charges as ch

D0, D1, D2 = date(2026, 9, 21), date(2026, 9, 22), date(2026, 9, 23)
FAR = "2026-10-27"


def rows(day, call110, put90, spot, extra=()):
    base = dict(TradDt=day.isoformat(), TckrSymb="ABC", UndrlygPric=spot, ChngInOpnIntrst=0, NewBrdLotQty=100)
    r = [dict(base, FinInstrmTp="STF", XpryDt=D2.isoformat(), StrkPric=0, OptnTp=None, ClsPric=spot, OpnIntrst=100_000,
              ChngInOpnIntrst=10_000, TtlTradgVol=1000),
         dict(base, FinInstrmTp="STO", XpryDt=D2.isoformat(), StrkPric=110, OptnTp="CE", ClsPric=call110, OpnIntrst=50_000, TtlTradgVol=500),
         dict(base, FinInstrmTp="STO", XpryDt=D2.isoformat(), StrkPric=90, OptnTp="PE", ClsPric=put90, OpnIntrst=40_000, TtlTradgVol=0),
         dict(base, FinInstrmTp="STO", XpryDt=D2.isoformat(), StrkPric=100, OptnTp="CE", ClsPric=5.5, OpnIntrst=1_000, TtlTradgVol=10),
         dict(base, FinInstrmTp="STO", XpryDt=FAR, StrkPric=130, OptnTp="CE", ClsPric=0.3, OpnIntrst=1_000, TtlTradgVol=10)]
    return pd.DataFrame(r + list(extra))


BHAV = {D0: rows(D0, 1.00, 0.50, 105.0), D1: rows(D1, 2.00, 0.30, 110.0), D2: rows(D2, 3.00, 0.05, 114.0)}


def equity(sym):
    days = pd.bdate_range(end=pd.Timestamp(D0), periods=30)
    close = [100.0] * 29 + [105.0]                  # up 5% on the day
    vol = [1000.0] * 29 + [3000.0]                  # 3x its 20-day average
    return pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close, "Volume": vol}, index=days)


@pytest.fixture
def result():
    inp = Inputs(sessions=[D0, D1, D2], bhav=BHAV.get, equity=equity, lots={"ABC": 100})
    return run(inp, D0, D0, max_premium=2.0, dte=(2, 2), hold=2)


def test_sessions_to_expiry_counts_the_calendar_then_weekdays():
    cal = [D0, D1, D2]
    assert sessions_to(cal, D0, D2) == 2 and sessions_to(cal, D2, D2) == 0
    assert sessions_to(cal, D0, date(2026, 9, 28)) == 5        # D1, D2, then Thu, Fri, Mon past the calendar


def test_only_cheap_contracts_in_the_expiry_window_are_kept(result):
    assert sorted(result["contract"]) == ["ABC26SEP110CE", "ABC26SEP90PE"]        # 5.50 too dear; Oct too far
    assert set(result["label"]) == {BULLISH}                                       # up 5%, 3x volume, OI rising
    r = result.set_index("type")
    assert r.loc["CE", "spot"] == 105.0 and r.loc["CE", "dte"] == 2 and r.loc["CE", "lot"] == 100


def test_call_multiples_by_hand(result):
    c = result.set_index("type").loc["CE"]
    buy = ch.leg("CE", "BUY", 100, 1.05)["total"]
    sell = ch.leg("CE", "SELL", 100, 2.95)["total"]
    assert buy == pytest.approx(23.65) and sell == pytest.approx(24.16)
    assert c["cost"] == pytest.approx(128.65)
    assert c["exit_close"] == 3.0 and c["exit_payoff"] == pytest.approx(270.84)
    assert c["exit_net"] == pytest.approx(142.19) and c["exit_multiple"] == pytest.approx(270.84 / 128.65, abs=1e-4)
    assert c["intrinsic"] == 4.0 and c["expiry_payoff"] == pytest.approx(399.40)
    assert c["expiry_multiple"] == pytest.approx(399.40 / 128.65, abs=1e-4)


def test_put_that_expires_worthless_lapses(result):
    p = result.set_index("type").loc["PE"]
    assert p["cost"] == pytest.approx(55.0 + ch.leg("PE", "BUY", 100, 0.55)["total"])
    assert p["exit_payoff"] == 0 and p["exit_multiple"] == 0 and p["exit_net"] == pytest.approx(-p["cost"])
    assert p["intrinsic"] == 0 and p["expiry_payoff"] == 0


def test_summary_groups_and_binomial_lines(result, capsys):
    s = summarise(result, (2, 2))
    by = {r["group"]: r for r in s["exit"]}
    assert by["all cheap calls"]["count"] == 1 and by["all cheap calls"]["wins"] == 1
    assert by["calls on Bullish-labelled stocks"]["count"] == 1
    assert by["all cheap puts"]["count"] == 1 and by["all cheap puts"]["pct_positive"] == 0
    assert by["puts on Bearish-labelled stocks"]["count"] == 0
    assert by["calls, 2 sessions to expiry"]["mean_multiple"] == pytest.approx(2.1053, abs=1e-3)
    assert by["all cheap calls"]["net_per_1000"] == pytest.approx(142.19 / 128.65 * 1000, abs=0.1)
    assert "31/50, 59/100, 112/200, 217/400" in by["all cheap calls"]["binomial"]
    print_table(s, hold=2)
    out = capsys.readouterr().out
    assert "(a) sell at the option's close 2 sessions later" in out and "(b) hold to expiry" in out


def test_missing_outcome_data_is_left_blank_not_guessed():
    inp = Inputs(sessions=[D0, D1, D2], bhav=lambda d: BHAV[D0] if d == D0 else None, equity=equity, lots={})
    r = run(inp, D0, D0, max_premium=2.0, dte=(2, 2), hold=2)
    assert r["exit_net"].isna().all() and r["expiry_net"].isna().all()
