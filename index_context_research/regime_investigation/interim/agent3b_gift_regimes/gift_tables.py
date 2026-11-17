"""Agent 3b: tables/tests for H10 (GIFT overnight), H11 (indicated vs actual), H12 (Asia) and pre-registered overnight combinations.
Methods for cell(), boot_ci(), kw(), welch() copied unchanged from agent3_regimes/regime_tables.py. Needs gift_labels.py output."""
import itertools, math, os
import numpy as np, pandas as pd
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__))
L = pd.read_csv(os.path.join(HERE, "gift_labels.csv"), parse_dates=["date"])
STRATS = ["G1-F", "G1", "G1-C", "XP"]
MIN_N, NB, SEED = 10, 5000, 20261117
ORD = {"gift_cls": ["gap-down", "flat", "gap-up"], "ivsa_cls": ["weaker", "in line", "stronger"], "asia_cls": ["down", "flat", "up"],
       "gift_cls_rob": ["gap-down", "flat", "gap-up"], "ivsa_cls_rob": ["weaker", "in line", "stronger"],
       "dir3": ["bearish", "sideways", "bullish"], "vix_level": ["low", "normal", "high"]}
HYP = {"H10": ["gift_cls"], "H11": ["ivsa_cls"], "H12": ["asia_cls"],
       "C1_dir3xGIFT": ["dir3", "gift_cls"], "C2_VIXxGIFT": ["vix_level", "gift_cls"]}
ROB = {"R1_gift_prevrow": ["gift_cls_rob"], "R2_ivsa_prevrow": ["ivsa_cls_rob"]}
# named Welch contrasts: (column, A, B); B == "REST" means all other classified trades
NAMED = {"H10": [("gift_cls", "gap-down", "gap-up"), ("gift_cls", "flat", "REST")],
         "H11": [("ivsa_cls", "in line", "REST"), ("ivsa_cls", "weaker", "stronger")],
         "H12": [("asia_cls", "down", "up")],
         "R1_gift_prevrow": [("gift_cls_rob", "gap-down", "gap-up")], "R2_ivsa_prevrow": [("ivsa_cls_rob", "in line", "REST")]}
ONECOL = {"H10": "gift_cls", "H11": "ivsa_cls", "H12": "asia_cls"}


def boot_ci(df):
    if len(df) < 2:
        return (np.nan, np.nan)
    g = df.groupby("date")["net_pct"].agg(["sum", "count"])
    s, c = g["sum"].values, g["count"].values
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(g), (NB, len(g)))
    m = s[idx].sum(1) / c[idx].sum(1)
    return tuple(np.percentile(m, [2.5, 97.5]))


def cell(df):
    n = len(df)
    o = {"n": n}
    if n == 0:
        return o
    w = df[df.net_rs > 0]
    l = df[df.net_rs <= 0]
    o.update(wins=len(w), losses=len(l), win_rate=len(w) / n * 100, mean_net_pct=df.net_pct.mean(), median_net_pct=df.net_pct.median(),
             total_net_rs=df.net_rs.sum(), avg_profit_rs=w.net_rs.mean() if len(w) else np.nan, avg_loss_rs=l.net_rs.mean() if len(l) else np.nan,
             maxup_mean=df.maxup.mean(), maxup_median=df.maxup.median(), maxup_ge50=(df.maxup >= 50).mean() * 100,
             maxup_ge100=(df.maxup >= 100).mean() * 100, maxup_ge200=(df.maxup >= 200).mean() * 100)
    k = math.ceil(0.05 * n)
    tot = df.net_rs.sum()
    o["top5pct_share_of_total_rs"] = df.net_rs.nlargest(k).sum() / tot * 100 if tot > 0 else np.nan
    o["boot_lo"], o["boot_hi"] = boot_ci(df)
    return o


def kw(parts):
    ok = [p.net_pct.values for p in parts if len(p) >= MIN_N]
    if len(ok) < 2:
        return np.nan
    try:
        return stats.kruskal(*ok).pvalue
    except ValueError:
        return np.nan


def welch(a, b):
    if len(a) < MIN_N or len(b) < MIN_N:
        return (np.nan, np.nan)
    t = stats.ttest_ind(a.net_pct, b.net_pct, equal_var=False)
    return (a.net_pct.mean() - b.net_pct.mean(), t.pvalue)


def cells_of(S, dims):
    if len(dims) == 1:
        for v in ORD[dims[0]]:
            yield (str(v),), S[S[dims[0]].astype(str) == str(v)]
    else:
        for a, b in itertools.product(ORD[dims[0]], ORD[dims[1]]):
            yield (str(a), str(b)), S[(S[dims[0]].astype(str) == str(a)) & (S[dims[1]].astype(str) == str(b))]


def run(S, tag, st):
    out, tests = [], []
    for hname, dims in {**HYP, **ROB}.items():
        parts = []
        for key, sub in cells_of(S, dims):
            r = {"strategy": st, "hypothesis": hname, "dims": "x".join(dims), "regime": " | ".join(key), "section": tag, **cell(sub)}
            r["small"] = "too few" if r["n"] < MIN_N else ""
            out.append(r)
            parts.append(sub)
        tests.append({"strategy": st, "section": tag, "hypothesis": hname, "test": "Kruskal-Wallis", "contrast": "all classes with n>=10",
                      "diff_pp": np.nan, "p_raw": kw(parts), "n_cells_ge10": sum(len(p) >= MIN_N for p in parts)})
        for col, a, b in NAMED.get(hname, []):
            A = S[S[col].astype(str) == a]
            B = S[(S[col].astype(str) != a) & S[col].notna()] if b == "REST" else S[S[col].astype(str) == b]
            d, p = welch(A, B)
            tests.append({"strategy": st, "section": tag, "hypothesis": hname, "test": "Welch",
                          "contrast": f"{a} minus {'the rest' if b == 'REST' else b} (nA={len(A)}, nB={len(B)})",
                          "diff_pp": d, "p_raw": p, "n_cells_ge10": np.nan})
    return out, tests


rows, tests = [], []
for st in STRATS:
    S = L[L.strategy == st]
    for tag, sub in (("explanatory_all", S), ("discovery_to_2025-09-30", S[S.period == "discovery"]), ("second_half", S[S.period == "second_half"])):
        o, t = run(sub, tag, st)
        rows += o
        tests += t
R = pd.DataFrame(rows)
T = pd.DataFrame(tests)
cols = ["strategy", "section", "hypothesis", "dims", "regime", "n", "small", "wins", "losses", "win_rate", "mean_net_pct", "boot_lo", "boot_hi",
        "median_net_pct", "total_net_rs", "avg_profit_rs", "avg_loss_rs", "maxup_mean", "maxup_median", "maxup_ge50", "maxup_ge100", "maxup_ge200",
        "top5pct_share_of_total_rs"]
R[cols].to_csv(os.path.join(HERE, "gift_tables.csv"), index=False)
T.to_csv(os.path.join(HERE, "gift_tests.csv"), index=False)

# triple direction3 x VIX level x GIFT class: tested only if every cell >= 10
tr = []
for st in STRATS:
    S = L[L.strategy == st]
    ns = {f"{a}|{b}|{c}": len(S[(S.dir3 == a) & (S.vix_level == b) & (S.gift_cls == c)])
          for a, b, c in itertools.product(ORD["dir3"], ORD["vix_level"], ORD["gift_cls"])}
    tr.append({"strategy": st, "cells": len(ns), "smallest_cell": min(ns.values()), "cells_ge10": sum(v >= 10 for v in ns.values()),
               "status": "tested" if min(ns.values()) >= 10 else "insufficient", "cell_counts": "; ".join(f"{k}={v}" for k, v in ns.items() if v)})
pd.DataFrame(tr).to_csv(os.path.join(HERE, "gift_triple_status.csv"), index=False)

# predictive consistency: class vs rest, discovery vs second half
cons = []
for st in STRATS:
    S = L[L.strategy == st]
    for h, col in ONECOL.items():
        for v in ORD[col]:
            row = {"strategy": st, "hypothesis": h, "class": v}
            for per, P in (("disc", S[S.period == "discovery"]), ("second", S[S.period == "second_half"])):
                P = P[P[col].notna()]
                a = P[P[col] == v]
                b = P[P[col] != v]
                row[f"n_{per}"] = len(a)
                row[f"mean_{per}"] = a.net_pct.mean() if len(a) >= MIN_N else np.nan
                row[f"diff_vs_rest_{per}"] = a.net_pct.mean() - b.net_pct.mean() if len(a) >= MIN_N and len(b) >= MIN_N else np.nan
            d1, d2 = row["diff_vs_rest_disc"], row["diff_vs_rest_second"]
            row["same_sign"] = bool(np.sign(d1) == np.sign(d2)) if d1 == d1 and d2 == d2 else "not testable"
            cons.append(row)
pd.DataFrame(cons).to_csv(os.path.join(HERE, "gift_consistency.csv"), index=False)

hy = []
for st in STRATS:
    S = L[L.strategy == st]
    for hp, P in S.groupby("halfyear"):
        for col, key in (("gift_cls", "gap-down"), ("gift_cls", "gap-up"), ("gift_cls", "flat"), ("ivsa_cls", "weaker"),
                         ("ivsa_cls", "stronger"), ("ivsa_cls", "in line"), ("asia_cls", "down"), ("asia_cls", "up")):
            a = P[P[col] == key]
            hy.append({"strategy": st, "halfyear": hp, "class": f"{col}={key}", "n": len(a), "n_all": len(P),
                       "mean_net_pct": a.net_pct.mean() if len(a) >= MIN_N else np.nan, "all_mean_net_pct": P.net_pct.mean()})
pd.DataFrame(hy).to_csv(os.path.join(HERE, "gift_halfyear.csv"), index=False)

# descriptive: GIFT class vs actual NIFTY gap on trade days
desc = []
for st in STRATS:
    S = L[(L.strategy == st) & L.gift_cls.notna()]
    cc = S.gift_ret.corr(S.gap_pct)
    cr = S.gift_ret_rob.corr(S.gap_pct)
    for v in ORD["gift_cls"]:
        s = S[S.gift_cls == v]
        desc.append({"strategy": st, "gift_cls": v, "n": len(s), "mean_gift_ret": s.gift_ret.mean(), "mean_actual_gap": s.gap_pct.mean(),
                     "actual_gapdown_n": int((s.gap_cls == "gap-down").sum()), "actual_flat_n": int((s.gap_cls == "flat").sum()),
                     "actual_gapup_n": int((s.gap_cls == "gap-up").sum()),
                     "corr_gift_actual_all_rows": cc, "corr_gift_prevrow_actual_all_rows": cr})
pd.DataFrame(desc).to_csv(os.path.join(HERE, "gift_vs_actual_descriptive.csv"), index=False)
print("done")
