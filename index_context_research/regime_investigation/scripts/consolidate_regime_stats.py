"""Coordinator: one consistent statistics table per strategy x condition x class, recomputed from the recorded trades and the agents' CLASS LABEL files
(labels are taken as given; every statistic is recomputed here with ONE set of definitions, answering Agent 5's request to harmonise wins and top-5 % share).
Definitions: win = net % > 0; percentage = net rupees after slippage and charges / premium paid; top-5 % share = rupees of the best ceil(5 % n) trades / total net rupees
(blank when the class total is not positive); mean_wo_top3 = mean net % without the 3 best trades of the class; CI = bootstrap 95 % of the mean net %, resampling trading days (2000 draws, seed 20261117).
Outputs: ../results_tables/regime_stats_all.csv and ../results_tables/REGIME_STATS_TABLES.md"""
import math
import os

import numpy as np
import pandas as pd

RI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I = os.path.join(RI, "interim")
OUT = os.path.join(RI, "results_tables")
os.makedirs(OUT, exist_ok=True)

lab = pd.read_csv(os.path.join(I, "agent3_regimes", "regime_labels.csv"))
lab["date"] = pd.to_datetime(lab["date"]).dt.date.astype(str)
g = pd.read_csv(os.path.join(I, "agent3b_gift_regimes", "gift_labels_samecontract.csv"))
g["date"] = pd.to_datetime(g["date"]).dt.date.astype(str)
r = g["gift_ret_samecontract"]
g["gift_sc"] = np.where(r.isna(), None, np.where(r >= 0.3, "gap-up", np.where(r <= -0.3, "gap-down", "flat")))
d = g["gap_minus_gift_samecontract"]
g["ivsa_sc"] = np.where(d.isna(), None, np.where(d >= 0.2, "stronger", np.where(d <= -0.2, "weaker", "in line")))
e = pd.read_csv(os.path.join(I, "agent4_external", "external_features.csv"))
e["date"] = pd.to_datetime(e["date"]).dt.date.astype(str)
STRAT = {"G1-F": ("G1F", "G1-F"), "G1": ("G1", "G1"), "G1-C": ("G1C", "G1-C"), "XP": ("XP", "XP")}
a_files = {"G1-F": "anatomy_dataset.csv", "G1": "anatomy_dataset_G1.csv", "G1-C": "anatomy_dataset_G1C.csv"}


def boot(x, days, n=2000, seed=20261117):
    rng = np.random.default_rng(seed)
    dd = pd.DataFrame({"x": x.to_numpy(), "d": days.to_numpy()})
    grp = dd.groupby("d")["x"].agg(["sum", "count"])
    s, c = grp["sum"].to_numpy(), grp["count"].to_numpy()
    if len(s) < 3:
        return (np.nan, np.nan)
    m = []
    for _ in range(n):
        i = rng.integers(0, len(s), len(s))
        m.append(s[i].sum() / c[i].sum())
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def stats(cond, cls, x):
    n = len(x)
    if n < 10:
        return {"condition": cond, "class": cls, "n": n, "note": "too few (n < 10): no numbers"}
    v = x["net_pct"]
    rs = x["net_rs"]
    top = max(1, math.ceil(0.05 * n))
    srt = x.sort_values("net_pct", ascending=False)
    lo, hi = boot(v, x["date"])
    w = v > 0
    out = {"condition": cond, "class": cls, "n": n, "wins": int(w.sum()), "losses": int((~w).sum()), "win_rate_pct": w.mean() * 100, "mean_net_pct": v.mean(), "ci_lo": lo, "ci_hi": hi,
           "median_net_pct": v.median(), "total_net_rs": rs.sum(), "avg_win_rs": rs[w].mean() if w.any() else np.nan, "avg_loss_rs": rs[~w].mean() if (~w).any() else np.nan,
           "avg_win_pct": v[w].mean() if w.any() else np.nan, "avg_loss_pct": v[~w].mean() if (~w).any() else np.nan,
           "maxup_mean_pct": x["maxup"].mean(), "maxup_ge100_share_pct": (x["maxup"] >= 100).mean() * 100,
           "top5pct_share_of_total_rs": (srt["net_rs"].iloc[:top].sum() / rs.sum() * 100) if rs.sum() > 0 else np.nan,
           "mean_wo_top3_pct": srt["net_pct"].iloc[3:].mean() if n > 3 else np.nan, "note": ""}
    for c in ("mfe_any_pct", "mae_any_pct", "duration_trading_min"):
        if c in x.columns:
            out[c.replace("_any_pct", "").replace("duration_trading_min", "duration_min") + ("_mean" if "duration" not in c else "")] = x[c].mean()
    return out


rows = []
for name, (k, lname) in STRAT.items():
    L = lab[lab["strategy"] == lname].copy()
    if name in a_files:
        a = pd.read_csv(os.path.join(I, "agent2_anatomy", a_files[name]))
        a["date"] = pd.to_datetime(a["day"]).dt.date.astype(str)
        L = L.merge(a[["date", "mfe_any_pct", "mae_any_pct", "duration_trading_min"]], on="date", how="left")
    conds = [("H1 direction (ret20 quintile, 1 bearish .. 5 bullish)", "q20", L), ("H1b direction3", "dir3", L), ("H2 VIX level (previous close)", "vix_level", L), ("H3 VIX 5-day direction", "vix_dir", L),
             ("H4 sudden VIX expansion", "vix_expansion", L), ("H5 actual NIFTY opening gap", "gap_cls", L), ("H6 S&P previous session (agent 3, stale cache)", "us_cls", L)]
    G = g[g["strategy"] == lname].merge(L[["date"] + [c for c in ("mfe_any_pct", "mae_any_pct", "duration_trading_min") if c in L.columns]], on="date", how="left")
    conds += [("H10 GIFT overnight, same-contract (PRIMARY)", "gift_sc", G), ("H11 indicated vs actual opening, same-contract (PRIMARY)", "ivsa_sc", G), ("H12 Asia pre-entry (agent 3b, mean of available markets)", "asia_cls", G)]
    E = e[e["strategy"] == k].copy()
    if name in a_files:
        E = E.merge(L[["date"] + [c for c in ("mfe_any_pct", "mae_any_pct", "duration_trading_min") if c in L.columns]], on="date", how="left")
    for lbl, col in (("X01 S&P 500 previous US session", "us_class"), ("X02 USD/INR previous session (hourly)", "usd_class"), ("X03 Brent previous day (quality-limited)", "brent_class"), ("X04 US VIX spike", "usvix_class"),
                     ("X05 Global risk-on / off", "risk_class"), ("X06 Asia pre-entry (agent 4, needs both markets)", "asia_class"), ("X07 Market breadth, previous session", "breadth_class"),
                     ("X08 Sector leadership (Bank minus Nifty)", "sector_class"), ("X09 FII / DII cash (limited window, third party)", "fiidii_class"), ("X10 FII futures level", "fii_fut_level_class"),
                     ("X11 News tone (GDELT, global)", "tone_class"), ("X12 Scheduled events", "event_class")):
        conds.append((lbl, col, E))
    for cond, col, src in conds:
        if col not in src.columns:
            continue
        for cls, x in src.dropna(subset=[col]).groupby(col):
            x = x.dropna(subset=["net_pct", "net_rs"])
            s = stats(cond, str(cls), x)
            s["strategy"] = name
            rows.append(s)
R = pd.DataFrame(rows)
cols = ["strategy", "condition", "class", "n", "wins", "losses", "win_rate_pct", "mean_net_pct", "ci_lo", "ci_hi", "median_net_pct", "total_net_rs", "avg_win_rs", "avg_loss_rs", "avg_win_pct", "avg_loss_pct",
        "maxup_mean_pct", "maxup_ge100_share_pct", "mfe_mean", "mae_mean", "duration_min", "top5pct_share_of_total_rs", "mean_wo_top3_pct", "note"]
R = R[[c for c in cols if c in R.columns]]
R.to_csv(os.path.join(OUT, "regime_stats_all.csv"), index=False)
md = ["# Regime statistics, every strategy x condition x class (coordinator recomputation; 17 Nov 2026)", "",
      "One set of definitions for all agents' class labels: win = net % > 0; percentage = net rupees after slippage and charges / premium paid; rupees separate; top-5 % share = rupees of the best 5 % of trades / the class's total net rupees (blank if the total is not positive, can exceed 100 %); `without top 3` = mean net % without the class's 3 best trades; interval = bootstrap 95 % of the mean resampling trading days; MFE = highest option value after entry through the next close (% above price paid, minute closes); MAE = lowest minute close between entry and exit (% below price paid); duration in trading minutes. Classes under 10 trades carry no numbers. Percent and rupees are never mixed. Labels come from `interim/agent3_regimes`, `agent3b_gift_regimes` (same-contract) and `agent4_external`; definitions in `PREREG_REGIME.md`.", ""]
for name in STRAT:
    md.append(f"## {name}")
    sub = R[R["strategy"] == name]
    for cond, grp in sub.groupby("condition", sort=False):
        md.append(f"**{cond}**")
        for _, s in grp.iterrows():
            if s.get("note"):
                md.append(f"- {s['class']}: n {int(s['n'])} {s['note']}")
                continue
            md.append(f"- {s['class']}: n {int(s['n'])} ({int(s['wins'])} W / {int(s['losses'])} L, win {s['win_rate_pct']:.0f} %), mean {s['mean_net_pct']:+.1f} % [{s['ci_lo']:+.0f}, {s['ci_hi']:+.0f}], median {s['median_net_pct']:+.1f} %, "
                      f"total Rs {s['total_net_rs']:,.0f}, avg win Rs {s['avg_win_rs']:,.0f} ({s['avg_win_pct']:+.0f} %), avg loss Rs {s['avg_loss_rs']:,.0f} ({s['avg_loss_pct']:+.0f} %), max up mean {s['maxup_mean_pct']:.0f} % "
                      f"(>= +100 % on {s['maxup_ge100_share_pct']:.0f} %)" + (f", MFE {s['mfe_mean']:.0f} %, MAE {s['mae_mean']:.0f} %" if 'mfe_mean' in s and pd.notna(s.get('mfe_mean')) else "") +
                      (f", top-5 % share {s['top5pct_share_of_total_rs']:.0f} %" if pd.notna(s['top5pct_share_of_total_rs']) else "") + f", without top 3 {s['mean_wo_top3_pct']:+.1f} %")
        md.append("")
open(os.path.join(OUT, "REGIME_STATS_TABLES.md"), "w", encoding="utf-8").write("\n".join(md))
print(len(R), "rows; strategies:", R["strategy"].value_counts().to_dict())
