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
INDEX_FILE = "nifty 50"   # eod2's NIFTY 50 file (daily/nifty 50.csv): the market the scoreboard adjusts for


# Old NSE symbols (still in older bhavcopies) -> the symbol eod2 files the same company's history under.
# Renames only: a merger into another listed stock (HDFC -> HDFCBANK, IDFC -> IDFCFIRSTB) is not an alias.
# TMPV's eod2 history is not adjusted for the Oct 2025 demerger (660.75 on 2025-10-13, 395.45 on 2025-10-14).
EOD2_ALIASES = {
    "TATAMOTORS": "TMPV",          # Tata Motors -> Tata Motors Passenger Vehicles (demerger, Oct 2025)
    "LTIM": "LTM",                 # LTIMindtree
    "MCDOWELL-N": "UNITDSPR",      # United Spirits
    "L&TFH": "LTF",                # L&T Finance
    "GMRINFRA": "GMRAIRPORT",      # GMR Airports
    "PVR": "PVRINOX",              # PVR INOX
    "IBULHSGFIN": "SAMMAANCAP",    # Sammaan Capital
}
_MISSING: set[str] = set()


def eod2_filename(symbol: str) -> str:
    # eod2 names files with the lowercase NSE symbol, special characters kept (m&m.csv, bajaj-auto.csv)
    return EOD2_ALIASES.get(symbol.upper(), symbol).lower()


def load_symbol(symbol: str, local_dir: Path | None, timeout: int = 60) -> pd.DataFrame:
    name = eod2_filename(symbol)
    path = local_dir / f"{name}.csv" if local_dir else None
    if path and path.exists():
        raw = pd.read_csv(path, usecols=["Date", "Open", "High", "Low", "Close", "Volume", "Series"],
                          parse_dates=["Date"])
    else:
        r = requests.get(RAW_BASE.format(name=name), timeout=timeout)
        if r.status_code == 404 and symbol not in _MISSING:       # once per symbol per run
            _MISSING.add(symbol)
            log.warning("eod2 has no file for %s (tried daily/%s.csv); if NSE renamed it, add it to "
                        "EOD2_ALIASES in scanner/equity.py", symbol, name)
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
    # each session's volume / the average of the 20 sessions before it, for the scoreboard's naive baseline
    ratios = (df["Volume"] / df["Volume"].rolling(VOL_WINDOW).mean().shift(1)).iloc[-CHART_DAYS:]
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
        "chart_volume_ratios": [None if pd.isna(v) else round(float(v), 2) for v in ratios.values],
    }


def index_closes(local_dir: Path | None, as_of: pd.Timestamp, name: str = INDEX_FILE, days: int = CHART_DAYS,
                 timeout: int = 60) -> dict | None:
    """The last `days` closes of an eod2 index file up to `as_of`, for market-adjusted scoring.
    Returns {"name", "dates", "closes"} or None when the file cannot be read (the page then scores raw moves)."""
    path = local_dir / f"{name}.csv" if local_dir else None
    try:
        if path and path.exists():
            raw = pd.read_csv(path, usecols=["Date", "Close"], parse_dates=["Date"])
        else:
            r = requests.get(RAW_BASE.format(name=requests.utils.quote(name)), timeout=timeout)
            r.raise_for_status()
            from io import StringIO
            raw = pd.read_csv(StringIO(r.text), usecols=["Date", "Close"], parse_dates=["Date"])
            if path:
                local_dir.mkdir(parents=True, exist_ok=True)
                raw.to_csv(path, index=False)
    except Exception as exc:  # noqa: BLE001 - the scan never fails for want of the index
        log.warning("index %s unavailable (%s); the scoreboard will use raw moves", name, exc)
        return None
    raw = raw[raw["Close"] > 0].set_index("Date").sort_index()
    raw = raw[raw.index <= as_of].iloc[-days:]
    if raw.empty:
        return None
    return {"name": name.upper(), "dates": [d.strftime("%Y-%m-%d") for d in raw.index],
            "closes": [round(float(c), 2) for c in raw["Close"].values]}


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
