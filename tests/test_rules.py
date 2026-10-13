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


def at(d, h, m=0):
    return datetime(2026, 10, d, h, m, tzinfo=IST)


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
    assert close["entry"]["price"] == 20.05 and close["strike"] == 1300.0
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
