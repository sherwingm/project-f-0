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
