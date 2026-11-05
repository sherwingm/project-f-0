"""Agent 5b: skeptical review of module optionchain (design: reports/lld/review_optionchain.md).

Rebuilds the passers' signals from load_panel with independent code, recomputes discovery / validation, tests
whether the chain signals add anything beyond public vol measures (VIX, hv10, range of t, calendar), runs
robustness splits and spot-checks two rejected / observed claims. Writes results/review_optionchain/.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel_io import load_panel  # noqa: E402
from stats_utils import bh, binom_p, wilson, block_boot_mean  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "results" / "review_optionchain"
OUT.mkdir(parents=True, exist_ok=True)
THEIRS = ROOT / "results" / "optionchain"
CUT = pd.Timestamp("2024-06-30")
VSTART = pd.Timestamp("2023-01-01")

# passers: cand, ul, ctx, signal, bucket, target
PASSERS = [
    ("OC01", "BANKNIFTY", "ALL", "iv", "hi", "range_big"),
    ("OC02", "NIFTY", "ALL", "iv", "hi", "range_big"),
    ("OC04", "NIFTY", "ALL", "iv", "hi", "big_move"),
    ("OC08", "BANKNIFTY", "ALL", "wall_width", "hi", "range_big"),
    ("OC10", "BANKNIFTY", "ALL", "iv", "hi", "gap_big"),
    ("OC11", "BANKNIFTY", "ALL", "wall_near", "hi", "range_big"),
    ("OC13", "NIFTY", "ALL", "wall_near", "hi", "range_big"),
    ("OC17", "NIFTY", "ALL", "wall_width", "hi", "range_big"),
    ("OC21", "NIFTY", "ALL", "wall_near", "hi", "big_move"),
    ("OC22", "BANKNIFTY", "ALL", "strad_chg", "lo", "big_move"),
    ("OC24", "BANKNIFTY", "ALL", "mp_abs", "hi", "range_big"),
    ("OC25", "NIFTY", "ALL", "wall_width", "hi", "big_move"),
    ("OC39", "NIFTY", "ALL", "wall_near", "lo", "range_big"),
    ("OC43", "NIFTY", "ALL", "strad_chg", "lo", "range_big"),
    ("OC52", "NIFTY", "ALL", "vol_surge", "hi", "range_big"),
    ("OC59", "NIFTY", "ALL", "strad_chg", "lo", "big_move"),
    ("OC94", "NIFTY", "NW", "wall_near", "hi", "big_move"),
    ("OC97", "BANKNIFTY", "NW", "wall_width", "hi", "range_big"),
    ("OC118", "BANKNIFTY", "ALL", "iv_chg", "hi", "range_big"),
]


# ---------------------------------------------------------------- features (my own code)
def build(ul):
    P = load_panel(ul).copy()
    P["date"] = pd.to_datetime(P["date"])
    assert P["date"].max() <= CUT
    P = P.sort_values("date").reset_index(drop=True)
    P["ne"] = pd.to_datetime(P["f_opt_near_expiry"])
    # sessions t+1..expiry, counted on the trading calendar of the panel itself where possible (my variant) and as
    # plain weekdays (their definition)
    d1 = (P["date"] + pd.Timedelta(days=1)).values.astype("datetime64[D]")
    e1 = (P["ne"] + pd.Timedelta(days=1)).values.astype("datetime64[D]")
    ok = P["ne"].notna().values
    nsw = np.full(len(P), np.nan)
    nsw[ok] = np.busday_count(d1[ok], e1[ok])
    P["n_sess"] = nsw
    S, K = P["px_close"], P["f_opt_near_atm_strike"]
    tv = P["f_opt_near_straddle_pct"] - (K / S - 1).abs() * 100
    P["iv"] = tv / 0.7979 / np.sqrt(P["n_sess"].clip(lower=1)) * np.sqrt(252)
    same = P["ne"].eq(P["ne"].shift(1))
    P["iv_chg"] = (P["iv"] - P["iv"].shift(1)).where(same)
    P["strad_chg"] = P["f_opt_near_straddle_chg1"]
    P["strad_chg_mine"] = (P["f_opt_near_straddle_pct"] - P["f_opt_near_straddle_pct"].shift(1)).where(same)
    P["wall_width"] = P["f_opt_near_callwall_dist_pct"] - P["f_opt_near_putwall_dist_pct"]
    P["wall_near"] = np.minimum(P["f_opt_near_callwall_dist_pct"], -P["f_opt_near_putwall_dist_pct"])
    P["mp_abs"] = P["f_opt_near_maxpain_dist_pct"].abs()
    vol = P["f_opt_near_ce_vol"] + P["f_opt_near_pe_vol"]
    # causal: for each row, median of the previous <=5 rows (strictly earlier dates) with the same n_sess
    vs = np.full(len(P), np.nan)
    hist = {}
    for i, (n, v) in enumerate(zip(P["n_sess"].values, vol.values)):
        h = hist.setdefault(n, [])
        if len(h) >= 3:
            vs[i] = v / np.median(h[-5:])
        h.append(v)
    P["vol_surge"] = vs
    P["regime"] = [("monthly_only_2018" if d < pd.Timestamp("2019-02-11") else "thu_weekly") if ul == "NIFTY" else
                   ("thu_weekly" if d < pd.Timestamp("2023-09-01") else "wed_weekly") for d in P["date"]]
    return P


def context(P, ctx):
    C = P[P["split_edge"] != True].copy()  # noqa: E712
    if ctx == "NW":
        C = C[C["cal_next_kind"] == "weekly"]
    C["tdate"] = pd.to_datetime(C["y_date"])
    C = C[C["tdate"].notna() & (C["tdate"] <= CUT)]
    tsp = np.where(C["tdate"] < VSTART, "discovery", "validation")
    C = C[tsp == C["split"].values].copy()
    return C


def target(C, tgt, med):
    if tgt == "range_big":
        v = C["y_range_pct"]
        return (v > med["range"]).astype(float).where(v.notna()), v
    if tgt == "gap_big":
        v = C["y_gap_pct"].abs()
        return (v > med["agap"]).astype(float).where(v.notna()), v
    if tgt == "big_move":
        v = C["y_max_exc"]
        b = C["y_big_move_exc"].astype(float)
        return b.where(v.notna()), v
    raise ValueError(tgt)


# ---------------------------------------------------------------- logistic regression (IRLS)
def logit_fit(X, y, ridge=1e-6, it=50):
    b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b))
        W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + ridge * np.eye(X.shape[1])
        g = X.T @ (y - p)
        step = np.linalg.solve(H, g)
        b += step
        if np.max(np.abs(step)) < 1e-9:
            break
    p = 1 / (1 + np.exp(-X @ b))
    H = X.T @ (X * (p * (1 - p))[:, None]) + ridge * np.eye(X.shape[1])
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return b, se


COV = ["lvix", "lhv10", "lrng_t", "absmom", "is_exp", "sess_to_exp", "dow_mon", "dow_tue", "dow_wed", "dow_thu"]


def design(C):
    X = pd.DataFrame(index=C.index)
    X["const"] = 1.0
    X["lvix"] = np.log(C["f_vix_close"])
    X["lhv10"] = np.log(C["f_hv10"].clip(lower=1))
    X["lrng_t"] = np.log(C["o_range_pct"].clip(lower=0.05))  # range of session t: known at TCLOSE(t)
    X["absmom"] = C["f_mom1"].abs()
    X["is_exp"] = (C["cal_next_is_expiry"] == True).astype(float)  # noqa: E712
    X["sess_to_exp"] = C["cal_next_sessions_to_expiry"].clip(upper=10)
    for d in ["mon", "tue", "wed", "thu"]:
        X["dow_" + d] = (C["tdate"].dt.day_name().str[:3].str.lower() == d).astype(float)
    return X


def excess(y, p, m):
    """bucket excess over the baseline, minus the non-bucket excess (removes period-level miscalibration)."""
    r = y - p
    a, b = r[m], r[~m]
    d = a.mean() - b.mean()
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)) if len(a) > 1 and len(b) > 1 else np.nan
    return d, se, (2 * stats.norm.sf(abs(d / se)) if se and se > 0 else np.nan), a.mean()


def main():
    feats = {ul: build(ul) for ul in ["NIFTY", "BANKNIFTY"]}
    th = pd.read_csv(THEIRS / "thresholds.csv")
    frozen = pd.read_csv(THEIRS / "candidates_frozen.csv")
    val = pd.read_csv(THEIRS / "validation.csv")
    LK, RC, INC, RB = [], [], [], []

    # ---------- leakage / reproduction checks
    for ul, P in feats.items():
        T = pd.read_parquet(THEIRS / f"features_{ul}.parquet")
        T["date"] = pd.to_datetime(T["date"])
        M = P.merge(T[["date", "iv", "iv_chg", "strad_chg", "wall_width", "wall_near", "mp_abs", "vol_surge"]],
                    on="date", suffixes=("", "_t"))
        for c in ["iv", "iv_chg", "strad_chg", "wall_width", "wall_near", "mp_abs", "vol_surge"]:
            d = (M[c] - M[c + "_t"]).abs()
            LK.append(dict(underlying=ul, check=f"reproduce_{c}", value=float(d.max()),
                           note=f"max |mine - theirs|; non-null mine {M[c].notna().sum()} theirs {M[c+'_t'].notna().sum()}"))
        d = (P["strad_chg"] - P["strad_chg_mine"]).abs()
        LK.append(dict(underlying=ul, check="panel_straddle_chg1_is_same_expiry_diff", value=float(d.max()),
                       note="f_opt_near_straddle_chg1 vs my straddle_pct diff with same near expiry"))
        # near expiry is after t (never t itself)
        LK.append(dict(underlying=ul, check="near_expiry_after_t", value=float((P["ne"] > P["date"]).mean()),
                       note="share of rows with near expiry > t"))
        nw = P[P["cal_next_kind"] == "weekly"]
        LK.append(dict(underlying=ul, check="NW_near_expiry_eq_tplus1", value=float(
            (nw["ne"] == pd.to_datetime(nw["y_date"])).mean()), note=f"NW rows {len(nw)}"))
        # correlation of signals with sessions-to-expiry and VIX (confounding)
        A = context(P, "ALL")
        for s in ["iv", "wall_width", "wall_near", "mp_abs", "strad_chg", "vol_surge", "iv_chg"]:
            for z in ["f_vix_close", "n_sess", "o_range_pct", "f_hv10"]:
                cc = A[[s, z]].dropna().corr(method="spearman").iloc[0, 1]
                LK.append(dict(underlying=ul, check=f"spearman_{s}_vs_{z}", value=float(cc), note="ALL disc+val"))
        # strad_chg vs weekday of t (weekend theta)
        g = A.groupby(A["date"].dt.day_name())["strad_chg"].mean()
        LK.append(dict(underlying=ul, check="strad_chg_mean_by_weekday_of_t", value=np.nan,
                       note="; ".join(f"{k[:3]} {v:.3f}" for k, v in g.items())))

    # ---------- per-candidate
    for cand, ul, ctx, sig, b, tgt in PASSERS:
        P = feats[ul]
        C = context(P, ctx)
        D = C[C["split"] == "discovery"]
        V = C[C["split"] == "validation"]
        med = {"range": float(D["y_range_pct"].median()), "agap": float(D["y_gap_pct"].abs().median())}
        x = D[sig].dropna()
        qs = {q: float(x.quantile(q)) for q in [0.2, 0.25, 1 / 3, 0.4, 0.6, 2 / 3, 0.7, 0.75, 0.8]}
        thr = qs[2 / 3] if b == "hi" else qs[1 / 3]
        tt = th[(th.underlying == ul) & (th.ctx == ctx) & (th.signal == sig)].iloc[0]
        tm = th[(th.underlying == ul) & (th.ctx == ctx) & (th.signal == "_target_median")].iloc[0]
        LK.append(dict(underlying=ul, check=f"{cand}_threshold_eq_disc_quantile",
                       value=float(abs(thr - (tt["q67"] if b == "hi" else tt["q33"]))),
                       note=f"mine {thr:.6g}; target median diff {abs(med['range']-tm['range']):.2g}"))

        def mask(F, t=thr):
            return (F[sig] >= t) if b == "hi" else (F[sig] <= t)

        def stat(F, t=thr, drop_q=None):
            y, v = target(F, tgt, med)
            base_rows = y.notna() & F[sig].notna()
            if drop_q is not None:  # drop the largest outcomes of ALL rows (bucket and base)
                cut = v[base_rows].quantile(1 - drop_q)
                base_rows &= ~(v > cut)
            m = mask(F, t) & base_rows
            n, k = int(m.sum()), int(y[m].sum())
            base = float(y[base_rows].mean())
            return n, k, (k / n if n else np.nan), base

        sgn = 1 if b == "hi" else -1
        # sign of the claimed effect: lo-bucket wall_near / OC39 is "smaller", strad_chg lo is "larger"
        fr = frozen[frozen.cand == cand].iloc[0]
        sgn = int(np.sign(fr["effect"]))
        for split, F in [("discovery", D), ("validation", V)]:
            n, k, r, base = stat(F)
            lo, hi = wilson(k, n)[1:]
            alt = "greater" if sgn > 0 else "less"
            p1 = stats.binomtest(k, n, base, alternative=alt).pvalue if n else np.nan
            RC.append(dict(cand=cand, underlying=ul, ctx=ctx, rule=f"{sig} {'>=' if b == 'hi' else '<='} {thr:.6g}",
                           target=tgt, split=split, n=n, k=k, rate=r, ci_lo=lo, ci_hi=hi, base=base,
                           effect=r - base, p_two_sided=binom_p(k, n, base), p_one_sided=p1, small_n=n < 30))
        vr = val[val.cand == cand].iloc[0]
        RC.append(dict(cand=cand, underlying=ul, ctx=ctx, rule="THEIRS", target=tgt, split="validation(theirs)",
                       n=vr["val_n"], k=vr["val_k"], rate=vr["val_rate"], base=vr["val_base"],
                       effect=vr["val_effect"], p_one_sided=vr["val_p_one_sided"]))
        mine_v = RC[-2]
        pass_mine = bool(np.sign(mine_v["effect"]) == sgn and mine_v["p_one_sided"] < 0.05 and
                         abs(mine_v["effect"]) >= 0.5 * abs(fr["effect"]))
        RC[-2]["pass_rule_mine"] = pass_mine

        # ---------- incremental value over public vol measures (baseline fit on discovery only)
        cols = ["f_vix_close", "f_hv10", "o_range_pct", "f_mom1", "cal_next_sessions_to_expiry", sig]
        Dm = D.dropna(subset=cols)
        Vm = V.dropna(subset=cols)
        yD, _ = target(Dm, tgt, med)
        yV, _ = target(Vm, tgt, med)
        okD, okV = yD.notna(), yV.notna()
        Dm, yD, Vm, yV = Dm[okD], yD[okD].to_numpy(), Vm[okV], yV[okV].to_numpy()
        XD, XV = design(Dm), design(Vm)
        bD, _ = logit_fit(XD.to_numpy(), yD)
        pD = 1 / (1 + np.exp(-XD.to_numpy() @ bD))
        pV = 1 / (1 + np.exp(-XV.to_numpy() @ bD))
        mD, mV = mask(Dm).to_numpy(), mask(Vm).to_numpy()
        row = dict(cand=cand, underlying=ul, ctx=ctx, signal=sig, bucket=b, target=tgt,
                   n_disc=int(mD.sum()), n_val=int(mV.sum()))
        for tag, y, p, m in [("disc", yD, pD, mD), ("val", yV, pV, mV)]:
            d, se, pv, ex_in = excess(y, p, m)
            row.update({f"{tag}_raw_effect": y[m].mean() - y.mean(), f"{tag}_resid_effect": d,
                        f"{tag}_resid_se": se, f"{tag}_resid_p": pv, f"{tag}_bucket_pred": p[m].mean(),
                        f"{tag}_bucket_obs": y[m].mean()})
        # logistic with the bucket dummy added, fit separately per period
        for tag, F, y in [("disc", Dm, yD), ("val", Vm, yV)]:
            X = design(F)
            X["bucket"] = mask(F).astype(float).to_numpy()
            try:
                bb, se = logit_fit(X.to_numpy(), y)
                row[f"{tag}_logit_bucket_coef"] = bb[-1]
                row[f"{tag}_logit_bucket_z"] = bb[-1] / se[-1]
                row[f"{tag}_logit_bucket_p"] = 2 * stats.norm.sf(abs(bb[-1] / se[-1]))
            except np.linalg.LinAlgError:
                row[f"{tag}_logit_bucket_coef"] = np.nan
        # simplest control: within VIX terciles AND range-of-t terciles (cut on discovery), pooled excess
        INC.append(row)

        # ---------- robustness on discovery + validation
        def add(check, grp, F, t=thr, drop_q=None):
            n, k, r, base = stat(F, t, drop_q)
            RB.append(dict(cand=cand, check=check, group=grp, n=n, rate=r, base=base, effect=r - base,
                           same_sign=bool(np.sign(r - base) == sgn) if n else False, small_n=n < 30))
        add("all", "disc+val", C)
        for dq in (0.01, 0.05):
            add("drop_top_outcomes", f"top{int(dq*100)}pct", C, drop_q=dq)
        for yr, g in C.groupby(C["date"].dt.year):
            add("year", str(yr), g)
        for rg, g in C.groupby("regime"):
            add("regime", rg, g)
        vt = pd.qcut(C["f_vix_close"], 3, labels=["vix_lo", "vix_mid", "vix_hi"])
        for vk, g in C.groupby(vt, observed=True):
            add("vix_tercile", str(vk), g)
        # VIX terciles cut on DISCOVERY only, validation rows only
        vq = D["f_vix_close"].quantile([1 / 3, 2 / 3]).to_numpy()
        vtv = np.digitize(V["f_vix_close"], vq)
        for kk, g in V.groupby(vtv):
            add("val_vix_tercile_disc_cuts", ["lo", "mid", "hi"][kk], g)
        # within range-of-t terciles (vol clustering control)
        rt = pd.qcut(C["o_range_pct"], 3, labels=["rng_t_lo", "rng_t_mid", "rng_t_hi"])
        for vk, g in C.groupby(rt, observed=True):
            add("range_t_tercile", str(vk), g)
        # t+1 is expiry vs not
        for k_, g in C.groupby(C["cal_next_is_expiry"] == True):  # noqa: E712
            add("t1_is_expiry", str(k_), g)
        for q in ([0.6, 0.7, 0.75, 0.8] if b == "hi" else [0.2, 0.25, 0.3, 0.4]):
            add("threshold", f"q{q:.2f}", C, t=float(x.quantile(q)))
    LK.append(dict(underlying="-", check="frozen_has_no_validation_columns",
                   value=float(any(c.startswith("val_") for c in frozen.columns)), note=",".join(frozen.columns)))
    for f in ["thresholds.csv", "hypotheses.csv", "candidates_frozen.csv", "validation.csv"]:
        LK.append(dict(underlying="-", check=f"mtime_{f}", value=(THEIRS / f).stat().st_mtime, note=""))
    H = pd.read_csv(THEIRS / "hypotheses.csv")
    LK.append(dict(underlying="-", check="family_rows_with_p", value=int(H["p"].notna().sum()),
                   note=f"expected 2 UL x 4 ctx x 192 bucket + 6 x 19 structural = {2*4*192 + 6*19}"))
    q, _ = bh(H["p"].fillna(1).to_numpy(), 0.10)
    LK.append(dict(underlying="-", check="bh_recomputed_max_abs_diff_q",
                   value=float(np.nanmax(np.abs(q[H['p'].notna()] - H.loc[H['p'].notna(), 'bh_q'].to_numpy()))),
                   note="NaN p set to 1 in my recompute only for the length; compared on non-NaN rows"))

    pd.DataFrame(LK).to_csv(OUT / "leak_checks.csv", index=False)
    pd.DataFrame(RC).to_csv(OUT / "recompute.csv", index=False)
    pd.DataFrame(INC).to_csv(OUT / "incremental.csv", index=False)
    RBd = pd.DataFrame(RB)
    RBd.to_csv(OUT / "robust.csv", index=False)

    # ---------- spot-checks of rejected / observed claims
    SP = []
    for ul, P in feats.items():
        A = P[(P["split_edge"] != True)].copy()  # noqa: E712
        A["S0"] = A["px_close_official"].fillna(A["px_close"])
        A["S1"] = A["S0"].shift(-1)
        A["S2"] = A["S0"].shift(-2)
        A["d1"] = pd.to_datetime(A["date"].shift(-1))
        A["d2"] = pd.to_datetime(A["date"].shift(-2))
        A = A[A["d1"] <= CUT]
        mp = A["f_opt_near_maxpain"]
        for split in ["discovery", "validation"]:
            Z = A[A["split"] == split]
            Z = Z[(Z["d1"] < VSTART) if split == "discovery" else (Z["d1"] >= VSTART)]
            ok = mp.loc[Z.index].notna() & (mp.loc[Z.index] != Z["S0"])
            closer = ((mp.loc[Z.index] - Z["S1"]).abs() < (mp.loc[Z.index] - Z["S0"]).abs())[ok & Z["S1"].notna()]
            nw = (Z["cal_next_kind"] == "weekly")[closer.index]
            k, n = int(closer[nw].sum()), int(nw.sum())
            base = float(closer.mean())
            SP.append(dict(claim="OBS-MP closer on weekly eve (t+1 close vs t close)", underlying=ul, split=split,
                           n=n, rate=k / n, base_all_rows=base, effect=k / n - base, p=binom_p(k, n, base)))
        # D-2 straddle: bought at settle on t (t+2 = near expiry), payoff at the official close of t+2
        Z = A[(A["cal_next_sessions_to_expiry"] == 1) & (A["ne"] == A["d2"]) & A["S2"].notna() & (A["d2"] <= CUT)]
        diff = (Z["S2"] - Z["f_opt_near_atm_strike"]).abs() / Z["px_close"] * 100 - Z["f_opt_near_straddle_pct"]
        for split in ["discovery", "validation"]:
            dd = diff[((Z["d2"] < VSTART) if split == "discovery" else (Z["d2"] >= VSTART)) & (Z["split"] == split)]
            dd = dd.dropna()
            m, lo, hi = block_boot_mean(dd.to_numpy(), block=3)
            SP.append(dict(claim="D-2 ATM straddle settle -> official close of expiry (payoff - cost, pp)",
                           underlying=ul, split=split, n=len(dd), rate=m, base_all_rows=0.0, effect=m,
                           p=float(stats.ttest_1samp(dd, 0).pvalue), ci_lo=lo, ci_hi=hi))
        # D-1 straddle
        Z = A[(A["cal_next_kind"] == "weekly") & (A["ne"] == A["d1"]) & A["S1"].notna()]
        diff = (Z["S1"] - Z["f_opt_near_atm_strike"]).abs() / Z["px_close"] * 100 - Z["f_opt_near_straddle_pct"]
        for split in ["discovery", "validation"]:
            dd = diff[((Z["d1"] < VSTART) if split == "discovery" else (Z["d1"] >= VSTART)) & (Z["split"] == split)]
            dd = dd.dropna()
            m, lo, hi = block_boot_mean(dd.to_numpy(), block=3)
            SP.append(dict(claim="D-1 weekly ATM straddle settle -> official close (payoff - cost, pp)",
                           underlying=ul, split=split, n=len(dd), rate=m, base_all_rows=0.0, effect=m,
                           p=float(stats.ttest_1samp(dd, 0).pvalue), ci_lo=lo, ci_hi=hi))
    pd.DataFrame(SP).to_csv(OUT / "spot_checks.csv", index=False)

    pd.set_option("display.width", 260)
    pd.set_option("display.max_rows", 500)
    pd.set_option("display.max_columns", 40)
    print(pd.DataFrame(LK).to_string())
    print(pd.DataFrame(RC)[["cand", "split", "n", "k", "rate", "base", "effect", "p_one_sided", "pass_rule_mine"]]
          .to_string())
    print(pd.DataFrame(INC).round(4).to_string())
    print(pd.DataFrame(SP).round(4).to_string())
    s = RBd[RBd.check != "all"].groupby(["cand", "check"]).apply(
        lambda g: f"{int(g.same_sign.sum())}/{len(g)} min_eff {g.effect.min():+.3f} max_eff {g.effect.max():+.3f}",
        include_groups=False)
    print(s.to_string())


if __name__ == "__main__":
    main()
