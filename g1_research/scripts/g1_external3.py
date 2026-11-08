"""FII/DII positions vs NIFTY next-day direction and size, all sessions (g1_research/EXTERNAL3_PREREG.md)."""
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from scanner import s3_regime as G  # noqa: E402
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
    daily = G.daily()
    daily.index = pd.to_datetime(daily.index)
    ret = daily["close"].shift(-1) / daily["close"] - 1                 # close(t) -> close(t+1)
    T = X.join(ret.rename("ret"), how="inner").dropna(subset=["ret"])
    T = T[(T.index >= "2021-11-01") & (T.index <= "2026-10-28")].copy()
    T["up"] = (T["ret"] > 0).astype(int)
    T["absret"] = T["ret"].abs() * 100
    D_END, V_END = pd.Timestamp("2023-09-30"), pd.Timestamp("2024-09-30")
    T = T.reset_index().rename(columns={"index": "day"})
    big_cut = np.percentile(T.loc[T["day"] <= D_END, "absret"], 66.7)
    T["big"] = (T["absret"] >= big_cut).astype(int)
    D, V, C = T[T["day"] <= D_END], T[(T["day"] > D_END) & (T["day"] <= V_END)], T[T["day"] > V_END]
    print(f"sessions {len(T)} | discovery {len(D)} validation {len(V)} confirmation {len(C)} | big move cut {big_cut:.2f} %")
    print(f"base rates: up {D.up.mean()*100:.0f}/{V.up.mean()*100:.0f}/{C.up.mean()*100:.0f} %, big {D.big.mean()*100:.0f}/{V.big.mean()*100:.0f}/{C.big.mean()*100:.0f} % (disc/valid/confirm)")
    feats = list(X.columns)
    out = []
    for outc in ("up", "big"):
        for f in feats:
            x = D[f].dropna()
            if len(x) < 100:
                continue
            p33, p67 = np.percentile(x, [33.3, 66.7])
            for name, cond in ((f"high >= {p67:.3g}", lambda s_, t_=p67: s_ >= t_), (f"low <= {p33:.3g}", lambda s_, t_=p33: s_ <= t_)):
                def grp(df):
                    df = df[df[f].notna()]
                    g_ = df[cond(df[f])]
                    return g_, df.drop(g_.index)
                g, o = grp(D)
                if len(g) < 10 or len(o) < 10:
                    continue
                p = stats.fisher_exact([[g[outc].sum(), len(g) - g[outc].sum()], [o[outc].sum(), len(o) - o[outc].sum()]])[1]
                row = {"outcome": outc, "feature": f, "rule": name, "d_n": len(g), "d_rate": g[outc].mean() * 100, "d_out": o[outc].mean() * 100, "d_p": p}
                for tag, df in (("v", V), ("c", C)):
                    gg, oo = grp(df)
                    row[f"{tag}_n"] = len(gg)
                    row[f"{tag}_rate"] = gg[outc].mean() * 100 if len(gg) else np.nan
                    row[f"{tag}_out"] = oo[outc].mean() * 100 if len(oo) else np.nan
                    row[f"{tag}_tab"] = [[gg[outc].sum(), len(gg) - gg[outc].sum()], [oo[outc].sum(), len(oo) - oo[outc].sum()]]
                out.append(row)
    R = pd.DataFrame(out)
    R["d_q"] = GF.bh(R["d_p"].values)
    R["d_eff"] = R["d_rate"] - R["d_out"]
    R["cand"] = (R["d_q"] <= 0.10) & (R["d_n"] >= 40)
    pd.set_option("display.width", 250)
    print("rules in family:", len(R), "| candidates:", int(R["cand"].sum()))
    print(R.sort_values("d_p").head(10)[["outcome", "feature", "rule", "d_n", "d_rate", "d_out", "d_p", "d_q"]].round(3).to_string(index=False))
    R.drop(columns=["v_tab", "c_tab"]).to_csv(os.path.join(ROOT, "results", "g1_external3_all_rules.csv"), index=False)
    cols = ["outcome", "feature", "rule", "d_n", "d_rate", "d_out", "v_n", "v_rate", "v_out", "c_n", "c_rate", "c_out"]
    Cn = R[R["cand"]].copy()
    if not len(Cn):
        print("\nno candidate at q <= 0.10\nFOR INFORMATION ONLY (not a test): the 6 smallest discovery p")
        print(R.sort_values("d_p").head(6)[cols].round(1).to_string(index=False))
        return
    sg = np.sign(Cn["d_eff"])
    for tag in ("v", "c"):
        Cn[f"{tag}_eff"] = Cn[f"{tag}_rate"] - Cn[f"{tag}_out"]
        Cn[f"{tag}_p1"] = [stats.fisher_exact(tb, alternative="greater" if e > 0 else "less")[1] for tb, e in zip(Cn[f"{tag}_tab"], Cn["d_eff"])]
    Cn["pass_v"] = (Cn["v_n"] >= 30) & (np.sign(Cn["v_eff"]) == sg) & (Cn["v_p1"] < 0.05) & (Cn["v_eff"].abs() >= 0.5 * Cn["d_eff"].abs())
    Cn["pass_c"] = Cn["pass_v"] & (Cn["c_n"] >= 30) & (np.sign(Cn["c_eff"]) == sg) & (Cn["c_p1"] < 0.05)
    print(Cn[cols + ["d_q", "v_p1", "pass_v", "c_p1", "pass_c"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
