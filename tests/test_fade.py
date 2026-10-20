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
    assert F.walk([100.0], 100.0, "CE", cheap) == "cheapest liquid lot below Rs 600 (Rs 500 at 100)"
    tiny = lambda k: {"lot_size": 8000, "depth": {"bid": [(1.38, 1)], "ask": [(1.40, 1)]}}      # noqa: E731
    assert F.walk([62.0, 63.0], 63.1, "PE", tiny) == "premium below Rs 2 (at 63: ask 1.4)"   # UJJIVANSFB, 19 Oct


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


def test_the_wait_reason_is_shown_until_it_fills(setup):
    lg, q, ft, _ = setup
    q.set("PE", 1220.0, 1.0, 1.05)
    ft.on_poll(at(15, 9, 16))
    w = lg.state["rules"]["fade_wait"]["2026-10-15:HCLTECH"]
    assert w["reason"].startswith("premium below Rs 2") and w["at"].startswith("2026-10-15T09:16")
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(at(15, 9, 20))
    assert lg.state["positions"] and "2026-10-15:HCLTECH" not in lg.state["rules"]["fade_wait"]


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


def test_index_page_and_api_are_read_only_and_reachable(monkeypatch):
    from fastapi.testclient import TestClient
    import server.app as app_mod
    import server.index_api as ia
    monkeypatch.setattr(ia, "read", lambda name: {"next": {"NIFTY": ["2026-10-19"]}} if name == "expiries_next.json" else None)
    app_mod.app.dependency_overrides[app_mod.auth] = lambda: "user"
    try:
        c = TestClient(app_mod.app)
        page, sub = c.get("/index"), c.get("/index/coverage")
        exp, pos = c.get("/api/index/expiries").json(), c.get("/api/index/positions").json()
        home = c.get("/").text
    finally:
        app_mod.app.dependency_overrides.clear()
    assert page.status_code == 200 and "Index options" in page.text and "/*__SERVER__*/" not in page.text
    assert sub.status_code == 200 and exp["next"]["NIFTY"] == ["2026-10-19"] and pos["pods"] == []
    assert 'href="/index"' in home
    assert "place" not in page.text.lower() or "can place an order" in page.text      # no order controls


def test_a_never_fit_fade_is_refused_at_once(setup):
    lg, q, ft, _ = setup
    for k in (1180.0, 1200.0, 1220.0):
        q.set("PE", k, 1.3, 1.4, lot=8000)                           # UJJIVANSFB-like: Rs 8,000 / 8,000 = Rs 1 a share
    ft.on_poll(at(15, 9, 16))
    r = [x for x in lg.state["rules"]["refused"] if x["mode"] == "fade"]
    assert len(r) == 1 and r[0]["reason"].startswith("never fits: 1 lot is 8,000 shares")
    assert lg.state["rules"]["fade"]["2026-10-15:HCLTECH"] == "refused" and not lg.state["rules"].get("fade_wait")


# ---------------------------------------------------------------- the +100 % shadow exit (S1_v10_t100_shadow_track.md)
def test_t100_shadow_tags_the_hit_and_leaves_the_real_exit(setup):
    from server import charges as ch
    lg, q, ft, _ = setup
    q.set("PE", 1220.0, 18.0, 18.5)                                                             # Rs 6,475
    ft.on_poll(at(15, 9, 16))
    (p,) = lg.state["positions"]
    assert p["rule"]["shadow_t100"] == {"target": 37.0, "hit_at": None, "max_bid": None}
    q.set("PE", 1220.0, 36.95, 37.5)                                                            # bid 1 tick short
    ft.on_poll(at(15, 10, 0))
    assert p["rule"]["shadow_t100"]["hit_at"] is None and p["rule"]["shadow_t100"]["max_bid"] == 36.95
    q.set("PE", 1220.0, 37.0, 37.5)
    ft.on_poll(at(15, 11, 0))
    assert p["rule"]["shadow_t100"]["hit_at"].startswith("2026-10-15T11:00") and lg.state["positions"]   # still open
    q.set("PE", 1220.0, 20.0, 20.5)
    ft.on_poll(at(15, 15, 20))
    c = lg.state["closed"][-1]
    assert c["exit"]["price"] == 20.0 and c["reason"] == "fade_eod"                             # the real exit: 15:20
    s = F.t100(lg.state)
    want = round((37.0 - 18.5) * 350 - c["entry_charges"] - ch.leg("PE", "SELL", 350, 37.0)["total"], 2)
    assert s["real_1520"]["net_rs"] == c["net_pnl"] and s["shadow_t100"]["net_rs"] == want
    assert s["shadow_t100"]["targets_hit"] == 1 and s["real_1520"]["closed"] == 1


def test_t100_untouched_target_matches_the_real_exit_and_old_trades_are_untagged(setup):
    lg, q, ft, _ = setup
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(at(15, 9, 16))
    q.set("PE", 1220.0, 15.0, 15.5)
    ft.on_poll(at(15, 15, 20))
    lg.state["closed"].append({"rule": {"strategy": "fade"}, "net_pnl": -100.0})
    s = F.t100(lg.state)
    assert s["shadow_t100"]["net_rs"] == s["real_1520"]["net_rs"] and s["untagged_closed"] == 1
    assert F.t100_target(1.23) == 2.46 and F.t100_target(18.5) == 37.0 and F.t100_target(1.235) == 2.47   # Rs 0.01 tick


# ---------------------------------------------------------------- sub-Rs 2 shadow entries (S1_v10_subfloor_entry.md)
def _shadows(lg):
    return (lg.state.get("rules") or {}).get("fade_shadow_entries") or []


def test_a_sub_rs2_refusal_creates_one_shadow_entry_and_no_position(setup):
    lg, q, ft, _ = setup
    q.set("PE", 1220.0, 1.40, 1.45, lot=1000)                                                   # Rs 1,450 a lot
    ft.on_poll(at(15, 9, 16))
    assert lg.state["positions"] == []                                                          # the real rule refuses
    (s,) = _shadows(lg)
    assert (s["strike"], s["entry"], s["lot_size"], s["lot_cost"], s["bid_at_entry"]) == (1220.0, 1.45, 1000, 1450.0, 1.40)
    assert s["refused"].startswith("premium below Rs 2") and s["opened_at"].startswith("2026-10-15T09:16")
    ft.on_poll(at(15, 9, 20))                                                                   # the retry: still one
    assert len(_shadows(lg)) == 1


def test_the_shadow_entry_is_marked_and_netted_at_15_20(setup):
    from server import charges as ch
    lg, q, ft, _ = setup
    q.set("PE", 1220.0, 1.40, 1.45, lot=1000)
    ft.on_poll(at(15, 9, 16))
    q.set("PE", 1220.0, 1.90, 1.95, lot=1000)
    ft.on_poll(at(15, 11, 0))
    (s,) = _shadows(lg)
    assert s["max_bid"] == 1.90 and s["exit"] is None
    q.set("PE", 1220.0, 1.80, 1.85, lot=1000)
    ft.on_poll(at(15, 15, 20))
    want = round((1.80 - 1.45) * 1000 - ch.leg("PE", "BUY", 1000, 1.45)["total"] - ch.leg("PE", "SELL", 1000, 1.80)["total"], 2)
    assert s["exit"] == 1.80 and s["net"] == want and s["closed_at"].startswith("2026-10-15T15:20") and not s["late"]
    assert s["net_pct"] == round(want / 1450 * 100, 2)
    summ = F.shadow_entries(lg.state)
    assert summ["closed"] == 1 and summ["wins"] == 1 and summ["net_rs"] == want and summ["open"] == 0
    assert lg.state["positions"] == [] and lg.state["closed"] == []                             # never a real trade


@pytest.mark.parametrize("quotes", [
    {1180.0: (39.0, 40.0, 350), 1200.0: (39.0, 40.0, 350), 1220.0: (39.0, 40.0, 350)},          # lot cost above Rs 8,000
    {1220.0: (10.0, 20.0, 350)},                                                                # spread above 10 %
    {1220.0: (1.00, 1.05, 350)},                                                                # sub-Rs 2, lot below Rs 600
    {1220.0: (1.00, 1.90, 1000)},                                                               # sub-Rs 2, spread too wide
])
def test_other_refusals_create_no_shadow_entry(setup, quotes):
    lg, q, ft, _ = setup
    for k, (bid, ask, lot) in quotes.items():
        q.set("PE", k, bid, ask, lot=lot)
    ft.on_poll(at(15, 9, 16))
    ft.on_poll(at(15, 15, 21))
    assert _shadows(lg) == [] and lg.state["positions"] == []


def test_a_never_fits_refusal_is_a_floor_refusal_and_a_real_buy_flags_the_shadow(setup):
    lg, q, ft, _ = setup
    q.set("PE", 1220.0, 1.40, 1.45, lot=5000)                    # Rs 2 x 5,000 > Rs 8,000: refused at once, never fits
    ft.on_poll(at(15, 9, 16))
    (s,) = _shadows(lg)
    assert s["refused"].startswith("never fits") and s["lot_cost"] == 7250.0
    lg.state["rules"]["fade_shadow_entries"] = []
    lg.state["rules"]["fade"] = {}
    q.book.clear()
    q.set("PE", 1220.0, 1.40, 1.45, lot=1000)
    ft._tried.clear()
    ft.on_poll(at(15, 9, 30))                                                                  # sub-Rs 2: shadow
    q.set("PE", 1220.0, 2.40, 2.45, lot=1000)
    ft._tried.clear()
    ft.on_poll(at(15, 9, 40))                                                                  # ask rose: real buy
    (s,) = _shadows(lg)
    assert lg.state["positions"] and s["real_bought"] is True
    assert F.shadow_entries(lg.state)["real_bought"] == 1


# ---------------------------------------------------------------- S1 v11: the -20 % stop is the live exit, v10 is the shadow
def test_v11_stop_sells_at_the_bid_and_v10_shadow_takes_the_1520_bid(setup):
    from server import charges as ch
    lg, q, ft, _ = setup
    q.set("PE", 1220.0, 18.0, 18.5)                                                             # entry 18.50, stop 14.80
    ft.on_poll(at(15, 9, 16))
    (p,) = lg.state["positions"]
    assert p["rule"]["version"] == "v11" and p["rule"]["stop"]["level"] == 14.8
    assert p["rule"]["shadow_v10"] == {"status": "open"}
    q.set("PE", 1220.0, 14.85, 15.2)                                                            # a tick above the stop
    ft.on_poll(at(15, 10, 0))
    assert lg.state["positions"]
    q.set("PE", 1220.0, 13.9, 14.3)                                                             # gapped through it
    ft.on_poll(at(15, 10, 1))
    c = lg.state["closed"][-1]
    assert lg.state["positions"] == [] and c["reason"] == "fade_stop" and c["exit"]["price"] == 13.9
    assert c["rule"]["shadow_v10"]["status"] == "pending"
    q.set("PE", 1220.0, 24.0, 24.4)                                                             # recovers by 15:20
    ft.on_poll(at(15, 15, 0))
    assert c["rule"]["shadow_v10"]["status"] == "pending"                                       # not before 15:20
    ft.on_poll(at(15, 15, 20))
    sh = c["rule"]["shadow_v10"]
    want = round((24.0 - 18.5) * 350 - c["entry_charges"] - ch.leg("PE", "SELL", 350, 24.0)["total"], 2)
    assert sh["status"] == "done" and sh["fill"] == 24.0 and sh["net"] == want and not sh["late"]
    s = F.v10_shadow(lg.state)
    assert s["real_v11"]["net_rs"] == c["net_pnl"] and s["shadow_v10"]["net_rs"] == want
    assert s["stops"] == 1 and s["stopped_but_v10_better"] == 1


def test_v11_not_stopped_sells_at_1520_and_the_shadow_is_the_same(setup):
    lg, q, ft, _ = setup
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(at(15, 9, 16))
    q.set("PE", 1220.0, 37.0, 37.5)                                                             # +100 %: the t100 tag
    ft.on_poll(at(15, 11, 0))
    (p,) = lg.state["positions"]
    assert p["rule"]["shadow_t100"]["hit_at"]
    q.set("PE", 1220.0, 20.0, 20.5)
    ft.on_poll(at(15, 15, 20))
    c = lg.state["closed"][-1]
    assert c["reason"] == "fade_eod" and c["rule"]["shadow_v10"] == {"status": "same"}
    s = F.v10_shadow(lg.state)
    assert s["shadow_v10"]["net_rs"] == s["real_v11"]["net_rs"] == c["net_pnl"] and s["stops"] == 0


def test_v11_stop_is_not_active_in_the_0915_minute(setup):
    lg, q, ft, _ = setup
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(datetime(2026, 10, 15, 9, 15, 20, tzinfo=IST))                                  # bought at 09:15
    q.set("PE", 1220.0, 13.0, 13.5)                                                             # dip in the 09:15 minute
    ft.on_poll(datetime(2026, 10, 15, 9, 15, 50, tzinfo=IST))
    assert lg.state["positions"]
    ft.on_poll(at(15, 9, 16))                                                                   # still below at 09:16
    assert lg.state["closed"][-1]["reason"] == "fade_stop" and lg.state["closed"][-1]["exit"]["price"] == 13.0


def test_v11_stopped_trade_whose_1520_poll_was_missed_gets_a_late_shadow(setup):
    lg, q, ft, box = setup
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(at(15, 9, 16))
    q.set("PE", 1220.0, 13.0, 13.5)
    ft.on_poll(at(15, 9, 30))
    box["f"] = None                                                                             # server asleep at 15:20
    q.set("PE", 1220.0, 11.0, 11.5)
    ft.on_poll(at(16, 9, 20))
    sh = lg.state["closed"][-1]["rule"]["shadow_v10"]
    assert sh["status"] == "done" and sh["fill"] == 11.0 and sh["late"]
