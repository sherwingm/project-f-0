"""NSE F&O security ban list for a trade date (tier 1).

File: https://nsearchives.nseindia.com/archives/fo/sec_ban/fo_secban_DDMMYYYY.csv
    Securities in Ban For Trade Date 22-SEP-2026:
    1,BANDHANBNK
    ...
A day with no file (holiday, or no bans published yet) yields []. "Out of ban" is derived by the
runner from the difference against the previous session's list.
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta

from ..http import EventHttp, FetchError, read_fixture

log = logging.getLogger(__name__)
URL = "https://nsearchives.nseindia.com/archives/fo/sec_ban/fo_secban_{d:%d%m%Y}.csv"
SOURCE = "nse_ban"


def fetch(day: date, http: EventHttp | None = None, fixture: str | None = None) -> list[dict]:
    if fixture:
        text = read_fixture(fixture)
    else:
        try:
            text = (http or EventHttp()).get_text(URL.format(d=day), "https://www.nseindia.com/")
        except FetchError as exc:
            log.info("%s: no ban file (%s)", day, exc)
            return []
    out = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2 and parts[0].isdigit() and parts[1]:
            sym = parts[1].upper()
            out.append({"source": SOURCE, "source_id": f"{day.isoformat()}:{sym}", "symbol": sym,
                        "event_date": day.isoformat(), "event_time": None, "category": "ban",
                        "subject": f"{sym} in F&O ban for {day.isoformat()}", "text": "", "url": URL.format(d=day),
                        "extra": {"in_ban": True}})
    return out


def backfill(start: date, end: date, http: EventHttp | None = None):
    http = http or EventHttp()
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d.isoformat(), fetch(d, http)
        d += timedelta(days=1)


def main() -> None:
    ap = argparse.ArgumentParser(description="NSE F&O ban list")
    ap.add_argument("--day", type=date.fromisoformat, default=date.today())
    ap.add_argument("--fixture")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    items = fetch(a.day, fixture=a.fixture)
    print(f"{len(items)} in ban:", ", ".join(i["symbol"] for i in items))


if __name__ == "__main__":
    main()
