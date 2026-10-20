"""The GitHub-run index job queue (index_data/job_queue.py) and the probe report table (index_data/probe_report.py)."""
import json

import index_data.job_queue as Q
import index_data.probe_report as PR


def test_add_dedupes_and_pop_records_history():
    q = {"queue": [], "history": []}
    assert Q.add(q, "upstox_expired", "--underlying SENSEX --max-minutes 300", "rest of SENSEX")
    assert not Q.add(q, "upstox_expired", "--underlying SENSEX --max-minutes 300", "again")
    assert Q.add(q, "reconcile", "--from 2026-10-19", "x")
    assert Q.add(q, "upstox_expired", "--underlying NIFTY", "first", front=True)
    assert [x["job"] for x in q["queue"]] == ["upstox_expired", "upstox_expired", "reconcile"]
    item = Q.pop(q)
    assert item["args"] == "--underlying NIFTY" and q["history"][-1]["dispatched"] and len(q["queue"]) == 2
    assert Q.pop({"queue": [], "history": []}) is None


def test_requeue_only_when_the_backfill_stopped_on_its_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(Q, "SMALL", tmp_path)
    (tmp_path / "status.json").write_text(json.dumps({"upstox_expired": {
        "SENSEX": {"stopped": "time budget reached (restart to continue)"}, "NIFTY": {"stopped": None}}}))
    assert Q.stopped_on_budget("upstox_expired", "--underlying SENSEX --max-minutes 300")
    assert not Q.stopped_on_budget("upstox_expired", "--underlying NIFTY --max-minutes 180")
    assert not Q.stopped_on_budget("reconcile", "--underlying SENSEX")


REPORT = """# R

## Expired-token retention
text

| Probe | Date | 1-min 10-12 → 10-16 | Expiry day | 5-min | Daily | Still listed | NIFTY control | Verdict |
|---|---|---|---|---|---|---|---|---|
| before expiry (DATA_ACCESS_AUDIT) | 2026-10-18 | 1,923 | — | 385 | — | yes | 1,807 | — |
| probe 1 | old row | | | | | | | |

## VIX corrections
"""


def test_probe_table_is_rewritten_from_the_results():
    hist = [{"run_on": "2026-10-20", "label": "2026-10-20", "verdict": "not retained", "checks": [
        {"check": "1min before expiry", "rows": 0, "error": None}, {"check": "1min expiry day", "rows": 0, "error": None},
        {"check": "5min", "rows": 0, "error": None}, {"check": "daily", "rows": 0, "error": "token not found"},
        {"check": "control: NIFTY 50 spot 1min expiry day", "rows": 375, "error": None},
        {"check": "still in the scrip master", "result": False}]}]
    out = PR.render(REPORT, hist)
    assert "| probe 1 | 2026-10-20 (run 2026-10-20) | 0 | 0 | 0 | error: token not found | no | 375 | not retained |" in out
    assert "old row" not in out and "| before expiry (DATA_ACCESS_AUDIT)" in out and out.endswith("## VIX corrections\n")
    assert PR.render(out, hist) == out                                     # running it again changes nothing
