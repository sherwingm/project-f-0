"""The trade sheet's option-path rules: upside-only peak, downside-only dip, the last allowed day."""
from scanner import trade_sheet as ts


def test_peak_is_upside_only_and_dip_downside_only():
    s = ts.span([("2024-01-02", 8.0), ("2024-01-03", 9.0)], 10.0)          # never above entry
    assert (s["peak"], s["peak_date"]) == (0.0, None) and (s["dip"], s["dip_date"]) == (-20.0, "2024-01-02")
    s = ts.span([("2024-01-02", 12.0), ("2024-01-03", 30.0)], 10.0)         # never below entry
    assert (s["peak"], s["peak_date"]) == (200.0, "2024-01-03") and (s["dip"], s["dip_date"]) == (0.0, None)
    assert ts.span([], 10.0)["peak"] is None


def test_last_day_and_sessions_between():
    sessions = ["2024-01-22", "2024-01-23", "2024-01-24", "2024-01-25"]
    assert ts.last_day(sessions, "2024-01-25", 1) == "2024-01-24"
    assert ts.last_day(sessions, "2024-01-25", 2) == "2024-01-23"
    assert ts.last_day(sessions, "2024-01-26", 1) == "2024-01-24"         # expiry not a cached session
    assert ts.sessions_between(sessions, "2024-01-22", "2024-01-24") == 2
    assert ts.sessions_between(sessions, "2024-01-22", None) is None
