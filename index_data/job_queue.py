"""The index-data job queue on GitHub (no PC needed): data/index/job_queue.json on main.

    python -m index_data.job_queue add --job upstox_expired --args "--underlying SENSEX --max-minutes 300" --why "..."
    python -m index_data.job_queue next               # pop the first job; prints job=... / args=... for $GITHUB_OUTPUT
    python -m index_data.job_queue requeue-if-stopped --job upstox_expired --args "--underlying SENSEX ..."

The hourly scheduler (.github/workflows/index-scheduler.yml) pops one job when no index-data run is active and
dispatches it to index-jobs.yml. An upstox_expired run that stopped on its time budget puts itself back at the front
(requeue-if-stopped), so a long backfill continues by itself, one run after the other, until it is complete.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# standard library only (no pandas): the scheduler and the hand-off steps run it without installing anything
IST = timezone(timedelta(hours=5, minutes=30))
SMALL = Path(__file__).resolve().parents[1] / "data" / "index"
PATH = SMALL / "job_queue.json"


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")


def load() -> dict:
    q = read_json(SMALL / "job_queue.json", {}) or {}
    return {"queue": list(q.get("queue") or []), "history": list(q.get("history") or [])}


def save(q: dict) -> None:
    q["history"] = q["history"][-40:]
    write_json(SMALL / "job_queue.json", q)


def now() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def add(q: dict, job: str, args: str, why: str, front: bool = False) -> bool:
    """Queue a job unless the same job with the same args is already waiting. True when added."""
    if any(x["job"] == job and x.get("args", "") == args for x in q["queue"]):
        return False
    item = {"job": job, "args": args, "added": now(), "why": why}
    q["queue"].insert(0, item) if front else q["queue"].append(item)
    return True


def pop(q: dict) -> dict | None:
    if not q["queue"]:
        return None
    item = q["queue"].pop(0)
    q["history"].append({**item, "dispatched": now()})
    return item


def stopped_on_budget(job: str, args: str) -> bool:
    """Whether the last upstox_expired run for this underlying stopped on its time budget (status.json)."""
    if job != "upstox_expired":
        return False
    parts = args.split()
    under = parts[parts.index("--underlying") + 1] if "--underlying" in parts else None
    res = ((read_json(SMALL / "status.json", {}) or {}).get("upstox_expired") or {}).get(under) or {}
    return str(res.get("stopped") or "").startswith("time budget")


def main() -> None:
    ap = argparse.ArgumentParser(description="index-data job queue")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("add")
    a2 = sub.add_parser("requeue-if-stopped")
    for p in (a1, a2):
        p.add_argument("--job", required=True)
        p.add_argument("--args", default="")
    a1.add_argument("--why", default="")
    sub.add_parser("next")
    a = ap.parse_args()
    q = load()
    if a.cmd == "add":
        print("added" if add(q, a.job, a.args, a.why) else "already queued")
    elif a.cmd == "requeue-if-stopped":
        if not stopped_on_budget(a.job, a.args):
            print("finished: not requeued")
            return
        print("requeued" if add(q, a.job, a.args, "continues: the last run stopped on its time budget", front=True)
              else "already queued")
    else:
        item = pop(q)
        print(f"job={item['job']}\nargs={item.get('args', '')}" if item else "job=")
    save(q)


if __name__ == "__main__":
    main()
