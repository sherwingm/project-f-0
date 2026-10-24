"""Paper rule trades filled as real orders (server/order_sim.py, PaperLedger.buy_rule / work_orders;
strategies/S1_paper_real_order_fills.md)."""
from datetime import datetime

import pytest

from server import fade as F
from server import order_sim as om
from server import rules as R
from server.paper import PaperLedger
from server.sessions import IST

from .test_fade import Quotes as FadeQuotes, sig
from .test_rules import Quotes as RuleQuotes, fw

KEY = "2026-10-15:HCLTECH"
TS = "HCLTECH26OCT1200PE"


def at(d, h, m=0, s=0):
    return datetime(2026, 10, d, h, m, s, tzinfo=IST)


def book(q, bids, asks, ltp=None):
    """Several levels for HCLTECH 1200 PE: bids / asks as [(price, qty), ...]."""
    q.book[TS] = {"last_price": ltp or asks[0][0], "atp": asks[0][0], "volume": 0, "lot_size": 350,
                  "depth": {"bid": bids, "ask": asks}}


@pytest.fixture
def setup(tmp_path):
    q = FadeQuotes()
    lg = PaperLedger(tmp_path, q, capital=500_000, clock=lambda: at(15, 9, 16), real_orders=True)
    box = {"f": sig()}
    return lg, q, F.FadeTrader(lg, lambda: box["f"]), box


# ---------------------------------------------------------------- the pure rules
def test_protection_bands_and_limits():
    assert om.protection(0.5) == 0.10
    assert om.protection(4.0) == pytest.approx(0.40)              # 10 %
    assert om.protection(8.0) == pytest.approx(0.40)              # 5 %
    assert om.protection(18.5) == pytest.approx(0.555)            # 3 %
    assert om.protection(200.0) == pytest.approx(4.0)             # 2 %
    assert om.buy_limit(18.5, 0.05) == 19.10 and om.buy_limit(18.5, 0.01) == 19.06
    assert om.sell_limit(14.0, 0.01) == 13.58
    assert om.tick_for(1225.0) == 0.05 and om.tick_for(120.0) == 0.01 and om.tick_for(None) == 0.05


def test_rejections():
    assert "no last traded price" in om.rejected(19.1, None)
    assert om.rejected(19.1, 18.5) is None
    assert "price protection" in om.rejected(45.0, 18.5)          # > Rs 20 away below Rs 50
    assert om.rejected(130.0, 100.0) is None and "protection" in om.rejected(141.0, 100.0)   # 40 % above Rs 50


def test_match_needs_the_whole_order_within_the_limit():
    d = {"ask": [(18.5, 200), (18.6, 200), (19.5, 5000)], "bid": [(18.0, 100)]}
    m = om.match("BUY", 350, 19.06, d)
    assert m["price"] == pytest.approx((18.5 * 200 + 18.6 * 150) / 350, abs=1e-4) and len(m["levels"]) == 2
    assert om.match("BUY", 500, 19.06, d) is None                 # only 400 within the limit
    s = {"bid": [(14.0, 100), (13.9, 100), (13.0, 9000)], "ask": [(14.2, 100)]}
    assert om.match("SELL", 350, 13.58, s) is None
    w = om.sweep(350, s)
    assert w["price"] == pytest.approx((14.0 * 100 + 13.9 * 100 + 13.0 * 150) / 350, abs=1e-4)
    o = om.sweep(350, {"bid": [(14.0, 100)], "ask": [(14.2, 100)]})
    assert o["levels"][-1] == {"price": 13.8, "qty": 250, "overflow": True}


# ---------------------------------------------------------------- the fade buy
def test_buy_fills_from_the_next_quote_not_the_decision(setup):
    lg, q, ft, _ = setup
    q.set("PE", 1200.0, 18.0, 18.5)
    ft.on_poll(at(15, 9, 16))
    assert lg.state["positions"] == [] and lg.state["rules"]["fade"][KEY] == "ordered"
    assert "buy order working" in lg.state["rules"]["fade_wait"][KEY]["reason"]
    lg.work_orders(at(15, 9, 16))                                  # the same second: still travelling
    assert lg.state["positions"] == []
    book(q, [(18.2, 5000)], [(18.7, 5000)])                       # the ask moved up by the next second
    lg.work_orders(at(15, 9, 16, 1))
    (p,) = lg.state["positions"]
    assert p["entry"]["price"] == 18.7                             # the book it met, not the decision's 18.5
    assert p["order"]["decision_price"] == 18.5 and p["order"]["limit"] == 19.1 and p["order"]["wait_s"] == 1.0
    assert p["rule"]["stop"]["level"] == round(18.7 * 0.8, 4)     # levels from the fill price
    assert p["rule"]["trail"]["start"] == round(18.7 * 1.10, 4)
    assert lg.state["rules"]["fade"][KEY] == "bought" and KEY not in lg.state["rules"]["fade_wait"]


def test_unfilled_buy_cancels_after_60_s_and_the_walk_retries(setup):
    lg, q, ft, _ = setup
    book(q, [(18.0, 5000)], [(18.5, 100), (25.0, 5000)])           # only 100 of 350 within the limit
    ft.on_poll(at(15, 9, 16))
    for s in range(1, 60):
        lg.work_orders(at(15, 9, 16, s))
    assert lg.state["positions"] == [] and lg.state["rules"]["fade"][KEY] == "ordered"
    lg.work_orders(at(15, 9, 17, 0))
    assert KEY not in lg.state["rules"]["fade"]
    assert "not filled" in lg.state["rules"]["fade_wait"][KEY]["reason"]
    book(q, [(18.0, 5000)], [(18.5, 5000)])
    ft.on_poll(at(15, 9, 17, 1))                                   # the walk orders again
    lg.work_orders(at(15, 9, 17, 2))
    assert lg.state["positions"][0]["entry"]["price"] == 18.5


def test_buy_without_a_last_price_is_rejected(setup):
    lg, q, ft, _ = setup
    q.set("PE", 1200.0, 18.0, 18.5)
    q.book[TS]["last_price"] = None
    ft.on_poll(at(15, 9, 16))
    assert lg.state["positions"] == [] and KEY not in lg.state["rules"]["fade"]
    assert "no last traded price" in lg.state["rules"]["fade_wait"][KEY]["reason"]


# ---------------------------------------------------------------- the sale
def _bought(lg, q, ft):
    q.set("PE", 1200.0, 18.0, 18.5)
    ft.on_poll(at(15, 9, 16))
    lg.work_orders(at(15, 9, 16, 1))
    return lg.state["positions"][0]


def test_stop_sells_at_the_next_quotes_bid_and_keeps_the_instant_price(setup):
    lg, q, ft, _ = setup
    p = _bought(lg, q, ft)
    book(q, [(14.0, 5000)], [(14.3, 5000)])                       # below the stop (14.8)
    ft.on_poll(at(15, 10, 0))
    assert lg.state["closed"] == [] and p["exiting"]["reason"] == "fade_stop"
    peak_n = p["held_bid"]["n"]
    ft.on_poll(at(15, 10, 0, 0))                                   # the stop does not fire twice
    book(q, [(13.6, 5000)], [(13.9, 5000)])
    lg.observe(p, q.book[TS], at(15, 10, 0, 1), "test")            # no longer held: not in the peak
    assert p["held_bid"]["n"] == peak_n
    lg.work_orders(at(15, 10, 0, 1))
    (c,) = lg.state["closed"]
    assert c["exit"]["price"] == 13.6 and c["reason"] == "fade_stop"
    assert c["instant"]["entry"] == 18.5 and c["instant"]["exit"] == 14.0
    assert c["fill_cost_rs"] == pytest.approx(c["instant"]["net"] - c["net_pnl"]) and c["fill_cost_rs"] > 0
    assert c["exit_order"]["decision_price"] == 14.0 and c["entry_order"]["decision_price"] == 18.5
    assert c["peak_capture"] is not None and c["post_exit_until"]


def test_a_thin_bid_is_chased_then_swept(setup):
    lg, q, ft, _ = setup
    _bought(lg, q, ft)
    book(q, [(14.0, 100), (13.9, 100), (12.0, 100)], [(14.3, 5000)])
    ft.on_poll(at(15, 10, 0))
    for s in range(1, 10):
        lg.work_orders(at(15, 10, 0, s))
    assert lg.state["closed"] == []                                # 13.58 limit: only 200 of 350
    lg.work_orders(at(15, 10, 0, 10))
    (c,) = lg.state["closed"]
    assert c["exit_order"]["swept"] is True
    assert c["exit"]["price"] == pytest.approx((14.0 * 100 + 13.9 * 100 + 12.0 * 100 + (12.0 - 0.3) * 50) / 350, abs=1e-4)


def test_a_working_sell_survives_a_restart(setup, tmp_path):
    lg, q, ft, _ = setup
    _bought(lg, q, ft)
    book(q, [(14.0, 5000)], [(14.3, 5000)])
    ft.on_poll(at(15, 10, 0))
    lg2 = PaperLedger(tmp_path, q, capital=500_000, clock=lambda: at(15, 10, 1), real_orders=True)
    lg2.work_orders(at(15, 10, 1))
    assert lg2.state["positions"] == [] and lg2.state["closed"][0]["reason"] == "fade_stop"


def test_a_buy_lost_in_a_restart_waits_again(setup, tmp_path):
    lg, q, ft, _ = setup
    q.set("PE", 1200.0, 18.0, 18.5)
    ft.on_poll(at(15, 9, 16))
    lg._save()
    lg2 = PaperLedger(tmp_path, q, capital=500_000, clock=lambda: at(15, 9, 17), real_orders=True)
    assert KEY not in lg2.state["rules"]["fade"]


def test_instant_fills_unchanged_when_off(tmp_path):
    q = FadeQuotes()
    lg = PaperLedger(tmp_path, q, capital=500_000, clock=lambda: at(15, 9, 16))
    ft = F.FadeTrader(lg, lambda: sig())
    q.set("PE", 1200.0, 18.0, 18.5)
    ft.on_poll(at(15, 9, 16))
    assert lg.state["positions"][0]["entry"]["price"] == 18.5 and "order" not in lg.state["positions"][0]


# ---------------------------------------------------------------- arms A / B
def test_the_15_20_close_entry_pays_the_real_ask_not_the_atp(tmp_path):
    q = RuleQuotes()
    lg = PaperLedger(tmp_path, q, capital=500_000, clock=lambda: at(14, 15, 20), real_orders=True)
    rt = R.RuleTrader(lg, lambda: fw())
    q.set(1300.0, 19.0, bid=19.4, ask=19.6, atp=17.0)              # the day's average far below 15:20
    rt.on_poll(at(14, 15, 20))
    st = lg.state["rules"]
    assert st["close"]["2026-10-14:HCLTECH"] == "ordered"
    lg.work_orders(at(14, 15, 20, 1))
    p = next(p for p in lg.state["positions"] if p["rule"]["entry_mode"] == "close")
    assert p["entry"]["price"] == 19.6 and p["order"]["old_price"] == 17.01
    assert st["close"]["2026-10-14:HCLTECH"] == "bought"
