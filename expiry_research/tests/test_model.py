"""Checks for the `model` module (reports/lld/model.md): decision-time hygiene of every feature set, D2 / T1515
alignment, label alignment, walk-forward fold hygiene, frozen-candidate integrity."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from model_common import (CUTOFFS, O_NEEDS_CLOSE, OUT, ULS, build_frame, feature_cols)  # noqa: E402
from panel_io import load_panel  # noqa: E402


@pytest.fixture(scope="module")
def frames():
    return {(ul, c): build_frame(ul, c) for ul in ULS for c in CUTOFFS}


def test_no_label_in_features(frames):
    for F in frames.values():
        for c in feature_cols(F):
            assert not c.startswith(("y_", "t_", "src_", "b_")), c
            assert "y_" not in c.split("_", 1)[0]


def test_t1515_has_no_close_information_of_t(frames):
    for ul in ULS:
        fc = feature_cols(frames[(ul, "T1515")])
        for c in fc:
            assert not c.startswith("f_"), f"f_ of t used at T1515: {c}"
            assert c not in O_NEEDS_CLOSE, f"close-dependent outcome of t used at T1515: {c}"
            assert c.startswith(("f1515_", "l1_", "c_", "o_gap_pct", "o_ret", "d_absgap")), c


def test_d2_features_are_previous_row(frames):
    for ul in ULS:
        P = load_panel(ul).sort_values("date").reset_index(drop=True)
        F = frames[(ul, "D2")]
        prev = dict(zip(P["date"].shift(-1).astype(str), P["f_vix_close"]))
        got = F.set_index("date_t")["l1_f_vix_close"]
        for d in got.index[5:400:37]:
            assert np.isclose(got[d], prev[str(d)], equal_nan=True)
        assert all(not c.startswith(("f_", "o_", "d_")) for c in feature_cols(F)), "D2 uses a value of t"


def test_target_is_next_session_outcome(frames):
    for ul in ULS:
        P = load_panel(ul).sort_values("date").reset_index(drop=True)
        nxt = dict(zip(P["date"].astype(str), P["o_gap_pct"]))
        F = frames[(ul, "TCLOSE")]
        for _, r in F.iloc[10:1500:97].iterrows():
            g = nxt[str(r["target_date"])]
            assert r["t_gap_abs"] == pytest.approx(abs(g))


def test_no_final_period_rows(frames):
    for F in frames.values():
        assert (F["target_date"] < "2024-07-01").all()
        assert set(F["split"]) <= {"discovery", "validation"}
        assert (F.loc[F.split == "discovery", "target_date"] <= "2022-12-31").all()


def test_walkforward_folds_are_chronological_and_purged():
    files = sorted(OUT.glob("predictions_*_*.csv"))
    if not files:
        pytest.skip("walk-forward not run yet")
    for f in files[:20]:
        D = pd.read_csv(f)
        ul, cut = f.stem.split("_")[1], f.stem.split("_")[-1]
        assert D["fold"].is_monotonic_increasing or D.sort_values("target_date")["fold"].is_monotonic_increasing
        for Y, g in D.groupby("fold"):
            assert (g["target_date"].str[:4].astype(int) == Y).all()
        assert D["target_date"].max() < "2024-07-01"
        # training rows of a fold are all before the fold: n_train equals the count of earlier rows minus the purge
        F = build_frame(ul, cut)
        tg = f.stem[len(f"predictions_{ul}_"):-len(cut) - 1]
        G = F[F["t_" + tg].notna()]
        for Y, g in D.groupby("fold"):
            assert g["n_train"].iloc[0] == (G["year"] < Y).sum() - 1


def test_frozen_hash_matches_validation():
    fz, val = OUT / "candidates_frozen.csv", OUT / "candidates_validation.csv"
    if not val.exists():
        pytest.skip("validation not run yet")
    sha = hashlib.sha256(fz.read_bytes()).hexdigest()
    assert (OUT / "candidates_frozen.sha256").read_text().strip() == sha
    V = pd.read_csv(val)
    assert (V["frozen_sha256"] == sha).all()
    C = pd.read_csv(fz)
    assert list(C["cid"]) == list(V["cid"])
    for r in C["rule_json"]:
        json.loads(r)


def test_validation_labels_follow_the_fixed_pass_rule():
    val = OUT / "candidates_validation.csv"
    if not val.exists():
        pytest.skip("validation not run yet")
    V = pd.read_csv(val)
    for _, r in V.iterrows():
        if r["val_n"] < 20:
            assert r["label"] == "Suggestive"
            continue
        same = np.sign(r["val_effect"]) == np.sign(r["disc_effect"])
        ok = bool(same and r["val_p_one_sided"] < 0.05 and abs(r["val_effect"]) >= 0.5 * abs(r["disc_effect"]))
        assert r["label"] == ("Passed-validation" if ok else "Rejected"), r["cid"]
    assert "Validated" not in set(V["label"])


def test_walkforward_has_no_selection_on_test_folds():
    f = OUT / "wf_primary.csv"
    if not f.exists():
        pytest.skip("walk-forward not run yet")
    P = pd.read_csv(f)
    assert set(P["model"]) == {"logit"}, "the primary model is fixed in advance (logit / ridge)"
    M = pd.read_csv(OUT / "wf_metrics.csv")
    assert (M.loc[(M.model == "logit") & (M.subset == "all"), "n"] > 0).all()
    # every prediction file covers only discovery + validation dates and has the fixed model columns
    for p in OUT.glob("predictions_*_*.csv"):
        D = pd.read_csv(p, usecols=lambda c: c in {"target_date", "logit", "tree", "rf", "hgb"})
        assert D["target_date"].max() < "2024-07-01"
        assert {"logit", "tree", "rf", "hgb"} <= set(D.columns)


def test_hypothesis_log_has_bh_over_whole_family():
    f = OUT / "hypotheses.csv"
    if not f.exists():
        pytest.skip("finalize not run yet")
    H = pd.read_csv(f)
    assert {"validation", "walkforward"} <= set(H["stage"])
    ok = H["p"].notna()
    assert H.loc[ok, "q_bh_all"].between(0, 1).all()
    assert (H.loc[ok, "q_bh_all"] >= H.loc[ok, "p"] - 1e-12).all()
