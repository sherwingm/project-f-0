"""Spec 12 step 7: the model — features, walk-forward discipline, metrics, scan inference."""
import numpy as np
import pandas as pd
import pytest

from scanner.model import (CLASSES, FLAG_COLS, _metrics, _top_decile, day_flags, featurise,
                           infer_for_scan, walk_forward)

RNG = np.random.default_rng(7)


def synth(n=9000, signal=True):
    """Planted pattern: f_order high and rating +1 make 'up' far likelier; everything else noise."""
    quarters = np.repeat([f"202{y}Q{q}" for y in (3, 4, 5) for q in (1, 2, 3, 4)], n // 12)
    n = len(quarters)
    f_order = RNG.integers(0, 4, n).astype(float)
    f_rating = RNG.choice([-1.0, 0.0, 1.0], n)
    score = 0.8 * (f_order >= 2) + 0.8 * (f_rating > 0) - 0.8 * (f_rating < 0) + RNG.normal(0, 0.8, n)
    y = np.where(score > 0.8, "up", np.where(score < -0.8, "down", "flat"))
    if not signal:
        y = RNG.permutation(y)
    return pd.DataFrame({
        "symbol": "S", "day": "2025-01-01", "quarter": quarters,
        "price_change_pct": RNG.normal(0, 2, n), "volume_ratio": RNG.uniform(0.2, 3, n),
        "oi_change_pct": RNG.normal(0, 5, n), "pcr": RNG.uniform(0.3, 2, n),
        "ret_5": RNG.normal(0, 4, n), "ret_20": RNG.normal(0, 8, n), "nifty_ret_5": RNG.normal(0, 2, n),
        "label": RNG.choice(["Bullish setup", "Bearish setup", "Neutral", "Unclassified"], n),
        "sector": RNG.choice(["auto", "banks", "other"], n),
        "f_results_soon": RNG.integers(0, 99, n).astype(float), "f_order": f_order,
        "f_capacity": np.zeros(n), "f_rating": f_rating, "f_deal": np.zeros(n),
        "f_insider": np.zeros(n), "f_ban": np.zeros(n), "y": y, "fwd": score})


def test_featurise_is_stable_and_alignable():
    df = synth(600)
    X, names = featurise(df)
    assert X.shape == (len(df), len(names))
    assert "label_bullish" in names and "sector_banks" in names and "f_order" in names
    sub = df[df["sector"] != "banks"]
    X2, _ = featurise(sub, names)                     # missing dummy column comes back as zeros
    assert X2.shape[1] == len(names)
    assert X2[:, names.index("sector_banks")].sum() == 0


def test_walk_forward_learns_a_planted_pattern_and_beats_base_rate():
    report = walk_forward(synth(9000), min_train=1500)
    assert report["folds"] and report["folds"][0]["quarter"] > "2023Q1"        # never tests on its train
    o = report["overall"]
    base = max(report["class_share"].values())
    assert o["accuracy"] > base + 0.05                                          # the signal is found
    assert o["brier"] < 0.66                                                    # better than uniform-ish
    td = o["top_decile"]
    assert td["up"]["hit_rate"] > td["up"]["base_rate"] + 0.1
    assert set(td) == {"up", "down"}


def test_walk_forward_on_noise_stays_at_the_base_rate():
    report = walk_forward(synth(9000, signal=False), min_train=1500)
    o = report["overall"]
    base = max(report["class_share"].values())
    assert abs(o["accuracy"] - base) < 0.06                                     # no fake skill on shuffled labels


def test_metrics_and_top_decile_shapes():
    y = np.array(["up", "down", "flat", "up"])
    proba = np.array([[0.1, 0.2, 0.7], [0.6, 0.3, 0.1], [0.2, 0.6, 0.2], [0.2, 0.3, 0.5]])
    m = _metrics(y, proba)
    assert m["accuracy"] == 1.0 and 0 < m["brier"] < 2
    td = _top_decile(y, proba)
    assert td["up"]["n"] >= 1


def test_day_flags_sees_only_the_past_window():
    cal = [f"2026-09-{d:02d}" for d in (1, 2, 3, 4, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 21)]
    events = [
        {"type": "order_win", "event_date": "2026-09-02", "bucket": "major", "subtype": None, "direction": 1, "tier": 1},
        {"type": "rating", "event_date": "2026-09-08", "bucket": "significant", "subtype": "downgrade", "direction": -1, "tier": 1},
        {"type": "results_date", "event_date": "2026-09-17", "bucket": "significant", "subtype": "scheduled", "direction": 0, "tier": 1},
        {"type": "ban", "event_date": "2026-09-14", "bucket": "significant", "subtype": "in", "direction": -1, "tier": 1},
        {"type": "ban", "event_date": "2026-09-16", "bucket": "significant", "subtype": "out", "direction": 0, "tier": 1},
    ]
    f = day_flags(events, cal)
    assert f["2026-09-01"]["f_order"] == 0                                      # the day before the order win
    assert f["2026-09-02"]["f_order"] == 3 and f["2026-09-14"]["f_order"] == 3   # within 10 sessions
    assert f["2026-09-16"]["f_order"] == 0                                      # rolled out of the window
    assert f["2026-09-08"]["f_rating"] == -1
    assert f["2026-09-14"]["f_ban"] == 1 and f["2026-09-16"]["f_ban"] == 0
    assert f["2026-09-10"]["f_results_soon"] == 5 and f["2026-09-17"]["f_results_soon"] == 0
    assert f["2026-09-18"]["f_results_soon"] == 99


def test_infer_for_scan_adds_the_model_block(monkeypatch, tmp_path):
    df = synth(3000)
    from scanner import model as model_mod
    model, _ = model_mod._make_model()
    X, names = featurise(df)
    model.fit(X, df["y"].to_numpy())
    payload = {"model": model, "features": names, "classes": list(CLASSES),
               "trained_through": "2026-06-30", "oos_brier": 0.61}
    monkeypatch.setattr(model_mod, "SECTORS_PATH", tmp_path / "sectors.csv")
    stocks = [{"symbol": "RELIANCE", "price_change_pct": 1.2, "volume_ratio": 2.0, "oi_change_pct": 3.0,
               "pcr": 0.9, "label": "Bullish setup", "chart_closes": list(range(100, 131)),
               "events": {"flags": {"order_win": "major", "rating": "upgrade", "ban": False}}},
              {"symbol": "TCS", "price_change_pct": None, "volume_ratio": None, "oi_change_pct": None,
               "pcr": None, "label": "Unclassified", "chart_closes": [], "events": {"flags": {}}}]
    infer_for_scan(stocks, {"closes": [100, 101, 102, 103, 104, 105, 106]}, payload)
    for s in stocks:
        m = s["model"]
        assert m["trained_through"] == "2026-06-30" and m["oos_brier"] == 0.61
        assert 0.999 < m["p_up"] + m["p_down"] + m["p_flat"] < 1.001


def test_base_rate_brier_and_fold_fields():
    report = walk_forward(synth(9000, signal=False), min_train=1500)
    o, f = report["overall"], report["folds"][0]
    shares = np.array(list(report["class_share"].values()))
    assert o["base_brier"] == pytest.approx(1 - (shares ** 2).sum(), abs=0.02)   # constant forecast at the shares
    assert o["brier"] >= o["base_brier"] - 0.01                                   # noise: no better than the base
    assert {"train_end", "test_start", "test_end", "base_brier", "top_decile"} <= set(f)
    assert set(f["top_decile"]) == {"up", "down"}


def test_model_top_decile_flag_is_per_day_and_display_only(monkeypatch, tmp_path):
    from scanner import model as model_mod
    from scanner.verdict_rules import verdict
    monkeypatch.setattr(model_mod, "SECTORS_PATH", tmp_path / "sectors.csv")
    n = 20
    ups = np.linspace(0.10, 0.60, n)                                    # stock i: p_up rises, p_down falls with i
    downs = np.linspace(0.55, 0.05, n)

    class Stub:
        classes_ = np.array(["down", "flat", "up"])

        def predict_proba(self, X):
            return np.stack([downs, 1 - ups - downs, ups], axis=1)

    payload = {"model": Stub(), "features": featurise(synth(60))[1], "classes": list(CLASSES),
               "trained_through": "2026-06-30", "oos_brier": 0.67, "base_brier": 0.667}
    stocks = [{"symbol": f"S{i}", "price_change_pct": 0.0, "volume_ratio": 1.0, "oi_change_pct": 0.0, "pcr": 1.0,
               "label": "Neutral", "chart_closes": [], "events": {"flags": {}}} for i in range(n)]
    infer_for_scan(stocks, None, payload)
    flags = [s["model_top_decile"] for s in stocks]
    assert flags[-2:] == ["up", "up"] and flags[:2] == ["down", "down"] and flags.count(None) == n - 4
    before = verdict(stocks[-1])
    stocks[-1]["model_top_decile"] = None
    assert verdict(stocks[-1]) == before                                 # never a vote


def test_walk_forward_reports_by_period():
    df = synth(9000, signal=False)
    df["day"] = df["quarter"].map(lambda q: f"{q[:4]}-{int(q[-1]) * 3 - 1:02d}-15")    # a date inside each quarter
    report = walk_forward(df, min_train=1500)
    bp = report["by_period"]
    assert set(bp) <= {"2021-22", "2023-24", "2025-26"} and "2025-26" in bp and "2023-24" in bp
    assert sum(m["n"] for m in bp.values()) == sum(f["test_rows"] for f in report["folds"])
    assert {"accuracy", "brier", "base_brier", "top_decile", "first", "last"} <= set(bp["2025-26"])
