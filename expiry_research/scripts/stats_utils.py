"""Shared statistics for every research module (one implementation, so all reports compute the same way).

wilson(k, n)            95 % Wilson interval for a rate
binom_p(k, n, p0)       two-sided exact binomial test against a base rate p0
two_prop(k1,n1,k2,n2)   two-sided two-proportion z test (pooled)
bh(pvals, q)            Benjamini-Hochberg: adjusted q-values and reject flags at FDR q
mean_ci(x)              mean with a t interval
block_boot_mean(x, ...) mean with a moving-block bootstrap interval (serial dependence in daily series)
t_stat(x)               mean / (sd / sqrt n)
"""
import math

import numpy as np
from scipy import stats


def wilson(k, n, z=1.959964):
    if n == 0:
        return (math.nan, math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def binom_p(k, n, p0):
    if n == 0:
        return math.nan
    return float(stats.binomtest(int(k), int(n), p0).pvalue)


def two_prop(k1, n1, k2, n2):
    if min(n1, n2) == 0:
        return math.nan
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return math.nan
    z = (k1 / n1 - k2 / n2) / se
    return float(2 * stats.norm.sf(abs(z)))


def bh(pvals, q=0.10):
    p = np.asarray(pvals, dtype=float)
    out_q = np.full(p.shape, np.nan)
    ok = ~np.isnan(p)
    m = ok.sum()
    if m == 0:
        return out_q, np.zeros(p.shape, bool)
    idx = np.where(ok)[0]
    order = idx[np.argsort(p[idx])]
    ranked = p[order] * m / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out_q[order] = np.minimum(ranked, 1.0)
    return out_q, np.nan_to_num(out_q, nan=1.0) <= q


def t_stat(x):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2 or x.std(ddof=1) == 0:
        return math.nan
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))


def mean_ci(x, level=0.95):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 2:
        return (float(x.mean()) if n else math.nan, math.nan, math.nan)
    m, se = x.mean(), x.std(ddof=1) / math.sqrt(n)
    h = stats.t.ppf(0.5 + level / 2, n - 1) * se
    return (float(m), float(m - h), float(m + h))


def block_boot_mean(x, block=5, reps=5000, level=0.95, seed=20261105):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 2 * block:
        return mean_ci(x, level)
    rng = np.random.default_rng(seed)
    starts = np.arange(n - block + 1)
    nb = math.ceil(n / block)
    means = np.empty(reps)
    for r in range(reps):
        s = rng.choice(starts, nb)
        means[r] = np.concatenate([x[i:i + block] for i in s])[:n].mean()
    lo, hi = np.quantile(means, [(1 - level) / 2, 0.5 + level / 2])
    return (float(x.mean()), float(lo), float(hi))
