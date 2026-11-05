"""S3 N1 forward booking on synthetic 1-second files (one row a minute is enough)."""
from datetime import date

import pandas as pd
import pytest

from scanner import s3_n1 as N

TZ = "Asia/Kolkata"
EX = "2026-11-17"                      # Tuesday expiry: 2026-11-16 the day before, 2026-11-13 two sessions out


def _day(day, spot, bid, kind="CE", strike=24100.0, bid_low=None):
    rows = []
    for i, ts in enumerate(pd.date_range(f"{day} 09:15", f"{day} 15:29", freq="min", tz=TZ)):
        c = spot(i)
        rows.append({"timestamp": ts, "symbol": "NIFTY 50", "kind": "INDEX", "expiry": None, "strike": None,
                     "o": c, "h": c, "l": c, "c": c, "bo": None, "bh": None, "bl": None, "bc": None, "a": None})
        b = bid(i)
        rows.append({"timestamp": ts + pd.Timedelta(seconds=30), "symbol": f"NIFTY {EX} {strike:.0f} {kind}",
                     "kind": kind, "expiry": EX, "strike": strike, "o": b, "h": b, "l": b, "c": b, "bo": b, "bh": b,
                     "bl": bid_low(i) if bid_low else b, "bc": b, "a": b + 0.5})
    return pd.DataFrame(rows)


def up_day(i):              # range 24000-24010 for 15 minutes, then a close above 24010 at 09:40 (i = 25)
    return 24005 + (5 if i % 2 else -5) if i < 15 else (24006 if i < 25 else 24020)


def down_day(i):
    return 24005 + (5 if i % 2 else -5) if i < 15 else (24004 if i < 25 else 23990)


def test_strike_is_two_steps_out():
    assert N.strike_for("CE", 24020) == 24100 and N.strike_for("PE", 23990) == 23900


def test_up_breakout_on_expiry_day_buys_call_and_sells_1515():
    d = _day(date(2026, 11, 17), up_day, lambda i: 10.0 if i < 200 else 25.0)
    r = N.book(date(2026, 11, 17), d)
    assert (r["side"], r["strike"], r["sessions_left"], r["strategy"]) == ("CE", 24100, 0, "near_expiry")
    assert (r["signal"], r["entry"], r["reason"], r["paid"], r["sold"]) == ("09:40", "09:41", "15:15", 10.5, 25.0)
    assert r["net_rs"] < r["gross_rs"] == pytest.approx((25.0 - 10.5) * 65)
    assert r["max_up_held_pct"] == pytest.approx((25.0 / 10.5 - 1) * 100, abs=0.1)


def test_down_breakout_day_before_buys_put_and_stops_on_bid():
    d = _day(date(2026, 11, 16), down_day, lambda i: 20.0, kind="PE", strike=23900.0,
             bid_low=lambda i: 9.0 if i == 100 else 20.0)
    r = N.book(date(2026, 11, 16), d)
    assert (r["side"], r["sessions_left"], r["reason"], r["sold"]) == ("PE", 1, "stop", 9.0)


def test_no_trade_two_sessions_out_or_without_breakout():
    assert N.book(date(2026, 11, 13), _day(date(2026, 11, 13), up_day, lambda i: 10.0)) is None
    flat = _day(date(2026, 11, 17), lambda i: 24005 + (5 if i % 2 else -5), lambda i: 10.0)
    assert N.book(date(2026, 11, 17), flat) is None


def test_missing_ask_is_a_skip_not_a_guess():
    d = _day(date(2026, 11, 17), up_day, lambda i: 10.0, strike=24150.0)     # wrong strike recorded
    r = N.book(date(2026, 11, 17), d)
    assert r["skip"].startswith("no ask for 24100 CE")
