"""Breakout score 0-7 for G1 signals + history check (g1_research/SCORE_PREREG.md). Record only. History, in-sample caveats."""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
SPLIT = pd.Timestamp("2025-10-01")
# item: (column, direction, label)   direction: ">=" or "<=" median ; vix fixed < 17
ITEMS = [("Breakout depth at signal %", ">=", "depth"), ("Minutes after 09:30", "<=", "time"), ("OR width %", "<=", "width"),
         ("Day-1 gap at open %", "<=", "gap"), ("VIX at signal", "<17", "vix"), ("Prev 5-day return %", "<=", "prev5"),
         ("Prev close vs EMA20 %", "<=", "ema20")]


def thresholds(disc):
    return {lab: (float(disc[c].median()) if d != "<17" else 17.0) for c, d, lab in ITEMS}


def points(row_or_df, th):
    out = {}
    for c, d, lab in ITEMS:
        x = row_or_df[c]
        out[lab] = ((x >= th[lab]) if d == ">=" else (x < th[lab]) if d == "<17" else (x <= th[lab])).astype(int)
    return pd.DataFrame(out)


def shares(s):
    return {"n": len(s), "ge50": (s >= 50).mean() * 100, "ge100": (s >= 100).mean() * 100, "ge200": (s >= 200).mean() * 100,
            "mean": s.mean(), "median": s.median()}


def table(T, by, label):
    rows = []
    for k, g in T.groupby(by, observed=True):
        r = shares(g["peak_k1"])
        r.update({label: k, "win": (g["k1_net"] > 0).mean() * 100, "booked_mean": g["k1_net"].mean(), "booked_median": g["k1_net"].median(),
                  "stopped": (g["k1_reason"] == "stop").mean() * 100})
        rows.append(r)
    return pd.DataFrame(rows).set_index(label).round(1)


def main():
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    h = pd.read_csv(os.path.join(ROOT, "data", "g1_hold_days_trades.csv"))
    d["day"], h["day"] = pd.to_datetime(d["Day"]), pd.to_datetime(h["day"])
    T = d.merge(h[["day", "peak_k1", "k1_net", "k1_reason", "g1f"]], on="day").sort_values("day").reset_index(drop=True)
    disc = T[T["day"] < SPLIT]
    th = thresholds(disc)
    path = os.path.join(ROOT, "results", "score_thresholds.csv")
    if not os.path.exists(path):
        pd.Series(th, name="threshold").to_csv(path, header=True)
    P = points(T, th)
    T["score"] = P.sum(axis=1)
    T["score_pct"] = T["score"] / 7 * 100
    T["run_avg_pct"] = T["score_pct"].expanding().mean()
    # expanding percentile (only earlier signals) and full-history percentile
    s = T["score"].values
    T["pctile_exp"] = [np.nan if i == 0 else ((s[:i] < s[i]).sum() + 0.5 * (s[:i] == s[i]).sum()) / i * 100 for i in range(len(s))]
    T["pctile_full"] = [((s < v).sum() + 0.5 * (s == v).sum() - 0.5) / len(s) * 100 for v in s]
    T["band"] = pd.cut(T["score"], [-1, 2, 4, 7], labels=["low 0-2", "mid 3-4", "high 5-7"])
    T["period"] = np.where(T["day"] < SPLIT, "discovery", "validation")
    pd.set_option("display.width", 250)
    print("thresholds", {k: round(v, 3) for k, v in th.items()})
    print("\nscore counts\n", T.groupby("period")["score"].value_counts().unstack(fill_value=0).to_string())
    out = {}
    print("\n=== 1. DOES IT WORK (max up through next close, no stop) ===")
    for per in ["discovery", "validation"]:
        g = T[T["period"] == per]
        rho, p = stats.spearmanr(g["score"], g["peak_k1"])
        print(f"\n{per}: n={len(g)} Spearman score vs max up rho={rho:.3f} p={p:.3f}")
        print(table(g, "band", "band").to_string())
        print("by points:\n", table(g, "score", "score").to_string())
        hi, lo = g[g["band"] == "high 5-7"], g[g["band"] == "low 0-2"]
        tab = [[(hi["peak_k1"] >= 100).sum(), (hi["peak_k1"] < 100).sum()], [(lo["peak_k1"] >= 100).sum(), (lo["peak_k1"] < 100).sum()]]
        pf = stats.fisher_exact(tab, alternative="greater")[1] if len(hi) and len(lo) else np.nan
        eff = (hi["peak_k1"] >= 100).mean() * 100 - (lo["peak_k1"] >= 100).mean() * 100
        print(f"high vs low >=+100%: {(hi['peak_k1']>=100).mean()*100:.0f}% vs {(lo['peak_k1']>=100).mean()*100:.0f}% effect {eff:.1f} pts one-sided Fisher p={pf:.3f}")
        out[per] = (rho, p, eff, pf)
    print("\n=== 2. WHAT MIGHT BE HIDING ===")
    print("\na. each item alone: points=1 vs 0, max up >=+100% and median (all, then validation only)")
    rows = []
    for lab in P.columns:
        for nm, mask in (("all", np.ones(len(T), bool)), ("valid", (T["period"] == "validation").values)):
            one, zero = T[mask & (P[lab] == 1).values], T[mask & (P[lab] == 0).values]
            rows.append({"item": lab, "set": nm, "n1": len(one), "ge100_1": (one["peak_k1"] >= 100).mean() * 100, "ge100_0": (zero["peak_k1"] >= 100).mean() * 100,
                         "med_1": one["peak_k1"].median(), "med_0": zero["peak_k1"].median(),
                         "p": stats.mannwhitneyu(one["peak_k1"], zero["peak_k1"])[1] if len(one) > 3 and len(zero) > 3 else np.nan})
    print(pd.DataFrame(rows).round(2).to_string(index=False))
    print("\n   drop-one Spearman (validation) / (all):")
    for lab in P.columns:
        sc = P.drop(columns=lab).sum(axis=1)
        v = (T["period"] == "validation").values
        print(f"   without {lab:6s}: valid rho={stats.spearmanr(sc[v], T['peak_k1'][v])[0]:.3f}  all rho={stats.spearmanr(sc, T['peak_k1'])[0]:.3f}")
    print("\nb. item overlap (correlation of the 0/1 points):\n", P.corr().round(2).to_string())
    print("\nc. by year / G1-F only")
    T["year"] = T["day"].dt.year
    for yr, g in T.groupby("year"):
        print(f"   {yr}: n={len(g)} rho={stats.spearmanr(g['score'], g['peak_k1'])[0]:.3f}")
    f = T[T["g1f"] == 1]
    print(f"   G1-F only: n={len(f)} rho={stats.spearmanr(f['score'], f['peak_k1'])[0]:.3f} (valid n={(f['period']=='validation').sum()}, rho={stats.spearmanr(f[f['period']=='validation']['score'], f[f['period']=='validation']['peak_k1'])[0]:.3f})")
    print(table(f, "band", "band").to_string())
    print("\nd. without the 10 biggest max-up trades")
    t10 = T.drop(T["peak_k1"].nlargest(10).index)
    print(f"   all rho={stats.spearmanr(t10['score'], t10['peak_k1'])[0]:.3f}  validation rho={stats.spearmanr(t10[t10['period']=='validation']['score'], t10[t10['period']=='validation']['peak_k1'])[0]:.3f}")
    print(table(t10, "band", "band").to_string())
    print("\nf. expanding vs full percentile: Spearman between them", round(stats.spearmanr(T["pctile_exp"].iloc[1:], T["pctile_full"].iloc[1:])[0], 3))
    T["band_exp"] = pd.cut(T["pctile_exp"], [-1, 33.3, 66.7, 101], labels=["bottom third", "mid third", "top third"])
    print("   by expanding percentile thirds, ALL:\n", table(T[T["pctile_exp"].notna()], "band_exp", "band").to_string())
    T.drop(columns=["band_exp"]).to_csv(os.path.join(ROOT, "results", "g1_score_history.csv"), index=False)
    rho_v, p_v, eff_v, pf_v = out["validation"]
    rho_d, p_d, eff_d, pf_d = out["discovery"]
    passed = (rho_v > 0) and (pf_v < 0.05) and (eff_v >= 0.5 * eff_d) and eff_d > 0
    print(f"\nVERDICT: discovery rho {rho_d:.3f} effect {eff_d:.1f} | validation rho {rho_v:.3f} effect {eff_v:.1f} p {pf_v:.3f} -> {'Passed validation' if passed else 'Rejected as a predictor (stays a record)'}")


if __name__ == "__main__":
    main()
