"""G1-C (the call mirror of G1): server/g1c_live.py driven tick by tick with a fake stream; G1 itself must stay a put trader."""
from datetime import date, datetime, time, timedelta

import pytest

from server import g1_live as G
from server.g1c_live import G1CTrader
from tests.test_g1_live import D1, D2, EXP, Stream, run

IST = G.IST


class UpstoxCE:
    _nifty = {**{(e, "PE", float(k)): f"PE{k}" for e in ("2026-11-03", EXP) for k in range(23500, 24550, 50)},
              **{(e, "CE", float(k)): f"CE{k}" for e in ("2026-11-03", EXP) for k in range(23500, 24550, 50)}}


def put_call(st, k, bid, ask, opt="CE"):
    st.s[f"{opt}{k}"] = {"depth": [(bid, 75, ask, 75)]}


def up_day(st, bid=100.0):
    def f(t):
        m = t.time()
        st.vix(13.0)
        if m < time(9, 30):
            st.spot(24000.0 if (t.second // 10) % 2 else 24010.0)
        elif m < time(9, 40):
            st.spot(24004.0)
        else:
            st.spot(24020.0)                    # first close above the high (24010) at 09:40; ATM stays 24000
        put_call(st, 24000, bid, bid + 0.5)
    return f


def down_day(st):
    def f(t):
        m = t.time()
        st.vix(13.0)
        if m < time(9, 30):
            st.spot(24000.0 if (t.second // 10) % 2 else 24010.0)
        elif m < time(9, 40):
            st.spot(24004.0)
        else:
            st.spot(23990.0)
        put_call(st, 24000, 100.0, 100.5)
        put_call(st, 24000, 100.0, 100.5, "PE")
    return f


@pytest.fixture
def gc(tmp_path, monkeypatch):
    monkeypatch.setattr(G.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(G.alerts, "send", lambda *a, **k: False)
    st = Stream()
    return G1CTrader(st, UpstoxCE(), tmp_path), st


def test_buys_the_atm_call_at_the_ask_after_an_upside_breakout(gc):
    tr, st = gc
    run(tr, D1, time(9, 15), time(9, 45), before=up_day(st))
    o = tr.state["open"]
    assert (o["signal"], o["entry"], o["strike"], o["expiry"], o["paid"], o["key"]) == ("09:40", "09:41", 24000.0, EXP, 100.5, "CE24000")
    assert o["g1f_skip"] == "" and "score" not in o                       # no filters, no score
    assert "bought" in tr.state["days"][str(D1)]["status"] and "24000 CE" in tr.state["days"][str(D1)]["status"]
    assert tr.view()["opt"] == "CE" and [t["pod"] for t in tr.view()["tracks"]] == ["G1-C (call mirror)"]


def test_a_downside_first_break_is_no_g1c_trade(gc):
    tr, st = gc
    run(tr, D1, time(9, 15), time(9, 45), before=down_day(st))
    assert tr.state["open"] is None and "first breakout down" in tr.state["days"][str(D1)]["status"]


def test_holds_to_next_close_and_stops_at_half(gc, tmp_path):
    tr, st = gc
    run(tr, D1, time(9, 15), time(9, 45), before=up_day(st))

    def d2(t):
        st.spot(24100.0)
        put_call(st, 24000, 150.0 if t.time() < time(15, 0) else 180.0, 182.0)
    run(tr, D2, time(9, 15), time(9, 18), before=d2)
    assert tr.state["open"] is not None
    run(tr, D2, time(15, 20), time(15, 30), before=d2)
    t = tr.state["trades"][0]
    assert t["reason"] == "next close" and t["sold"] == 180.0 and t["max_up_pct"] > 70
    assert (tmp_path / "g1c_ledger.json").exists() and not (tmp_path / "g1_ledger.json").exists()


def test_stop_on_day_one(gc):
    tr, st = gc
    run(tr, D1, time(9, 15), time(9, 45), before=up_day(st))

    def drop(t):
        st.spot(23900.0)
        put_call(st, 24000, 45.0, 46.0)
    run(tr, D1, time(11, 0), time(11, 0, 20), before=drop)
    t = tr.state["trades"][0]
    assert (t["reason"], t["sold"]) == ("stop", 45.0) and t["net_pct"] < -50


def test_g1_is_still_a_put_trader_and_ignores_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(G.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(G.alerts, "send", lambda *a, **k: False)
    st = Stream()
    g1 = G.G1Trader(st, UpstoxCE(), tmp_path)
    assert g1.OPT == "PE" and G1CTrader.OPT == "CE"
    run(g1, D1, time(9, 15), time(9, 45), before=up_day(st))
    assert g1.state["open"] is None and "first breakout up" in g1.state["days"][str(D1)]["status"]     # an up-break is still no G1 trade
