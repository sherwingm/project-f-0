"""Current NSE F&O stock universe, read from NSE's own permitted-lot-size file.

NSE publishes https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv and revises it
whenever stocks enter or leave the derivatives segment, so the list is fetched live on every
build and never hardcoded. Index rows (NIFTY, BANKNIFTY, ...) are dropped: this scanner is
stock-level only.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd
import requests

from .nse_fo import NSE_HEADERS

log = logging.getLogger(__name__)

MKTLOTS_URL = "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"


def fetch_fo_universe(cache_path: Path | None = None, timeout: int = 30) -> list[str]:
    """Return the sorted list of F&O-eligible stock symbols (see fetch_fo_lots for lot sizes)."""
    return sorted(fetch_fo_lots(cache_path, timeout))


def fetch_fo_lots(cache_path: Path | None = None, timeout: int = 30) -> dict[str, int]:
    """Return {symbol: current-month lot size} for every F&O-eligible stock.

    Falls back to ``cache_path`` (one symbol per line) when NSE is unreachable, so a stale
    universe is used rather than an empty one; the caller is told via the log.
    """
    try:
        r = requests.get(MKTLOTS_URL, headers=NSE_HEADERS, timeout=timeout)
        r.raise_for_status()
        lots = _parse_mktlots(r.text)
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text("\n".join(f"{s},{n}" for s, n in sorted(lots.items())) + "\n")
        log.info("F&O universe: %d stocks (live from NSE)", len(lots))
        return lots
    except Exception as exc:  # noqa: BLE001 - any network/parse failure falls back
        if cache_path and cache_path.exists():
            lots = {}
            for line in cache_path.read_text().splitlines():
                if not line.strip():
                    continue
                sym, _, n = line.strip().partition(",")
                lots[sym] = int(n) if n.isdigit() else 0
            log.warning("NSE unreachable (%s); using cached universe of %d stocks", exc, len(lots))
            return lots
        raise RuntimeError(f"Could not fetch F&O universe from {MKTLOTS_URL}: {exc}") from exc


def _parse_mktlots(text: str) -> dict[str, int]:
    """The file has two blocks: index rows, then a 'Derivatives on Individual Securities' header
    followed by one row per stock. Every value is padded with spaces."""
    df = pd.read_csv(io.StringIO(text), skipinitialspace=True, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df = df.map(lambda v: v.strip() if isinstance(v, str) else v)
    # locate the stock block by its sub-header row
    first_col = df.columns[0]
    start_rows = df.index[df[first_col].str.contains("Individual Securities", case=False, na=False)]
    if len(start_rows) == 0:
        raise ValueError("fo_mktlots.csv layout changed: stock block header not found")
    stocks = df.loc[start_rows[0] + 1 :]
    stocks = stocks[stocks["SYMBOL"].notna() & (stocks["SYMBOL"].str.len() > 0)]
    lot_col = df.columns[2]                       # first expiry column = current month's lot
    out = {}
    for _, r in stocks.iterrows():
        v = str(r[lot_col]).strip()
        out[r["SYMBOL"]] = int(v) if v.isdigit() else 0
    return out


def pit_universe(cache_dir: Path, since: str | None = None, until: str | None = None) -> dict[str, set[str]]:
    """Point-in-time F&O universe: {YYYY-MM-DD: stocks with stock futures (STF) in that day's cached bhavcopy}.
    Stocks that later left F&O are in; stocks that joined later are not yet; index derivatives never are."""
    out: dict[str, set[str]] = {}
    for f in sorted(Path(cache_dir).glob("fo_bhavcopy_*.csv")):
        d = f"{f.stem[-8:-4]}-{f.stem[-4:-2]}-{f.stem[-2:]}"
        if (since and d < since) or (until and d > until):
            continue
        b = pd.read_csv(f, usecols=["TckrSymb", "FinInstrmTp"])
        out[d] = set(b.loc[b["FinInstrmTp"] == "STF", "TckrSymb"].astype(str).str.strip())
    return out
