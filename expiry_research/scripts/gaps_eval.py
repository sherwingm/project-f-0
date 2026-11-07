"""Evaluation of one gaps spec on a set of rows (design: reports/lld/gaps.md). Uses stats_utils for every
rate interval, binomial / two-proportion test, BH and mean interval; scipy only for Welch t, chi-square,
the Cochran-Armitage tail and one-sided binomial tails."""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats_utils import binom_p, mean_ci, two_prop, wilson  # noqa: E402


def _companion(P, spec):
    c = spec.get("comp_col") or spec["outcome"]
    if c.startswith("-"):
        return -P[c[1:]]
    return P[c]


def masks(spec, P, prm=None):
    prm = spec["prm"] if prm is None else prm
    F = P[spec["uses"]]
    y = P[spec["outcome"]]
    valid = y.notna()
    if spec.get("minute"):
        valid &= P["src"].eq("spot_1m") & P["y_src"].eq("spot_1m") & F.notna().all(axis=1)
    A = spec["cond"](F, prm).fillna(False).astype(bool) & valid
    B = None
    if spec.get("comp") is not None:
        B = spec["comp"](F, prm).fillna(False).astype(bool) & valid
    return A, B, valid


def evaluate(spec, P, prm=None, sign=None, drop_best=False):
    """sign: expected direction (+1/-1) for the one-sided p (validation); drop_best: drop the best 1 % of A."""
    A, B, valid = masks(spec, P, prm)
    y = P[spec["outcome"]]
    kind = spec["kind"]
    if drop_best and kind in ("rate_vs_base", "rate_2g", "mean_2g"):
        s = sign if sign is not None else 1
        comp = _companion(P, spec)[A] * s
        nd = int(math.ceil(0.01 * A.sum()))
        if nd > 0:
            drop = comp.sort_values(ascending=False).index[:nd]
            A = A.copy()
            A.loc[drop] = False
    out = {"n": int(A.sum()), "nB": np.nan, "rate": np.nan, "base": np.nan, "effect": np.nan,
           "ci_lo": np.nan, "ci_hi": np.nan, "p": np.nan, "p1": np.nan}
    if kind == "rate_vs_base":
        n, k = int(A.sum()), float(y[A].sum())
        base = float(y[valid].mean()) if valid.any() else np.nan
        r, lo, hi = wilson(k, n)
        out.update(nB=int(valid.sum()), rate=r, base=base, effect=r - base, ci_lo=lo, ci_hi=hi,
                   p=binom_p(k, n, base) if n else np.nan)
        if sign is not None and n:
            out["p1"] = float(stats.binomtest(int(k), n, base, alternative="greater" if sign > 0 else "less").pvalue)
    elif kind == "rate_2g":
        n1, k1, n2, k2 = int(A.sum()), float(y[A].sum()), int(B.sum()), float(y[B].sum())
        r, lo, hi = wilson(k1, n1)
        rb = k2 / n2 if n2 else np.nan
        out.update(nB=n2, rate=r, base=rb, effect=r - rb, ci_lo=lo, ci_hi=hi, p=two_prop(k1, n1, k2, n2))
        if sign is not None and min(n1, n2) > 0:
            pp = (k1 + k2) / (n1 + n2)
            se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
            out["p1"] = float(stats.norm.sf(sign * (r - rb) / se)) if se > 0 else np.nan
    elif kind == "mean_2g":
        a, b = y[A].astype(float).values, y[B].astype(float).values
        m, lo, hi = mean_ci(a)
        out.update(nB=len(b), rate=m, base=float(b.mean()) if len(b) else np.nan, ci_lo=lo, ci_hi=hi)
        out["effect"] = out["rate"] - out["base"]
        if len(a) >= 2 and len(b) >= 2:
            t = stats.ttest_ind(a, b, equal_var=False)
            out["p"] = float(t.pvalue)
            if sign is not None:
                va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
                df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
                out["p1"] = float(stats.t.sf(sign * t.statistic, df))
    elif kind == "trend":
        sc = (4 - P.loc[A, "k"]).astype(float).values
        yy = y[A].astype(float).values
        n = len(yy)
        if n > 2 and yy.std() > 0:
            pbar = yy.mean()
            T = np.sum(sc * (yy - pbar))
            var = pbar * (1 - pbar) * np.sum((sc - sc.mean()) ** 2)
            z = T / math.sqrt(var)
            slope = np.polyfit(sc, yy, 1)[0]
            r0 = yy[sc == 4].mean() if (sc == 4).any() else np.nan
            out.update(rate=r0, base=pbar, effect=slope, p=float(2 * stats.norm.sf(abs(z))))
            if sign is not None:
                out["p1"] = float(stats.norm.sf(sign * z))
    elif kind == "chi2":
        tab = pd.crosstab(P.loc[A, "o_gap_dir"], y[A])
        if tab.shape[0] > 1 and tab.shape[1] > 1:
            chi2, p, dof, _ = stats.chi2_contingency(tab)
            v = math.sqrt(chi2 / (tab.values.sum() * (min(tab.shape) - 1)))
            out.update(effect=v, p=float(p), p1=float(p))
    return out


def passes(disc_effect, val):
    s = np.sign(disc_effect)
    ok_sign = np.sign(val["effect"]) == s
    ok_p = (val["p1"] < 0.05) if not np.isnan(val["p1"]) else False
    ok_size = abs(val["effect"]) >= 0.5 * abs(disc_effect)
    return bool(ok_sign and ok_p and ok_size), bool(ok_sign), bool(ok_p), bool(ok_size)
