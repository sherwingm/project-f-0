"""NSE corporate actions (dividends with their ex-dates and amounts, and the other actions as listed), 2021 on.

    python -m scanner.corp_actions --from 2021-01-01 --to 2026-10-14     # -> data/cache/corp_actions.csv

Source: www.nseindia.com/api/corporates-corporateActions (one call per month, through events/http.EventHttp at
NSE's pace). A dividend's subject reads like "Dividend - Rs 65 Per Sh", "Interim Dividend - Re 0.80 Per Share",
"Annual General Meeting/Dividend - Rs 1.10 Per Share"; several dividends in one row are summed.
"""
from __future__ import annotations

import argparse
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from .build import ROOT

log = logging.getLogger("corp_actions")
URL = "https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date={a}&to_date={b}"
REFERER = "https://www.nseindia.com/companies-listing/corporate-filings-actions"
OUT = ROOT / "data" / "cache" / "corp_actions.csv"
AMOUNT = re.compile(r"(?:Rs\.?|Re\.?|INR)\s*([0-9]+(?:\.[0-9]+)?)", re.I)


def dividend_amount(subject: str) -> float | None:
    """Rupees per share of the dividend(s) in a subject; None when it is not a dividend or names no amount."""
    s = str(subject or "")
    if "dividend" not in s.lower():
        return None
    parts = [p for p in re.split(r"/|;|\band\b", s, flags=re.I) if "dividend" in p.lower() or AMOUNT.search(p)]
    vals = [float(m.group(1)) for p in parts for m in AMOUNT.finditer(p)]
    return round(sum(vals), 4) if vals else None


def parse(rows: list[dict]) -> pd.DataFrame:
    out = []
    for r in rows or []:
        try:
            ex = datetime.strptime(str(r.get("exDate", "")).strip(), "%d-%b-%Y").date().isoformat()
        except ValueError:
            continue
        subj = str(r.get("subject") or "").strip()
        out.append({"symbol": str(r.get("symbol") or "").strip(), "series": r.get("series"), "ex_date": ex,
                    "subject": subj, "dividend_rs": dividend_amount(subj),
                    "kind": "dividend" if "dividend" in subj.lower() else
                            "split" if "split" in subj.lower() else "bonus" if "bonus" in subj.lower() else "other",
                    "face_value": r.get("faceVal")})
    return pd.DataFrame(out)


def fetch(a: date, b: date, http=None) -> pd.DataFrame:
    from .events.http import EventHttp
    http = http or EventHttp()
    frames, d = [], date(a.year, a.month, 1)
    while d <= b:
        end = min(b, (date(d.year + d.month // 12, d.month % 12 + 1, 1) - timedelta(days=1)))
        try:
            rows = http.get_json(URL.format(a=d.strftime("%d-%m-%Y"), b=end.strftime("%d-%m-%Y")), REFERER)
            rows = rows if isinstance(rows, list) else (rows or {}).get("data", [])
            frames.append(parse(rows))
            log.info("%s: %d actions", d.strftime("%Y-%m"), len(rows))
        except Exception as exc:  # noqa: BLE001 - a month that fails is logged and retried on the next run
            log.warning("%s: %s", d.strftime("%Y-%m"), exc)
        d = end + timedelta(days=1)
    return pd.concat(frames, ignore_index=True).drop_duplicates() if frames else pd.DataFrame()


def main() -> None:
    ap = argparse.ArgumentParser(description="NSE corporate actions -> data/cache/corp_actions.csv")
    ap.add_argument("--from", dest="a", type=date.fromisoformat, default=date(2021, 1, 1))
    ap.add_argument("--to", dest="b", type=date.fromisoformat, default=date.today())
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    df = fetch(args.a, args.b)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(len(df), "actions;", int((df["kind"] == "dividend").sum()) if len(df) else 0, "dividends ->", OUT)


if __name__ == "__main__":
    main()
