"""Step 5: the paper ledger. Entries, marks, manual/stop/T-2 exits, the market-closed queue, P&L, API."""
import json
from datetime import datetime

import pytest

from server import charges as ch
from server.broker import OrderRequest, PaperBroker
from server.paper import PaperLedger, PaperRejected
from server.sessions import IST

EXP = "2026-09-29"                          # Tuesday expiry: T-1 Mon 28, T-2 Fri 25
CE = "RELIANCE26SEP1300CE"
FUT = "RELIANCE26SEPFUT"


@pytest.fixture(autouse=True)
def allow_lottery(monkeypatch):
    """These tests cover the engine with the cheap / near-expiry bucket switched on (ALLOW_LOTTERY=true)."""
    from server.config import settings
    monkeypatch.setattr(settings, "allow_lottery", True)


def at(day, hh=10, mm=0):
    return datetime(2026, 9, day, hh, mm, tzinfo=IST)


CLOCK = lambda: at(22)                      # every ledger built here reads this, never the machine's clock:
                                            # Tue 22 Sep, 5 sessions before the 29 Sep expiry the tests trade


class StubQuotes:
    """Quote source whose book the test sets directly."""
    def __init__(self):
        self.book, self.last_error = {}, None

    def set(self, ts, bid, ask, oi=100 * 500, bid_qty=5000, ask_qty=5000):
        bids = bid if isinstance(bid, list) else ([(bid, bid_qty)] if bid is not None else [])
        asks = ask if isinstance(ask, list) else ([(ask, ask_qty)] if ask is not None else [])
        self.book[ts] = {"depth": {"bid": bids, "ask": asks}, "open_interest": oi, "last_price": (asks or bids)[0][0]}

    def get(self, contract, fresh=True):
        return self.book.get(contract["tradingsymbol"])

    def spot(self, symbol):
        return 1250.0


def order(instrument="CE", side="BUY", lots=1, expiry=EXP, strike=1300.0, order_type="MARKET", price=None):
    return OrderRequest("RELIANCE", instrument, expiry, strike if instrument != "FUT" else None, side, lots, order_type, price)


def resolved(ts, lots=1):
    return {"tradingsymbol": ts, "quantity": 500 * lots, "lot_size": 500, "exchange": "NFO"}


@pytest.fixture
def lg(tmp_path):
    q = StubQuotes()
    ledger = PaperLedger(tmp_path, q, capital=500_000, clock=CLOCK)
    return ledger, q


def test_long_option_entry_charges_cash_and_mark(lg):
    ledger, q = lg
    q.set(CE, 4.0, 4.1)                                          # 2.5% spread, 100 lots OI: accept
    rec = ledger.submit(order(), resolved(CE), now=at(21))
    assert rec["status"] == "FILLED" and rec["fill_price"] == 4.15 and rec["liquidity_class"] == "accept"
    entry_ch = ch.leg("CE", "BUY", 500, 4.15)["total"]
    assert ledger.state["cash"] == pytest.approx(500_000 - 4.15 * 500 - entry_ch, abs=0.01)
    pos = ledger.positions_view()[0]
    assert pos["bucket"] == "normal" and pos["entry"]["class"] == "accept" and pos["t2_date"] == "2026-09-25"

    q.set(CE, 5.0, 5.1)
    ledger.on_poll(now=at(21, 11))
    pos = ledger.positions_view()[0]
    assert pos["mark"]["price"] == 5.0                           # long marked at the bid
    exit_ch = ch.leg("CE", "SELL", 500, 5.0)["total"]
    assert pos["unrealised"] == pytest.approx((5.0 - 4.15) * 500 - entry_ch - exit_ch, abs=0.01)
    assert ledger.equity() == pytest.approx(500_000 + pos["unrealised"], abs=0.02)


def test_manual_exit_realises_net_of_both_legs(lg):
    ledger, q = lg
    q.set(CE, 4.0, 4.1)
    ledger.submit(order(), resolved(CE), now=at(21))
    q.set(CE, 5.0, 5.1)
    rec = ledger.submit(order(side="SELL"), resolved(CE), now=at(22))
    assert rec["intent"] == "exit" and rec["fill_price"] == 4.95        # bid 5.00 - 1 tick
    t = ledger.trades_view()[0]
    expected = (4.95 - 4.15) * 500 - ch.leg("CE", "BUY", 500, 4.15)["total"] - ch.leg("CE", "SELL", 500, 4.95)["total"]
    assert t["net_pnl"] == pytest.approx(expected, abs=0.02) and t["reason"] == "manual"
    assert not ledger.positions_view()
    assert ledger.equity() == pytest.approx(500_000 + t["net_pnl"], abs=0.02)
    assert t["return_pct"] == pytest.approx(t["net_pnl"] / (4.15 * 500) * 100, abs=0.01)


def test_partial_exit_keeps_the_rest_open(lg):
    ledger, q = lg
    q.set(CE, 4.0, 4.1)
    ledger.submit(order(lots=2), resolved(CE, 2), now=at(21))
    q.set(CE, 5.0, 5.1)
    ledger.submit(order(side="SELL"), resolved(CE), now=at(22))
    pos = ledger.positions_view()[0]
    assert pos["lots"] == 1 and pos["qty"] == 500 and len(ledger.trades_view()) == 1
    with pytest.raises(PaperRejected):
        ledger.submit(order(side="SELL", lots=2), resolved(CE, 2), now=at(22))    # bigger than what is open


def test_stop_exits_at_the_next_polls_book_not_at_the_stop_price(lg):
    ledger, q = lg
    q.set(FUT, 1000.0, 1000.1, oi=10_000_000)
    rec = ledger.submit(order("FUT"), resolved(FUT), stop=995.0, now=at(21))
    assert rec["fill_price"] == 1000.15
    q.set(FUT, 994.0, 994.1, oi=10_000_000)
    ledger.on_poll(now=at(21, 11))                               # trigger: bid 994 <= 995
    pos = ledger.positions_view()[0]
    assert pos["stop_triggered_at"] and not ledger.trades_view()
    q.set(FUT, [(990.0, 300), (989.5, 300)], 990.1, oi=10_000_000)
    ledger.on_poll(now=at(21, 11, 1))                            # the first poll after the trigger
    t = ledger.trades_view()[0]
    # walk 300 @ 990 + 200 @ 989.5 = 989.80, minus a tick; the exit is 83% of the visible bids (refuse class for
    # an entry), and exits are never refused: they fill in penalty mode, a further half spread (0.05) lower
    assert t["reason"] == "stop" and t["exit"]["class"] == "refuse" and t["exit"]["mode"] == "penalty"
    assert t["exit"]["price"] == 989.70 and t["exit"]["price"] != 995.0


def test_forced_exit_at_t2_waits_for_0920(lg):
    ledger, q = lg
    q.set(CE, 4.0, 4.1)
    ledger.submit(order(), resolved(CE), now=at(21))
    ledger.on_poll(now=at(25, 9, 19))
    assert ledger.positions_view()                               # T-2, but before 09:20
    ledger.on_poll(now=at(25, 9, 20))
    assert not ledger.positions_view() and ledger.trades_view()[0]["reason"] == "forced_t2"


def test_position_opened_on_t2_is_forced_out_at_the_next_sessions_0920(lg):
    ledger, q = lg
    q.set(CE, 4.0, 4.1)
    rec = ledger.submit(order(), resolved(CE), now=at(25, 11))
    assert rec["bucket"] == "cheap_near_expiry"                  # 2 sessions to expiry: lottery bucket
    ledger.on_poll(now=at(25, 14))
    assert ledger.positions_view()
    ledger.on_poll(now=at(28, 9, 20))
    assert ledger.trades_view()[0]["reason"] == "forced_t2"


def test_market_closed_order_queues_and_fills_at_0920_on_that_polls_depth(lg, tmp_path):
    ledger, q = lg
    ts = "RELIANCE26OCT1300CE"
    q.set(ts, 10.0, 10.2)
    rec = ledger.submit(order(expiry="2026-10-27"), resolved(ts), now=at(26, 11))     # Saturday
    assert rec["status"] == "QUEUED" and rec["fill_after"].startswith("2026-09-28T09:20")
    assert not ledger.positions_view() and len(ledger.queue.pending()) == 1
    q.set(ts, 12.0, 12.2)
    ledger.on_poll(now=at(28, 9, 19))
    assert not ledger.positions_view()
    ledger.on_poll(now=at(28, 9, 20))
    pos = ledger.positions_view()[0]
    assert pos["entry"]["price"] == 12.25                        # that poll's ask + 1 tick, not Saturday's
    assert not ledger.queue.pending()
    orders = PaperBroker(tmp_path).orders()
    assert orders[0]["order_id"] == rec["order_id"] and orders[0]["status"] == "FILLED"


def test_lottery_fill_is_tagged_cheap_near_expiry(lg):
    ledger, q = lg
    q.set(CE, 1.0, 1.4, oi=500)                                  # wide spread, 1 lot of OI: lottery, not refused
    rec = ledger.submit(order(), resolved(CE), now=at(21))
    assert rec["liquidity_class"] == "lottery" and rec["bucket"] == "cheap_near_expiry"
    assert rec["fill_price"] == 1.45


def test_blocks_future_without_stop_bad_liquidity_and_limit(lg, tmp_path):
    ledger, q = lg
    q.set(FUT, 1000.0, 1000.1, oi=10_000_000)
    with pytest.raises(PaperRejected, match="stop"):
        ledger.submit(order("FUT"), resolved(FUT), now=at(21))
    q.set(CE, 10.0, 11.0)                                        # 9.5% spread
    with pytest.raises(PaperRejected, match="liquidity"):
        ledger.submit(order(), resolved(CE), now=at(21))
    refusals = [json.loads(l) for l in (tmp_path / "refusals.jsonl").read_text().splitlines()]
    assert refusals[-1]["contract"] == CE and refusals[-1]["stage"] == "place"
    q.set(CE, 10.0, 10.2)
    with pytest.raises(PaperRejected, match="limit"):
        ledger.submit(order(order_type="LIMIT", price=10.2), resolved(CE), now=at(21))   # fill 10.25 > limit


def test_summary_day_week_drawdown_and_margin(lg):
    ledger, q = lg
    q.set(CE, 4.0, 4.1)
    ledger.submit(order(), resolved(CE), now=at(21))
    q.set(CE, 2.0, 2.1)
    ledger.on_poll(now=at(21, 12))
    s = ledger.summary(now=at(21, 12))
    assert s["open_margin"] == pytest.approx(4.15 * 500)         # long option: the premium
    assert s["day_pnl"] < 0 and s["week_pnl"] == s["day_pnl"]
    assert s["drawdown_pct"] > 0 and s["equity"] == pytest.approx(500_000 + s["day_pnl"], abs=0.01)
    assert s["open_positions"] == 1 and s["capital"] == 500_000


def test_ledger_survives_a_restart(lg, tmp_path):
    ledger, q = lg
    q.set(CE, 4.0, 4.1)
    ledger.submit(order(), resolved(CE), now=at(21))
    again = PaperLedger(tmp_path, q, clock=CLOCK)
    assert again.positions_view()[0]["tradingsymbol"] == CE and again.state["cash"] == ledger.state["cash"]


def test_no_live_depth_means_no_fill(tmp_path):
    ledger = PaperLedger(tmp_path, None, capital=500_000, clock=CLOCK)
    with pytest.raises(PaperRejected, match="no live depth"):
        ledger.submit(order(), resolved(CE), now=at(21))


def test_api_preview_place_and_paper_endpoints(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from server import app as app_mod
    from server.config import settings

    q = StubQuotes()
    q.set(CE, 4.0, 4.1)
    ledger = PaperLedger(tmp_path, q, capital=500_000, always_open=True, clock=CLOCK)
    monkeypatch.setattr(settings, "app_password", "pw")
    monkeypatch.setattr(app_mod.state, "ledger", ledger)
    monkeypatch.setattr(app_mod.state, "broker", PaperBroker(tmp_path, ledger))
    monkeypatch.setattr(app_mod.state, "stocks", {"RELIANCE": {"symbol": "RELIANCE", "close": 1250.0, "lot_size": 500,
                                                               "chain": {"expiry": EXP, "strikes": []}}})
    c = TestClient(app_mod.app)
    body = {"symbol": "RELIANCE", "instrument": "CE", "expiry": EXP, "strike": 1300, "side": "BUY", "lots": 1,
            "order_type": "MARKET"}
    pv = c.post("/api/order/preview", json=body, auth=("user", "pw")).json()
    assert pv["token"] and pv["review"]["fill"]["price"] == 4.15 and pv["review"]["liquidity"]["class"] in ("accept", "lottery")
    placed = c.post("/api/order", json={**body, "token": pv["token"]}, auth=("user", "pw")).json()
    assert placed["status"] == "FILLED"
    assert c.get("/api/paper/summary", auth=("user", "pw")).json()["open_positions"] == 1
    assert c.get("/api/paper/positions", auth=("user", "pw")).json()[0]["tradingsymbol"] == CE
    assert c.get("/api/paper/trades", auth=("user", "pw")).json()["trades"] == []
    blocked = c.post("/api/order/preview", json={**body, "instrument": "FUT", "strike": None}, auth=("user", "pw")).json()
    assert blocked["token"] is None and any("stop" in b for b in blocked["review"]["blocked"])
