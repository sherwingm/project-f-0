"""Shared definitions for module optionchain (contexts, signals, targets, buckets, structural measures).

Used by optionchain_discovery.py and optionchain_validation.py so both compute exactly the same thing.
Design: reports/lld/optionchain.md.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
OUT = ROOT / "results" / "optionchain"
CUTOFF = pd.Timestamp("2024-06-30")
ULS = ["NIFTY", "BANKNIFTY"]
CTXS = ["ALL", "NW", "NM", "D2"]

DIR_SIGNALS = ["pcr_oi", "pcr_vol", "pcr_oi_chg", "net_oi_flow", "mon_pcr_oi", "atmz_pcr", "atmz_flow",
               "maxpain_dist", "wall_skew", "basis_ann"]
DIR_CATS = {"fut_build": ["LB", "SB", "SC", "LU"], "opt_build": ["UP_PW", "UP_CW", "DN_PW", "DN_CW"]}
VOL_SIGNALS = ["iv", "iv_chg", "strad_chg", "iv_hv", "vol_surge", "top3", "wall_width", "wall_near", "fut_oi_abs",
               "mp_abs"]
DIR_TARGETS = ["gap_up", "oc_up", "ret30_up", "cc_up"]
VOL_TARGETS = ["gap_big", "range_big", "big_move", "gap_fill"]
# continuous outcome behind each binary target, and which sign is "favourable" for that binary
CONT = {"gap_up": "gap", "oc_up": "oc", "ret30_up": "ret30", "cc_up": "cc", "gap_big": "agap",
        "range_big": "range", "big_move": "maxexc", "gap_fill": "gap_fill"}


def load_features(ul):
    F = pd.read_parquet(OUT / f"features_{ul}.parquet")
    F["date"] = pd.to_datetime(F["date"])
    assert F["date"].max() <= CUTOFF
    return F.sort_values("date").reset_index(drop=True)


def regime(ul, d):
    d = pd.Timestamp(d)
    if ul == "NIFTY":
        return "monthly_only_2018" if d < pd.Timestamp("2019-02-11") else "thu_weekly"
    return "thu_weekly" if d < pd.Timestamp("2023-09-01") else "wed_weekly"


def context_frame(F, ul, ctx):
    """Rows of a context with continuous outcomes (gap, oc, ret30, cc, agap, range, maxexc, gap_fill) for the target
    session: t+1 for ALL / NW / NM, t+2 for D2. split_edge rows and rows whose target session is in a later split
    are dropped."""
    F = F[F["split_edge"] != True].copy()  # noqa: E712
    if ctx == "D2":
        F = F[F["cal_next_sessions_to_expiry"] == 1].copy()
        tgt_date = pd.to_datetime(F["n_y_date"])
        F["gap"] = F["n_y_gap_pct"]
        F["oc"] = F["n_y_oc"]
        F["ret30"] = F["n_y_ret30"]
        F["cc"] = ((1 + F["y_cc"] / 100) * (1 + F["n_y_cc"] / 100) - 1) * 100
        F["range"] = F["n_y_range_pct"]
        F["maxexc"] = F["n_y_max_exc"]
        F["big"] = F["n_y_big_move_exc"]
        F["gap_fill"] = F["n_y_gap_filled"]
        F["S_target"] = F["close_official_t2"]
        F["target_date"] = tgt_date
    else:
        if ctx == "NW":
            F = F[F["cal_next_kind"] == "weekly"].copy()
        elif ctx == "NM":
            F = F[F["cal_next_kind"] == "monthly"].copy()
        F["gap"] = F["y_gap_pct"]
        F["oc"] = F["y_oc"]
        F["ret30"] = F["y_ret30"]
        F["cc"] = F["y_cc"]
        F["range"] = F["y_range_pct"]
        F["maxexc"] = F["y_max_exc"]
        F["big"] = F["y_big_move_exc"]
        F["gap_fill"] = F["y_gap_filled"]
        F["S_target"] = F["close_official_t1"]
        F["target_date"] = pd.to_datetime(F["y_date"])
    F = F[F["target_date"].notna() & (F["target_date"] <= CUTOFF)]
    tsplit = np.where(F["target_date"] < pd.Timestamp("2023-01-01"), "discovery", "validation")
    F = F[tsplit == F["split"].values].copy()
    F["agap"] = F["gap"].abs()
    for c in ["big", "gap_fill"]:
        F[c] = F[c].astype("float")
    F["regime"] = [regime(ul, d) for d in F["date"]]
    return F


def binary_target(C, target, med):
    """med: dict with discovery medians {'agap': x, 'range': y} of this ul/ctx."""
    if target == "gap_up":
        y = C["gap"] > 0
        v = C["gap"]
    elif target == "oc_up":
        y, v = C["oc"] > 0, C["oc"]
    elif target == "ret30_up":
        y, v = C["ret30"] > 0, C["ret30"]
    elif target == "cc_up":
        y, v = C["cc"] > 0, C["cc"]
    elif target == "gap_big":
        y, v = C["agap"] > med["agap"], C["agap"]
    elif target == "range_big":
        y, v = C["range"] > med["range"], C["range"]
    elif target == "big_move":
        y, v = C["big"] > 0.5, C["maxexc"]
    elif target == "gap_fill":
        y, v = C["gap_fill"] > 0.5, C["gap_fill"]
    else:
        raise ValueError(target)
    src = CONT[target]
    src_col = {"agap": "agap", "maxexc": "maxexc"}.get(src, src)
    ok = C[src_col].notna()
    return y.astype(float).where(ok), v.where(ok)


def bucket_mask(C, signal, bucket, thr, tail=None):
    """thr: dict of discovery quantiles for this signal {'q30','q33','q40','q60','q67','q70'}; tail in
    {None (=1/3), 0.30, 0.40}."""
    if signal in DIR_CATS:
        return C[signal] == bucket
    x = C[signal]
    lo_key, hi_key = {None: ("q33", "q67"), 0.30: ("q30", "q70"), 0.40: ("q40", "q60")}[tail]
    if bucket == "hi":
        return x >= thr[hi_key]
    if bucket == "lo":
        return x <= thr[lo_key]
    raise ValueError(bucket)


def thresholds(Cdisc, signal):
    x = Cdisc[signal].dropna()
    qs = {"q30": 0.30, "q33": 1 / 3, "q40": 0.40, "q60": 0.60, "q67": 2 / 3, "q70": 0.70}
    return {k: float(x.quantile(v)) if len(x) else np.nan for k, v in qs.items()}


def target_list(signal):
    return DIR_TARGETS if (signal in DIR_SIGNALS or signal in DIR_CATS) else VOL_TARGETS


def buckets(signal):
    return DIR_CATS[signal] if signal in DIR_CATS else ["hi", "lo"]


def all_signals():
    return DIR_SIGNALS + list(DIR_CATS) + VOL_SIGNALS


# ---------- structural measures ----------
def mp_toward(C, min_dist=0.0):
    """closer: |maxpain - S_target| < |maxpain - close_t|; agree: sign(S_target - close_t) == sign(maxpain - close_t).
    Rows need |maxpain_dist| >= min_dist (%)."""
    S0 = C["close_official"]
    mp = C["f_opt_near_maxpain"]
    S1 = C["S_target"]
    ok = S1.notna() & mp.notna() & (C["maxpain_dist"].abs() >= min_dist) & (mp != S0)
    closer = ((mp - S1).abs() < (mp - S0).abs()).astype(float).where(ok)
    agree = (np.sign(S1 - S0) == np.sign(mp - S0)).astype(float).where(ok)
    return closer, agree


def straddle_measure(C):
    """D-1 / D-2 ATM straddle (settle on t) held to the near expiry's final settlement.
    Only rows whose near expiry is the target session. Returns frame with cost%, payoff%, diff%, ratio."""
    ok = (pd.to_datetime(C["f_opt_near_expiry"]) == C["target_date"]) | (
        C["settle_index_near"].isna() & C["S_target"].notna())
    ok &= C["f_opt_near_straddle_pct"].notna() & C["S_target"].notna()
    D = C[ok].copy()
    SE = D["settle_index_near"].where(pd.to_datetime(D["f_opt_near_expiry"]) == D["target_date"])
    D["S_E"] = SE.fillna(D["S_target"])
    D["S_E_src"] = np.where(SE.notna(), "bhavcopy_settlement", "official_close")
    K = D["f_opt_near_atm_strike"]
    D["cost_pct"] = D["f_opt_near_straddle_pct"]
    D["payoff_pct"] = (D["S_E"] - K).abs() / D["px_close"] * 100
    D["diff_pct"] = D["payoff_pct"] - D["cost_pct"]
    D["ratio"] = D["payoff_pct"] / D["cost_pct"]
    D["realised_move_pct"] = (D["S_E"] / D["close_official"] - 1).abs() * 100
    D["maxexc_vs_cost"] = D["maxexc"] - D["cost_pct"]
    return D
