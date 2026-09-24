"""NSE board-meeting intimations (tier 1): the dated results meetings the announcements feed does not carry.

API: https://www.nseindia.com/api/corporate-board-meetings?index=equities&from_date=DD-MM-YYYY&to_date=DD-MM-YYYY
The range filters on the meeting date (bm_date). Rows: bm_symbol, bm_date ('31-Oct-2025'), bm_purpose
('Financial Results', 'Financial Results/Dividend', 'Board Meeting Intimation', 'Fund Raising', ...), bm_desc,
bm_timestamp (when NSE broadcast the intimation), attachment.

The event date is the meeting date; the intimation time is kept in extra.announced. One item per stock per
meeting date (a revised intimation replaces the earlier one). The taxonomy keeps it as results_date only when
the purpose or description names financial results.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date, timedelta

from ..http import EventHttp, read_fixture
from . import chunks, ddmmyyyy, parse_nse_ts

log = logging.getLogger(__name__)
URL = "https://www.nseindia.com/api/corporate-board-meetings?index=equities&from_date={a}&to_date={b}"
REFERER = "https://www.nseindia.com/companies-listing/corporate-filings-board-meetings"
SOURCE = "nse_bm"
BACKFILL_CHUNK_DAYS = 30
DAILY_AHEAD_DAYS = 30                 # a daily run asks for meetings up to this many days ahead


def fetch(day: date, http: EventHttp | None = None, fixture: str | None = None,
          until: date | None = None) -> list[dict]:
    if fixture:
        payload = json.loads(read_fixture(fixture))
    else:
        payload = (http or EventHttp()).get_json(URL.format(a=ddmmyyyy(day), b=ddmmyyyy(until or day)), REFERER)
    rows = payload if isinstance(payload, list) else (payload.get("data", []) if isinstance(payload, dict) else [])
    out: dict[str, dict] = {}
    for r in rows:
        sym = str(r.get("bm_symbol") or "").strip().upper()
        d, _ = parse_nse_ts(r.get("bm_date"))
        if not sym or not d:
            continue
        announced, _ = parse_nse_ts(r.get("bm_timestamp"))
        purpose = str(r.get("bm_purpose") or "").strip()
        desc = str(r.get("bm_desc") or "").strip()
        item = {"source": SOURCE, "source_id": f"{sym}:{d}", "symbol": sym, "event_date": d, "event_time": None,
                "category": f"board meeting: {purpose}", "subject": desc or purpose, "text": f"{purpose} {desc}",
                "url": r.get("attachment") or "",
                "extra": {"purpose": purpose, "announced": r.get("bm_timestamp"), "announced_date": announced}}
        prev = out.get(item["source_id"])
        if prev is None or (announced or "") >= (prev["extra"]["announced_date"] or ""):
            out[item["source_id"]] = item
    return list(out.values())


def fetch_ahead(day: date, http: EventHttp | None = None, fixture: str | None = None) -> list[dict]:
    """A daily run: meetings from `day` to DAILY_AHEAD_DAYS ahead (the scan's 'upcoming' block reads them)."""
    return fetch(day, http, fixture=fixture, until=day + timedelta(days=DAILY_AHEAD_DAYS))


def backfill(start: date, end: date, http: EventHttp | None = None):
    http = http or EventHttp()
    for a, b in chunks(start, end, BACKFILL_CHUNK_DAYS):
        yield f"{a}..{b}", fetch(a, http, until=b)


def main() -> None:
    ap = argparse.ArgumentParser(description="NSE board-meeting intimations")
    ap.add_argument("--day", type=date.fromisoformat, default=date.today())
    ap.add_argument("--fixture")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    for i in fetch_ahead(a.day, fixture=a.fixture):
        print(f"{i['event_date']} {i['symbol']:<12} {i['category'][:40]:<42} {i['subject'][:60]}")


if __name__ == "__main__":
    main()
