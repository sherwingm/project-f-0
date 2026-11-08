"""Near Tighty (NT) results for 2025-10-01 -> present (the user, 2026-11-08: "get the result between the year of 2025 oct to
present"). A re-cut of the booked NT trades; no new simulation. NT = G1's downside opening-range put, 1-3 sessions to expiry.

    python near_tighty_research/scripts/nt_oct2025_on.py

Reads data/nt_target_trades.csv (NIFTY, nt_targets.py) and data/nt_sensex_booked_trades.csv (SENSEX, nt_sensex_booked.py);
history ends 2026-10-28. Max up = the put's highest minute close after entry through the window (no stop, no exit);
booked = 50 % stop, 0.5 % exit slippage, charges, 1 lot (NIFTY lot of the day, SENSEX lot 20).
Writes near_tighty_research/results/nt_oct2025_on.csv.
"""
import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from scanner.stats import clustered_t  # noqa: E402

FROM = "2025-10-01"


def load():
    n = pd.read_csv(os.path.join(ROOT, "data", "nt_target_trades.csv"))
    n = n[(n["nt"] == 1) & n["window"].isin(("nt_live", "g1_live"))].copy()
    n["window"] = n["window"].map({"nt_live": "next_0916", "g1_live": "next_close"})
    s = pd.read_csv(os.path.join(ROOT, "data", "nt_sensex_booked_trades.csv"))
    s = s[s["nt"] == 1].copy()
    out = []
    for idx, d in (("NIFTY", n), ("SENSEX", s)):
        d = d.copy()
        d["day"] = d["day"].astype(str).str[:10]
        d["index"] = idx
        out.append(d)
    return pd.concat(out, ignore_index=True)


def stats(g):
    x = g["net_pct"]
    top = g.nlargest(5, "net_rs")
    m = g.groupby(g["day"].str[:7])["net_rs"].sum()
    return {"n": len(g), "mean_pct": x.mean(), "median_pct": x.median(), "won": (x > 0).mean(),
            "t": clustered_t(x, g["day"]), "total_rs": g["net_rs"].sum(), "stop_hit": (g["reason"] == "stop").mean(),
            "worst_rs": g["net_rs"].min(), "mean_without_top5_pct": g.drop(top.index)["net_pct"].mean(),
            "months": len(m), "positive_months": int((m > 0).sum()),
            "maxup_mean": g["max_up_pct"].mean(), "maxup_median": g["max_up_pct"].median(),
            "ge50": (g["max_up_pct"] >= 50).mean(), "ge100": (g["max_up_pct"] >= 100).mean(),
            "ge200": (g["max_up_pct"] >= 200).mean()}


def main():
    T = load()
    rows = []
    for period, d in (("2025-10 -> now", T[T["day"] >= FROM]), ("before 2025-10", T[T["day"] < FROM]),
                      ("whole history", T)):
        for (idx, win, tg), g in d.groupby(["index", "window", "target"]):
            if tg in ("none", "2x", "3x"):
                rows.append({"period": period, "index": idx, "window": win, "target": tg, **stats(g)})
    S = pd.DataFrame(rows)
    S.to_csv(os.path.join(ROOT, "results", "nt_oct2025_on.csv"), index=False)
    pd.set_option("display.width", 250)
    print(S[(S["period"] == "2025-10 -> now")].round(2).to_string(index=False))
    print(S[(S["target"] == "none") & (S["window"] == "next_0916")][["period", "index", "n", "mean_pct", "t", "total_rs"]].round(2).to_string(index=False))
    print("last trade day:", T["day"].max(), "first in period:", T[T["day"] >= FROM]["day"].min())


if __name__ == "__main__":
    main()
