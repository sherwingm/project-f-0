"""S1 forward paper test: one session at a time — signal, next-session fill, marking with stop / 5-session decay /
T-1, the after-exit tracking, refusals, cooldown and the peak/dip stats."""
from collections import Counter
from datetime import date, timedelta

import pandas as pd
import pytest

from scanner import forward_s1 as fw
from scanner.backtest_s1_v2 import Inputs, Market

EXPIRY, NEXT = "2026-10-27", "2026-11-24"


def weekdays(a: date, b: date) -> list[str]:
    out, d = [], a
    while d <= b:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


CAL = weekdays(date(2026, 6, 1), date(2026, 10, 23))
I0 = CAL.index("2026-10-13")


def closes(daily: float, jump: float = 0.0) -> pd.Series:
    vals, v = [], 100.0
    for i, _ in enumerate(CAL):
        v *= 1 + daily + (jump if i == I0 else 0.0)
        vals.append(v)
    return pd.Series(vals, index=pd.to_datetime(CAL))


@pytest.fixture
def m():
    peers = {f"P{k}": closes(0.003) for k in range(4)}          # the sector outruns a flat NIFTY 500: arm B is open
    stock = {"STK": closes(0.003, jump=0.035), "OTH": closes(0.0, jump=0.03)}   # OTH has no sector -> NIFTY 500
    sector_of = {**{p: "nifty it" for p in peers}, "STK": "nifty it"}
    return Market(Inputs(cal=CAL, bhav=lambda d: None, opens=lambda d: None, stock={**peers, **stock},
                         sector_of=sector_of, bench=closes(0.0)))


def day(calls: dict[str, float], strikes=(95.0, 100.0, 105.0, 110.0)) -> dict:
    chain = pd.DataFrame({"XpryDt": [EXPIRY] * len(strikes) + [NEXT] * len(strikes), "StrkPric": list(strikes) * 2})
    return {"calls": {(s, EXPIRY, 100.0): c for s, c in calls.items()}, "futs": {},
            "spot": {"STK": 100.0, "OTH": 100.0}, "chain": {"STK": chain, "OTH": chain}}


def prices(sym="STK", close=10.0, contracts=200, lot=500) -> pd.DataFrame:
    return pd.DataFrame({"TckrSymb": [sym], "XpryDt": [EXPIRY], "OptnTp": ["CE"], "StrkPric": [100.0],
                         "TtlTradgVol": [contracts], "TtlTrfVal": [0.0], "NewBrdLotQty": [lot], "ClsPric": [close],
                         "LwPric": [close], "HghPric": [close]})


CAT = lambda s, d: ("large", None)                                # noqa: E731
RESULTS = [("STK", "2026-10-13", "08:00"), ("OTH", "2026-10-13", "08:00")]


def run_days(state, m, seq):
    for session, calls, px in seq:
        fw.step(state, session, m, day(calls), px, RESULTS, set(), CAT)


def test_signal_then_next_session_fill(m):
    st = fw.empty_state()
    fw.step(st, "2026-10-13", m, day({}), None, RESULTS, set(), CAT)
    a, b = st["arms"]["A"], st["arms"]["B"]
    assert {p["symbol"] for p in a["pending"]} == {"STK", "OTH"}
    assert [p["symbol"] for p in b["pending"]] == ["STK"]                       # OTH has no sector: not in B
    assert a["pending"][0]["expiry"] == EXPIRY                                    # >= 2 sessions left
    fw.step(st, "2026-10-14", m, day({"STK": 10.0}), prices(), RESULTS, set(), CAT)
    t = next(x for x in a["open"] if x["symbol"] == "STK")
    assert (t["entry_date"], t["strike"], t["entry_price"], t["cost"]) == ("2026-10-14", 100.0, 10.05, 5025.0)
    assert t["path"] == [["2026-10-14", 10.0]] and a["pending"] == []
    assert any(r["symbol"] == "OTH" and "no strike" in r["reason"] for r in a["refused"])   # OTH has no prices row


def test_stop_then_after_exit_tracking_until_t_minus_1(m):
    st = fw.empty_state()
    run_days(st, m, [("2026-10-13", {}, None), ("2026-10-14", {"STK": 12.0}, prices()),
                     ("2026-10-15", {"STK": 5.0}, None), ("2026-10-16", {"STK": 30.0}, None),
                     ("2026-10-19", {"STK": 2.0}, None)])
    t = next(x for x in st["arms"]["A"]["closed"] if x["symbol"] == "STK")
    assert (t["exit_date"], t["exit_reason"], t["exit_price"]) == ("2026-10-15", "0_stop", 4.95)
    assert t["net"] < 0 and t["tracking"]
    s = fw.stats(t)
    assert (s["h_peak"], s["h_peak_date"]) == (pytest.approx(19.4, abs=0.1), "2026-10-14")
    assert s["a_peak"] == pytest.approx(198.51, abs=0.1) and s["a_peak_date"] == "2026-10-16" and s["above_exit"]
    assert s["a_dip"] == pytest.approx(-80.1, abs=0.1)


def test_five_sessions_without_a_new_high_and_cooldown(m):
    st = fw.empty_state()
    seq = [("2026-10-13", {}, None), ("2026-10-14", {"STK": 11.0}, prices())]
    seq += [(d, {"STK": 10.5}, None) for d in ("2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20")]
    run_days(st, m, seq)
    assert st["arms"]["A"]["open"][0]["stall"] == 4
    run_days(st, m, [("2026-10-21", {"STK": 10.4}, None)])
    t = st["arms"]["A"]["closed"][-1]
    assert t["exit_reason"] == "1_decay" and t["exit_date"] == "2026-10-21"
    pos = {d: i for i, d in enumerate(CAL)}
    assert fw.blocked(st["arms"]["A"], "STK", pos["2026-10-22"], pos)         # inside the 10-session cooldown


def test_ban_and_band_refusals(m):
    st = fw.empty_state()
    fw.step(st, "2026-10-13", m, day({}), None, RESULTS, set(), CAT)
    fw.step(st, "2026-10-14", m, day({}), prices(close=40.0), RESULTS, {"OTH"}, CAT)    # STK lot Rs 20,025
    reasons = {r["symbol"]: r["reason"] for r in st["arms"]["A"]["refused"]}
    assert "ban" in reasons["OTH"] and "Rs 600-8,000" in reasons["STK"]
    assert st["arms"]["A"]["open"] == []


def test_a_missing_contract_is_excluded(m):
    st = fw.empty_state()
    run_days(st, m, [("2026-10-13", {}, None), ("2026-10-14", {"STK": 10.0}, prices()), ("2026-10-15", {}, None)])
    t = next(x for x in st["arms"]["A"]["closed"] if x["symbol"] == "STK")
    assert t["excluded"] == "contract_changed" and t["net"] is None


def test_new_signals_only_for_the_session(m):
    st = fw.empty_state()
    added = fw.new_signals(st, "2026-10-14", m, RESULTS, day({}), Counter())
    assert added == []                                                            # day 0 was the 13th


def test_a_quiet_results_day_is_skipped(m):
    import numpy as np
    st = fw.empty_state()
    m.day_range = {"STK": np.full(len(CAL), 2.5), "OTH": np.full(len(CAL), 6.0)}
    fw.step(st, "2026-10-13", m, day({}), None, RESULTS, set(), CAT)
    a = st["arms"]["A"]
    assert [p["symbol"] for p in a["pending"]] == ["OTH"]
    assert any(r["symbol"] == "STK" and "quiet results day" in r["reason"] for r in a["refused"])
    assert st["arms"]["B"]["pending"] == []                      # STK was arm B's only signal


def test_day_range_is_in_percent_of_the_previous_close():
    import pandas as pd
    f = pd.DataFrame({"High": [101.0, 106.0], "Low": [99.0, 100.0], "Close": [100.0, 104.0]},
                     index=pd.to_datetime(["2026-10-12", "2026-10-13"]))
    r = fw.day_range(f, ["2026-10-12", "2026-10-13"])
    assert r[1] == 6.0 and r[0] != r[0]                          # (106 - 100) / 100; the first day has no previous close


# ---------------------------------------------------------------- expiry rule from 2026-10-17: >= 2 sessions left
def test_current_monthly_kept_while_two_sessions_remain_holidays_counted():
    exps = ["2026-10-27", "2026-11-23", "2026-12-29"]
    assert fw.choose_expiry(exps, date(2026, 10, 16)) == ("2026-10-27", 6)     # 19, 21, 22, 23, 26, 27 (20 Oct holiday)
    assert fw.choose_expiry(exps, date(2026, 10, 23)) == ("2026-10-27", 2)     # 26, 27: still the current monthly
    assert fw.choose_expiry(exps, date(2026, 10, 26))[0] == "2026-11-23"       # 1 session left: the next monthly
    assert fw.choose_expiry(["2026-10-27"], date(2026, 10, 26)) is None


def test_repick_moves_a_pending_signal_to_the_current_monthly():
    st = fw.empty_state()
    chain = pd.DataFrame({"XpryDt": ["2026-10-27"] * 2 + ["2026-11-23"] * 2, "StrkPric": [100.0, 105.0, 110.0, 120.0]})
    st["arms"]["A"]["pending"].append({"arm": "A", "symbol": "STK", "signal_date": "2026-10-16", "expiry": "2026-11-23",
                                       "spot": 101.0, "strikes": [110.0, 120.0], "open_strike": 110.0})
    st["arms"]["A"]["pending"].append({"arm": "A", "symbol": "OLD", "signal_date": "2026-10-15", "expiry": "2026-11-23"})
    changed = fw.repick(st, "2026-10-16", {"chain": {"STK": chain, "OLD": chain}}, None)
    p, old = st["arms"]["A"]["pending"]
    assert [c["symbol"] for c in changed] == ["STK"] and p["expiry"] == "2026-10-27" and p["strikes"] == [100.0, 105.0]
    assert p["open_strike"] is None and "2026-11-23 -> 2026-10-27" in p["expiry_repicked"]
    assert old["expiry"] == "2026-11-23"                                       # another session's signal: untouched
