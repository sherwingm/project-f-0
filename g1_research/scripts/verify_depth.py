"""Minimum breakout size (g1_research/DEPTH_PREREG.md, variant A): trade only if the signal close is >= X % beyond the range edge."""
import os
import sys
import warnings
from datetime import date

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from index_data import load as L  # noqa: E402
from scanner import s3_regime as G  # noqa: E402
from scanner.s3_b2 import signal  # noqa: E402

HALF = date(2025, 10, 1)
XS = [0.01, 0.02, 0.03, 0.05, 0.10, 0.15, 0.20]


def main():
    sp = L.spot_1m(date(2024, 10, 1), date(2026, 10, 28), "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    days = {d: g.reset_index(drop=True) for d, g in sp.groupby("d") if len(g) >= G.MIN_BARS}
    V = pd.read_csv(os.path.join(ROOT, "data", "verify_strikes_trades.csv"), parse_dates=["day"])
    V = V[V.strike == "ATM"].copy()
    V["day"] = V["day"].dt.date
    dep = {}
    for day in sorted(set(V.day)):
        sg = signal(days[day], 15, None)
        g = days[day]
        close = float(g.loc[g.timestamp == sg[1], "close"].iloc[0])
        dep[day] = ((sg[3] - close) / sg[3] * 100) if sg[0] == "PE" else ((close - sg[2]) / sg[2] * 100)
    V["depth"] = V.day.map(dep)
    a1, a2 = V[V.cost == 1.0].copy(), V[V.cost == 2.0].set_index(["day", "side"])
    a1["net_pct_2x"] = [a2.loc[(d, s), "net_pct"] for d, s in zip(a1.day, a1.side)]
    a1["net_rs_2x"] = [a2.loc[(d, s), "net_rs"] for d, s in zip(a1.day, a1.side)]
    a1.to_csv(os.path.join(ROOT, "data", "verify_depth_trades.csv"), index=False)
    sets = {"G1 puts (259)": a1[a1.side == "PE"], "G1-F puts": a1[(a1.side == "PE") & (a1.g1f == 1)], "Call mirror (235)": a1[a1.side == "CE"]}
    pd.set_option("display.width", 250)
    print("depth % of the signal close beyond the range edge: quantiles", {q: round(float(np.percentile(a1.depth, q)), 3) for q in (10, 25, 50, 75, 90)})
    rows, decisions = [], []
    for name, S in sets.items():
        base = S.net_pct.mean()
        for X in [0.0] + XS:
            kept = S[S.depth >= X]
            drop = S[S.depth < X]
            def m(x, col="net_pct"):
                return x[col].mean() if len(x) else np.nan
            r = {"set": name, "min_depth": X, "kept": len(kept), "dropped": len(drop),
                 "k_ge100": (kept.peak >= 100).mean() * 100, "k_maxup_mean": kept.peak.mean(), "k_maxup_med": kept.peak.median(),
                 "d_ge100": (drop.peak >= 100).mean() * 100 if len(drop) else np.nan, "d_maxup_mean": drop.peak.mean() if len(drop) else np.nan,
                 "k_win": (kept.net_pct > 0).mean() * 100, "k_avg": m(kept), "k_med": kept.net_pct.median(), "k_total": kept.net_rs.sum(),
                 "d_avg": m(drop), "d_total": drop.net_rs.sum() if len(drop) else 0.0, "base_avg": base, "base_total": S.net_rs.sum()}
            rows.append(r)
            if X > 0 and len(drop) > 5 and len(kept) > 5:
                t = stats.ttest_ind(kept.net_pct, drop.net_pct, equal_var=False)
                h1k, h1d = kept[kept.day < HALF], drop[drop.day < HALF]
                h2k, h2d = kept[kept.day >= HALF], drop[drop.day >= HALF]
                d1 = h1k.net_pct.mean() - h1d.net_pct.mean() if len(h1k) and len(h1d) else np.nan
                d2 = h2k.net_pct.mean() - h2d.net_pct.mean() if len(h2k) and len(h2d) else np.nan
                t2 = stats.ttest_ind(kept.net_pct_2x, drop.net_pct_2x, equal_var=False)
                ok = (kept.net_pct.mean() > drop.net_pct.mean() and t.statistic >= 2 and kept.net_pct.mean() > base and d1 > 0 and d2 > 0
                      and kept.net_pct_2x.mean() > drop.net_pct_2x.mean() and t2.statistic >= 2)
                decisions.append({"set": name, "X": X, "kept": len(kept), "kept_minus_dropped": kept.net_pct.mean() - drop.net_pct.mean(), "t": t.statistic,
                                  "half1": d1, "half2": d2, "t_2x": t2.statistic, "HELPS": ok})
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(ROOT, "results", "verify_depth_summary.csv"), index=False)
    for name in sets:
        print("\n==", name)
        print(R[R.set == name].drop(columns="set").round({"min_depth": 2, "k_ge100": 1, "k_maxup_mean": 1, "k_maxup_med": 1, "d_ge100": 1, "d_maxup_mean": 1, "k_win": 1, "k_avg": 1, "k_med": 1, "k_total": 0, "d_avg": 1, "d_total": 0, "base_avg": 1, "base_total": 0}).to_string(index=False))
    D = pd.DataFrame(decisions)
    print("\nDECISION (kept vs dropped, pre-registered):")
    print(D.round(2).to_string(index=False))
    print("thresholds that HELP:", D[D.HELPS][["set", "X"]].values.tolist() or "none", "| tries:", len(D))


if __name__ == "__main__":
    main()
