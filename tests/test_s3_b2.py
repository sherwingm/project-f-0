"""S3 B2 signal and failure exit (scanner/s3_b2.py)."""
import pandas as pd

from scanner import s3_b2 as B


def day(closes, start="09:15"):
    """1-minute bars from `start`; the opening range bars (09:15-09:29) sit at 100 with high 101 / low 99."""
    ts = pd.date_range(f"2025-01-06 {start}", periods=len(closes), freq="min", tz="Asia/Kolkata")
    c = pd.Series(closes, dtype=float)
    return pd.DataFrame({"timestamp": ts, "open": c, "high": c.where(c != 100, 101), "low": c.where(c != 100, 99),
                         "close": c})


def test_accepted_after_n_closes_beyond_the_edge():
    d = day([100] * 15 + [102] * 20 + [100] * 10)
    side, ts, hi, lo = B.signal(d, 15, 15)
    assert (side, ts.strftime("%H:%M"), hi, lo) == ("CE", "09:45", 101, 99)   # breakout 09:30 + 15 closes


def test_a_breakout_that_falls_back_is_void_and_the_scan_goes_on():
    d = day([100] * 15 + [102] * 5 + [100] + [98] * 20 + [100] * 5)
    side, ts, *_ = B.signal(d, 15, 15)
    assert side == "PE" and ts.strftime("%H:%M") == "09:51"                 # the put breakout at 09:36 + 15
    assert B.signal(d, 15, None)[0] == "CE"                                  # B1's first breakout


def test_no_signal_when_acceptance_ends_after_13_15():
    d = day([100] * 15 + [100] * (13 * 60 + 5 - 9 * 60 - 30) + [102] * 30)
    assert B.signal(d, 15, 15) is None


def test_exit_the_minute_after_the_first_close_back_inside():
    d = day([100] * 15 + [102] * 20 + [100.5] + [102] * 10)
    side, ts, hi, lo = B.signal(d, 15, 15)
    ext, why = B.exit_minute(d, side, ts + pd.Timedelta(minutes=1), hi, lo)
    assert why == "fail" and ext.strftime("%H:%M") == "09:51"                # close 100.5 < 101 at 09:50
    d2 = day([100] * 15 + [102] * 40)
    s2 = B.signal(d2, 15, 15)
    ext2, why2 = B.exit_minute(d2, "CE", s2[1] + pd.Timedelta(minutes=1), 101, 99)
    assert why2 == "time" and ext2.strftime("%H:%M") == "15:15"
