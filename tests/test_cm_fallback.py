"""Scan freshness: sessions eod2 lacks are filled from NSE's cash-market bhavcopy, in memory, and listed."""
from datetime import date

import pandas as pd

from scanner import cm_fallback as cm


def _frame(last="2026-09-25", close=100.0):
    idx = pd.DatetimeIndex(pd.bdate_range(end=last, periods=3), name="Date")
    return pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close, "Volume": 1000.0}, index=idx)


def test_missing_days_are_the_weekdays_after_eod2():
    assert cm.missing_days(date(2026, 9, 25), date(2026, 9, 30)) == [date(2026, 9, 28), date(2026, 9, 29), date(2026, 9, 30)]
    assert cm.missing_days(date(2026, 9, 30), date(2026, 9, 30)) == []
    assert len(cm.missing_days(date(2026, 1, 1), date(2026, 9, 30))) <= cm.MAX_GAP_DAYS


def test_fill_appends_published_sessions_and_skips_holidays():
    frames = {"ABC": _frame(), "XYZ": _frame(close=50.0)}

    def download(d, cache_dir):
        if d == date(2026, 9, 29):
            return None                                           # a holiday / not published
        return pd.DataFrame({"symbol": ["ABC"], "Open": [101.0], "High": [102.0], "Low": [99.0], "Close": [101.5],
                             "Volume": [5000.0]})
    days = cm.fill(frames, today=date(2026, 9, 30), download=download)
    assert days == ["2026-09-28", "2026-09-30"]
    assert list(frames["ABC"].index[-2:].strftime("%Y-%m-%d")) == ["2026-09-28", "2026-09-30"]
    assert frames["ABC"]["Close"].iloc[-1] == 101.5
    assert frames["XYZ"].index[-1] == pd.Timestamp("2026-09-25")   # not in the file: nothing invented


def test_fill_does_nothing_when_eod2_is_current():
    frames = {"ABC": _frame(last="2026-09-30")}
    assert cm.fill(frames, today=date(2026, 9, 30), download=lambda d, c: 1 / 0) == []


def test_a_failed_download_is_skipped():
    frames = {"ABC": _frame()}

    def download(d, cache_dir):
        raise OSError("refused")
    assert cm.fill(frames, today=date(2026, 9, 28), download=download) == []


def test_fill_index():
    s = pd.Series([100.0], index=pd.DatetimeIndex(["2026-09-25"]))
    out = cm.fill_index(s, ["2026-09-28", "2026-09-29"], get_close=lambda d: None if d.day == 29 else 101.0)
    assert list(out.values) == [100.0, 101.0]
