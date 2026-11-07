"""G1 / G1-F max up after entry with NO exit (the user, 2026-11-06: "our main motive is the max up after entry, it is
not about the exit"). Normal index work; own folder, not mixed with expiry_research/ or near_tighty_research/.

For every G1 history trade from 2025-01-01 (data/results/S3_G1_datasheet.csv; entry = the engine's fill, 'Premium
paid') the put is followed after the entry minute with no stop and no exit, and the highest later minute close is
taken as % above the price paid. Windows:
  day1          entry -> 15:29 of the entry day
  next_0916     entry -> 09:16 of the next session (G1's hold window, but WITHOUT the 50 % stop cutting it short)
  next_close    entry -> 15:29 of the next session
G1-F = the same trades that pass the three skip filters (day-1 gap < +0.3 %, range width not in 0.5-0.8 %, VIX < 17).
Marks follow scanner.s3_buy_maxup (last traded close carried forward; a mark older than 30 minutes is not counted).
Writes g1_research/data/g1_maxup_free_trades.csv and g1_research/results/g1_maxup_free_summary.csv.
"""
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from index_data import load as L  # noqa: E402
from scanner.s3_buy_maxup import max_up  # noqa: E402
from scanner.s3_engine import chain_between  # noqa: E402

LEVELS = (25, 50, 100, 200)
WIN = ("day1", "next_0916", "next_close")


def main():
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    d = d[pd.to_datetime(d["Day"]) >= "2025-01-01"]
    num = lambda c: pd.to_numeric(d[c], errors="coerce")  # noqa: E731
    gap, wid, vix = num("Day-1 gap at open %"), num("OR width %"), num("VIX at signal")
    d = d.assign(g1f=~((gap >= 0.3) | ((wid >= 0.5) & (wid < 0.8)) | (vix >= 17)))
    rows = []
    for r in d.to_dict("records"):
        day, expiry = date.fromisoformat(str(r["Day"])[:10]), date.fromisoformat(str(r["Expiry"])[:10])
        k, paid = float(r["Strike"]), float(r["Premium paid (₹/unit)"])
        hh, mm = (int(x) for x in str(r["Entry time"]).split(":"))
        legs, t_in = [("B", k, "PE", paid, 0.0)], L.at(day, hh, mm)
        nxt = next((x for x in L.trade_days("NIFTY", expiry) if x > day), None)
        o = {"day": day, "entry": f"{hh:02d}:{mm:02d}", "strike": k, "paid": paid, "g1f": int(r["g1f"]),
             "g1_exit": r["G1 exit"], "g1_net_pct": r["G1 net %"], "g1_max_up_held_pct": r["G1 max up held %"]}
        m1 = max_up(chain_between("NIFTY", expiry, day, None), legs, t_in, L.at(day, 15, 29), L.at(day, 15, 29))
        o["day1"] = m1["max_up_any_pct"]
        if nxt is not None:
            m2 = max_up(chain_between("NIFTY", expiry, day, nxt), legs, t_in, L.at(nxt, 9, 16), L.at(nxt, 15, 29))
            o["next_0916"], o["next_close"] = m2["max_up_held_pct"], m2["max_up_any_pct"]
            o["peak_next_close_at"] = m2["peak_any_at"]
        rows.append(o)
    T = pd.DataFrame(rows)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    T.to_csv(os.path.join(ROOT, "data", "g1_maxup_free_trades.csv"), index=False)
    T["year"] = pd.to_datetime(T["day"]).dt.year
    out = []
    for name, G in (("G1-F (main)", T[T["g1f"] == 1]), ("G1", T)):
        for per, P in (("2025 → now", G), ("2025", G[G["year"] == 2025]), ("2026", G[G["year"] == 2026])):
            for w in WIN:
                v = P[w].dropna().values
                o = {"strategy": name, "period": per, "window": w, "n": len(v), "mean": np.mean(v), "median": np.median(v)}
                for lv in LEVELS:
                    o[f"ge{lv}"], o[f"n_ge{lv}"] = np.mean(v >= lv), int((v >= lv).sum())
                out.append(o)
    S = pd.DataFrame(out)
    S.to_csv(os.path.join(ROOT, "results", "g1_maxup_free_summary.csv"), index=False)
    sh = S.copy()
    sh[["mean", "median"]] = sh[["mean", "median"]].round(0)
    for lv in LEVELS:
        sh[f"ge{lv}"] = (sh[f"ge{lv}"] * 100).round(0)
    pd.set_option("display.width", 200)
    print(sh[["strategy", "period", "window", "n", "mean", "median", "ge50", "ge100", "ge200", "n_ge100"]].to_string(index=False))
    held = T["g1_max_up_held_pct"]
    print("old 'held' max up mean/median", round(held.mean()), round(held.median()), "G1-F", round(T[T.g1f == 1].g1_max_up_held_pct.mean()))


if __name__ == "__main__":
    main()
