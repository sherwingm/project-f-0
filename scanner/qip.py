"""QIP (qualified institutional placement) announcements on NSE, 2021 on, for the event screens.

    python -m scanner.qip --from 2021-01-01 --to 2026-10-14        # -> data/cache/qip_events.csv

Source: the corporate-announcements API (scanner/events/sources/nse_announcements.URL) read in 15-day windows; rows
whose category is "Qualified Institutional Placement" are kept with their filing time. A QIP files several notices
(opening, floor price, closing, allotment); `first_per_issue` keeps the first notice of each stock within 45 days.
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .build import ROOT

log = logging.getLogger("qip")
OUT = ROOT / "data" / "cache" / "qip_events.csv"
CATEGORY = "qualified institutional placement"
ISSUE_GAP_DAYS = 45


def keep(rows: list[dict]) -> list[dict]:
    from .events.sources.nse_announcements import parse_nse_ts
    out = []
    for r in rows or []:
        if str(r.get("desc") or "").strip().lower() != CATEGORY:
            continue
        d, t = parse_nse_ts(r.get("an_dt") or r.get("exchdisstime") or r.get("sort_date"))
        sym = str(r.get("symbol") or "").strip().upper()
        if sym and d:
            out.append({"symbol": sym, "date": d, "time": t, "text": str(r.get("attchmntText") or "")[:300],
                        "url": r.get("attchmntFile") or ""})
    return out


def first_per_issue(df: pd.DataFrame, gap: int = ISSUE_GAP_DAYS) -> pd.DataFrame:
    """The first notice of each QIP: a stock's notices within `gap` days of its previous kept one are the same issue."""
    out, last = [], {}
    for r in df.sort_values(["date", "time"]).itertuples(index=False):
        prev = last.get(r.symbol)
        if prev is None or (pd.Timestamp(r.date) - pd.Timestamp(prev)).days > gap:
            out.append(r._asdict())
            last[r.symbol] = r.date
    return pd.DataFrame(out, columns=df.columns)


def fetch(a: date, b: date, http=None) -> pd.DataFrame:
    from .events.http import EventHttp
    from .events.sources.nse_announcements import REFERER, URL, ddmmyyyy
    http = http or EventHttp()
    rows, d = [], a
    while d <= b:
        end = min(b, d + timedelta(days=14))
        try:
            got = http.get_json(URL.format(a=ddmmyyyy(d), b=ddmmyyyy(end)), REFERER)
            got = got if isinstance(got, list) else (got or {}).get("data", [])
            k = keep(got)
            rows += k
            log.info("%s..%s: %d announcements, %d QIP", d, end, len(got), len(k))
        except Exception as exc:  # noqa: BLE001
            log.warning("%s..%s: %s", d, end, exc)
        d = end + timedelta(days=1)
    return pd.DataFrame(rows, columns=["symbol", "date", "time", "text", "url"]).drop_duplicates()


def main() -> None:
    ap = argparse.ArgumentParser(description="NSE QIP announcements -> data/cache/qip_events.csv")
    ap.add_argument("--from", dest="a", type=date.fromisoformat, default=date(2021, 1, 1))
    ap.add_argument("--to", dest="b", type=date.fromisoformat, default=date.today())
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    df = fetch(args.a, args.b)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(len(df), "QIP notices,", len(first_per_issue(df)) if len(df) else 0, "issues ->", OUT)


if __name__ == "__main__":
    main()
