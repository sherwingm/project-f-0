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
