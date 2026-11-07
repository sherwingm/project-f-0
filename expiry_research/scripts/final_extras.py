"""Observed-only robustness of the final-period results (reports/lld/final.md, section "Observed extras").

Reads only results/final/flags_<UL>.csv and final_results.csv (written by final_test.py); never the sealed panels.
Per candidate: distinct months with a flag, effect by half-year, effect inside final-period VIX terciles, and a
circular-shift permutation p (flag series shifted against the outcomes by >= 20 sessions, 2000 draws) that keeps
the clustering of flags. None of this changes a label.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "final"
SEED = 20261105


def main():
    R = pd.read_csv(OUT / "final_results.csv")
    rng = np.random.default_rng(SEED)
    rows, grp = [], []
    for _, r in R.iterrows():
        F = pd.read_csv(OUT / f"flags_{r['ul']}.csv")
        i = r["id"]
        T = F[F[f"{i}_target"].notna()].sort_values("date").reset_index(drop=True)
        y = T[f"{i}_target"].to_numpy(float)
        f = T[f"{i}_flag"].to_numpy(float) > 0.5
        d = np.sign(r["disc_effect"])
        eff = y[f].mean() - y.mean()
        n = len(y)
        draws = np.array([y[np.roll(f, s)].mean() - y.mean() for s in rng.integers(20, n - 20, 2000)])
        p_shift = float(((draws * d >= eff * d).sum() + 1) / (len(draws) + 1))
        months = T.loc[f, "y_date"].str[:7]
        top3 = months.value_counts().head(3).sum() / max(1, f.sum())
        rows.append(dict(id=i, ul=r["ul"], n_rows=n, n_flag=int(f.sum()), effect=eff, p_circular_shift=p_shift,
                         flag_months=months.nunique(), share_flags_top3_months=top3))
        T["half"] = T["y_date"].str[:4] + np.where(T["y_date"].str[5:7] <= "06", "H1", "H2")
        T["vix_t"] = pd.qcut(T["f_vix_close"], 3, labels=["low", "mid", "high"])
        for by in ["half", "vix_t"]:
            for g, G in T.groupby(by, observed=True):
                gf = G[f"{i}_flag"] > 0.5
                yy = G[f"{i}_target"]
                grp.append(dict(id=i, by=by, group=str(g), n=len(G), n_flag=int(gf.sum()),
                                rate=yy[gf].mean() if gf.any() else np.nan, base=yy.mean(),
                                effect=(yy[gf].mean() - yy.mean()) if gf.any() else np.nan))
    X = pd.DataFrame(rows)
    G = pd.DataFrame(grp)
    G["same_sign"] = [np.sign(e) == np.sign(R.set_index("id").loc[i, "disc_effect"]) if pd.notna(e) else np.nan
                      for i, e in zip(G["id"], G["effect"])]
    H = G[G["n_flag"] >= 5].copy()
    H["ss"] = H["same_sign"].astype(float)
    summ = H.groupby(["id", "by"])["ss"].agg(lambda s: f"{int(s.sum())}/{len(s)}")
    X["halves_same_sign"] = X["id"].map(summ.xs("half", level="by"))
    X["vix_terciles_same_sign"] = X["id"].map(summ.xs("vix_t", level="by"))
    X.to_csv(OUT / "extras_summary.csv", index=False)
    G.to_csv(OUT / "extras_groups.csv", index=False)
    pd.set_option("display.width", 200)
    print(X.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
