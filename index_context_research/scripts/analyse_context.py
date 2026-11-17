"""Stage 1 (individual factors), yearly tables and validation of index_context_research/PREREG_CONTEXT.md.
Stage 1 uses the DISCOVERY half only to choose splits and survivors; the validation half is opened once, for frozen survivors.
Outputs: results/ctx_stage1_discovery.csv, ctx_frozen.csv, ctx_validation.csv, ctx_yearly.csv, ctx_yearly.md"""
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
sys.stdout.reconfigure(encoding="utf-8")
FEATS = ["gap_pct", "vix_signal", "vix_chg5", "vix_pct1y", "gift_basis", "gift_ret_prev", "us_prev_ret", "fut_oi_chg", "fut_px_chg", "fii_fut_longshare", "fii_fut_chg",
         "atm_iv", "pcr_oi", "iv_skew", "breadth_prev", "event_window", "expiry_day"]
BINARY = {"event_window", "expiry_day"}
Q = 0.10
SETS = ["G1", "G1F", "G1C", "XP"]


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 5 or len(b) < 5:
        return np.nan, np.nan
    d = a.mean() - b.mean()
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return d, d / se if se > 0 else np.nan


def p2(t):
    return math.erfc(abs(t) / math.sqrt(2)) if t == t else np.nan


def stats(x):
    v = x["net_pct"].astype(float)
    if len(v) == 0:
        return {"n": 0}
    rs = x["net_rs"].astype(float)
    gp, gl = rs[rs > 0].sum(), -rs[rs < 0].sum()
    eq = rs.cumsum().to_numpy()
    dd = (eq - np.maximum.accumulate(np.concatenate([[0], eq]))[1:]).min()
    mu = x["maxup"].dropna()
    return {"n": len(v), "maxup_ge100": (mu >= 100).mean() * 100 if len(mu) else np.nan, "maxup_mean": mu.mean() if len(mu) else np.nan, "maxup_median": mu.median() if len(mu) else np.nan,
            "win_pct": (v > 0).mean() * 100, "mean_pct": v.mean(), "median_pct": v.median(), "pf": gp / gl if gl > 0 else np.nan, "total_rs": rs.sum(), "max_dd_rs": dd,
            "avg_win": v[v > 0].mean() if (v > 0).any() else np.nan, "avg_loss": v[v < 0].mean() if (v < 0).any() else np.nan}


def boot_diff(a, b, n=2000, seed=20261116):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a, float), np.asarray(b, float)
    ds = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n)]
    return float(np.percentile(ds, 2.5)), float(np.percentile(ds, 97.5))


def split(x, f, med):
    if f in BINARY:
        return x[x[f] == 1], x[x[f] == 0]
    return x[x[f] > med], x[x[f] <= med]


def main():
    D = pd.read_csv(os.path.join(RES, "context_dataset.csv"), parse_dates=["day"])
    D["day"] = D["day"].dt.date
    D = D[D["note"].isna()] if "note" in D else D
    rows = []
    for s in SETS:
        T = D[D["tset"] == s]
        Td = T[T["half"] == "D"]
        for f in FEATS:
            x = Td[Td[f].notna()]
            # pre-registered rule: not tested when more than 30 % missing. (The first run also skipped n < 60, which was NOT in the plan;
            # removed on 16 Nov before the validation half was ever opened, so XP (about 52 discovery days) is now tested as planned.)
            if len(Td) == 0 or Td[f].isna().mean() > 0.3:
                rows.append({"tset": s, "feature": f, "n": len(x), "tested": False, "why": "missing > 30 %"})
                continue
            med = float(x[f].median()) if f not in BINARY else 0.5
            hi, lo = split(x, f, med)
            d, t = welch(hi["net_pct"], lo["net_pct"])
            if t != t:
                rows.append({"tset": s, "feature": f, "n": len(x), "tested": False, "why": "a side has < 5 trades"})
                continue
            lo_ci, hi_ci = boot_diff(hi["net_pct"], lo["net_pct"])
            sh, sl = stats(hi), stats(lo)
            rows.append({"tset": s, "feature": f, "n": len(x), "median": med, "tested": True, "n_high": sh["n"], "n_low": sl["n"], "mean_high": sh["mean_pct"], "mean_low": sl["mean_pct"],
                         "diff": d, "t": t, "p": p2(t), "ci_lo": lo_ci, "ci_hi": hi_ci, "maxup100_high": sh["maxup_ge100"], "maxup100_low": sl["maxup_ge100"],
                         "win_high": sh["win_pct"], "win_low": sl["win_pct"], "pf_high": sh["pf"], "pf_low": sl["pf"], "dd_high": sh["max_dd_rs"], "dd_low": sl["max_dd_rs"]})
    R = pd.DataFrame(rows)
    tested = R[R["tested"] == True].sort_values("p").reset_index(drop=True)  # noqa: E712
    m = len(tested)
    tested["bh_thr"] = [(i + 1) / m * Q for i in range(m)]
    k = max([i for i in range(m) if tested.loc[i, "p"] <= tested.loc[i, "bh_thr"]], default=-1)
    tested["bh_pass"] = [i <= k for i in range(m)]
    R = R.merge(tested[["tset", "feature", "bh_thr", "bh_pass"]], on=["tset", "feature"], how="left")
    R.to_csv(os.path.join(RES, "ctx_stage1_discovery.csv"), index=False)
    surv = tested[tested["bh_pass"]]
    surv[["tset", "feature", "median", "diff", "t"]].to_csv(os.path.join(RES, "ctx_frozen.csv"), index=False)
    pd.set_option("display.width", 250, "display.max_columns", 30)
    show = ["tset", "feature", "n", "n_high", "n_low", "mean_high", "mean_low", "diff", "t", "p", "maxup100_high", "maxup100_low"]
    print(f"=== STAGE 1, DISCOVERY (entries to 2025-09-30): {m} cells tested, BH 10 %: {len(surv)} survivors ===")
    print(R[R["tested"] == True][show].sort_values("p").round(3).head(30).to_string(index=False))  # noqa: E712
    print("not tested:", R[R["tested"] == False][["tset", "feature", "why"]].values.tolist())  # noqa: E712
    # validation, once, frozen survivors
    vr = []
    for _, sv in surv.iterrows():
        Tv = D[(D["tset"] == sv["tset"]) & (D["half"] == "V") & D[sv["feature"]].notna()]
        hi, lo = split(Tv, sv["feature"], sv["median"])
        d, t = welch(hi["net_pct"], lo["net_pct"])
        better_high = sv["diff"] > 0
        best = hi if better_high else lo
        ok = (len(best) >= 20 and d == d and (d > 0) == better_high and abs(t) >= 1.5 and best["net_pct"].mean() > 0)
        vr.append({"tset": sv["tset"], "feature": sv["feature"], "discovery_diff": sv["diff"], "val_n_high": len(hi), "val_n_low": len(lo), "val_diff": d, "val_t": t,
                   "val_mean_better_side": best["net_pct"].mean() if len(best) else np.nan, "passes_validation": bool(ok)})
    V = pd.DataFrame(vr)
    V.to_csv(os.path.join(RES, "ctx_validation.csv"), index=False)
    print("=== VALIDATION (opened once, frozen survivors only) ===")
    print(V.round(3).to_string(index=False) if len(V) else "no survivors: nothing to validate")
    # yearly / quarterly tables
    yr = []
    for s in SETS:
        T = D[D["tset"] == s]
        for lab, key in (("year", "year"), ("quarter", "quarter")):
            for kval, x in T.groupby(key):
                st = stats(x)
                yr.append({"tset": s, "by": lab, "period": kval, **st, "partial": (kval == 2026) if lab == "year" else str(kval).startswith("2026")})
        for lab, col in (("weekday", "weekday"), ("expiry_day", "expiry_day"), ("trend_prev", "trend_prev")):
            for kval, x in T.groupby(col):
                yr.append({"tset": s, "by": lab, "period": kval, **stats(x)})
        T = T.assign(gap_t=pd.qcut(T["gap_pct"], 3, labels=["low", "mid", "high"], duplicates="drop"), vix_t=pd.qcut(T["vix_signal"], 3, labels=["low", "mid", "high"], duplicates="drop"))
        for lab, col in (("gap_tercile", "gap_t"), ("vix_tercile", "vix_t")):
            for kval, x in T.groupby(col, observed=True):
                yr.append({"tset": s, "by": lab, "period": kval, **stats(x)})
        top = T.sort_values("net_rs", ascending=False)
        k5 = max(1, int(round(len(T) * 0.05)))
        yr.append({"tset": s, "by": "concentration", "period": "top5pct_share_of_profit", "n": k5, "total_rs": top["net_rs"].iloc[:k5].sum(), "mean_pct": T["net_rs"].sum()})
    Y = pd.DataFrame(yr)
    Y.to_csv(os.path.join(RES, "ctx_yearly.csv"), index=False)
    print("=== YEARLY (net % per trade; max up >= +100 % share) ===")
    print(Y[Y["by"] == "year"][["tset", "period", "n", "maxup_ge100", "maxup_mean", "win_pct", "mean_pct", "median_pct", "pf", "total_rs", "max_dd_rs"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
