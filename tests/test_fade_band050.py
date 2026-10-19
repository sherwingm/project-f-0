"""S1 v10 Rs 0.50-1 band exits on minute candles (scanner/fade_band050.simulate; strategies/S1_v10_band050_trail.md)."""
import pandas as pd

from scanner.fade_band050 import simulate


def mins(*bars):
    """(time, open, high, low, close) rows."""
    return pd.DataFrame([{"t": t, "o": o, "h": h, "l": l, "c": c} for t, o, h, l, c in bars])


def test_entry_is_the_0915_close_plus_two_ticks_and_the_baseline_sells_at_1519_close_minus_two():
    s = simulate(mins(("09:15", .70, .72, .68, .70), ("10:00", .7, .9, .7, .8), ("15:19", .6, .6, .6, .60)), None)
    assert s == {"entry": .80, "exit": .50, "reason": "15:20", "at": "15:19"}


def test_target_fills_at_entry_x_1_2_rounded_up_when_the_high_clears_it_by_a_tick():
    m = mins(("09:15", .70, .70, .70, .70), ("09:16", .8, 1.00, .8, .9), ("09:17", .9, 1.05, .9, 1.0))
    s = simulate(m, 0.30)                                       # entry .80 -> .96 -> target 1.00: 09:16 only touches
    assert (s["reason"], s["exit"], s["at"]) == ("target", 1.00, "09:17")


def test_trailing_stop_uses_the_peak_so_far_and_fills_two_ticks_under():
    m = mins(("09:15", .70, .70, .70, .70), ("09:16", .8, .90, .8, .9), ("09:17", .9, .9, .70, .7))
    s = simulate(m, 0.20)                                       # peak .90 -> stop .72 -> tick .70; low .70 hits
    assert (s["reason"], s["exit"], s["at"]) == ("stop", .60, "09:17")


def test_a_minute_touching_both_takes_the_stop_and_a_gap_fills_at_the_open():
    both = mins(("09:15", .70, .70, .70, .70), ("09:16", .8, 1.2, .5, 1.0))
    assert simulate(both, 0.10)["reason"] == "stop"
    gap = mins(("09:15", .70, .70, .70, .70), ("09:16", .50, .55, .45, .5))
    assert simulate(gap, 0.10)["exit"] == .40                   # stop .72, but it opened at .50: .50 - 2 ticks


def test_no_minute_by_0920_is_no_trade():
    assert simulate(mins(("09:25", .7, .7, .7, .7)), None) is None


def test_after_mode_holds_until_plus_100_then_trails_from_the_peak():
    m = mins(("09:15", .70, .70, .70, .70), ("09:16", .8, .9, .30, .5),         # a deep dip: no stop before the target
             ("09:17", .9, 1.70, .9, 1.6), ("09:18", 1.6, 2.00, 1.6, 1.9),      # 1.65 + tick reached -> armed, peak 1.70
             ("09:19", 1.9, 1.9, 1.55, 1.6))                                     # peak 2.00 -> 20 % stop 1.60
    s = simulate(m, 0.20, 1.00, "after")
    assert (s["reason"], s["exit"], s["at"]) == ("stop", 1.50, "09:19")
    never = mins(("09:15", .70, .70, .70, .70), ("09:16", .8, 1.0, .3, .4), ("15:19", .4, .4, .4, .4))
    assert simulate(never, 0.20, 1.00, "after")["reason"] == "15:20"


def test_before_mode_with_a_100_pct_target():
    m = mins(("09:15", .70, .70, .70, .70), ("09:16", .8, 1.70, .8, 1.6))
    assert simulate(m, 0.30, 1.00, "before") == {"entry": .80, "exit": 1.60, "reason": "target", "at": "09:16"}
