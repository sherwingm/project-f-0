"""S1 rule trades in the paper account (server/rules.py): the open and 15:20 entries, arm tags, the rule exits,
stale lists, and the ledger's fresh start under the new epoch."""
import json
from datetime import date, datetime

import pytest

from server import rules as R
from server.paper import PAPER_EPOCH, PaperLedger
from server.sessions import IST

EXP = "2026-10-27"
TS = {k: f"HCLTECH26OCT{int(k)}CE" for k in (1300.0, 1350.0, 1400.0)}


def at(d, h, m=0, s=0):
    return datetime(2026, 10, d, h, m, s, tzinfo=IST)


class Quotes:
    def __init__(self):
        self.book, self.last_error = {}, None

    def set(self, k, ltp, bid=None, ask=None, atp=None, contracts=200, lot=350):
        self.book[TS[k]] = {"last_price": ltp, "atp": atp if atp is not None else ltp, "volume": contracts * lot,
                            "lot_size": lot, "depth": {"bid": [(bid or ltp - 0.1, 5000)], "ask": [(ask or ltp + 0.1, 5000)]}}

    def get(self, c, fresh=True):
        return self.book.get(c["tradingsymbol"])

    def spot(self, s):
        return 1300.0


def fw(last="2026-10-13", open_strike=1300.0):
    p = {"symbol": "HCLTECH", "signal_date": last, "beat": 4.5, "move": 8.4, "expiry": EXP, "spot": 1300.0,
         "strikes": [1300.0, 1350.0, 1400.0], "open_strike": open_strike, "open_lot": 350}
    return {"last_session": last, "arms": {"A": {"pending": [p]}, "B": {"pending": [dict(p)]}}}


@pytest.fixture
def setup(tmp_path):
    q = Quotes()
    lg = PaperLedger(tmp_path, q, capital=500_000, clock=lambda: at(14, 9, 16))
    box = {"fw": fw()}
    return lg, q, R.RuleTrader(lg, lambda: box["fw"]), box


def test_signals_merge_arms_and_ignore_a_stale_list():
    s = R.signals_for(fw(), date(2026, 10, 14))
    assert len(s) == 1 and s[0]["arms"] == ["A", "B"]
    assert R.signals_for(fw(), date(2026, 10, 15)) == []          # the 14th already passed
    assert R.signals_for(fw(last="2026-10-14"), date(2026, 10, 14)) == []


def test_open_and_close_entries_are_two_tagged_positions(setup):
    lg, q, rt, _ = setup
    q.set(1300.0, 19.0, ask=19.2)
    rt.on_poll(at(14, 9, 16))
    rt.on_poll(at(14, 9, 17))                                      # not bought twice
    pos = lg.state["positions"]
    assert len(pos) == 1 and pos[0]["entry"]["price"] == 19.2 and pos[0]["rule"]["entry_mode"] == "open"
    assert pos[0]["rule"]["arms"] == ["A", "B"] and pos[0]["qty"] == 350
    q.set(1300.0, 21.0, atp=20.0)
    rt.on_poll(at(14, 15, 20))
    modes = sorted(p["rule"]["entry_mode"] for p in lg.state["positions"])
    assert modes == ["close", "open"]
    close = next(p for p in lg.state["positions"] if p["rule"]["entry_mode"] == "close")
    assert close["entry"]["price"] == 20.01 and close["strike"] == 1300.0         # ATP + 1 tick (Rs 0.01)
    assert all(p["rule"]["checked"] == "2026-10-14" for p in lg.state["positions"])   # first close counted


def test_the_15_20_walk_skips_thin_and_dear_strikes(setup):
    lg, q, rt, box = setup
    box["fw"] = fw(open_strike=None)
    q.set(1300.0, 30.0, atp=30.0)                                  # Rs 10,517 a lot: too dear
    q.set(1350.0, 15.0, atp=15.0, contracts=10)                    # too thin
    q.set(1400.0, 8.0, atp=8.0)
    rt.on_poll(at(14, 15, 21))
    (p,) = lg.state["positions"]
    assert p["strike"] == 1400.0 and p["rule"]["entry_mode"] == "close"
    assert lg.state["rules"]["refused"][0]["mode"] == "open"       # no strike picked overnight


def test_rule_exits_stop_decay_and_t_minus_1(setup):
    lg, q, rt, box = setup
    q.set(1300.0, 20.0, ask=20.0)
    rt.on_poll(at(14, 9, 16))
    box["fw"] = None
    q.set(1300.0, 9.9, bid=9.8)                                    # <= 50 % of 20.0 at the close
    rt.on_poll(at(15, 15, 20))
    c = lg.state["closed"][-1]
    assert c["reason"] == "rule_stop" and c["exit"]["price"] == 9.8 and c["rule"]["arms"] == ["A", "B"]
    assert c["after"]["until"]                                     # followed after the exit


def test_t_minus_1_exit(setup):
    lg, q, rt, box = setup
    q.set(1300.0, 20.0, ask=20.0)
    rt.on_poll(at(14, 9, 16))
    box["fw"] = None
    q.set(1300.0, 25.0, bid=24.9)
    rt.on_poll(at(26, 15, 20))                                     # Mon 26 Oct: the session before the 27th
    assert lg.state["closed"][-1]["reason"] == "rule_t1"


def test_old_ledger_is_archived_under_the_new_epoch(tmp_path):
    old = {"capital": 500000.0, "cash": 480000.0, "positions": [{"id": "P-1", "symbol": "APOLLOHOSP"}], "closed": [],
           "daily": {}, "peak_equity": 500000.0, "created_at": "2026-09-30T11:52:00+05:30"}
    (tmp_path / "paper_ledger.json").write_text(json.dumps(old))
    lg = PaperLedger(tmp_path, Quotes(), capital=500_000)
    assert lg.state["epoch"] == PAPER_EPOCH and lg.state["positions"] == [] and lg.state["cash"] == 500000.0
    assert lg.state["archive"][0]["positions"][0]["symbol"] == "APOLLOHOSP"



def test_open_window_re_walks_a_gap_up_and_retries(setup):
    lg, q, rt, box = setup
    box["fw"]["arms"]["A"]["pending"][0]["liquid_strikes"] = [1300.0, 1350.0, 1400.0]
    box["fw"]["arms"]["B"]["pending"][0]["liquid_strikes"] = [1300.0, 1350.0, 1400.0]
    for k in (1300.0, 1350.0, 1400.0):
        q.set(k, 40.0, ask=40.0)                                    # every lot Rs 14,000: nothing fits at 09:16
    rt.on_poll(at(14, 9, 16))
    assert lg.state["positions"] == []
    q.set(1350.0, 20.0, ask=20.0)                                   # 7,000 a lot
    rt.on_poll(at(14, 9, 16, 10))                                   # 10 s later: not retried yet
    assert lg.state["positions"] == []
    rt.on_poll(at(14, 9, 16, 38))                                   # the next poll, 28 s on: retried
    (p,) = lg.state["positions"]
    assert (p["strike"], p["entry"]["price"], p["rule"]["entry_mode"]) == (1350.0, 20.0, "open")


def test_the_open_wait_reason_is_shown_until_it_fills(setup):
    lg, q, rt, box = setup
    for a in ("A", "B"):
        box["fw"]["arms"][a]["pending"][0]["liquid_strikes"] = [1300.0, 1350.0, 1400.0]
    for k in (1300.0, 1350.0, 1400.0):
        q.set(k, 40.0, ask=40.0)                                    # Rs 14,000 a lot: nothing fits
    rt._state()["open_wait"] = {"2026-10-13:OLD": {"reason": "x", "at": "", "arms": ["A"]}}
    rt.on_poll(at(14, 9, 16))
    w = lg.state["rules"]["open_wait"]
    assert list(w) == ["2026-10-14:HCLTECH"]                         # an earlier day's reason is dropped
    assert "more than Rs 8,000" in w["2026-10-14:HCLTECH"]["reason"] and "at 1400" in w["2026-10-14:HCLTECH"]["reason"]
    assert w["2026-10-14:HCLTECH"]["at"].startswith("2026-10-14T09:16") and w["2026-10-14:HCLTECH"]["arms"] == ["A", "B"]
    q.set(1350.0, 20.0, ask=20.0)
    rt.on_poll(at(14, 9, 19))
    assert lg.state["positions"] and lg.state["rules"]["open_wait"] == {}
    saved = json.loads((lg.path).read_text(encoding="utf-8"))["rules"]       # on disk at once: a restart does not re-buy
    assert saved["open"]["2026-10-14:HCLTECH"] == "bought" and saved["open_wait"] == {}


def test_the_open_wait_reason_names_the_strike_and_clears_on_refusal(setup):
    lg, q, rt, box = setup
    for a in ("A", "B"):
        box["fw"]["arms"][a]["pending"][0]["liquid_strikes"] = [1300.0]
    q.set(1300.0, 1.5, ask=1.5)
    rt.on_poll(at(14, 9, 16))
    assert lg.state["rules"]["open_wait"]["2026-10-14:HCLTECH"]["reason"] == "premium below Rs 2 (at 1300: ask 1.5)"
    rt = R.RuleTrader(lg, lambda: box["fw"])                         # a restart: the in-memory reason is gone
    rt.on_poll(at(14, 15, 20))
    r = [x for x in lg.state["rules"]["refused"] if x["mode"] == "open"]
    assert r[0]["reason"] == "premium below Rs 2 (at 1300: ask 1.5)" and lg.state["rules"]["open_wait"] == {}


def test_walk_reasons_name_the_strike_and_price():
    cheap = lambda k: {"lot_size": 100, "atp": 4.0, "volume": 100 * 100, "depth": {"ask": [(4.0, 1)]}}  # noqa: E731
    assert R.walk_ask([100.0], 100.0, cheap) == "cheapest liquid lot below Rs 600 (Rs 400 at 100)"
    assert R.walk_live([100.0], 100.0, cheap) == "cheapest liquid lot below Rs 600 (Rs 401 at 100)"    # ATP + Rs 0.01
    tiny = lambda k: {"lot_size": 4250, "atp": 1.8, "volume": 4250 * 100, "depth": {"ask": [(1.85, 1)]}}  # noqa: E731
    assert R.walk_ask([80.0, 81.0], 80.2, tiny) == "premium below Rs 2 (at 80: ask 1.85)"
    assert R.walk_live([80.0, 81.0], 80.2, tiny) == "premium below Rs 2 (at 80: ATP 1.8)"


def test_open_window_refuses_at_15_20_with_the_reason(setup):
    lg, q, rt, box = setup
    box["fw"]["arms"]["A"]["pending"][0]["liquid_strikes"] = [1300.0]
    box["fw"]["arms"]["B"]["pending"][0]["liquid_strikes"] = [1300.0]
    q.set(1300.0, 40.0, ask=40.0)
    rt.on_poll(at(14, 9, 16))
    rt.on_poll(at(14, 15, 20))
    r = [x for x in lg.state["rules"]["refused"] if x["mode"] == "open"]
    assert len(r) == 1 and "more than Rs 8,000" in r[0]["reason"]


# ---------------------------------------------------------------- the lot-size range (the user's idea, 2026-10-19)
def test_banned_today_only_reads_a_list_for_today():
    f = {"session": "2026-10-14", "ban": ["HCLTECH", "RBLBANK"]}
    assert R.banned_today(f, date(2026, 10, 14)) == {"HCLTECH", "RBLBANK"}
    assert R.banned_today(f, date(2026, 10, 15)) == set()            # yesterday's list blocks nothing
    assert R.banned_today({"session": "2026-10-14"}, date(2026, 10, 14)) == set()
    assert R.banned_today(None, date(2026, 10, 14)) == set()


def test_a_stock_in_the_fo_ban_is_refused_by_both_entries(tmp_path):
    q = Quotes()
    lg = PaperLedger(tmp_path, q, capital=500_000, clock=lambda: at(14, 9, 16))
    fade = {"session": "2026-10-14", "ban": ["HCLTECH"]}
    rt = R.RuleTrader(lg, lambda: fw(), fade=lambda: fade)
    q.set(1300.0, 19.0, ask=19.2)                                    # it would fit
    rt.on_poll(at(14, 9, 16))
    r = lg.state["rules"]["refused"]
    assert [(x["mode"], x["reason"]) for x in r] == [("open", "in the F&O ban today")] and lg.state["positions"] == []
    assert lg.state["rules"]["open"]["2026-10-14:HCLTECH"] == "refused" and lg.state["rules"]["open_wait"] == {}
    rt.on_poll(at(14, 15, 20))
    assert [(x["mode"], x["reason"]) for x in lg.state["rules"]["refused"]] == [
        ("open", "in the F&O ban today"), ("close", "in the F&O ban today")]
    assert lg.state["positions"] == []


def test_a_ban_list_for_another_session_blocks_nothing(tmp_path):
    q = Quotes()
    lg = PaperLedger(tmp_path, q, capital=500_000, clock=lambda: at(14, 9, 16))
    rt = R.RuleTrader(lg, lambda: fw(), fade=lambda: {"session": "2026-10-13", "ban": ["HCLTECH"]})
    q.set(1300.0, 19.0, ask=19.2)
    rt.on_poll(at(14, 9, 16))
    assert len(lg.state["positions"]) == 1


def test_never_fits_from_the_lot_alone():
    why = R.never_fits(5425)                                         # IRFC: Rs 8,000 / 5,425 = Rs 1.47 a share
    assert why == "never fits: 1 lot is 5,425 shares, so Rs 8,000 allows at most Rs 1.47 a share, below the Rs 2 floor"
    assert R.never_fits(400) is None and R.never_fits(4000) is None   # HCLTECH: Rs 2-20; 4,000: exactly Rs 2
    assert R.never_fits(0) is None                                   # lot unknown: walk as before


def test_a_never_fit_stock_is_refused_at_once_both_entries(setup):
    lg, q, rt, box = setup
    for a in ("A", "B"):
        box["fw"]["arms"][a]["pending"][0]["liquid_strikes"] = [1300.0, 1350.0]
    for k in (1300.0, 1350.0, 1400.0):
        q.set(k, 1.2, ask=1.2, lot=5425)
    rt.on_poll(at(14, 9, 16))
    r = lg.state["rules"]["refused"]
    assert [x["mode"] for x in r] == ["open"] and r[0]["reason"].startswith("never fits: 1 lot is 5,425 shares")
    assert lg.state["rules"]["open"]["2026-10-14:HCLTECH"] == "refused" and lg.state["rules"]["open_wait"] == {}
    rt.on_poll(at(14, 15, 20))
    assert [x["mode"] for x in lg.state["rules"]["refused"]] == ["open", "close"]
    assert lg.state["rules"]["refused"][1]["reason"].startswith("never fits") and lg.state["positions"] == []


def test_each_try_prices_all_its_strikes_in_one_call(setup):
    lg, q, rt, box = setup
    calls = []
    q.get_many = lambda cs: calls.append([c["strike"] for c in cs]) or {c["tradingsymbol"]: q.book.get(c["tradingsymbol"]) for c in cs}
    for a in ("A", "B"):
        box["fw"]["arms"][a]["pending"][0]["liquid_strikes"] = [1300.0, 1350.0, 1400.0]
    for k in (1300.0, 1350.0):
        q.set(k, 40.0, ask=40.0)                                     # dear
    q.set(1400.0, 20.0, ask=20.0)                                    # Rs 7,000 a lot
    rt.on_poll(at(14, 9, 16))
    assert calls == [[1300.0, 1350.0, 1400.0]]
    (p,) = lg.state["positions"]
    assert p["strike"] == 1400.0 and p["entry"]["price"] == 20.0


def test_quote_source_get_many_uses_one_provider_call():
    from server.paper import QuoteSource

    class Prov:
        calls = []
        def quote_many(self, tss):
            self.calls.append(list(tss))
            return {t: {"lot_size": 400, "depth": {"ask": [(10.0, 1)]}} for t in tss if not t.endswith("1400CE")}

    class Feed:
        provider = Prov()
        def snapshot(self):
            return {"quotes": {"HCLTECH": {"ltp": 1301.0}}}

    cs = [{"symbol": "HCLTECH", "instrument": "CE", "tradingsymbol": TS[k]} for k in (1300.0, 1400.0)]
    got = QuoteSource(Feed()).get_many(cs)
    assert Feed.provider.calls == [[TS[1300.0], TS[1400.0]]]
    assert got[TS[1300.0]]["underlying"] == 1301.0 and got[TS[1400.0]] is None


# ---------------------------------------------------------------- the 26 Oct 2026 stale list (page and server agree)
def test_a_list_missing_a_session_is_stale_and_the_next_session_is_current():
    from datetime import date
    from server.rules import forward_is_current, signals_for
    fw = {"last_session": "2026-10-22", "arms": {"A": {"pending": [{"symbol": "INDHOTEL"}]}}}      # made after Thursday
    assert forward_is_current(fw, date(2026, 10, 23)) is True                                       # Friday: its session
    assert forward_is_current(fw, date(2026, 10, 26)) is False                                      # Monday: Friday was missed
    assert signals_for(fw, date(2026, 10, 26)) == []                                                # the trader agrees
    fri = {**fw, "last_session": "2026-10-23"}
    assert forward_is_current(fri, date(2026, 10, 26)) is True                                      # weekend skipped
    assert forward_is_current(None, date(2026, 10, 26)) is False and forward_is_current({}, date(2026, 10, 26)) is False


def test_the_results_page_is_told_whether_the_forward_list_is_for_today(monkeypatch):
    from datetime import datetime
    import server.app as app_mod
    stale = {"last_session": "2026-10-22", "arms": {}}
    monkeypatch.setattr(app_mod, "datetime", type("D", (datetime,), {"now": classmethod(lambda cls, tz=None: datetime(2026, 10, 26, 9, 30, tzinfo=tz))}))
    assert app_mod._forward_for_page(stale)["for_today"] is False
    assert app_mod._forward_for_page(None) is None


def test_the_0915_buy_waits_for_the_first_trade_today_and_15_20_refuses_an_option_with_none(setup):
    lg, q, rt, box = setup                                          # 27 Oct 2026: Arm A bought at yesterday's ask too
    q.set(1300.0, 10.0, ask=10.0)
    q.book[TS[1300.0]]["timestamp"] = "2026-10-13 15:29:59"
    rt.on_poll(at(14, 9, 15, 2))
    assert lg.state["positions"] == [] and not lg.state["rules"]["refused"]
    assert "first trade today" in lg.state["rules"]["open_wait"]["2026-10-14:HCLTECH"]["reason"]
    q.set(1300.0, 6.0, ask=6.0)
    q.book[TS[1300.0]]["timestamp"] = "2026-10-14 09:16:02"
    rt.on_poll(at(14, 9, 16, 5))
    assert [p["entry"]["price"] for p in lg.state["positions"]] == [6.0]


def test_the_15_20_buy_refuses_an_option_that_has_not_traded_today(setup):
    lg, q, rt, box = setup
    for k in (1300.0, 1350.0, 1400.0):
        q.set(k, 10.0, ask=10.0)
        q.book[TS[k]]["timestamp"] = "2026-10-13 15:29:59"
    rt.on_poll(at(14, 15, 20))
    assert not [p for p in lg.state["positions"] if p.get("rule", {}).get("mode") == "close"]
    assert any("not traded today" in r.get("reason", "") or "the quote is yesterday's" in r.get("reason", "")
               for r in lg.state["rules"]["refused"])
