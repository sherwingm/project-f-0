"""Date-clustered t-statistics. Stock returns on the same day move together (the whole market moves), so treating
every stock-day as independent overstates t. These cluster the standard error by date (one-way cluster-robust,
CR1 small-sample correction), the rule the strategy gate in DECISIONS.md uses.

    clustered_t(values, dates)                       t of the mean
    clustered_diff_t(values, dates, base, base_dates) t of mean(values) - mean(base), both clustered by date
"""
from __future__ import annotations

import math

import numpy as np


def _clean(values, clusters):
    v = np.asarray(values, dtype=float)
    c = np.asarray(clusters, dtype=object)
    keep = ~np.isnan(v)
    return v[keep], c[keep]


def clustered_t(values, clusters) -> float | None:
    """Mean / cluster-robust SE, clustering on `clusters` (dates). None with fewer than 2 clusters."""
    v, c = _clean(values, clusters)
    n = len(v)
    groups = {}
    if n:
        e = v - v.mean()
        for ci, ei in zip(c, e):
            groups[ci] = groups.get(ci, 0.0) + ei
    g = len(groups)
    if g < 2:
        return None
    var = g / (g - 1) * sum(s * s for s in groups.values()) / (n * n)     # CR1 for a mean (k = 1)
    return round(float(v.mean() / math.sqrt(var)), 3) if var > 0 else None


def clustered_diff_t(values, clusters, base, base_clusters) -> float | None:
    """t of the difference in means: OLS of y on [1, is_group] over both samples, errors clustered by date
    (a date shared by both samples is one cluster), CR1 correction."""
    y1, c1 = _clean(values, clusters)
    y0, c0 = _clean(base, base_clusters)
    if len(y1) < 2 or len(y0) < 2:
        return None
    y = np.concatenate([y1, y0])
    d = np.concatenate([np.ones(len(y1)), np.zeros(len(y0))])
    cl = np.concatenate([c1, c0])
    X = np.column_stack([np.ones(len(y)), d])
    bread = np.linalg.inv(X.T @ X)
    beta = bread @ X.T @ y
    e = y - X @ beta
    meat = np.zeros((2, 2))
    idx: dict = {}
    for i, ci in enumerate(cl):
        idx.setdefault(ci, []).append(i)
    for rows in idx.values():
        s = X[rows].T @ e[rows]
        meat += np.outer(s, s)
    g, n, k = len(idx), len(y), 2
    if g < 2:
        return None
    v = g / (g - 1) * (n - 1) / (n - k) * bread @ meat @ bread
    return round(float(beta[1] / math.sqrt(v[1, 1])), 3) if v[1, 1] > 0 else None
