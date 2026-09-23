"""Spec 12 step 5: the events block each stock gets in scan.json."""
from datetime import date

import pytest

from scanner.events.store import Store
from scanner.events_join import events_for_scan, flags_of

AS_OF = "2026-09-24"
CAL = ["2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11", "2026-09-12", "2026-09-15", "2026-09-16",
       "2026-09-17", "2026-09-18", "2026-09-19", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-29"]


def ev(**over):
    base = {"id": "x", "symbol": "RELIANCE", "event_date": AS_OF, "event_time": None, "type": "order_win",
            "subtype": None, "tier": 1, "direction": 1, "value_cr": 800.0, "materiality": 20.0,
            "bucket": "major", "source": "nse_ann", "subject": "LoA", "url": "u", "raw_json": {}}
    return {**base, **over}


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "events.sqlite"
    with Store(path) as s:
        s.upsert([
            ev(id="1"),                                                       # today, major
            ev(id="2", event_date="2026-09-16", type="rating", subtype="upgrade", direction=1,
               bucket="significant", value_cr=None, materiality=None),
            ev(id="3", event_date="2026-09-01", type="capacity", bucket="major"),          # too old
            ev(id="4", event_date="2026-09-22", type="block_deal", subtype="promoter_buy", bucket="significant"),
            ev(id="5", event_date="2026-09-23", type="order_win", bucket="ignore"),        # ignored bucket
            ev(id="6", event_date="2026-09-29", type="results_date", subtype="scheduled", direction=0,
               bucket="significant", value_cr=None),                                        # upcoming
            ev(id="7", event_date="2026-09-23", type="analyst_view", tier=3, subtype="upgrade",
               source="rss:et_markets", subject="Broker raises target"),
            ev(id="8", event_date=AS_OF, type="ban", subtype="in", direction=-1, bucket="significant"),
            ev(id="9", symbol="TCS", event_date=AS_OF, type="results", subtype="outcome", bucket="significant"),
        ])
    return path


def test_per_stock_block(db):
    out = events_for_scan(["RELIANCE", "TCS", "INFY"], AS_OF, CAL, db_path=db)
    r = out["RELIANCE"]
    assert [e["type"] for e in r["today"]] == ["order_win", "ban"]
    types = [e["type"] for e in r["last_10"]]
    assert "rating" in types and "block_deal" in types
    assert "capacity" not in types                                   # outside the 10-session window
    assert all(e["bucket"] != "ignore" for e in r["last_10"])
    assert all(e["tier"] <= 2 for e in r["last_10"] + r["today"])
    assert r["upcoming"] == [{"type": "results", "date": "2026-09-29", "sessions": 1, "subject": "LoA"}]
    assert len(r["analyst_view"]) == 1 and r["analyst_view"][0]["label"] == "analyst view (news, not a filing)"
    assert out["TCS"]["flags"].get("results_today") is True
    assert out["INFY"] == {"today": [], "last_10": [], "upcoming": [], "analyst_view": [], "flags": {}}


def test_flags_are_the_model_features(db):
    f = events_for_scan(["RELIANCE"], AS_OF, CAL, db_path=db)["RELIANCE"]["flags"]
    assert f == {"results_soon": 1, "order_win": "major", "rating": "upgrade",
                 "block_deal": "promoter_buy", "ban": True}


def test_flags_pick_the_strongest_and_latest():
    recent = [
        {"type": "order_win", "bucket": "minor", "event_date": "2026-09-20", "subtype": None},
        {"type": "order_win", "bucket": "significant", "event_date": "2026-09-18", "subtype": None},
        {"type": "rating", "subtype": "upgrade", "event_date": "2026-09-18", "bucket": "significant"},
        {"type": "rating", "subtype": "downgrade", "event_date": "2026-09-22", "bucket": "significant"},
        {"type": "ban", "subtype": "in", "event_date": "2026-09-22", "bucket": "significant"},
        {"type": "ban", "subtype": "out", "event_date": "2026-09-23", "bucket": "significant"},
    ]
    f = flags_of(recent, [], "2026-09-24")
    assert f["order_win"] == "significant"                          # strongest bucket, not latest
    assert f["rating"] == "downgrade"                               # latest rating action
    assert f["ban"] is False                                        # latest ban state


def test_missing_db_gives_empty_blocks(tmp_path):
    out = events_for_scan(["RELIANCE"], AS_OF, CAL, db_path=tmp_path / "none.sqlite")
    assert out["RELIANCE"]["flags"] == {} and out["RELIANCE"]["today"] == []


def test_build_attaches_events_and_status(db, monkeypatch, tmp_path):
    """The full build path stays healthy with and without the DB (static page constraint)."""
    from scanner.events import config as ecfg
    monkeypatch.setattr(ecfg, "EVENTS_DB", db)
    out = events_for_scan(["RELIANCE"], AS_OF, CAL)                  # default path now the tmp DB
    assert out["RELIANCE"]["flags"]
    from scanner.events_join import events_status
    st = events_status(db)
    assert st["available"] and st["counts"]["order_win"] == 2
