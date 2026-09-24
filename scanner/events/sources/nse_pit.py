"""NSE insider-trading (PIT reg 7(2)) and SAST disclosures (tier 1).

API: https://www.nseindia.com/api/corporates-pit?index=equities&from_date=DD-MM-YYYY&to_date=DD-MM-YYYY
Rows carry symbol, acqName, personCategory (Promoters / Promoter Group / Director / Employee / ...),
tdpTransactionType (Buy/Sell/Pledge...), secAcq (quantity), secVal (value), befAcqSharesPer,
afterAcqSharesPer (% of the company held before / after), date (NSE's broadcast time, '23-Jan-2025 18:21'),
intimDt / acqfromDt / acqtoDt (typed by the company, and sometimes wrong: '23-Jan-1925', '10-Nov-2026').

The event date is the broadcast time: it is when the market could see the filing, and it is always inside the
requested window. intimDt is only a fallback. A date outside VALID_YEARS is dropped and counted.

Note: as of this build the endpoint answers HTTP 200 with an empty data list from a residential
connection; the shape below is NSE's documented one, exercised by the fixture. An empty answer is a
normal day-with-no-disclosures result, and the run records the last successful fetch per source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import date

from ..http import EventHttp, read_fixture
from . import chunks, ddmmyyyy, parse_nse_ts

log = logging.getLogger(__name__)
URL = "https://www.nseindia.com/api/corporates-pit?index=equities&from_date={a}&to_date={b}"
REFERER = "https://www.nseindia.com/companies-listing/corporate-filings-insider-trading"
SOURCE = "nse_pit"
BACKFILL_CHUNK_DAYS = 30
VALID_YEARS = (2000, 2035)


def fetch(day: date, http: EventHttp | None = None, fixture: str | None = None,
          until: date | None = None) -> list[dict]:
    if fixture:
        payload = json.loads(read_fixture(fixture))
    else:
        payload = (http or EventHttp()).get_json(URL.format(a=ddmmyyyy(day), b=ddmmyyyy(until or day)), REFERER)
    out = []
    for r in payload.get("data", []) if isinstance(payload, dict) else []:
        sym = str(r.get("symbol") or "").strip().upper()
        d, t = parse_nse_ts(r.get("date") or r.get("intimDt"))
        if not sym or not d:
            continue
        if not VALID_YEARS[0] <= int(d[:4]) <= VALID_YEARS[1]:
            log.warning("nse_pit %s: dropped, date %r (intimDt %r) is not plausible", sym, r.get("date"), r.get("intimDt"))
            continue
        qty = _f(r.get("secAcq"))
        sid = hashlib.md5(f"{sym}|{r.get('acqName')}|{r.get('date')}|{qty}|{r.get('tdpTransactionType')}".encode()).hexdigest()[:16]
        out.append({"source": SOURCE, "source_id": sid, "symbol": sym, "event_date": d, "event_time": t,
                    "category": "insider", "subject": f"{r.get('acqName')} ({r.get('personCategory')}) "
                                                      f"{r.get('tdpTransactionType')} {r.get('secAcq')}",
                    "text": str(r.get("acqName") or ""), "url": REFERER,
                    "extra": {"person": r.get("acqName"), "person_category": r.get("personCategory"),
                              "side": str(r.get("tdpTransactionType") or "").strip().upper(),
                              "quantity": qty, "value": _f(r.get("secVal")),
                              "pct_traded": _f(r.get("secAcqPer")),
                              "pct_before": _f(_either(r, "befAcqSharesPer", "befAcqSharesPerc")),
                              "pct_after": _f(_either(r, "afterAcqSharesPer", "afterAcqSharesPerc")),
                              "intimated": r.get("intimDt")}})
    return out


def backfill(start: date, end: date, http: EventHttp | None = None):
    http = http or EventHttp()
    for a, b in chunks(start, end, BACKFILL_CHUNK_DAYS):
        yield f"{a}..{b}", fetch(a, http, until=b)


def _either(r: dict, live: str, documented: str):
    """The live API sends befAcqSharesPer / afterAcqSharesPer; the documented shape says ...Perc."""
    return r.get(live) if r.get(live) not in (None, "") else r.get(documented)


def _f(v):
    try:
        return None if v in (None, "", "-") else float(str(v).replace(",", ""))
    except ValueError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="NSE insider-trading (PIT) disclosures")
    ap.add_argument("--day", type=date.fromisoformat, default=date.today())
    ap.add_argument("--fixture")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    for i in fetch(a.day, fixture=a.fixture):
        print(f"{i['event_date']} {i['symbol']:<12} {i['subject'][:80]}")


if __name__ == "__main__":
    main()
