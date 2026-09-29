"""Stock -> NSE sector index map (strategies/S1_v2_weak_sector_put.md) and sector index closes from eod2.

    python -m scanner.sectors            # writes data/sector_map.csv from NSE's constituent lists

Membership of the bank and pharma indices first, then the NIFTY 500 list's industry mapped to the sector index
with history back to 2020. Today's lists: NSE publishes no free history of constituents.
"""
from __future__ import annotations

import argparse
import io
import logging
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

from .build import ROOT
from .equity import RAW_BASE
from .nse_fo import NSE_HEADERS

log = logging.getLogger("sectors")
MAP_PATH = ROOT / "data" / "sector_map.csv"
LIST_URL = "https://nsearchives.nseindia.com/content/indices/{name}.csv"
BENCHMARK = "nifty 500"
# index membership that wins over the industry, in this order
MEMBERSHIP = (("ind_niftypsubanklist", "nifty psu bank"), ("ind_nifty_privatebanklist", "nifty private bank"),
              ("ind_niftybanklist", "nifty bank"), ("ind_niftypharmalist", "nifty pharma"))
INDUSTRY = {
    "Financial Services": "nifty financial services", "Information Technology": "nifty it",
    "Healthcare": "nifty healthcare index", "Automobile and Auto Components": "nifty auto",
    "Fast Moving Consumer Goods": "nifty fmcg", "Consumer Durables": "nifty consumer durables",
    "Metals & Mining": "nifty metal", "Realty": "nifty realty", "Media Entertainment & Publication": "nifty media",
    "Oil Gas & Consumable Fuels": "nifty oil & gas", "Power": "nifty energy",
    "Capital Goods": "nifty infrastructure", "Construction": "nifty infrastructure",
    "Construction Materials": "nifty infrastructure", "Telecommunication": "nifty infrastructure",
    "Services": "nifty services sector",
}


def _list(name: str, get=None) -> pd.DataFrame:
    get = get or (lambda url: requests.get(url, headers=NSE_HEADERS, timeout=60))
    r = get(LIST_URL.format(name=name))
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = [str(c).strip() for c in df.columns]
    df["Symbol"] = df["Symbol"].astype(str).str.strip()
    return df


def build_map(get=None) -> pd.DataFrame:
    """symbol, sector_index, source ('member:<list>' or 'industry:<name>'), for every NIFTY 500 stock with a sector."""
    out: dict[str, tuple[str, str]] = {}
    for lst, index in MEMBERSHIP:
        for sym in _list(lst, get)["Symbol"]:
            out.setdefault(sym, (index, f"member:{lst}"))
    n500 = _list("ind_nifty500list", get)
    for sym, ind in zip(n500["Symbol"], n500["Industry"].astype(str).str.strip()):
        if sym not in out and ind in INDUSTRY:
            out[sym] = (INDUSTRY[ind], f"industry:{ind}")
    return pd.DataFrame([(s, i, src) for s, (i, src) in sorted(out.items())], columns=["symbol", "sector_index", "source"])


def load_map(path: Path = MAP_PATH) -> dict[str, str]:
    df = pd.read_csv(path)
    return dict(zip(df["symbol"], df["sector_index"]))


def index_closes(name: str, eod2_dir: Path) -> pd.Series:
    """Daily closes of an eod2 index file (cached under data/eod2/), indexed by date."""
    path = Path(eod2_dir) / f"{name}.csv"
    if not path.exists():
        r = requests.get(RAW_BASE.format(name=quote(name)), timeout=60)
        r.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(r.text, encoding="utf-8")
    df = pd.read_csv(path, usecols=["Date", "Close"], parse_dates=["Date"])
    return df[df["Close"] > 0].set_index("Date").sort_index()["Close"]


def main() -> None:
    ap = argparse.ArgumentParser(description="build data/sector_map.csv from NSE's index constituent lists")
    ap.add_argument("--out", type=Path, default=MAP_PATH)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    df = build_map()
    df.to_csv(a.out, index=False)
    print(f"{len(df)} stocks -> {a.out}")
    print(df["sector_index"].value_counts().to_string())


if __name__ == "__main__":
    main()
