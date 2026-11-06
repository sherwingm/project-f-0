"""Near Tighty (NT) max up after entry (the user, 2026-11-06: "our main motive is to take away the max up after entry,
it is not about the exit"; "don't mix this with near tighty ... create a separate data storage file").

NT = G1's NIFTY downside opening-range-breakout put, only when the expiry is 1-3 sessions away
(strategies/NT_near_tighty.md). This script measures, for every G1 history trade (data/results/S3_G1_datasheet.csv,
2024-10 -> 2026-10; entry price = the engine's fill, the 'Premium paid'), the highest later minute close of the put as
% above that entry price. It does NOT apply any stop or exit: the put is simply followed.
Windows (all start after the entry minute):
  to_next_0916  : until 09:16 of the next session (the NT hold window, no stop)
  to_next_close : until 15:29 of the next session
  to_expiry     : until 15:29 of the expiry day (held with no exit)
Also the day-1 window (entry -> 15:29 same day). Marks follow scanner.s3_buy_maxup (last traded close carried forward,
a mark older than 30 minutes is not counted).

Reads : data/results/S3_G1_datasheet.csv, option minutes via index_data (INDEX_STORE).
Writes: near_tighty_research/data/nt_maxup_trades.csv  (the storage file: one row per trade, every window)
        near_tighty_research/results/nt_maxup_summary.csv  (by days to expiry, NT 1-3 vs 4-5, per half-year)
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


def main():
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    rows = []
    for r in d.to_dict("records"):
        day, expiry = date.fromisoformat(str(r["Day"])[:10]), date.fromisoformat(str(r["Expiry"])[:10])
        k, paid, dte = float(r["Strike"]), float(r["Premium paid (₹/unit)"]), int(r["Days to expiry"])
        hh, mm = (int(x) for x in str(r["Entry time"]).split(":"))
        days = [x for x in L.trade_days("NIFTY", expiry) if x > day]
        nxt = days[0] if days else None
        base = {"day": day, "expiry": expiry, "dte": dte, "nt": int(1 <= dte <= 3), "entry": f"{hh:02d}:{mm:02d}",
                "strike": k, "paid": paid, "g1_exit": r["G1 exit"], "g1_net_pct": r["G1 net %"],
                "g1_max_up_held_pct": r["G1 max up held %"], "vix": r["VIX at signal"], "gap_pct": r["Day-1 gap at open %"]}
        legs = [("B", k, "PE", paid, 0.0)]
        t_in = L.at(day, hh, mm)
        # day-1 window
        c1 = chain_between("NIFTY", expiry, day, None)
        m1 = max_up(c1, legs, t_in, L.at(day, 15, 29), L.at(day, 15, 29))
        base["max_up_day1_pct"] = m1["max_up_any_pct"]
        if nxt is None:
            rows.append(base)
            continue
        c2 = chain_between("NIFTY", expiry, day, nxt)
        m2 = max_up(c2, legs, t_in, L.at(nxt, 9, 16), L.at(nxt, 15, 29))
        base["max_up_to_next_0916_pct"], base["peak_to_next_0916_at"] = m2["max_up_held_pct"], m2["peak_held_at"]
        base["max_up_to_next_close_pct"], base["peak_to_next_close_at"] = m2["max_up_any_pct"], m2["peak_any_at"]
        c3 = chain_between("NIFTY", expiry, day, expiry)
        m3 = max_up(c3, legs, t_in, L.at(nxt, 9, 16), L.at(expiry, 15, 29))
        base["max_up_to_expiry_pct"], base["peak_to_expiry_at"] = m3["max_up_any_pct"], m3["peak_any_at"]
        rows.append(base)
    T = pd.DataFrame(rows)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    T.to_csv(os.path.join(ROOT, "data", "nt_maxup_trades.csv"), index=False)

    cols = ["max_up_day1_pct", "max_up_to_next_0916_pct", "max_up_to_next_close_pct", "max_up_to_expiry_pct"]
    out = []

    def block(name, G):
        for c in cols:
            v = G[c].dropna().values
            o = {"group": name, "window": c.replace("max_up_", "").replace("_pct", ""), "n": len(v),
                 "mean": np.mean(v) if len(v) else np.nan, "median": np.median(v) if len(v) else np.nan}
            for lv in LEVELS:
                o[f"ge{lv}"] = np.mean(v >= lv) if len(v) else np.nan
                o[f"n_ge{lv}"] = int((v >= lv).sum())
            out.append(o)
    block("NT (1-3 sessions to expiry)", T[T["nt"] == 1])
    block("not NT (4-5 sessions)", T[T["nt"] == 0])
    for k in sorted(T["dte"].unique()):
        block(f"dte {k}", T[T["dte"] == k])
    nt = T[T["nt"] == 1].copy()
    nt["half"] = np.where(pd.to_datetime(nt["day"]) < pd.Timestamp("2025-10-01"), "Oct24-Sep25", "Oct25-Oct26")
    for h, G in nt.groupby("half"):
        block(f"NT {h}", G)
    S = pd.DataFrame(out)
    S.to_csv(os.path.join(ROOT, "results", "nt_maxup_summary.csv"), index=False)
    pd.set_option("display.width", 200)
    sh = S.copy()
    sh[["mean", "median"]] = sh[["mean", "median"]].round(0)
    for lv in LEVELS:
        sh[f"ge{lv}"] = (sh[f"ge{lv}"] * 100).round(0)
    print(sh[["group", "window", "n", "mean", "median", "ge50", "ge100", "ge200", "n_ge100"]].to_string(index=False))
    print("trades", len(T), "NT", int(T["nt"].sum()))


if __name__ == "__main__":
    main()
