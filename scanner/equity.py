"""Price change, volume ratio and the 30-day close series from eod2 daily CSVs.

Reuses the Quantis data path: the BennyThadikaran/eod2_data repository (NSE bhavcopy, adjusted
for corporate actions), one CSV per symbol under daily/, EQ series only. Files are read from a
local checkout/download dir when present and fetched from raw.githubusercontent.com otherwise.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)

RAW_BASE = "https://raw.githubusercontent.com/BennyThadikaran/eod2_data/main/daily/{name}.csv"
VOL_WINDOW = 20      # sessions in the average-volume baseline
CHART_DAYS = 30      # closes kept for the expandable chart


def eod2_filename(symbol: str) -> str:
    # eod2 names files with the lowercase NSE symbol, special characters kept (m&m.csv, bajaj-auto.csv)
    return symbol.lower()


def load_symbol(symbol: str, local_dir: Path | None, timeout: int = 60) -> pd.DataFrame:
    name = eod2_filename(symbol)
    path = local_dir / f"{name}.csv" if local_dir else None
    if path and path.exists():
        raw = pd.read_csv(path, usecols=["Date", "Open", "High", "Low", "Close", "Volume", "Series"],
                          parse_dates=["Date"])
    else:
        r = requests.get(RAW_BASE.format(name=name), timeout=timeout)
        r.raise_for_status()
        from io import StringIO
        raw = pd.read_csv(StringIO(r.text), usecols=["Date", "Open", "High", "Low", "Close", "Volume", "Series"],
                          parse_dates=["Date"])
        if local_dir:
            local_dir.mkdir(parents=True, exist_ok=True)
            raw.to_csv(path, index=False)
    raw = raw[raw["Series"] == "EQ"].drop(columns="Series").set_index("Date").sort_index()
    return raw[(raw["Close"] > 0)]


def equity_metrics_one(symbol: str, df: pd.DataFrame, as_of: pd.Timestamp | None = None) -> dict | None:
    """Metrics for the session ``as_of`` (default: last row). Returns None when history is too short."""
    if as_of is not None:
        df = df[df.index <= as_of]
    if len(df) < VOL_WINDOW + 2:
        return None
    last, prev = df.iloc[-1], df.iloc[-2]
    baseline = df["Volume"].iloc[-(VOL_WINDOW + 1):-1]          # the 20 sessions before the last one
    avg_vol = float(baseline.mean()) if len(baseline) == VOL_WINDOW else None
    closes = df["Close"].iloc[-CHART_DAYS:]
    return {
        "symbol": symbol,
        "date": last.name.strftime("%Y-%m-%d"),
        "prev_date": prev.name.strftime("%Y-%m-%d"),
        "close": round(float(last["Close"]), 2),
        "prev_close": round(float(prev["Close"]), 2),
        "price_change_pct": round((float(last["Close"]) / float(prev["Close"]) - 1) * 100, 2),
        "volume": int(last["Volume"]),
        "avg_volume_20d": int(avg_vol) if avg_vol else None,
        "volume_ratio": round(float(last["Volume"]) / avg_vol, 2) if avg_vol else None,
        "chart_dates": [d.strftime("%Y-%m-%d") for d in closes.index],
        "chart_closes": [round(float(c), 2) for c in closes.values],
    }


def equity_metrics(symbols: list[str], local_dir: Path | None, workers: int = 8) -> tuple[pd.Timestamp, list[dict]]:
    """Load every symbol, align all of them on the latest common session, return (as_of, rows)."""
    frames: dict[str, pd.DataFrame] = {}

    def _load(sym: str):
        try:
            frames[sym] = load_symbol(sym, local_dir)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: no eod2 data (%s)", sym, exc)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(_load, symbols))

    if not frames:
        raise RuntimeError("No eod2 data loaded for any symbol")
    # The universe's most common last date; a few symbols can lag (suspended, just listed).
    last_dates = pd.Series({s: f.index[-1] for s, f in frames.items()})
    as_of = last_dates.mode().iloc[0]
    rows = []
    for sym, f in frames.items():
        m = equity_metrics_one(sym, f, as_of=as_of)
        if m and m["date"] == as_of.strftime("%Y-%m-%d"):
            rows.append(m)
        else:
            log.warning("%s: no bar for %s, skipped", sym, as_of.date())
    return as_of, rows
