"""NSE block-deal and bulk-deal files (tier 1): client name, buy/sell, quantity, trade price.

API: https://www.nseindia.com/api/historicalOR/bulk-block-short-deals?optionType={block_deals|bulk_deals}
     &from=DD-MM-YYYY&to=DD-MM-YYYY
Rows: BD_DT_DATE, BD_SYMBOL, BD_CLIENT_NAME, BD_BUY_SELL, BD_QTY_TRD, BD_TP_WATP, BD_REMARKS.

The JSON answer is capped at 70 rows per request, whatever the range (a single busy day has 180+ bulk deals),
and silently drops the rest. The same endpoint with &csv=true (the page's "Download (.csv)") is not capped: a
30-day bulk request returned 2,685 rows. So the CSV is read, 30 days at a time for both kinds; CSV columns:
Date, Symbol, Security Name, Client Name, Buy / Sell, Quantity Traded ('12,54,865'), Trade Price / Wght. Avg.
Price, Remarks. Fixtures keep the JSON shape.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import logging
from datetime import date, datetime

from ..http import EventHttp, read_fixture
from . import chunks, ddmmyyyy

log = logging.getLogger(__name__)
URL = ("https://www.nseindia.com/api/historicalOR/bulk-block-short-deals?optionType={kind}_deals"
       "&from={a}&to={b}")
REFERER = "https://www.nseindia.com/report-detail/display-bulk-and-block-deals"
KINDS = ("block", "bulk")
BACKFILL_CHUNK_DAYS = {"block": 30, "bulk": 30}
CSV_TO_JSON = {"Date": "BD_DT_DATE", "Symbol": "BD_SYMBOL", "Client Name": "BD_CLIENT_NAME", "Buy / Sell": "BD_BUY_SELL",
               "Quantity Traded": "BD_QTY_TRD", "Trade Price / Wght. Avg. Price": "BD_TP_WATP", "Remarks": "BD_REMARKS"}


def fetch(day: date, http: EventHttp | None = None, fixture: str | None = None,
          kind: str = "block", until: date | None = None) -> list[dict]:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if fixture:
        payload = json.loads(read_fixture(fixture))
        rows = payload.get("data", []) if isinstance(payload, dict) else []
    else:
        rows = _csv_rows(http or EventHttp(), kind, day, until or day)
    out = []
    for r in rows:
        sym = str(r.get("BD_SYMBOL") or "").strip().upper()
        try:
            d = datetime.strptime(str(r.get("BD_DT_DATE")).strip(), "%d-%b-%Y").date().isoformat()
        except (ValueError, TypeError):
            continue
        if not sym:
            continue
        qty = int(_f(r.get("BD_QTY_TRD")) or 0)
        price = _f(r.get("BD_TP_WATP"))
        side = str(r.get("BD_BUY_SELL") or "").strip().upper()
        client = str(r.get("BD_CLIENT_NAME") or "").strip()
        sid = hashlib.md5(f"{d}|{sym}|{client}|{side}|{qty}|{price if price is None else f'{price:.4f}'}".encode()).hexdigest()[:16]
        out.append({"source": f"nse_{kind}", "source_id": sid, "symbol": sym, "event_date": d, "event_time": None,
                    "category": f"{kind} deal", "subject": f"{client} {side} {qty:,} @ {price}",
                    "text": client, "url": REFERER,
                    "extra": {"client": client, "side": side, "quantity": qty, "price": price,
                              "remarks": r.get("BD_REMARKS")}})
    return out


def _csv_rows(http: EventHttp, kind: str, a: date, b: date) -> list[dict]:
    """Every row for [a, b] from the uncapped CSV download, keyed like the JSON rows."""
    text = http.get(URL.format(kind=kind, a=ddmmyyyy(a), b=ddmmyyyy(b)) + "&csv=true", REFERER).content.decode("utf-8-sig")
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        row = {str(k).strip(): (v or "").strip() for k, v in row.items() if k}
        out.append({CSV_TO_JSON[k]: v for k, v in row.items() if k in CSV_TO_JSON})
    return out


def backfill(start: date, end: date, http: EventHttp | None = None, kind: str = "block"):
    http = http or EventHttp()
    for a, b in chunks(start, end, BACKFILL_CHUNK_DAYS[kind]):
        yield f"{kind} {a}..{b}", fetch(a, http, kind=kind, until=b)


def _f(v):
    try:
        return float(str(v).replace(",", ""))           # the CSV writes Indian grouping: 12,54,865
    except (TypeError, ValueError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="NSE block/bulk deals")
    ap.add_argument("--day", type=date.fromisoformat, default=date.today())
    ap.add_argument("--kind", choices=KINDS, default="block")
    ap.add_argument("--fixture")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    for i in fetch(a.day, kind=a.kind, fixture=a.fixture):
        print(f"{i['event_date']} {i['symbol']:<12} {i['subject'][:80]}")


if __name__ == "__main__":
    main()
