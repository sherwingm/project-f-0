"""Agent 3: pre-registered regime tables, tests (KW, Welch, BH 10% per strategy), explanatory vs predictive. Needs regimes.py output."""
import itertools, math, os
import numpy as np, pandas as pd
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__))
L = pd.read_csv(os.path.join(HERE, "regime_labels.csv"), parse_dates=["date"])
STRATS = ["G1-F", "G1", "G1-C", "XP"]
MIN_N, NB, SEED = 10, 5000, 20261117
ORD = {"dir5": [1, 2, 3, 4, 5], "dir3": ["bearish", "sideways", "bullish"], "vix_level": ["low", "normal", "high"],
       "vix_dir": ["falling", "flat", "rising"], "vix_expansion": ["no", "yes"], "gap_cls": ["gap-down", "flat", "gap-up"],
       "us_cls": ["down", "flat", "up"], "q5": [1, 2, 3, 4, 5], "q10": [1, 2, 3, 4, 5], "ma_struct": ["bear", "mixed", "bull"]}
HYP = {"H1": ["dir5"], "H2": ["vix_level"], "H3": ["vix_dir"], "H4": ["vix_expansion"], "H5": ["gap_cls"], "H6": ["us_cls"],
       "H7": ["dir3", "vix_level"], "H8": ["dir3", "gap_cls"], "H9": ["vix_level", "gap_cls"]}
ROB = {"X1_dir3": ["dir3"], "R1_ret5": ["q5"], "R2_ret10": ["q10"], "R3_ma": ["ma_struct"]}
NAMED = {"H1": ("dir3", "bearish", "bullish"), "H2": ("vix_level", "low", "high"), "H3": ("vix_dir", "falling", "rising"),
         "H4": ("vix_expansion", "no", "yes"), "H5": ("gap_cls", "gap-down", "flat"), "H6": ("us_cls", "down", "up")}
ONECOL = {"H1": "dir3", "H2": "vix_level", "H3": "vix_dir", "H4": "vix_expansion", "H5": "gap_cls", "H6": "us_cls"}


def boot_ci(df):
    """95% CI of mean net_pct, resampling trading days (clusters), NB draws."""
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


def bh(p, q=0.10):
    p = pd.Series(p)
    ok = p.dropna().sort_values()
    m = len(ok)
    res = pd.Series(False, index=p.index)
    if m == 0:
        return res
    passed = [pv <= (i + 1) / m * q for i, pv in enumerate(ok.values)]
    if any(passed):
        kmax = max(i for i, x in enumerate(passed) if x)
        res[ok.index[:kmax + 1]] = True
    return res


def cells_of(S, dims):
    if len(dims) == 1:
        for v in ORD[dims[0]]:
            yield (str(v),), S[S[dims[0]].astype(str) == str(v)]
    else:
        for a, b in itertools.product(ORD[dims[0]], ORD[dims[1]]):
            yield (str(a), str(b)), S[(S[dims[0]].astype(str) == str(a)) & (S[dims[1]].astype(str) == str(b))]


def run(S, tag):
    out, tests = [], []
    for hname, dims in {**HYP, **ROB}.items():
        parts = []
        for key, sub in cells_of(S, dims):
            r = {"hypothesis": hname, "dims": "x".join(dims), "regime": " | ".join(key), "section": tag, **cell(sub)}
            r["small"] = "too few" if r["n"] < MIN_N else ""
            out.append(r)
            parts.append(sub)
        t = {"hypothesis": hname, "section": tag, "kw_p": kw(parts), "n_cells_ge10": sum(len(p) >= MIN_N for p in parts)}
        if hname in NAMED:
            col, a, b = NAMED[hname]
            d, p = welch(S[S[col].astype(str) == a], S[S[col].astype(str) == b])
            t.update(welch_pair=f"{a} minus {b}", welch_diff_pct=d, welch_p=p)
            if hname == "H5":
                d2, p2 = welch(S[S[col] == "gap-down"], S[S[col] == "gap-up"])
                t.update(welch2_pair="gap-down minus gap-up", welch2_diff_pct=d2, welch2_p=p2)
        tests.append(t)
    return out, tests


all_rows, all_tests = [], []
for st in STRATS:
    S = L[L.strategy == st]
    for tag, sub in (("explanatory_all", S), ("discovery_to_2025-09-30", S[S.period == "discovery"]), ("second_half", S[S.period == "second_half"])):
        o, t = run(sub, tag)
        for r in o:
            r["strategy"] = st
        for r in t:
            r["strategy"] = st
        all_rows += o
        all_tests += t
R = pd.DataFrame(all_rows)
T = pd.DataFrame(all_tests)
T["bh10_survives"] = False
for (st, sec), g in T[T.hypothesis.str.startswith("H")].groupby(["strategy", "section"]):
    T.loc[g.index, "bh10_survives"] = bh(g.kw_p).values

trip = []
for st in STRATS:
    S = L[L.strategy == st]
    ns = [len(S[(S.dir3 == a) & (S.vix_level == b) & (S.gap_cls == c)])
          for a, b, c in itertools.product(ORD["dir3"], ORD["vix_level"], ORD["gap_cls"])]
    trip.append({"strategy": st, "cells": len(ns), "min_cell_n": min(ns), "cells_ge10": sum(n >= 10 for n in ns),
                 "status": "tested" if min(ns) >= 10 else "insufficient (some cells < 10)"})
pd.DataFrame(trip).to_csv(os.path.join(HERE, "triple_status.csv"), index=False)

cols = ["strategy", "section", "hypothesis", "dims", "regime", "n", "small", "wins", "losses", "win_rate", "mean_net_pct", "boot_lo", "boot_hi",
        "median_net_pct", "total_net_rs", "avg_profit_rs", "avg_loss_rs", "maxup_mean", "maxup_median", "maxup_ge50", "maxup_ge100", "maxup_ge200",
        "top5pct_share_of_total_rs"]
R[cols].to_csv(os.path.join(HERE, "regime_tables.csv"), index=False)
T.to_csv(os.path.join(HERE, "regime_tests.csv"), index=False)

# predictive consistency: class mean minus mean of the other trades, discovery vs second half
cons = []
for st in STRATS:
    S = L[L.strategy == st]
    for h, col in ONECOL.items():
        for v in ORD[col]:
            row = {"strategy": st, "hypothesis": h, "class": str(v)}
            for per, P in (("disc", S[S.period == "discovery"]), ("second", S[S.period == "second_half"])):
                a = P[P[col].astype(str) == str(v)]
                b = P[P[col].astype(str) != str(v)]
                row[f"n_{per}"] = len(a)
                row[f"diff_vs_rest_{per}"] = a.net_pct.mean() - b.net_pct.mean() if len(a) >= MIN_N and len(b) >= MIN_N else np.nan
            d1, d2 = row["diff_vs_rest_disc"], row["diff_vs_rest_second"]
            row["same_sign"] = bool(np.sign(d1) == np.sign(d2)) if d1 == d1 and d2 == d2 else np.nan
            cons.append(row)
pd.DataFrame(cons).to_csv(os.path.join(HERE, "regime_consistency.csv"), index=False)

hy = []
for st in STRATS:
    S = L[L.strategy == st]
    for hp, P in S.groupby("halfyear"):
        for col, key in (("dir3", "bearish"), ("dir3", "bullish"), ("vix_level", "low"), ("vix_dir", "rising"), ("gap_cls", "gap-down")):
            a = P[P[col] == key]
            hy.append({"strategy": st, "halfyear": hp, "class": f"{col}={key}", "n": len(a), "n_all": len(P),
                       "mean_net_pct": a.net_pct.mean() if len(a) >= MIN_N else np.nan, "all_mean_net_pct": P.net_pct.mean()})
pd.DataFrame(hy).to_csv(os.path.join(HERE, "regime_halfyear.csv"), index=False)

dt = L.assign(dte_cls=np.where(L.dte == 0, "0", np.where(L.dte == 1, "1", "2+")))
sup = []
for st in STRATS:
    for v in ["0", "1", "2+"]:
        s = dt[(dt.strategy == st) & (dt.dte_cls == v)]
        sup.append({"strategy": st, "dte": v, **cell(s)})
pd.DataFrame(sup).to_csv(os.path.join(HERE, "supp_dte.csv"), index=False)
xw = L[L.strategy == "XP"].assign(wd=lambda d: d.date.dt.dayofweek)
pd.DataFrame([{"weekday": w, **cell(s)} for w, s in xw.groupby("wd")]).to_csv(os.path.join(HERE, "supp_xp_weekday.csv"), index=False)
print("done")
