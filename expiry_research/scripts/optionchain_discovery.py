"""Discovery stage of module optionchain: hypothesis family on DISCOVERY rows only, BH, frozen candidates.

Reads results/optionchain/features_<UL>.parquet (built by optionchain_features.py). Computes nothing on validation
rows (they are dropped right after the context frame is built). Writes thresholds.csv, hypotheses.csv,
structural_discovery.csv, candidates_frozen.csv. Design: reports/lld/optionchain.md.
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
import optionchain_common as oc  # noqa: E402
from stats_utils import bh, binom_p, block_boot_mean, t_stat, two_prop, wilson  # noqa: E402

OUT = oc.OUT
STRAD_SIGNALS = ["iv", "iv_hv", "iv_chg", "strad_chg", "vol_surge", "top3", "wall_width", "mp_abs"]


def t_p(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    t = t_stat(x)
    if math.isnan(t):
        return math.nan
    return float(2 * stats.t.sf(abs(t), len(x) - 1))


def rate_row(y, mask, base_rows):
    yb = y[base_rows].dropna()
    yc = y[base_rows & mask].dropna()
    n, k = len(yc), int(yc.sum())
    base = float(yb.mean()) if len(yb) else math.nan
    r, lo, hi = wilson(k, n)
    p = binom_p(k, n, base) if n and 0 < base < 1 else math.nan
    return dict(n=n, k=k, rate=r, ci_lo=lo, ci_hi=hi, base=base, n_base=len(yb), effect=r - base, p=p)


def main():
    H, TH, ST = [], [], []
    for ul in oc.ULS:
        F = oc.load_features(ul)
        for ctx in oc.CTXS:
            C = oc.context_frame(F, ul, ctx)
            C = C[C["split"] == "discovery"].copy()  # discovery only from here on
            med = {"agap": float(C["agap"].median()), "range": float(C["range"].median())}
            TH.append(dict(underlying=ul, ctx=ctx, signal="_target_median", **{"agap": med["agap"],
                                                                                 "range": med["range"]}))
            for sig in oc.all_signals():
                thr = oc.thresholds(C, sig) if sig not in oc.DIR_CATS else {}
                if thr:
                    TH.append(dict(underlying=ul, ctx=ctx, signal=sig, **thr))
                for tgt in oc.target_list(sig):
                    y, v = oc.binary_target(C, tgt, med)
                    base_rows = y.notna() & C[sig].notna()
                    for b in oc.buckets(sig):
                        m = oc.bucket_mask(C, sig, b, thr)
                        r = rate_row(y, m, base_rows)
                        vc = v[base_rows & m].dropna()
                        vb = v[base_rows].dropna()
                        H.append(dict(id=f"{ul}|{ctx}|{sig}|{b}|{tgt}", kind="bucket", underlying=ul, ctx=ctx,
                                      signal=sig, bucket=b, target=tgt, **r,
                                      cond_mean=float(vc.mean()) if len(vc) else np.nan,
                                      base_mean=float(vb.mean()) if len(vb) else np.nan,
                                      small_n=r["n"] < 30))
            # ---- structural tests (D-1 contexts NW / NM and D2) ----
            if ctx in ("NW", "NM", "D2"):
                A = oc.context_frame(F, ul, "ALL")
                A = A[A["split"] == "discovery"]
                if ctx == "D2":
                    # base for D2: every row, target = close two sessions ahead
                    A2 = F[(F["split_edge"] != True) & (F["split"] == "discovery")].copy()  # noqa: E712
                    A2 = A2[A2["t2_date"].notna() & (A2["t2_date"] < pd.Timestamp("2023-01-01"))]
                    A2["S_target"] = A2["close_official_t2"]
                    A = A2
                mpname = "MP3" if ctx == "D2" else "MP1"
                for min_dist, tag in [(0.0, "closer"), (0.25, "agree")]:
                    cl, ag = oc.mp_toward(C, min_dist)
                    bcl, bag = oc.mp_toward(A, min_dist)
                    yv, bv = (cl, bcl) if tag == "closer" else (ag, bag)
                    yv, bv = yv.dropna(), bv.dropna()
                    n, k = len(yv), int(yv.sum())
                    r, lo, hi = wilson(k, n)
                    base = float(bv.mean())
                    # non-eve rows only, for the two-proportion comparison
                    H.append(dict(id=f"{ul}|{ctx}|{mpname}_{tag}", kind="structural", underlying=ul, ctx=ctx,
                                  signal=f"maxpain_{tag}", bucket="all", target=f"{mpname}_{tag}",
                                  n=n, k=k, rate=r, ci_lo=lo, ci_hi=hi, base=base, n_base=len(bv),
                                  effect=r - base, p=binom_p(k, n, base), p_two_prop=two_prop(k, n, int(bv.sum()),
                                                                                              len(bv)),
                                  small_n=n < 30))
                D = oc.straddle_measure(C)
                name = "ST2" if ctx == "D2" else "ST1"
                x = D["diff_pct"].to_numpy()
                m, blo, bhi = block_boot_mean(x, block=3)
                kpos = int((D["diff_pct"] > 0).sum())
                rr = wilson(kpos, len(D))
                H.append(dict(id=f"{ul}|{ctx}|{name}_straddle_pnl", kind="structural", underlying=ul, ctx=ctx,
                              signal="atm_straddle_settle", bucket="all", target=f"{name}_payoff_minus_cost_pct",
                              n=len(D), k=kpos, rate=rr[0], ci_lo=blo, ci_hi=bhi, base=0.0, n_base=np.nan,
                              effect=m, p=t_p(x), cond_mean=m, small_n=len(D) < 30))
                # conditional straddle P&L: does a vol / chain signal pick expiries where the bought straddle pays?
                for sig in STRAD_SIGNALS:
                    thr = oc.thresholds(C, sig)
                    for b in ["hi", "lo"]:
                        mm = oc.bucket_mask(D, sig, b, thr) & D[sig].notna()
                        xb = D.loc[D[sig].notna(), "diff_pct"]
                        xc = D.loc[mm, "diff_pct"].dropna()
                        bm = float(xb.mean())
                        mc, clo, chi = block_boot_mean(xc.to_numpy(), block=3)
                        pv = float(stats.ttest_1samp(xc, bm).pvalue) if len(xc) > 2 else np.nan
                        kp = int((xc > 0).sum())
                        H.append(dict(id=f"{ul}|{ctx}|{name}c|{sig}|{b}", kind="straddle_cond", underlying=ul,
                                      ctx=ctx, signal=sig, bucket=b, target=f"{name}_payoff_minus_cost_pct",
                                      n=len(xc), k=kp, rate=kp / len(xc) if len(xc) else np.nan, ci_lo=clo,
                                      ci_hi=chi, base=bm, n_base=len(xb), effect=mc - bm, p=pv, cond_mean=mc,
                                      base_mean=bm, small_n=len(xc) < 30))
                ST.append(dict(underlying=ul, ctx=ctx, split="discovery", n=len(D),
                               mean_cost_pct=D["cost_pct"].mean(), mean_payoff_pct=D["payoff_pct"].mean(),
                               mean_diff_pct=m, diff_ci_lo=blo, diff_ci_hi=bhi, diff_p=t_p(x),
                               median_ratio=D["ratio"].median(), share_payoff_gt_cost=rr[0],
                               share_ci_lo=rr[1], share_ci_hi=rr[2],
                               mean_realised_move_pct=D["realised_move_pct"].mean(),
                               share_maxexc_gt_cost=(D["maxexc_vs_cost"] > 0).mean(),
                               share_range_gt_cost=(D["range"] > D["cost_pct"]).mean(),
                               settle_src_bhav=(D["S_E_src"] == "bhavcopy_settlement").mean()))
            print(ul, ctx, "discovery rows", len(C))
    H = pd.DataFrame(H)
    q, rej = bh(H["p"].to_numpy(), 0.10)
    H["bh_q"] = q
    H["bh_reject"] = rej
    H["family_size"] = int(H["p"].notna().sum())
    H.to_csv(OUT / "hypotheses.csv", index=False)
    pd.DataFrame(TH).to_csv(OUT / "thresholds.csv", index=False)
    pd.DataFrame(ST).to_csv(OUT / "structural_discovery.csv", index=False)
    print("family size (tests with a p-value):", int(H["p"].notna().sum()), " BH rejections:", int(rej.sum()))
    # ---- freeze ----
    ok = H[(H["n"] >= 30) & H["p"].notna()].sort_values("p")
    fz = ok[ok["bh_q"] <= 0.10].copy()
    fz["freeze_reason"] = "BH q<=0.10"
    if len(fz) < 5:
        extra = ok[(ok["bh_q"] > 0.10) & (ok["p"] < 0.01)].head(10 - len(fz)).copy()
        extra["freeze_reason"] = "exploratory p<0.01"
        fz = pd.concat([fz, extra])
    fz = fz.reset_index(drop=True)
    fz.insert(0, "cand", [f"OC{i + 1:02d}" for i in range(len(fz))])
    th = pd.DataFrame(TH)

    def rule(r):
        if r["kind"] == "structural":
            return r["target"]
        if r["signal"] in oc.DIR_CATS:
            return f"{r['signal']} == {r['bucket']}"
        t = th[(th.underlying == r["underlying"]) & (th.ctx == r["ctx"]) & (th.signal == r["signal"])].iloc[0]
        return (f"{r['signal']} >= {t['q67']:.6g}" if r["bucket"] == "hi" else f"{r['signal']} <= {t['q33']:.6g}")

    fz["rule"] = [rule(r) for _, r in fz.iterrows()]
    fz["decision_time"] = np.where(fz["ctx"] == "D2", "TCLOSE(D-2), target = expiry session t+2",
                                   "TCLOSE(t), target = t+1 (earliest entry t+1 open)")
    keep = ["cand", "id", "kind", "underlying", "ctx", "signal", "bucket", "rule", "decision_time", "target", "n",
            "k", "rate", "ci_lo", "ci_hi", "base", "effect", "p", "bh_q", "freeze_reason", "cond_mean", "base_mean"]
    fz[keep].to_csv(OUT / "candidates_frozen.csv", index=False)
    print("frozen candidates:", len(fz))
    pd.set_option("display.width", 250)
    print(fz[keep[:4] + ["rule", "target", "n", "rate", "base", "effect", "p", "bh_q", "freeze_reason"]].to_string())
    print("\nTop 25 by p (n>=30):")
    print(ok.head(25)[["id", "n", "rate", "base", "effect", "p", "bh_q"]].to_string())


if __name__ == "__main__":
    main()
