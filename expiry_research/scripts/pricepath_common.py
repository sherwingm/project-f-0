"""pricepath: shared feature builder, contexts, targets and the rule engine (see reports/lld/pricepath.md).

Every derived feature of row t uses rows <= t only (rolling windows end at t; shifts are backward).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel_io import load_panel  # noqa: E402
from stats_utils import wilson, binom_p  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "results" / "pricepath"
ULS = ["NIFTY", "BANKNIFTY"]
ROUND_STEP = {"NIFTY": 500.0, "BANKNIFTY": 1000.0}


def wd_regime(ul, d):
    if ul == "NIFTY":
        return np.where(d < "2019-02-11", "thu_monthly_only", "thu_weekly")
    return np.where(d < "2023-09-01", "thu", np.where(d <= "2024-02-29", "wed_weekly_thu_monthly", "wed"))


def build_features(ul, P=None):
    """Open panel plus derived pricepath features. P can be passed (tests feed truncated panels)."""
    if P is None:
        P = load_panel(ul)
    P = P.sort_values("date").reset_index(drop=True).copy()
    h, l, c = P["px_high"], P["px_low"], P["px_close"]
    rng = h - l
    P["atr_prev"] = P["f_atr14_pct"].shift(1)
    P["abs_cc"] = P["o_cc"].abs()
    P["cc_n"] = P["abs_cc"] / P["atr_prev"]
    P["range_n"] = P["o_range_pct"] / P["atr_prev"]
    P["gap_n"] = P["o_gap_pct"].abs() / P["atr_prev"]
    s0, s1 = np.sign(P["o_cc"]), np.sign(P["o_cc"].shift(1))
    P["persist"] = np.where((s0 == 0) | (s1 == 0) | s0.isna() | s1.isna(), np.nan, (s0 == s1).astype(float))
    P["o_up"] = np.where(P["o_cc"].isna(), np.nan, (P["o_cc"] > 0).astype(float))
    P["nr4"] = (rng <= rng.rolling(4).min()).astype(float).where(rng.rolling(4).count() == 4)
    P["nr7"] = (rng <= rng.rolling(7).min()).astype(float).where(rng.rolling(7).count() == 7)
    P["hv_ratio"] = P["f_hv10"] / P["f_hv20"]
    P["rng3_pct"] = (h.rolling(3).max() - l.rolling(3).min()) / c * 100
    up = (P["o_cc"] > 0).astype(float).where(P["o_cc"].notna())
    dn = (P["o_cc"] < 0).astype(float).where(P["o_cc"].notna())
    P["up3"] = up.rolling(3).sum()
    P["dn3"] = dn.rolling(3).sum()
    ph, pl = h.shift(1), l.shift(1)
    fbu = ((h > ph) & (c < ph)).astype(float).where(ph.notna())
    fbd = ((l < pl) & (c > pl)).astype(float).where(pl.notna())
    P["fbu3"] = fbu.rolling(3).sum()
    P["fbd3"] = fbd.rolling(3).sum()
    step = ROUND_STEP[ul]
    P["round_dist_pct"] = (c - (c / step).round() * step).abs() / c * 100
    P["wd_regime"] = wd_regime(ul, P["date"].values)
    P["year"] = P["date"].str[:4].astype(int)
    # contexts of t+1 (known at TCLOSE(t))
    nk, nse, nuk = P["cal_next_kind"], P["cal_next_sessions_to_expiry"], P["cal_next_upcoming_kind"]
    P["ctx_W0"] = nk == "weekly"
    P["ctx_M0"] = nk == "monthly"
    P["ctx_W1"] = (nse == 1) & (nuk == "weekly")
    P["ctx_M1"] = (P["cal_next_sessions_to_monthly"] == 1)
    P["ctx_X"] = nk == "none"
    P["ctx_ALL"] = nk.notna() | True
    # targets (labels of t+1)
    yc = P["y_cc"]
    P["t_down"] = np.where(yc.isna(), np.nan, (yc < 0).astype(float))
    P["t_up"] = np.where(yc.isna(), np.nan, (yc > 0).astype(float))
    P["t_gap_up"] = np.where(P["y_gap_pct"].isna() | (P["y_gap_pct"] == 0), np.nan, (P["y_gap_pct"] > 0).astype(float))
    P["t_oc_up"] = np.where(P["y_oc"].isna(), np.nan, (P["y_oc"] > 0).astype(float))
    P["t_ret30_up"] = np.where(P["y_ret30"].isna(), np.nan, (P["y_ret30"] > 0).astype(float))
    P["t_big"] = P["y_big_move_exc"].astype(float).where(P["y_big_move_exc"].notna())
    sy, so = np.sign(yc), np.sign(P["o_cc"])
    P["t_rev"] = np.where(yc.isna() | P["o_cc"].isna() | (sy == 0) | (so == 0), np.nan, (sy != so).astype(float))
    syo = np.sign(P["y_oc"])
    P["t_rev_oc"] = np.where(P["y_oc"].isna() | P["o_cc"].isna() | (syo == 0) | (so == 0), np.nan,
                             (syo != so).astype(float))
    # usable rows for tests
    P["usable"] = (~P["split_edge"].astype(bool)) & (~P["cal_special_between"].fillna(False).astype(bool))
    return P


def disc_quantiles(P, cols, levels=(0.1, 0.15, 0.2, 0.25, 0.3, 0.7, 0.75, 0.8, 0.85, 0.9)):
    D = P[P["split"] == "discovery"]
    return {c: {q: float(D[c].quantile(q)) for q in levels} for c in cols}


def add_quantile_targets(P, Q):
    """Targets whose thresholds are discovery quantiles (Q from disc_quantiles on abs_cc and o_range_pct)."""
    a80 = Q["abs_cc"][0.8]
    r80, r20 = Q["o_range_pct"][0.8], Q["o_range_pct"][0.2]
    yc = P["y_cc"]
    P["t_sharp_fall"] = np.where(yc.isna(), np.nan, (yc <= -a80).astype(float))
    P["t_sharp_rise"] = np.where(yc.isna(), np.nan, (yc >= a80).astype(float))
    P["t_wide"] = np.where(P["y_range_pct"].isna(), np.nan, (P["y_range_pct"] >= r80).astype(float))
    P["t_quiet"] = np.where(P["y_range_pct"].isna(), np.nan, (P["y_range_pct"] <= r20).astype(float))
    return {"abs_cc_q80": a80, "range_q80": r80, "range_q20": r20}


OPS = {">=": np.greater_equal, "<=": np.less_equal, "==": np.equal}


def cond_mask(P, cond):
    """cond: list of (col, op, value). AND of all; NaN feature -> False."""
    m = pd.Series(True, index=P.index)
    for col, op, v in cond:
        x = P[col]
        m &= x.notna() & OPS[op](x.fillna(-1e18 if op == ">=" else 1e18), v)
    return m


def cond_text(cond):
    return " AND ".join(f"{c} {o} {v:.4g}" for c, o, v in cond)


def rate_test(P, mask_rows, sig, target):
    """Rows mask_rows (context, split, usable); sig: signal mask. Returns dict with n, k, rate, CI, base, p."""
    y = P.loc[mask_rows, target]
    y = y[y.notna()]
    s = sig.loc[y.index]
    n_base, k_base = len(y), int(y.sum())
    base = k_base / n_base if n_base else np.nan
    ys = y[s]
    n, k = len(ys), int(ys.sum())
    r, lo, hi = wilson(k, n)
    p = binom_p(k, n, base) if n and n_base else np.nan
    return dict(n=n, k=k, rate=r, ci_lo=lo, ci_hi=hi, base=base, n_base=n_base,
                effect=(r - base) if n else np.nan, p=p)
