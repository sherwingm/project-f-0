"""Coverage summary of the index store for the /index page: dataset x underlying x resolution x date range.

    INDEX_STORE=... python -m index_data.coverage        # -> SMALL/coverage.json (committed to main)
"""
from __future__ import annotations

import pandas as pd

from .common import SMALL, STORE, today_ist, write_json


def scan(store=STORE) -> list[dict]:
    rows = []
    base = store / "options_1m"
    for under in sorted(p.name for p in base.glob("*") if p.is_dir()):
        files = sorted(base.glob(f"{under}/*/*.parquet"))
        if not files:
            continue
        srcs: dict[str, list[str]] = {}
        for f in files:
            try:
                s = pd.read_parquet(f, columns=["source"])["source"].unique()
            except Exception:  # noqa: BLE001 - an old file without the column
                s = ["kotak"]
            for x in s:
                srcs.setdefault(x, []).append(f.stem)
        for src, days in srcs.items():
            rows.append({"dataset": "options 1-minute", "underlying": under, "resolution": "1 min", "source": src,
                         "first": min(days), "last": max(days), "files": len(days),
                         "expiries": len({f.parent.name for f in files})})
    for under_dir in sorted((store / "options_daily").glob("*")):
        files = sorted(under_dir.glob("*.parquet"))
        if files:
            d = pd.concat([pd.read_parquet(f, columns=["TradDt"]) for f in (files[0], files[-1])])
            rows.append({"dataset": "options daily OHLC", "underlying": under_dir.name, "resolution": "1 day",
                         "source": "nse_bhavcopy", "first": d["TradDt"].min(), "last": d["TradDt"].max(),
                         "files": len(files)})
    for name_dir in sorted((store / "spot_1m").glob("*")):
        files = sorted(name_dir.glob("*.parquet"))
        if files:
            rows.append({"dataset": "spot 1-minute", "underlying": name_dir.name, "resolution": "1 min",
                         "source": "kotak", "first": files[0].stem, "last": files[-1].stem, "files": len(files)})
    if (store / "vix_daily.parquet").exists():
        v = pd.read_parquet(store / "vix_daily.parquet", columns=["date"])
        rows.append({"dataset": "India VIX daily", "underlying": "INDIAVIX", "resolution": "1 day", "source": "yfinance",
                     "first": v["date"].min(), "last": v["date"].max(), "files": 1})
    snaps = sorted((store / "instruments").glob("*.parquet"))
    if snaps:
        rows.append({"dataset": "contract list snapshots", "underlying": "all", "resolution": "daily", "source": "kotak",
                     "first": snaps[0].stem, "last": snaps[-1].stem, "files": len(snaps)})
    chains = sorted((store / "chain_eod").glob("*.parquet"))
    if chains:
        rows.append({"dataset": "EOD chain snapshot", "underlying": "NIFTY/SENSEX/BANKNIFTY", "resolution": "daily",
                     "source": "kotak", "first": chains[0].stem, "last": chains[-1].stem, "files": len(chains)})
    return rows


def main() -> None:
    write_json(SMALL / "coverage.json", {"as_of": today_ist().isoformat(), "rows": scan()})
    print(len(scan()), "coverage rows")


if __name__ == "__main__":
    main()
