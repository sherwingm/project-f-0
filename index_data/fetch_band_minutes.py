"""Day-0 1-minute candles of the S1 v10 Rs 0.50-1 band contracts (strategies/S1_v10_band050_trail.md), from Upstox's
expired-instruments API. Runs on GitHub (the token is a secret); the CSV is uploaded as a run artifact.

    UPSTOX_ANALYTICS_TOKEN=... python -m index_data.fetch_band_minutes [050|12]

Reads data/results/S1_v10_band<band>_contracts.csv; writes data/results/S1_v10_band<band>_minutes.csv (symbol, day0,
side, strike, ts, o, h, l, c, volume, oi) and prints what was missing. Band 050 by default; 12 = the Rs 1-2 study.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import sys
from collections import Counter
from pathlib import Path

import requests

from .upstox_common import Upstox

ROOT = Path(__file__).resolve().parents[1]
BAND = sys.argv[1] if len(sys.argv) > 1 else "050"
SRC, OUT = ROOT / f"data/results/S1_v10_band{BAND}_contracts.csv", ROOT / f"data/results/S1_v10_band{BAND}_minutes.csv"
INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"


def isins() -> dict[str, str]:
    raw = requests.get(INSTRUMENTS_URL, timeout=120).content
    rows = json.load(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(raw)), encoding="utf-8"))
    return {r["trading_symbol"]: r["isin"] for r in rows
            if r.get("segment") == "NSE_EQ" and r.get("instrument_type") == "EQ" and r.get("isin")}


def main() -> None:
    u, isin, fun = Upstox(), isins(), Counter()
    contracts: dict[tuple, list] = {}
    with SRC.open() as f, OUT.open("w", newline="") as g:
        w = csv.writer(g)
        w.writerow(["symbol", "day0", "side", "strike", "ts", "o", "h", "l", "c", "volume", "oi"])
        for r in csv.DictReader(f):
            fun["contracts"] += 1
            sym, exp, side, k = r["symbol"], r["expiry"], r["side"], float(r["strike"])
            if sym not in isin:
                fun["no_isin"] += 1
                print("no ISIN:", sym)
                continue
            key = (sym, exp)
            if key not in contracts:
                try:
                    contracts[key] = (u.get("/v2/expired-instruments/option/contract",
                                            {"instrument_key": f"NSE_EQ|{isin[sym]}", "expiry_date": exp}).get("data")) or []
                except Exception as exc:                         # noqa: BLE001 - counted and reported
                    print("contracts error:", sym, exp, str(exc)[:200])
                    contracts[key] = []
            c = next((c for c in contracts[key] if c.get("instrument_type") == side
                      and abs(float(c.get("strike_price") or 0) - k) < 1e-6), None)
            if c is None:
                fun["no_contract"] += 1
                print("no contract:", sym, exp, side, k, f"({len(contracts[key])} listed)")
                continue
            try:
                body = u.get(f"/v2/expired-instruments/historical-candle/{u.q(c['instrument_key'])}/1minute/"
                             f"{r['day0']}/{r['day0']}")
            except Exception as exc:                             # noqa: BLE001
                fun["candle_error"] += 1
                print("candles error:", c.get("trading_symbol"), str(exc)[:200])
                continue
            rows = (body.get("data") or {}).get("candles") or []
            if not rows:
                fun["no_candles"] += 1
                print("no candles:", c.get("trading_symbol"), r["day0"])
                continue
            fun["fetched"] += 1
            for x in rows:
                w.writerow([sym, r["day0"], side, k, x[0], *x[1:7]])
    print(dict(fun), "calls:", u.calls)


if __name__ == "__main__":
    main()
