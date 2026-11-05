"""Stage 2 of the `model` module: evaluate the FROZEN candidates on VALIDATION once, then robustness on
discovery + validation (design: reports/lld/model.md). Never re-tunes anything.

Writes results/model/candidates_validation.csv and results/model/robustness_years.csv.
"""
import hashlib
import json
import math
import sys
import warnings
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.simplefilter("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from model_common import (BIN_TARGETS, CUTOFFS, OUT, SOURCE, ULS, apply_rule, build_frame, ctx_mask)  # noqa: E402
from stats_utils import mean_ci, wilson  # noqa: E402

MIN_VAL_N = 20


def rows_for(F, cand):
    """(cond mask, base mask) for a candidate on frame F (any split subset)."""
    y = F["t_" + cand["target"]]
    rule = json.loads(cand["rule_json"])
    if cand["stage"] == "context":
        base = y.notna()
        cond = base & ctx_mask(F, cand["context"])
    else:
        _, present = apply_rule(F, rule)
        base = y.notna() & ctx_mask(F, cand["context"]) & present
        m, _ = apply_rule(F, rule)
        cond = base & m
    return cond, base


def stat(F, cond, base, target, binary):
    y = F["t_" + target]
    yc, yb = y[cond].values, y[base].values
    n = len(yc)
    b = float(yb.mean()) if len(yb) else np.nan
    if binary:
        k = int(yc.sum())
        r, lo, hi = wilson(k, n) if n else (np.nan,) * 3
        return n, k, r, lo, hi, b
    m, lo, hi = mean_ci(yc) if n else (np.nan,) * 3
    return n, np.nan, m, lo, hi, b


def one_sided_p(F, cond, base, target, binary, direction):
    y = F["t_" + target]
    yc, yb = y[cond].values, y[base].values
    n = len(yc)
    if n < 3 or len(yb) == 0:
        return np.nan
    b = yb.mean()
    alt = "greater" if direction == "higher" else "less"
    if binary:
        if not 0 < b < 1:
            return np.nan
        return float(stats.binomtest(int(yc.sum()), n, b, alternative=alt).pvalue)
    return float(stats.ttest_1samp(yc, b, alternative=alt).pvalue)


def effect(F, cond, base, target):
    y = F["t_" + target]
    if cond.sum() == 0 or base.sum() == 0:
        return np.nan, int(cond.sum())
    return float(y[cond].mean() - y[base].mean()), int(cond.sum())


def main():
    fz = OUT / "candidates_frozen.csv"
    if not fz.exists():
        raise SystemExit("candidates_frozen.csv missing: run model_discovery.py first")
    sha = hashlib.sha256(fz.read_bytes()).hexdigest()
    rec = (OUT / "candidates_frozen.sha256").read_text().strip()
    if sha != rec:
        raise SystemExit("candidates_frozen.csv changed after freezing")
    C = pd.read_csv(fz)
    frames = {(ul, c): build_frame(ul, c) for ul in ULS for c in CUTOFFS}
    out, yrows = [], []
    for _, c in C.iterrows():
        cut = "TCLOSE" if c["cutoff"] == "CAL" else c["cutoff"]
        F = frames[(c["ul"], cut)]
        binary = c["target"] in BIN_TARGETS
        r = dict(cid=c["cid"])
        # ---- validation, once
        V = F[F.split == "validation"]
        cond, base = rows_for(V, c)
        n, k, rate, lo, hi, b = stat(V, cond, base, c["target"], binary)
        eff = rate - b if n else np.nan
        p = one_sided_p(V, cond, base, c["target"], binary, c["direction"])
        de = c["disc_effect"]
        same = (not math.isnan(eff)) and np.sign(eff) == np.sign(de)
        big = same and abs(eff) >= 0.5 * abs(de)
        if n < MIN_VAL_N:
            passed, label = False, "Suggestive"
        else:
            passed = bool(same and (p < 0.05) and big)
            label = "Passed-validation" if passed else "Rejected"
        r.update(val_n=n, val_k=k, val_rate=rate, val_ci_lo=lo, val_ci_hi=hi, val_base=b, val_effect=eff,
                 val_p_one_sided=p, val_same_sign=same, val_half_effect=big, val_pass=passed, label=label,
                 val_small_n=n < 30)
        # ---- robustness on discovery + validation
        A = F[F.split.isin(["discovery", "validation"])]
        cond, base = rows_for(A, c)
        ea, na = effect(A, cond, base, c["target"])
        r.update(dv_n=na, dv_effect=ea)
        src = SOURCE[c["target"]]
        if src is not None and na >= 10:
            s = A.loc[cond, "src_" + src]
            ndrop = max(1, int(math.ceil(0.01 * na)))
            idx = (s.sort_values(ascending=(c["direction"] != "higher")).index[:ndrop])
            cond2 = cond.copy()
            cond2.loc[idx] = False
            r["drop1_effect"], _ = effect(A, cond2, base, c["target"])
        else:
            r["drop1_effect"] = np.nan
        sgn = np.sign(de)
        ys = []
        for yv, g in A.groupby("year"):
            cg, bg = cond.loc[g.index], base.loc[g.index]
            e, ng = effect(g, cg, bg, c["target"])
            yrows.append(dict(cid=c["cid"], by="year", group=yv, n=ng, effect=e))
            if ng >= 10 and not math.isnan(e):
                ys.append(np.sign(e) == sgn)
        r["years_tested"] = len(ys)
        r["years_same_sign"] = int(sum(ys))
        rs = []
        for rv, g in A.groupby("regime"):
            e, ng = effect(g, cond.loc[g.index], base.loc[g.index], c["target"])
            yrows.append(dict(cid=c["cid"], by="regime", group=rv, n=ng, effect=e))
            if ng >= 10 and not math.isnan(e):
                rs.append(np.sign(e) == sgn)
        r["regimes_tested"] = len(rs)
        r["regimes_same_sign"] = int(sum(rs))
        Dv = F[F.split == "discovery"]["vix_ref"].dropna()
        q1, q2 = Dv.quantile(1 / 3), Dv.quantile(2 / 3)
        terc = pd.cut(A["vix_ref"], [-np.inf, q1, q2, np.inf], labels=["low", "mid", "high"])
        vs = []
        for tv in ["low", "mid", "high"]:
            g = A[terc == tv]
            e, ng = effect(g, cond.loc[g.index], base.loc[g.index], c["target"])
            yrows.append(dict(cid=c["cid"], by="vix_tercile", group=tv, n=ng, effect=e))
            if ng >= 10 and not math.isnan(e):
                vs.append(np.sign(e) == sgn)
        r["vix_terciles_tested"] = len(vs)
        r["vix_terciles_same_sign"] = int(sum(vs))
        # neighbouring thresholds: every numeric threshold moved to its discovery quantile -/+ 0.05
        rule = json.loads(c["rule_json"])
        D = F[(F.split == "discovery") & F["t_" + c["target"]].notna()]
        nb = []
        if rule and any(x["op"] != "==" for x in rule):
            for shift in (-0.05, 0.05):
                r2 = []
                for x in rule:
                    if x["op"] == "==":
                        r2.append(x)
                        continue
                    d = D[x["f"]].dropna()
                    lev = float((d <= x["v"]).mean())
                    r2.append(dict(x, v=float(d.quantile(min(max(lev + shift, 0.01), 0.99)))))
                c2 = dict(c)
                c2["rule_json"] = json.dumps(r2)
                cn, bn = rows_for(A, c2)
                e, ng = effect(A, cn, bn, c["target"])
                nb.append(e)
                r[f"nb{'m' if shift < 0 else 'p'}_effect"] = e
                r[f"nb{'m' if shift < 0 else 'p'}_n"] = ng
        else:
            r["nbm_effect"] = r["nbp_effect"] = np.nan
        nb_ok = all(np.sign(e) == sgn for e in nb if not math.isnan(e)) if nb else True
        drop_ok = math.isnan(r["drop1_effect"]) or np.sign(r["drop1_effect"]) == sgn
        r["robust"] = bool(drop_ok and nb_ok
                           and (r["years_tested"] == 0 or r["years_same_sign"] / r["years_tested"] >= 0.6)
                           and r["regimes_same_sign"] == r["regimes_tested"]
                           and (r["vix_terciles_tested"] == 0
                                or r["vix_terciles_same_sign"] / r["vix_terciles_tested"] >= 2 / 3))
        out.append(r)
    R = C.merge(pd.DataFrame(out), on="cid")
    R["frozen_sha256"] = sha
    R.to_csv(OUT / "candidates_validation.csv", index=False)
    pd.DataFrame(yrows).to_csv(OUT / "robustness_groups.csv", index=False)
    print("frozen sha256:", sha)
    print("candidates:", len(R))
    print(R["label"].value_counts().to_string())
    print(R.groupby(["ul", "target"])["label"].value_counts().unstack(fill_value=0).to_string())
    print("passed and robust:", int((R.val_pass & R.robust).sum()))


if __name__ == "__main__":
    main()
