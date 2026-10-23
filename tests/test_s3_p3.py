import math
from datetime import date

import pandas as pd

from scanner.s3_p3 import CELLS, NEIGHBOURS, PRIMARY, condor, event_in
from scanner.s3_regime import delta


def test_condor_legs_from_the_chosen_shorts():
    s = condor(PRIMARY, 24300.0, 23700.0, 24000.0)
    assert [(lg.side, lg.opt, lg.offset) for lg in s.legs] == [("SELL", "CE", 6), ("SELL", "PE", -6), ("BUY", "CE", 8),
                                                               ("BUY", "PE", -8)]
    assert s.target == 0.5 and s.stop == 1.0 and s.entry == (15, 0) and s.exit == (15, 15)


def test_grid_has_primary_and_neighbours():
    assert len(CELLS) == 108 and PRIMARY in CELLS and all(n in CELLS for n in NEIGHBOURS)


def test_delta_signs_and_atm_half():
    t = 2 / 365
    assert 0.45 < delta("CE", 24000, 24000, t, 0.14) < 0.55
    assert -0.55 < delta("PE", 24000, 24000, t, 0.14) < -0.45
    assert delta("CE", 24000, 24300, t, 0.14) < 0.2


def test_event_in_holding_range():
    assert event_in(date(2025, 4, 8), date(2025, 4, 9)) and not event_in(date(2025, 4, 10), date(2025, 4, 17))
