"""Validation tests (Stage 4, 2026-11-12): look-ahead, closed minutes, and signal parity between the history code and the live traders.
New tests only; they read production code and change nothing. They document behaviour, including known gaps (see docs/research/VALIDATION_INVENTORY.md).

A. Look-ahead: the signal found on a full day must be the same when the data is cut at the signal minute, and must not change when every later bar
   is replaced by garbage; cut one minute earlier there must be no signal.
B. Closed minutes: the live traders use a minute's close only once the minute is over.
C. Parity: the same minute path gives the same signal minute and side in `scanner.s3_b2.signal` (history) and in `G1Trader` / `G1CTrader` (live).
"""
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
import pytest

from scanner.s3_b2 import LAST_ACCEPT, LAST_BREAKOUT, signal
from server import g1_live as G
from server.g1c_live import G1CTrader
from tests.test_g1_live import D1, EXP, Stream, Upstox, run

IST = G.IST
DAY = date(2025, 1, 9)
TZ = "Asia/Kolkata"


def random_day(seed: int, vol: float = 0.0007, start: float = 24000.0, flat: bool = False) -> pd.DataFrame:
    """375 one-minute bars 09:15-15:29 of a seeded random walk. flat=True makes every bar open = high = low = close (a point per minute)."""
    rng = np.random.default_rng(seed)
    n = 375
    ts = pd.date_range(f"{DAY} 09:15", periods=n, freq="1min", tz=TZ)
    close = start * np.exp(np.cumsum(rng.normal(0, vol, n)))
    open_ = np.r_[start, close[:-1]]
    if flat:
        return pd.DataFrame({"timestamp": ts, "open": close, "high": close, "low": close, "close": close})
    spread = np.abs(rng.normal(0, vol / 2, n)) * close
    return pd.DataFrame({"timestamp": ts, "open": open_, "high": np.maximum(open_, close) + spread,
                         "low": np.minimum(open_, close) - spread, "close": close})


# ------------------------------------------------------------------ A. look-ahead
@pytest.mark.parametrize("accept", [None, 3])
def test_a_signal_does_not_depend_on_bars_after_the_signal_minute(accept):
    found = 0
    for seed in range(400):
        full = random_day(seed)
        sig = signal(full, 15, accept)
        if sig is None:
            continue
        found += 1
        side, ts, hi, lo = sig
        cut = full[full["timestamp"] <= ts].reset_index(drop=True)
        assert signal(cut, 15, accept) == sig, f"seed {seed}: cutting the data at the signal minute changed the signal"
        rng = np.random.default_rng(10_000 + seed)
        garbage = full.copy()
        later = garbage["timestamp"] > ts
        n = int(later.sum())
        for col in ("open", "high", "low", "close"):
            garbage.loc[later, col] = rng.uniform(15000, 35000, n)
        assert signal(garbage, 15, accept) == sig, f"seed {seed}: later bars changed the signal"
        before = full[full["timestamp"] < ts].reset_index(drop=True)
        assert signal(before, 15, accept) is None, f"seed {seed}: a signal existed before the signal minute"
    assert found >= 40                       # the property was exercised on enough real signals, not vacuously


def test_a_opening_range_and_signal_times_are_inside_their_windows():
    for seed in range(300):
        for accept, last in ((None, LAST_BREAKOUT), (3, LAST_ACCEPT)):
            sig = signal(random_day(seed), 15, accept)
            if sig is not None:
                assert time(9, 30) <= sig[1].time() <= last


def test_a_range_is_taken_from_the_opening_minutes_only():
    d = random_day(5)
    hi, lo = float(d[d.timestamp.dt.time < time(9, 30)].high.max()), float(d[d.timestamp.dt.time < time(9, 30)].low.min())
    for seed in range(300):
        sig = signal(random_day(seed), 15, None)
        if sig is not None:
            r = random_day(seed)
            o = r[r.timestamp.dt.time < time(9, 30)]
            assert (sig[2], sig[3]) == (float(o.high.max()), float(o.low.min()))
    assert hi > lo


# ------------------------------------------------------------------ B. closed minutes (live)
def put_quotes(st, k=24000):
    st.put(k, 100.0, 100.5)


def drive(tr, st, closes: dict, t_from: time, t_to: time, every: int = 10):
    """Feed one price per tick: the close of that tick's minute (a point per minute)."""
    t = datetime.combine(D1, t_from, IST)
    end = datetime.combine(D1, t_to, IST)
    while t <= end:
        m = t.time().replace(second=0, microsecond=0)
        if m in closes:
            st.spot(closes[m])
            st.vix(13.0)
            put_quotes(st)
            st.s[f"CE{24000}"] = {"depth": [(100.0, 75, 100.5, 75)]}
        tr.tick(t)
        t += timedelta(seconds=every)


def path_closing_below(at: time, depth: float = 4.0) -> dict:
    """Minute closes: range 24000-24010 until 09:29, quiet inside it, then the minute `at` closes `depth` points below the low."""
    out, t = {}, datetime.combine(D1, time(9, 15))
    while t.time() < time(9, 30):
        out[t.time()] = 24010.0 if t.minute % 2 else 24000.0
        t += timedelta(minutes=1)
    while t.time() < at:
        out[t.time()] = 24005.0
        t += timedelta(minutes=1)
    while t.time() <= time(10, 30):
        out[t.time()] = 24000.0 - depth
        t += timedelta(minutes=1)
    return out


@pytest.fixture
def put_trader(tmp_path, monkeypatch):
    monkeypatch.setattr(G.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(G.alerts, "send", lambda *a, **k: False)
    st = Stream()
    return G.G1Trader(st, Upstox(), tmp_path), st


def test_b_a_minute_that_is_not_finished_is_never_a_signal(put_trader):
    tr, st = put_trader
    closes = path_closing_below(time(9, 40))
    drive(tr, st, closes, time(9, 15), time(9, 40, 50))        # 09:40 has printed 23996 for 50 s, but the minute is still open
    today = tr.state["days"][str(D1)]
    assert today.get("phase") == "scan" and "signal" not in today and tr.state["open"] is None
    drive(tr, st, closes, time(9, 40, 51), time(9, 41, 10))    # the minute is over: now it is the signal, entry is the next minute
    today = tr.state["days"][str(D1)]
    assert today["signal"] == "09:40" and today["entry"] == "09:41"


def test_b_the_entry_minute_is_the_minute_after_the_signal_minute(put_trader):
    tr, st = put_trader
    drive(tr, st, path_closing_below(time(9, 52)), time(9, 15), time(9, 56))
    today = tr.state["days"][str(D1)]
    assert (today["signal"], today["entry"]) == ("09:52", "09:53")
    assert tr.state["open"] is not None and tr.state["open"]["entry"] == "09:53"


# ------------------------------------------------------------------ C. signal parity: history `signal` vs live traders
def live_signal(cls, tmp_path, closes_by_minute: dict, last: time):
    st = Stream()
    tr = cls(st, Upstox(), tmp_path)
    for strike in range(23500, 24550, 50):
        st.s[f"CE{strike}"] = {"depth": [(100.0, 75, 100.5, 75)]}
        st.s[f"PE{strike}"] = {"depth": [(100.0, 75, 100.5, 75)]}
    drive(tr, st, closes_by_minute, time(9, 15), last, every=20)
    return tr.state["days"].get(str(D1), {})


class UpstoxBoth(Upstox):
    _nifty = {**Upstox._nifty, **{(e, "CE", float(k)): f"CE{k}" for e in ("2026-11-03", EXP) for k in range(23500, 24550, 50)}}


@pytest.mark.parametrize("seed", range(12))
def test_c_history_and_live_find_the_same_signal_minute_and_side(seed, tmp_path, monkeypatch):
    monkeypatch.setattr(G.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(G.alerts, "send", lambda *a, **k: False)
    day = random_day(seed, vol=0.0009, flat=True)
    hist = signal(day, 15, None)
    closes = {ts.time(): float(c) for ts, c in zip(day.timestamp, day.close)}
    for cls, side in ((G.G1Trader, "PE"), (G1CTrader, "CE")):
        st = Stream()
        tr = cls(st, UpstoxBoth(), tmp_path / cls.__name__)
        (tmp_path / cls.__name__).mkdir()
        tr.dir = tmp_path / cls.__name__
        tr.file = tr.dir / tr.LEDGER
        for strike in range(23000, 25050, 50):
            st.s[f"CE{strike}"] = {"depth": [(100.0, 75, 100.5, 75)]}
            st.s[f"PE{strike}"] = {"depth": [(100.0, 75, 100.5, 75)]}
        last = (hist[1] + timedelta(minutes=2)).time() if hist is not None else time(13, 6)
        t = datetime.combine(D1, time(9, 15), IST)
        end = datetime.combine(D1, last, IST)
        while t <= end:
            m = t.time().replace(second=0, microsecond=0)
            if m in closes:
                st.spot(closes[m])
                st.vix(13.0)
            tr.tick(t)
            t += timedelta(seconds=15)
        today = tr.state["days"].get(str(D1), {})
        if hist is None:
            assert "signal" not in today and "first breakout" not in today.get("status", ""), (seed, cls.__name__)
        elif hist[0] == side:
            assert today.get("signal") == f"{hist[1]:%H:%M}", (seed, cls.__name__, today)
        else:                                                     # the other side broke first: no trade, same minute
            assert "signal" not in today and f"first breakout {'up' if side == 'PE' else 'down'} at {hist[1]:%H:%M}" in today["status"], (seed, cls.__name__, today)
