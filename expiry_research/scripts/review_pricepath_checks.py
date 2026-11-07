"""review_pricepath: independent skeptical checks of the pricepath module (design: reports/lld/review_pricepath.md).

Own code from panel_io.load_panel only (pricepath code is NOT imported). Reads pricepath's frozen / validation CSVs
to know which rules to check and what they claimed. Writes results/review_pricepath/*.csv. Open period only.
Run (Git Bash, from C:/Users/sherw/project-f-0):
  INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe expiry_research/scripts/review_pricepath_checks.py
"""
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel_io import load_panel  # noqa: E402
from stats_utils import bh, binom_p, mean_ci, two_prop, wilson  # noqa: E402

ROOT = HERE.parent
PP = ROOT / "results" / "pricepath"
OUT = ROOT / "results" / "review_pricepath"
SEED = 20261107
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 400)
LOG = []  # review hypothesis log


def logt(name, ul, split, n, effect, p, note=""):
    LOG.append(dict(test=name, ul=ul, split=split, n=n, effect=effect, p=p, note=note))


# ------------------------------------------------------------------ features (own code)
def streak(sign):
    out = np.zeros(len(sign))
    for i, s in enumerate(sign):
        if np.isnan(s) or s == 0:
            out[i] = 0
        elif i and np.sign(out[i - 1]) == s:
            out[i] = out[i - 1] + s
        else:
            out[i] = s
    return out


def build(ul):
    P = load_panel(ul).sort_values("date").reset_index(drop=True)
    assert P["date"].max() < "2024-07-01"
    o, h, l, c = P["px_open"], P["px_high"], P["px_low"], P["px_close"]
    pc = c.shift(1)
    M = pd.DataFrame(index=P.index)
    M["o_cc"] = (c / pc - 1) * 100
    M["o_range_pct"] = (h - l) / pc * 100
    M["o_gap_pct"] = (o / pc - 1) * 100
    M["f_mom5"] = (c / c.shift(5) - 1) * 100
    # the dictionary says "20 sessions ending at t - 1"; the panel actually uses t-19..t (t's own high / low, still
    # known at TCLOSE(t)). Both are computed; the panel's definition is used for the rules (the frozen thresholds
    # were set on it). The t-1 version is kept only for the definition check.
    M["f_dist_low20"] = (c / l.rolling(20).min() - 1) * 100
    M["f_dist_high20"] = (c / h.rolling(20).max() - 1) * 100
    M["f_dist_low20_dict_def"] = (c / l.shift(1).rolling(20).min() - 1) * 100
    M["f_dist_high20_dict_def"] = (c / h.shift(1).rolling(20).max() - 1) * 100
    M["f_vix_chg1"] = (P["f_vix_close"] / P["f_vix_close"].shift(1) - 1) * 100
    fv = P["f_fut_vol"]
    M["f_fut_vol_r20"] = fv / fv.shift(1).rolling(20, min_periods=15).mean()
    M["f_streak_close"] = streak(np.sign(M["o_cc"].values))
    # compare with the panel's own columns (leakage / definition check)
    chk = []
    for col in M.columns:
        a, b = M[col], P[col.replace("_dict_def", "")]
        both = a.notna() & b.notna()
        d = (a[both] - b[both]).abs()
        chk.append(dict(ul=ul, column=col, rows_compared=int(both.sum()), max_abs_diff=float(d.max()),
                        rows_diff_gt_1e6=int((d > 1e-6).sum()), panel_only=int((b.notna() & a.isna()).sum())))
    # label identity: y_max_exc(t) == o_max_exc(t+1)
    yid = (P["y_max_exc"] - P["o_max_exc"].shift(-1)).abs()
    chk.append(dict(ul=ul, column="y_max_exc == next o_max_exc", rows_compared=int(yid.notna().sum()),
                    max_abs_diff=float(yid.max()), rows_diff_gt_1e6=int((yid > 1e-6).sum()), panel_only=0))
    # use my recomputations where I have them; the panel elsewhere
    F = P.copy()
    for col in [x for x in M.columns if not x.endswith("_dict_def")]:
        F[col] = M[col].where(M[col].notna(), P[col])  # first rows: panel uses pre-2018 history
    F["usable"] = ~F["split_edge"].astype(bool) & ~F["cal_special_between"].fillna(False).astype(bool)
    F["t_big"] = (F["y_max_exc"] >= 1).astype(float).where(F["y_max_exc"].notna())
    yo = 1 + F["y_gap_pct"] / 100
    hi_o = (1 + F["y_high_vs_prevclose"] / 100) / yo - 1
    lo_o = 1 - (1 + F["y_low_vs_prevclose"] / 100) / yo
    F["y_exc_open"] = np.maximum(hi_o, lo_o) * 100
    F["t_big_open"] = (F["y_exc_open"] >= 1).astype(float).where(F["y_exc_open"].notna())
    F["t_gap1"] = (F["y_gap_pct"].abs() >= 1).astype(float).where(F["y_gap_pct"].notna())
    F["year"] = F["date"].str[:4].astype(int)
    for k, v in {"W0": "weekly", "M0": "monthly", "X": "none"}.items():
        F[f"ctx_{k}"] = F["cal_next_kind"] == v
    F["ctx_ALL"] = True
    rng = h - l
    F["nr4"] = (rng <= rng.rolling(4).min()).astype(float).where(rng.rolling(4).count() == 4)
    F["atr14"] = F["f_atr14_pct"]
    return F, pd.DataFrame(chk)


def mask(F, cond):
    m = pd.Series(True, index=F.index)
    for col, op, v in cond:
        x = F[col]
        m &= x.notna() & ({">=": x >= v, "<=": x <= v, "==": x == v}[op])
    return m


def rate(F, rows, sig, target):
    y = F.loc[rows, target].dropna()
    s = sig.loc[y.index]
    n_b, k_b = len(y), int(y.sum())
    base = k_b / n_b if n_b else np.nan
    n, k = int(s.sum()), int(y[s].sum())
    r, lo, hi = wilson(k, n)
    return dict(n=n, k=k, rate=r, lo=lo, hi=hi, base=base, n_base=n_b, effect=r - base if n else np.nan)


def p1(k, n, p0, d):
    if n == 0 or np.isnan(p0):
        return np.nan
    return float(stats.binomtest(int(k), int(n), p0, alternative="greater" if d > 0 else "less").pvalue)


def rows_of(F, split, ctx, extra=None):
    m = F["usable"] & F[f"ctx_{ctx}"]
    if split == "dv":
        m &= F["split"].isin(["discovery", "validation"])
    else:
        m &= F["split"] == split
    if extra is not None:
        m &= extra
    return F.index[m]


# ------------------------------------------------------------------ logistic (IRLS, no statsmodels in the venv)
def logit_fit(X, y, iters=50):
    X = np.column_stack([np.ones(len(X)), X])
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ b))
        W = p * (1 - p)
        g = X.T @ (y - p)
        Hm = X.T @ (X * W[:, None])
        step = np.linalg.solve(Hm + 1e-9 * np.eye(len(b)), g)
        b += step
        if np.abs(step).max() < 1e-10:
            break
    return b


def logit_pred(b, X):
    X = np.column_stack([np.ones(len(X)), X])
    return 1 / (1 + np.exp(-X @ b))


def vol_X(F, idx):
    return np.column_stack([np.log(F.loc[idx, "f_vix_close"].values), np.log(F.loc[idx, "atr14"].values)])


# ------------------------------------------------------------------ main checks
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FR = pd.read_csv(PP / "candidates_frozen.csv")
    VA = pd.read_csv(PP / "validation.csv")
    lab = VA.set_index("id")["label"]
    target_ids = sorted(lab[lab.isin(["Suggestive", "Passed-validation"])].index)
    print("candidates under review:", len(target_ids), lab[target_ids].value_counts().to_dict())

    FF, CHK = {}, []
    for ul in ("NIFTY", "BANKNIFTY"):
        F, chk = build(ul)
        FF[ul] = F
        CHK.append(chk)
    CHK = pd.concat(CHK)

    # ---- 1b thresholds: discovery quantiles recomputed; validation rows never enter
    th = []
    for _, c in FR[FR["type"] == "rule"].iterrows():
        F = FF[c["ul"]]
        D = F[F["split"] == "discovery"]
        for col, op, v, q in json.loads(c["cond_json"]):
            if q is None:
                continue
            mine = float(D[col].quantile(q)) if col in D else np.nan
            dv_q = float(F[F["split"].isin(["discovery", "validation"])][col].quantile(q)) if col in F else np.nan
            th.append(dict(id=c["id"], ul=c["ul"], col=col, q=q, frozen=v, mine_disc=mine, disc_plus_val=dv_q,
                           match_disc=abs(v - mine) < 1e-6 * max(1, abs(v)) if not np.isnan(mine) else None))
    TH = pd.DataFrame(th)
    CHK = pd.concat([CHK, pd.DataFrame([dict(ul="both", column="frozen thresholds == discovery quantile (own)",
                                             rows_compared=int(TH["match_disc"].notna().sum()),
                                             max_abs_diff=float((TH["frozen"] - TH["mine_disc"]).abs().max()),
                                             rows_diff_gt_1e6=int((TH["match_disc"] == False).sum()),  # noqa
                                             panel_only=0)])])
    # condition columns by decision time
    late_o = {"o_cc", "o_oc", "o_range_pct", "o_max_exc", "o_last_hour", "o_rv", "o_high_min", "o_low_min",
              "o_gap_filled"}
    bad = []
    for _, c in FR[FR["type"] == "rule"].iterrows():
        for col, *_ in json.loads(c["cond_json"]):
            if col.startswith(("y_", "t_")) or (c["decision"] == "T1515(t)" and (col in late_o or
                                                                                    not col.startswith("f1515_"))):
                bad.append((c["id"], col))
            if col.startswith("cal_"):
                bad.append((c["id"], col + " (calendar: check re-dating)"))
    CHK = pd.concat([CHK, pd.DataFrame([dict(ul="both", column="condition columns violating decision time",
                                             rows_compared=int((FR["type"] == "rule").sum()),
                                             max_abs_diff=np.nan, rows_diff_gt_1e6=len(bad), panel_only=0)])])
    CHK.to_csv(OUT / "leakage_checks.csv", index=False)
    TH.to_csv(OUT / "threshold_checks.csv", index=False)
    print(CHK.to_string(index=False))
    print("bad condition columns:", bad)

    # ---- 2 recompute + 6 tradeable + vol-adjusted + 5 robustness for every reviewed rule
    REC, TRD, VOL, ROB = [], [], [], []
    models = {}
    for ul, F in FF.items():
        for tg in ("t_big", "t_big_open"):
            for sp in ("discovery", "validation"):
                idx = rows_of(F, sp, "ALL")
                idx = idx[F.loc[idx, tg].notna() & F.loc[idx, "f_vix_close"].notna() & F.loc[idx, "atr14"].notna()]
                models[(ul, tg, sp)] = logit_fit(vol_X(F, idx), F.loc[idx, tg].values)
    for cid in target_ids:
        c = FR.set_index("id").loc[cid]
        v = VA.set_index("id").loc[cid]
        if c["type"] != "rule":
            continue
        F = FF[c["ul"]]
        cond = [x[:3] for x in json.loads(c["cond_json"])]
        sig = mask(F, cond)
        d = float(np.sign(c["effect"]))
        rd = rate(F, rows_of(F, "discovery", c["context"]), sig, c["target"])
        rv = rate(F, rows_of(F, "validation", c["context"]), sig, c["target"])
        pd_ = binom_p(rd["k"], rd["n"], rd["base"])
        pv = p1(rv["k"], rv["n"], rv["base"], d)
        passed = (rv["n"] >= 10 and np.sign(rv["effect"]) == d and pv < 0.05
                  and abs(rv["effect"]) >= 0.5 * abs(rd["effect"]))
        REC.append(dict(id=cid, ul=c["ul"], ctx=c["context"], rule=c["rule"], label=lab[cid],
                        disc_n_theirs=c["n"], disc_n=rd["n"], disc_rate_theirs=c["rate"], disc_rate=rd["rate"],
                        disc_base=rd["base"], disc_eff=rd["effect"], disc_p=pd_, disc_p_theirs=c["p"],
                        val_n_theirs=v["val_n"], val_n=rv["n"], val_rate_theirs=v["val_rate"], val_rate=rv["rate"],
                        val_lo=rv["lo"], val_hi=rv["hi"], val_base=rv["base"], val_eff=rv["effect"], val_p1=pv,
                        val_p1_theirs=v["val_p_one_sided"], pass_mine=bool(passed) if rv["n"] >= 10 else None))
        logt(f"{cid} recompute disc", c["ul"], "discovery", rd["n"], rd["effect"], pd_)
        if rv["n"] >= 10:
            logt(f"{cid} recompute val (one-sided)", c["ul"], "validation", rv["n"], rv["effect"], pv)
        # tradeable target (from the t+1 open) and gap-only
        for tg in ("t_big_open", "t_gap1"):
            a = rate(F, rows_of(F, "discovery", c["context"]), sig, tg)
            b = rate(F, rows_of(F, "validation", c["context"]), sig, tg)
            pa = binom_p(a["k"], a["n"], a["base"])
            pb = p1(b["k"], b["n"], b["base"], d)
            TRD.append(dict(id=cid, ul=c["ul"], ctx=c["context"], target=tg, disc_n=a["n"], disc_rate=a["rate"],
                            disc_base=a["base"], disc_eff=a["effect"], disc_p=pa, val_n=b["n"], val_rate=b["rate"],
                            val_lo=b["lo"], val_hi=b["hi"], val_base=b["base"], val_eff=b["effect"], val_p1=pb))
            logt(f"{cid} {tg} disc", c["ul"], "discovery", a["n"], a["effect"], pa)
            if b["n"] >= 10:
                logt(f"{cid} {tg} val", c["ul"], "validation", b["n"], b["effect"], pb)
        # volatility-adjusted: observed vs logistic(log VIX, log ATR) expected on signal rows
        for tg in ("t_big", "t_big_open"):
            for sp in ("discovery", "validation"):
                idx = rows_of(F, sp, c["context"])
                idx = idx[F.loc[idx, tg].notna() & F.loc[idx, "f_vix_close"].notna() & F.loc[idx, "atr14"].notna()]
                s_idx = idx[sig.loc[idx].values]
                if len(s_idx) == 0:
                    continue
                for fit in (("discovery", "validation") if sp == "validation" else ("discovery",)):
                    pr = logit_pred(models[(c["ul"], tg, fit)], vol_X(F, s_idx))
                    k = F.loc[s_idx, tg].sum()
                    E, var = pr.sum(), (pr * (1 - pr)).sum()
                    z = (k - E) / math.sqrt(var) if var > 0 else np.nan
                    pz = (2 * stats.norm.sf(abs(z)) if sp == "discovery" else
                          float(stats.norm.sf(z * d))) if not np.isnan(z) else np.nan
                    VOL.append(dict(id=cid, ul=c["ul"], ctx=c["context"], target=tg, split=sp, model_fit_on=fit,
                                    n=len(s_idx), obs_rate=k / len(s_idx), exp_rate=E / len(s_idx),
                                    excess=(k - E) / len(s_idx), z=z, p=pz))
                    logt(f"{cid} voladj {tg} fit={fit}", c["ul"], sp, len(s_idx), (k - E) / len(s_idx), pz)
        # robustness on discovery + validation
        dvr = rows_of(F, "dv", c["context"])
        base_r = rate(F, dvr, sig, c["target"])
        ROB.append(dict(id=cid, check="all_dv", group="all", **base_r))
        for yr, g in F.loc[dvr].groupby("year").groups.items():
            ROB.append(dict(id=cid, check="year", group=str(yr), **rate(F, g, sig, c["target"])))
        ROB.append(dict(id=cid, check="excl_2020", group="no 2020",
                        **rate(F, dvr[F.loc[dvr, "year"].values != 2020], sig, c["target"])))
        cut = F.loc[dvr, "y_max_exc"].quantile(0.99)
        ROB.append(dict(id=cid, check="excl_top1pct_y_max_exc", group=f"y_max_exc < {cut:.2f}",
                        **rate(F, dvr[(F.loc[dvr, "y_max_exc"] < cut).values], sig, c["target"])))
        vt = pd.qcut(F.loc[F["split"].isin(["discovery", "validation"]), "f_vix_close"], 3,
                     labels=["low", "mid", "high"]).reindex(F.index)
        for g in ("low", "mid", "high"):
            ROB.append(dict(id=cid, check="vix_tercile", group=g, **rate(F, dvr[(vt.loc[dvr] == g).values], sig,
                                                                           c["target"])))
        # neighbours (discovery quantile +- 0.05 / 0.10; streak +- 1)
        raw = json.loads(c["cond_json"])
        D = F[F["split"] == "discovery"]
        for i, (col, op, val, q) in enumerate(raw):
            alts = []
            if q is not None:
                alts = [(f"q{q + dq:.2f}", float(D[col].quantile(round(q + dq, 2)))) for dq in (-.1, -.05, .05, .1)]
            elif col == "f_streak_close":
                alts = [(str(val - 1), val - 1), (str(val + 1), val + 1)]
            for tag, a in alts:
                c2 = [x[:3] for x in raw]
                c2[i] = [col, op, a]
                ROB.append(dict(id=cid, check="neighbour", group=f"{col} {op} {tag}",
                                **rate(F, dvr, mask(F, c2), c["target"])))
    REC, TRD, VOL, ROB = map(pd.DataFrame, (REC, TRD, VOL, ROB))
    REC.to_csv(OUT / "recompute.csv", index=False)
    TRD.to_csv(OUT / "tradeable_target.csv", index=False)
    VOL.to_csv(OUT / "vol_adjusted.csv", index=False)
    ROB.to_csv(OUT / "robustness.csv", index=False)
    print("\n== recompute (theirs vs mine)")
    print(REC[["id", "ul", "ctx", "label", "disc_n_theirs", "disc_n", "disc_rate_theirs", "disc_rate", "val_n_theirs",
               "val_n", "val_rate_theirs", "val_rate", "val_base", "val_p1_theirs", "val_p1", "pass_mine"]]
          .round(4).to_string(index=False))
    print("\n== tradeable (from t+1 open) and gap>=1 %")
    print(TRD.round(4).to_string(index=False))
    print("\n== vol-adjusted")
    print(VOL.round(4).to_string(index=False))

    # ---- PPC009 deep check (own shuffle)
    ppc009(FF["NIFTY"])
    # ---- spot checks of Rejected / Observed
    spot(FF)
    # ---- freeze order + family
    freeze_family()
    # ---- review log with BH over the review family
    L = pd.DataFrame(LOG)
    q, rej = bh(L["p"].values, 0.10)
    L["bh_q"], L["bh_sig"] = q, rej
    L.to_csv(OUT / "review_hypotheses.csv", index=False)
    print("\nreview family size", int(L["p"].notna().sum()))


def anchors(F):
    A = [(i, F.at[i, "cal_kind"]) for i in np.where(F["cal_kind"].isin(["weekly", "monthly"]))[0]]
    pre = F[F["date"] < "2019-02-11"].copy()
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
    A["date"] = F.loc[A["i"], "date"].values
    A["month"] = A["date"].str[:7]
    return A


def shuffle_p(vals, real_rows, pools, k, rng, nd=2000, drop_rows=()):
    real_rows = [r for r in real_rows if r not in drop_rows]
    real = np.nanmean(vals[real_rows])
    months = [m for m in pools if len(pools[m])]
    draws = np.empty(nd)
    for r in range(nd):
        idx = np.array([rng.choice(pools[m]) for m in months]) + k
        idx = idx[(idx >= 0) & (idx < len(vals))]
        idx = np.array([i for i in idx if i not in drop_rows])
        draws[r] = np.nanmean(vals[idx])
    two = min(1.0, 2 * min((draws >= real).mean(), (draws <= real).mean()) + 1 / nd)
    one_lo = (draws <= real).mean() + 1 / nd
    return real, draws.mean(), np.quantile(draws, .025), np.quantile(draws, .975), two, one_lo


def ppc009(F):
    rng = np.random.default_rng(SEED)
    A = anchors(F)
    k = -3
    vals = F["o_cc"].values
    rows = []
    any_mo = np.zeros(len(F), bool)
    for kk in range(-5, 1):
        any_mo |= (F["cal_sessions_to_monthly"] == -kk).values
    any_mo |= (F["cal_kind"].shift(1) == "monthly").values
    for sp, (a, b) in {"discovery": ("2018-01-01", "2022-12-31"), "validation": ("2023-01-01", "2024-06-30")}.items():
        Ad = A[(A["date"] >= a) & (A["date"] <= b)]
        months = sorted(Ad.loc[Ad["kind"] == "monthly", "month"].unique())
        pools = {m: Ad.loc[(Ad["month"] == m) & (Ad["kind"] != "monthly"), "i"].values for m in months}
        real_rows = list(F.index[(F["split"] == sp) & (F["cal_sessions_to_monthly"] == 3)])
        variants = {"as_frozen": (), "drop_2020-03-23": tuple(F.index[F["date"] == "2020-03-23"]),
                    "drop_march_2020": tuple(F.index[F["date"].str[:7] == "2020-03"])}
        for name, drop in variants.items():
            if sp == "validation" and name != "as_frozen":
                continue
            pl = {m: (p if name != "drop_march_2020" or m != "2020-03" else np.array([], int)) for m, p in pools.items()}
            real, mdraw, lo, hi, two, one = shuffle_p(vals, real_rows, pl, k, rng, drop_rows=drop)
            rows.append(dict(split=sp, test="calendar_shuffle", variant=name, n=len([r for r in real_rows
                                                                                       if r not in drop]),
                             value=real, comp=mdraw, diff=real - mdraw, placebo_lo=lo, placebo_hi=hi,
                             p_two=two, p_one_lower=one))
            logt(f"PPC009 shuffle {name}", "NIFTY", sp, len(real_rows), real - mdraw, two if sp == "discovery" else one)
        # Welch vs matched non-monthly weeks (same k before a non-monthly anchor, not a monthly position)
        mt = np.zeros(len(F), bool)
        for _, r in Ad[Ad["kind"] != "monthly"].iterrows():
            j = int(r["i"]) + k
            if 0 <= j < len(F) and not any_mo[j]:
                mt[j] = True
        x = F.loc[real_rows, "o_cc"].dropna()
        y = F.loc[mt & (F["split"] == sp).values, "o_cc"].dropna()
        for name, xx in {"as_frozen": x, "drop_2020-03-23": x[F.loc[x.index, "date"] != "2020-03-23"]}.items():
            if sp == "validation" and name != "as_frozen":
                continue
            pw = float(stats.ttest_ind(xx, y, equal_var=False).pvalue)
            pw1 = float(stats.ttest_ind(xx, y, equal_var=False, alternative="less").pvalue)
            pmw = float(stats.mannwhitneyu(xx, y, alternative="two-sided" if sp == "discovery" else "less").pvalue)
            m, lo, hi = mean_ci(xx.values)
            rows.append(dict(split=sp, test="welch_vs_matched", variant=name, n=len(xx), value=xx.mean(),
                             comp=y.mean(), diff=xx.mean() - y.mean(), placebo_lo=lo, placebo_hi=hi,
                             p_two=pw, p_one_lower=pw1, median=xx.median(), comp_median=y.median(), p_mannwhitney=pmw,
                             neg_rate=(xx < 0).mean(), comp_neg_rate=(y < 0).mean(),
                             p_negrate=two_prop(int((xx < 0).sum()), len(xx), int((y < 0).sum()), len(y)),
                             n_comp=len(y)))
            logt(f"PPC009 welch {name}", "NIFTY", sp, len(xx), xx.mean() - y.mean(), pw if sp == "discovery" else pw1)
            logt(f"PPC009 mannwhitney {name}", "NIFTY", sp, len(xx), xx.median() - y.median(), pmw)
        if sp == "discovery":
            wd = pd.to_datetime(F.loc[real_rows, "date"]).dt.day_name().value_counts().to_dict()
            print("PPC009 discovery D-3 weekdays", wd)
            print("PPC009 largest |o_cc| D-3 rows:\n", F.loc[real_rows, ["date", "o_cc"]].sort_values("o_cc").head(5)
                  .to_string(index=False))
        else:
            wd = pd.to_datetime(F.loc[real_rows, "date"]).dt.day_name().value_counts().to_dict()
            print("PPC009 validation D-3 weekdays", wd)
            print(F.loc[real_rows, ["date", "o_cc"]].to_string(index=False))
    # weekday composition, open-to-close (a TCLOSE / calendar trade enters at the D-3 open), seed sensitivity
    for sp in ("discovery", "validation"):
        rr = F[(F["split"] == sp) & (F["cal_sessions_to_monthly"] == 3)]
        wdn = pd.to_datetime(rr["date"]).dt.day_name()
        for wname, sub in (("Monday", rr[wdn == "Monday"]), ("not Monday", rr[wdn != "Monday"])):
            m, lo, hi = mean_ci(sub["o_cc"].values)
            rows.append(dict(split=sp, test="weekday_split_o_cc", variant=wname, n=len(sub), value=m,
                             placebo_lo=lo, placebo_hi=hi))
        x = rr["o_oc"].dropna()
        mtm = np.zeros(len(F), bool)
        lo_d, hi_d = (("2018-01-01", "2022-12-31") if sp == "discovery" else ("2023-01-01", "2024-06-30"))
        Ad = A[(A["date"] >= lo_d) & (A["date"] <= hi_d) & (A["kind"] != "monthly")]
        for _, r in Ad.iterrows():
            j = int(r["i"]) + k
            if 0 <= j < len(F) and not any_mo[j]:
                mtm[j] = True
        y = F.loc[mtm, "o_oc"].dropna()
        alt = "two-sided" if sp == "discovery" else "less"
        pw = float(stats.ttest_ind(x, y, equal_var=False, alternative=alt).pvalue)
        rows.append(dict(split=sp, test="welch_o_oc_vs_matched", variant="open-to-close of D-3", n=len(x),
                         value=x.mean(), comp=y.mean(), diff=x.mean() - y.mean(), p_two=pw if sp == "discovery"
                         else np.nan, p_one_lower=pw if sp != "discovery" else np.nan, n_comp=len(y)))
        logt(f"PPC009 o_oc welch", "NIFTY", sp, len(x), x.mean() - y.mean(), pw)
    Av = A[(A["date"] >= "2023-01-01") & (A["date"] <= "2024-06-30")]
    mv = sorted(Av.loc[Av["kind"] == "monthly", "month"].unique())
    pv = {m: Av.loc[(Av["month"] == m) & (Av["kind"] != "monthly"), "i"].values for m in mv}
    rv = list(F.index[(F["split"] == "validation") & (F["cal_sessions_to_monthly"] == 3)])
    ps = [shuffle_p(vals, rv, pv, k, np.random.default_rng(s_))[5] for s_ in range(10)]
    rows.append(dict(split="validation", test="calendar_shuffle_seed_spread", variant="10 seeds x 2000 draws",
                     n=len(rv), p_one_lower=float(np.median(ps)), placebo_lo=min(ps), placebo_hi=max(ps)))
    # per year: D-3 mean vs matched mean (all open years)
    yr = []
    for y_, g in F.groupby("year"):
        xs = g.loc[g["cal_sessions_to_monthly"] == 3, "o_cc"]
        yr.append(dict(split="by_year", test="mean_by_year", variant=str(y_), n=len(xs), value=xs.mean()))
    R = pd.concat([pd.DataFrame(rows), pd.DataFrame(yr)], ignore_index=True)
    R.to_csv(OUT / "ppc009_checks.csv", index=False)
    print("\n== PPC009")
    print(R.round(4).to_string(index=False))


def spot(FF):
    out = []
    # PPC007: BANKNIFTY weekly D0 persistence vs other sessions
    F = FF["BANKNIFTY"]
    s0, s1 = np.sign(F["o_cc"]), np.sign(F["o_cc"].shift(1))
    pers = pd.Series(np.where((s0 == 0) | (s1 == 0) | s0.isna() | s1.isna(), np.nan, (s0 == s1).astype(float)),
                     index=F.index)
    wk0 = (F["cal_upcoming_kind"] == "weekly") & (F["cal_sessions_to_expiry"] == 0)
    for sp in ("discovery", "validation"):
        m = F["split"] == sp
        x, y = pers[m & wk0].dropna(), pers[m & ~wk0].dropna()
        k1, n1, k2, n2 = int(x.sum()), len(x), int(y.sum()), len(y)
        pp = (k1 + k2) / (n1 + n2)
        z = (k1 / n1 - k2 / n2) / math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
        pv = two_prop(k1, n1, k2, n2) if sp == "discovery" else float(stats.norm.cdf(z))
        out.append(dict(id="PPC007", split=sp, n=n1, rate=k1 / n1, base=k2 / n2, effect=k1 / n1 - k2 / n2, p=pv))
        logt("PPC007 spot", "BANKNIFTY", sp, n1, k1 / n1 - k2 / n2, pv)
    # PPC007 by validation weekday regime
    for lab_, mm in {"val_thu_regime(<2023-09)": F["date"] < "2023-09-01",
                     "val_wed_regime(>=2023-09)": F["date"] >= "2023-09-01"}.items():
        m = (F["split"] == "validation") & mm
        x, y = pers[m & wk0].dropna(), pers[m & ~wk0].dropna()
        out.append(dict(id="PPC007", split=lab_, n=len(x), rate=x.mean(), base=y.mean(), effect=x.mean() - y.mean(),
                        p=two_prop(int(x.sum()), len(x), int(y.sum()), len(y))))
    # PPC146: NIFTY nr4 W0 -> t_big ; PPC059: NIFTY f1515_ret_open_to_1514 <= thr [X] -> gap up
    F = FF["NIFTY"]
    FR = pd.read_csv(PP / "candidates_frozen.csv").set_index("id")
    F["t_gap_up"] = np.where(F["y_gap_pct"].isna() | (F["y_gap_pct"] == 0), np.nan, (F["y_gap_pct"] > 0).astype(float))
    for cid, tg in (("PPC146", "t_big"), ("PPC059", "t_gap_up")):
        c = FR.loc[cid]
        cond = [x[:3] for x in json.loads(c["cond_json"])]
        sig = mask(F, cond)
        d = float(np.sign(c["effect"]))
        for sp in ("discovery", "validation"):
            r = rate(F, rows_of(F, sp, c["context"]), sig, tg)
            pv = binom_p(r["k"], r["n"], r["base"]) if sp == "discovery" else p1(r["k"], r["n"], r["base"], d)
            out.append(dict(id=cid, split=sp, n=r["n"], rate=r["rate"], base=r["base"], effect=r["effect"], p=pv,
                            rule=c["rule"], theirs_n=c["n"] if sp == "discovery" else None))
            logt(f"{cid} spot", "NIFTY", sp, r["n"], r["effect"], pv)
    S = pd.DataFrame(out)
    S.to_csv(OUT / "spot_checks.csv", index=False)
    print("\n== spot checks")
    print(S.round(4).to_string(index=False))


def freeze_family():
    fr, va = PP / "candidates_frozen.csv", PP / "validation.csv"
    sha = hashlib.sha256(fr.read_bytes()).hexdigest()
    V = pd.read_csv(va)
    rows = [dict(check="sha256 of frozen file == validation.csv frozen_sha256", value=sha[:16],
                 ok=set(V["frozen_sha256"]) == {sha[:16]})]
    names = ["reports/lld/pricepath.md", "scripts/pricepath_common.py", "scripts/pricepath_discovery.py",
             "results/pricepath/candidates_frozen.csv", "results/pricepath/hypotheses.csv",
             "scripts/pricepath_validate.py", "results/pricepath/validation.csv", "scripts/pricepath_extras.py"]
    for n in names:
        p = ROOT / n
        rows.append(dict(check=f"mtime {n}", value=pd.Timestamp(os.path.getmtime(p), unit="s", tz="UTC")
                         .tz_convert("Asia/Kolkata").strftime("%H:%M:%S.%f"), ok=None))
    H = pd.read_csv(PP / "hypotheses.csv", low_memory=False)
    exp = {"A": 7 * 7 * 4 + 7 * 7 * 3, "B": 2 * (14 * 2 + 14 * 2 + 4 * 4 * 2 + 2 * 5 * 2 + 2 * 4 + 3 * 4),
           "C1": 2 * (18 * 2 * 4 * 4 + 5 * 2 * 4 + 2 * 4 * 4)}
    for part, e in exp.items():
        got = int((H["part"] == part).sum())
        rows.append(dict(check=f"family rows part {part}: expected from script loops", value=f"{got} vs {e}",
                         ok=got == e))
    rows.append(dict(check="family rows part C2 (data-dependent pairs)", value=int((H["part"] == "C2").sum()),
                     ok=None))
    rows.append(dict(check="family size used for BH (p not NaN)", value=int(H["p"].notna().sum()), ok=None))
    q, rej = bh(H["p"].values, 0.10)
    rows.append(dict(check="BH recomputed == their bh_sig", value=int(rej.sum()),
                     ok=bool((rej == H["bh_sig"].astype(bool).values).all())))
    W = pd.DataFrame(rows)
    W.to_csv(OUT / "freeze_family_checks.csv", index=False)
    print("\n== freeze / family")
    print(W.to_string(index=False))


def overlap():
    """Pairwise overlap of validation signal days among the passed rules (are 22 passes 22 ideas?)."""
    FR = pd.read_csv(PP / "candidates_frozen.csv").set_index("id")
    VA = pd.read_csv(PP / "validation.csv")
    ids = list(VA.loc[(VA["label"] == "Passed-validation") & (VA["type"] == "rule"), "id"])
    out = []
    for ul in ("NIFTY", "BANKNIFTY"):
        F, _ = build(ul)
        val = F.index[(F["split"] == "validation") & F["usable"] & F["t_big"].notna()]
        S = {i: set(val[mask(F, [x[:3] for x in json.loads(FR.loc[i, "cond_json"])]).loc[val].values])
             for i in ids if FR.loc[i, "ul"] == ul and FR.loc[i, "context"] == "ALL"}
        union = set().union(*S.values())
        hits = int(F.loc[list(union), "t_big"].sum())
        out.append(dict(ul=ul, a="UNION of ALL-context passed rules", b="", n_a=len(union), n_b=len(val),
                        jaccard=np.nan, union_rate=hits / len(union), base=F.loc[val, "t_big"].mean()))
        for a in S:
            for b in S:
                if a < b:
                    j = len(S[a] & S[b]) / max(1, len(S[a] | S[b]))
                    out.append(dict(ul=ul, a=a, b=b, n_a=len(S[a]), n_b=len(S[b]), jaccard=j,
                                    share_a_in_b=len(S[a] & S[b]) / max(1, len(S[a]))))
    O = pd.DataFrame(out)
    O.to_csv(OUT / "overlap_validation_signals.csv", index=False)
    print("\n== overlap of validation signal days (ALL-context passed rules)")
    print(O.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
    overlap()
