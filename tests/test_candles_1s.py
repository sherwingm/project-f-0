"""1-second candles from the Upstox stream's ticks (server/upstox_stream.py Candles)."""
import json

from server import upstox_stream as U

IK = "NSE_FO|12345"
T0 = 1_792_000_000.0                       # a whole second


def st(ltp, bid, ask, vtt):
    return {"ltpc": {"ltp": ltp}, "depth": [(bid, 100, ask, 100), (bid - 0.1, 50, ask + 0.1, 50)], "vtt": vtt}


def test_ticks_in_one_second_make_one_ohlc_row():
    c = U.Candles()
    c.want({IK: "HCLTECH26OCT1200PE"}, T0)
    c.tick(IK, st(18.5, 18.4, 18.6, 1000), T0 + 0.1)
    c.tick(IK, st(19.2, 19.1, 19.3, 1700), T0 + 0.4)      # the spike a once-a-second read can miss
    c.tick(IK, st(18.7, 18.6, 18.8, 2100), T0 + 0.9)
    assert c.take(T0 + 0.95) == []                         # the second is still open
    c.tick(IK, st(18.8, 18.7, 18.9, 2400), T0 + 1.2)
    (r,) = c.take(T0 + 1.3)
    assert (r["o"], r["h"], r["l"], r["c"]) == (18.5, 19.2, 18.5, 18.7)
    assert (r["bo"], r["bh"], r["bl"], r["bc"], r["a"], r["n"]) == (18.4, 19.1, 18.4, 18.6, 18.8, 3)
    assert r["ts"] == "HCLTECH26OCT1200PE" and r["v"] == 1100
    (r2,) = c.take(T0 + 2.5)                               # a quiet second closes the open one
    assert r2["n"] == 1 and r2["v"] == 300                 # volume since the previous second's last tick


def test_unwatched_and_expired_contracts_write_nothing():
    c = U.Candles()
    c.tick(IK, st(18.5, 18.4, 18.6, 1000), T0)
    assert c.take(T0 + 5) == []
    c.want({IK: "X"}, T0)
    c.tick(IK, st(18.5, 18.4, 18.6, 1000), T0 + U.WATCH_FOR + 1)
    assert c.take(T0 + U.WATCH_FOR + 3) == [] and IK not in c.watch


def test_write_candles_appends_jsonl(tmp_path, monkeypatch):
    s = U.UpstoxStream("tok")
    s.candles.want({IK: "HCLTECH26OCT1200PE"}, T0)
    s.candles.tick(IK, st(18.5, 18.4, 18.6, 1000), T0)
    monkeypatch.setattr(U.time, "time", lambda: T0 + 3)
    assert s.write_candles(tmp_path) == 1
    (f,) = (tmp_path / U.CANDLES).glob("*.jsonl")
    assert json.loads(f.read_text().splitlines()[0])["c"] == 18.5
