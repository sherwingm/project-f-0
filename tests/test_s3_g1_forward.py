"""S3 G1 forward booking on synthetic 1-second files (one row a minute is enough)."""
from datetime import date

import pandas as pd
import pytest

from scanner import s3_g1_forward as G

TZ = "Asia/Kolkata"
EX = "2026-11-10"


def _day(day, spot, put_bid, put_ask=None, bid_low=None):
    """A session 09:15-15:29: NIFTY 50 closes from spot(minute index), the 24000 PE quotes from put_bid(i)."""
    rows = []
    for i, ts in enumerate(pd.date_range(f"{day} 09:15", f"{day} 15:29", freq="min", tz=TZ)):
        c = spot(i)
        rows.append({"timestamp": ts, "symbol": "NIFTY 50", "kind": "INDEX", "expiry": None, "strike": None,
                     "o": c, "h": c, "l": c, "c": c, "bo": None, "bh": None, "bl": None, "bc": None, "a": None})
        b = put_bid(i)
        rows.append({"timestamp": ts + pd.Timedelta(seconds=30), "symbol": f"NIFTY {EX} 24000 PE", "kind": "PE",
                     "expiry": EX, "strike": 24000.0, "o": b, "h": b, "l": b, "c": b, "bo": b, "bh": b,
                     "bl": bid_low(i) if bid_low else b, "bc": b, "a": (put_ask or (lambda j: b + 0.5))(i)})
    return pd.DataFrame(rows)


def down_day(i):            # range 24000-24010 for 15 minutes, then a close below 24000 at 09:40 (i = 25)
    return 24005 + (5 if i % 2 else -5) if i < 15 else (24004 if i < 25 else 23990)


def test_next_open_exit_books_ask_in_bid_out():
    d1 = _day(date(2026, 11, 5), down_day, lambda i: 100.0)
    d2 = _day(date(2026, 11, 6), lambda i: 23900, lambda i: 150.0)
    r = G.book(date(2026, 11, 5), d1, date(2026, 11, 6), d2)
    assert (r["signal"], r["entry"], r["strike"], r["expiry"]) == ("09:40", "09:41", 24000, EX)
    assert r["reason"] == "next open" and r["paid"] == 100.5 and r["sold"] == 150.0
    assert r["exit_at"] == "09:16:30"
    assert r["gross_rs"] == pytest.approx((150.0 - 100.5) * G.LOT)
    assert r["net_rs"] < r["gross_rs"] and r["net_pct_2x"] < r["net_pct"]


def test_stop_on_the_bid_low_day_one():
    d1 = _day(date(2026, 11, 5), down_day, lambda i: 100.0, bid_low=lambda i: 40.0 if i == 200 else 100.0)
    d2 = _day(date(2026, 11, 6), lambda i: 23900, lambda i: 150.0)
    r = G.book(date(2026, 11, 5), d1, date(2026, 11, 6), d2)
    assert (r["reason"], r["sold"], r["exit_day"]) == ("stop", 40.0, date(2026, 11, 5))
    assert r["net_pct"] < -50


def test_upward_first_breakout_is_no_trade():
    d1 = _day(date(2026, 11, 5), lambda i: 24005 if i < 25 else 24020, lambda i: 100.0)
    assert G.book(date(2026, 11, 5), d1, None, None) is None


def test_waits_for_next_session_file():
    d1 = _day(date(2026, 11, 5), down_day, lambda i: 100.0)
    r = G.book(date(2026, 11, 5), d1, None, None)
    assert r["pending"] and r["skip"].startswith("waiting")


def _with_vix(df, vix):
    v = df[df["symbol"] == "NIFTY 50"].copy()
    v["symbol"], v[["o", "h", "l", "c"]] = "INDIA VIX", vix
    return pd.concat([df, v], ignore_index=True)


def test_g1f_takes_a_quiet_day():
    d1 = _with_vix(_day(date(2026, 11, 5), down_day, lambda i: 100.0), 13.0)
    d2 = _day(date(2026, 11, 6), lambda i: 23900, lambda i: 150.0)
    r = G.book(date(2026, 11, 5), d1, date(2026, 11, 6), d2, prev_close=24000.0)
    assert r["g1f_skip"] == "" and r["vix_signal"] == 13.0
    assert r["or_width_pct"] == pytest.approx(10 / 24000 * 100, abs=1e-3)


def test_g1f_skips_gap_up_and_high_vix_and_missing_close():
    d1 = _with_vix(_day(date(2026, 11, 5), down_day, lambda i: 100.0), 18.0)
    r = G.book(date(2026, 11, 5), d1, None, None, prev_close=23900.0)      # open 24000 → +0.42 % gap
    assert "day-1 gap" in r["g1f_skip"] and "VIX 18.00" in r["g1f_skip"]
    r = G.book(date(2026, 11, 5), _day(date(2026, 11, 5), down_day, lambda i: 100.0), None, None)
    assert "no previous close" in r["g1f_skip"] and "no VIX" in r["g1f_skip"]
