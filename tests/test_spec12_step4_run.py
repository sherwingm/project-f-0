"""Spec 12 step 4: the runner — fixture day, ban in/out, results linking, resumable back-fill."""
import json
from datetime import date

import pytest

from scanner.events import run as run_mod
from scanner.events.store import Store


@pytest.fixture
def runner(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod, "STATUS_PATH", tmp_path / "events_status.json")
    monkeypatch.setattr(run_mod, "PROGRESS_PATH", tmp_path / "events_backfill.json")
    monkeypatch.setattr(run_mod, "NAMES_PATH", tmp_path / "equity_names.csv")
    (tmp_path / "equity_names.csv").write_text('symbol,name\nRELIANCE,"Reliance Industries Limited"\n')
    store = Store(tmp_path / "events.sqlite")
    universe = {"RELIANCE", "TCS", "BANDHANBNK", "INOXWIND", "LICHSGFIN", "MANAPPURAM", "SAIL"}
    return run_mod.Runner(store=store, universe=universe, fixtures=True), store


def test_fixture_day_end_to_end(runner):
    r, store = runner
    counts = r.run_day(date(2026, 9, 22))
    assert counts["ban"] == 5 and counts["insider"] == 2
    assert store.counts_by_type() == {"ban": 5, "insider": 2}
    ins = store.all_of_type("insider")
    assert {e["symbol"] for e in ins} == {"RELIANCE", "TCS"}
    promoter = next(e for e in ins if e["symbol"] == "RELIANCE")
    assert promoter["subtype"] == "promoter_buy" and promoter["direction"] == 1 and promoter["bucket"] == "ignore"
    status = json.loads(run_mod.STATUS_PATH.read_text())
    assert status["nse_ann"]["items"] >= 30 and status["nse_ban"]["error"] is None


def test_ban_out_is_derived_from_the_previous_list(runner):
    r, store = runner
    store.upsert([{"id": "nse_ban:2026-09-19:SAIL", "symbol": "SAIL", "event_date": "2026-09-19", "type": "ban",
                   "subtype": "in", "tier": 1, "direction": -1, "bucket": "significant", "source": "nse_ban"},
                  {"id": "nse_ban:2026-09-19:PNB", "symbol": "PNB", "event_date": "2026-09-19", "type": "ban",
                   "subtype": "in", "tier": 1, "direction": -1, "bucket": "significant", "source": "nse_ban"}])
    r.run_day(date(2026, 9, 22))                                  # today's fixture list has SAIL but not PNB
    outs = [e for e in store.all_of_type("ban") if e["subtype"] == "out"]
    assert [e["symbol"] for e in outs] == ["PNB"]
    assert outs[0]["event_date"] == "2026-09-22" and outs[0]["direction"] == 0


def test_results_maybe_links_to_a_results_date_in_the_same_batch(runner):
    r, store = runner
    batch = [
        {"id": "nse_ann:a", "symbol": "RELIANCE", "event_date": "2026-09-22", "event_time": None,
         "type": "results_date", "subtype": "scheduled", "tier": 1, "direction": 0, "value_cr": None,
         "materiality": None, "bucket": "minor", "source": "nse_ann", "subject": "intimation", "url": "",
         "raw_json": {}},
        {"id": "nse_ann:b", "symbol": "RELIANCE", "event_date": "2026-09-22", "event_time": None,
         "type": "results_maybe", "subtype": "unlinked", "tier": 1, "direction": 0, "value_cr": None,
         "materiality": None, "bucket": "minor", "source": "nse_ann", "subject": "Outcome of Board Meeting",
         "url": "", "raw_json": {}},
        {"id": "nse_ann:c", "symbol": "TCS", "event_date": "2026-09-22", "event_time": None,
         "type": "results_maybe", "subtype": "unlinked", "tier": 1, "direction": 0, "value_cr": None,
         "materiality": None, "bucket": "minor", "source": "nse_ann", "subject": "Outcome of Board Meeting",
         "url": "", "raw_json": {}},
    ]
    written = r._settle(batch)
    types = {(e["symbol"], e["type"]) for e in written}
    assert ("RELIANCE", "results") in types and not any(t == "results_maybe" for _, t in types)
    assert ("TCS", "results") not in types                        # no results_date for TCS: dropped
    stored = store.events_for("RELIANCE")
    assert {e["type"] for e in stored} == {"results_date", "results"}
    assert next(e for e in stored if e["type"] == "results")["bucket"] == "significant"


def test_backfill_resumes_from_the_progress_file(runner, monkeypatch):
    r, store = runner
    calls = []

    def fake_backfill(start, end, http=None, **kw):
        for label in ("2026-01-01", "2026-01-02"):                 # ban labels are ISO dates in real sources
            calls.append((kw.get("kind", "ann"), label))
            yield label, []
    for mod in (run_mod.nse_announcements, run_mod.nse_pit, run_mod.nse_ban):
        monkeypatch.setattr(mod, "backfill", fake_backfill)
    monkeypatch.setattr(run_mod.nse_deals, "backfill", fake_backfill)
    run_mod.PROGRESS_PATH.write_text(json.dumps({"nse_ann": ["2026-01-01"]}))     # first chunk already done
    r.backfill(date(2026, 1, 1), date(2026, 1, 31))
    progress = json.loads(run_mod.PROGRESS_PATH.read_text())
    assert set(progress) == {"nse_ann", "nse_block", "nse_bulk", "nse_pit", "nse_ban"}
    assert progress["nse_ann"] == ["2026-01-01", "2026-01-02"]
    assert progress["nse_block"] == ["2026-01-01", "2026-01-02"]


def test_daily_loop_schedules_events_before_rebuild():
    import inspect
    from server import app as app_mod
    src = inspect.getsource(app_mod._daily_rebuild_loop)
    assert "19, 45" in src and "_events_run" in src and "20, 30" in src
