from datetime import date

import pandas as pd

from index_data import load as L
from scanner.s3_p4 import CELLS, NEIGHBOURS, PRIMARY, signal, spec

DAY = date(2025, 2, 4)


def _spot(path):
    return pd.DataFrame([dict(timestamp=L.at(DAY, *map(int, t.split(":"))), open=c, high=h, low=lo, close=c)
                         for t, (c, h, lo) in path.items()])


def test_first_close_beyond_the_range_is_the_signal():
    s = _spot({"09:15": (100, 101, 99), "09:29": (100, 102, 98), "09:30": (101.5, 103, 101), "09:40": (97, 97, 96),
               "09:41": (103, 103, 102)})
    assert signal(s, 15) == ("PE", L.at(DAY, 9, 40))          # 09:30's high is 103 but its close 101.5 is inside


def test_no_signal_after_13_00():
    s = _spot({"09:15": (100, 101, 99), "13:01": (110, 110, 109)})
    assert signal(s, 15) is None


def test_primary_spec_is_one_long_atm_leg_with_stop_and_trail():
    sp = spec(PRIMARY, "CE", (9, 41))
    assert [(lg.side, lg.opt, lg.offset) for lg in sp.legs] == [("BUY", "CE", 0)]
    assert sp.stop == 0.25 and sp.trail == 0.25 and sp.exit == (15, 15) and sp.entry == (9, 41)
    assert PRIMARY in CELLS and all(n in CELLS for n in NEIGHBOURS)
