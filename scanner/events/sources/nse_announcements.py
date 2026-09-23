"""NSE corporate announcements (equities): the tier-1 filing feed.

API: https://www.nseindia.com/api/corporate-announcements?index=equities&from_date=DD-MM-YYYY&to_date=DD-MM-YYYY
One JSON row per filing: symbol, desc (category), attchmntText (subject text), attchmntFile, an_dt, seq_id.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date

from ..http import EventHttp, read_fixture
from . import chunks, ddmmyyyy, parse_nse_ts

log = logging.getLogger(__name__)
URL = "https://www.nseindia.com/api/corporate-announcements?index=equities&from_date={a}&to_date={b}"
REFERER = "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
SOURCE = "nse_ann"
BACKFILL_CHUNK_DAYS = 7


def fetch(day: date, http: EventHttp | None = None, fixture: str | None = None,
          until: date | None = None) -> list[dict]:
    if fixture:
        rows = json.loads(read_fixture(fixture))
    else:
        rows = (http or EventHttp()).get_json(URL.format(a=ddmmyyyy(day), b=ddmmyyyy(until or day)), REFERER)
    if not isinstance(rows, list):
        rows = rows.get("data", []) if isinstance(rows, dict) else []
    out = []
    for r in rows:
        d, t = parse_nse_ts(r.get("an_dt") or r.get("exchdisstime") or r.get("sort_date"))
        sym = str(r.get("symbol") or "").strip().upper()
        if not sym or not d:
            continue
        sid = str(r.get("seq_id") or f"{sym}:{r.get('an_dt')}:{hash(r.get('attchmntText'))}")
        out.append({"source": SOURCE, "source_id": sid, "symbol": sym, "event_date": d, "event_time": t,
                    "category": str(r.get("desc") or "").strip(), "subject": str(r.get("attchmntText") or "").strip(),
                    "text": str(r.get("attchmntText") or "").strip(), "url": r.get("attchmntFile") or "",
                    "extra": {"company": r.get("sm_name"), "industry": r.get("smIndustry")}})
    return out


def backfill(start: date, end: date, http: EventHttp | None = None):
    http = http or EventHttp()
    for a, b in chunks(start, end, BACKFILL_CHUNK_DAYS):
        yield f"{a}..{b}", fetch(a, http, until=b)


def main() -> None:
    ap = argparse.ArgumentParser(description="NSE corporate announcements")
    ap.add_argument("--day", type=date.fromisoformat, default=date.today())
    ap.add_argument("--fixture", help="read a saved response from tests/fixtures/ instead of the network")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    items = fetch(a.day, fixture=a.fixture)
    print(f"{SOURCE}: {len(items)} filings", *(f"  {i['symbol']:<12} {i['category'][:40]:<42} {i['subject'][:60]}"
                                               for i in items[:15]), sep="\n")


if __name__ == "__main__":
    main()
