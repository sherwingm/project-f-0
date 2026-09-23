"""NSE block-deal and bulk-deal files (tier 1): client name, buy/sell, quantity, trade price.

API: https://www.nseindia.com/api/historicalOR/bulk-block-short-deals?optionType={block_deals|bulk_deals}
     &from=DD-MM-YYYY&to=DD-MM-YYYY
Rows: BD_DT_DATE, BD_SYMBOL, BD_CLIENT_NAME, BD_BUY_SELL, BD_QTY_TRD, BD_TP_WATP, BD_REMARKS.
"""
from __future__ import annotations

import argparse
import hashlib
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
BACKFILL_CHUNK_DAYS = 30


def fetch(day: date, http: EventHttp | None = None, fixture: str | None = None,
          kind: str = "block", until: date | None = None) -> list[dict]:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if fixture:
        payload = json.loads(read_fixture(fixture))
    else:
        payload = (http or EventHttp()).get_json(URL.format(kind=kind, a=ddmmyyyy(day), b=ddmmyyyy(until or day)), REFERER)
    out = []
    for r in payload.get("data", []) if isinstance(payload, dict) else []:
        sym = str(r.get("BD_SYMBOL") or "").strip().upper()
        try:
            d = datetime.strptime(str(r.get("BD_DT_DATE")).strip(), "%d-%b-%Y").date().isoformat()
        except (ValueError, TypeError):
            continue
        if not sym:
            continue
        qty = int(float(r.get("BD_QTY_TRD") or 0))
        side = str(r.get("BD_BUY_SELL") or "").strip().upper()
        client = str(r.get("BD_CLIENT_NAME") or "").strip()
        sid = hashlib.md5(f"{d}|{sym}|{client}|{side}|{qty}|{r.get('BD_TP_WATP')}".encode()).hexdigest()[:16]
        out.append({"source": f"nse_{kind}", "source_id": sid, "symbol": sym, "event_date": d, "event_time": None,
                    "category": f"{kind} deal", "subject": f"{client} {side} {qty:,} @ {r.get('BD_TP_WATP')}",
                    "text": client, "url": REFERER,
                    "extra": {"client": client, "side": side, "quantity": qty, "price": _f(r.get("BD_TP_WATP")),
                              "remarks": r.get("BD_REMARKS")}})
    return out


def backfill(start: date, end: date, http: EventHttp | None = None, kind: str = "block"):
    http = http or EventHttp()
    for a, b in chunks(start, end, BACKFILL_CHUNK_DAYS):
        yield f"{kind} {a}..{b}", fetch(a, http, kind=kind, until=b)


def _f(v):
    try:
        return float(v)
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
