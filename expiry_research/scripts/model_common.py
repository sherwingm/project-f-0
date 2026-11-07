"""Shared frame builder for the `model` module (design: reports/lld/model.md).

build_frame(ul, cutoff) -> one row per target session s (= t+1) with
  meta columns (date_t, target_date, split, year, regime, context tags, vix_ref),
  feature columns (names returned by feature_cols(frame)),
  targets  (t_<name>), continuous sources (src_<name>), baseline inputs (b_prevgap, b_persist_<name>).
Only panel_io.load_panel is used (discovery + validation rows).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel_io import load_panel  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "results" / "model"
ULS = ["NIFTY", "BANKNIFTY"]
CUTOFFS = ["D2", "TCLOSE", "T1515"]
DISC_END = "2022-12-31"
VAL_START, VAL_END = "2023-01-01", "2024-06-30"

# TCLOSE(t) features of a decision row (stationary ones only; level columns excluded)
F_DAILY = [
    "f_body_frac", "f_upper_wick_frac", "f_lower_wick_frac", "f_close_pos", "f_streak_close", "f_streak_gap",
    "f_mom1", "f_mom3", "f_mom5", "f_mom10", "f_mom20", "f_dist_high20", "f_dist_low20", "f_dist_high55",
    "f_dist_low55", "f_hv10", "f_hv20", "f_atr14_pct", "f_vix_close", "f_vix_chg1", "f_vix_chg5", "f_vix_pctile_1y",
    "f_fut_basis_pct", "f_fut_oi_r20", "f_fut_vol_r20", "f_futall_oi_r20",
    "f_opt_near_dte", "f_opt_near_pcr_oi", "f_opt_near_pcr_vol", "f_opt_near_top3_oi_share",
    "f_opt_near_straddle_pct", "f_opt_near_maxpain_dist_pct", "f_opt_near_callwall_dist_pct",
    "f_opt_near_putwall_dist_pct", "f_opt_near_straddle_chg1", "f_opt_near_is_monthly",
    "f_opt_mon_pcr_oi", "f_opt_mon_pcr_vol", "f_opt_mon_maxpain_dist_pct", "f_opt_mon_straddle_pct",
    "f_opt_mon_callwall_dist_pct", "f_opt_mon_putwall_dist_pct",
    "f_rel_bn_nifty_ret1", "f_rel_bn_nifty_ret5",
    "d_absmom1", "d_opt_near_netoichg", "d_opt_near_straddle_daily", "d_opt_near_atmvol_ratio",
]
# outcomes of t that are known at TCLOSE(t)
O_CLOSE = ["o_gap_pct", "d_absgap", "o_oc", "o_range_pct", "o_max_exc", "o_high_vs_prevclose",
           "o_low_vs_prevclose", "o_gap_filled", "o_ret15", "o_ret30", "o_ret60", "o_last_hour", "o_rv"]
# outcomes of t that are known by 10:15 of t (usable at T1515)
O_EARLY = ["o_gap_pct", "d_absgap", "o_ret15", "o_ret30", "o_ret60"]
# o_ columns that need the close of t: never usable at T1515
O_NEEDS_CLOSE = ["o_cc", "o_oc", "o_range_pct", "o_max_exc", "o_last_hour", "o_rv", "o_high_min", "o_low_min",
                 "o_gap_filled", "o_high_vs_prevclose", "o_low_vs_prevclose", "o_big_move_cc", "o_big_move_exc",
                 "o_gap_fill_min"]
F1515 = ["f1515_ret_to_1514", "f1515_ret_open_to_1514", "f1515_pos_in_range", "f1515_range_pct", "f1515_rv",
         "f1515_vix_1514", "f1515_vix_chg"]
CAL = ["c_sessions_to_expiry", "c_is_expiry", "c_is_monthly", "c_dow", "c_days_to_session", "c_sessions_since"]

BIN_TARGETS = ["gap_up", "ret15_up", "ret30_up", "ret60_up", "oc_up", "gap_filled", "big_exc", "big_cc"]
REG_TARGETS = ["gap_abs", "high_pc", "low_pc"]
TARGETS = BIN_TARGETS + REG_TARGETS
MINUTE_TARGETS = ["ret15_up", "ret30_up", "ret60_up"]
# continuous source of each target (for "drop the best 1 %"); favourable side follows the rule direction
SOURCE = {"gap_up": "y_gap_pct", "ret15_up": "y_ret15", "ret30_up": "y_ret30", "ret60_up": "y_ret60",
          "oc_up": "y_oc", "gap_filled": None, "big_exc": "y_max_exc", "big_cc": "abs_y_cc",
          "gap_abs": "gap_abs", "high_pc": "y_high_vs_prevclose", "low_pc": "y_low_vs_prevclose"}
DOW = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}


def _derive(P):
    P = P.copy()
    P["d_absgap"] = P["o_gap_pct"].abs()
    P["d_absmom1"] = P["f_mom1"].abs()
    tot = P["f_opt_near_ce_oi"] + P["f_opt_near_pe_oi"]
    P["d_opt_near_netoichg"] = (P["f_opt_near_pe_oi_chg"] - P["f_opt_near_ce_oi_chg"]) / tot.where(tot > 0)
    P["d_opt_near_straddle_daily"] = P["f_opt_near_straddle_pct"] / np.sqrt(P["f_opt_near_dte"].clip(lower=1))
    P["d_opt_near_atmvol_ratio"] = P["f_opt_near_atm_pe_vol"] / P["f_opt_near_atm_ce_vol"].where(
        P["f_opt_near_atm_ce_vol"] > 0)
    for c in ["o_gap_filled", "f_opt_near_is_monthly"]:
        P[c] = P[c].map({True: 1.0, False: 0.0, 1: 1.0, 0: 0.0}).astype(float)
    return P


def regime(ul, d):
    d = str(d)
    if ul == "NIFTY":
        return "2018 monthly-only" if d < "2019-02-14" else "Thu weekly"
    if d <= "2023-09-01":
        return "Thu"
    if d <= "2024-02-29":
        return "Wed weekly + Thu monthly"
    return "Wed"


def build_frame(ul, cutoff):
    assert cutoff in CUTOFFS
    P = _derive(load_panel(ul).sort_values("date").reset_index(drop=True))
    F = {}
    F["date_t"] = P["date"]
    F["target_date"] = P["y_date"]
    # calendar of s (published in advance)
    F["kind"] = P["cal_next_kind"]
    F["is_expiry"] = P["cal_next_is_expiry"].astype("boolean")
    F["s_to_exp"] = P["cal_next_sessions_to_expiry"]
    F["s_since_exp"] = P["cal_next_sessions_since_expiry"]
    F["dow"] = P["cal_next_dow"]
    F["c_sessions_to_expiry"] = P["cal_next_sessions_to_expiry"].astype(float)
    F["c_is_expiry"] = P["cal_next_is_expiry"].map({True: 1.0, False: 0.0}).astype(float)
    F["c_is_monthly"] = (P["cal_next_kind"] == "monthly").astype(float).where(P["cal_next_kind"].notna())
    F["c_dow"] = P["cal_next_dow"].map(DOW).astype(float)
    F["c_days_to_session"] = P["cal_days_to_next_session"].astype(float)
    F["c_sessions_since"] = P["cal_next_sessions_since_expiry"].astype(float)

    lag = P.shift(1)
    if cutoff == "TCLOSE":
        for c in F_DAILY + O_CLOSE:
            F[c] = P[c].astype(float)
        F["vix_ref"] = P["f_vix_close"]
        F["b_prevgap"] = np.sign(P["o_gap_pct"])
        last = P
        early = P
    elif cutoff == "D2":
        for c in F_DAILY + O_CLOSE:
            F["l1_" + c] = lag[c].astype(float)
        F["vix_ref"] = lag["f_vix_close"]
        F["b_prevgap"] = np.sign(lag["o_gap_pct"])
        last = lag
        early = lag
    else:  # T1515
        for c in F1515 + O_EARLY:
            F[c] = P[c].astype(float)
        for c in F_DAILY + O_CLOSE:
            F["l1_" + c] = lag[c].astype(float)
        F["vix_ref"] = lag["f_vix_close"]
        F["b_prevgap"] = np.sign(P["o_gap_pct"])
        last = lag      # fully known session
        early = P       # open-known outcomes of t
    # persistence inputs: same outcome of the last session for which it is known at the cutoff
    F["b_persist_gap_up"] = (early["o_gap_pct"] > 0).astype(float).where(early["o_gap_pct"].notna())
    for k in ["15", "30", "60"]:
        F[f"b_persist_ret{k}_up"] = (early[f"o_ret{k}"] > 0).astype(float).where(early[f"o_ret{k}"].notna())
    if cutoff == "T1515":
        x = P["f1515_ret_open_to_1514"]
        F["b_persist_oc_up"] = (x > 0).astype(float).where(x.notna())
    else:
        F["b_persist_oc_up"] = (last["o_oc"] > 0).astype(float).where(last["o_oc"].notna())
    F["b_persist_gap_filled"] = last["o_gap_filled"]
    F["b_persist_big_exc"] = (last["o_max_exc"] >= 1).astype(float).where(last["o_max_exc"].notna())
    F["b_persist_big_cc"] = (last["o_cc"].abs() >= 1).astype(float).where(last["o_cc"].notna())
    F["b_persist_gap_abs"] = early["o_gap_pct"].abs()
    F["b_persist_high_pc"] = last["o_high_vs_prevclose"]
    F["b_persist_low_pc"] = last["o_low_vs_prevclose"]

    # targets (labels of s)
    g = P["y_gap_pct"]
    F["t_gap_up"] = (g > 0).astype(float).where(g.notna() & (g != 0))
    for k in ["15", "30", "60"]:
        r = P[f"y_ret{k}"]
        F[f"t_ret{k}_up"] = (r > 0).astype(float).where(r.notna())
    F["t_oc_up"] = (P["y_oc"] > 0).astype(float).where(P["y_oc"].notna())
    F["t_gap_filled"] = P["y_gap_filled"].map({True: 1.0, False: 0.0}).astype(float)
    F["t_big_exc"] = (P["y_max_exc"] >= 1).astype(float).where(P["y_max_exc"].notna())
    F["t_big_cc"] = (P["y_cc"].abs() >= 1).astype(float).where(P["y_cc"].notna())
    F["t_gap_abs"] = g.abs()
    F["t_high_pc"] = P["y_high_vs_prevclose"]
    F["t_low_pc"] = P["y_low_vs_prevclose"]
    for c in ["y_gap_pct", "y_ret15", "y_ret30", "y_ret60", "y_oc", "y_max_exc", "y_high_vs_prevclose",
              "y_low_vs_prevclose"]:
        F["src_" + c] = P[c]
    F["src_abs_y_cc"] = P["y_cc"].abs()
    F["src_gap_abs"] = g.abs()

    F = pd.DataFrame(F, index=P.index)
    F["target_date"] = F["target_date"].astype("string")
    keep = F["target_date"].notna() & (F["target_date"] < "2024-07-01") & (P["cal_special_between"] != True)  # noqa: E712
    if cutoff == "T1515":
        keep &= P["f1515_ret_to_1514"].notna()
    F = F[keep].copy()
    F["target_date"] = F["target_date"].astype(str)
    assert (F["target_date"] < "2024-07-01").all()
    F["split"] = np.where(F["target_date"] <= DISC_END, "discovery",
                          np.where(F["target_date"] <= VAL_END, "validation", "final"))
    assert not (F["split"] == "final").any()
    F["year"] = F["target_date"].str[:4].astype(int)
    F["regime"] = [regime(ul, d) for d in F["target_date"]]
    F["ul"] = ul
    F["cutoff"] = cutoff
    return F.reset_index(drop=True)


def feature_cols(F):
    pre = ("f_", "f1515_", "o_", "d_", "l1_", "c_")
    return [c for c in F.columns if c.startswith(pre)]


def discover_cols(F):
    """Features used in the univariate / pair / tree search (calendar handled by contexts)."""
    return [c for c in feature_cols(F) if not c.startswith("c_")]


CONTEXTS = ["all", "D0", "D0w", "D0m", "Dm1", "Dm2", "Dm3", "Dm4", "Dm5", "Dp1", "nonexp",
            "Mon", "Tue", "Wed", "Thu", "Fri"]


def ctx_mask(F, ctx):
    ie = F["is_expiry"].fillna(False).astype(bool)
    if ctx == "all":
        return pd.Series(True, index=F.index)
    if ctx == "D0":
        return ie
    if ctx == "D0w":
        return ie & (F["kind"] == "weekly")
    if ctx == "D0m":
        return ie & (F["kind"] == "monthly")
    if ctx.startswith("Dm"):
        return F["s_to_exp"] == int(ctx[2:])
    if ctx == "Dp1":
        return (F["s_since_exp"] == 1) & ~ie
    if ctx == "nonexp":
        return F["is_expiry"].notna() & ~ie
    days = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday"}
    return F["dow"] == days[ctx]


def apply_rule(F, rule):
    """rule = list of {"f": col, "op": "<=" | ">=" | "<" | ">" | "==", "v": float}; empty = all rows.
    Returns (mask, present) where present = every rule feature is non-null."""
    m = pd.Series(True, index=F.index)
    present = pd.Series(True, index=F.index)
    for c in rule:
        x = F[c["f"]]
        present &= x.notna()
        op, v = c["op"], c["v"]
        if op == "<=":
            m &= x <= v
        elif op == ">=":
            m &= x >= v
        elif op == "<":
            m &= x < v
        elif op == ">":
            m &= x > v
        elif op == "==":
            m &= x == v
        else:
            raise ValueError(op)
    return m & present, present


def rule_text(rule):
    if not rule:
        return "(context only)"
    return " & ".join(f"{c['f']} {c['op']} {c['v']:.4g}" for c in rule)


def dumps(rule):
    return json.dumps(rule, separators=(",", ":"))
