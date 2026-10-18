"""S2 screen B gate 2: the external series, cached once (strategies/S2_put_screens_B.md).

    python -m scanner.s2_parents --fetch       # download once -> data/parents/yf_<ticker>.csv (+ 1h bars for the check)
    python -m scanner.s2_parents               # print the cache's rows, ranges and SHA-256

yfinance 1.7.0, auto_adjust=False, column Close, index stripped to the exchange trade date, range 2020-04-01 ..
2026-09-27, never a bar dated on or after the download day. Reruns read the cache and never download again.
"""
from __future__ import annotations

import argparse
import hashlib
import logging
from datetime import date
from pathlib import Path

import pandas as pd

from .build import ROOT

log = logging.getLogger("s2_parents")

DIR = ROOT / "data" / "parents"
TICKERS = ("INFY", "USDINR=X", "BZ=F", "HG=F", "TIO=F", "ALI=F", "^GSPC")
HOURLY = ("BZ=F", "HG=F", "ALI=F", "INFY")
START, END = "2020-04-01", "2026-09-27"


def path_of(ticker: str, hourly: bool = False) -> Path:
    return DIR / f"yf_{ticker.replace('^', '').replace('=', '_')}{'_1h' if hourly else ''}.csv"


def load(ticker: str, hourly: bool = False) -> pd.Series:
    """The cached Close series of a ticker (daily: indexed by the exchange trade date as YYYY-MM-DD)."""
    f = pd.read_csv(path_of(ticker, hourly), index_col=0)
    return f["Close"].astype(float).dropna()


def strict_before(series: pd.Series, entry: str, signal_day: str) -> tuple[str, float] | None:
    """The last bar dated strictly before the entry session and on or before the signal day (spec: never asof/ffill)."""
    s = series[(series.index < entry) & (series.index <= signal_day)]
    return (s.index[-1], float(s.iloc[-1])) if len(s) else None


def fetch() -> None:
    import yfinance as yf
    DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    for t in TICKERS:
        d = yf.download(t, start=START, end=END, auto_adjust=False, progress=False, interval="1d")
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d.index = pd.to_datetime(d.index).tz_localize(None).strftime("%Y-%m-%d")
        d = d[d.index < today][["Open", "High", "Low", "Close", "Volume"]]
        d.index.name = "Date"
        d.to_csv(path_of(t))
        log.info("%s: %d daily bars %s .. %s", t, len(d), d.index[0], d.index[-1])
    for t in HOURLY:                                                  # Yahoo serves 1h bars for the last 730 days only
        d = yf.download(t, period="730d", auto_adjust=False, progress=False, interval="1h")
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        idx = pd.to_datetime(d.index)
        idx = idx.tz_convert("America/New_York") if idx.tz is not None else idx
        d.index = idx.tz_localize(None).strftime("%Y-%m-%d %H:%M")
        d = d[d.index < today][["Open", "High", "Low", "Close", "Volume"]]
        d.index.name = "Datetime_ET"
        d.to_csv(path_of(t, hourly=True))
        log.info("%s: %d hourly bars", t, len(d))


def manifest() -> pd.DataFrame:
    rows = []
    for t in TICKERS:
        for h in ((False, True) if t in HOURLY else (False,)):
            p = path_of(t, h)
            if not p.exists():
                continue
            s = load(t, h)
            rows.append({"file": p.name, "rows": len(s), "first": s.index[0], "last": s.index[-1],
                         "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="S2 screen B external series (cached once)")
    ap.add_argument("--fetch", action="store_true", help="download into data/parents/ (only when the cache is empty)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if a.fetch:
        if any(path_of(t).exists() for t in TICKERS):
            raise SystemExit("the cache exists: reruns read it and never download again")
        fetch()
    print(manifest().to_string(index=False))


if __name__ == "__main__":
    main()
