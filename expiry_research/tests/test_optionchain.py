"""Checks for module optionchain (reports/lld/optionchain.md). Run with pytest from the repo root."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import optionchain_common as oc  # noqa: E402

OUT = ROOT / "results" / "optionchain"
CUT = pd.Timestamp("2024-06-30")


@pytest.mark.parametrize("ul", oc.ULS)
def test_no_date_after_cutoff(ul):
    F = oc.load_features(ul)
    assert F["date"].max() <= CUT
    for c in ["y_date", "n_y_date", "t1_date", "t2_date"]:
        d = pd.to_datetime(F[c])
        late = d > CUT
        # a late label date may exist only with blank label values
        if c == "t2_date":
            assert F.loc[late, "close_official_t2"].isna().all()
        if c == "t1_date":
            assert F.loc[late, "close_official_t1"].isna().all()
        if c in ("y_date", "n_y_date"):
            pre = "y_" if c == "y_date" else "n_y_"
            vals = [x for x in F.columns if x.startswith(pre) and x not in ("y_date", "n_y_date")]
            assert F.loc[late, vals].isna().all().all()


@pytest.mark.parametrize("ul", oc.ULS)
def test_d2_targets_are_next_row_labels(ul):
    F = oc.load_features(ul)
    C = oc.context_frame(F, ul, "D2")
    nxt = F.set_index("date").shift(-1)
    for d, row in C.head(50).iterrows():
        t = row["date"]
        assert np.isclose(row["oc"], nxt.loc[t, "y_oc"], equal_nan=True)
        assert np.isclose(row["range"], nxt.loc[t, "y_range_pct"], equal_nan=True)
    # t+2 must be an expiry: the near expiry listed on t equals the target date on almost every row
    eq = (pd.to_datetime(C["f_opt_near_expiry"]) == C["target_date"]).mean()
    assert eq > 0.98


@pytest.mark.parametrize("ul", oc.ULS)
def test_features_use_only_t(ul):
    """Recompute two features from panel columns of t and t-1 only."""
    F = oc.load_features(ul)
    same = F["f_opt_near_expiry"].eq(F["f_opt_near_expiry"].shift(1))
    exp = (F["f_opt_near_pcr_oi"] - F["f_opt_near_pcr_oi"].shift(1)).where(same)
    assert np.allclose(F["pcr_oi_chg"], exp, equal_nan=True)
    vol = F["f_opt_near_ce_vol"] + F["f_opt_near_pe_vol"]
    # vol_surge denominator uses only earlier rows (shift(1) inside each n_sess group)
    med = vol.groupby(F["n_sess"]).transform(lambda s: s.shift(1).rolling(5, min_periods=3).median())
    assert np.allclose(F["vol_surge"], vol / med, equal_nan=True)


def test_thresholds_from_discovery_only():
    th = pd.read_csv(OUT / "thresholds.csv")
    for ul in oc.ULS:
        F = oc.load_features(ul)
        C = oc.context_frame(F, ul, "ALL")
        Cd = C[C["split"] == "discovery"]
        r = th[(th.underlying == ul) & (th.ctx == "ALL") & (th.signal == "pcr_oi")].iloc[0]
        assert np.isclose(r["q67"], Cd["pcr_oi"].quantile(2 / 3))
        assert not np.isclose(r["q67"], C["pcr_oi"].quantile(2 / 3))


def test_frozen_file_has_no_validation_columns():
    fz = pd.read_csv(OUT / "candidates_frozen.csv")
    assert not [c for c in fz.columns if c.startswith("val_")]
    assert (fz["n"] >= 30).all()


def test_contexts_are_expiry_eves():
    for ul in oc.ULS:
        F = oc.load_features(ul)
        for ctx, kind in [("NW", "weekly"), ("NM", "monthly")]:
            C = oc.context_frame(F, ul, ctx)
            assert (C["cal_next_kind"] == kind).all()
            assert (C["cal_next_is_expiry"] == True).all()  # noqa: E712
