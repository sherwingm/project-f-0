"""Bias module, stage 3: VALIDATION (run once, after bias_freeze.py). Design: reports/lld/bias.md.

Reference tables on validation rows, regime checks that need validation rows (BANKNIFTY weekday regimes, base-rate
shift), official-vs-minute gap labels in validation, and the single evaluation of the frozen candidates.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from scipy import stats

import bias_common as bc
import bias_discovery as bd
import stats_utils as su

OUT = bc.OUT
assert (OUT / "candidates_frozen.csv").exists(), "freeze first"
LOGF = bc.log_out("validation")
bd.HYP.clear()
hyp = bd.hyp


def eval_candidates(Vs):
    F = pd.read_csv(OUT / "candidates_frozen.csv")
    rows = []
    for _, c in F.iterrows():
        V = Vs[c.underlying]
        lab = V[c.tag].astype(str) if c.tag != "xkind_ctx" else (V["xkind"] + "|" + V["ctx"])
        m = lab == c.level
        sign = 1 if c.direction == "higher" else -1
        if c.stat == "rate":
            x = V.loc[m, c.target].dropna()
            base = V[c.target].mean()
            n, k = len(x), x.sum()
            rate = k / n if n else np.nan
            p1 = stats.binomtest(int(k), n, base, alternative="greater" if sign > 0 else "less").pvalue if n else np.nan
            lo, hi = su.wilson(k, n)[1:] if n else (np.nan, np.nan)
        else:
            x = V.loc[m, c.target].dropna()
            base = V[c.target].mean()
            n, rate = len(x), x.mean() if len(x) else np.nan
            p1 = stats.ttest_1samp(x, base, alternative="greater" if sign > 0 else "less").pvalue if n > 1 else np.nan
            _, lo, hi = su.mean_ci(x)
        eff = rate - base if n else np.nan
        if n == 0:
            verdict = "Untestable (context absent in validation)"
        else:
            ok = (np.sign(eff) == sign) and (p1 < 0.05) and (abs(eff) >= 0.5 * abs(c.disc_effect))
            verdict = "Passed-validation" if ok else "Rejected"
        rows.append(dict(id=c.id, underlying=c.underlying, tag=c.tag, level=c.level, target=c.target,
                         direction=c.direction, disc_effect=c.disc_effect, val_n=n, val_rate=rate, val_ci_lo=lo,
                         val_ci_hi=hi, val_base=base, val_effect=eff, val_p_one_sided=p1,
                         half_disc_effect=0.5 * abs(c.disc_effect), small_n=n < 30, verdict=verdict))
        if n:
            hyp("candidate_validation", c.underlying, "validation", f"{c.id} one-sided", n, eff, p1)
    return pd.DataFrame(rows)


def weekday_vs_expiry(A, ul):
    """Is an 'expiry-day' effect a weekday effect? Compares the same weekday of t+1 across regimes."""
    rows = []
    if ul != "BANKNIFTY":
        n_shift = int(((A["ctx"] == "D0") & (A["cal_next_dow"] != "Thursday")).sum())
        rows.append(dict(ul=ul, comparison="NIFTY D0 on a non-Thursday (holiday shifts), open period", n=n_shift))
        for t in ["big_exc", "big_cc"]:
            a = A[(A["ctx"] == "D0") & (A["cal_next_dow"] != "Thursday")][t]
            b = A[(A["ctx"] == "D0") & (A["cal_next_dow"] == "Thursday")][t]
            p = su.two_prop(a.sum(), len(a), b.sum(), len(b))
            rows.append(dict(ul=ul, comparison=f"D0 shifted vs D0 Thursday {t}", n=len(a), rate=a.mean(),
                             other_n=len(b), other_rate=b.mean(), diff=a.mean() - b.mean(), p=p))
            hyp("regime", ul, "disc+val", f"D0 shifted vs Thursday {t}", len(a), a.mean() - b.mean(), p)
        return rows
    for dow in ["Thursday", "Wednesday"]:
        for t in ["big_exc", "big_cc", "gap_up", "oc_pos"]:
            s1 = A[(A["wd_regime"] == "B1") & (A["cal_next_dow"] == dow)]
            s3 = A[(A["wd_regime"].isin(["B2", "B3"])) & (A["cal_next_dow"] == dow)]
            p = su.two_prop(s1[t].sum(), len(s1), s3[t].sum(), len(s3))
            rows.append(dict(ul=ul, comparison=f"t+1 {dow}: B1 (Thu expiry) vs B2+B3 (Wed weekly) {t}",
                             n=len(s1), rate=s1[t].mean(), d0_share=(s1["ctx"] == "D0").mean(), other_n=len(s3),
                             other_rate=s3[t].mean(), other_d0_share=(s3["ctx"] == "D0").mean(),
                             diff=s1[t].mean() - s3[t].mean(), p=p))
            hyp("regime", ul, "disc+val", f"BN t+1 {dow} B1 vs B2+B3 {t}", len(s1), s1[t].mean() - s3[t].mean(), p)
    # same calendar years only (2023-01 .. 2024-06), to separate the weekday move from the 2018-22 volatility level
    V = A[A["split"] == "validation"]
    for t in ["big_exc", "big_cc"]:
        for lab, m in (("D0", V["ctx"] == "D0"), ("Thursday non-D0", (V["cal_next_dow"] == "Thursday") & (V["ctx"] != "D0")),
                       ("Wednesday non-D0", (V["cal_next_dow"] == "Wednesday") & (V["ctx"] != "D0"))):
            for reg in ["B1", "B2", "B3"]:
                s = V[m & (V["wd_regime"] == reg)][t]
                rows.append(dict(ul=ul, comparison=f"validation {lab} in {reg} {t}", n=len(s),
                                 rate=s.mean() if len(s) else np.nan))
    return rows


def main():
    Vs, refs, trans, labs, bands, regs, wds = {}, [], [], [], [], [], []
    for ul in bc.ULS:
        P, cuts = bc.load(ul)
        P = bd.official_labels(P)
        A = P[P["usable"]].copy()
        V = A[A["split"] == "validation"].copy()
        D = A[A["split"] == "discovery"]
        Vs[ul] = V
        print(f"{ul}: validation usable rows {len(V)}; VIX terciles (discovery cuts) "
              f"{V['vix_terc'].value_counts().to_dict()}")
        refs.append(bd.ref_table(V, ul, "validation"))
        t, chip = bd.transition(V, ul, "validation")
        trans.append(t)
        hyp("ref", ul, "validation", "gap dir transition chi2", len(V), np.nan, chip)
        Vm = V[V["minute_era"] & V["y_gap_dir_off"].notna() & V["o_gap_dir_off"].notna()]
        labs.append(bd.label_check(Vm, ul, "validation"))
        trans.append(bd.transition(Vm, ul, "validation", "o_gap_dir_off", "y_gap_dir_off", "official")[0])
        bands += [bd.flat_band(V, ul, "validation"), bd.flat_band(Vm, ul, "validation", "y_gap_off")]
        # base-rate shift discovery -> validation, and periods inside validation
        for tg in bc.TARGETS + ["gap_flat"]:
            p = su.two_prop(V[tg].sum(), len(V), D[tg].sum(), len(D))
            regs.append(dict(ul=ul, split="validation", regime="split", level="validation vs discovery", target=tg,
                             n=len(V), rate=V[tg].mean(), rest_rate=D[tg].mean(), diff=V[tg].mean() - D[tg].mean(), p=p))
            hyp("regime", ul, "validation", f"base shift validation vs discovery {tg}", len(V),
                V[tg].mean() - D[tg].mean(), p)
            half = V["year"] + np.where(V["y_date"].str[5:7] <= "06", "H1", "H2")
            for h in sorted(half.unique()):
                a, b = V.loc[half == h, tg], V.loc[half != h, tg]
                p = su.two_prop(a.sum(), len(a), b.sum(), len(b))
                regs.append(dict(ul=ul, split="validation", regime="half", level=h, target=tg, n=len(a),
                                 rate=a.mean(), rest_rate=b.mean(), diff=a.mean() - b.mean(), p=p))
                hyp("regime", ul, "validation", f"half={h} {tg} vs rest of validation", len(a), a.mean() - b.mean(), p)
            if ul == "BANKNIFTY":
                for reg in ["B1", "B2", "B3"]:
                    a, b = V.loc[V["wd_regime"] == reg, tg], V.loc[V["wd_regime"] != reg, tg]
                    p = su.two_prop(a.sum(), len(a), b.sum(), len(b))
                    regs.append(dict(ul=ul, split="validation", regime="wd_regime", level=reg, target=tg, n=len(a),
                                     rate=a.mean(), rest_rate=b.mean(), diff=a.mean() - b.mean(), p=p))
                    hyp("regime", ul, "validation", f"wd_regime={reg} {tg} vs rest of validation", len(a),
                        a.mean() - b.mean(), p)
        for tg in ["y_range_pct"]:
            p = stats.ttest_ind(V[tg], D[tg], equal_var=False).pvalue
            regs.append(dict(ul=ul, split="validation", regime="split", level="validation vs discovery",
                             target="mean " + tg, n=len(V), rate=V[tg].mean(), rest_rate=D[tg].mean(),
                             diff=V[tg].mean() - D[tg].mean(), p=p))
            hyp("regime", ul, "validation", f"base shift validation vs discovery mean {tg}", len(V),
                V[tg].mean() - D[tg].mean(), p)
        wds += weekday_vs_expiry(A, ul)
    pd.concat(refs).to_csv(OUT / "ref_validation.csv", index=False)
    pd.concat(trans).to_csv(OUT / "gap_transition_validation.csv", index=False)
    pd.concat(labs).to_csv(OUT / "label_official_vs_minute_validation.csv", index=False)
    pd.concat(bands).to_csv(OUT / "flat_band_validation.csv", index=False)
    pd.DataFrame(regs).to_csv(OUT / "regimes_validation.csv", index=False)
    pd.DataFrame(wds).to_csv(OUT / "weekday_vs_expiry.csv", index=False)
    CV = eval_candidates(Vs)
    CV.to_csv(OUT / "candidates_validation.csv", index=False)
    pd.set_option("display.width", 250)
    print(CV[["id", "underlying", "level", "target", "direction", "disc_effect", "val_n", "val_rate", "val_base",
              "val_effect", "val_p_one_sided", "verdict"]].round(4).to_string(index=False))
    H = pd.DataFrame(bd.HYP)
    H.to_csv(OUT / "hypotheses_validation.csv", index=False)
    print(f"validation tests logged: {len(H)}")
    LOGF.close()


if __name__ == "__main__":
    main()
