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
        st.put(24000, 150.0 if t.time() < time(15, 0) else 180.0, 182.0)
    run(tr, D2, time(9, 15), time(9, 18), before=d2)
    assert tr.state["open"] is not None                      # not sold at 09:16 any more (G1 holds to the close)
    run(tr, D2, time(15, 20), time(15, 30), before=d2)
    assert tr.state["open"] is None
    t = tr.state["trades"][0]
    assert t["reason"] == "next close" and t["sold"] == 180.0 and t["sold_at"].startswith("2026-11-06T15:29")
    assert t["gross_rs"] == pytest.approx((180.0 - 100.5) * 65)
    assert t["net_rs"] < t["gross_rs"] and t["max_up_pct"] > 70
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


def test_missed_close_sells_at_the_first_bid_next_session(g1):
    tr, st = g1
    run(tr, D1, time(9, 15), time(9, 45), before=down_day(st))
    st.spot(23900.0)
    st.put(24000, 120.0, 121.0)
    tr.tick(datetime.combine(D2, time(9, 20), IST))          # first tick of the next session: hold day set
    assert tr.state["open"]["hold_day"] == D2.isoformat()
    d3 = date(2026, 11, 9)                                   # the server was down at D2's close
    st.put(24000, 130.0, 131.0)
    tr.tick(datetime.combine(d3, time(9, 20), IST))
    assert tr.state["open"] is None and "missed" in tr.state["trades"][0]["reason"]


def test_g1_runs_on_an_announced_saturday_session(g1, monkeypatch):
    tr, st = g1
    sat = date(2026, 11, 7)
    monkeypatch.setattr(G.sessions, "special_sessions", lambda: {sat})
    run(tr, sat, time(9, 15), time(9, 45), before=down_day(st))
    assert tr.state["open"] is not None and tr.state["open"]["entry"] == "09:41"


def test_open_position_marks_are_saved_so_a_restart_keeps_the_max_up(g1, tmp_path):
    import json
    tr, st = g1
    run(tr, D1, time(9, 15), time(9, 45), before=down_day(st))
    assert tr.state["open"] is not None

    def d2(t):
        st.spot(24000.0, 24000.0)
        st.put(24000, 160.0 if t.time() < time(11, 0) else 120.0, 162.0)
    run(tr, D2, time(9, 15), time(11, 5), every=20, before=d2)
    saved = json.loads((tmp_path / "g1_ledger.json").read_text(encoding="utf-8"))["open"]
    assert saved["max_bid"] == 160.0 and saved["mark"] == 120.0       # on disk, not only in memory
