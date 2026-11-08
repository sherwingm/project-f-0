"""Drift-free FII/DII (g1_research/EXTERNAL2_PREREG.md)."""
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import g1_external as E  # noqa: E402
import g1_formation as GF  # noqa: E402

BASE = ["fii_fut_net", "fii_fut_ratio", "fii_opt_bear", "dii_fut_net", "client_fut_net", "pro_fut_net"]


def main():
    P = E.participant_frame()
    X = pd.DataFrame(index=P.index)
    for c in BASE:
        s = P[c]
        prev = s.shift(1)
        X[f"{c}_z60"] = (s - prev.rolling(60).mean()) / prev.rolling(60).std()
        X[f"{c}_p250"] = [np.nan if i < 250 else (s.iloc[i - 250:i] < s.iloc[i]).mean() for i in range(len(s))]
    for c in ("fii_fut_net", "fii_opt_bear", "dii_fut_net", "client_fut_net"):
        d = P[c].diff()
        X[f"{c}_chgz"] = d / d.shift(1).rolling(60).std()
    T = pd.read_csv(os.path.join(ROOT, "results", "g1_underlying_signals.csv"), parse_dates=["day"])[["day", "F", "reach"]]
    rows = []
    for d in T["day"]:
        prior = X.index[X.index < d]
        rows.append(X.loc[prior[-1]].to_dict() if len(prior) else {})
    T = pd.concat([T, pd.DataFrame(rows)], axis=1)
    feats = list(X.columns)
    T.to_csv(os.path.join(ROOT, "results", "g1_external2_features.csv"), index=False)
    D, V, C = T[T["day"] <= E.D_END], T[(T["day"] > E.D_END) & (T["day"] <= E.V_END)], T[T["day"] > E.V_END]
    print("non-missing:", int(T[feats].notna().all(axis=1).sum()), "of", len(T), "| periods", len(D), len(V), len(C))
    out = []
    for f in feats:
        x = D[f].dropna()
        if len(x) < 60:
            continue
        p33, p67 = np.percentile(x, [33.3, 66.7])
        for name, cond in ((f"high >= {p67:.3g}", lambda s_, t_=p67: s_ >= t_), (f"low <= {p33:.3g}", lambda s_, t_=p33: s_ <= t_)):
            def grp(df):
                df = df[df[f].notna()]
                g_ = df[cond(df[f])]
                return g_, df.drop(g_.index)
            g, o = grp(D)
            if len(g) < 5 or len(o) < 5:
                continue
            p = stats.fisher_exact([[g.reach.sum(), len(g) - g.reach.sum()], [o.reach.sum(), len(o) - o.reach.sum()]])[1]
            row = {"feature": f, "rule": name, "d_n": len(g), "d_reach": g.reach.mean() * 100, "d_out": o.reach.mean() * 100, "d_p": p}
            for tag, df in (("v", V), ("c", C)):
                gg, oo = grp(df)
                row[f"{tag}_n"] = len(gg)
                row[f"{tag}_reach"] = gg.reach.mean() * 100 if len(gg) else np.nan
                row[f"{tag}_out"] = oo.reach.mean() * 100 if len(oo) else np.nan
                row[f"{tag}_tab"] = [[gg.reach.sum(), len(gg) - gg.reach.sum()], [oo.reach.sum(), len(oo) - oo.reach.sum()]]
            out.append(row)
    R = pd.DataFrame(out)
    R["d_q"] = GF.bh(R["d_p"].values)
    R["d_eff"] = R["d_reach"] - R["d_out"]
    R["cand"] = (R["d_q"] <= 0.10) & (R["d_n"] >= 25)
    pd.set_option("display.width", 250)
    print("rules in family:", len(R), "| candidates:", int(R["cand"].sum()))
    print(R.sort_values("d_p").head(10)[["feature", "rule", "d_n", "d_reach", "d_out", "d_p", "d_q"]].round(3).to_string(index=False))
    R.drop(columns=["v_tab", "c_tab"]).to_csv(os.path.join(ROOT, "results", "g1_external2_all_rules.csv"), index=False)
    Cn = R[R["cand"]].copy()
    cols = ["feature", "rule", "d_n", "d_reach", "d_out", "v_n", "v_reach", "v_out", "c_n", "c_reach", "c_out"]
    if not len(Cn):
        print("\nno candidate at q <= 0.10\nFOR INFORMATION ONLY (not a test): the 6 smallest discovery p")
        print(R.sort_values("d_p").head(6)[cols].round(1).to_string(index=False))
        return
    sg = np.sign(Cn["d_eff"])
    for tag in ("v", "c"):
        Cn[f"{tag}_eff"] = Cn[f"{tag}_reach"] - Cn[f"{tag}_out"]
        Cn[f"{tag}_p1"] = [stats.fisher_exact(tb, alternative="greater" if e > 0 else "less")[1] for tb, e in zip(Cn[f"{tag}_tab"], Cn["d_eff"])]
    Cn["pass_v"] = (Cn["v_n"] >= 20) & (np.sign(Cn["v_eff"]) == sg) & (Cn["v_p1"] < 0.05) & (Cn["v_eff"].abs() >= 0.5 * Cn["d_eff"].abs())
    Cn["pass_c"] = Cn["pass_v"] & (Cn["c_n"] >= 20) & (np.sign(Cn["c_eff"]) == sg) & (Cn["c_p1"] < 0.05)
    print(Cn[cols + ["d_q", "v_p1", "pass_v", "c_p1", "pass_c"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
