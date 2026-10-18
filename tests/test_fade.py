"""S1 v10 results-day fade: the signal rules (scanner/fade_live.py) and the paper trades (server/fade.py)."""
from datetime import date, datetime

import pytest

from scanner import fade_live as fl
from server import fade as F
from server import rules as R
from server.paper import PaperLedger
from server.sessions import IST

EXP = "2026-10-27"


def at(d, h, m=0):
    return datetime(2026, 10, d, h, m, tzinfo=IST)


class Quotes:
    def __init__(self):
        self.book, self.last_error = {}, None

    def set(self, side, k, bid, ask, lot=350, ltp=None):
        self.book[f"HCLTECH26OCT{int(k)}{side}"] = {"last_price": ltp or (bid + ask) / 2, "atp": ask, "volume": 0,
                                                    "lot_size": lot, "depth": {"bid": [(bid, 5000)], "ask": [(ask, 5000)]}}

    def get(self, c, fresh=True):
        return self.book.get(c["tradingsymbol"])

    def spot(self, s):
        return 1225.0


def sig(side="PE", session="2026-10-15"):
    return {"session": session, "signals": [{"symbol": "HCLTECH", "side": side, "expiry": EXP, "spot": 1222.98,
                                             "strikes": [1180.0, 1200.0, 1220.0, 1240.0, 1260.0], "filed": "2026-10-14",
                                             "why": "net profit YoY +21.2 %"}]}


@pytest.fixture
def setup(tmp_path):
    q = Quotes()
    lg = PaperLedger(tmp_path, q, capital=500_000, clock=lambda: at(15, 9, 16))
    box = {"f": sig()}
    return lg, q, F.FadeTrader(lg, lambda: box["f"]), box


# ---------------------------------------------------------------- signal rules
def test_classify_strong_put_weak_call():
    assert fl.classify({"net_profit_yoy": 21.2, "net_profit_qoq": 10.9, "revenue_yoy": 11.5}) == "PE"
    assert fl.classify({"net_profit_yoy": -30, "net_profit_qoq": -5, "revenue_yoy": 4}) == "CE"
    assert fl.classify({"net_profit_yoy": 10.0, "net_profit_qoq": -0.2, "revenue_yoy": 15}) is None   # TATAELXSI
    assert fl.classify({"net_profit_yoy": None, "net_profit_qoq": None, "revenue_yoy": -2.3}) is None


def test_target_session_and_day0():
    sess = lambda d: d.weekday() < 5                                                             # noqa: E731
    assert fl.target_session(at(14, 20, 45), sess) == date(2026, 10, 15)       # evening -> tomorrow
    assert fl.target_session(at(15, 7, 47), sess) == date(2026, 10, 15)        # morning run -> today
    assert fl.target_session(at(16, 21, 0), sess) == date(2026, 10, 19)        # Friday evening -> Monday
    cal = fl.calendar(date(2026, 10, 15), sess)
    res = [("A", "2026-10-14", "16:58"), ("B", "2026-10-15", "08:10"), ("C", "2026-10-14", "11:00"),
           ("D", "2026-10-15", "10:30"), ("E", "2026-10-13", "18:00")]
    got = sorted(s for s, _, _ in fl.day0_signals(res, cal))
    assert got == ["A", "B", "C"]          # C filed during the 14th's session: day 0 is the 15th; D's is the 16th


def test_expiry_keeps_two_sessions():
    left = lambda t, e: {"2026-10-27": 1, "2026-11-24": 25}[e]                                  # noqa: E731
    assert fl.choose_expiry(["2026-10-27", "2026-11-24"], date(2026, 10, 23), left) == "2026-11-24"


# ---------------------------------------------------------------- the walk
def test_put_walk_goes_down_and_skips_wide_and_dear():
    q = {1220.0: (39.0, 40.0), 1200.0: (20.0, 26.0), 1180.0: (17.0, 18.0)}                    # lot 350
    look = lambda k: {"lot_size": 350, "depth": {"bid": [(q[k][0], 1)], "ask": [(q[k][1], 1)]}} if k in q else None  # noqa: E731
    assert F.walk([1180.0, 1200.0, 1220.0, 1240.0], 1225.0, "PE", look) == (1180.0, 18.0, 350)
    assert "spread" in F.walk([1200.0], 1200.0, "PE", look)


def test_call_walk_goes_up_and_tie_rules():
    look = lambda k: {"lot_size": 100, "depth": {"bid": [(9.9, 1)], "ask": [(10.0, 1)]}}        # noqa: E731
    assert F.walk([100.0, 110.0], 105.0, "CE", look)[0] == 100.0                                # tie: lower call
    assert F.walk([100.0, 110.0], 105.0, "PE", look)[0] == 110.0                                # tie: higher put
    cheap = lambda k: {"lot_size": 100, "depth": {"bid": [(4.9, 1)], "ask": [(5.0, 1)]}}        # noqa: E731
    assert F.walk([100.0], 100.0, "CE", cheap) == "cheapest liquid lot below Rs 600"


# ---------------------------------------------------------------- the paper trades
def test_buys_on_day0_and_sells_at_15_20(setup):
    lg, q, ft, _ = setup
    q.set("PE", 1220.0, 30.0, 30.5)                                                             # Rs 10,675: dear
    q.set("PE", 1200.0, 18.0, 18.5)                                                             # Rs 6,475
    ft.on_poll(at(14, 10, 0))                                                                   # not its session
    assert lg.state["positions"] == []
    ft.on_poll(at(15, 9, 16))
    (p,) = lg.state["positions"]
    assert (p["instrument"], p["strike"], p["entry"]["price"]) == ("PE", 1200.0, 18.5)
    assert p["rule"]["strategy"] == "fade" and p["rule"]["arms"] == ["F"]
    ft.on_poll(at(15, 9, 30))
    assert len(lg.state["positions"]) == 1                                                      # bought once
    R.RuleTrader(lg, lambda: None).check_exits(at(15, 15, 20))                                  # S1 exits: hands off
    assert len(lg.state["positions"]) == 1
    q.set("PE", 1200.0, 24.0, 24.4)
    ft.on_poll(at(15, 15, 20))
    c = lg.state["closed"][-1]
    assert lg.state["positions"] == [] and c["exit"]["price"] == 24.0 and c["reason"] == "fade_eod"


def test_refused_at_15_20_with_the_reason(setup):
    lg, q, ft, _ = setup
    for k in (1180.0, 1200.0, 1220.0):
        q.set("PE", k, 39.0, 40.0)                                                              # Rs 14,000 each
    ft.on_poll(at(15, 9, 16))
    ft.on_poll(at(15, 15, 21))
    r = [x for x in lg.state["rules"]["refused"] if x["mode"] == "fade"]
    assert lg.state["positions"] == [] and len(r) == 1 and "more than Rs 8,000" in r[0]["reason"]


def test_a_position_left_open_is_sold_next_day(setup):
    lg, q, ft, box = setup
    q.set("PE", 1220.0, 20.0, 20.4)
    ft.on_poll(at(15, 9, 16))
    box["f"] = None
    q.set("PE", 1220.0, 15.0, 15.4)
    ft.on_poll(at(16, 9, 20))
    assert lg.state["closed"][-1]["reason"] == "fade_late"


# ---------------------------------------------------------------- review fixes
def test_morning_rerun_keeps_the_nightly_signals():
    prior = {"session": "2026-10-15", "made_at": "2026-10-14T20:45:00+05:30",
             "signals": [{"symbol": "HCLTECH", "side": "PE"}, {"symbol": "RBLBANK", "side": "PE"},
                         {"symbol": "TCS", "side": "PE"}]}
    new_sigs = [{"symbol": "INFY", "side": "CE"}]
    new_skip = [{"symbol": "HCLTECH", "reason": "no F&O bhavcopy for the last session"},
                {"symbol": "TCS", "reason": "numbers neither strong nor weak"}]
    sigs, skip = fl.keep_earlier(prior, "2026-10-15", new_sigs, new_skip)
    assert sorted(s["symbol"] for s in sigs) == ["HCLTECH", "INFY", "RBLBANK"]   # TCS re-judged: dropped
    assert [s["symbol"] for s in skip] == ["TCS"]
    assert fl.keep_earlier(prior, "2026-10-16", new_sigs, new_skip) == (new_sigs, new_skip)   # a new session


def test_holiday_file_is_a_non_session():
    from server import sessions
    assert not sessions.is_session(date(2026, 10, 20))                    # Dussehra, data/nse_holidays.json
    assert fl.target_session(at(19, 20, 45), sessions.is_session) == date(2026, 10, 21)


def test_fade_closes_do_not_crowd_out_s1_follow(setup):
    lg, q, ft, _ = setup
    s1 = {"symbol": "X", "instrument": "CE", "expiry": EXP, "strike": 100.0, "tradingsymbol": "X26OCT100CE",
          "lot_size": 100, "rule": {"arms": ["A"]}, "after": {"until": EXP, "peak": None, "trough": None, "last": None}}
    fades = [{**s1, "tradingsymbol": f"F{i}", "rule": {"strategy": "fade", "arms": ["F"]},
              "after": {"until": EXP, "peak": None, "trough": None, "last": None}} for i in range(12)]
    lg.state["closed"] = [s1] + fades
    q.book["X26OCT100CE"] = {"last_price": 7.0}
    lg._follow_closed(at(16, 10, 0))
    assert lg.state["closed"][0]["after"]["last"]["price"] == 7.0


# ---------------------------------------------------------------- the carried trades (addendum 2026-10-17)
@pytest.fixture
def carried(setup, monkeypatch):
    """A fade put bought on the 15th at 18.50 that is treated as a carried trade (its signal date is in CARRY_DATES)."""
    lg, q, ft, box = setup
    monkeypatch.setattr(F, "CARRY_DATES", {"2026-10-15"})
    q.set("PE", 1200.0, 18.0, 18.5)
    ft.on_poll(at(15, 9, 16))
    box["f"] = None
    (p,) = lg.state["positions"]
    assert ft.carried(p) and p["entry"]["price"] == 18.5
    return lg, q, ft, p


def test_carried_trade_is_not_sold_at_the_first_poll_of_the_next_day(carried):
    lg, q, ft, _ = carried
    q.set("PE", 1200.0, 17.0, 17.4)
    ft.on_poll(at(16, 9, 20))
    ft.on_poll(at(16, 14, 0))
    assert len(lg.state["positions"]) == 1


def test_carried_trade_stops_at_minus_20_percent_on_the_close(carried):
    lg, q, ft, _ = carried
    q.set("PE", 1200.0, 14.9, 15.3, ltp=15.0)                    # 15.0 > 0.80 x 18.5 = 14.8: kept
    ft.on_poll(at(16, 15, 20))
    assert len(lg.state["positions"]) == 1
    q.set("PE", 1200.0, 14.5, 14.9, ltp=14.7)                    # 14.7 <= 14.8: sold at the bid
    ft.on_poll(at(19, 15, 19))
    assert len(lg.state["positions"]) == 1                       # not before 15:20
    ft.on_poll(at(19, 15, 20))
    c = lg.state["closed"][-1]
    assert lg.state["positions"] == [] and c["reason"] == "carry_stop" and c["exit"]["price"] == 14.5


def test_carried_trade_trails_25_percent_below_the_highest_close(carried):
    lg, q, ft, _ = carried
    q.set("PE", 1200.0, 24.8, 25.2, ltp=25.0)                    # a new peak of 25.0
    ft.on_poll(at(16, 15, 20))
    assert lg.state["positions"][0]["rule"]["carry"]["peak"] == 25.0
    q.set("PE", 1200.0, 19.0, 19.4, ltp=19.2)                    # 19.2 > 0.75 x 25 = 18.75: kept
    ft.on_poll(at(19, 15, 20))
    assert len(lg.state["positions"]) == 1
    q.set("PE", 1200.0, 18.5, 18.9, ltp=18.7)                    # 18.7 <= 18.75: sold, though still above the entry
    ft.on_poll(at(21, 15, 20))
    c = lg.state["closed"][-1]
    assert lg.state["positions"] == [] and c["reason"] == "carry_trail" and c["exit"]["price"] == 18.5


def test_carried_trade_is_checked_once_a_session_and_sold_at_t_minus_1(carried):
    lg, q, ft, _ = carried
    q.set("PE", 1200.0, 17.9, 18.3, ltp=18.1)
    ft.on_poll(at(16, 15, 20))
    q.set("PE", 1200.0, 10.0, 10.4, ltp=10.2)                    # a later poll the same day is ignored
    ft.on_poll(at(16, 15, 25))
    assert len(lg.state["positions"]) == 1
    q.set("PE", 1200.0, 18.9, 19.3, ltp=19.0)
    ft.on_poll(at(23, 15, 20))
    assert len(lg.state["positions"]) == 1                       # 27 Oct expiry: T-1 is Mon 26 Oct
    ft.on_poll(at(26, 15, 20))
    assert lg.state["closed"][-1]["reason"] == "carry_t1" and lg.state["positions"] == []


def test_no_position_follows_the_carry_rule_and_the_eight_sell_at_the_next_first_poll(setup):
    """2026-10-17: the carried trades were closed, not kept; the same-day exit is strict for every fade trade."""
    assert F.CARRY_DATES == set()
    lg, q, ft, box = setup
    q.set("PE", 1220.0, 20.0, 20.4)
    ft.on_poll(at(15, 9, 16))
    (p,) = lg.state["positions"]
    p["rule"]["signal_date"] = "2026-10-16"                       # as the eight opened on Friday 16 Oct
    assert not ft.carried(p)
    box["f"] = None
    q.set("PE", 1220.0, 12.0, 12.4)                               # a losing weekend, far below -20 %
    ft.on_poll(at(19, 9, 15))
    assert lg.state["positions"] == [] and lg.state["closed"][-1]["reason"] == "fade_late"


def test_summary_endpoint_reports_the_running_commit(monkeypatch):
    """/api/paper/summary carries version.commit (Render's RENDER_GIT_COMMIT) so a deploy can be checked from outside."""
    from fastapi.testclient import TestClient
    import server.app as app_mod
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc1234")
    monkeypatch.setattr(app_mod, "_ledger", lambda: type("L", (), {"summary": lambda self: {"open_positions": 0}})())
    monkeypatch.setattr(app_mod.state, "mirror", None, raising=False)
    app_mod.app.dependency_overrides[app_mod.auth] = lambda: "user"
    try:
        body = TestClient(app_mod.app).get("/api/paper/summary").json()
    finally:
        app_mod.app.dependency_overrides.clear()
    assert body["version"] == {"commit": "abc1234", "fade_carry_dates": []}
    assert body["fade_split"]["v10 all fade"]["closed"] == 0


def test_history_endpoint_serves_a_past_stock_day_and_refuses_market_hours(monkeypatch):
    """/api/history/<stock>?day= reads the broker's history through the server's key (S1 v10 stop-loss study)."""
    from fastapi.testclient import TestClient
    import server.app as app_mod
    calls = []

    class Prov:
        def history(self, key, tf, day):
            calls.append((key, tf, day))
            return [{"time": 1, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10.0, "atp": None}]

    monkeypatch.setattr(app_mod.state, "feed", type("Feed", (), {"provider": Prov()})(), raising=False)
    app_mod.app.dependency_overrides[app_mod.auth] = lambda: "user"
    try:
        c = TestClient(app_mod.app)
        monkeypatch.setattr(app_mod, "market_open", lambda: False)
        body = c.get("/api/history/tcs?day=2025-01-10&tf=1").json()
        assert calls == [("NSE:TCS", 1, "2025-01-10")] and body["candles"][0]["high"] == 2.0 and body["error"] is None
        assert c.get("/api/history/TCS?day=2999-01-01").status_code == 400
        assert c.get("/api/history/TCS?day=10-01-2025").status_code == 400
        monkeypatch.setattr(app_mod, "market_open", lambda: True)
        assert c.get("/api/history/TCS?day=2025-01-10").status_code == 503
    finally:
        app_mod.app.dependency_overrides.clear()


# ---------------------------------------------------------------- NP YoY > 25 % shadow track (tag only)
def test_entry_tags_the_numbers_and_the_shadow_track(setup):
    lg, q, ft, box = setup
    box["f"]["signals"][0].update(np_yoy=21.2, np_qoq=4.0, rev_yoy=9.0)
    q.set("PE", 1200.0, 18.0, 18.5)
    ft.on_poll(at(15, 9, 16))
    r = lg.state["positions"][0]["rule"]
    assert (r["np_yoy"], r["np_qoq"], r["rev_yoy"], r["shadow_np25"]) == (21.2, 4.0, 9.0, False)   # v10 still buys it


def test_shadow_rule_and_the_note_fallback():
    assert F.in_shadow("CE", -40.0) is True and F.in_shadow("CE", None) is True
    assert F.in_shadow("PE", 25.0) is False and F.in_shadow("PE", 25.1) is True and F.in_shadow("PE", None) is None
    assert F.np_yoy_of({"why": "net profit YoY +119.0 %, QoQ +117.9 %"}) == 119.0
    assert F.np_yoy_of({"why": "net profit YoY -25.4 %, QoQ -27.2 %"}) == -25.4
    assert F.np_yoy_of({"np_yoy": 13.9, "why": "net profit YoY +99 %"}) == 13.9 and F.np_yoy_of({}) is None


def test_split_counts_closed_and_open_fade_trades():
    fade = lambda why, **k: {"strategy": "fade", "why": why, **k}                               # noqa: E731
    st = {"closed": [{"instrument": "PE", "net_pnl": -192.2, "return_pct": -3.25, "rule": fade("net profit YoY +119.0 %")},
                     {"instrument": "PE", "net_pnl": -500.0, "return_pct": -10.0, "rule": fade("net profit YoY +13.9 %")},
                     {"instrument": "CE", "net_pnl": 300.0, "return_pct": 6.0, "rule": fade("net profit YoY -51.0 %")},
                     {"instrument": "CE", "net_pnl": 999.0, "return_pct": 9.0, "rule": {"strategy": "s1"}}],
          "positions": [{"instrument": "PE", "unrealised": 50.0, "rule": fade("x", np_yoy=40.0, shadow_np25=True)}]}
    s = F.split(st)
    assert s["v10 all fade"] == {"closed": 3, "wins": 1, "net_rs": -392.2, "mean_net_pct": -2.42, "open": 1,
                                 "unrealised_rs": 50.0}
    assert s["shadow: calls + puts NP YoY > 25 %"]["closed"] == 2 and s["shadow: calls + puts NP YoY > 25 %"]["open"] == 1
    assert s["left out: puts NP YoY <= 25 %"] == {"closed": 1, "wins": 0, "net_rs": -500.0, "mean_net_pct": -10.0,
                                                  "open": 0, "unrealised_rs": 0.0}


# ---------------------------------------------------------------- the results page: Arm F workspace data
def test_results_page_embeds_the_fade_list_and_api_fade_serves_it(monkeypatch):
    from fastapi.testclient import TestClient
    import server.app as app_mod
    fade = {"session": "2026-10-19", "signals": [{"symbol": "FEDERALBNK", "side": "PE", "np_yoy": 51.1}], "skipped": []}
    monkeypatch.setattr(app_mod.state, "scan", {"meta": {"forward": None, "fade": fade}}, raising=False)
    app_mod.app.dependency_overrides[app_mod.auth] = lambda: "user"
    try:
        c = TestClient(app_mod.app)
        page, api = c.get("/").text, c.get("/api/fade").json()
    finally:
        app_mod.app.dependency_overrides.clear()
    assert "/*__FADE__*/" not in page and '"FEDERALBNK"' in page and 'data-tab' in page
    assert api == fade


def test_static_results_copy_embeds_the_fade_list(tmp_path):
    from scanner.build import ROOT, render_results
    out = tmp_path / "results.html"
    render_results({"meta": {"forward": None, "fade": {"session": "2026-10-19", "signals": []}}}, ROOT / "templates" / "results.html", out)
    html = out.read_text(encoding="utf-8")
    assert "/*__FADE__*/" not in html and '"session":"2026-10-19"' in html
