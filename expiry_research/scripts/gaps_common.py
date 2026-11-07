"""Shared data preparation for the gaps module (design: reports/lld/gaps.md).

prepare(ul) -> DataFrame of open-panel rows (discovery + validation) with tags for the target session t+1.
Reads panels only via panel_io.load_panel; minute files only for months <= 2024-06, rows <= 2024-06-30.
"""
import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel_io import load_panel  # noqa: E402

ROOT = HERE.parent
RES = ROOT / "results" / "gaps"
STORE = Path(os.environ.get("INDEX_STORE", str(ROOT.parent.parent / "fo-index-data" / "data" / "index")))
CUTOFF = "2024-06-30"
IX = {"NIFTY": "NIFTY50", "BANKNIFTY": "NIFTYBANK"}
FLAT = 0.1


def load_minutes(ul):
    """Minute bars 09:15..15:29 of `ul` with date <= CUTOFF (files after 2024-06 are never opened)."""
    files = sorted(glob.glob(str(STORE / f"spot_1m/{IX[ul]}/*.parquet")))
    files = [f for f in files if Path(f).stem <= CUTOFF[:7]]
    m = pd.concat([pd.read_parquet(f, columns=["timestamp", "open", "high", "low", "close"]) for f in files])
    m["timestamp"] = m["timestamp"].dt.tz_convert("Asia/Kolkata")
    m["date"] = m["timestamp"].dt.strftime("%Y-%m-%d")
    m = m[m["date"] <= CUTOFF]
    m["hm"] = m["timestamp"].dt.strftime("%H:%M")
    m = m[(m["hm"] >= "09:15") & (m["hm"] <= "15:29")]
    m = m.drop_duplicates("timestamp").sort_values("timestamp")
    return m


def minute_entry_outcomes(ul, prev_close):
    """Per date: returns from the 09:15 bar close (entry after the opening print) and a later fill flag.

    prev_close: Series date -> previous session close (px_close of t, keyed by date of t+1).
    """
    m = load_minutes(ul)
    rows = []
    for d, g in m.groupby("date", sort=True):
        g = g.set_index("hm")
        if "09:15" not in g.index or len(g) < 370:
            continue
        e = g.at["09:15", "close"]

        def at(hm):
            s = g.loc[g.index <= hm, "close"]
            return s.iloc[-1] if len(s) else np.nan

        pc = prev_close.get(d, np.nan)
        later = g.loc[g.index >= "09:16"]
        rows.append({"date": d, "e_entry": e,
                     "e_ret15": (at("09:29") / e - 1) * 100, "e_ret30": (at("09:44") / e - 1) * 100,
                     "e_ret60": (at("10:14") / e - 1) * 100, "e_oc": (at("15:29") / e - 1) * 100,
                     "e_lo_after": later["low"].min(), "e_hi_after": later["high"].max(), "e_prev_close": pc})
    return pd.DataFrame(rows)


def weekday_regime(ul, d):
    if ul == "NIFTY":
        return "N18_monthly_only" if d < "2019-02-11" else "N_thu_weekly"
    if d < "2023-09-01":
        return "B_thu"
    if d <= "2024-02-29":
        return "B_wed_weekly_thu_monthly"
    return "B_wed"


def gap_bucket(g):
    a = abs(g)
    if np.isnan(a):
        return np.nan
    if a < 0.1:
        return "flat"
    s = "up" if g > 0 else "down"
    if a < 0.3:
        b = "0.1-0.3"
    elif a < 0.5:
        b = "0.3-0.5"
    elif a < 1.0:
        b = "0.5-1.0"
    else:
        b = ">=1.0"
    return f"{s} {b}"


def own_streak(dirs):
    out, cur = [], 0
    for d in dirs:
        if d == "up":
            cur = cur + 1 if cur > 0 else 1
        elif d == "down":
            cur = cur - 1 if cur < 0 else -1
        else:
            cur = 0
        out.append(cur)
    return np.array(out)


def prepare(ul, with_minutes=True):
    P = load_panel(ul).sort_values("date").reset_index(drop=True)
    assert P["date"].max() <= CUTOFF
    P["g_streak"] = own_streak(P["o_gap_dir"].tolist())
    # minute entry outcomes of t+1 (keyed by y_date)
    if with_minutes:
        prev_close = pd.Series(P["px_close"].values, index=P["y_date"].values)
        M = minute_entry_outcomes(ul, prev_close)
        M = M.rename(columns={"date": "y_date"})
        P = P.merge(M, on="y_date", how="left")
        ok = P["y_src"].eq("spot_1m")
        for c in ["e_ret15", "e_ret30", "e_ret60", "e_oc", "e_lo_after", "e_hi_after"]:
            P.loc[~ok, c] = np.nan
        up = P["y_gap_pct"] > 0
        P["e_fill"] = np.where(P["e_ret15"].isna() | (P["y_gap_pct"] == 0), np.nan,
                               np.where(up, P["e_lo_after"] <= P["px_close"], P["e_hi_after"] >= P["px_close"]))
    keep = (~P["split_edge"].astype(bool)) & (~P["cal_special_between"].astype(bool)) & P["y_gap_pct"].notna()
    P = P[keep].copy()
    # context of t+1
    k = P["cal_next_sessions_to_expiry"]
    P["k"] = np.where(k.isna(), np.nan, np.minimum(k, 5))
    P["dplus1"] = (P["cal_next_sessions_since_expiry"] == 1) & (P["cal_next_is_expiry"] != True)  # noqa: E712
    P["d0"] = P["cal_next_is_expiry"] == True  # noqa: E712
    P["kind_ctx"] = np.where(P["d0"], P["cal_next_kind"],
                             np.where(P["dplus1"], P["cal_kind"], P["cal_next_upcoming_kind"]))
    P["regime"] = [weekday_regime(ul, d) for d in P["y_date"]]
    P["year"] = P["y_date"].str[:4]
    # gap features / labels
    P["y_sgn"] = np.sign(P["y_gap_pct"])
    P["y_bucket"] = [gap_bucket(g) for g in P["y_gap_pct"]]
    P["o_bucket"] = [gap_bucket(g) for g in P["o_gap_pct"]]
    P["y_abs_gap"] = P["y_gap_pct"].abs()
    P["y_up"] = (P["y_gap_dir"] == "up").astype(float)
    P["y_down"] = (P["y_gap_dir"] == "down").astype(float)
    P["y_oc_pos"] = (P["y_oc"] > 0).astype(float)
    P["y_oc_neg"] = (P["y_oc"] < 0).astype(float)
    P["y_cc_pos"] = (P["y_cc"] > 0).astype(float)
    P["y_cc_neg"] = (P["y_cc"] < 0).astype(float)
    nonflat = P["y_gap_dir"] != "flat"
    P["y_cont"] = np.where(nonflat, (np.sign(P["y_oc"]) == P["y_sgn"]).astype(float), np.nan)
    P["y_soc"] = np.where(nonflat, P["y_oc"] * P["y_sgn"], np.nan)  # signed oc: > 0 = continuation
    P["y_fill"] = np.where(nonflat, P["y_gap_filled"].astype(float), np.nan)
    for c in ["e_ret15", "e_ret30", "e_ret60", "e_oc"]:
        if c in P:
            P["s" + c] = np.where(nonflat, P[c] * P["y_sgn"], np.nan)
    if "e_fill" in P:
        P["e_fill"] = np.where(nonflat, P["e_fill"], np.nan).astype(float)
    # reversal of the previous gap at the next open
    pn = P["o_gap_dir"].isin(["up", "down"]) & nonflat
    P["rev"] = np.where(pn, (P["o_gap_dir"] != P["y_gap_dir"]).astype(float), np.nan)
    # behaviour metrics of t+1
    P["y_abs_cc"] = P["y_cc"].abs()
    P["y_abs_oc"] = P["y_oc"].abs()
    P["y_bigexc"] = P["y_big_move_exc"].astype(float)
    P["y_bigcc"] = P["y_big_move_cc"].astype(float)
    # VIX terciles with discovery cut points
    v = P.loc[P["split"] == "discovery", "f_vix_close"]
    c1, c2 = v.quantile([1 / 3, 2 / 3])
    P["vix_t"] = np.where(P["f_vix_close"].isna(), np.nan,
                          np.where(P["f_vix_close"] <= c1, 1, np.where(P["f_vix_close"] <= c2, 2, 3)))
    P.attrs["vix_cuts"] = (float(c1), float(c2))
    P["mom5_sgn"] = np.sign(P["f_mom5"])
    P["ul"] = ul
    return P.reset_index(drop=True)
