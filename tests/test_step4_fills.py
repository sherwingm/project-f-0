"""Step 4: fill engine (walks, VWAP, overflow, tick rounding, penalty, lottery) and the queue calendar."""
from datetime import datetime

import pytest

from server import sessions
from server.config import settings
from server.fills import NoLiquidity, PaperQueue, fill, round_to_tick

IST = sessions.IST


def test_single_level_fill_adds_one_tick_of_latency():
    r = fill("BUY", 500, {"bid": [(99.9, 1000)], "ask": [(100.0, 1000)]})
    assert r["price"] == 100.05
    assert r["levels"] == [{"price": 100.0, "qty": 500}] and r["overflow_qty"] == 0
    assert r["mid"] == 99.95 and r["slippage_vs_mid"] == pytest.approx(0.10)
    assert r["slippage_value"] == pytest.approx(50.0)


def test_multi_level_vwap_buy_and_sell():
    buy = fill("BUY", 500, {"bid": [(99.9, 300)], "ask": [(100.0, 300), (100.1, 300), (100.2, 300)]})
    assert buy["levels"] == [{"price": 100.0, "qty": 300}, {"price": 100.1, "qty": 200}]
    assert buy["vwap"] == pytest.approx(100.04)                 # (300 x 100.0 + 200 x 100.1) / 500
    assert buy["price"] == 100.10                               # 100.04 + 0.05 = 100.09, rounded up to the tick
    sell = fill("SELL", 500, {"bid": [(99.9, 300), (99.8, 300)], "ask": [(100.0, 300)]})
    assert sell["vwap"] == pytest.approx(99.86)
    assert sell["price"] == 99.80                               # 99.86 - 0.05 = 99.81, rounded down to the tick
    assert sell["slippage_vs_mid"] == pytest.approx(99.95 - 99.80)


def test_overflow_beyond_visible_depth_prices_at_worst_level_plus_a_spread():
    r = fill("BUY", 800, {"bid": [(99.9, 1000)], "ask": [(100.0, 300), (100.1, 200)]})
    assert r["overflow_qty"] == 300
    assert r["levels"][-1] == {"price": 100.2, "qty": 300, "overflow": True}     # 100.1 + spread 0.1
    assert r["vwap"] == pytest.approx((300 * 100.0 + 200 * 100.1 + 300 * 100.2) / 800)
    assert r["price"] == 100.15


def test_overflow_on_a_sell_goes_below_the_worst_bid():
    r = fill("SELL", 300, {"bid": [(50.0, 100)], "ask": [(50.5, 100)]})
    assert r["overflow_qty"] == 200 and r["levels"][-1]["price"] == 49.5
    assert r["price"] == round_to_tick((100 * 50.0 + 200 * 49.5) / 300 - 0.05, 0.05, up=False)


def test_tick_rounding_is_against_the_order():
    r = fill("BUY", 500, {"bid": [(99.95, 100)], "ask": [(100.0, 300), (100.05, 200)]})
    assert r["vwap"] == pytest.approx(100.02) and r["price"] == 100.10
    assert round_to_tick(100.0, 0.05, up=True) == 100.0         # already on the tick: unchanged
    assert round_to_tick(10.01, 0.05, up=True) == 10.05
    assert round_to_tick(10.04, 0.05, up=False) == 10.0


def test_penalty_adds_half_a_spread():
    book = {"bid": [(99.8, 1000)], "ask": [(100.0, 1000)]}
    assert fill("BUY", 500, book, mode="penalty")["price"] == 100.15      # 100 + 0.05 tick + 0.10 half spread
    assert fill("SELL", 500, book, mode="penalty")["price"] == 99.65      # 99.8 - 0.05 - 0.10


def test_lottery_fills_at_best_level_one_tick_worse_regardless_of_spread():
    book = {"bid": [(0.5, 100), (0.45, 5000)], "ask": [(1.0, 100), (1.05, 5000)]}
    buy = fill("BUY", 500, book, mode="lottery")
    assert buy["price"] == 1.05 and buy["levels"] == [{"price": 1.0, "qty": 500}]
    assert fill("SELL", 500, book, mode="lottery")["price"] == 0.45
    assert fill("SELL", 100, {"bid": [(0.05, 100)], "ask": []}, mode="lottery")["price"] == 0.0


def test_empty_side_raises_no_liquidity():
    with pytest.raises(NoLiquidity):
        fill("BUY", 1, {"bid": [(10.0, 5)], "ask": []})


def test_queue_fill_time_is_the_next_sessions_0920():
    fri_evening = datetime(2026, 9, 25, 16, 0, tzinfo=IST)
    assert sessions.next_fill_time(fri_evening) == datetime(2026, 9, 28, 9, 20, tzinfo=IST)     # Monday
    mon_early = datetime(2026, 9, 28, 8, 0, tzinfo=IST)
    assert sessions.next_fill_time(mon_early) == datetime(2026, 9, 28, 9, 20, tzinfo=IST)
    assert sessions.next_fill_time(datetime(2026, 9, 26, 11, 0, tzinfo=IST)).date().isoformat() == "2026-09-28"


def test_holidays_are_skipped(monkeypatch):
    monkeypatch.setattr(settings, "nse_holidays", "2026-10-02")
    thu_evening = datetime(2026, 10, 1, 18, 0, tzinfo=IST)
    assert sessions.next_fill_time(thu_evening).date().isoformat() == "2026-10-05"
    assert sessions.sessions_to_expiry("2026-09-29", "2026-10-06") == 4           # 30, 1, 5, 6 (2nd is a holiday)


def test_sessions_to_expiry_and_t_minus_agree():
    assert sessions.sessions_to_expiry("2026-09-24", "2026-09-29") == 3           # Fri, Mon, Tue
    t2 = sessions.t_minus("2026-09-29", 2)
    assert t2.isoformat() == "2026-09-25"                                          # Tue expiry: T-1 Mon, T-2 Fri
    assert sessions.sessions_to_expiry(t2, "2026-09-29") == 2


def test_paper_queue_round_trip(tmp_path):
    q = PaperQueue(tmp_path / "paper_queue.jsonl")
    q.add({"order_id": "A", "x": 1}); q.add({"order_id": "B", "x": 2})
    assert [o["order_id"] for o in q.pending()] == ["A", "B"]
    q.remove({"A"})
    assert [o["order_id"] for o in q.pending()] == ["B"]
