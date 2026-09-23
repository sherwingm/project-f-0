"""Event fetchers, one module per official source (plus tier-3 RSS).

Every module exposes
    fetch(day, http=None, fixture=None) -> list[RawItem]
    backfill(start, end, http=None) -> iterator of (chunk_label, list[RawItem])
and a small CLI (`python -m scanner.events.sources.<name> --day 2026-09-24 [--fixture FILE]`).

A RawItem is a plain dict: source, source_id, symbol (None until mapped), event_date (YYYY-MM-DD IST),
event_time (HH:MM or None), category, subject, text, url, extra. Classification into typed, scored
events happens in scanner/events/taxonomy.py; fetchers only fetch and normalise fields.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta


def ddmmyyyy(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def parse_nse_ts(s: str | None) -> tuple[str | None, str | None]:
    """'22-Sep-2026 23:58:18' -> ('2026-09-22', '23:58'); date-only forms accepted."""
    if not s:
        return None, None
    s = str(s).strip()
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date().isoformat(), (dt.strftime("%H:%M") if "%H" in fmt else None)
        except ValueError:
            continue
    return None, None


def chunks(start: date, end: date, days: int):
    d = start
    while d <= end:
        e = min(end, d + timedelta(days=days - 1))
        yield d, e
        d = e + timedelta(days=1)
