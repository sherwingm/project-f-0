"""Agent 4 (v2): class tables, Kruskal-Wallis, Welch, bootstrap, consistency.  Reads external_features.csv (build_features.py).
All classes and thresholds are the fixed Amendment-1 definitions (or fixed in advance in the brief); nothing is searched or re-cut.
Outputs: external_tables.csv, external_tests.csv, external_consistency.csv.   Run: python -W ignore analyse_external.py
"""
import math, os
import numpy as np
import pandas as pd
from scipy import stats

OUT = os.path.dirname(os.path.abspath(__file__))
F = pd.read_csv(os.path.join(OUT, "external_features.csv"), parse_dates=["date"])
DISC_END = pd.Timestamp("2025-09-30")
SEED, NBOOT, MINN = 20261117, 5000, 10
F["period"] = np.where(F["date"] <= DISC_END, "discovery", "second_half")
F["brent_class_clean"] = np.where(F["brent_suspect"] == 0, F["brent_class"], np.nan)
STRATS = [("G1F", "G1-F (primary)"), ("G1", "G1 puts"), ("G1C", "G1-C calls"), ("XP", "XP straddle")]

# id, family, description, column, ordered classes, named pair for Welch (a vs b)
HYPS = [
    ("H12", "main", "Asia pre-entry: mean of Nikkei and Hang Seng opening gap (+/-0.3 %)", "asia_class", ["down", "flat", "up"], ("up", "down")),
    ("H13", "main", "Global risk: risk-on = US up & Asia not down; risk-off = US down & Asia not up", "risk_class", ["risk_off", "mixed", "risk_on"], ("risk_on", "risk_off")),
    ("H14", "main", "Breadth: advance share of previous session (<=p25 low, >=p75 high; cuts from 2021-10..2024-09)", "breadth_class", ["low", "mid", "high"], ("high", "low")),
    ("H15", "main", "FII/DII cash previous session (third party, 2025-12..2026-10): diverge / both buying / both selling", "fiidii_class", ["diverge", "both_buy", "both_sell"], ("both_buy", "diverge")),
    ("X01", "main", "US overnight: S&P 500 previous US session (+/-0.3 %)", "us_class", ["down", "flat", "up"], ("up", "down")),
    ("X02", "main", "USD/INR previous Indian-session change, hourly (+/-0.2 %)", "usd_class", ["down", "flat", "up"], ("up", "down")),
    ("X03", "main", "Brent previous-day change (+/-1 %); quality-limited", "brent_class", ["down", "flat", "up"], ("up", "down")),
    ("X04", "main", "US VIX previous-session rise >= +10 % (spike)", "usvix_class", ["no_spike", "spike"], ("spike", "no_spike")),
    ("X05", "main", "Dollar index previous-day direction (descriptive)", "dxy_class", ["down", "up"], ("up", "down")),
    ("X06", "main", "US 10-year yield previous-day direction (descriptive)", "us10y_class", ["down", "up"], ("up", "down")),
    ("X07", "main", "Sector leadership: Nifty Bank minus Nifty 50 previous day (+/-0.3 pts)", "sector_class", ["bank_lags", "in_line", "bank_leads"], ("bank_leads", "bank_lags")),
    ("X08", "main", "FII index-futures long share LEVEL (terciles of session days 2024-10..2025-09)", "fii_fut_level_class", ["low", "mid", "high"], ("high", "low")),
    ("X09", "main", "FII index-futures long share, 1-session change sign", "fii_fut_chg_class", ["down", "up"], ("up", "down")),
    ("X10", "main", "DII index-futures long share LEVEL (discovery-window terciles)", "dii_fut_level_class", ["low", "mid", "high"], ("high", "low")),
    ("X11", "main", "DII index-futures long share, 1-session change sign", "dii_fut_chg_class", ["down", "up"], ("up", "down")),
    ("X12", "main", "FII index-options stance (net puts minus net calls / option OI) LEVEL (terciles)", "fii_opt_level_class", ["low", "mid", "high"], ("high", "low")),
    ("X13", "main", "FII index-options stance, 1-session change sign (up = more put-heavy)", "fii_opt_chg_class", ["down", "up"], ("up", "down")),
    ("X14", "main", "GDELT tone of the previous UTC day vs trailing 250-day median (global machine score)", "tone_class", ["below_median", "above_median"], ("above_median", "below_median")),
    ("X15", "main", "Scheduled events (RBI / Budget / FOMC / US election) relative to the entry session", "event_class", ["none", "day_before", "event_day", "day_after"], ("event_day", "none")),
    ("S01", "suppl", "Brent excluding days where daily and hourly closes differ by >2 % (robustness)", "brent_class_clean", ["down", "flat", "up"], ("up", "down")),
    ("S02", "suppl", "FII cash net sign previous session (third party)", "fii_cash_sign", ["sell", "buy"], ("buy", "sell")),
    ("S03", "suppl", "DII cash net sign previous session (third party)", "dii_cash_sign", ["sell", "buy"], ("buy", "sell")),
]


def boot_ci(sub):
    g = sub.groupby("date")["net_pct"].agg(["sum", "count"])
    if len(g) < 2: return np.nan, np.nan
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(g), size=(NBOOT, len(g)))
    s, c = g["sum"].to_numpy(), g["count"].to_numpy()
    m = s[idx].sum(1) / c[idx].sum(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def top5_share(sub):
    pos = np.sort(sub.net_rs[sub.net_rs > 0].to_numpy())[::-1]
    if len(pos) == 0: return np.nan
    k = max(1, math.ceil(0.05 * len(sub)))
    return 100 * pos[:k].sum() / pos.sum()


def cell(sub):
    n = len(sub); r = dict(n=n)
    if n == 0: return r
    w, l = sub["net_rs"] > 0, sub["net_rs"] < 0
    r.update(wins=int(w.sum()), losses=int(l.sum()), win_rate=100 * w.mean(), mean_pct=sub.net_pct.mean(), median_pct=sub.net_pct.median(),
             total_rs=sub.net_rs.sum(), avg_profit_rs=sub.net_rs[w].mean() if w.any() else np.nan, avg_loss_rs=sub.net_rs[l].mean() if l.any() else np.nan,
             avg_win_pct=sub.net_pct[w].mean() if w.any() else np.nan, avg_loss_pct=sub.net_pct[l].mean() if l.any() else np.nan,
             maxup_mean=sub.maxup.mean(), maxup_median=sub.maxup.median(),
             share_ge50=100 * (sub.maxup >= 50).mean(), share_ge100=100 * (sub.maxup >= 100).mean(), share_ge200=100 * (sub.maxup >= 200).mean(),
             top5pct_share_of_gross_profit=top5_share(sub))
    r["ci_lo"], r["ci_hi"] = boot_ci(sub) if n >= 2 else (np.nan, np.nan)
    r["flag"] = "too few (n<10): no conclusion" if n < MINN else ""
    return r


def bh(p, q=0.10):
    p = np.asarray(p, float); ok = ~np.isnan(p); out = np.full(len(p), np.nan)
    if ok.sum() == 0: return out
    pv = p[ok]; o = np.argsort(pv); m = len(pv); adj = np.empty(m); prev = 1.0
    for rank in range(m, 0, -1):
        i = o[rank - 1]; prev = min(prev, pv[i] * m / rank); adj[i] = prev
    out[ok] = adj; return out


tab, tst = [], []
HYS = sorted(F.halfyear.unique())
sets = [("whole", None), ("discovery", "discovery"), ("second_half", "second_half")] + [(f"hy_{h}", h) for h in HYS]
for s, _ in STRATS:
    for hid, fam, hname, col, order, pair in HYPS:
        for an, key in sets:
            m = F.strategy == s
            if an in ("discovery", "second_half"): m &= F.period == key
            elif an.startswith("hy_"): m &= F.halfyear == key
            sub = F[m]
            present = sub[col].dropna().unique().tolist()
            classes = order + [c for c in present if c not in order]
            groups, byc = [], {}
            for c in classes:
                x = sub[sub[col] == c]; byc[c] = x
                row = dict(strategy=s, hyp=hid, family=fam, analysis=an, column=col, cls=c); row.update(cell(x)); tab.append(row)
                if len(x) >= MINN: groups.append(x.net_pct.to_numpy())
            if an.startswith("hy_"): continue
            H = p = np.nan
            if len(groups) >= 2:
                try: H, p = stats.kruskal(*groups)
                except ValueError: pass
            a, b = byc.get(pair[0], sub.iloc[0:0]), byc.get(pair[1], sub.iloc[0:0])
            wt = wp = wd = np.nan
            if len(a) >= MINN and len(b) >= MINN:
                wt, wp = stats.ttest_ind(a.net_pct, b.net_pct, equal_var=False); wd = a.net_pct.mean() - b.net_pct.mean()
            tst.append(dict(strategy=s, hyp=hid, family=fam, description=hname, analysis=an, column=col, n_total=len(sub), n_missing=int(sub[col].isna().sum()),
                            classes_tested=len(groups), KW_H=H, KW_p=p, welch_pair=f"{pair[0]} vs {pair[1]}", welch_n_a=len(a), welch_n_b=len(b),
                            welch_diff_mean_pct=wd, welch_t=wt, welch_p=wp))
T = pd.DataFrame(tab); S = pd.DataFrame(tst)
S["KW_q_BH_own_main_family"] = np.nan
for (s, an), g in S[S.family == "main"].groupby(["strategy", "analysis"]):
    S.loc[g.index, "KW_q_BH_own_main_family"] = bh(g.KW_p.to_numpy())
S["note"] = "raw p-values; the coordinator applies the final Benjamini-Hochberg over the enlarged family; own q is informative only"
T.to_csv(os.path.join(OUT, "external_tables.csv"), index=False)
S.to_csv(os.path.join(OUT, "external_tests.csv"), index=False)

# ---- consistency: predictive rule fixed in advance = discovery best / worst class (n>=10); do they keep the order in the second half and by half-year?
cons = []
for s, _ in STRATS:
    for hid, fam, hname, col, order, pair in HYPS:
        d = T[(T.strategy == s) & (T.hyp == hid) & (T.analysis == "discovery") & (T.n >= MINN)]
        r = dict(strategy=s, hyp=hid, family=fam, column=col)
        g = lambda an, c: S[(S.strategy == s) & (S.hyp == hid) & (S.analysis == an)].iloc[0][c]
        r.update(disc_KW_p=g("discovery", "KW_p"), h2_KW_p=g("second_half", "KW_p"), whole_KW_p=g("whole", "KW_p"),
                 disc_welch_diff=g("discovery", "welch_diff_mean_pct"), h2_welch_diff=g("second_half", "welch_diff_mean_pct"),
                 disc_welch_p=g("discovery", "welch_p"), h2_welch_p=g("second_half", "welch_p"))
        dd, dh = r["disc_welch_diff"], r["h2_welch_diff"]
        r["welch_pair_sign_same_in_both"] = (np.sign(dd) == np.sign(dh)) if pd.notna(dd) and pd.notna(dh) else "not testable (n<10 in a class)"
        if len(d) >= 2:
            h2 = T[(T.strategy == s) & (T.hyp == hid) & (T.analysis == "second_half")].set_index("cls")
            best, worst = d.loc[d.mean_pct.idxmax()], d.loc[d.mean_pct.idxmin()]
            r.update(best_cls=best.cls, best_mean_disc=best.mean_pct, best_n_disc=best.n, worst_cls=worst.cls, worst_mean_disc=worst.mean_pct, worst_n_disc=worst.n)
            if best.cls in h2.index and worst.cls in h2.index:
                b2, w2 = h2.loc[best.cls], h2.loc[worst.cls]
                r.update(best_mean_h2=b2.mean_pct, best_n_h2=b2.n, worst_mean_h2=w2.mean_pct, worst_n_h2=w2.n)
                r["order_holds_h2_mean"] = bool(b2.mean_pct > w2.mean_pct) if (b2.n >= MINN and w2.n >= MINN) else "too few"
                r["order_holds_h2_median"] = bool(b2.median_pct > w2.median_pct) if (b2.n >= MINN and w2.n >= MINN) else "too few"
            hyh = T[(T.strategy == s) & (T.hyp == hid) & (T.analysis.str.startswith("hy_"))]
            ok = []
            for hy_ in HYS:
                x = hyh[hyh.analysis == f"hy_{hy_}"].set_index("cls")
                if best.cls in x.index and worst.cls in x.index and x.loc[best.cls, "n"] >= 5 and x.loc[worst.cls, "n"] >= 5:
                    ok.append(x.loc[best.cls, "mean_pct"] > x.loc[worst.cls, "mean_pct"])
            r["halfyears_testable_n>=5each"] = len(ok); r["halfyears_order_holds"] = int(sum(ok))
        cons.append(r)
C = pd.DataFrame(cons); C.to_csv(os.path.join(OUT, "external_consistency.csv"), index=False)
for an in ["whole", "discovery", "second_half"]:
    print(an); print(S[(S.analysis == an) & (S.family == "main")].pivot(index="hyp", columns="strategy", values="KW_p").round(3))
