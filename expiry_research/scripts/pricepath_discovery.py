"""pricepath discovery: event study (Part A), listed hypotheses (Part B), candle features (Part C), BH, freeze.

Reads discovery rows only for every statistic (validation rows are present in the panel for rolling windows only and
are never used here). Writes results/pricepath/{eventstudy,placebo_shuffle,hypotheses,candidates_frozen}.csv.
Run: ../.venvs/fo/Scripts/python.exe expiry_research/scripts/pricepath_discovery.py   (from the repo root)
"""
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pricepath_common import (OUT, ULS, add_quantile_targets, build_features, cond_mask, cond_text,  # noqa: E402
                              disc_quantiles, rate_test)
from stats_utils import bh, two_prop  # noqa: E402

SEED = 20261105
N_SHUFFLE = 2000
METRICS = [("o_cc", "mean"), ("o_up", "rate"), ("cc_n", "mean"), ("range_n", "mean"), ("gap_n", "mean"),
           ("persist", "rate"), ("o_rv", "mean")]
POS = [-5, -4, -3, -2, -1, 0, 1]

QCOLS = ["abs_cc", "o_range_pct", "f_mom3", "hv_ratio", "rng3_pct", "f_body_frac", "f_upper_wick_frac",
         "f_lower_wick_frac", "f_close_pos", "o_cc", "o_gap_pct", "o_last_hour", "f_mom5", "f_dist_high20",
         "f_dist_low20", "f_hv10", "f_atr14_pct", "f_vix_close", "f_vix_chg1", "f_futall_oi_r20", "f_fut_vol_r20",
         "f1515_pos_in_range", "f1515_ret_open_to_1514", "f1515_ret_to_1514", "f1515_range_pct", "f1515_vix_chg"]
CANDLE = ["f_body_frac", "f_upper_wick_frac", "f_lower_wick_frac", "f_close_pos", "o_range_pct", "o_cc", "o_gap_pct",
          "o_last_hour", "f_mom5", "f_dist_high20", "f_dist_low20", "f_hv10", "hv_ratio", "f_atr14_pct",
          "f_vix_close", "f_vix_chg1", "f_futall_oi_r20", "f_fut_vol_r20"]
T1515 = ["f1515_pos_in_range", "f1515_ret_open_to_1514", "f1515_ret_to_1514", "f1515_range_pct", "f1515_vix_chg"]


# ---------------------------------------------------------------- Part A: event study
def anchors(P, ul):
    """Expiry-weekday anchor session of every week: real expiries, plus fake ones in NIFTY pre-weekly weeks."""
    A = []
    for i in np.where(P["cal_kind"].isin(["weekly", "monthly"]))[0]:
        A.append((i, P.at[i, "cal_kind"]))
    if ul == "NIFTY":
        pre = P[(P["date"] < "2019-02-11")].copy()
        dt = pd.to_datetime(pre["date"])
        pre["wk"] = dt.dt.isocalendar().year.astype(str) + "-" + dt.dt.isocalendar().week.astype(str)
        pre["wd"] = dt.dt.weekday
        for _, g in pre.groupby("wk"):
            if (g["cal_kind"] == "monthly").any():
                continue
            th = g[g["wd"] == 3]
            we = g[g["wd"] == 2]
            if len(th):
                A.append((int(th.index[0]), "fake"))
            elif len(we):
                A.append((int(we.index[0]), "fake"))
    A = pd.DataFrame(A, columns=["i", "kind"]).sort_values("i").reset_index(drop=True)
    A["date"] = P.loc[A["i"], "date"].values
    A["month"] = A["date"].str[:7]
    A["prev_i"] = A["i"].shift(1)
    return A


def positions(P, ul):
    """Boolean columns <fam>_<k> for k in POS: wk (real weekly), fk (fake weekly, NIFTY pre-weekly), mo (monthly),
    mt (matched: k sessions from a non-monthly week's anchor, not itself a monthly position)."""
    n = len(P)
    for fam in ("wk", "fk", "mo", "mt"):
        for k in POS:
            P[f"{fam}_{k}"] = False
    for k in range(-5, 1):
        P[f"wk_{k}"] = ((P["cal_upcoming_kind"] == "weekly") & (P["cal_sessions_to_expiry"] == -k)).values
        P[f"mo_{k}"] = (P["cal_sessions_to_monthly"] == -k).values
    P["wk_1"] = (P["cal_kind"].shift(1) == "weekly").values
    P["mo_1"] = (P["cal_kind"].shift(1) == "monthly").values
    any_mo = P[[f"mo_{k}" for k in POS]].any(axis=1).values
    A = anchors(P, ul)
    fk = {k: np.zeros(n, bool) for k in POS}
    mt = {k: np.zeros(n, bool) for k in POS}
    for _, a in A.iterrows():
        i = int(a["i"])
        prev = -1 if pd.isna(a["prev_i"]) else int(a["prev_i"])
        for k in POS:
            j = i + k
            if not 0 <= j < n:
                continue
            if a["kind"] == "fake" and (k >= 0 or j > prev):
                fk[k][j] = True
            if a["kind"] != "monthly" and not any_mo[j]:
                mt[k][j] = True
    for k in POS:
        P[f"fk_{k}"] = fk[k]
        P[f"mt_{k}"] = mt[k]
    return A


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return np.nan
    return float(stats.ttest_ind(a, b, equal_var=False).pvalue)


def compare(x, y, kind):
    x, y = x.dropna(), y.dropna()
    if kind == "mean":
        return len(x), x.mean() if len(x) else np.nan, len(y), y.mean() if len(y) else np.nan, welch(x, y)
    return (len(x), x.mean() if len(x) else np.nan, len(y), y.mean() if len(y) else np.nan,
            two_prop(int(x.sum()), len(x), int(y.sum()), len(y)))


def event_study(P, ul, rng, split="discovery", start="2018-01-01", end="2022-12-31", n_shuffle=N_SHUFFLE):
    D = P[(P["split"] == split)]
    rows, shuf = [], []
    wk_era = D[(D["date"] >= "2019-02-11")] if ul == "NIFTY" else D
    pre = D[D["date"] < "2019-02-11"] if ul == "NIFTY" else D.iloc[0:0]
    A = anchors(P, ul)
    Ad = A[(A["date"] >= start) & (A["date"] <= end)]
    for k in POS:
        for col, kind in METRICS:
            # 1. weekly D-k vs every other weekly-era session
            x = wk_era.loc[wk_era[f"wk_{k}"], col]
            y = wk_era.loc[~wk_era[f"wk_{k}"], col]
            n1, m1, n2, m2, p = compare(x, y, kind)
            rows.append(dict(ul=ul, kind="weekly", pos=k, metric=col, stat=kind, comparison="other_sessions",
                             n=n1, value=m1, n_comp=n2, comp_value=m2, diff=m1 - m2, p=p))
            # 2. weekly placebo (NIFTY 2018 fake weekly) vs other 2018 sessions
            if len(pre):
                x = pre.loc[pre[f"fk_{k}"], col]
                y = pre.loc[~pre[f"fk_{k}"], col]
                n1, m1, n2, m2, p = compare(x, y, kind)
                rows.append(dict(ul=ul, kind="weekly_placebo_2018", pos=k, metric=col, stat=kind,
                                 comparison="other_sessions_2018", n=n1, value=m1, n_comp=n2, comp_value=m2,
                                 diff=m1 - m2, p=p))
            # 3. monthly D-k vs matched (same k before a non-monthly week's anchor)
            x = D.loc[D[f"mo_{k}"], col]
            y = D.loc[D[f"mt_{k}"], col]
            n1, m1, n2, m2, p = compare(x, y, kind)
            rows.append(dict(ul=ul, kind="monthly", pos=k, metric=col, stat=kind, comparison="matched_nonmonthly",
                             n=n1, value=m1, n_comp=n2, comp_value=m2, diff=m1 - m2, p=p))
    # 4. calendar-shuffled placebo for monthly
    months = sorted(Ad.loc[Ad["kind"] == "monthly", "month"].unique())
    pools = {mo: Ad.loc[(Ad["month"] == mo) & (Ad["kind"] != "monthly"), "i"].values for mo in months}
    months = [mo for mo in months if len(pools[mo])]
    vals = {(k, c): P[c].values for k in POS for c, _ in METRICS}
    real = {}
    for k in POS:
        for col, _ in METRICS:
            real[(k, col)] = D.loc[D[f"mo_{k}"], col].mean()
    draws = {key: np.empty(n_shuffle) for key in real}
    for r in range(n_shuffle):
        pick = np.array([rng.choice(pools[mo]) for mo in months])
        for k in POS:
            idx = pick + k
            idx = idx[(idx >= 0) & (idx < len(P))]
            for col, _ in METRICS:
                draws[(k, col)][r] = np.nanmean(vals[(k, col)][idx])
    for (k, col), v in real.items():
        d = draws[(k, col)]
        d = d[~np.isnan(d)]
        if len(d) == 0 or np.isnan(v):
            p = np.nan
        else:
            p = min(1.0, 2 * min((d >= v).mean(), (d <= v).mean()) + 1 / len(d))
        kind = dict(METRICS)[col]
        shuf.append(dict(ul=ul, kind="monthly_shuffle", pos=k, metric=col, stat=kind, draws=d,
                         comparison="calendar_shuffle", n=int(D[f"mo_{k}"].sum()), value=v,
                         n_comp=len(d), comp_value=float(np.mean(d)) if len(d) else np.nan,
                         diff=v - (float(np.mean(d)) if len(d) else np.nan), p=p,
                         placebo_lo=float(np.quantile(d, 0.025)) if len(d) else np.nan,
                         placebo_hi=float(np.quantile(d, 0.975)) if len(d) else np.nan))
    return rows, shuf


# ---------------------------------------------------------------- Parts B and C: rule tests
def rule_specs(Q):
    """List of (hyp, cond, contexts, targets, expected_dir, primary_ctx_target set)."""
    S = []
    for q in (0.7, 0.8, 0.9):
        c = [["f_mom3", ">=", Q["f_mom3"][q], q], ["up3", ">=", 2.0, None]]
        ctx = ["W1", "M1", "W0", "M0"] + (["X", "ALL"] if q == 0.8 else [])
        S.append(("H1_rise_then_fall", c, ctx, ["t_down", "t_sharp_fall"], 1, q == 0.8, ["t_down"]))
    for q in (0.3, 0.2, 0.1):
        c = [["f_mom3", "<=", Q["f_mom3"][q], q], ["dn3", ">=", 2.0, None]]
        ctx = ["W1", "M1", "W0", "M0"] + (["X", "ALL"] if q == 0.2 else [])
        S.append(("H2_decline_then_recovery", c, ctx, ["t_up", "t_sharp_rise"], 1, q == 0.2, ["t_up"]))
    for name, c, prim in [("nr4", [["nr4", "==", 1.0, None]], True), ("nr7", [["nr7", "==", 1.0, None]], False),
                          ("hv_fall", [["hv_ratio", "<=", Q["hv_ratio"][0.2], 0.2]], False),
                          ("rng3_narrow", [["rng3_pct", "<=", Q["rng3_pct"][0.2], 0.2]], False)]:
        S.append(("H3_sideways_then_big", c, ["W0", "M0", "X", "ALL"], ["t_big", "t_wide"], 1, prim, ["t_big"]))
    for q in (0.8, 0.9):
        c = [["abs_cc", ">=", Q["abs_cc"][q], q]]
        S.append(("H4_big_then_reversal", c, ["W0", "M0", "W1", "X", "ALL"], ["t_rev", "t_rev_oc"], 1, q == 0.8,
                  ["t_rev"]))
    S.append(("H5_failed_up_breakouts", [["fbu3", ">=", 2.0, None]], ["W0", "M0", "X", "ALL"], ["t_down"], 1, True,
              ["t_down"]))
    S.append(("H5_failed_down_breakouts", [["fbd3", ">=", 2.0, None]], ["W0", "M0", "X", "ALL"], ["t_up"], 1, True,
              ["t_up"]))
    S.append(("H6_near_round_quiet", [["round_dist_pct", "<=", 0.5, None]], ["W0", "M0", "X", "ALL"], ["t_quiet"], 1,
              True, ["t_quiet"]))
    S.append(("H6_near_high20_up", [["f_dist_high20", ">=", -0.5, None]], ["W0", "M0", "X", "ALL"], ["t_up"], 1,
              False, []))
    S.append(("H6_near_low20_down", [["f_dist_low20", "<=", 0.5, None]], ["W0", "M0", "X", "ALL"], ["t_down"], 1,
              False, []))
    return S


def run_rule(P, ul, hyp, part, cond, ctx, target, exp_dir, primary, decision="TCLOSE(t)"):
    rows = P.index[(P["split"] == "discovery") & P["usable"] & P[f"ctx_{ctx}"]]
    sig = cond_mask(P, [c[:3] for c in cond])
    r = rate_test(P, rows, sig, target)
    return dict(part=part, hyp=hyp, ul=ul, context=ctx, target=target, rule=cond_text([c[:3] for c in cond]),
                cond_json=json.dumps(cond), decision=decision, expected_dir=exp_dir, primary=primary, **r)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    ev_rows, sh_rows, tests, qinfo = [], [], [], []
    for ul in ULS:
        P = build_features(ul)
        positions(P, ul)
        Q = disc_quantiles(P, QCOLS)
        qt = add_quantile_targets(P, Q)
        qinfo.append(dict(ul=ul, **qt))
        P.to_parquet(OUT / f"features_{ul}.parquet")
        # ---- Part A
        r, s = event_study(P, ul, rng)
        ev_rows += r
        sh_rows += s
        # ---- Part B
        for hyp, cond, ctxs, targets, ed, prim_q, prim_t in rule_specs(Q):
            for ctx in ctxs:
                for tg in targets:
                    prim = bool(prim_q and tg in prim_t and ctx in ("W0", "M0"))
                    tests.append(run_rule(P, ul, hyp, "B", cond, ctx, tg, ed, prim))
        # ---- Part C single tails
        singles = []
        for f in CANDLE + T1515:
            if f in T1515:
                tlist = ["t_gap_up"]
                dec = "T1515(t)"
            else:
                tlist = ["t_gap_up", "t_oc_up", "t_ret30_up", "t_big"]
                dec = "TCLOSE(t)"
            tails = [[[f, "<=", Q[f][0.2], 0.2]], [[f, ">=", Q[f][0.8], 0.8]]]
            for cond in tails:
                for ctx in ["ALL", "X", "W0", "M0"]:
                    for tg in tlist:
                        t = run_rule(P, ul, f"C_{f}", "C1", cond, ctx, tg, 0, False, dec)
                        tests.append(t)
                        singles.append(t)
        for cond in ([["f_streak_close", "<=", -3.0, None]], [["f_streak_close", ">=", 3.0, None]]):
            for ctx in ["ALL", "X", "W0", "M0"]:
                for tg in ["t_gap_up", "t_oc_up", "t_ret30_up", "t_big"]:
                    t = run_rule(P, ul, "C_f_streak_close", "C1", cond, ctx, tg, 0, False)
                    tests.append(t)
                    singles.append(t)
        # ---- Part C pairs (built from discovery singles with raw p < 0.05, TCLOSE features only)
        S = pd.DataFrame(singles)
        S = S[(S["decision"] == "TCLOSE(t)") & (S["p"] < 0.05) & (S["n"] >= 30)]
        for (ctx, tg), g in S.groupby(["context", "target"]):
            g = g.sort_values("p").head(4)
            conds = [json.loads(c) for c in g["cond_json"]]
            for a, b in combinations(conds, 2):
                if a[0][0] == b[0][0]:
                    continue
                tests.append(run_rule(P, ul, f"C2_{a[0][0]}&{b[0][0]}", "C2", a + b, ctx, tg, 0, False))
        print(ul, "tests so far", len(tests))
    for r in sh_rows:
        r.pop("draws")
    EV = pd.DataFrame(ev_rows + sh_rows)
    EV.to_csv(OUT / "eventstudy.csv", index=False)
    pd.DataFrame(sh_rows).to_csv(OUT / "placebo_shuffle.csv", index=False)
    pd.DataFrame(qinfo).to_csv(OUT / "quantile_targets.csv", index=False)
    T = pd.DataFrame(tests)
    # ---- hypothesis log: event tests + rule tests, one BH family
    EVh = EV.copy()
    EVh["part"] = "A"
    EVh["hyp"] = "A_" + EVh["kind"] + "_" + EVh["metric"]
    EVh["context"] = EVh["kind"] + "_D" + EVh["pos"].map(lambda k: f"{k:+d}" if k else "0")
    EVh["target"] = EVh["metric"]
    EVh["rule"] = "position " + EVh["context"] + " vs " + EVh["comparison"]
    EVh["decision"] = "descriptive"
    EVh["effect"] = EVh["diff"]
    EVh["rate"] = EVh["value"]
    EVh["base"] = EVh["comp_value"]
    H = pd.concat([EVh, T], ignore_index=True, sort=False)
    H["small_n"] = H["n"] < 30
    q, rej = bh(H["p"].values, 0.10)
    H["bh_q"] = q
    H["bh_sig"] = rej
    H.insert(0, "test_id", [f"PP{i:04d}" for i in range(len(H))])
    H.to_csv(OUT / "hypotheses.csv", index=False)
    print("family size", int(H["p"].notna().sum()), "BH-significant", int(H["bh_sig"].sum()),
          "with n>=30", int((H["bh_sig"] & ~H["small_n"]).sum()))
    # ---- freeze
    sig = H[H["bh_sig"] & ~H["small_n"]].copy()
    sig = sig[sig["kind"].fillna("") != "weekly_placebo_2018"]
    sig["why"] = "Suggestive (BH q <= 0.10)"
    prim = H[(H["primary"] == True) & ~H["test_id"].isin(sig["test_id"])].copy()  # noqa: E712
    prim["why"] = "primary listed hypothesis (frozen regardless of significance)"
    F = pd.concat([sig, prim], ignore_index=True)
    F["type"] = np.where(F["part"] == "A", "event", "rule")
    F["direction"] = np.sign(F["effect"])
    F["id"] = [f"PPC{i:03d}" for i in range(len(F))]
    keep = ["id", "test_id", "type", "why", "part", "hyp", "ul", "kind", "pos", "metric", "stat", "comparison",
            "context", "target", "rule", "cond_json", "decision", "direction", "n", "rate", "base", "effect", "p",
            "bh_q", "ci_lo", "ci_hi"]
    F = F[[c for c in keep if c in F.columns]]
    F.to_csv(OUT / "candidates_frozen.csv", index=False)
    print("frozen candidates", len(F), "of which Suggestive", int((F["why"].str.startswith("Suggestive")).sum()))


if __name__ == "__main__":
    main()
