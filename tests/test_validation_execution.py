"""Validation tests (Stage 4, 2026-11-12): entry timing, live-versus-history stop parity, and edge cases.
New tests only; they read production code and change nothing. Tests named `known_*` pin a DOCUMENTED difference or gap so that any future change
to it fails loudly instead of silently moving the history (see docs/research/VALIDATION_INVENTORY.md).
"""
import re
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
import pytest

from index_data import load as L
from scanner.s3_b2 import signal
from scanner.s3_engine import ENTRY_STALE, MARK_STALE, Leg, Spec, simulate
from server import g1_live as G
from tests.test_g1_live import D1, D2, EXP, Stream, Upstox, down_day, run
from tests.test_validation_lookahead import TZ, random_day

IST = G.IST
DAY = date(2025, 1, 9)
COLS = ["timestamp", "strike", "option_type", "open", "high", "low", "close", "volume", "oi", "source"]


def chain(prices):
    """prices: {(strike, 'CE'|'PE'): {'HH:MM': close or (close, low)}} -> a merged-chain frame (as tests/test_s3_engine.py)."""
    rows = []
    for (k, o), path in prices.items():
        for t, v in path.items():
            c, low = v if isinstance(v, tuple) else (v, v)
            rows.append(dict(timestamp=L.at(DAY, *map(int, t.split(":"))), strike=float(k), option_type=o, open=c, high=c,
                             low=low, close=c, volume=10, oi=100, source="upstox"))
    if not rows:
        return pd.DataFrame(columns=COLS)
    return pd.DataFrame(rows).sort_values(["strike", "option_type", "timestamp"]).reset_index(drop=True)


BUY_PE = Spec("long_put", [Leg("BUY", "PE", 0)], entry=(9, 41), exit=(15, 15), stop=0.5)


def fills(r):
    """(entry fill, exit fill) parsed from the engine's `legs` text B24000PE@120.60>110.45."""
    m = re.search(r"@([\d.]+)>([\d.]+)", r["legs"])
    return float(m.group(1)), float(m.group(2))


# ------------------------------------------------------------------ C. entry timing (history engine)
def test_c_engine_fills_at_the_entry_minutes_own_close_plus_slippage():
    c = chain({(24000, "PE"): {"09:40": 100, "09:41": 120, "09:42": 150, "15:15": 130}})
    r = simulate(c, 24000.0, DAY, BUY_PE, lot=75)
    assert r["skip"] == ""
    entry, _ = fills(r)
    assert entry == pytest.approx(120 * 1.005, abs=0.01)                 # not the 09:40 or the 09:42 bar


def test_c_engine_uses_the_last_fresh_price_and_never_a_later_bar():
    c = chain({(24000, "PE"): {"09:38": 110, "09:43": 150, "15:15": 130}})      # no bar at 09:41; 09:38 is within ENTRY_STALE minutes
    entry, _ = fills(simulate(c, 24000.0, DAY, BUY_PE, lot=75))
    assert entry == pytest.approx(110 * 1.005, abs=0.01)
    stale = chain({(24000, "PE"): {"09:30": 110, "15:15": 130}})                  # 11 minutes old: refused, not guessed
    assert ENTRY_STALE < 11
    assert simulate(stale, 24000.0, DAY, BUY_PE, lot=75)["skip"].startswith("no price 24000 PE")


def test_c_live_entry_minute_is_signal_plus_one_and_the_price_is_that_minutes_last_ask(tmp_path, monkeypatch):
    monkeypatch.setattr(G.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(G.alerts, "send", lambda *a, **k: False)
    st = Stream()
    tr = G.G1Trader(st, Upstox(), tmp_path)
    run(tr, D1, time(9, 15), time(9, 45), before=down_day(st, put_bid=100.0))
    o = tr.state["open"]
    assert (o["signal"], o["entry"]) == ("09:40", "09:41") and o["paid"] == 100.5      # the ask of the 09:41 minute, not a later one


# ------------------------------------------------------------------ D. stop parity: history (minute marks) versus live (per-second bid)
def live_trade_with_bids(tmp_path, monkeypatch, bid_at):
    """Buy at 100.5 on D1 09:41, then feed bids tick by tick; bid_at(datetime) -> bid."""
    monkeypatch.setattr(G.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(G.alerts, "send", lambda *a, **k: False)
    st = Stream()
    tr = G.G1Trader(st, Upstox(), tmp_path)
    run(tr, D1, time(9, 15), time(9, 45), before=down_day(st))
    assert tr.state["open"]["paid"] == 100.5

    def f(t):
        st.spot(24000.0)
        b = bid_at(t)
        st.put(24000, b, b + 0.5)
    run(tr, D1, time(9, 46), time(11, 5), every=5, before=f)
    return tr


def test_d_a_sustained_drop_stops_in_both_and_the_prices_agree_within_slippage(tmp_path, monkeypatch):
    live = live_trade_with_bids(tmp_path, monkeypatch, lambda t: 100.0 if t.time() < time(11, 0) else 45.0)
    t = live.state["trades"][0]
    assert t["reason"] == "stop" and t["sold"] == 45.0
    hist = simulate(chain({(24000, "PE"): {"09:41": 100, "10:59": 100, "11:00": 45, "15:15": 45}}), 24000.0, DAY, BUY_PE, lot=75)
    assert hist["reason"] == "stop" and hist["exit_at"] == "11:00"
    _, h_out = fills(hist)
    assert abs(h_out - t["sold"]) / t["sold"] <= 0.006                                 # 0.5 % slippage is the whole difference


def test_known_difference_a_dip_inside_one_minute_stops_live_but_not_in_history(tmp_path, monkeypatch):
    def bid(t):
        return 30.0 if (t.hour, t.minute, t.second // 10) == (11, 0, 1) else 100.0     # one 10-second dip to 30, then back to 100
    live = live_trade_with_bids(tmp_path, monkeypatch, bid)
    assert live.state["trades"][0]["reason"] == "stop"                                # live: any second at or below half the price paid
    hist = simulate(chain({(24000, "PE"): {"09:41": 100, "11:00": (95, 30), "15:15": 100}}), 24000.0, DAY, BUY_PE, lot=75)
    assert hist["reason"] == "time"                                                   # history: the minute's CLOSE is the mark; its low (30) is ignored


# ------------------------------------------------------------------ E. edge cases
def test_e_a_chain_with_no_data_skips_the_day():
    r = simulate(chain({}), 24000.0, DAY, BUY_PE, lot=75)
    assert r["skip"].startswith("no price 24000 PE")


def test_e_a_missing_exit_bar_uses_the_last_carried_mark_not_a_guess():
    c = chain({(24000, "PE"): {"09:41": 100, "14:30": 120}})                          # nothing at 15:15
    r = simulate(c, 24000.0, DAY, BUY_PE, lot=75)
    assert r["reason"] == "time"
    _, out = fills(r)
    assert out == pytest.approx(120 * 0.99, abs=0.01) and MARK_STALE >= 30         # last mark 120, sold at 15:15 (1 % slippage from 15:00)


def test_e_a_missing_strike_for_one_leg_skips_the_day():
    two = Spec("pair", [Leg("BUY", "CE", 0), Leg("BUY", "PE", 0)], entry=(9, 41), exit=(15, 15))
    c = chain({(24000, "PE"): {"09:41": 100, "15:15": 100}})
    assert simulate(c, 24000.0, DAY, two, lot=75)["skip"].startswith("no price 24000 CE")


def test_e_session_boundary_a_break_at_1300_is_a_signal_and_at_1301_is_not():
    def day(break_at):
        d = random_day(0, vol=0.0)                                               # flat 24000, then shape the range and the break
        t = d.timestamp.dt.time
        d.loc[t < time(9, 30), ["open", "high", "low", "close"]] = 24005.0
        d.loc[(t < time(9, 30)) & (d.timestamp.dt.minute % 2 == 0), ["high"]] = 24010.0
        d.loc[(t < time(9, 30)) & (d.timestamp.dt.minute % 2 == 1), ["low"]] = 24000.0
        d.loc[t >= time(9, 30), ["open", "high", "low", "close"]] = 24005.0
        d.loc[t == break_at, ["close"]] = 23990.0
        return d
    assert signal(day(time(13, 0)), 15, None) is not None
    assert signal(day(time(13, 1)), 15, None) is None


def test_e_half_session_and_missing_candles_never_crash_and_never_invent_a_bar():
    for seed in range(60):
        d = random_day(seed)
        half = d[d.timestamp.dt.time < time(12, 0)].reset_index(drop=True)
        sig = signal(half, 15, None)
        assert sig is None or sig[1] in set(half.timestamp)
        rng = np.random.default_rng(seed)
        holes = d[(d.timestamp.dt.time < time(9, 30)) | (rng.random(len(d)) > 0.15)].reset_index(drop=True)   # 15 % of later bars missing
        sig = signal(holes, 15, None)
        assert sig is None or sig[1] in set(holes.timestamp)


def test_e_no_opening_range_means_no_signal():
    d = random_day(3)
    assert signal(d[d.timestamp.dt.time >= time(9, 30)].reset_index(drop=True), 15, None) is None


def test_known_gap_a_partly_missing_opening_range_is_accepted_as_is():
    """Documented gap: `signal` (and the live trader) take the range from whatever bars exist before 09:30; a day with only the last five opening
    minutes still trades. If a full-range requirement is ever added, update this test and the validation inventory."""
    d = random_day(0, vol=0.0)
    t = d.timestamp.dt.time
    d.loc[:, ["open", "high", "low", "close"]] = 24005.0
    d.loc[(t >= time(9, 25)) & (t < time(9, 30)), "high"] = 24010.0
    d.loc[(t >= time(9, 25)) & (t < time(9, 30)), "low"] = 24000.0
    d.loc[t == time(9, 40), "close"] = 23990.0
    partial = d[(t >= time(9, 25))].reset_index(drop=True)
    sig = signal(partial, 15, None)
    assert sig is not None and sig[0] == "PE" and sig[1].time() == time(9, 40)


def test_e_expiry_boundary_the_live_trader_takes_the_next_expiry_strictly_after_today(tmp_path):
    tr = G.G1Trader(Stream(), Upstox(), tmp_path)
    assert tr.expiry_after(date(2026, 11, 2)) == "2026-11-03"
    assert tr.expiry_after(date(2026, 11, 3)) == EXP                      # on an expiry day the NEXT expiry is bought, never today's
    assert tr.expiry_after(date(2026, 11, 10)) is None


def test_e_live_no_option_quote_in_the_entry_minute_is_no_trade_not_a_guess(tmp_path, monkeypatch):
    monkeypatch.setattr(G.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(G.alerts, "send", lambda *a, **k: False)
    st = Stream()
    tr = G.G1Trader(st, Upstox(), tmp_path)

    def spot_only(t):
        m = t.time()
        st.vix(13.0)
        st.spot(24000.0 if (t.second // 10) % 2 and m < time(9, 30) else 24010.0 if m < time(9, 30) else 24004.0 if m < time(9, 40) else 23990.0)
    run(tr, D1, time(9, 15), time(9, 45), before=spot_only)                # no option quotes at all
    assert tr.state["open"] is None and "no ask" in tr.state["days"][str(D1)]["status"]
