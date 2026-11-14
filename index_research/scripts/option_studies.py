"""R06-R08 of index_research/PROGRAM.md on NIFTY option minutes (Oct 2024 - Oct 2026) with the S3 engine (fills, slippage, dated charges).
Periods: D = to 2025-09-30, V = from 2025-10-01 (no late period). Validation runs only for discovery passers (BH 10 % across the study).
Amendment A1 (PROGRAM.md, written before this script ran): R07 FOMC exit = 15:25 on the FOMC date (the US announcement is after the Indian close).
Usage: python index_research/scripts/option_studies.py R06 | R07 | R08
"""
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

from lib import L, boot_ci, bh, mc_drawdown, save, summary, validation_pass
from scanner import s3_regime as G
from scanner.s3_b2 import signal
from scanner.s3_buy4 import BUDGET, FOMC_US, RBI, expiry_after
from scanner.s3_engine import Leg, Spec, run_day

sys.stdout.reconfigure(encoding="utf-8")
W = (date(2024, 10, 1), date(2026, 10, 28))
SPLIT = date(2025, 10, 1)


def sessions():
    sp = L.spot_1m(W[0], W[1] + timedelta(days=10), "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    return {d: g for d, g in sp.groupby("d") if len(g) >= G.MIN_BARS}


def one(name, legs, day, e, entry, exit_, exit_day, stop=None, cm=1.0):
    r = run_day(Spec(name, legs, entry=entry, exit=exit_, stop=stop, cost_mult=cm), day, e, exit_day=exit_day)
    return None if r.get("skip") else r


def rec(cell, day, legs, e, entry, exit_, exit_day, stop=None, extra=None):
    a = one(cell, legs, day, e, entry, exit_, exit_day, stop)
    if a is None:
        return None
    b = one(cell, legs, day, e, entry, exit_, exit_day, stop, 2.0)
    o = {"cell": cell, "day": day, "net_pct": a["net_pct_premium"], "net_rs": a["net_rs"], "reason": a["reason"],
         "net_pct_2x": b["net_pct_premium"] if b else np.nan}
    o.update(extra or {})
    return o


def vix_frames():
    v = L.vix_1m(W[0] - timedelta(days=500), W[1] + timedelta(days=1))
    v["d"] = v["timestamp"].dt.date
    dv = v.groupby("d")["close"].last()
    vov = dv.rolling(5).std()
    vov_med = vov.rolling(250, min_periods=120).median().shift(1)
    return v, dv, vov, vov_med


def r06(days):
    ses = sorted(days)
    v, dv, vov, vov_med = vix_frames()
    out = []
    structs = {"short_fly": [Leg("SELL", "CE", 0), Leg("SELL", "PE", 0), Leg("BUY", "CE", 10), Leg("BUY", "PE", -10)],
               "short_straddle": [Leg("SELL", "CE", 0), Leg("SELL", "PE", 0)],
               "long_straddle": [Leg("BUY", "CE", 0), Leg("BUY", "PE", 0)]}
    for i, d in enumerate(ses[:-1]):
        if not W[0] <= d <= W[1]:
            continue
        nxt = ses[i + 1]
        e = expiry_after(d)
        if e is None:
            continue
        vv = v[(v["d"] == d) & (v["timestamp"] <= L.at(d, 15, 15))]
        vix = float(vv["close"].iloc[-1]) if len(vv) else np.nan
        prevd = ses[i - 1] if i else None
        f_vix = 12 <= vix <= 18
        f_vov = f_vix and prevd in vov.index and vov.get(prevd, np.nan) < vov_med.get(prevd, np.nan)
        for s, legs in structs.items():
            r = rec(f"{s}", d, legs, e, (15, 15), (9, 16), nxt)
            if r is None:
                continue
            for f, ok in (("all", True), ("vix", f_vix), ("vixvov", f_vov)):
                if ok:
                    out.append({**r, "cell": f"{s}_{f}"})
    return out


def r07(days):
    ses = sorted(days)
    exps = sorted(L.expiries("NIFTY"))
    out = []
    events = [(d, "RBI", (9, 58)) for d in RBI] + [(d, "Budget", (10, 58)) for d in BUDGET] + [(d, "FOMC", (15, 25)) for d in FOMC_US]
    for E, kind, ex in events:
        if E not in days:
            print("no session for", kind, E)
            continue
        k = ses.index(E)
        if k < 3:
            continue
        d0 = ses[k - 3]
        e = next((x for x in exps if x >= E), None)
        if e is None:
            continue
        for nm, legs in (("straddle", [Leg("SELL", "CE", 0), Leg("SELL", "PE", 0)]), ("strangle", [Leg("SELL", "CE", 2), Leg("SELL", "PE", -2)])):
            for stop in (None, 0.3):
                r = rec(f"{nm}_stop{0 if stop is None else 30}", d0, legs, e, (15, 15), ex, E, stop, {"event": kind, "event_day": E})
                if r:
                    out.append(r)
                else:
                    print("no prices", kind, E, nm)
    return out


def r08(days):
    ses = sorted(days)
    exps = sorted(L.expiries("NIFTY"))
    out = []
    for i, d in enumerate(ses[:-1]):
        if not W[0] <= d <= W[1]:
            continue
        sg = signal(days[d], 15, None)
        if sg is None:
            continue
        side = sg[0]
        e = expiry_after(d)
        if e is None:
            continue
        e2 = next((x for x in exps if x > e), None)
        ent = sg[1] + timedelta(minutes=1)
        nxt = ses[i + 1]
        itm = 1 if side == "PE" else -1
        for en, ee in (("near", e), ("next", e2)):
            if ee is None:
                continue
            for kn, k in (("atm", 0), ("itm1", itm)):
                r = rec(f"{side}_{en}_{kn}", d, [Leg("BUY", side, k)], ee, (ent.hour, ent.minute), (15, 29), nxt, 0.5)
                if r:
                    out.append(r)
    return out


def evaluate(study, trades):
    T = pd.DataFrame(trades)
    T["period"] = np.where(T["day"] < SPLIT, "D", "V")
    save(T, f"{study}_trades.csv")
    rows = [{"key": k, **summary(x)} for k, x in T[T["period"] == "D"].groupby("cell")]
    C = bh(pd.DataFrame(rows))
    save(C, f"{study}_discovery.csv")
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 200)
    cols = ["key", "n", "win_pct", "mean_pct", "median_pct", "total_rs", "t", "pf", "mean_2x", "h1_mean", "h2_mean", "max_dd_rs", "discovery_pass"]
    print(f"=== {study} DISCOVERY (to 2025-09-30) ===")
    print(C[cols].round(2).to_string(index=False))
    vrows = []
    for key in C.loc[C["discovery_pass"], "key"]:
        x = T[(T["cell"] == key) & (T["period"] == "V")]
        s = {"key": key, **summary(x)}
        s["validation_pass"] = validation_pass(s)
        if s["validation_pass"]:
            lo, hi = boot_ci(x)
            s.update({"boot_lo": lo, "boot_hi": hi, **mc_drawdown(x["net_rs"])})
        vrows.append(s)
    if vrows:
        V = pd.DataFrame(vrows)
        save(V, f"{study}_validation.csv")
        print(f"=== {study} VALIDATION (2025-10 ->) ===")
        print(V.round(2).to_string(index=False))
    print("discovery passes:", int(C["discovery_pass"].sum()))
    return T, C


if __name__ == "__main__":
    days = sessions()
    for st in sys.argv[1:]:
        evaluate(st, {"R06": r06, "R07": r07, "R08": r08}[st](days))
