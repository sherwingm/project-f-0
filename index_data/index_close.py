"""Official daily index closes from NSE's free archive (ind_close_all_DDMMYYYY.csv), 2018 → 2025-09.

    python -m index_data.index_close [--from 2018-01-01] [--to 2025-09-30]    # run on the PC: NSE refuses cloud IPs

Why: the 1-minute spot store starts 2021-10-21, so the 2018-2021 studies (L1, the D6 re-run) need NIFTY's daily close
for strike choice and expiry settlement. NIFTY options settle at this official closing value on expiry day. The same
file lists India VIX, used to cross-check vix_daily.parquet (yfinance). Kept: Nifty 50, Nifty Bank, India VIX.
Stored as STORE/index_close_daily.parquet (date, index, open, high, low, close). Restart-safe: days already in the
file are skipped. A 404 means no session that day (holiday).
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import date, timedelta
from io import StringIO

import pandas as pd
import requests

from .common import STORE, upsert_parquet
from .load import read_store

log = logging.getLogger("index_data.index_close")
URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{dmy}.csv"
KEEP = {"Nifty 50": "NIFTY50", "Nifty Bank": "NIFTYBANK", "India VIX": "INDIAVIX"}
FILE = "index_close_daily.parquet"
COLS = {"Open Index Value": "open", "High Index Value": "high", "Low Index Value": "low", "Closing Index Value": "close"}


def parse(text: str, day: date) -> pd.DataFrame:
    d = pd.read_csv(StringIO(text))
    d.columns = [str(c).strip() for c in d.columns]
    d["Index Name"] = d["Index Name"].astype(str).str.strip()
    d = d[d["Index Name"].str.lower().isin([k.lower() for k in KEEP])].copy()
    d["index"] = d["Index Name"].str.lower().map({k.lower(): v for k, v in KEEP.items()})
    d["date"] = day.isoformat()
    d = d.rename(columns=COLS)
    for c in COLS.values():
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d[["date", "index", *COLS.values()]].reset_index(drop=True)


def run(start: date, end: date, store=STORE) -> dict:
    from scanner.nse_fo import NSE_HEADERS
    f = store / FILE
    have = set(pd.read_parquet(f, columns=["date"])["date"]) if f.exists() else set()
    st = {"sessions": 0, "holidays": 0, "skipped_existing": 0, "errors": []}
    d = start
    while d <= end:
        if d.weekday() >= 5 or d.isoformat() in have:
            st["skipped_existing"] += d.isoformat() in have
            d += timedelta(days=1)
            continue
        for attempt in range(3):
            try:
                r = requests.get(URL.format(dmy=d.strftime("%d%m%Y")), headers=NSE_HEADERS, timeout=30)
                if r.status_code == 404:
                    st["holidays"] += 1
                    break
                r.raise_for_status()
                rows = parse(r.text, d)
                if len(rows):
                    upsert_parquet(f, rows, ["date", "index"])
                    st["sessions"] += 1
                break
            except Exception as exc:  # noqa: BLE001 - retry, then record and move on
                if attempt == 2:
                    st["errors"].append(f"{d}: {exc}"[:200])
                time.sleep(3 * (attempt + 1))
        time.sleep(0.3)
        d += timedelta(days=1)
    return st


def load(store=STORE) -> pd.DataFrame:
    d = read_store(store / FILE)
    d["date"] = pd.to_datetime(d["date"]).dt.date
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description="NSE official daily index closes (Nifty 50, Nifty Bank, India VIX)")
    ap.add_argument("--from", dest="start", default="2018-01-01")
    ap.add_argument("--to", dest="end", default="2025-09-30")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(run(date.fromisoformat(a.start), date.fromisoformat(a.end)))


if __name__ == "__main__":
    main()
