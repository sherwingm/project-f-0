"""Agent 4: class tables, Kruskal-Wallis tests, Benjamini-Hochberg 10 %, second-half consistency.
Reads external_features.csv (written by build_features.py). All classes / thresholds were fixed in the pre-analysis
brief before any return was looked at; terciles use DISCOVERY entries (to 2025-09-30) of the same strategy only.
Outputs: external_tables.csv, external_tests.csv, external_consistency.csv, external_level_cuts.csv.
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

OUT = os.path.dirname(os.path.abspath(__file__))
F = pd.read_csv(os.path.join(OUT, "external_features.csv"), parse_dates=["date"])
DISC_END = pd.Timestamp("2025-09-30")
SEED, NBOOT, MINN = 20261117, 5000, 10
F["period"] = np.where(F["date"] <= DISC_END, "discovery", "second_half")
STRATS = [("G1F", "G1-F (primary)"), ("G1", "G1 puts"), ("G1C", "G1-C calls"), ("XP", "XP straddle")]

# ---- tercile classes of the FII index-futures long share level (cuts from the strategy's own discovery entries only)
cuts = []
F["fii_level_class"] = pd.Series([None] * len(F), dtype=object)
for s, _ in STRATS:
    m = F.strategy == s
    d = F[m & (F.period == "discovery")]["fii_fut_share"].dropna()
    lo, hi = np.quantile(d, [1 / 3, 2 / 3])
    cuts.append(dict(strategy=s, n_discovery=len(d), p33=lo, p67=hi))
    v = F.loc[m, "fii_fut_share"]
    F.loc[m, "fii_level_class"] = np.where(v.isna(), None, np.where(v <= lo, "low", np.where(v >= hi, "high", "mid")))
pd.DataFrame(cuts).to_csv(os.path.join(OUT, "external_level_cuts.csv"), index=False)

HYPS = [
    ("H1", "S&P 500 previous US session (down <=-0.3 / flat / up >=+0.3 %)", "sp_class", ["down", "flat", "up"]),
    ("H2", "USD/INR 1-session change (down <=-0.2 / flat / up >=+0.2 %)", "usd_class", ["down", "flat", "up"]),
    ("H3", "Brent 1-session change (down <=-1 / flat / up >=+1 %); Yahoo daily, see data note", "brent_class", ["down", "flat", "up"]),
    ("H4", "Global risk indicator (risk-on = S&P>=+0.3 & USDINR<+0.2; risk-off = S&P<=-0.3 & USDINR>-0.2; else mixed)", "risk_class", ["risk_off", "mixed", "risk_on"]),
    ("H5", "Copper 1-session change (+/-1 %), risk context", "copper_class", ["down", "flat", "up"]),
    ("H6", "FII index-futures long share, sign of 1-session change", "fii_fut_share_chgsign", ["down", "up"]),
    ("H7", "FII index-futures long share LEVEL (discovery terciles)", "fii_level_class", ["low", "mid", "high"]),
    ("H8", "DII index-futures long share, sign of 1-session change", "dii_fut_share_chgsign", ["down", "up"]),
    ("H9", "FII vs DII futures divergence (sign of changes)", "fii_dii_diverge", ["divergent", "both_up", "both_down"]),
    ("H10", "FII index-options bearishness (net puts minus net calls), sign of 1-session change", "fii_opt_bear_chgsign", ["down", "up"]),
    ("H11", "Client (retail) index-futures long share, sign of 1-session change", "client_fut_share_chgsign", ["down", "up"]),
    ("H12", "Scheduled events (RBI / Budget / FOMC next session / US election)", "event_class", ["none", "day_before", "event_day", "day_after"]),
    ("H13", "GDELT tone of the previous day vs trailing 250-day median", "tone_class", ["below_median", "above_median"]),
]


def boot_ci(sub):
    """95 % interval of the mean net_pct, resampling trading days (clusters)."""
    g = sub.groupby("date")["net_pct"].agg(["sum", "count"])
    if len(g) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(g), size=(NBOOT, len(g)))
    sums, cnts = g["sum"].to_numpy(), g["count"].to_numpy()
    m = sums[idx].sum(1) / cnts[idx].sum(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def cell(sub):
    n = len(sub)
    r = dict(n=n)
    if n == 0:
        return r
    w = sub["net_rs"] > 0
    l = sub["net_rs"] < 0
    r.update(wins=int(w.sum()), losses=int(l.sum()), win_rate=100 * w.mean(), mean_pct=sub.net_pct.mean(), median_pct=sub.net_pct.median(),
             total_rs=sub.net_rs.sum(), avg_profit_rs=sub.net_rs[w].mean() if w.any() else np.nan,
             avg_loss_rs=sub.net_rs[l].mean() if l.any() else np.nan,
             avg_win_pct=sub.net_pct[w].mean() if w.any() else np.nan, avg_loss_pct=sub.net_pct[l].mean() if l.any() else np.nan,
             maxup_mean=sub.maxup.mean(), maxup_median=sub.maxup.median(),
             share_ge50=100 * (sub.maxup >= 50).mean(), share_ge100=100 * (sub.maxup >= 100).mean(), share_ge200=100 * (sub.maxup >= 200).mean())
    r["ci_lo"], r["ci_hi"] = boot_ci(sub) if n >= 2 else (np.nan, np.nan)
    r["flag"] = "too few (n<10): no conclusion" if n < MINN else ""
    return r


def bh(p, q=0.10):
    p = np.asarray(p, float)
    ok = ~np.isnan(p)
    out = np.full(len(p), np.nan)
    passed = np.zeros(len(p), bool)
    if ok.sum() == 0:
        return out, passed
    pv = p[ok]
    o = np.argsort(pv)
    m = len(pv)
    adj = np.empty(m)
    prev = 1.0
    for rank in range(m, 0, -1):
        i = o[rank - 1]
        prev = min(prev, pv[i] * m / rank)
        adj[i] = prev
    out[ok] = adj
    passed[ok] = adj <= q
    return out, passed


tab, tst = [], []
for s, sname in STRATS:
    for hid, hname, col, order in HYPS:
        for an, mask in [("whole", F.strategy == s), ("discovery", (F.strategy == s) & (F.period == "discovery")),
                         ("second_half", (F.strategy == s) & (F.period == "second_half"))]:
            sub = F[mask]
            present = sub[col].dropna().unique().tolist()
            classes = order + [c for c in present if c not in order]
            groups = []
            for c in classes:
                x = sub[sub[col] == c]
                row = dict(strategy=s, hyp=hid, analysis=an, column=col, cls=c)
                row.update(cell(x))
                tab.append(row)
                if len(x) >= MINN:
                    groups.append(x.net_pct.to_numpy())
            nmiss = int(sub[col].isna().sum())
            if len(groups) >= 2:
                try:
                    H, p = stats.kruskal(*groups)
                except ValueError:
                    H, p = np.nan, np.nan
            else:
                H, p = np.nan, np.nan
            tst.append(dict(strategy=s, hyp=hid, analysis=an, column=col, n_total=len(sub), n_missing=nmiss, classes_tested=len(groups), KW_H=H, p=p))

T = pd.DataFrame(tab)
S = pd.DataFrame(tst)
S["q_BH"] = np.nan
S["pass_BH10"] = False
for (s, an), g in S.groupby(["strategy", "analysis"]):
    q, ps = bh(g.p.to_numpy())
    S.loc[g.index, "q_BH"] = q
    S.loc[g.index, "pass_BH10"] = ps
T.to_csv(os.path.join(OUT, "external_tables.csv"), index=False)
S.to_csv(os.path.join(OUT, "external_tests.csv"), index=False)

# ---- consistency: discovery best / worst class (n >= 10) and whether the same order holds in the second half
cons = []
for s, _ in STRATS:
    for hid, hname, col, order in HYPS:
        d = T[(T.strategy == s) & (T.hyp == hid) & (T.analysis == "discovery") & (T.n >= MINN)]
        h2 = T[(T.strategy == s) & (T.hyp == hid) & (T.analysis == "second_half")].set_index("cls")
        r = dict(strategy=s, hyp=hid)
        pd_ = S[(S.strategy == s) & (S.hyp == hid) & (S.analysis == "discovery")].iloc[0]
        r.update(disc_p=pd_.p, disc_q=pd_.q_BH, disc_pass=bool(pd_.pass_BH10))
        ps = S[(S.strategy == s) & (S.hyp == hid) & (S.analysis == "second_half")].iloc[0]
        r.update(h2_p=ps.p, h2_q=ps.q_BH)
        pw = S[(S.strategy == s) & (S.hyp == hid) & (S.analysis == "whole")].iloc[0]
        r.update(whole_p=pw.p, whole_q=pw.q_BH, whole_pass=bool(pw.pass_BH10))
        if len(d) >= 2:
            best = d.loc[d.mean_pct.idxmax()]
            worst = d.loc[d.mean_pct.idxmin()]
            r.update(best_cls=best.cls, best_mean_disc=best.mean_pct, best_n_disc=best.n, worst_cls=worst.cls, worst_mean_disc=worst.mean_pct, worst_n_disc=worst.n)
            if best.cls in h2.index and worst.cls in h2.index:
                b2, w2 = h2.loc[best.cls], h2.loc[worst.cls]
                r.update(best_mean_h2=b2.mean_pct, best_n_h2=b2.n, worst_mean_h2=w2.mean_pct, worst_n_h2=w2.n)
                if b2.n >= MINN and w2.n >= MINN:
                    r["order_holds_h2"] = bool(b2.mean_pct > w2.mean_pct)
                    r["median_order_holds_h2"] = bool(b2.median_pct > w2.median_pct)
                else:
                    r["order_holds_h2"] = "too few"
        cons.append(r)
C = pd.DataFrame(cons)
C.to_csv(os.path.join(OUT, "external_consistency.csv"), index=False)
print(S[S.analysis == "whole"].pivot(index="hyp", columns="strategy", values="p").round(3))
print(S[S.analysis == "discovery"].pivot(index="hyp", columns="strategy", values="p").round(3))
print(S[S.analysis == "second_half"].pivot(index="hyp", columns="strategy", values="p").round(3))
print("BH pass (whole):\n", S[(S.analysis == "whole") & S.pass_BH10][["strategy", "hyp", "p", "q_BH"]])
print("BH pass (discovery):\n", S[(S.analysis == "discovery") & S.pass_BH10][["strategy", "hyp", "p", "q_BH"]])
