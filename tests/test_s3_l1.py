"""S3 L1: signal on closes only, lot by expiry, ATM by parity, exit fallback, one position at a time, costs."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from scanner import s3_l1 as M


def sessions(n=30, start=date(2020, 3, 2)):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def test_signal_needs_above_22_and_above_five_sessions_ago():
    s = sessions(12)
    v = pd.Series([20, 21, 21, 21, 21, 23, 22.5, 19, 23, 23, 23, 25], index=s)
    sig = M.signals(s, v)
    assert s[5] in sig and sig[s[5]] == (23, 20)        # 23 > 22 and > 20
    assert s[6] in sig                                   # 22.5 > 21
    assert s[7] not in sig                               # 19 < 22
    assert s[10] not in sig                              # 23 > 22 but not above 23 five sessions earlier
    assert all(d >= s[5] for d in sig)                   # the first five sessions have no lookback


def test_lot_by_contract_expiry():
    assert M.lot_for(date(2021, 7, 22)) == 75 and M.lot_for(date(2021, 7, 29)) == 50 and M.lot_for(date(2018, 3, 28)) == 75


def chain(s, expiry, ce, pe, vol=500, strikes=(9900, 10000, 10100)):
    rows = []
    for i, d in enumerate(s):
        for k in strikes:
            off = (k - 10000) / 10
            rows += [{"TradDt": d, "XpryDt": expiry, "StrkPric": float(k), "OptnTp": "CE", "ClsPric": ce[i] - off, "TtlTradgVol": vol},
                     {"TradDt": d, "XpryDt": expiry, "StrkPric": float(k), "OptnTp": "PE", "ClsPric": pe[i] + off, "TtlTradgVol": vol}]
    return pd.DataFrame(rows)


def test_simulate_entry_next_close_exit_after_five_sessions_and_costs():
    s = sessions(20)
    ex = s[-1] + timedelta(days=7)
    ce = [100.0] * 20
    pe = [100.0] * 20
    ce[7] = 150.0                                         # exit session = entry (s[1]) + 5 = s[6]? no: s[6]
    ce[6] = 130.0
    b = chain(s, ex, ce, pe)
    t, sk = M.simulate(b, s, {s[0]}, pd.Series(dtype=float), pd.Series(dtype=float))
    r = t.iloc[0]
    assert r["day"] == s[1] and r["exit_day"] == s[6] and r["strike"] == 10000 and r["lot"] == 75
    debit = 200 * 1.01 * 75
    gross = (130 + 100) * 0.99 * 75 - debit
    assert r["debit_rs"] == pytest.approx(debit) and r["net_rs"] == pytest.approx(gross - r["fees_rs"], abs=0.02)
    t2, _ = M.simulate(b, s, {s[0]}, pd.Series(dtype=float), pd.Series(dtype=float), cost_mult=2)
    assert t2.iloc[0]["net_rs"] < r["net_rs"]


def test_one_position_at_a_time_and_signal_on_exit_day_allowed():
    s = sessions(30)
    b = chain(s, s[-1] + timedelta(days=12), [100.0] * 30, [100.0] * 30)
    t, _ = M.simulate(b, s, {s[0], s[2], s[6], s[7]}, pd.Series(dtype=float), pd.Series(dtype=float))
    assert list(t["signal_day"]) == [s[0], s[6]]          # s[2] inside the first trade; s[6] = its exit day


def test_exit_fallback_and_data_gap():
    s = sessions(20)
    ex = s[-1] + timedelta(days=7)
    b = chain(s, ex, [100.0] * 20, [100.0] * 20)
    b.loc[(b["TradDt"] == s[6]) & (b["OptnTp"] == "CE"), "TtlTradgVol"] = 0
    t, _ = M.simulate(b, s, {s[0]}, pd.Series(dtype=float), pd.Series(dtype=float))
    assert t.iloc[0]["exit_day"] == s[7] and bool(t.iloc[0]["exit_fallback"])
    for j in (6, 7, 8):
        b.loc[(b["TradDt"] == s[j]) & (b["OptnTp"] == "PE"), "TtlTradgVol"] = 0
    t, sk = M.simulate(b, s, {s[0]}, pd.Series(dtype=float), pd.Series(dtype=float))
    assert t.empty and sk[0]["why"] == "data gap at exit"


def test_entry_skipped_without_liquid_strike():
    s = sessions(20)
    b = chain(s, s[-1] + timedelta(days=7), [100.0] * 20, [100.0] * 20, vol=50)
    t, sk = M.simulate(b, s, {s[0]}, pd.Series(dtype=float), pd.Series(dtype=float))
    assert t.empty and "100 contracts" in sk[0]["why"]


def test_expiry_under_10_days_out_is_not_used():
    s = sessions(20)
    ex = s[4]                                              # only expiry is 4 sessions out
    b = chain(s, ex, [100.0] * 20, [100.0] * 20)
    t, sk = M.simulate(b, s, {s[0]}, pd.Series(dtype=float), pd.Series(dtype=float))
    assert t.empty and "10 days" in sk[0]["why"]
