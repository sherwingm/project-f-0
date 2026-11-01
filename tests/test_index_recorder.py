"""NIFTY 1-second recorder (server/index_recorder.py) and the index group of the stream's candles."""
import gzip
import json
from datetime import date, datetime

from server import index_recorder as R
from server import upstox_stream as U

T0 = 1_792_000_000.0
IST = U.IST


def nifty_master():
    m = {("2026-11-30", "FUT", None): "NSE_FO|FUT1", ("2026-12-29", "FUT", None): "NSE_FO|FUT2"}
    for e in ("2026-11-03", "2026-11-10", "2026-11-17", "2026-10-27"):
        for k in range(24000, 26050, 50):
            for s in ("CE", "PE"):
                m[(e, s, float(k))] = f"NSE_FO|{e}{k}{s}"
    return m


def test_option_pairs_two_expiries_band_and_nearest_future():
    p = R.option_pairs(nifty_master(), 25012.0, date(2026, 11, 2))
    assert p["NSE_FO|FUT1"] == "NIFTY FUT 2026-11-30" and "NSE_FO|FUT2" not in p
    labels = [v for v in p.values() if "FUT" not in v]
    assert len(labels) == 2 * 21 * 2                                  # 2 expiries x 21 strikes x CE/PE
    assert {v.split()[1] for v in labels} == {"2026-11-03", "2026-11-10"}   # expired 10-27 and far 11-17 left out
    ks = sorted({int(v.split()[2]) for v in labels})
    assert ks[0] == 24500 and ks[-1] == 25500


def test_index_rows_go_to_their_own_file(tmp_path, monkeypatch):
    s = U.UpstoxStream("tok")
    s.candles.want({"NSE_FO|1": "HCLTECH26OCT1200PE"}, T0)
    s.candles.want({"NSE_INDEX|Nifty 50": "NIFTY 50"}, T0, "index")
    s.candles.tick("NSE_FO|1", {"ltpc": {"ltp": 18.5}}, T0)
    s.candles.tick("NSE_INDEX|Nifty 50", {"ltpc": {"ltp": 25000.5}}, T0)
    monkeypatch.setattr(U.time, "time", lambda: T0 + 3)
    assert s.write_candles(tmp_path) == 2
    (a,) = (tmp_path / U.CANDLES).glob("*.jsonl")
    (b,) = (tmp_path / U.CANDLES_INDEX).glob("*.jsonl")
    ra, rb = json.loads(a.read_text()), json.loads(b.read_text())
    assert ra["ts"] == "HCLTECH26OCT1200PE" and "g" not in ra
    assert rb["ts"] == "NIFTY 50" and rb["c"] == 25000.5 and "g" not in rb


class FakeStream:
    def __init__(self, spot):
        self.spot, self.wanted, self.watched = spot, set(), {}

    def get(self, key):
        return {"ltpc": {"ltp": self.spot}} if key == R.SPOT_KEY and self.spot else None

    def want(self, keys):
        self.wanted.update(keys)

    def watch(self, pairs, group=""):
        assert group == "index"
        self.watched = dict(pairs)


class FakeUpstox:
    _loaded = True
    _nifty = nifty_master()


def test_recorder_market_hours_follow_spot_and_keep_strikes(tmp_path):
    fs = FakeStream(25000.0)
    r = R.IndexRecorder(fs, FakeUpstox(), tmp_path)
    r.tick(datetime(2026, 11, 2, 9, 0, tzinfo=IST))                 # before the open: nothing
    assert fs.watched == {}
    r.tick(datetime(2026, 11, 2, 9, 20, tzinfo=IST))
    n0 = len(fs.watched)
    assert set(R.INDICES) <= set(fs.watched) and n0 == 3 + 1 + 84
    fs.spot = 25500.0
    r.tick(datetime(2026, 11, 2, 9, 20, 10, tzinfo=IST))           # within EVERY: no refresh
    assert len(fs.watched) == n0
    r.tick(datetime(2026, 11, 2, 9, 21, tzinfo=IST))
    assert "NSE_FO|2026-11-0324500CE" in fs.watched                 # the morning's strikes stay
    assert "NSE_FO|2026-11-0326000CE" in fs.watched and len(fs.watched) > n0
    assert fs.wanted == set(fs.watched)
    r.tick(datetime(2026, 11, 7, 10, 0, tzinfo=IST))                # Saturday: nothing new
    assert r.pairs == {}


def test_no_spot_yet_records_indices_only(tmp_path):
    fs = FakeStream(None)
    R.IndexRecorder(fs, FakeUpstox(), tmp_path).tick(datetime(2026, 11, 2, 9, 15, tzinfo=IST))
    assert set(fs.watched) == set(R.INDICES)


def test_gzip_old_days_only(tmp_path):
    (tmp_path / "2026-10-30.jsonl").write_text('{"a":1}\n')
    (tmp_path / "2026-11-02.jsonl").write_text('{"a":2}\n')
    assert R.gzip_old(tmp_path, date(2026, 11, 2)) == 1
    assert gzip.open(tmp_path / "2026-10-30.jsonl.gz", "rt").read() == '{"a":1}\n'
    assert not (tmp_path / "2026-10-30.jsonl").exists() and (tmp_path / "2026-11-02.jsonl").exists()
