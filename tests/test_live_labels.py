"""Live labels (the EOD rule on live inputs, every poll) and the 09:30 opening snapshot, scored as its own group."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from scanner.build import live_snapshot_calls
from scanner.classify import BEARISH, BULLISH, NEUTRAL, UNCLASSIFIED
from server.live import IST, LiveFeed, live_label

EOD = {"symbol": "ABC", "close": 100.0, "fut_oi": 2000, "avg_volume_20d": 1_000_000, "pcr": 1.0}
SCAN = {"stocks": [EOD]}
FUTS = {"ABC": ["ABC26OCTFUT", "ABC26NOVFUT"]}


def at(hh, mm, day=30):                                   # 2026-09-30 is a Wednesday
    return datetime(2026, 9, day, hh, mm, tzinfo=IST)


class Stub:
    def __init__(self, ltp=102.0, volume=600_000, oi=(1050, 1050)):
        self.ltp, self.volume, self.oi = ltp, volume, oi

    def quote(self, keys):
        return {"NSE:ABC": {"last_price": self.ltp, "volume": self.volume, "ohlc": {"close": 100.0}},
                "NFO:ABC26OCTFUT": {"last_price": self.ltp, "open_interest": self.oi[0]},
                "NFO:ABC26NOVFUT": {"last_price": self.ltp, "open_interest": self.oi[1]}}


def test_live_label_uses_the_eod_rule_with_volume_pro_rata():
    row = {"chg_pct": 2.0, "volume": 600_000, "fut_oi_chg_pct": 5.0, "live_pcr": None}
    r = live_label(row, EOD, at(10, 30))                   # 75 of 375 minutes: expected 200,000 so far
    assert r["live_volume_ratio"] == 3.0 and r["live_label"] == BULLISH and r["live_label_pcr"] == "eod"
    assert live_label({**row, "chg_pct": -2.0}, EOD, at(10, 30))["live_label"] == BEARISH
    assert live_label({**row, "volume": 100_000}, EOD, at(10, 30))["live_label"] == NEUTRAL      # 0.5x pro rata
    assert live_label(row, EOD, at(9, 16))["live_volume_ratio"] == 15.0                           # 15-minute floor
    assert live_label({**row, "fut_oi_chg_pct": None}, EOD, at(10, 30))["live_label"] == UNCLASSIFIED
    assert live_label({**row, "live_pcr": 0.5}, EOD, at(15, 30))["live_label_pcr"] == "live"


def test_feed_rows_carry_the_live_label():
    feed = LiveFeed(Stub(), SCAN, fut_tradingsymbols=FUTS)
    feed.poll_once(now=at(10, 30))
    q = feed.snapshot()["quotes"]["ABC"]
    assert q["chg_pct"] == 2.0 and q["fut_oi_chg_pct"] == 5.0 and q["live_label"] == BULLISH
    assert any("long buildup" in r for r in q["live_reasons"])


def test_opening_snapshot_is_written_once_between_0930_and_1030(tmp_path):
    feed = LiveFeed(Stub(), SCAN, fut_tradingsymbols=FUTS)
    feed.snapshot_dir = tmp_path
    feed.poll_once(now=at(9, 25))
    assert not list(tmp_path.glob("*.json"))                                  # before 09:30
    feed.poll_once(now=at(9, 31))
    snap = json.loads((tmp_path / "2026-09-30.json").read_text())
    assert snap["taken_at"] == "09:31:00" and snap["rows"][0]["symbol"] == "ABC" and snap["rows"][0]["label"] == BULLISH
    feed.provider = Stub(ltp=97.0)
    feed.poll_once(now=at(9, 45))
    assert json.loads((tmp_path / "2026-09-30.json").read_text())["taken_at"] == "09:31:00"   # once a day
    feed.poll_once(now=at(10, 45, day=29))                                  # after 10:30: too late for an opening
    feed.poll_once(now=at(9, 40, day=26))                                   # Saturday
    assert sorted(p.name for p in tmp_path.glob("*.json")) == ["2026-09-30.json"]


def test_snapshot_endpoint(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from server import app as app_mod
    from server.config import settings
    monkeypatch.setattr(settings, "public_access", True)
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    (tmp_path / "live_snapshots").mkdir()
    (tmp_path / "live_snapshots" / "2026-09-30.json").write_text(json.dumps({"date": "2026-09-30", "rows": []}))
    c = TestClient(app_mod.app)
    assert c.get("/api/live/snapshot?date=2026-09-30").json()["date"] == "2026-09-30"
    assert c.get("/api/live/snapshot?date=2026-09-29").status_code == 404
    assert c.get("/api/live/snapshot?date=../etc").status_code == 400


def test_build_embeds_directional_snapshot_rows_for_session_days_only(tmp_path):
    rows = [{"symbol": "ABC", "label": BULLISH}, {"symbol": "DEF", "label": NEUTRAL}, {"symbol": "GHI", "label": BEARISH}]
    (tmp_path / "2026-09-30.json").write_text(json.dumps({"date": "2026-09-30", "taken_at": "09:31:00", "rows": rows}))
    (tmp_path / "2026-10-02.json").write_text(json.dumps({"date": "2026-10-02", "taken_at": "09:31:00", "rows": rows}))
    got = live_snapshot_calls(tmp_path, ["2026-09-29", "2026-09-30", "2026-10-01"])      # 2 Oct: a holiday
    assert got == [{"date": "2026-09-30", "symbol": "ABC", "label": BULLISH, "taken_at": "09:31:00"},
                   {"date": "2026-09-30", "symbol": "GHI", "label": BEARISH, "taken_at": "09:31:00"}]
    assert live_snapshot_calls(tmp_path / "missing", ["2026-09-30"]) == []


@pytest.mark.parametrize("piece", ["function livePill(s)", "live: ", "09:30 live labels", "meta.live_snapshots",
                                   "pro rata"])
def test_page_shows_live_labels_and_scores_the_snapshots(piece):
    html = (Path(__file__).resolve().parent.parent / "templates" / "index.html").read_text(encoding="utf-8")
    assert piece in html


def test_the_model_never_reads_live_data():
    import inspect
    from server import live
    assert "model" not in inspect.getsource(live).lower().replace("the model never sees live data", "")
