"""Mirror of G1 on the call side, NIFTY and SENSEX: first close ABOVE the 09:15-09:29 range (09:30-13:00) -> buy the ATM
CALL (the user, 2026-11-06: "do the call buying too, by inversing the rule of buy put"). Max up after entry, NO exit.
History only, descriptive. Own folder (g1_research/). Entry price = minute close x 1.005 (x 1.01 before 09:30).
Mirror-F = the mirrored skip filters: day-1 gap <= -0.3 %, range width in 0.5-0.8 %, VIX >= 17 (a guess by symmetry; the
original filters were found on puts, so this is NOT tested knowledge).

Same rule as G1 (strategies/S3_G1_put_overnight.md), SENSEX substitutions as in R2 (scanner/s3_buy4.py): SENSEX spot
1-minute bars, strike step 100, SENSEX weekly expiries from the option files:
  opening range 09:15-09:29; the first close outside it 09:30-13:00 (scanner.s3_b2.signal, no acceptance); only a
  close below the low trades; ATM put (strike nearest the entry minute's SENSEX close) of the nearest SENSEX expiry
  after the signal day that has a chain file that day; entry = the minute after the signal minute, price = that
  minute's last traded close x 1.005 (the engine's 0.5 % slippage; x 1.01 before 09:30).
No stop, no exit: the put is followed. Windows: day1 (-> 15:29), next_0916, next_close (as the NIFTY run).
G1-F = same trades that pass: day-1 gap < +0.3 %, range width not in 0.5-0.8 %, India VIX < 17 (all known at the signal).
Out: g1_research/data/sensex_maxup_free_trades.csv, g1_research/results/sensex_maxup_free_summary.csv
"""
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from index_data import load as L  # noqa: E402
from scanner.s3_b2 import signal  # noqa: E402
from scanner.s3_buy_maxup import max_up  # noqa: E402
from scanner.s3_engine import chain_between  # noqa: E402
from scanner.s3_p1 import vix_at  # noqa: E402

START, END = date(2024, 10, 1), date(2026, 10, 28)
MIN_BARS = 300
LEVELS = (25, 50, 100, 200)
WIN = ("day1", "next_0916", "next_close")


def main(UL, IDX, STEP):
    sp = L.spot_1m(START - timedelta(days=10), END + timedelta(days=10), IDX)
    sp["d"] = sp["timestamp"].dt.date
    days = {d: g.reset_index(drop=True) for d, g in sp.groupby("d") if len(g) >= MIN_BARS}
    ses = sorted(days)
    exps = list(L.expiries(UL))
    tdays = {e: set(L.trade_days(UL, e)) for e in exps}
    vcache, rows, skipped = {}, [], {"no expiry file": 0, "no entry price": 0}
    for i, day in enumerate(ses):
        if not START <= day <= END:
            continue
        sg = signal(days[day], 15, None)
        if sg is None or sg[0] != "CE":
            continue
        side, ts, hi, lo = sg
        ent = ts + timedelta(minutes=1)
        e = next((x for x in exps if x > day and day in tdays[x]), None)
        if e is None:
            skipped["no expiry file"] += 1
            continue
        spot = float(days[day].loc[days[day]["timestamp"] == ent, "close"].iloc[0]) if (days[day]["timestamp"] == ent).any() else None
        if spot is None:
            skipped["no entry price"] += 1
            continue
        k = float(round(spot / STEP) * STEP)
        nxt = ses[i + 1] if i + 1 < len(ses) else None
        chain = chain_between(UL, e, day, nxt if nxt and nxt <= e else None)
        t_in = L.at(day, ent.hour, ent.minute)
        px0 = L.price_at(chain, k, "CE", t_in, stale=3)
        if px0 is None:
            skipped["no entry price"] += 1
            continue
        paid = px0 * (1.01 if ent.time() < pd.Timestamp("09:30").time() else 1.005)
        legs = [("B", k, "CE", paid, 0.0)]
        o = {"day": day, "expiry": e, "entry": ent.strftime("%H:%M"), "strike": k, "paid": round(paid, 2), "spot": spot}
        m1 = max_up(chain, legs, t_in, L.at(day, 15, 29), L.at(day, 15, 29))
        o["day1"] = m1["max_up_any_pct"]
        if nxt is not None and nxt <= e:
            c2 = chain_between(UL, e, day, nxt)
            m2 = max_up(c2, legs, t_in, L.at(nxt, 9, 16), L.at(nxt, 15, 29))
            o["next_0916"], o["next_close"] = m2["max_up_held_pct"], m2["max_up_any_pct"]
        width = (hi - lo) / lo * 100
        prev = float(days[ses[i - 1]]["close"].iloc[-1]) if i > 0 else None
        gap = (float(days[day]["open"].iloc[0]) / prev - 1) * 100 if prev else None
        v = vix_at(day, ent.hour, ent.minute, vcache)
        o.update(gap_pct=gap, width_pct=width, vix=v)
        o["g1f"] = int(gap is not None and v is not None and gap > -0.3 and not (0.5 <= width < 0.8) and v < 17)
        rows.append(o)
    T = pd.DataFrame(rows)
    T["year"] = pd.to_datetime(T["day"]).dt.year
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    T.to_csv(os.path.join(ROOT, "data", f"calls_{UL.lower()}_maxup_free_trades.csv"), index=False)
    out = []
    for name, G in ((f"{UL} calls, mirror filters", T[T["g1f"] == 1]), (f"{UL} calls, no filter", T)):
        for per, P in (("Oct 2024 → now", G), ("2025 → now", G[pd.to_datetime(G["day"]) >= "2025-01-01"])):
            for w in WIN:
                v = P[w].dropna().values
                o = {"strategy": name, "period": per, "window": w, "n": len(v),
                     "mean": np.mean(v) if len(v) else np.nan, "median": np.median(v) if len(v) else np.nan}
                for lv in LEVELS:
                    o[f"ge{lv}"], o[f"n_ge{lv}"] = (np.mean(v >= lv) if len(v) else np.nan), int((v >= lv).sum())
                out.append(o)
    S = pd.DataFrame(out)
    S.to_csv(os.path.join(ROOT, "results", f"calls_{UL.lower()}_maxup_free_summary.csv"), index=False)
    sh = S.copy()
    sh[["mean", "median"]] = sh[["mean", "median"]].round(0)
    for lv in LEVELS:
        sh[f"ge{lv}"] = (sh[f"ge{lv}"] * 100).round(0)
    pd.set_option("display.width", 200)
    print(sh[["strategy", "period", "window", "n", "mean", "median", "ge50", "ge100", "ge200", "n_ge100"]].to_string(index=False))
    print("trades", len(T), "G1-F", int(T["g1f"].sum()), "skipped", skipped, "span", T["day"].min(), T["day"].max())
    print(T.groupby(pd.to_datetime(T["day"]).dt.to_period("M")).size().describe()[["mean", "min", "max"]].round(1).to_dict())


if __name__ == "__main__":
    for ul, idx, step in (("NIFTY", "NIFTY50", 50), ("SENSEX", "SENSEX", 100)):
        print("=====", ul)
        main(ul, idx, step)
