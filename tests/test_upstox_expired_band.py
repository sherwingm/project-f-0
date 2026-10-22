from datetime import date

import pandas as pd

from index_data.upstox_expired import path_range, pick


def _c(strike, typ="CE"):
    return {"instrument_type": typ, "strike_price": strike, "instrument_key": f"K{strike}{typ}"}


def test_path_range_spans_the_whole_window():
    closes = pd.Series([26200.0, 25500.0, 24400.0, 24600.0],
                       index=["2024-09-26", "2024-10-07", "2024-10-23", "2024-10-25"])
    assert path_range(closes, date(2024, 9, 26), date(2024, 10, 24)) == (24400.0, 26200.0)


def test_path_range_starts_at_the_last_close_before_the_window():
    closes = pd.Series([30000.0, 26000.0, 25000.0], index=["2024-09-20", "2024-09-25", "2024-10-01"])
    assert path_range(closes, date(2024, 9, 26), date(2024, 10, 2)) == (25000.0, 26000.0)


def test_pick_keeps_strikes_within_the_band_of_the_range():
    cons = [_c(23100), _c(23200), _c(24400, "PE"), _c(27500), _c(27600), {"instrument_type": "FUT", "strike_price": 0}]
    got = [c["strike_price"] for c in pick(cons, 24400.0, 26200.0)]
    assert got == [23200, 24400, 27500]          # 24400 x 0.95 = 23180, 26200 x 1.05 = 27510


def test_pick_with_one_reference_is_the_old_band():
    got = [c["strike_price"] for c in pick([_c(94), _c(95), _c(105), _c(106)], 100.0)]
    assert got == [95, 105]
