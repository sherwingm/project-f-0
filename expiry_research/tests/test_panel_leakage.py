"""Leakage and seal checks on the panels (see reports/lld/panel.md, Tests and change 2026-11-05).

Run from the repo root (loads the raw store, takes a few minutes):
    INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe -m pytest -p no:cacheprovider \
        expiry_research/tests/test_panel_leakage.py -q
(or run this file directly with python).

a. Cut every raw input at TCLOSE(t) (and separately at T1515(t)), rebuild, and require row t to be unchanged.
b. Recompute every y_ label of row t from the raw data of t+1 with separate code here, and require equality.
c. Every column has a dictionary entry with the availability its prefix implies.
d. Guard: no feature column is (almost) a copy of a next-session label.
e. Seal: the open panels hold no final-period row or label; the sealed files hold exactly the final rows + edge row;
   no cal_ / cal_next_ count uses an expiry that was not known on t.
Only the open panels (discovery + validation) are read in full. For final-period sample dates, test a reads only the
id / f_ / f1515_ / cal_ columns of the sealed files (panel_io.sealed_feature_columns); o_ / y_ / px_ stay unread.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_panel as bp  # noqa: E402
import panel_io  # noqa: E402

ULS = ["NIFTY", "BANKNIFTY", "SENSEX"]
PANELS = {ul: panel_io.load_panel(ul) for ul in ULS}
SEALED_F = {ul: panel_io.sealed_feature_columns(ul) for ul in ULS}       # id + f_ / f1515_ / cal_ only
SESS = {ul: pd.read_csv(ROOT / "data" / f"sessions_{ul}.csv", dtype=str) for ul in ULS}
DICT = pd.read_csv(ROOT / "data" / "panel_dictionary.csv")
_RAW = {}
pytestmark = pytest.mark.filterwarnings("ignore::pandas.errors.PerformanceWarning")

# sample dates: edges and ordinary days in every split (all are NIFTY sessions)
FIXED = ["2018-03-28", "2019-09-20", "2020-03-23", "2021-04-01", "2021-10-28", "2021-11-11", "2022-03-08",
         "2022-12-30", "2023-09-06", "2024-01-23", "2024-06-28", "2024-11-13", "2025-02-03", "2025-08-28",
         "2025-09-30", "2026-10-27"]


def raws():
    if "r" not in _RAW:
        _RAW["r"] = bp.load_raw_all()
    return _RAW["r"]


def sample_dates(n_random=6, seed=7):
    d = PANELS["NIFTY"]["date"]
    rnd = d.iloc[:-1].sample(n_random, random_state=seed).tolist()
    sealed = SEALED_F["NIFTY"].loc[SEALED_F["NIFTY"]["split"] == "final", "date"]
    return sorted(set(FIXED + rnd) & (set(d) | set(sealed)))


# ---------------------------------------------------------------- helpers
def cut_raw(r, t, mode, lookback_days=500):
    """Copy of the raw inputs as they stood at TCLOSE(t) or T1515(t); also cut 500 days on the left (speed)."""
    lo = (pd.Timestamp(t) - pd.Timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    keep_t = mode == "TCLOSE"

    def daily(df, col="date"):
        x = df[df[col] >= lo]
        return x[x[col] <= t] if keep_t else x[x[col] < t]

    def minutes(m):
        m = m[m["date"] >= lo]
        if keep_t:
            return m[m["date"] <= t]
        return m[(m["date"] < t) | ((m["date"] == t) & (m["mins"] <= bp.M_1514))]
    out = {"vixd": daily(r["vixd"]), "icd_vix": daily(r["icd_vix"]), "vixmin": minutes(r["vixmin"]),
           "special": r["special"], "cal": r["cal"], "nse_sess": r["nse_sess"]}
    for ul in ULS:
        x = r[ul]
        out[ul] = {"min": minutes(x["min"]), "icd": daily(x["icd"]),
                   "bhav": None if x["bhav"] is None else daily(x["bhav"], "TradDt"), "sess": x["sess"]}
    return out


def same(a, b):
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    if isinstance(a, (float, int, np.floating, np.integer)) and not isinstance(a, (bool, np.bool_)):
        return bool(np.isclose(float(a), float(b), rtol=1e-9, atol=1e-12))
    return a == b


def row_of(P, t):
    r = P[P["date"] == t]
    assert len(r) == 1, t
    return r.iloc[0]


# ---------------------------------------------------------------- a. truncation
def check_truncation(mode):
    r = raws()
    bad = []
    for t in sample_dates():
        cut = bp.build_all(cut_raw(r, t, mode))
        for ul in ULS:
            if t < panel_io.FINAL_START:
                full = PANELS[ul]
            else:                                       # sealed period: id + feature columns only
                full = SEALED_F[ul][SEALED_F[ul]["split"] == "final"]
            if t not in set(full["date"]):
                continue
            if mode == "TCLOSE":
                cols = [c for c in full.columns if (c.startswith("f_") or c.startswith("o_") or c.startswith("cal_")
                                                    or c.startswith("px_") or c in ("src", "m_ok"))]
            else:
                cols = [c for c in full.columns if c.startswith("f1515_")]
            a, b = row_of(full, t), row_of(cut[ul], t)
            for c in cols:
                if not same(a[c], b[c]):
                    bad.append((mode, ul, t, c, a[c], b[c]))
    assert not bad, f"{len(bad)} values change when the raw data is cut at {mode}: {bad[:10]}"


def test_a_features_known_at_tclose():
    check_truncation("TCLOSE")


def test_a_f1515_known_at_1515():
    check_truncation("T1515")


# ---------------------------------------------------------------- b. labels from raw t+1
def raw_daily(r, ul, d, src):
    """Daily OHLC of session d straight from the raw store, for the source the panel says it used."""
    if src == "index_close_daily":
        x = r[ul]["icd"]
        x = x[x["date"] == d].iloc[0]
        return x["open"], x["high"], x["low"], x["close"], None
    m = r[ul]["min"]
    m = m[m["date"] == d].sort_values("mins")
    return m["open"].iloc[0], m["high"].max(), m["low"].min(), m["close"].iloc[-1], m


def expected_labels(r, ul, t, t1, src_t, src_t1):
    c0 = raw_daily(r, ul, t, src_t)[3]
    o, h, low, c, m = raw_daily(r, ul, t1, src_t1)
    gap = (o / c0 - 1) * 100
    e = {"y_gap_pct": gap, "y_gap_sign": float(np.sign(gap)),
         "y_gap_dir": "flat" if abs(gap) < 0.1 else ("up" if gap > 0 else "down"),
         "y_oc": (c / o - 1) * 100, "y_cc": (c / c0 - 1) * 100,
         "y_high_vs_prevclose": (h / c0 - 1) * 100, "y_low_vs_prevclose": (low / c0 - 1) * 100,
         "y_range_pct": (h - low) / c0 * 100}
    e["y_max_exc"] = max(e["y_high_vs_prevclose"], -e["y_low_vs_prevclose"])
    e["y_big_move_cc"] = abs(e["y_cc"]) >= 1.0
    e["y_big_move_exc"] = e["y_max_exc"] >= 1.0
    e["y_gap_filled"] = (low <= c0) if gap > 0 else ((h >= c0) if gap < 0 else np.nan)
    if m is not None and src_t1 == "spot_1m":
        def at(hh, mm):
            k = (hh - 9) * 60 + mm - 15
            return m[m["mins"] <= k]["close"].iloc[-1]
        e["y_ret15"] = (at(9, 29) / o - 1) * 100
        e["y_ret30"] = (at(9, 44) / o - 1) * 100
        e["y_ret60"] = (at(10, 14) / o - 1) * 100
        e["y_last_hour"] = (c / at(14, 29) - 1) * 100
        prev = m["close"].shift(1).to_numpy()
        prev[0] = m["open"].iloc[0]
        e["y_rv"] = float(np.sqrt(np.sum(np.log(m["close"].to_numpy() / prev) ** 2)) * 100)
        e["y_high_min"] = float(m["mins"].iloc[int(np.argmax(m["high"].to_numpy()))])
        e["y_low_min"] = float(m["mins"].iloc[int(np.argmin(m["low"].to_numpy()))])
        if gap > 0:
            hit = m[m["low"] <= c0]
        elif gap < 0:
            hit = m[m["high"] >= c0]
        else:
            hit = m.iloc[0:0]
        e["y_gap_fill_min"] = float(hit["mins"].iloc[0]) if len(hit) else np.nan
    else:
        for k in ["y_ret15", "y_ret30", "y_ret60", "y_last_hour", "y_rv", "y_high_min", "y_low_min",
                  "y_gap_fill_min"]:
            e[k] = np.nan
    return e


def test_b_labels_from_next_session_raw():
    r = raws()
    bad, n = [], 0
    for ul in ULS:
        P = PANELS[ul].reset_index(drop=True)
        idx = sorted(set(P.sample(40, random_state=11).index.tolist()) - {len(P) - 1})
        for i in idx:
            a, b = P.iloc[i], P.iloc[i + 1]
            if a["src"] == "none" or b["src"] == "none":
                continue
            e = expected_labels(r, ul, a["date"], b["date"], a["src"], b["src"])
            assert a["y_date"] == b["date"] and a["y_src"] == b["src"]
            for k, v in e.items():
                n += 1
                if not same(a[k], v):
                    bad.append((ul, a["date"], k, a[k], v))
    assert n > 1000
    assert not bad, f"{len(bad)} labels differ from raw t+1: {bad[:10]}"


def test_b_label_is_next_rows_outcome():
    for ul, P in PANELS.items():
        for yc in [c for c in P.columns if c.startswith("y_") and c not in ("y_src", "y_date")]:
            oc = "o_" + yc[2:]
            a = P[yc].iloc[:-1].reset_index(drop=True)
            b = P[oc].iloc[1:].reset_index(drop=True)
            ok = (a.isna() & b.isna()) | (a == b)
            assert ok.all(), (ul, yc, int((~ok).sum()))
        # last open row (2024-06-28): its t+1 is a final session, so every label except y_date is sealed (blank)
        last = P.iloc[-1]
        assert last["y_date"] >= panel_io.FINAL_START
        assert last[[c for c in P.columns if c.startswith("y_") and c != "y_date"]].isna().all()


# ---------------------------------------------------------------- c. dictionary
def test_c_dictionary_complete():
    d = DICT.set_index("column")
    assert d.index.is_unique
    allowed = {"T1515(t)", "TCLOSE(t)", "OUTCOME(t)", "NEXT(t+1)"}
    assert set(d["availability"]) <= allowed
    want = {"f1515_": "T1515(t)", "f_": "TCLOSE(t)", "o_": "OUTCOME(t)", "y_": "NEXT(t+1)", "cal_": "TCLOSE(t)"}
    ids = {"date", "underlying", "split", "split_edge", "src", "m_ok", "n_bars", "px_open", "px_high", "px_low",
           "px_close", "px_close_official"}
    for ul, P in PANELS.items():
        for c in P.columns:
            assert c in d.index, f"{ul}: {c} has no dictionary entry"
            assert isinstance(d.loc[c, "definition"], str) and len(d.loc[c, "definition"]) > 5
            p = next((p for p in ["f1515_", "f_", "o_", "y_", "cal_"] if c.startswith(p)), None)
            if p is None:
                assert c in ids, f"{c}: unknown prefix"
                assert d.loc[c, "availability"] == "TCLOSE(t)"
            else:
                assert d.loc[c, "availability"] == want[p], c


# ---------------------------------------------------------------- d. guard
def test_d_no_feature_copies_a_label():
    for ul, P in PANELS.items():
        feats = [c for c in P.columns if c.split("_")[0] in ("f", "f1515", "o", "cal")
                 and pd.api.types.is_numeric_dtype(P[c]) and not pd.api.types.is_bool_dtype(P[c])]
        for y in ["y_gap_pct", "y_cc", "y_oc", "y_ret15", "y_range_pct"]:
            for f in feats:
                x = P[[f, y]].dropna()
                if len(x) < 100 or x[f].std() == 0:
                    continue
                rho = x[f].corr(x[y])
                assert abs(rho) < 0.9, (ul, f, y, rho)


# ---------------------------------------------------------------- e. seal and calendar known-from
def test_e_final_period_sealed():
    for ul, P in PANELS.items():
        assert (P["date"] < panel_io.FINAL_START).all() and set(P["split"]) <= {"discovery", "validation"}
        late = P["y_date"].fillna("") >= panel_io.FINAL_START
        ycols = [c for c in P.columns if c.startswith("y_") and c != "y_date"]
        assert late.sum() == 1 and P.loc[late, ycols].isna().all().all(), ul
        S = SEALED_F[ul]
        assert panel_io.sealed_schema(ul) == list(P.columns), ul       # same columns (labels kept in the sealed file)
        assert not any(c.startswith(("o_", "y_", "px_")) for c in S.columns)
        fin = S[S["split"] == "final"]
        assert (fin["date"] >= panel_io.FINAL_START).all()
        edge = S[S["split"] != "final"]
        assert list(edge["date"]) == [P["date"].iloc[-1]], ul         # the one edge row, unblanked in the sealed file
        # open + final rows = every panel session (none lost, none duplicated)
        sess = SESS["NIFTY"]
        sess = sess[sess["is_special_session"] == "False"]["date"]
        if ul == "SENSEX":
            sess = sess[sess >= bp.SENSEX_FIRST]
        assert sorted(P["date"].tolist() + fin["date"].tolist()) == sorted(sess.tolist()), ul
    try:
        panel_io.load_sealed_final("NIFTY")
        raise AssertionError("load_sealed_final opened without the coordinator flag")
    except PermissionError:
        pass


def test_e_cal_tags_use_known_expiries_only():
    """No cal_ count of t, and no cal_next_ count used at t, points to an expiry first known after t."""
    pairs = [("sessions_to_expiry", "next_expiry_known_from"), ("sessions_to_weekly", "next_weekly_known_from"),
             ("sessions_to_monthly", "next_monthly_known_from")]
    for ul in ULS:
        s = SESS[ul].set_index("date")
        for P in (PANELS[ul], SEALED_F[ul][SEALED_F[ul]["split"] == "final"]):
            P = P.reset_index(drop=True)
            today = P["date"].to_numpy().astype(str)
            nd = P["date"].shift(-1).fillna("")
            for tag, kcol in pairs:
                for col, keys in [("cal_" + tag, P["date"]), ("cal_next_" + tag, nd)]:
                    kf = s[kcol].reindex(keys).fillna("").to_numpy().astype(str)
                    bad = P[col].notna().to_numpy() & (kf != "") & (kf > today)
                    assert not bad.any(), (ul, col, P.loc[bad, "date"].tolist()[:5])
    n = PANELS["NIFTY"]
    pre = n[n["date"] < "2019-02-11"]
    assert len(pre) > 250
    assert pre["cal_sessions_to_weekly"].isna().all() and pre["cal_next_sessions_to_weekly"].isna().all()


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as ex:
                fails += 1
                print("FAIL", name, str(ex)[:2000])
    sys.exit(1 if fails else 0)
