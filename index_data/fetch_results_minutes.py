"""1-minute stock candles for strategies/S1_intraday_results_reaction.md, from Kotak's history (5 years back).
Runs on GitHub (the key is a secret); the CSV is uploaded as a run artifact.

    KOTAK_CONSUMER_KEY=... python -m index_data.fetch_results_minutes [from_year] [to_year]

Reads data/results/S1_intraday_cases.csv (symbol, day, t0); writes data/results/S1_intraday_minutes.csv (symbol,
day, ts, o, h, l, c, volume) for each case day and prints what was missing.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

from .common import Kotak, candles_frame
from .s1_trades_1m import tokens

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "data/results/S1_intraday_cases.csv", ROOT / "data/results/S1_intraday_minutes.csv"


def main() -> None:
    lo, hi = (sys.argv[1] if len(sys.argv) > 1 else "2022"), (sys.argv[2] if len(sys.argv) > 2 else "2026")
    k, fun = Kotak(), Counter()
    eq, _, _ = tokens(k)
    with SRC.open() as f, OUT.open("w", newline="") as g:
        w = csv.writer(g)
        w.writerow(["symbol", "day", "ts", "o", "h", "l", "c", "volume"])
        for r in csv.DictReader(f):
            if not (lo <= r["day"][:4] <= hi):
                continue
            fun["cases"] += 1
            tok = eq.get(r["symbol"])
            if not tok:
                fun["no_token"] += 1
                print("no token:", r["symbol"], r["day"])
                continue
            try:
                df = candles_frame(k.history(f"nse_cm|{tok}", "1min", r["day"], r["day"]))
            except (ValueError, RuntimeError) as exc:
                fun["error"] += 1
                print("error:", r["symbol"], r["day"], str(exc)[:120])
                continue
            if df.empty:
                fun["no_candles"] += 1
                print("no candles:", r["symbol"], r["day"])
                continue
            fun["fetched"] += 1
            for x in df.itertuples():
                w.writerow([r["symbol"], r["day"], x.timestamp.isoformat(), x.open, x.high, x.low, x.close, x.volume])
    print(dict(fun), "calls", k.calls)


if __name__ == "__main__":
    main()
