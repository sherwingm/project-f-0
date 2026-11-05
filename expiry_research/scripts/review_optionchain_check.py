"""Skeptical review of module optionchain (Agent 5b). Design: reports/lld/review_optionchain.md.

Rebuilds every passed-validation signal from the panels (panel_io.load_panel only), recomputes discovery and
validation numbers, robustness, and an incremental-information test against volatility controls. Spot-checks the
max-pain, OC139 and OC128 rejections. Writes results/review_optionchain/*.csv.
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
from stats_utils import binom_p, wilson, bh, block_boot_mean  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "results" / "review_optionchain"
OUT.mkdir(parents=True, exist_ok=True)
THEIRS = ROOT / "results" / "optionchain"
VAL0 = pd.Timestamp("2023-01-01")

# the 19 passers: (cand, ul, ctx, signal, bucket, target)
CANDS = [("OC01", "BANKNIFTY", "ALL", "iv", "hi", "range_big"), ("OC02", "NIFTY", "ALL", "iv", "hi", "range_big"),
         ("OC04", "NIFTY", "ALL", "iv", "hi", "big_move"), ("OC08", "BANKNIFTY", "ALL", "wall_width", "hi", "range_big"),
         ("OC10", "BANKNIFTY", "ALL", "iv", "hi", "gap_big"), ("OC11", "BANKNIFTY", "ALL", "wall_near", "hi", "range_big"),
         ("OC13", "NIFTY", "ALL", "wall_near", "hi", "range_big"), ("OC17", "NIFTY", "ALL", "wall_width", "hi", "range_big"),
         ("OC21", "NIFTY", "ALL", "wall_near", "hi", "big_move"), ("OC22", "BANKNIFTY", "ALL", "strad_chg", "lo", "big_move"),
         ("OC24", "BANKNIFTY", "ALL", "mp_abs", "hi", "range_big"), ("OC25", "NIFTY", "ALL", "wall_width", "hi", "big_move"),
         ("OC39", "NIFTY", "ALL", "wall_near", "lo", "range_big"), ("OC43", "NIFTY", "ALL", "strad_chg", "lo", "range_big"),
         ("OC52", "NIFTY", "ALL", "vol_surge", "hi", "range_big"), ("OC59", "NIFTY", "ALL", "strad_chg", "lo", "big_move"),
         ("OC94", "NIFTY", "NW", "wall_near", "hi", "big_move"), ("OC97", "BANKNIFTY", "NW", "wall_width", "hi", "range_big"),
         ("OC118", "BANKNIFTY", "ALL", "iv_chg", "hi", "range_big")]


# ---------------------------------------------------------------- features (own code)
def build(ul):
    P = load_panel(ul).copy()
    P["date"] = pd.to_datetime(P["date"])
    P = P.sort_values("date").reset_index(drop=True)
    E = pd.to_datetime(P["f_opt_near_expiry"])
    dates = P["date"].values
    # weekday count t+1..E (their definition) and real session count from the panel calendar
    nb = np.full(len(P), np.nan)
    nr = np.full(len(P), np.nan)
    last = P["date"].max()
    for i in range(len(P)):
        if pd.isna(E.iloc[i]):
            continue
        t, e = P["date"].iloc[i], E.iloc[i]
        nb[i] = np.busday_count((t + pd.Timedelta(days=1)).date(), (e + pd.Timedelta(days=1)).date())
        if e <= last:
            nr[i] = int(np.searchsorted(dates, np.datetime64(e), side="right") - (i + 1))
    P["n_bus"], P["n_real"] = nb, nr
    S, K, sp = P["px_close"], P["f_opt_near_atm_strike"], P["f_opt_near_straddle_pct"]
    tv = sp - (K / S - 1).abs() * 100
    P["iv"] = tv / math.sqrt(2 / math.pi) / np.sqrt(P["n_bus"].clip(lower=1)) * math.sqrt(252)
    P["iv_real"] = tv / math.sqrt(2 / math.pi) / np.sqrt(P["n_real"].clip(lower=1)) * math.sqrt(252)
    same = E.eq(E.shift(1))
    P["iv_chg"] = (P["iv"] - P["iv"].shift(1)).where(same)
    P["strad_chg_own"] = (sp - sp.shift(1)).where(same)
    P["strad_chg"] = P["f_opt_near_straddle_chg1"]
    cw, pw = P["f_opt_near_callwall_dist_pct"], P["f_opt_near_putwall_dist_pct"]
    P["wall_width"] = cw - pw
    P["wall_near"] = np.minimum(cw, -pw)
    P["mp_abs"] = P["f_opt_near_maxpain_dist_pct"].abs()
    vol = (P["f_opt_near_ce_vol"] + P["f_opt_near_pe_vol"]).to_numpy()
    vs = np.full(len(P), np.nan)
    hist = {}
    for i in range(len(P)):  # strictly earlier rows with the same weekday count
        k = nb[i]
        if np.isnan(k):
            continue
        h = hist.setdefault(k, [])
        prev = [v for v in h[-5:] if not np.isnan(v)]
        if len(h[-5:]) >= 3 and len(prev) >= 3:
            vs[i] = vol[i] / np.median(prev)
        h.append(vol[i])
    P["vol_surge"] = vs
    # controls known at TCLOSE(t)
    P["lvix"] = np.log(P["f_vix_close"])
    P["lrng"] = np.log(P["o_range_pct"].clip(lower=0.05))
    P["latr"] = np.log(P["f_atr14_pct"])
    P["lhv"] = np.log(P["f_hv10"].clip(lower=1))
    P["agap_t"] = P["o_gap_pct"].abs()
    P["dow_next"] = pd.to_datetime(P["cal_next_date"]).dt.dayofweek
    P["regime"] = [("monthly_only_2018" if d < pd.Timestamp("2019-02-11") else "thu_weekly") if ul == "NIFTY" else
                   ("thu_weekly" if d < pd.Timestamp("2023-09-01") else "wed_weekly") for d in P["date"]]
    P["close_off"] = P["px_close_official"].fillna(P["px_close"])
    P["close_off_t1"] = P["close_off"].shift(-1)
    P["close_off_t2"] = P["close_off"].shift(-2)
    P["date_t2"] = P["date"].shift(-2)
    return P


def ctx_rows(P, ctx):
    C = P[(P["split_edge"] != True) & P["y_date"].notna()].copy()  # noqa: E712
    C = C[(pd.to_datetime(C["y_date"]) < VAL0) == (C["split"] == "discovery")]
    if ctx == "NW":
        C = C[C["cal_next_kind"] == "weekly"]
    C["range"] = C["y_range_pct"]
    C["maxexc"] = C["y_max_exc"]
    C["agap"] = C["y_gap_pct"].abs()
    return C


def target(C, tgt, med):
    if tgt == "range_big":
        return (C["range"] > med["range"]).astype(float).where(C["range"].notna()), C["range"]
    if tgt == "gap_big":
        return (C["agap"] > med["agap"]).astype(float).where(C["agap"].notna()), C["agap"]
    if tgt == "big_move":
        return C["y_big_move_exc"].astype(float), C["maxexc"]
    raise ValueError(tgt)


def rate_vs_base(y, m, rows):
    yb = y[rows].dropna()
    yc = y[rows & m].dropna()
    n, k = len(yc), int(yc.sum())
    base = yb.mean() if len(yb) else np.nan
    return n, k, (k / n if n else np.nan), base


# ---------------------------------------------------------------- logistic regression (IRLS)
def logit(X, y, ridge=1e-6):
    X = np.column_stack([np.ones(len(X)), X])
    b = np.zeros(X.shape[1])
    for _ in range(100):
        p = 1 / (1 + np.exp(-X @ b))
        W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + ridge * np.eye(X.shape[1])
        g = X.T @ (y - p) - ridge * b
        step = np.linalg.solve(H, g)
        b += step
        if np.abs(step).max() < 1e-9:
            break
    p = 1 / (1 + np.exp(-X @ b))
    H = X.T @ (X * (p * (1 - p))[:, None]) + ridge * np.eye(X.shape[1])
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return b, se


def design(C, ctx, ul):
    cols = ["lvix", "lrng", "latr", "lhv", "agap_t"] if ctx == "ALL" else ["lvix", "lrng", "latr"]
    X = C[cols].copy()
    if ctx == "ALL":
        ns = C["n_bus"].clip(upper=5)
        for v in [2, 3, 4, 5]:
            X[f"ns{v}"] = (ns == v).astype(float)
        for v in [1, 2, 3, 4]:
            X[f"dow{v}"] = (C["dow_next"] == v).astype(float)
    elif ul == "BANKNIFTY":
        X["wed"] = (C["regime"] == "wed_weekly").astype(float)
    return X


def main():
    feats = {ul: build(ul) for ul in ["NIFTY", "BANKNIFTY"]}
    th = pd.read_csv(THEIRS / "thresholds.csv")
    fz = pd.read_csv(THEIRS / "candidates_frozen.csv").set_index("cand")
    V = pd.read_csv(THEIRS / "validation.csv").set_index("cand")

    # ---- leakage / construction checks
    LK = []
    for ul, P in feats.items():
        d = (P["strad_chg_own"] - P["strad_chg"]).abs()
        LK.append(dict(ul=ul, check="straddle_chg1 panel vs own (prev row, same expiry)", n=int(d.notna().sum()),
                       max_abs_diff=float(d.max()), share_panel_nonnull_own_null=float(
                           (P["strad_chg"].notna() & P["strad_chg_own"].isna()).mean())))
        d2 = (P["n_bus"] - P["n_real"])
        LK.append(dict(ul=ul, check="weekday count minus real session count (holidays)", n=int(d2.notna().sum()),
                       max_abs_diff=float(d2.max()), share_panel_nonnull_own_null=float((d2 != 0).mean())))
        nw = P[P["cal_next_kind"] == "weekly"]
        LK.append(dict(ul=ul, check="NW rows: near expiry != cal_next_date", n=len(nw),
                       max_abs_diff=float((pd.to_datetime(nw["f_opt_near_expiry"])
                                           != pd.to_datetime(nw["cal_next_date"])).sum()),
                       share_panel_nonnull_own_null=np.nan))
        # correlation of each signal with the TCLOSE controls and n_bus
        for s in ["iv", "wall_width", "wall_near", "mp_abs", "strad_chg", "vol_surge", "iv_chg"]:
            D = P[P["split"] == "discovery"]
            for c in ["lvix", "lrng", "latr", "n_bus"]:
                LK.append(dict(ul=ul, check=f"spearman({s},{c}) discovery", n=int(D[[s, c]].dropna().shape[0]),
                               max_abs_diff=float(D[s].corr(D[c], method="spearman")),
                               share_panel_nonnull_own_null=np.nan))
    pd.DataFrame(LK).to_csv(OUT / "construction_checks.csv", index=False)

    R, RB, LG = [], [], []
    for cand, ul, ctx, sig, bkt, tgt in CANDS:
        P = feats[ul]
        C = ctx_rows(P, ctx)
        Cd, Cv = C[C["split"] == "discovery"], C[C["split"] == "validation"]
        med = {"range": Cd["range"].median(), "agap": Cd["agap"].median()}
        x = Cd[sig].dropna()
        q = {k: x.quantile(v) for k, v in dict(q20=.2, q25=.25, q30=.3, q33=1 / 3, q40=.4, q60=.6, q67=2 / 3,
                                                   q70=.7, q75=.75, q80=.8).items()}
        thr = q["q67"] if bkt == "hi" else q["q33"]
        tt = th[(th.underlying == ul) & (th.ctx == ctx) & (th.signal == sig)].iloc[0]
        their_thr = tt["q67"] if bkt == "hi" else tt["q33"]
        sgn = 1 if fz.loc[cand, "effect"] > 0 else -1

        def mask(D, t=thr, b=bkt):
            return D[sig] >= t if b == "hi" else D[sig] <= t

        out = dict(cand=cand, ul=ul, ctx=ctx, signal=sig, bucket=bkt, target=tgt, my_thr=thr, their_thr=their_thr)
        for nm, D in [("disc", Cd), ("val", Cv)]:
            y, v = target(D, tgt, med)
            rows = y.notna() & D[sig].notna()
            n, k, r, b = rate_vs_base(y, mask(D), rows)
            lo, hi = wilson(k, n)[1:]
            if nm == "disc":
                p = binom_p(k, n, b)
            else:
                p = float(stats.binomtest(k, n, b, alternative="greater" if sgn > 0 else "less").pvalue)
            out.update({f"{nm}_n": n, f"{nm}_k": k, f"{nm}_rate": r, f"{nm}_ci_lo": lo, f"{nm}_ci_hi": hi,
                        f"{nm}_base": b, f"{nm}_effect": r - b, f"{nm}_p": p})
        out["pass_recomputed"] = bool(np.sign(out["val_effect"]) == sgn and out["val_p"] < 0.05
                                      and abs(out["val_effect"]) >= 0.5 * abs(out["disc_effect"]))
        out["their_disc_n"], out["their_disc_effect"] = fz.loc[cand, "n"], fz.loc[cand, "effect"]
        out["their_val_n"], out["their_val_effect"] = V.loc[cand, "val_n"], V.loc[cand, "val_effect"]
        out["their_passed"] = V.loc[cand, "passed"]
        # iv with real session counts (holiday-aware) for the iv candidates
        if sig == "iv":
            xr = Cd["iv_real"].dropna()
            tr = xr.quantile(2 / 3)
            y, _ = target(Cv, tgt, med)
            rows = y.notna() & Cv["iv_real"].notna()
            n, k, r, b = rate_vs_base(y, Cv["iv_real"] >= tr, rows)
            out["val_effect_iv_realsessions"], out["val_n_iv_realsessions"] = r - b, n
        R.append(out)

        # ---- robustness on discovery + validation
        y, v = target(C, tgt, med)
        rows = y.notna() & C[sig].notna()
        for grp_name, grp in [("year", C["date"].dt.year), ("regime", C["regime"]), ("split", C["split"]),
                              ("n_sess", C["n_bus"].clip(upper=5))]:
            for g in sorted(grp.dropna().unique()):
                gm = (grp == g)
                n, k, r, b = rate_vs_base(y, mask(C), rows & gm)
                RB.append(dict(cand=cand, check=grp_name, group=str(g), n=n, rate=r, base=b, effect=r - b,
                               same_sign=bool(np.sign(r - b) == sgn) if n else np.nan))
        for frac in (0.01, 0.05):  # drop the largest outcomes (favourable for 'higher' buckets) of all rows
            cut = v[rows].quantile(1 - frac) if sgn > 0 else v[rows].quantile(frac)
            keep = rows & ((v < cut) if sgn > 0 else (v > cut))
            n, k, r, b = rate_vs_base(y, mask(C), keep)
            RB.append(dict(cand=cand, check="drop_extreme_outcomes_all_rows", group=f"{frac:.2f}", n=n, rate=r,
                           base=b, effect=r - b, same_sign=bool(np.sign(r - b) == sgn)))
        for qk in (["q60", "q70", "q75", "q80"] if bkt == "hi" else ["q40", "q30", "q25", "q20"]):
            for nm, D in [("disc", Cd), ("val", Cv)]:
                yy, _ = target(D, tgt, med)
                rr = yy.notna() & D[sig].notna()
                n, k, r, b = rate_vs_base(yy, mask(D, q[qk]), rr)
                RB.append(dict(cand=cand, check=f"threshold_{nm}", group=qk, n=n, rate=r, base=b, effect=r - b,
                               same_sign=bool(np.sign(r - b) == sgn) if n else np.nan))

        # ---- incremental information beyond volatility controls (per period)
        for nm, D in [("disc", Cd), ("val", Cv)]:
            yy, _ = target(D, tgt, med)
            X = design(D, ctx, ul)
            ok = yy.notna() & D[sig].notna() & X.notna().all(axis=1)
            Xb = X[ok].copy()
            Xb["bucket"] = mask(D)[ok].astype(float)
            Xs = Xb.copy()
            for c in Xs.columns:
                if Xs[c].nunique() > 2:
                    Xs[c] = (Xs[c] - Xs[c].mean()) / Xs[c].std()
            b, se = logit(Xs.to_numpy(), yy[ok].to_numpy())
            z = b[-1] / se[-1]
            b0, se0 = logit(Xs[["bucket"]].to_numpy(), yy[ok].to_numpy())  # bucket only, no controls
            LG.append(dict(cand=cand, period=nm, n=int(ok.sum()), n_bucket=int(Xb["bucket"].sum()),
                           coef_bucket_raw=b0[-1], p_raw=float(2 * stats.norm.sf(abs(b0[-1] / se0[-1]))),
                           coef_bucket_controlled=b[-1], se=se[-1],
                           p_controlled_two_sided=float(2 * stats.norm.sf(abs(z))),
                           p_controlled_one_sided=float(stats.norm.sf(z * sgn)),
                           same_sign=bool(np.sign(b[-1]) == sgn)))
        # out-of-sample residual: baseline (controls only) fit on discovery, applied to validation
        yd, _ = target(Cd, tgt, med)
        Xd = design(Cd, ctx, ul)
        okd = yd.notna() & Xd.notna().all(axis=1)
        mu, sd = Xd[okd].mean(), Xd[okd].std().replace(0, 1)
        bin_cols = [c for c in Xd.columns if Xd[c].nunique() <= 2]
        mu[bin_cols], sd[bin_cols] = 0, 1
        bb, _ = logit(((Xd[okd] - mu) / sd).to_numpy(), yd[okd].to_numpy())
        yv, _ = target(Cv, tgt, med)
        Xv = design(Cv, ctx, ul)
        okv = yv.notna() & Xv.notna().all(axis=1) & Cv[sig].notna()
        pv = 1 / (1 + np.exp(-(np.column_stack([np.ones(okv.sum()), ((Xv[okv] - mu) / sd).to_numpy()]) @ bb)))
        res = yv[okv].to_numpy() - pv
        mv = mask(Cv)[okv].to_numpy()
        tst = stats.ttest_ind(res[mv], res[~mv], equal_var=False) if mv.sum() > 2 else None
        LG.append(dict(cand=cand, period="val_oos_residual", n=int(okv.sum()), n_bucket=int(mv.sum()),
                       coef_bucket_raw=np.nan, p_raw=np.nan,
                       coef_bucket_controlled=float(res[mv].mean() - res[~mv].mean()) if mv.sum() else np.nan,
                       se=np.nan,
                       p_controlled_two_sided=float(tst.pvalue) if tst is not None else np.nan,
                       p_controlled_one_sided=(float(tst.pvalue / 2) if np.sign(tst.statistic) == sgn else
                                               1 - float(tst.pvalue / 2)) if tst is not None else np.nan,
                       same_sign=bool(np.sign(res[mv].mean() - res[~mv].mean()) == sgn) if mv.sum() else np.nan))
    R = pd.DataFrame(R)
    R.to_csv(OUT / "recompute.csv", index=False)
    RB = pd.DataFrame(RB)
    RB.to_csv(OUT / "robustness.csv", index=False)
    LG = pd.DataFrame(LG)
    LG.to_csv(OUT / "incremental_logit.csv", index=False)

    # ---- volatility-clustering benchmark rule on the same targets (o_range_pct(t) top tercile)
    BM = []
    for ul in ["NIFTY", "BANKNIFTY"]:
        for ctx in ["ALL", "NW"]:
            C = ctx_rows(feats[ul], ctx)
            Cd = C[C["split"] == "discovery"]
            med = {"range": Cd["range"].median(), "agap": Cd["agap"].median()}
            for ctl in ["o_range_pct", "f_vix_close", "f_atr14_pct"]:
                t67 = Cd[ctl].quantile(2 / 3)
                for tgt in ["range_big", "big_move", "gap_big"]:
                    for nm in ["discovery", "validation"]:
                        D = C[C["split"] == nm]
                        y, _ = target(D, tgt, med)
                        rows = y.notna() & D[ctl].notna()
                        n, k, r, b = rate_vs_base(y, D[ctl] >= t67, rows)
                        BM.append(dict(ul=ul, ctx=ctx, rule=f"{ctl} >= disc q67 ({t67:.4g})", target=tgt, period=nm,
                                       n=n, rate=r, base=b, effect=r - b))
    pd.DataFrame(BM).to_csv(OUT / "volclustering_benchmark.csv", index=False)

    # ---- spot checks of rejected / observed claims
    SP = []
    for ul in ["NIFTY", "BANKNIFTY"]:
        P = feats[ul]
        C = ctx_rows(P, "NW")
        for nm in ["discovery", "validation"]:
            D = C[C["split"] == nm]
            mp, S0, S1 = D["f_opt_near_maxpain"], D["close_off"], D["close_off_t1"]
            ok = mp.notna() & S1.notna() & (mp != S0)
            mirror = 2 * S0 - mp
            cl = ((mp - S1).abs() < (mp - S0).abs())[ok]
            clm = ((mirror - S1).abs() < (mirror - S0).abs())[ok]
            # paired sign test: closer to max pain but not to the mirror vs the reverse
            a, bb = int((cl & ~clm).sum()), int((~cl & clm).sum())
            SP.append(dict(check="OBS-MP closer vs mirror point (NW)", ul=ul, period=nm, n=int(ok.sum()),
                           rate=cl.mean(), base=clm.mean(), effect=cl.mean() - clm.mean(),
                           p=binom_p(a, a + bb, 0.5) if a + bb else np.nan))
            far = ok & ((mp / S0 - 1).abs() >= 0.0025)
            ag = (np.sign(S1 - S0) == np.sign(mp - S0))[far]
            SP.append(dict(check="OBS-MP direction agreement |dist|>=0.25% (NW) vs 50%", ul=ul, period=nm,
                           n=int(far.sum()), rate=ag.mean(), base=0.5, effect=ag.mean() - 0.5,
                           p=binom_p(int(ag.sum()), int(far.sum()), 0.5)))
        # OC139: NIFTY long build-up -> cc up
        if ul == "NIFTY":
            A = ctx_rows(P, "ALL")
            fb = np.where((A["f_mom1"] > 0) & (A["f_futall_oi_chg"] > 0), "LB",
                          np.where(A["f_mom1"].notna() & A["f_futall_oi_chg"].notna()
                                   & (A["f_mom1"] != 0) & (A["f_futall_oi_chg"] != 0), "other", "na"))
            for nm in ["discovery", "validation"]:
                m = (A["split"] == nm).to_numpy() & (fb != "na")
                y = (A["y_cc"] > 0).astype(float)[m]
                lb = (fb[m] == "LB")
                n, k = int(lb.sum()), int(y[lb].sum())
                SP.append(dict(check="OC139 NIFTY LB -> cc up", ul=ul, period=nm, n=n, rate=k / n, base=y.mean(),
                               effect=k / n - y.mean(), p=binom_p(k, n, y.mean())))
        # OC128 / ST2: D-2 ATM straddle at settle held to expiry (official close of expiry day as settlement)
        D2 = P[(P["split_edge"] != True) & (P["cal_next_sessions_to_expiry"] == 1)].copy()  # noqa: E712
        D2 = D2[pd.to_datetime(D2["f_opt_near_expiry"]) == D2["date_t2"]]
        D2 = D2[D2["date_t2"].notna() & ((D2["date_t2"] < VAL0) == (D2["split"] == "discovery"))]
        D2["diff"] = ((D2["close_off_t2"] - D2["f_opt_near_atm_strike"]).abs() / D2["px_close"] * 100
                      - D2["f_opt_near_straddle_pct"])
        for nm in ["discovery", "validation"]:
            x = D2.loc[D2["split"] == nm, "diff"].dropna().to_numpy()
            m, lo, hi = block_boot_mean(x, block=3)
            SP.append(dict(check="ST2 D-2 straddle payoff-cost % spot", ul=ul, period=nm, n=len(x), rate=m, base=0.0,
                           effect=m, p=float(stats.ttest_1samp(x, 0).pvalue), ci_lo=lo, ci_hi=hi))
    SP = pd.DataFrame(SP)
    SP.to_csv(OUT / "spot_checks.csv", index=False)

    # ---- family-size check
    H = pd.read_csv(THEIRS / "hypotheses.csv")
    fam = dict(rows=len(H), with_p=int(H["p"].notna().sum()), bucket=int((H.kind == "bucket").sum()),
               structural=int((H.kind == "structural").sum()), straddle_cond=int((H.kind == "straddle_cond").sum()),
               expected_bucket=2 * 4 * (10 * 4 * 2 + 2 * 4 * 4 + 10 * 4 * 2), bh_q_recomputed_max_abs_diff=float(
                   np.nanmax(np.abs(bh(H["p"].to_numpy(), 0.10)[0] - H["bh_q"].to_numpy()))))
    pd.DataFrame([fam]).to_csv(OUT / "family_check.csv", index=False)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    pd.set_option("display.max_rows", 500)
    print(pd.DataFrame(LK).to_string())
    print(R[["cand", "my_thr", "their_thr", "disc_n", "their_disc_n", "disc_rate", "disc_base", "disc_effect",
             "their_disc_effect", "disc_p", "val_n", "their_val_n", "val_rate", "val_base", "val_effect",
             "their_val_effect", "val_p", "pass_recomputed", "their_passed"]].to_string())
    if "val_effect_iv_realsessions" in R:
        print(R[["cand", "val_effect_iv_realsessions", "val_n_iv_realsessions"]].dropna().to_string())
    print(LG.to_string())
    print(pd.DataFrame(BM).to_string())
    print(SP.to_string())
    print(fam)


if __name__ == "__main__":
    main()
