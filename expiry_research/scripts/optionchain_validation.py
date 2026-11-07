"""Validation + robustness of the FROZEN candidates of module optionchain (run once).

Reads candidates_frozen.csv and thresholds.csv written by optionchain_discovery.py; refuses to run without them.
Writes validation.csv, robustness.csv, robustness_summary.csv, pred_<cand>.csv (expiry contexts) and
straddle_per_expiry_<UL>.csv. Pass rule (fixed in the LLD): same sign, one-sided p < 0.05 vs the validation base,
|effect| >= half the discovery |effect|.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import optionchain_common as oc  # noqa: E402
from stats_utils import block_boot_mean, wilson  # noqa: E402

OUT = oc.OUT
FZ = OUT / "candidates_frozen.csv"
if not FZ.exists():
    raise SystemExit("candidates_frozen.csv missing: run optionchain_discovery.py first")


def one_sided_binom(k, n, p0, effect_sign):
    alt = "greater" if effect_sign > 0 else "less"
    return float(stats.binomtest(int(k), int(n), p0, alternative=alt).pvalue)


def bucket_eval(C, r, thr, med, tail=None, drop_best=False):
    y, v = oc.binary_target(C, r["target"], med)
    base_rows = y.notna() & C[r["signal"]].notna()
    m = oc.bucket_mask(C, r["signal"], r["bucket"], thr, tail) & base_rows
    if drop_best and r["target"] != "gap_fill":
        cond = v[m].dropna()
        if len(cond) >= 10:
            n_drop = max(1, int(round(0.01 * len(cond))))
            # favourable = outcomes that push the rate in the direction of the effect
            fav = cond.sort_values(ascending=(r["effect"] > 0)).index[-n_drop:]
            base_rows = base_rows & ~C.index.isin(fav)
            m = m & ~C.index.isin(fav)
    yb, yc = y[base_rows], y[m]
    n, k = int(yc.notna().sum()), int(yc.sum())
    base = float(yb.mean()) if len(yb) else np.nan
    rate = k / n if n else np.nan
    return n, k, rate, base


def strad_eval(C, r, drop_best=False):
    D = oc.straddle_measure(C)
    if r["kind"] == "straddle_cond":
        raise NotImplementedError
    x = D["diff_pct"].dropna()
    if drop_best and len(x) >= 10:
        n_drop = max(1, int(round(0.01 * len(x))))
        xs = x.sort_values()
        x = xs.iloc[n_drop:] if r["effect"] < 0 else xs.iloc[:-n_drop]
    return x


def main():
    fz = pd.read_csv(FZ)
    th = pd.read_csv(OUT / "thresholds.csv")
    feats = {ul: oc.load_features(ul) for ul in oc.ULS}
    ctxf = {(ul, c): oc.context_frame(feats[ul], ul, c) for ul in oc.ULS for c in oc.CTXS}
    V, RB, RS = [], [], []
    for _, r in fz.iterrows():
        ul, ctx = r["underlying"], r["ctx"]
        C = ctxf[(ul, ctx)]
        tm = th[(th.underlying == ul) & (th.ctx == ctx) & (th.signal == "_target_median")].iloc[0]
        med = {"agap": tm["agap"], "range": tm["range"]}
        thr = {}
        if r["kind"] == "bucket" and r["signal"] not in oc.DIR_CATS:
            thr = th[(th.underlying == ul) & (th.ctx == ctx) & (th.signal == r["signal"])].iloc[0].to_dict()
        Cv = C[C["split"] == "validation"]
        sgn = np.sign(r["effect"])
        if r["kind"] == "bucket":
            n, k, rate, base = bucket_eval(Cv, r, thr, med)
            lo, hi = wilson(k, n)[1:]
            eff = rate - base
            p1 = one_sided_binom(k, n, base, sgn) if n and 0 < base < 1 else np.nan
        else:  # structural straddle mean vs 0
            x = strad_eval(Cv, r)
            n, k = len(x), int((x > 0).sum())
            rate, base = x.mean(), 0.0
            _, lo, hi = block_boot_mean(x.to_numpy(), block=3)
            eff = rate
            tt = stats.ttest_1samp(x, 0.0)
            p1 = float(tt.pvalue / 2) if np.sign(tt.statistic) == sgn else 1 - float(tt.pvalue / 2)
        passed = bool(n > 0 and np.sign(eff) == sgn and p1 < 0.05 and abs(eff) >= 0.5 * abs(r["effect"]))
        V.append(dict(cand=r["cand"], id=r["id"], val_n=n, val_k=k, val_rate=rate, val_ci_lo=lo, val_ci_hi=hi,
                      val_base=base, val_effect=eff, val_p_one_sided=p1, disc_effect=r["effect"],
                      passed=passed, small_n=n < 30))
        # ---------- robustness on discovery + validation ----------
        rows = []
        if r["kind"] == "bucket":
            n, k, rate, base = bucket_eval(C, r, thr, med)
            rows.append(("all", "disc+val", n, rate, base))
            n, k, rate, base = bucket_eval(C, r, thr, med, drop_best=True)
            rows.append(("drop_best_1pct", "disc+val", n, rate, base))
            for yr, g in C.groupby(C["date"].dt.year):
                n, k, rate, base = bucket_eval(g, r, thr, med)
                rows.append(("year", str(yr), n, rate, base))
            for rg, g in C.groupby("regime"):
                n, k, rate, base = bucket_eval(g, r, thr, med)
                rows.append(("regime", rg, n, rate, base))
            vt = pd.qcut(C["f_vix_close"], 3, labels=["vix_lo", "vix_mid", "vix_hi"])
            for vk, g in C.groupby(vt, observed=True):
                n, k, rate, base = bucket_eval(g, r, thr, med)
                rows.append(("vix_tercile", str(vk), n, rate, base))
            if thr:
                for tail in (0.30, 0.40):
                    n, k, rate, base = bucket_eval(C, r, thr, med, tail=tail)
                    rows.append(("threshold", f"tail_{tail:.2f}", n, rate, base))
        else:
            x = strad_eval(C, r)
            rows.append(("all", "disc+val", len(x), x.mean(), 0.0))
            x = strad_eval(C, r, drop_best=True)
            rows.append(("drop_best_1pct", "disc+val", len(x), x.mean(), 0.0))
            D = oc.straddle_measure(C)
            for yr, g in D.groupby(D["date"].dt.year):
                rows.append(("year", str(yr), len(g), g["diff_pct"].mean(), 0.0))
            for rg, g in D.groupby("regime"):
                rows.append(("regime", rg, len(g), g["diff_pct"].mean(), 0.0))
            vt = pd.qcut(D["f_vix_close"], 3, labels=["vix_lo", "vix_mid", "vix_hi"])
            for vk, g in D.groupby(vt, observed=True):
                rows.append(("vix_tercile", str(vk), len(g), g["diff_pct"].mean(), 0.0))
        for kind, grp, n, rate, base in rows:
            RB.append(dict(cand=r["cand"], id=r["id"], check=kind, group=grp, n=n, rate=rate, base=base,
                           effect=rate - base if pd.notna(rate) else np.nan, same_sign=np.sign(rate - base) == sgn))
        rb = pd.DataFrame(RB)
        rb = rb[rb.cand == r["cand"]]
        yrs = rb[(rb.check == "year") & (rb.n >= 10)]
        vx = rb[rb.check == "vix_tercile"]
        rg = rb[rb.check == "regime"]
        tr = rb[rb.check == "threshold"]
        db = rb[rb.check == "drop_best_1pct"]
        RS.append(dict(cand=r["cand"], id=r["id"],
                       years_same_sign=f"{int(yrs.same_sign.sum())}/{len(yrs)}",
                       vix_terciles_same_sign=f"{int(vx.same_sign.sum())}/{len(vx)}",
                       regimes_same_sign=f"{int(rg.same_sign.sum())}/{len(rg)}",
                       thresholds_same_sign=f"{int(tr.same_sign.sum())}/{len(tr)}" if len(tr) else "n/a",
                       drop_best_effect=float(db.effect.iloc[0]) if len(db) else np.nan,
                       full_effect=float(rb[rb.check == "all"].effect.iloc[0])))
        # ---------- per-expiry predictions ----------
        if ctx in ("NW", "NM", "D2"):
            if r["kind"] == "bucket":
                y, v = oc.binary_target(C, r["target"], med)
                P = pd.DataFrame({"date": C["date"].dt.date, "target_date": C["target_date"].dt.date,
                                  "split": C["split"], "signal": C[r["signal"]],
                                  "in_bucket": oc.bucket_mask(C, r["signal"], r["bucket"], thr),
                                  "target_binary": y, "target_value": v})
            else:
                D = oc.straddle_measure(C)
                P = D[["date", "target_date", "split", "f_opt_near_atm_strike", "cost_pct", "S_E", "S_E_src",
                       "payoff_pct", "diff_pct"]].copy()
            P.to_csv(OUT / f"pred_{r['cand']}.csv", index=False)
    V = pd.DataFrame(V)
    V.to_csv(OUT / "validation.csv", index=False)
    pd.DataFrame(RB).to_csv(OUT / "robustness.csv", index=False)
    pd.DataFrame(RS).to_csv(OUT / "robustness_summary.csv", index=False)
    # straddle per expiry (descriptive file for the report; D-1 and D-2, both splits) -- written only here, after
    # freezing, because it contains validation rows
    for ul in oc.ULS:
        parts = []
        for ctx in ("NW", "NM", "D2"):
            D = oc.straddle_measure(ctxf[(ul, ctx)])
            D["ctx"] = ctx
            parts.append(D[["ctx", "date", "target_date", "split", "f_opt_near_atm_strike", "cost_pct", "S_E",
                            "S_E_src", "payoff_pct", "diff_pct", "realised_move_pct", "range", "maxexc"]])
        pd.concat(parts).to_csv(OUT / f"straddle_per_expiry_{ul}.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 400)
    M = fz[["cand", "id", "n", "rate", "base", "effect", "bh_q"]].merge(V.drop(columns=["id"]), on="cand").merge(
        pd.DataFrame(RS).drop(columns=["id"]), on="cand")
    print(M.to_string())
    print("passed:", int(V.passed.sum()), "of", len(V))


if __name__ == "__main__":
    main()
