"""SQLite store for exchange events: one row per filing / deal / disclosure, deduplicated by id.

    from scanner.events.store import Store
    with Store() as s:
        s.upsert(events)                      # list of dicts with the schema's keys; id and symbol required
        s.events_for("RELIANCE", since="2026-09-01", until="2026-09-24")
        s.upcoming("RELIANCE", sessions=5)    # future-dated events (results_date) within N weekdays
        s.all_of_type("order_win")

`id` is source + source_id, so refetching a day is idempotent. Tier: 1 official filing or exchange file,
2 registered agency press release, 3 mainstream news (analyst view only). Timestamps are IST.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import config

IST = timezone(timedelta(hours=5, minutes=30))

COLUMNS = ("id", "symbol", "event_date", "event_time", "type", "subtype", "tier", "direction", "value_cr",
           "materiality", "bucket", "source", "subject", "url", "raw_json", "fetched_at")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    event_date TEXT NOT NULL,
    event_time TEXT,
    type TEXT NOT NULL,
    subtype TEXT,
    tier INTEGER NOT NULL,
    direction INTEGER NOT NULL DEFAULT 0,
    value_cr REAL,
    materiality REAL,
    bucket TEXT NOT NULL DEFAULT 'ignore',
    source TEXT NOT NULL,
    subject TEXT,
    url TEXT,
    raw_json TEXT,
    fetched_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_events_symbol_date ON events (symbol, event_date);
CREATE INDEX IF NOT EXISTS ix_events_type ON events (type);
CREATE INDEX IF NOT EXISTS ix_events_date ON events (event_date);
"""


class Store:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or config.EVENTS_DB)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(_SCHEMA)
        self.db.execute("PRAGMA journal_mode=WAL")

    # ------------------------------------------------------------ write
    def upsert(self, events: list[dict]) -> int:
        """Insert or replace by id. Returns how many rows were written. Rows without id/symbol/event_date/type
        are rejected loudly: silently dropping a filing would bias every downstream number."""
        rows = []
        now = datetime.now(IST).isoformat(timespec="seconds")
        for e in events:
            missing = [k for k in ("id", "symbol", "event_date", "type", "source", "tier") if not e.get(k) and e.get(k) != 0]
            if missing:
                raise ValueError(f"event is missing {missing}: {str(e)[:200]}")
            raw = e.get("raw_json")
            rows.append(tuple(e.get(k) if k != "raw_json" else (raw if isinstance(raw, (str, type(None))) else json.dumps(raw))
                              for k in COLUMNS[:-1]) + (e.get("fetched_at") or now,))
        with self.db:
            self.db.executemany(f"INSERT OR REPLACE INTO events ({','.join(COLUMNS)}) "
                                f"VALUES ({','.join('?' * len(COLUMNS))})", rows)
        return len(rows)

    # ------------------------------------------------------------ read
    def events_for(self, symbol: str, since: str | date | None = None, until: str | date | None = None,
                   max_tier: int | None = None) -> list[dict]:
        q, args = "SELECT * FROM events WHERE symbol = ?", [str(symbol).upper()]
        if since is not None:
            q += " AND event_date >= ?"; args.append(_iso(since))
        if until is not None:
            q += " AND event_date <= ?"; args.append(_iso(until))
        if max_tier is not None:
            q += " AND tier <= ?"; args.append(max_tier)
        q += " ORDER BY event_date, event_time"
        return [dict(r) for r in self.db.execute(q, args)]

    def upcoming(self, symbol: str, sessions: int, today: str | date | None = None) -> list[dict]:
        """Future-dated events (a results_date filing dates the meeting) within `sessions` weekdays after
        `today`. Weekdays approximate sessions; the scan join recomputes exact sessions on its calendar."""
        t = _d(today) if today else datetime.now(IST).date()
        horizon, d = t, t
        n = 0
        while n < sessions:
            d += timedelta(days=1)
            if d.weekday() < 5:
                n += 1
            horizon = d
        return self.events_for(symbol, since=t + timedelta(days=1), until=horizon)

    def all_of_type(self, type_: str, since: str | date | None = None, max_tier: int | None = None) -> list[dict]:
        q, args = "SELECT * FROM events WHERE type = ?", [type_]
        if since is not None:
            q += " AND event_date >= ?"; args.append(_iso(since))
        if max_tier is not None:
            q += " AND tier <= ?"; args.append(max_tier)
        q += " ORDER BY event_date, symbol"
        return [dict(r) for r in self.db.execute(q, args)]

    def events_between(self, since: str | date, until: str | date, max_tier: int = 2) -> list[dict]:
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM events WHERE event_date >= ? AND event_date <= ? AND tier <= ? ORDER BY event_date, symbol",
            (_iso(since), _iso(until), max_tier))]

    def counts_by_type(self) -> dict[str, int]:
        return {r["type"]: r["n"] for r in self.db.execute(
            "SELECT type, COUNT(*) AS n FROM events GROUP BY type ORDER BY n DESC")}

    def latest_fetch(self, source_prefix: str) -> str | None:
        r = self.db.execute("SELECT MAX(fetched_at) AS t FROM events WHERE source LIKE ?",
                            (source_prefix + "%",)).fetchone()
        return r["t"]

    # ------------------------------------------------------------ lifecycle
    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _iso(d: str | date) -> str:
    return d if isinstance(d, str) else d.isoformat()


def _d(d: str | date) -> date:
    return d if isinstance(d, date) else date.fromisoformat(str(d)[:10])
