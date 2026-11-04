"""server/nt_live.py (NT Near Tighty) driven tick by tick with a fake stream: G1's rules plus 1-3 sessions to expiry,
its own ledger and its own page."""
from datetime import date, time

import pytest

from server import g1_live as G
from server import nt_live as N
from tests.test_g1_live import EXP, Stream, down_day, run

D1, D2 = date(2026, 11, 5), date(2026, 11, 6)        # Thu; expiry Tue 10 Nov = 3 sessions after D1 (6, 9, 10)
FAR = "2026-11-17"                                     # 8 sessions after D1


def upstox(*expiries):
    class U:
        _nifty = {(e, "PE", float(k)): f"PE{k}" for e in expiries for k in range(23500, 24550, 50)}
    return U()


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(G.sessions, "is_session", lambda d, hol=None: d.weekday() < 5)
    monkeypatch.setattr(G.sessions, "holidays", lambda: set())
    sent = []
    monkeypatch.setattr(G.alerts, "send", lambda msg, **k: sent.append(msg) or False)
    return tmp_path, Stream(), sent


def test_trades_when_expiry_is_1_to_3_sessions_away_in_its_own_ledger(env):
    tmp, st, sent = env
    nt = N.NearTightyTrader(st, upstox("2026-11-03", EXP), tmp)
    run(nt, D1, time(9, 15), time(9, 45), before=down_day(st))
    o = nt.state["open"]
    assert (o["entry"], o["strike"], o["expiry"], o["paid"]) == ("09:41", 24000.0, EXP, 100.5)
    assert "G1-F" not in nt.state["days"][str(D1)]["status"]
    assert (tmp / "nt_ledger.json").exists() and not (tmp / "g1_ledger.json").exists()
    assert sent and sent[0].startswith("🟢 Near Tighty paper: bought")

    def d2(t):
        st.spot(23900.0, 23990.0)
        st.put(24000, 151.0, 152.0)
    run(nt, D2, time(9, 15), time(9, 18), before=d2)
    t = nt.state["trades"][0]
    assert t["reason"] == "next open" and t["sold"] == 151.0
    v = nt.view()
    assert v["page"] == "strategies/NT_near_tighty.md" and v["near"] == [1, 3]
    assert [(x["pod"], x["trades"]) for x in v["tracks"]] == [("Near Tighty", 1)]


def test_no_trade_when_the_nearest_expiry_is_4_or_more_sessions_away(env):
    tmp, st, _ = env
    nt = N.NearTightyTrader(st, upstox(FAR), tmp)
    run(nt, D1, time(9, 15), time(9, 45), before=down_day(st))
    assert nt.state["open"] is None
    s = nt.state["days"][str(D1)]["status"]
    assert "8 sessions away" in s and "1-3 sessions" in s


def test_g1_still_trades_the_far_expiry_day(env):
    tmp, st, _ = env
    g1 = G.G1Trader(st, upstox(FAR), tmp)
    run(g1, D1, time(9, 15), time(9, 45), before=down_day(st))
    assert g1.state["open"]["expiry"] == FAR


def test_ledger_epoch_is_its_own(env):
    tmp, st, _ = env
    (tmp / "nt_ledger.json").write_text('{"epoch": "2026-11-05 G1 live paper", "open": {"x": 1}, "trades": [], "days": {}}')
    nt = N.NearTightyTrader(st, upstox(EXP), tmp)
    assert nt.state["open"] is None and nt.state["epoch"] == N.NearTightyTrader.EPOCH


def test_page_and_api():
    from server import nt_pages
    assert "Near Tighty" in nt_pages.near_tighty_page()
    assert "error" in nt_pages.near_tighty_api() or "tracks" in nt_pages.near_tighty_api()
