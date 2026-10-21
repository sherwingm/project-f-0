"""Each stock option's listing-day price: the close of its first session with volume > 0 (the S1 v12 below-Rs 2 rule,
strategies/S1_v12_sub2_listing.md).

    python -m scanner.listing_prices backfill     # from the local NSE caches, for every expiry not yet passed

Stored per expiry in data/listing/<expiry>.csv (symbol, side, strike, first_day, first_close). scanner/fade_live.py
adds each night's newly traded contracts (update) and attaches the prices to the fade signals (lookup).
"""
from __future__ import annotations

import glob
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from .build import ROOT

DIR = ROOT / "data" / "listing"
COLS = ["symbol", "side", "strike", "first_day", "first_close"]


def _load(expiry: str, d: Path = DIR) -> pd.DataFrame:
    f = d / f"{expiry}.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame(columns=COLS)


def update(bhav: pd.DataFrame, day: str, d: Path = DIR, today: str | None = None) -> int:
    """Add the stock options first traded on `day` (bhavcopy rows: TckrSymb, FinInstrmTp, XpryDt, StrkPric, OptnTp,
    ClsPric, TtlTradgVol). Expiries already passed are skipped; returns the contracts added."""
    today = today or date.today().isoformat()
    b = bhav[(bhav["FinInstrmTp"] == "STO") & (pd.to_numeric(bhav["TtlTradgVol"], errors="coerce") > 0)].copy()
    b["XpryDt"] = b["XpryDt"].astype(str).str[:10]
    added = 0
    d.mkdir(parents=True, exist_ok=True)
    for exp, g in b[b["XpryDt"] >= today].groupby("XpryDt"):
        cur = _load(exp, d)
        have = set(zip(cur["symbol"], cur["side"], cur["strike"].astype(float)))
        new = [{"symbol": str(r.TckrSymb).strip(), "side": r.OptnTp, "strike": float(r.StrkPric), "first_day": day,
                "first_close": float(r.ClsPric)} for r in g.itertuples()
               if (str(r.TckrSymb).strip(), r.OptnTp, float(r.StrkPric)) not in have]
        if new:
            out = pd.concat([cur, pd.DataFrame(new)], ignore_index=True)
            out = out.sort_values(["first_day"]).drop_duplicates(["symbol", "side", "strike"], keep="first")
            out.sort_values(["symbol", "side", "strike"]).to_csv(d / f"{exp}.csv", index=False)
            added += len(new)
    for f in d.glob("*.csv"):                                     # passed expiries are no longer needed
        if f.stem < today:
            f.unlink()
    return added


def lookup(symbol: str, side: str, expiry: str, d: Path = DIR) -> dict[str, float]:
    """{strike as text: listing-day close} for one stock, side and expiry."""
    g = _load(expiry, d)
    g = g[(g["symbol"] == symbol) & (g["side"] == side)]
    return {f"{float(k):g}": float(v) for k, v in zip(g["strike"], g["first_close"])}


def backfill(cache: Path = ROOT / "data" / "cache", d: Path = DIR, today: str | None = None) -> int:
    """From the local fo_bhavcopy_*.csv (to its end) and fo_prices_*.csv (later days), in date order."""
    today = today or date.today().isoformat()
    files = {}
    for f in glob.glob(str(cache / "fo_bhavcopy_*.csv")):
        files[f[-12:-4]] = ("bhav", f)
    for f in glob.glob(str(cache / "fo_prices_*.csv")):
        files.setdefault(f[-12:-4], ("prices", f))
    n = 0
    for k in sorted(files):
        if k < "20260601":                                       # series still open in Oct 2026 listed after this
            continue
        kind, f = files[k]
        x = pd.read_csv(f)
        if kind == "prices":
            x["FinInstrmTp"] = "STO"
        n += update(x, f"{k[:4]}-{k[4:6]}-{k[6:]}", d, today)
    return n


if __name__ == "__main__":
    if sys.argv[1:] == ["backfill"]:
        print("added", backfill())
