"""S3 X1 expiry-day buy (scanner/s3_x1.py): fills and the resting target on daily rows."""
from datetime import date

import pandas as pd

from scanner import s3_x1 as X

EX, D0 = date(2023, 3, 9), date(2023, 3, 8)


def _row(day, k, opt, o, h, c, vol=100):
    return {"TradDt": day, "XpryDt": EX, "StrkPric": float(k), "OptnTp": opt, "OpnPric": o, "HghPric": h, "LwPric": 0.05,
            "ClsPric": c, "TtlTradgVol": vol}


def _patch(monkeypatch, rows, spot=17_010.0):
    df = pd.DataFrame(rows)
    monkeypatch.setattr(X, "_rows", lambda day, ex: df[(df["TradDt"] == day) & (df["XpryDt"] == ex)])
    monkeypatch.setattr(X, "prev_session", lambda day: D0)
    monkeypatch.setattr(X, "_spot", lambda day, which: spot)
    monkeypatch.setattr(X, "lot_for", lambda *a, **k: 50)


def test_overnight_put_hits_the_target(monkeypatch):
    _patch(monkeypatch, [_row(D0, 17000, "PE", 40, 45, 50), _row(EX, 17000, "PE", 60, 200, 10)])
    t = X.trade("overnight", EX, "PE", 0, 2.0)
    assert t["strike"] == 17000 and t["paid"] == 50.5 and t["hit"]
    assert abs(t["exit"] - 151.5) < 1e-9                               # 50.5 × 3, the day opened below it
    assert abs(t["max_up_pct"] - (200 / 50.5 - 1) * 100) < 1e-9


def test_gap_above_target_sells_at_the_open_and_a_miss_sells_at_the_close(monkeypatch):
    _patch(monkeypatch, [_row(D0, 17000, "PE", 40, 45, 50), _row(EX, 17000, "PE", 180, 190, 10)])
    assert abs(X.trade("overnight", EX, "PE", 0, 2.0)["exit"] - 180 * 0.99) < 1e-9
    _patch(monkeypatch, [_row(D0, 17000, "PE", 40, 45, 50), _row(EX, 17000, "PE", 60, 100, 10)])
    t = X.trade("overnight", EX, "PE", 0, 2.0)
    assert not t["hit"] and abs(t["exit"] - 9.9) < 1e-9 and t["net_rs"] < 0


def test_strike_steps_out_of_the_money(monkeypatch):
    _patch(monkeypatch, [_row(D0, 16950, "PE", 20, 25, 30), _row(EX, 16950, "PE", 20, 40, 5)])
    assert X.trade("overnight", EX, "PE", 1, 2.0)["strike"] == 16950
    assert X.trade("overnight", EX, "CE", 0, 2.0)["skip"].startswith("no 17000 CE")


def _low(day, k, opt, o, h, lo, c):
    r = _row(day, k, opt, o, h, c)
    r["LwPric"] = lo
    return r


def test_fifty_percent_stop_and_the_worst_case_when_both_are_touched(monkeypatch):
    _patch(monkeypatch, [_row(D0, 17000, "PE", 40, 45, 50), _low(EX, 17000, "PE", 45, 60, 20, 30)])
    t = X.trade("overnight", EX, "PE", 0, 2.0, 0.5)                     # low 20 under the stop 25.25: out there
    assert t["why"] == "stop" and abs(t["exit"] - 50.5 * 0.5 * 0.99) < 0.01 and not t["both_touched"]
    _patch(monkeypatch, [_row(D0, 17000, "PE", 40, 45, 50), _low(EX, 17000, "PE", 45, 200, 20, 30)])
    t = X.trade("overnight", EX, "PE", 0, 2.0, 0.5)                     # touched both: the gate takes the stop
    assert t["why"] == "stop" and t["both_touched"] and t["hit_best"] and t["net_pct_best"] > 100
    _patch(monkeypatch, [_row(D0, 17000, "PE", 40, 45, 50), _low(EX, 17000, "PE", 20, 30, 15, 25)])
    t = X.trade("overnight", EX, "PE", 0, 2.0, 0.5)                     # opened below the stop: out at the open
    assert t["why"] == "gap stop" and abs(t["exit"] - 20 * 0.99) < 1e-9
