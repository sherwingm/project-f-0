"""server/xp_live.py driven tick by tick with a fake stream (no network, no other ledger)."""
from datetime import date, datetime, time, timedelta

import pytest

from server import xp_live as X

IST = X.IST
EXP = date(2026, 11, 10)             # a Tuesday expiry
OTHER = date(2026, 11, 11)


class Stream:
    def __init__(self):
        self.s, self.wanted = {}, set()

    def get(self, key):
        return self.s.get(key)

    def want(self, keys):
        self.wanted.update(keys)

    def spot(self, px, cp=24000.0):
        self.s[X.SPOT_KEY] = {"ltpc": {"ltp": px, "cp": cp}}

    def leg(self, typ, k, bid, ask, ltp=None):
        self.s[f"{typ}{k}"] = {"depth": [(bid, 75, ask, 75)], "ltpc": {"ltp": ltp or (bid + ask) / 2}}


class Upstox:
    _nifty = {(e, typ, float(k)): f"{typ}{k}" for e in (EXP.isoformat(), "2026-11-17")
              for typ in ("CE", "PE") for k in range(23500, 24550, 50)}


@pytest.fixture
def xp(tmp_path, monkeypatch):
    monkeypatch.setattr(X.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(X.alerts, "send", lambda *a, **k: False)
    st = Stream()
    return X.ExpiryStraddleLogger(st, Upstox(), tmp_path), st


def run(lg, day, t0, t1, before, every=10):
    t, end = datetime.combine(day, t0, IST), datetime.combine(day, t1, IST)
    while t <= end:
        before(t)
        lg.tick(t)
        t += timedelta(seconds=every)


def test_buys_atm_straddle_at_0916_asks_and_hits_target(xp):
    lg, st = xp

    def f(t):
        st.spot(24012.0)
        m = t.time()
        up = m >= time(11, 0)
        st.leg("CE", 24000, 61.0 if up else 49.0, 50.0 if not up else 62.0)
        st.leg("PE", 24000, 59.0 if up else 39.0, 40.0 if not up else 60.0)
    run(lg, EXP, time(9, 15), time(15, 16), f)
    t = lg.state["trades"][0]
    assert (t["strike"], t["paid_sum"]) == (24000.0, 90.0)
    assert t["primary"]["exit"] == "+20 % target" and t["primary"]["sold_sum"] == 120.0
    assert t["primary"]["at"].startswith("2026-11-10T11:00")
    assert t["hold_1515"]["at"].startswith("2026-11-10T15:15") and t["hold_1515"]["sold_sum"] == 120.0
    assert t["max_up_pct"] == pytest.approx(33.3, abs=0.1)
    assert lg.state["open"] is None and {"CE24000", "PE24000"} <= st.wanted
    v = lg.view()
    assert v["summary"]["days"] == 1 and v["tracks"][0]["trades"] == 1


def test_no_target_sells_at_1515(xp):
    lg, st = xp

    def f(t):
        st.spot(23990.0)
        late = t.time() >= time(12, 0)
        st.leg("CE", 24000, 20.0 if late else 49.0, 50.0)
        st.leg("PE", 24000, 30.0 if late else 39.0, 40.0)
    run(lg, EXP, time(9, 15), time(15, 20), f)
    t = lg.state["trades"][0]
    assert t["primary"]["exit"] == "15:15" and t["primary"]["sold_sum"] == 50.0
    assert t["primary"]["net_pct"] < -40


def test_not_an_expiry_day_no_trade(xp):
    lg, st = xp
    run(lg, OTHER, time(9, 15), time(9, 30), lambda t: st.spot(24000.0))
    assert lg.state["trades"] == [] and lg.state["open"] is None
    assert "not a NIFTY expiry day" in lg.state["days"][OTHER.isoformat()]["status"]


def test_missing_ask_skips_the_day(xp):
    lg, st = xp

    def f(t):
        st.spot(24000.0)
        st.leg("CE", 24000, 49.0, 50.0)            # no PE quote at all
    run(lg, EXP, time(9, 15), time(9, 20), f)
    assert lg.state["open"] is None and "no ask" in lg.state["days"][EXP.isoformat()]["status"]


def test_ledger_survives_a_restart(xp, tmp_path):
    lg, st = xp

    def f(t):
        st.spot(24000.0)
        st.leg("CE", 24000, 49.0, 50.0)
        st.leg("PE", 24000, 39.0, 40.0)
    run(lg, EXP, time(9, 15), time(9, 30), f)
    again = X.ExpiryStraddleLogger(st, Upstox(), tmp_path)
    assert again.state["open"]["paid_sum"] == 90.0
