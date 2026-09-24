"""Label backtest on synthetic eod2 frames and bhavcopies (no network).

40 sessions; bhavcopies cached for sessions 30, 31 and 38; horizon 3; NIFTY 100 until session 31, then 101 (+1%).
    ABC  s30: +5% on 3x volume, OI rising -> Bullish; s33 close +3% -> move 3 - 1 = +2.0 -> hit at 1%
         s31: +1% on high volume again   -> Bullish, within 3 sessions of s30 -> duplicate
    XYZ  s30: -5% on 3x volume, OI rising -> Bearish; s33 close +3% -> move +2.0 -> miss
         s31: flat -> Neutral; s34 close +3% vs s31 -> move +2.0
    NEU  s30: +2% on average volume -> Neutral; s33 +3.5% -> move +2.5; s31 flat -> Neutral, duplicate
    s38: everything Neutral, horizon past the data -> pending
"""
from datetime import date

import pandas as pd
import pytest

from scanner.backtest_labels import print_table, run, summarise
from scanner.classify import BEARISH, BULLISH, NEUTRAL

T = pd.bdate_range("2026-07-01", periods=40)
CAL = [t.date() for t in T]
DAYS = [CAL[30], CAL[31], CAL[38]]
INDEX = pd.Series([100.0] * 32 + [101.0] * 8, index=T)


def series(before, path, vol_at=()):
    close = [before] * 30 + path + [path[-1]] * (10 - len(path))
    vol = [1000.0] * 40
    for i in vol_at:
        vol[i] = 3000.0
    return pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close, "Volume": vol}, index=T)


FRAMES = {"ABC": series(100.0, [105.0, 106.05, 106.05, 108.15], vol_at=(30, 31)),
          "XYZ": series(100.0, [95.0, 95.0, 95.0, 97.85, 97.85], vol_at=(30,)),
          "NEU": series(100.0, [102.0, 102.0, 102.0, 105.57])}


def bhav(day):
    rows = []
    for s in FRAMES:
        rows += [dict(TckrSymb=s, FinInstrmTp="STF", OptnTp=None, OpnIntrst=110_000, ChngInOpnIntrst=10_000, TtlTradgVol=100),
                 dict(TckrSymb=s, FinInstrmTp="STO", OptnTp="CE", OpnIntrst=1_000, ChngInOpnIntrst=0, TtlTradgVol=10),
                 dict(TckrSymb=s, FinInstrmTp="STO", OptnTp="PE", OpnIntrst=1_000, ChngInOpnIntrst=0, TtlTradgVol=10)]
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def df():
    return run(DAYS, CAL, bhav, FRAMES.get, sorted(FRAMES), INDEX, horizon=3)


def at(df, i, sym):
    return df[(df["date"] == CAL[i].isoformat()) & (df["symbol"] == sym)].iloc[0]


def test_labels_and_market_adjusted_moves(df):
    assert len(df) == 9
    assert at(df, 30, "ABC")["label"] == BULLISH and at(df, 30, "ABC")["move"] == pytest.approx(2.0)
    assert at(df, 31, "ABC")["label"] == BULLISH
    assert at(df, 30, "XYZ")["label"] == BEARISH and at(df, 30, "XYZ")["move"] == pytest.approx(2.0)
    assert at(df, 31, "XYZ")["label"] == NEUTRAL and at(df, 31, "XYZ")["move"] == pytest.approx(2.0)
    assert at(df, 30, "NEU")["label"] == NEUTRAL and at(df, 30, "NEU")["move"] == pytest.approx(2.5)
    assert df[df["date"] == CAL[38].isoformat()]["move"].isna().all()


def test_scored_by_the_page_rules(df):
    s = {r["group"]: r for r in summarise(df, CAL, threshold=1.0)}
    bull, bear = s["Bullish setup"], s["Bearish setup"]
    assert (bull["stock_days"], bull["n"], bull["hits"], bull["dup"]) == (2, 1, 1, 1)
    assert (bear["n"], bear["hits"], bear["hit_pct"]) == (1, 0, 0.0)
    nb, nd = s["Neutral scored as if bullish (base rate)"], s["Neutral scored as if bearish (base rate)"]
    assert (nb["stock_days"], nb["n"], nb["hits"], nb["dup"], nb["pending"]) == (6, 2, 2, 1, 3)
    assert (nd["n"], nd["hits"]) == (2, 0)
    assert "here 1/1, needs 2: does not clear it" in bull["binomial"]


def test_moves_within_the_threshold_are_not_scored(df):
    s = {r["group"]: r for r in summarise(df, CAL, threshold=2.0)}
    assert s["Bullish setup"]["small"] == 1 and s["Bullish setup"]["n"] == 0 and s["Bullish setup"]["hit_pct"] is None
    assert s["Neutral scored as if bullish (base rate)"]["n"] == 1                 # NEU's +2.5 still counts


def test_table_prints(df, capsys):
    print_table(summarise(df, CAL, threshold=1.0), 1.0, 3)
    out = capsys.readouterr().out
    assert "Bullish setup" in out and "Neutral scored as if bearish (base rate)" in out and "hits needed" in out


def test_rows_carry_the_inputs_and_both_returns(df):
    r = at(df, 30, "ABC")
    assert r["price_change_pct"] == 5.0 and r["volume_ratio"] == 3.0 and r["pcr"] == 1.0
    assert r["oi_change_pct"] == pytest.approx(10.0)
    assert r["fwd_return"] == pytest.approx(3.0) and r["nifty_fwd_return"] == pytest.approx(1.0)
    assert r["move"] == pytest.approx(r["fwd_return"] - r["nifty_fwd_return"])


def test_annotate_marks_scored_rows_and_reasons(df):
    from scanner.backtest_labels import annotate
    a = annotate(df, CAL, threshold=1.0)
    row = lambda i, s: a[(a["date"] == CAL[i].isoformat()) & (a["symbol"] == s)].iloc[0]
    assert (row(30, "ABC")["scored"], row(30, "ABC")["hit"]) == ("Y", "Y")
    assert (row(31, "ABC")["scored"], row(31, "ABC")["scored_reason"], row(31, "ABC")["hit"]) == ("N", "dup", "")
    assert (row(30, "XYZ")["scored"], row(30, "XYZ")["hit"]) == ("Y", "N")
    assert row(30, "NEU")["scored_reason"] == "neutral" and row(30, "NEU")["scored"] == "N"
    assert annotate(df, CAL, threshold=2.0).pipe(lambda x: x[(x["date"] == CAL[30].isoformat()) & (x["symbol"] == "ABC")])[
        "scored_reason"].iloc[0] == "small"


def test_versus_base_and_z():
    from scanner.backtest_labels import two_prop_z
    assert two_prop_z(60, 100, 50, 100) == pytest.approx(1.421, abs=0.001)
    assert two_prop_z(1, 1, 2, 2) is None and two_prop_z(0, 0, 5, 10) is None


def test_versus_base_rows(df):
    from scanner.backtest_labels import versus_base
    rows = {(r["label"], r["threshold_pct"]): r for r in versus_base(df, CAL, [1.0])}
    bull = rows[(BULLISH, 1.0)]
    assert (bull["scored_n"], bull["hits"], bull["hit_pct"], bull["base_n"], bull["base_hit_pct"]) == (1, 1, 100.0, 2, 100.0)
    assert bull["diff_pts"] == 0.0 and bull["needs_vs_coin"] == 2
    bear = rows[(BEARISH, 1.0)]
    assert (bear["hits"], bear["base_hits"], bear["base_n"]) == (0, 0, 2)


def test_returns_at_1_3_5_sessions_vs_neutral(df):
    from scanner.backtest_labels import returns_vs_base
    abc30 = at(df, 30, "ABC")
    assert (abc30["adj_1"], abc30["adj_3"], abc30["adj_5"]) == (pytest.approx(1.0), pytest.approx(2.0), pytest.approx(2.0))
    assert at(df, 31, "ABC")["adj_1"] == pytest.approx(-1.0)                   # flat stock, NIFTY +1% on s32
    rows = {(r["label"], r["horizon_sessions"]): r for r in returns_vs_base(df, CAL)}
    b1, b3 = rows[(BULLISH, 1)], rows[(BULLISH, 3)]
    assert b1["n_returns"] == 2 and b1["mean_adj_return"] == pytest.approx(0.0)        # s30 and s31 both kept at h=1
    assert b3["n_returns"] == 1 and b3["mean_adj_return"] == pytest.approx(2.0)        # s31 overlaps s30 at h=3
    assert b3["base_n_returns"] == 2 and b3["base_mean_adj_return"] == pytest.approx(2.25)  # NEU +2.5, XYZ s31 +2.0
    assert b3["diff_mean"] == pytest.approx(-0.25) and b3["t_mean"] is None               # one value: no t
