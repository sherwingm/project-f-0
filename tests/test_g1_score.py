"""The G1 breakout score (record only): points, percentile, the live stamp, and that it never gates a trade."""
import csv
from datetime import time

import pytest

from server import g1_score as S
from tests.test_g1_live import D1, Stream, Upstox, down_day, run
from server import g1_live as G


def feats(**kw):
    f = {"depth": 0.05, "time": 3, "width": 0.3, "gap": -0.2, "vix": 14.0, "prev5": -1.0, "ema20": -0.5}
    f.update(kw)
    return f


def test_thresholds_match_the_frozen_file():
    rows = {r[""]: float(r["threshold"]) for r in csv.DictReader(open(S.REPO / "g1_research/results/score_thresholds.csv", encoding="utf-8"))}
    assert {lab: th for lab, _, th in S.ITEMS} == pytest.approx(rows)


def test_points_and_missing_inputs():
    assert S.points(feats())[0] == 7
    sc, got, miss = S.points(feats(depth=0.0, vix=17.0, prev5=None, ema20=None))
    assert sc == 3 and "vix" not in got and miss == ["prev5", "ema20"]


def test_features_from_daily_closes():
    closes = [100.0 + i for i in range(30)]                 # rising: prev5 > 0, close above its EMA
    f = S.features(24000.0, 23990.0, time(9, 40), 0.3, -0.1, 13.0, closes)
    assert f["time"] == 10 and f["depth"] == pytest.approx(10 / 24000 * 100)
    assert f["prev5"] == pytest.approx((129 / 124 - 1) * 100) and f["ema20"] > 0
    assert S.features(24000.0, 23990.0, time(9, 40), 0.3, -0.1, 13.0, None)["prev5"] is None


def test_percentile_band_and_stamp(monkeypatch):
    assert S.percentile(4, [1, 2, 4, 6]) == pytest.approx((2 + 0.5) / 4 * 100)
    assert S.band(2) == "low 0-2" and S.band(3) == "mid 3-4" and S.band(5) == "high 5-7"
    monkeypatch.setattr(S, "history_scores", lambda: [3, 4, 5])
    r = S.stamp(feats(), [2])
    assert r["score"] == 7 and r["score_pct"] == 100.0 and r["score_pctile"] == 100.0
    assert r["score_avg_pct"] == pytest.approx((3 + 4 + 5 + 2 + 7) / 5 / 7 * 100, abs=0.1)
    assert "score 7/7" in S.line(r)


def test_live_signal_is_scored_and_the_score_never_gates_the_trade(tmp_path, monkeypatch):
    monkeypatch.setattr(G.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(G.alerts, "send", lambda *a, **k: False)
    st = Stream()
    tr = G.G1Trader(st, Upstox(), tmp_path)             # the fake Upstox has no history: two trend items are 'missing'
    run(tr, D1, time(9, 15), time(9, 45), before=down_day(st))
    o, d = tr.state["open"], tr.state["days"][str(D1)]
    assert o is not None and o["paid"] == 100.5          # the trade is the same as without a score
    assert d["score"] == o["score"] and set(o["score_missing"]) == {"prev5", "ema20"} and 0 <= o["score"] <= 5
    assert o["score_band"] in ("low 0-2", "mid 3-4", "high 5-7")


def test_score_failure_never_stops_a_trade(tmp_path, monkeypatch):
    monkeypatch.setattr(G.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(G.alerts, "send", lambda *a, **k: False)
    monkeypatch.setattr(S, "stamp", lambda *a, **k: 1 / 0)
    st = Stream()
    tr = G.G1Trader(st, Upstox(), tmp_path)
    run(tr, D1, time(9, 15), time(9, 45), before=down_day(st))
    assert tr.state["open"] is not None and "score" not in tr.state["open"]


def test_near_tighty_is_not_scored(tmp_path, monkeypatch):
    from server.nt_live import NearTightyTrader
    assert NearTightyTrader.SCORE is False and G.G1Trader.SCORE is True


def test_view_carries_score_meta_and_bands(tmp_path, monkeypatch):
    monkeypatch.setattr(G.sessions, "is_session", lambda d: d.weekday() < 5)
    monkeypatch.setattr(G.alerts, "send", lambda *a, **k: False)
    tr = G.G1Trader(Stream(), Upstox(), tmp_path)
    tr.state["trades"] = [
        {"day": "2026-11-05", "paid": 100.0, "net_pct": 40.0, "net_rs": 2600.0, "max_up_pct": 150.0, "score": 6, "score_band": "high 5-7", "g1f_skip": ""},
        {"day": "2026-11-06", "paid": 100.0, "net_pct": -50.0, "net_rs": -3250.0, "max_up_pct": 10.0, "score": 2, "score_band": "low 0-2", "g1f_skip": "VIX 18 >= 17"},
        {"day": "2026-11-09", "paid": 100.0, "net_pct": 10.0, "net_rs": 650.0, "max_up_pct": 60.0, "g1f_skip": ""},     # no score (before the score existed)
    ]
    v = tr.view()
    assert [m["key"] for m in v["score_meta"]] == ["depth", "time", "width", "gap", "vix", "prev5", "ema20"]
    assert all(m["rule"] and m["short"] for m in v["score_meta"])
    f = next(t for t in v["tracks"] if t["pod"].startswith("G1-F"))
    hi = next(b for b in f["bands"] if b["band"] == "high 5-7")
    assert hi["n"] == 1 and hi["up100"] == 1.0 and hi["mean"] == 150.0 and hi["booked"] == 40.0
    assert next(b for b in f["bands"] if b["band"] == "low 0-2")["n"] == 0            # the low-score trade was skipped by G1-F
    g = next(t for t in v["tracks"] if t["pod"].startswith("G1 "))
    assert next(b for b in g["bands"] if b["band"] == "low 0-2")["n"] == 1
