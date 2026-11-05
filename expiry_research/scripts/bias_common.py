"""Shared helpers for the bias module (design: reports/lld/bias.md)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel_io import load_panel  # noqa: E402
import stats_utils as su  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "results" / "bias"
OUT.mkdir(parents=True, exist_ok=True)
ULS = ["NIFTY", "BANKNIFTY"]
OPEN_END = "2024-06-30"
TARGETS = ["gap_up", "gap_down", "oc_pos", "cc_pos", "big_cc", "big_exc"]
COVID = ("2020-02-20", "2020-06-30")
SEED = 20261105

# 20 TCLOSE features for the mining null (>= 95 % discovery coverage, no level / date columns)
MINING_FEATURES = [
    "f_body_frac", "f_close_pos", "f_upper_wick_frac", "f_streak_close", "f_streak_gap", "f_mom1", "f_mom3",
    "f_mom5", "f_mom20", "f_dist_high20", "f_dist_low20", "f_hv10", "f_atr14_pct", "f_vix_close", "f_vix_chg1",
    "f_vix_chg5", "f_fut_basis_pct", "f_fut_oi_r20", "f_opt_near_pcr_oi", "f_opt_near_straddle_pct",
]


def _f(s):
    """Nullable boolean / object -> float (NaN for missing)."""
    return pd.to_numeric(s.astype("object").where(s.notna(), np.nan), errors="coerce").astype(float)


def wd_regime(ul, d):
    if ul == "NIFTY":
        return np.where(d < "2019-02-11", "N0", "N1")
    return np.where(d <= "2023-09-01", "B1", np.where(d <= "2024-02-29", "B2", "B3"))


def load(ul):
    """Open panel with bias tags and binary targets. Rows t <= 2024-06-28 only (load_panel guarantees it)."""
    P = load_panel(ul).copy()
    assert (P["date"] < "2024-07-01").all()
    s2e = P["cal_next_sessions_to_expiry"]
    since = P["cal_next_sessions_since_expiry"]
    ctx = np.where(s2e.isna(), "unknown",
                   np.where(s2e == 0, "D0",
                            np.where(since == 1, "D+1",
                                     np.where(s2e >= 6, "D-6+", "D-" + s2e.fillna(-1).astype(int).astype(str)))))
    P["ctx"] = ctx
    P["dk"] = np.where(s2e.isna(), "unknown",
                       np.where(s2e == 0, "D0",
                                np.where(s2e >= 6, "D-6+", "D-" + s2e.fillna(-1).astype(int).astype(str))))
    P["xkind"] = P["cal_next_upcoming_kind"].fillna("unknown")
    P["wd_regime"] = wd_regime(ul, P["y_date"].fillna(P["cal_next_date"]).fillna(P["date"]))
    disc = P["split"] == "discovery"
    cuts = P.loc[disc, "f_vix_close"].quantile([1 / 3, 2 / 3]).values
    P["vix_terc"] = pd.cut(P["f_vix_close"], [-np.inf, cuts[0], cuts[1], np.inf], labels=["low", "mid", "high"]).astype(str)
    yd = P["y_date"].fillna("")
    P["covid"] = (yd >= COVID[0]) & (yd <= COVID[1])
    dn = P["cal_days_to_next_session"]
    P["gap_after"] = np.where(dn == 1, "1d", np.where(dn <= 3, "2-3d", "4d+"))
    P["year"] = yd.str[:4]
    gd = P["y_gap_dir"]
    P["gap_up"] = np.where(gd.isna(), np.nan, (gd == "up").astype(float))
    P["gap_down"] = np.where(gd.isna(), np.nan, (gd == "down").astype(float))
    P["gap_flat"] = np.where(gd.isna(), np.nan, (gd == "flat").astype(float))
    P["oc_pos"] = np.where(P["y_oc"].isna(), np.nan, (P["y_oc"] > 0).astype(float))
    P["cc_pos"] = np.where(P["y_cc"].isna(), np.nan, (P["y_cc"] > 0).astype(float))
    P["big_cc"] = _f(P["y_big_move_cc"])
    P["big_exc"] = _f(P["y_big_move_exc"])
    P["usable"] = (~P["split_edge"].astype(bool)) & P[TARGETS].notna().all(axis=1)
    return P, cuts


# ---------------------------------------------------------------- statistics
def binom_two_sided_table(n, p0):
    """Exact two-sided binomial p for k = 0..n (scipy 'minlike' rule: sum of pmf <= pmf(k))."""
    k = np.arange(n + 1)
    pmf = stats.binom.pmf(k, n, p0)
    order = np.sort(pmf)
    csum = np.cumsum(order)
    idx = np.searchsorted(order, pmf * (1 + 1e-7), side="right")
    p = csum[idx - 1]
    return np.minimum(p, 1.0)


def auc(x, y):
    """AUC of score x for binary y (ties count 1/2); NaNs dropped. Returns (auc, n1, n0, mann-whitney p)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    ok = ~np.isnan(x) & ~np.isnan(y)
    x, y = x[ok], y[ok]
    n1, n0 = int((y == 1).sum()), int((y == 0).sum())
    if n1 == 0 or n0 == 0:
        return (np.nan, n1, n0, np.nan)
    r = stats.rankdata(x)
    u = r[y == 1].sum() - n1 * (n1 + 1) / 2
    a = u / (n1 * n0)
    if np.unique(x).size < 2:
        return (a, n1, n0, np.nan)
    p = stats.mannwhitneyu(x[y == 1], x[y == 0], alternative="two-sided").pvalue
    return (float(a), n1, n0, float(p))


def week_blocks(dates):
    """Integer block id per row: ISO year-week of t."""
    d = pd.to_datetime(pd.Series(dates).values)
    iso = d.isocalendar()
    return (iso["year"].astype(int) * 100 + iso["week"].astype(int)).values


def perm_index(blocks, rng, same_length=False):
    """Row index that permutes whole week blocks (rows in date order) and concatenates them in the new order.

    same_length=True shuffles weeks only among weeks with the same number of rows (labels keep their slot)."""
    blocks = np.asarray(blocks)
    change = np.r_[True, blocks[1:] != blocks[:-1]]
    start = np.where(change)[0]
    ends = np.r_[start[1:], len(blocks)]
    segs = [np.arange(s, e) for s, e in zip(start, ends)]
    if not same_length:
        perm = rng.permutation(len(segs))
        return np.concatenate([segs[i] for i in perm])
    lens = np.array([len(s) for s in segs])
    new = np.arange(len(segs))
    for L in np.unique(lens):
        w = np.where(lens == L)[0]
        new[w] = rng.permutation(w)
    return np.concatenate([segs[i] for i in new])


def permute_weeks(Y, blocks, rng, same_length=False):
    return Y[perm_index(blocks, rng, same_length)]


def rate_row(k, n, p0):
    r, lo, hi = su.wilson(k, n)
    return dict(n=int(n), k=int(k), rate=r, ci_lo=lo, ci_hi=hi, base=p0, diff=(r - p0) if n else np.nan,
                p=su.binom_p(k, n, p0) if n else np.nan, small_n=n < 30)


def log_out(name):
    """Tee stdout to results/bias/<name>_stdout.txt."""
    f = open(OUT / f"{name}_stdout.txt", "w", encoding="utf-8")

    class Tee:
        def write(self, s):
            sys.__stdout__.write(s)
            if not f.closed:
                f.write(s)

        def flush(self):
            sys.__stdout__.flush()
            if not f.closed:
                f.flush()
    sys.stdout = Tee()
    return f
