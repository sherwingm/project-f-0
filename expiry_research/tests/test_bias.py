"""Unit tests for the bias module helpers (reports/lld/bias.md)."""
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bias_common as bc  # noqa: E402


def test_binom_table_matches_scipy():
    rng = np.random.default_rng(1)
    for _ in range(40):
        n = int(rng.integers(5, 400))
        p0 = float(rng.uniform(0.05, 0.95))
        tab = bc.binom_two_sided_table(n, p0)
        for k in rng.integers(0, n + 1, 10):
            ref = stats.binomtest(int(k), n, p0).pvalue
            assert abs(tab[k] - ref) <= 1e-9 + 1e-6 * ref, (n, p0, k, tab[k], ref)


def test_week_permutation_keeps_blocks():
    dates = np.array(["2022-01-03", "2022-01-04", "2022-01-05", "2022-01-10", "2022-01-11",
                      "2022-01-17", "2022-01-18", "2022-01-19", "2022-01-20"])
    blocks = bc.week_blocks(dates)
    Y = np.arange(len(dates))
    rng = np.random.default_rng(3)
    for same in (False, True):
        for _ in range(20):
            Z = bc.permute_weeks(Y, blocks, rng, same_length=same)
            assert sorted(Z) == list(Y)
            # each original week appears as a contiguous increasing run
            for b in np.unique(blocks):
                rows = Y[blocks == b]
                pos = np.where(np.isin(Z, rows))[0]
                assert np.all(np.diff(pos) == 1) and np.all(np.diff(Z[pos]) == 1)
            if same:   # labels keep the slot length of their week
                lens = [np.sum(blocks == b) for b in np.unique(blocks)]
                assert len(Z) == sum(lens)


def test_auc_equals_mann_whitney():
    rng = np.random.default_rng(5)
    x = rng.normal(size=300)
    y = (x + rng.normal(size=300) > 0).astype(float)
    a, n1, n0, p = bc.auc(x, y)
    u = stats.mannwhitneyu(x[y == 1], x[y == 0]).statistic
    assert abs(a - u / (n1 * n0)) < 1e-12
    assert bc.auc(x, (x > 0).astype(float))[0] == 1.0


def test_context_tags_known_dates():
    P, _ = bc.load("NIFTY")
    r = P.set_index("date").loc["2024-06-26"]
    assert r["ctx"] == "D0" and r["xkind"] == "monthly" and r["y_date"] == "2024-06-27"
    r = P.set_index("date").loc["2024-06-20"]          # t+1 = Fri after Thu expiry
    assert r["ctx"] == "D+1" and r["dk"] == "D-4"
    assert (P["date"] < "2024-07-01").all()
    B, _ = bc.load("BANKNIFTY")
    r = B.set_index("date").loc["2024-06-25"]
    assert r["ctx"] == "D0" and r["xkind"] == "monthly" and r["wd_regime"] == "B3"
    assert set(B.loc[B["date"] < "2023-01-01", "wd_regime"]) == {"B1"}
