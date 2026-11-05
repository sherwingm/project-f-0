"""Checks for the pricepath module (reports/lld/pricepath.md). Run: pytest expiry_research/tests/test_pricepath.py"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from panel_io import load_panel  # noqa: E402
from pricepath_common import OUT, build_features, disc_quantiles  # noqa: E402

DERIVED = ["atr_prev", "abs_cc", "cc_n", "range_n", "gap_n", "persist", "nr4", "nr7", "hv_ratio", "rng3_pct", "up3",
           "dn3", "fbu3", "fbd3", "round_dist_pct", "ctx_W0", "ctx_M0", "ctx_W1", "ctx_M1", "ctx_X"]
FINAL_START = "2024-07-01"


@pytest.mark.parametrize("ul", ["NIFTY", "BANKNIFTY"])
def test_derived_features_use_past_only(ul):
    P = load_panel(ul)
    full = build_features(ul, P.copy()).set_index("date")
    rng = np.random.default_rng(7)
    dates = list(rng.choice(P["date"].iloc[30:].values, 8, replace=False)) + ["2022-12-30", "2019-02-14"]
    for d in dates:
        cut = build_features(ul, P[P["date"] <= d].copy()).set_index("date")
        a, b = full.loc[d, DERIVED], cut.loc[d, DERIVED]
        for c in DERIVED:
            if pd.isna(a[c]) and pd.isna(b[c]):
                continue
            assert a[c] == pytest.approx(b[c]), (ul, d, c)


def test_frozen_conditions_use_decision_time_inputs():
    F = pd.read_csv(OUT / "candidates_frozen.csv")
    late = {"o_cc", "o_oc", "o_range_pct", "o_max_exc", "o_last_hour", "o_rv", "o_high_min", "o_low_min",
            "o_gap_filled", "abs_cc", "range_n", "cc_n", "rng3_pct", "nr4", "nr7", "up3", "dn3", "fbu3", "fbd3"}
    for _, c in F[F["type"] == "rule"].iterrows():
        for col, _, _, _ in json.loads(c["cond_json"]):
            assert not col.startswith(("y_", "t_")), c["id"]
            if c["decision"] == "T1515(t)":
                assert col.startswith("f1515_"), c["id"]
                assert col not in late


def test_thresholds_are_discovery_quantiles():
    F = pd.read_csv(OUT / "candidates_frozen.csv")
    for ul in ["NIFTY", "BANKNIFTY"]:
        P = build_features(ul)
        sub = F[(F["ul"] == ul) & (F["type"] == "rule")]
        cols = {x[0] for cj in sub["cond_json"] for x in json.loads(cj) if x[3] is not None}
        Q = disc_quantiles(P, sorted(cols))
        for cj in sub["cond_json"]:
            for col, _, v, q in json.loads(cj):
                if q is not None:
                    assert v == pytest.approx(Q[col][q]), (ul, col, q)


def test_validation_used_the_frozen_file():
    F = pd.read_csv(OUT / "candidates_frozen.csv")
    V = pd.read_csv(OUT / "validation.csv")
    sha = hashlib.sha256((OUT / "candidates_frozen.csv").read_bytes()).hexdigest()[:16]
    assert set(V["frozen_sha256"]) == {sha}
    assert list(V["id"]) == list(F["id"])
    assert (OUT / "candidates_frozen.csv").stat().st_mtime < (OUT / "validation.csv").stat().st_mtime


def test_no_final_period_rows():
    for ul in ["NIFTY", "BANKNIFTY"]:
        X = pd.read_parquet(OUT / f"features_{ul}.parquet", columns=["date", "y_date"])
        assert X["date"].max() < FINAL_START
    pr = pd.read_csv(OUT / "predictions_frozen.csv", usecols=["date", "y_date"])
    assert pr["date"].max() < FINAL_START
    assert pr["y_date"].dropna().max() < FINAL_START


def test_discovery_stats_use_discovery_rows_only():
    H = pd.read_csv(OUT / "hypotheses.csv")
    for ul in ["NIFTY", "BANKNIFTY"]:
        P = build_features(ul)
        n_disc_w0 = int((P["split"].eq("discovery") & P["usable"] & P["ctx_W0"] & P["t_down"].notna()).sum())
        h = H[(H["ul"] == ul) & (H["context"] == "W0") & (H["target"] == "t_down")]
        assert (h["n_base"] == n_disc_w0).all()
