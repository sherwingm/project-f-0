"""Inspect the cached NSE F&O bhavcopy for the data gaps that can affect a build.

    python -m scanner.diagnose                 # latest cached bhavcopy
    python -m scanner.diagnose 2026-09-18      # a specific date

Reports, per stock: NaN cells in the columns the scanner uses, strikes listed on one side only
(a call without a put or the reverse) in the nearest expiry, and whether the stock has futures
rows at all. Run it on a few different days to tell a one-off gap from a recurring one.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from .strikes import option_chains
from .nse_fo import COLUMNS, fo_metrics

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"


def main() -> None:
    files = sorted(CACHE.glob("fo_bhavcopy_*.csv"))
    if not files:
        sys.exit(f"no cached bhavcopy under {CACHE}; run python -m scanner.build first")
    if len(sys.argv) > 1:
        want = sys.argv[1].replace("-", "")
        files = [f for f in files if want in f.name] or sys.exit(f"no cached bhavcopy for {sys.argv[1]}")
    path = files[-1]
    bhav = pd.read_csv(path)
    missing = [c for c in COLUMNS if c not in bhav.columns]
    print(f"{path.name}: {len(bhav)} rows, {bhav['TckrSymb'].nunique()} symbols" + (f", MISSING COLUMNS {missing}" if missing else ""))

    # 1. NaN cells per column, and which symbols carry them
    print("\nNaN cells by column (symbols with the most):")
    for col in ("OpnIntrst", "ChngInOpnIntrst", "TtlTradgVol", "ClsPric", "UndrlygPric", "StrkPric", "XpryDt"):
        if col not in bhav:
            continue
        sub = bhav[bhav[col].isna()]
        if col == "StrkPric":
            sub = sub[sub["FinInstrmTp"].isin(["STO", "IDO"])]      # futures legitimately have no strike
        if len(sub):
            top = sub.groupby("TckrSymb").size().sort_values(ascending=False).head(8)
            print(f"  {col:16s} {len(sub):6d}  " + ", ".join(f"{s} ({n})" for s, n in top.items()))
        else:
            print(f"  {col:16s}      0")

    # 2. futures OI per stock
    fo = fo_metrics(bhav)
    no_oi = fo[fo["oi_change_pct"].isna()]["symbol"].tolist()
    no_pcr = fo[fo["pcr"].isna()]["symbol"].tolist()
    print(f"\nfutures OI: {len(fo)} stocks; OI change undefined for {len(no_oi)}: {no_oi or '-'}")
    print(f"PCR undefined (no call OI) for {len(no_pcr)}: {no_pcr or '-'}")

    # 3. option chains: one-sided strikes and per-stock failures
    closes = {s: float(v) for s, v in bhav[bhav["FinInstrmTp"] == "STO"].groupby("TckrSymb")["UndrlygPric"].median().dropna().items()}
    chains, problems = option_chains(bhav, closes)
    one_sided = {s: c["one_sided_strikes"] for s, c in chains.items() if c.get("one_sided_strikes")}
    print(f"\noption chains built for {len(chains)} stocks; failed for {len(problems)}")
    for sym, why in sorted(problems.items()):
        print(f"  FAILED {sym}: {why}")
    if one_sided:
        print(f"one-sided strikes in the nearest expiry ({len(one_sided)} stocks; these would have crashed the old build):")
        for sym, n in sorted(one_sided.items(), key=lambda kv: -kv[1]):
            print(f"  {sym}: {n}")
    else:
        print("no one-sided strikes in any nearest-expiry chain")


if __name__ == "__main__":
    main()
