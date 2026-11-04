"""server/g1_live.py driven tick by tick with a fake stream (no network, no S1 ledger)."""
from datetime import date, datetime, time, timedelta

import pytest

from server import g1_live as G

IST = G.IST
EXP = "2026-11-10"
D1, D2 = date(2026, 11, 5), date(2026, 11, 6)


class Stream:
    def __init__(self):
        self.s, self.wanted = {}, set()

    def get(self, key):
        return self.s.get(key)

    def want(self, keys):
        self.wanted.update(keys)

    def spot(self, px, cp=24000.0):
        self.s[G.SPOT_KEY] = {"ltpc": {"ltp": px, "cp": cp}}

    def vix(self, v):
        self.s[G.VIX_KEY] = {"ltpc": {"ltp": v}}

    def put(self, k, bid, ask):
        self.s[f"PE{k}"] = {"depth": [(bid, 75, ask, 75)]}


class Upstox:
    _nifty = {(e, "PE", float(k)): f"PE{k}" for e in ("2026-11-03", EXP) for k in range(23500, 24550, 50)}


@pytest.fixture
def g1(tmp_path, monkeypatch):
    monkeypatch.setattr(G.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(G.alerts, "send", lambda *a, **k: False)
    st = Stream()
    return G.G1Trader(st, Upstox(), tmp_path), st


def run(tr, day, t0, t1, every=10, before=None):
    t = datetime.combine(day, t0, IST)
    end = datetime.combine(day, t1, IST)
    while t <= end:
        if before:
            before(t)
        tr.tick(t)
        t += timedelta(seconds=every)


def down_day(st, put_bid=100.0, vix=13.0, cp=24000.0):
    def f(t):
        m = t.time()
        st.vix(vix)
        if m < time(9, 30):
            st.spot(24000.0 if (t.second // 10) % 2 else 24010.0, cp)
        elif m < time(9, 40):
            st.spot(24004.0, cp)
        else:
            st.spot(23990.0, cp)
        st.put(24000, put_bid, put_bid + 0.5)
    return f


def test_buys_at_the_ask_after_a_downside_breakout_and_sells_at_the_next_0916_bid(g1):
    tr, st = g1
    run(tr, D1, time(9, 15), time(9, 45), before=down_day(st))
    o = tr.state["open"]
    assert (o["signal"], o["entry"], o["strike"], o["expiry"], o["paid"]) == ("09:40", "09:41", 24000.0, EXP, 100.5)
    assert o["g1f_skip"] == "" and "G1-F counts it" in tr.state["days"][str(D1)]["status"]

    def d2(t):
        st.spot(23900.0, 23990.0)
        st.put(24000, 150.0 if t.time() < time(9, 16, 50) else 151.0, 152.0)
    run(tr, D2, time(9, 15), time(9, 18), before=d2)
    assert tr.state["open"] is None
    t = tr.state["trades"][0]
    assert t["reason"] == "next open" and t["sold"] == 151.0 and t["sold_at"].startswith("2026-11-06T09:16:5")
    assert t["gross_rs"] == pytest.approx((151.0 - 100.5) * 65)
    assert t["net_rs"] < t["gross_rs"] and t["max_up_pct"] > 49
    v = tr.view()
    assert [x["trades"] for x in v["tracks"]] == [1, 1]
    assert "PE24000" in st.wanted


def test_stop_at_half_the_price_paid_on_day_one(g1):
    tr, st = g1
    run(tr, D1, time(9, 15), time(9, 45), before=down_day(st))

    def drop(t):
        st.spot(24100.0)
        st.put(24000, 45.0, 46.0)
    run(tr, D1, time(11, 0), time(11, 0, 20), before=drop)
    t = tr.state["trades"][0]
    assert (t["reason"], t["sold"]) == ("stop", 45.0) and t["net_pct"] < -50


def test_upward_first_breakout_is_no_trade(g1):
    tr, st = g1

    def up(t):
        st.spot(24005.0 if t.time() < time(9, 40) else 24030.0)
    run(tr, D1, time(9, 15), time(9, 45), before=up)
    assert tr.state["open"] is None and "first breakout up" in tr.state["days"][str(D1)]["status"]


def test_g1f_skip_flags_gap_up_and_high_vix(g1):
    tr, st = g1
    run(tr, D1, time(9, 15), time(9, 45), before=down_day(st, vix=18.0, cp=23900.0))
    o = tr.state["open"]
    assert "day-1 gap" in o["g1f_skip"] and "VIX 18.00" in o["g1f_skip"]
    assert [x["trades"] for x in tr.view()["tracks"]] == [0, 0]


def test_ledger_survives_a_restart(g1, tmp_path):
    tr, st = g1
    run(tr, D1, time(9, 15), time(9, 45), before=down_day(st))
    again = G.G1Trader(st, Upstox(), tmp_path)
    assert again.state["open"]["paid"] == 100.5
