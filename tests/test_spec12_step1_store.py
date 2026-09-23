"""Spec 12 step 1: the event store."""
import json
from datetime import date

import pytest

from scanner.events.store import Store


def ev(**over):
    base = {"id": "nse_ann:1", "symbol": "RELIANCE", "event_date": "2026-09-21", "event_time": "18:05",
            "type": "order_win", "subtype": None, "tier": 1, "direction": 1, "value_cr": 800.0,
            "materiality": 0.2, "bucket": "major", "source": "nse_ann", "subject": "Letter of award",
            "url": "https://nsearchives.nseindia.com/x.pdf", "raw_json": {"a": 1}}
    return {**base, **over}


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "events.sqlite") as s:
        yield s


def test_upsert_dedups_by_id_and_serialises_raw(store):
    assert store.upsert([ev(), ev(subject="Letter of award (revised)")]) == 2
    rows = store.events_for("RELIANCE")
    assert len(rows) == 1 and rows[0]["subject"] == "Letter of award (revised)"
    assert json.loads(rows[0]["raw_json"]) == {"a": 1} and rows[0]["fetched_at"]


def test_events_for_filters_by_range_and_tier(store):
    store.upsert([ev(), ev(id="nse_ann:2", event_date="2026-09-10"),
                  ev(id="rss:x", tier=3, type="analyst_view", event_date="2026-09-21")])
    assert [r["id"] for r in store.events_for("RELIANCE", since="2026-09-15")] == ["nse_ann:1", "rss:x"]
    assert [r["id"] for r in store.events_for("RELIANCE", since="2026-09-15", max_tier=2)] == ["nse_ann:1"]
    assert store.events_for("TCS") == []


def test_upcoming_counts_weekdays(store):
    store.upsert([ev(id="a", type="results_date", event_date="2026-09-29"),      # Tue, 3 weekdays after Thu 24
                  ev(id="b", type="results_date", event_date="2026-10-08")])
    got = store.upcoming("RELIANCE", sessions=3, today=date(2026, 9, 24))
    assert [r["id"] for r in got] == ["a"]
    assert [r["id"] for r in store.upcoming("RELIANCE", sessions=10, today=date(2026, 9, 24))] == ["a", "b"]
    assert store.upcoming("RELIANCE", sessions=2, today=date(2026, 9, 24)) == []


def test_all_of_type_counts_and_status(store):
    store.upsert([ev(), ev(id="nse_ann:2", symbol="TCS", event_date="2026-08-01"),
                  ev(id="nse_block:1", type="block_deal", source="nse_block")])
    assert [r["symbol"] for r in store.all_of_type("order_win")] == ["TCS", "RELIANCE"]
    assert [r["symbol"] for r in store.all_of_type("order_win", since="2026-09-01")] == ["RELIANCE"]
    assert store.counts_by_type() == {"order_win": 2, "block_deal": 1}
    assert store.latest_fetch("nse_block") and store.latest_fetch("bse_ann") is None


def test_missing_required_fields_are_rejected(store):
    with pytest.raises(ValueError, match="event_date"):
        store.upsert([ev(event_date=None)])


def test_persistence_across_reopen(tmp_path):
    with Store(tmp_path / "e.sqlite") as s:
        s.upsert([ev()])
    with Store(tmp_path / "e.sqlite") as s:
        assert s.counts_by_type() == {"order_win": 1}
