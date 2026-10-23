from scanner.s3_p2s import NEIGHBOURS, POD, PRIMARY, spec


def test_primary_is_the_registered_fly():
    s = spec(PRIMARY)
    assert [(lg.side, lg.opt, lg.offset) for lg in s.legs] == [("SELL", "CE", 0), ("SELL", "PE", 0), ("BUY", "CE", 4),
                                                               ("BUY", "PE", -4)]
    assert s.entry == (14, 45) and s.exit == (15, 25) and s.stop == 0.30 and s.target is None


def test_grid_holds_primary_and_neighbours_once():
    labels = [POD.label(c) for c in POD.cells]
    assert len(labels) == len(set(labels)) == 108
    assert all(c in POD.cells for c in [PRIMARY] + NEIGHBOURS)
    assert POD.skip_events and POD.vix is None


def test_straddle_has_no_wings():
    assert len(spec(("straddle", (14, 45), (15, 25), None)).legs) == 2
