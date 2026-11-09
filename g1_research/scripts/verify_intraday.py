"""Tests 2-5 of g1_research/VERIFY_PREREG.md on NIFTY option 1-minute trade prices, 2024-10-01 to 2026-10-28:
2 Zerodha ORB on option premium (replication), 3 forum 2 %/2 % open trade, 4 the 30-minute ORB bot (gross vs net),
5 the "11.5-year" exit rules on our breakout entries. History only; claims to check, not rules adopted."""
import os
import sys
from datetime import date, datetime, time, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from index_data import load as L  # noqa: E402
from scanner import s3_regime as G  # noqa: E402
from scanner.s3_b2 import signal  # noqa: E402
from scanner.s3_buy4 import expiry_after  # noqa: E402
from server import charges as CH  # noqa: E402

WINDOW = (date(2024, 10, 1), date(2026, 10, 28))
HALF = date(2025, 10, 1)
STEP = 50
EXP = sorted(L.expiries("NIFTY"))


@lru_cache(maxsize=64)
def chain(expiry, day):
    df = L.options_day("NIFTY", expiry, day)
    if df.empty:
        return df
    df = df.copy()
    df["t"] = df["timestamp"].dt.time
    return df


def contract(expiry, day, strike, opt):
    c = chain(expiry, day)
    if c.empty:
        return c
    x = c[(c["strike"] == strike) & (c["option_type"] == opt)].sort_values("timestamp")
    return x.set_index("t")[["open", "high", "low", "close"]]


def current_expiry(day):
    for e in EXP:
        if e >= day and not chain(e, day).empty:
            return e
    return None


def bar_at(b, t, back=3):
    """Close of the bar at minute t, or the last one within `back` minutes before."""
    for k in range(back + 1):
        tt = (datetime.combine(date.today(), t) - timedelta(minutes=k)).time()
        if tt in b.index:
            return float(b.loc[tt, "close"])
    return None


def run(b, entry_t, exit_t, slip, stop=None, trail=False, target_pts=None, stop_pts=None):
    """Buy at the entry minute's close (+slip); walk later minutes to exit_t. stop: fraction below entry (0.3 = 30 %).
    trail: after +20 % the stop is max(entry, 80 % of the highest high). target_pts / stop_pts: absolute premium points.
    Returns (entry fill, exit fill, reason, max up % to exit_t with no stop) or None."""
    px = bar_at(b, entry_t, back=0)
    if px is None or px <= 0:
        return None
    fill = px * (1 + slip)
    later = b[(b.index > entry_t) & (b.index <= exit_t)]
    mu = (later["high"].max() / fill - 1) * 100 if len(later) else 0.0
    lvl = fill * (1 - stop) if stop is not None else (fill - stop_pts if stop_pts is not None else None)
    tgt = fill + target_pts if target_pts is not None else None
    peak, armed = fill, False
    for t, r in later.iterrows():
        if lvl is not None and r["low"] <= lvl:
            out = min(r["open"], lvl) if r["open"] <= lvl else lvl
            return fill, out * (1 - slip), "stop", mu
        if tgt is not None and r["high"] >= tgt:
            return fill, max(r["open"], tgt) * (1 - slip), "target", mu
        if trail:
            peak = max(peak, r["high"])
            if peak >= fill * 1.2:
                armed = True
            if armed:
                lvl = max(fill, peak * 0.8, lvl if lvl is not None else 0)
    last = bar_at(b, exit_t)
    if last is None:
        return None
    return fill, last * (1 - slip), "time", mu


def trade(day, expiry, strike, opt, qty, res, net=True):
    if res is None:
        return None
    fill, out, why, mu = res
    gross = (out - fill) * qty
    fees = (CH.leg(opt, "BUY", qty, fill)["total"] + CH.leg(opt, "SELL", qty, out)["total"]) if net else 0.0
    rs = gross - fees
    return {"day": day, "expiry": expiry, "strike": strike, "opt": opt, "qty": qty, "fill": fill, "out": out, "reason": why,
            "max_up": mu, "net_rs": rs, "net_pct": rs / (fill * qty) * 100}


def summary(T, label):
    if T.empty:
        return {"test": label, "n": 0}
    T = T.sort_values("day")
    eq = T["net_rs"].cumsum()
    dd = (eq - eq.cummax()).min()
    x = T["net_pct"]
    t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else np.nan
    h1, h2 = T[T["day"] < HALF], T[T["day"] >= HALF]
    return {"test": label, "n": len(T), "maxup_ge50": (T.max_up >= 50).mean() * 100, "maxup_ge100": (T.max_up >= 100).mean() * 100,
            "maxup_mean": T.max_up.mean(), "maxup_med": T.max_up.median(), "win": (x > 0).mean() * 100, "mean": x.mean(),
            "median": x.median(), "t": t, "total_rs": T.net_rs.sum(), "maxdd_rs": dd,
            "h1_mean": h1.net_pct.mean(), "h1_rs": h1.net_rs.sum(), "h2_mean": h2.net_pct.mean(), "h2_rs": h2.net_rs.sum(),
            "stopped": (T.reason == "stop").mean() * 100}


def nxt(t, k=1):
    return (datetime.combine(date.today(), t) + timedelta(minutes=k)).time()


def main():
    sp = L.spot_1m(WINDOW[0] - timedelta(days=10), WINDOW[1], "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    spot = {d: g.assign(t=g["timestamp"].dt.time).set_index("t") for d, g in sp.groupby("d") if len(g) >= G.MIN_BARS}
    ses = sorted(spot)
    rows = {k: [] for k in ("T2_02", "T2_05", "T2_02_1525", "T3", "T4_gross", "T4_net", "T5_trail", "T5_30", "T5_none")}
    for i, day in enumerate(ses):
        if not WINDOW[0] <= day <= WINDOW[1] or i == 0:
            continue
        s = spot[day]
        e = current_expiry(day)
        if e is None:
            continue
        qty = L.lot_on(day, "NIFTY", e)
        c = chain(e, day)
        # ---- Test 2: Zerodha ORB on premium
        at916 = c[c["t"] == time(9, 16)]
        for opt in ("CE", "PE"):
            a = at916[at916["option_type"] == opt]
            if a.empty:
                continue
            k = float(a.iloc[(a["close"] - 200).abs().argsort()[:1]]["strike"].iloc[0])
            b = contract(e, day, k, opt)
            rng = b[(b.index >= time(9, 15)) & (b.index <= time(11, 14))]
            if len(rng) < 30:
                continue
            hi = rng["high"].max()
            trig = b[(b.index >= time(11, 15)) & (b.index <= time(15, 0)) & (b["close"] > hi)]
            if trig.empty:
                continue
            et = nxt(trig.index[0])
            for key, slip, ex in (("T2_02", 0.002, time(15, 15)), ("T2_05", 0.005, time(15, 15)), ("T2_02_1525", 0.002, time(15, 25))):
                tr = trade(day, e, k, opt, qty, run(b, et, ex, slip, stop=0.2))
                if tr:
                    rows[key].append(tr)
        # ---- Test 3: open vs previous close, 1 ITM, +/- Rs 2,000, 15 minutes
        prev = spot[ses[i - 1]]
        o, pc = float(s["open"].iloc[0]), float(prev["close"].iloc[-1])
        if o != pc and time(9, 29) in s.index:
            opt = "CE" if o > pc else "PE"
            atm = round(float(s.loc[time(9, 29), "close"]) / STEP) * STEP
            k = atm - STEP if opt == "CE" else atm + STEP
            b = contract(e, day, float(k), opt)
            if len(b):
                pts = 2000 / qty
                tr = trade(day, e, k, opt, qty, run(b, time(9, 29), time(9, 44), 0.005, target_pts=pts, stop_pts=pts))
                if tr:
                    rows["T3"].append(tr)
        # ---- Test 4: 30-minute ORB bot
        sg = signal(sp[sp["d"] == day].reset_index(drop=True), 30, None)
        if sg is not None:
            opt = sg[0]
            et = nxt(sg[1].time())
            if et in s.index:
                atm = float(round(float(s.loc[et, "close"]) / STEP) * STEP)
                b = contract(e, day, atm, opt)
                if len(b):
                    for key, slip, net in (("T4_gross", 0.0, False), ("T4_net", 0.005, True)):
                        tr = trade(day, e, atm, opt, qty, run(b, et, time(15, 15), slip, stop=0.3), net=net)
                        if tr:
                            rows[key].append(tr)
        # ---- Test 5: 11.5-year exit rules on our 15-minute breakout entries (both sides, G1's expiry rule)
        sg = signal(sp[sp["d"] == day].reset_index(drop=True), 15, None)
        e5 = expiry_after(day)
        if sg is not None and e5 is not None:
            opt = sg[0]
            et = nxt(sg[1].time())
            if et in s.index:
                atm = float(round(float(s.loc[et, "close"]) / STEP) * STEP)
                b = contract(e5, day, atm, opt)
                q5 = L.lot_on(day, "NIFTY", e5)
                if len(b):
                    for key, kw in (("T5_trail", dict(stop=0.3, trail=True)), ("T5_30", dict(stop=0.3)), ("T5_none", {})):
                        tr = trade(day, e5, atm, opt, q5, run(b, et, time(15, 15), 0.005, **kw))
                        if tr:
                            rows[key].append(tr)
    pd.set_option("display.width", 260)
    allrows = []
    for key, lst in rows.items():
        T = pd.DataFrame(lst)
        T.to_csv(os.path.join(ROOT, "data", f"verify_{key}.csv"), index=False)
        allrows.append(summary(T, key))
        if key in ("T2_02", "T4_net", "T5_trail") and len(T):
            for opt, g in T.groupby("opt"):
                allrows.append(summary(g, f"{key} {opt}"))
        if len(T):
            T["yr"] = pd.to_datetime(T["day"]).dt.year
            print(key, "by year (net % mean, total Rs):", {int(y): (round(g.net_pct.mean(), 1), round(g.net_rs.sum())) for y, g in T.groupby("yr")})
    S = pd.DataFrame(allrows)
    S.to_csv(os.path.join(ROOT, "results", "verify_intraday_summary.csv"), index=False)
    print(S.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
