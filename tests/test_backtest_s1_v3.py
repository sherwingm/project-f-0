"""S1 v3: each score component, the selection, the stop rule and the purged out-of-sample model."""
import math

import numpy as np
import pandas as pd

from scanner import backtest_s1_v3 as v3
from scanner import model


def test_model_points_top_decile_each_way():
    assert v3.model_points(0.5, 0.2, 0.45, 0.4) == (3, 0)
    assert v3.model_points(0.3, 0.45, 0.45, 0.4) == (0, 3)
    assert v3.model_points(0.45, 0.4, 0.45, 0.4) == (3, 3)                  # at the cut counts
    assert v3.model_points(math.nan, math.nan, 0.45, 0.4) == (0, 0)          # no out-of-sample probability


def test_sector_points():
    assert v3.sector_points(1.0, 2.0) == (2, 0)
    assert v3.sector_points(1.0, -2.0) == (1, 1)
    assert v3.sector_points(-1.0, -2.0) == (0, 2)
    assert v3.sector_points(None, None) == (0, 0)


def test_event_session_and_points():
    cal = ["2026-09-24", "2026-09-25", "2026-09-28"]
    assert v3.event_session(cal, "2026-09-25", "15:29") == 1
    assert v3.event_session(cal, "2026-09-25", "15:30") == 2
    assert v3.event_session(cal, "2026-09-25", None) == 1                   # end-of-day file: that session
    assert v3.event_session(cal, "2026-09-26", "10:00") == 2                # Saturday: Monday
    assert v3.event_points({1}) == (2, 0) and v3.event_points({1, -1}) == (2, 2) and v3.event_points(set()) == (0, 0)


def test_volume_points_need_ratio_oi_and_the_close():
    assert v3.volume_points(1.6, 2.0, 0.01) == (1, 0)                       # long buildup
    assert v3.volume_points(1.6, 2.0, -0.01) == (0, 1)                      # short buildup
    assert v3.volume_points(1.5, 2.0, 0.01) == (0, 0)                       # ratio not above 1.5
    assert v3.volume_points(2.0, -1.0, 0.01) == (0, 0)                      # OI down
    assert v3.volume_points(2.0, None, 0.01) == (0, 0)


def test_direction_ties_and_atm():
    assert v3.direction(5, 2) == (1, 5) and v3.direction(1, 4) == (-1, 4) and v3.direction(3, 3) is None
    assert v3.atm_strike([90.0, 100.0, 110.0], 105.0) == 110.0              # tie: the higher
    assert v3.atm_strike([90.0, 100.0, 110.0], 103.0) == 100.0
    assert v3.liquid(100, 50 * 500, 500) and not v3.liquid(99, 1e9, 500) and not v3.liquid(100, 49 * 500, 500)


def test_select_top_score_ties_up_to_three_and_liquidity_zeroes():
    c = lambda s, sc, p: {"symbol": s, "score": sc, "p_dir": p}
    cands = [c("A", 6, 0.4), c("B", 6, 0.5), c("C", 6, 0.3), c("D", 6, 0.6), c("E", 7, 0.9), c("F", 5, 0.9)]
    got = [x["symbol"] for x in v3.select(cands, lambda x: x["symbol"] != "E")]
    assert got == ["D", "B", "A"]                          # E fails liquidity -> score 6 is the top; 4 tie -> 3
    assert [x["symbol"] for x in v3.select(cands, lambda x: True)] == ["E"]
    assert v3.select([c("A", 0, 0.9)], lambda x: True) == []                # score 0 never selected
    assert [x["symbol"] for x in v3.select([c("B", 2, math.nan), c("A", 2, math.nan)], lambda x: True)] == ["A", "B"]


def test_stop_rule():
    s = pd.DataFrame({"by": ["all", "all"], "horizon": [5, 20], "t_clustered": [3.0, 1.49]})
    assert v3.stop_rule(s) == (True, 1.49)
    s["t_clustered"] = [0.0, 1.5]
    assert v3.stop_rule(s) == (False, 1.5)


def test_oos_predictions_are_purged(monkeypatch):
    days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2021-01-01", "2021-06-30")]
    df = pd.DataFrame({"symbol": "A", "day": days, "quarter": [d[:4] + "Q" + str((int(d[5:7]) - 1) // 3 + 1) for d in days],
                       "y": ["up", "down", "flat"] * (len(days) // 3) + ["up"] * (len(days) % 3)})
    seen = []

    class Dummy:
        classes_ = np.array(["down", "flat", "up"])

        def fit(self, X, y):
            seen.append(len(y))

        def predict_proba(self, X):
            return np.tile([0.2, 0.3, 0.5], (len(X), 1))

    monkeypatch.setattr(model, "_make_model", lambda: (Dummy(), "dummy"))
    monkeypatch.setattr(model, "featurise", lambda d, names=None: (np.zeros((len(d), 1)), ["x"]))
    p = model.oos_predictions(df, min_train=10)
    q1 = [d for d in days if d < "2021-04-01"]
    assert seen == [len(q1) - 3]                                           # Q2's model: Q1 less its last 3 sessions
    assert p["day"].min() == "2021-04-01" and len(p) == len(days) - len(q1)
