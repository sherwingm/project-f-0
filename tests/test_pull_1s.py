"""NIFTY 1-second copy to this PC (index_data/pull_1s.py)."""
from datetime import date, datetime

from index_data import pull_1s as P

LINES = [
    '{"ts":"NIFTY 2026-11-09 23250 CE","t":"09:15:01","o":251.15,"h":252,"l":251,"c":251.5,"bo":250.35,"bh":250.35,'
    '"bl":250.35,"bc":250.35,"a":251.0,"n":3,"v":75}',
    '{"ts":"INDIA VIX","t":"09:15:00","o":15.47,"h":15.47,"l":15.47,"c":15.47,"bo":null,"bh":null,"bl":null,'
    '"bc":null,"a":null,"n":1,"v":null}',
    '{"ts":"NIFTY FUT 2026-11-23","t":"09:15:00","o":23010,"h":23012,"l":23009,"c":23011,"bo":23010,"bh":23011,'
    '"bl":23010,"bc":23010,"a":23012,"n":9,"v":1500}',
    "",
]


def test_labels():
    assert P.label_parts("NIFTY 2026-11-09 23250 CE") == ("CE", "2026-11-09", 23250.0)
    assert P.label_parts("NIFTY FUT 2026-11-23") == ("FUT", "2026-11-23", None)
    assert P.label_parts("NIFTY BANK") == ("INDEX", None, None)


def test_parse_keeps_every_row_and_writes_a_checked_parquet(tmp_path):
    df = P.parse(date(2026, 11, 2), LINES)
    assert len(df) == 3 and list(df["kind"]) == ["INDEX", "CE", "FUT"]        # sorted by symbol
    ce = df[df["kind"] == "CE"].iloc[0]
    assert str(ce["timestamp"]) == "2026-11-02 09:15:01+05:30" and ce["strike"] == 23250 and ce["v"] == 75
    assert df[df["kind"] == "INDEX"]["bo"].isna().all()
    p = tmp_path / "d.parquet"
    P.write(df, p, 3)
    assert P.local_rows(p) == 3
    P.write(df, p, 4)                                    # a row count that does not match the server: not a copy
    assert P.local_rows(p) is None


def test_today_waits_for_the_close():
    d = date(2026, 11, 2)
    assert not P.finished(d, datetime(2026, 11, 2, 15, 35, tzinfo=P.IST))
    assert P.finished(d, datetime(2026, 11, 2, 15, 41, tzinfo=P.IST))
    assert P.finished(d, datetime(2026, 11, 3, 8, 0, tzinfo=P.IST))
