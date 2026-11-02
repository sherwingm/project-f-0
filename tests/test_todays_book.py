"""Buys wait for today's order book (strategies/S1_paper_entry_todays_book.md): server/peak.py old_book, used by the
fade / Arm A-B entry walks and the real-order fill."""
from datetime import datetime

import pytest

from server import peak as pk
from server.sessions import IST

from .test_peak_capture import ledger
from .test_real_orders import KEY, TS, at, setup  # noqa: F401  (pytest fixture)


def t(h, m, s=0):
    return datetime(2026, 10, 15, h, m, s, tzinfo=IST)


def sq(volume, open_=None, ltt="2026-10-15 09:15:01", source="upstox_stream"):
    """A stream quote with only the fields old_book reads."""
    q = {"source": source, "volume": volume, "timestamp": ltt}
    if open_:
        q["ohlc"] = {"open": open_, "high": None, "low": None, "close": 5.0}
    return q


@pytest.mark.parametrize("quote, now, old", [
    (sq(1_420_075), t(9, 15, 3), True),                       # JSWENERGY 29 Oct: yesterday's volume, no open
    (sq(429_500), t(9, 15, 2), True),                         # GODREJCP 30 Oct at 09:15:02 ...
    (sq(4_500, 19.05), t(9, 15, 5), False),                   # ... today's book at 09:15:05
    (sq(0), t(9, 15, 1), False),                              # nothing traded yet today: the book is today's
    (sq(None), t(9, 15, 1), False),                           # no volume field: not held back by this rule
    (sq(1_420_075, source="kotak"), t(9, 15, 3), False),      # Kotak quotes are not checked for these fields
    ({"volume": 1_420_075, "timestamp": "2026-10-15 09:15:01"}, t(9, 15, 3), False),   # no source (Kotak)
    (sq(1_420_075), t(9, 30), False),                         # past 09:30 a missing open never holds a buy
    (sq(0, ltt="2026-10-14 15:29:59"), t(9, 15, 3), True),    # 27 Oct's case: last trade yesterday
    (None, t(9, 15, 3), False),
])
def test_old_book(quote, now, old):
    assert pk.old_book(quote, now) is old


def stream(q, ts, volume, open_=None):
    q.book[ts].update(source="upstox_stream", volume=volume, timestamp="2026-10-15 09:15:01")
    q.book[ts].pop("ohlc", None)
    if open_:
        q.book[ts]["ohlc"] = {"open": open_}


def test_the_fade_waits_on_yesterdays_book_after_a_trade_of_today(tmp_path):
    lg, q, ft = ledger(tmp_path)                              # 29 Oct 2026: JSWENERGY bought at 6.60, real ask 4.40
    q.set("PE", 1220.0, 18.0, 18.5)
    stream(q, "HCLTECH26OCT1220PE", 1_420_075)
    ft.on_poll(t(9, 15, 3))
    assert lg.state["positions"] == [] and not lg.state["rules"]["refused"]
    assert "yesterday's" in lg.state["rules"]["fade_wait"]["2026-10-15:HCLTECH"]["reason"]
    q.set("PE", 1220.0, 12.0, 12.3)                           # today's book: open printed, volume restarted
    stream(q, "HCLTECH26OCT1220PE", 4_500, 12.1)
    ft.on_poll(t(9, 16, 20))                                  # the next walk (Kotak-paced retry in this fake)
    p = lg.state["positions"][0]
    assert p["entry"]["price"] == 12.3 and p["entry_quote"]["todays_book"] is True
    assert p["entry_quote"]["day_open"] == 12.1


def test_a_real_order_never_fills_on_yesterdays_book(setup):  # noqa: F811
    lg, q, ft, _ = setup
    q.set("PE", 1200.0, 18.0, 18.5)
    stream(q, TS, 4_500, 18.2)                                # decided on today's book
    ft.on_poll(at(15, 9, 15, 10))
    assert lg.state["rules"]["fade"][KEY] == "ordered"
    stream(q, TS, 900_000)                                    # the next quote is yesterday's book again
    lg.work_orders(at(15, 9, 15, 11))
    assert lg.state["positions"] == []
    stream(q, TS, 5_000, 18.2)
    lg.work_orders(at(15, 9, 15, 12))
    assert lg.state["positions"][0]["entry"]["price"] == 18.5
