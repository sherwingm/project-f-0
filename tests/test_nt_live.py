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


def test_index_page_shows_near_tighty_and_there_is_no_separate_page():
    from pathlib import Path

    from server import index_api
    html = (Path(__file__).resolve().parents[1] / "templates" / "index_trading.html").read_text(encoding="utf-8")
    assert "/api/index/nt" in html and "/api/index/nt_sensex" in html and 'ntSection(D.nt, "NIFTY")' in html
    assert 'ntSection(D.nts, "SENSEX")' in html
    root = Path(__file__).resolve().parents[1]
    assert not (root / "templates" / "near_tighty.html").exists() and not (root / "server" / "nt_pages.py").exists()
    for fn in (index_api.nt, index_api.nt_sensex):          # not running in a test: a plain message, never a crash
        assert "error" in fn() or "tracks" in fn()
    for page in ("results.html", "s2.html"):
        assert "/near-tighty" not in (root / "templates" / page).read_text(encoding="utf-8")


# ---------------------------------------------------------------- Near Tighty on SENSEX
SX_SPOT = "BSE_INDEX|SENSEX"


class SxUpstox:
    """The Upstox client as the SENSEX trader sees it: the contract map, the lot per expiry, ensure_sensex."""
    def __init__(self, *expiries, lot=20):
        self._sensex = {(e, "PE", float(k)): f"SX{e}{k}" for e in expiries for k in range(77000, 81100, 100)}
        self._sensex_lot = {e: lot for e in expiries}
        self.ensured = []

    def ensure_sensex(self, today):
        self.ensured.append(today)


def sx_down_day(st, put_bid=300.0, vix=13.0, cp=79000.0, expiry=EXP):
    def f(t):
        m = t.time()
        st.s[G.VIX_KEY] = {"ltpc": {"ltp": vix}}
        px = (79000.0 if (t.second // 10) % 2 else 79050.0) if m < time(9, 30) else (79020.0 if m < time(9, 40) else 78950.0)
        st.s[SX_SPOT] = {"ltpc": {"ltp": px, "cp": cp}}
        for k in range(78800, 79300, 100):
            st.s[f"SX{expiry}{k}"] = {"depth": [(put_bid, 75, put_bid + 1.0, 75)]}
    return f


def test_sensex_trades_near_expiry_in_its_own_ledger(env):
    tmp, st, sent = env
    up = SxUpstox("2026-11-03", EXP)
    sx = N.NearTightySensexTrader(st, up, tmp)
    run(sx, D1, time(9, 15), time(9, 45), before=sx_down_day(st))
    o = sx.state["open"]
    assert (o["entry"], o["strike"], o["expiry"], o["paid"], o["qty"]) == ("09:41", 79000.0, EXP, 301.0, 20)
    assert "SENSEX" in sx.state["days"][str(D1)]["status"]
    assert (tmp / "nt_sensex_ledger.json").exists() and not (tmp / "nt_ledger.json").exists()
    assert sent and sent[0].startswith("🟢 Near Tighty SENSEX paper: bought SENSEX")
    assert up.ensured and f"SX{EXP}79000" in st.wanted and SX_SPOT in st.wanted

    def d2(t):
        st.s[SX_SPOT] = {"ltpc": {"ltp": 78500.0, "cp": 78950.0}}
        st.s[f"SX{EXP}79000"] = {"depth": [(450.0, 75, 451.0, 75)]}
    run(sx, D2, time(9, 15), time(9, 18), before=d2)
    t = sx.state["trades"][0]
    assert t["reason"] == "next open" and t["sold"] == 450.0 and t["qty"] == 20
    v = sx.view()
    assert v["index"] == "SENSEX" and v["near"] == [1, 3]
    assert [(x["pod"], x["trades"]) for x in v["tracks"]] == [("Near Tighty SENSEX", 1)]


def test_sensex_no_trade_when_the_nearest_expiry_is_4_or_more_sessions_away(env):
    tmp, st, _ = env
    sx = N.NearTightySensexTrader(st, SxUpstox(FAR), tmp)
    run(sx, D1, time(9, 15), time(9, 45), before=sx_down_day(st, expiry=FAR))
    assert sx.state["open"] is None
    s = sx.state["days"][str(D1)]["status"]
    assert "SENSEX downside breakout" in s and "8 sessions away" in s


def test_sensex_subscribes_spot_vix_and_the_puts_around_the_money(env):
    tmp, st, _ = env
    up = SxUpstox(EXP, FAR)
    sx = N.NearTightySensexTrader(st, up, tmp)
    sx_down_day(st)(datetime_at(D1, time(9, 5)))
    sx.tick(datetime_at(D1, time(9, 5)))                 # before 09:15: subscribes, no trading yet
    assert {SX_SPOT, G.VIX_KEY} <= st.wanted
    assert f"SX{EXP}78400" in st.wanted and f"SX{EXP}79600" in st.wanted        # ATM 79000 +/- 6 steps
    assert f"SX{EXP}78300" not in st.wanted and f"SX{EXP}79700" not in st.wanted
    assert any(k.startswith(f"SX{FAR}") for k in st.wanted)                      # the second expiry too
    assert sx.state["open"] is None


def test_nifty_and_sensex_each_hold_their_own_position(env):
    tmp, st, _ = env
    nifty = N.NearTightyTrader(st, upstox("2026-11-03", EXP), tmp)
    sx = N.NearTightySensexTrader(st, SxUpstox(EXP), tmp)

    def both(t):
        down_day(st)(t)
        sx_down_day(st)(t)
    for tr in (nifty, sx):
        run(tr, D1, time(9, 15), time(9, 45), before=both)
    assert nifty.state["open"]["strike"] == 24000.0 and sx.state["open"]["strike"] == 79000.0
    assert nifty.state["epoch"] != sx.state["epoch"]


def test_ingest_sensex_keeps_only_sensex_calls_and_puts_with_the_lot():
    from server.upstox import UpstoxProvider
    u = UpstoxProvider("x")
    rows = [
        {"instrument_type": "PE", "instrument_key": "BSE_FO|1", "strike_price": 79000.0, "expiry": "2026-11-12",
         "underlying_symbol": "SENSEX", "lot_size": 20},
        {"instrument_type": "CE", "instrument_key": "BSE_FO|2", "strike_price": 79000.0, "expiry": 1794441600000,
         "underlying_symbol": "SENSEX", "lot_size": 20},
        {"instrument_type": "PE", "instrument_key": "BSE_FO|3", "strike_price": 60000.0, "expiry": "2026-11-12",
         "underlying_symbol": "BANKEX", "lot_size": 30},
        {"instrument_type": "PE", "instrument_key": "BSE_FO|4", "strike_price": 79000.0, "expiry": "2026-11-12",
         "underlying_symbol": "SENSEX50", "lot_size": 60},
        {"instrument_type": "FUT", "instrument_key": "BSE_FO|5", "expiry": "2026-11-26", "underlying_symbol": "SENSEX"},
    ]
    assert u.ingest_sensex(rows) == 2
    assert u._sensex[("2026-11-12", "PE", 79000.0)] == "BSE_FO|1" and u._sensex[("2026-11-12", "CE", 79000.0)] == "BSE_FO|2"
    assert not any(v in ("BSE_FO|3", "BSE_FO|4", "BSE_FO|5") for v in u._sensex.values())   # BANKEX, SENSEX50, futures
    assert u._sensex_lot["2026-11-12"] == 20
    assert u.ingest_sensex([]) == 0 and len(u._sensex) == 2            # an empty answer keeps what is loaded


def datetime_at(day, t):
    from datetime import datetime
    return datetime.combine(day, t, G.IST)
