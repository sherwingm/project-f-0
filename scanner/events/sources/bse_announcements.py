"""BSE corporate announcements (tier 1), mapped to NSE symbols via the exchanges' own masters.

API: https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w?pageno=N&strCat=-1&strPrevDate=YYYYMMDD
     &strScrip=&strSearch=P&strToDate=YYYYMMDD&strType=C          (Referer: https://www.bseindia.com/)
Rows in Table[]: NEWSID, SCRIP_CD, SLONGNAME, NEWSSUB, CATEGORYNAME, SUBCATNAME, NEWS_DT, NSURL/ATTACHMENTNAME.

Mapping: BSE scrip code -> ISIN (BSE ListofScripData master) -> NSE symbol (EQUITY_L.csv), built once into
data/cache/bse_nse_map.csv. Unmapped rows are dropped and counted (`fetch.last_dropped`).

Note: BSE's API answers 403 to this build's network even with full browser headers; the fetcher then logs
and returns nothing, and the run's events_status says so. Every F&O stock files on NSE as well, so tier-1
coverage of this universe does not depend on BSE.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
from datetime import date
from pathlib import Path

from ...build import ROOT
from ..http import EventHttp, FetchError, read_fixture

log = logging.getLogger(__name__)
URL = ("https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w?pageno={page}&strCat=-1&strPrevDate={d:%Y%m%d}"
       "&strScrip=&strSearch=P&strToDate={d:%Y%m%d}&strType=C")
BSE_MASTER = ("https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry="
              "&segment=Equity&status=Active")
NSE_MASTER = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
REFERER = "https://www.bseindia.com/"
SOURCE = "bse_ann"
MAP_PATH = ROOT / "data" / "cache" / "bse_nse_map.csv"
MAX_PAGES = 40


def build_map(http: EventHttp | None = None, path: Path = MAP_PATH,
              bse_fixture: str | None = None, nse_fixture: str | None = None) -> dict[str, str]:
    """BSE scrip code -> NSE symbol by ISIN, written to data/cache/bse_nse_map.csv."""
    http = http or EventHttp()
    bse_rows = json.loads(read_fixture(bse_fixture)) if bse_fixture else http.get_json(BSE_MASTER, REFERER)
    nse_text = read_fixture(nse_fixture) if nse_fixture else http.get_text(NSE_MASTER, "https://www.nseindia.com/")
    isin_to_nse = {}
    for r in csv.DictReader(io.StringIO(nse_text)):
        r = {k.strip(): (v or "").strip() for k, v in r.items()}
        if r.get("SERIES") in ("EQ", "BE") and r.get("ISIN NUMBER"):
            isin_to_nse[r["ISIN NUMBER"]] = r["SYMBOL"]
    mapping = {}
    for r in bse_rows if isinstance(bse_rows, list) else []:
        code, isin = str(r.get("SCRIP_CD") or "").strip(), str(r.get("ISIN_NUMBER") or "").strip()
        if code and isin in isin_to_nse:
            mapping[code] = isin_to_nse[isin]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("scrip_cd,nse_symbol\n" + "".join(f"{c},{s}\n" for c, s in sorted(mapping.items())), encoding="utf-8")
    log.info("BSE->NSE map: %d of %d BSE scrips mapped by ISIN", len(mapping), len(bse_rows or []))
    return mapping


def load_map(path: Path = MAP_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    rows = path.read_text(encoding="utf-8").splitlines()[1:]
    return dict(line.split(",", 1) for line in rows if "," in line)


def fetch(day: date, http: EventHttp | None = None, fixture: str | None = None,
          mapping: dict[str, str] | None = None) -> list[dict]:
    mapping = mapping if mapping is not None else load_map()
    pages = []
    if fixture:
        pages.append(json.loads(read_fixture(fixture)))
    else:
        http = http or EventHttp()
        for page in range(1, MAX_PAGES + 1):
            try:
                payload = http.get_json(URL.format(page=page, d=day), REFERER)
            except FetchError as exc:
                log.warning("BSE announcements page %d: %s", page, exc)
                break
            pages.append(payload)
            rows = payload.get("Table") or []
            total = int((payload.get("Table1") or [{}])[0].get("ROWCNT") or 0)
            if not rows or sum(len(p.get("Table") or []) for p in pages) >= total:
                break
    out, dropped = [], 0
    for payload in pages:
        for r in payload.get("Table") or []:
            code = str(r.get("SCRIP_CD") or "").strip()
            sym = mapping.get(code)
            if not sym:
                dropped += 1
                continue
            dt = str(r.get("NEWS_DT") or r.get("DissemDT") or "").strip()          # 2026-09-22T18:30:05.55
            d, t = (dt[:10], dt[11:16] or None) if len(dt) >= 10 else (None, None)
            if not d:
                continue
            url = r.get("NSURL") or (("https://www.bseindia.com/xml-data/corpfiling/AttachLive/" + r["ATTACHMENTNAME"])
                                     if r.get("ATTACHMENTNAME") else "")
            out.append({"source": SOURCE, "source_id": str(r.get("NEWSID")), "symbol": sym, "event_date": d,
                        "event_time": t, "category": str(r.get("CATEGORYNAME") or "").strip(),
                        "subject": str(r.get("NEWSSUB") or r.get("HEADLINE") or "").strip(),
                        "text": str(r.get("HEADLINE") or r.get("NEWSSUB") or "").strip(), "url": url,
                        "extra": {"scrip_cd": code, "subcategory": r.get("SUBCATNAME"), "company": r.get("SLONGNAME")}})
    fetch.last_dropped = dropped
    if dropped:
        log.info("BSE announcements: %d rows dropped (no NSE mapping)", dropped)
    return out


fetch.last_dropped = 0


def backfill(start: date, end: date, http: EventHttp | None = None):
    http = http or EventHttp()
    mapping = load_map()
    d = start
    from datetime import timedelta
    while d <= end:
        if d.weekday() < 6:
            yield d.isoformat(), fetch(d, http, mapping=mapping)
        d += timedelta(days=1)


def main() -> None:
    ap = argparse.ArgumentParser(description="BSE announcements mapped to NSE symbols")
    ap.add_argument("--day", type=date.fromisoformat, default=date.today())
    ap.add_argument("--fixture")
    ap.add_argument("--build-map", action="store_true", help="rebuild data/cache/bse_nse_map.csv from the masters")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    if a.build_map:
        build_map()
        return
    items = fetch(a.day, fixture=a.fixture)
    print(f"{len(items)} announcements ({fetch.last_dropped} unmapped dropped)")
    for i in items[:15]:
        print(f"  {i['symbol']:<12} {i['category'][:30]:<32} {i['subject'][:60]}")


if __name__ == "__main__":
    main()
