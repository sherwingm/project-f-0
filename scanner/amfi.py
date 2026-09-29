"""AMFI market-cap categories (large / mid / small), point in time.

    python -m scanner.amfi          # downloads the half-yearly lists, writes data/amfi_categories.csv

AMFI publishes, twice a year, every listed company ranked by its 6-month average market cap: ranks 1-100
Large Cap, 101-250 Mid Cap, the rest Small Cap (SEBI circular of 6 Oct 2017). A list is used from the first day
of the second month after its half-year ends (the list for the half ending 30 Jun is in force 1 Aug - 31 Jan;
31 Dec: 1 Feb - 31 Jul), the date by which SEBI requires funds to comply; until the next list is published,
the latest one stays in force.
"""
from __future__ import annotations

import argparse
import bisect
import logging
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from .build import ROOT
from .equity import EOD2_ALIASES

log = logging.getLogger("amfi")
PATH = ROOT / "data" / "amfi_categories.csv"
_B = "https://www.amfiindia.com/Themes/Theme1/downloads/"
LISTS = {                                                  # half-year end -> AMFI's file (names vary by year)
    "2020-06-30": _B + "Average%20Market%20Capitalization%20of%20Listed%20Companies%20during%20Jan%20-%20Jun%202020_Final.xlsx",
    "2020-12-31": _B + "Average%20Market%20Capitalization%20of%20Listed%20Companies%20during%20Jul%20-%20Dec%202020_Final.xlsx",
    "2021-06-30": _B + "Average%20Market%20Capitalization%20of%20List%20Companies%20during%20Jan-June%202021.xlsx",
    "2021-12-31": _B + "Average%20Market%20Capitalisation%20of%20Listed%20Companies%20during%20Jul%20-%20Dec%202021.xlsx",
    "2022-06-30": _B + "AverageMarketCapitalizationoflistedcompaniesduringthesixmonthsended30June2022.xlsx",
    "2022-12-31": _B + "AverageMarketCapitalizationoflistedcompaniesduringthesixmonthsended31Dec2022.xlsx",
    "2023-06-30": _B + "AverageMarketCapitalizationoflistedcompaniesduringthesixmonthsended30Jun2023.xlsx",
    "2023-12-31": _B + "AverageMarketCapitalizationoflistedcompaniesduringthesixmonthsended31Dec2023.xlsx",
    "2024-06-30": "https://www.amfiindia.com/uploads/Average_Market_Capitalization_30_Jun2024_2a1ab4c1d8.xlsx",
    "2024-12-31": _B + "AverageMarketCapitalizationoflistedcompaniesduringthesixmonthsended31Dec2024.xlsx",
    "2025-06-30": _B + "AverageMarketCapitalization30Jun2025.xlsx",
    "2025-12-31": _B + "AverageMarketCapitalization31Dec2025.xlsx",
}
CATEGORY = {"Large Cap": "large", "Mid Cap": "mid", "Small Cap": "small"}


def in_force_from(half_end: str) -> str:
    """First day a list is used: 1 Aug for a half ending 30 Jun, 1 Feb of the next year for 31 Dec."""
    y, mth = int(half_end[:4]), int(half_end[5:7])
    return f"{y}-08-01" if mth == 6 else f"{y + 1}-02-01"


def parse(path: Path) -> pd.DataFrame:
    """symbol, category, rank from one AMFI xlsx (title row, then the header)."""
    x = pd.read_excel(path, header=1)
    sym = next(c for c in x.columns if str(c).strip().startswith("NSE Symbol"))
    cat = next(c for c in x.columns if str(c).strip().startswith("Categorization"))
    df = pd.DataFrame({"symbol": x[sym].astype(str).str.strip().str.upper(),
                       "category": x[cat].astype(str).str.strip().map(CATEGORY), "rank": x.iloc[:, 0]})
    return df[df["symbol"].ne("") & df["symbol"].ne("NAN") & df["category"].notna()].drop_duplicates("symbol")


def build(folder: Path, get=None) -> pd.DataFrame:
    get = get or (lambda url: requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120))
    folder.mkdir(parents=True, exist_ok=True)
    frames = []
    for half, url in LISTS.items():
        f = folder / f"{half}.xlsx"
        if not f.exists():
            r = get(url)
            r.raise_for_status()
            f.write_bytes(r.content)
        frames.append(parse(f).assign(half_end=half))
    return pd.concat(frames, ignore_index=True)[["half_end", "symbol", "category", "rank"]]


class Categories:
    """category_on(symbol, day) -> (large / mid / small / unknown, the half-year list used)."""

    def __init__(self, table: pd.DataFrame):
        self.versions = sorted(table["half_end"].unique())
        self.starts = [in_force_from(v) for v in self.versions]
        self.maps = {v: dict(zip(g["symbol"], g["category"])) for v, g in table.groupby("half_end")}
        rev = {v: k for k, v in EOD2_ALIASES.items()}
        self.names = lambda s: [s, EOD2_ALIASES.get(s, s), rev.get(s, s)]

    def version_on(self, day: str) -> str | None:
        j = bisect.bisect_right(self.starts, day) - 1
        return self.versions[j] if j >= 0 else None

    def category_on(self, symbol: str, day: str) -> tuple[str, str | None]:
        v = self.version_on(day)
        if v is None:
            return "unknown", None
        m = self.maps[v]
        for s in self.names(symbol.upper()):
            if s in m:
                return m[s], v
        return "unknown", v


def load(path: Path = PATH) -> Categories:
    return Categories(pd.read_csv(path))


def main() -> None:
    ap = argparse.ArgumentParser(description="AMFI large / mid / small lists -> data/amfi_categories.csv")
    ap.add_argument("--folder", type=Path, default=ROOT / "data" / "cache" / "amfi")
    ap.add_argument("--out", type=Path, default=PATH)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    df = build(a.folder)
    df.to_csv(a.out, index=False)
    print(df.groupby(["half_end", "category"]).size().unstack().to_string())


if __name__ == "__main__":
    main()
