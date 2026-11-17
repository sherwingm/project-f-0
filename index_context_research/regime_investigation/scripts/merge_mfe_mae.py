"""Coordinator merge: adds MFE / MAE / duration (Agent 2 anatomy) to Agent 3 / 3b regime labels, per class, for the main G1-F, G1 and G1-C hypotheses.
Output: ../results_tables/regime_mfe_mae.csv. Read-only on the agents' files."""
import os

import numpy as np
import pandas as pd

RI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I = os.path.join(RI, "interim")
OUT = os.path.join(RI, "results_tables")
os.makedirs(OUT, exist_ok=True)

lab = pd.read_csv(os.path.join(I, "agent3_regimes", "regime_labels.csv"))
lab["date"] = pd.to_datetime(lab["date"]).dt.date.astype(str)
gift = pd.read_csv(os.path.join(I, "agent3b_gift_regimes", "gift_labels_samecontract.csv"))
gift["date"] = pd.to_datetime(gift["date"]).dt.date.astype(str)
rows = []
for name, an in (("G1F", "anatomy_dataset.csv"), ("G1", "anatomy_dataset_G1.csv"), ("G1C", "anatomy_dataset_G1C.csv")):
    a = pd.read_csv(os.path.join(I, "agent2_anatomy", an))
    a["day"] = pd.to_datetime(a["day"]).dt.date.astype(str)
    keep = ["day", "mfe_any_pct", "mfe_held_pct", "mae_any_pct", "mae_before_peak_pct", "duration_trading_min"]
    a = a[[c for c in keep if c in a.columns]]
    strat = {"G1F": "G1-F", "G1": "G1", "G1C": "G1-C"}[name]
    L = lab[lab["strategy"] == strat]
    G = gift[gift["strategy"] == strat]
    M = L.merge(a, left_on="date", right_on="day", how="left")
    for hyp, col, src in (("H1 direction (ret20 quintile)", "q20", M), ("H1b direction3", "dir3", M), ("H2 VIX level", "vix_level", M), ("H3 VIX direction", "vix_dir", M),
                          ("H5 actual opening gap", "gap_cls", M), ("H6 S&P previous session", "us_cls", M)):
        for k, g in src.groupby(col, dropna=True):
            rows.append({"strategy": name, "hypothesis": hyp, "class": k, "n": len(g), "mean_net_pct": g["net_pct"].mean(), "mean_mfe_any_pct": g["mfe_any_pct"].mean(), "median_mfe_any_pct": g["mfe_any_pct"].median(),
                         "mean_mae_any_pct": g["mae_any_pct"].mean(), "median_mae_any_pct": g["mae_any_pct"].median(), "mean_duration_min": g["duration_trading_min"].mean()})
    MG = G.merge(a, left_on="date", right_on="day", how="left")
    r = MG["gift_ret_samecontract"]
    MG["gift_cls_samecontract"] = np.where(r.isna(), None, np.where(r >= 0.3, "gap-up", np.where(r <= -0.3, "gap-down", "flat")))
    d = MG["gap_minus_gift_samecontract"]
    MG["ivsa_cls_samecontract"] = np.where(d.isna(), None, np.where(d >= 0.2, "stronger", np.where(d <= -0.2, "weaker", "in line")))
    for hyp, col in (("H10 GIFT overnight (same-contract)", "gift_cls_samecontract"), ("H11 indicated vs actual (same-contract)", "ivsa_cls_samecontract"), ("H12 Asia", "asia_cls")):
        if col not in MG.columns:
            continue
        for k, g in MG.groupby(col, dropna=True):
            rows.append({"strategy": name, "hypothesis": hyp, "class": k, "n": len(g), "mean_net_pct": g["net_pct"].mean(), "mean_mfe_any_pct": g["mfe_any_pct"].mean(), "median_mfe_any_pct": g["mfe_any_pct"].median(),
                         "mean_mae_any_pct": g["mae_any_pct"].mean(), "median_mae_any_pct": g["mae_any_pct"].median(), "mean_duration_min": g["duration_trading_min"].mean()})
R = pd.DataFrame(rows)
R.to_csv(os.path.join(OUT, "regime_mfe_mae.csv"), index=False)
print(len(R), "rows;", R["strategy"].value_counts().to_dict())
pd.set_option("display.width", 220)
print(R[R["strategy"] == "G1F"].round(1).to_string(index=False))
