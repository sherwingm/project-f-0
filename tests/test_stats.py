"""Date-clustered t: equals the ordinary t when every value is its own date, shrinks when a date moves together."""
import math

import numpy as np
import pytest

from scanner.stats import clustered_diff_t, clustered_t

RNG = np.random.default_rng(3)


def test_singleton_clusters_give_the_ordinary_t():
    v = RNG.normal(0.2, 1.0, 200)
    ordinary = v.mean() / (v.std(ddof=1) / math.sqrt(len(v)))
    assert clustered_t(v, range(200)) == pytest.approx(ordinary, abs=1e-3)


def test_a_common_daily_move_is_not_counted_as_independent_evidence():
    days = np.repeat(np.arange(20), 50)                          # 20 dates x 50 stocks
    common = RNG.normal(0.3, 2.0, 20)[days]                       # the whole market moves each day
    v = common + RNG.normal(0, 0.5, len(days))
    naive = v.mean() / (v.std(ddof=1) / math.sqrt(len(v)))
    t = clustered_t(v, days)
    assert abs(t) < abs(naive) / 3                                # far fewer independent observations than 1,000
    assert clustered_t([1.0, 2.0], ["d", "d"]) is None            # one cluster: no t
    assert clustered_t([1.0, float("nan"), 3.0], ["a", "b", "c"]) is not None


def test_difference_t_with_singletons_matches_hc1_and_shared_dates_shrink_it():
    a, b = RNG.normal(0.5, 1.0, 120), RNG.normal(0.0, 1.0, 150)
    n1, n0 = len(a), len(b)
    n = n1 + n0
    hc1 = n / (n - 2) * (a.var(ddof=0) / n1 + b.var(ddof=0) / n0)
    t = clustered_diff_t(a, range(n1), b, range(n1, n))
    assert t == pytest.approx((a.mean() - b.mean()) / math.sqrt(hc1), abs=1e-3)
    days = np.arange(30)
    shock = RNG.normal(0, 3, 30)
    x = np.repeat(shock, 5) + 0.4 + RNG.normal(0, 0.3, 150)      # label group
    y = np.repeat(shock, 20) + RNG.normal(0, 0.3, 600)          # base group, same dates
    assert clustered_diff_t(x, np.repeat(days, 5), y, np.repeat(days, 20)) > 5      # common shock cancels
