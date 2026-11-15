"""Bid-ask spread of the stock options the live recorder follows, by time of day (numbers only, descriptive; not a strategy test).

    python -m scanner.spread_by_time

Reads data/candles_1s/*.jsonl (1-second rows with the ask `a` and the bid close `bc`, recorded live from 26 Oct 2026). Spread = (ask - bid) / ask in %, only rows with an ask of at
least Rs 2. Per contract and day the median spread inside each time window (at least 3 rows), then the median, mean, share above 10 % and 90th percentile across contract-days.
Writes data/results/S1_spread_by_time.md. Question behind it: the project's live call arms pay a wider spread at the 09:15 open than at the 15:20 close entry; is that a property of the
opening minutes in general on this data?
"""
from __future__ import annotations

import collections
import glob
import json
import statistics as st

from .build import ROOT

BUCKETS = [("09:15:00", "09:16:00", "09:15 (first minute)"), ("09:16:00", "09:21:00", "09:16-09:20"), ("09:21:00", "10:00:00", "09:21-10:00"),
           ("10:00:00", "14:00:00", "10:00-14:00"), ("14:00:00", "15:15:00", "14:00-15:15"), ("15:15:00", "15:25:00", "15:15-15:25 (close entry at 15:20)"),
           ("15:25:00", "15:31:00", "15:25-15:30")]


def main() -> None:
    per = {b[2]: collections.defaultdict(list) for b in BUCKETS}
    days, n_rows = set(), 0
    for f in sorted(glob.glob(str(ROOT / "data" / "candles_1s" / "*.jsonl"))):
        day = f[-16:-6]
        days.add(day)
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            a, b = r.get("a"), r.get("bc")
            if not a or not b or a < 2:
                continue
            for lo, hi, lab in BUCKETS:
                if lo <= r["t"] < hi:
                    per[lab][(day, r["ts"])].append((a - b) / a * 100)
                    n_rows += 1
                    break
    lines = [f"# Spread of stock options by time of day (live 1-second recorder, {min(days)} to {max(days)})\n",
             "Numbers only, descriptive. Spread = (ask - bid) / ask, rows with an ask of at least Rs 2; per contract and day the median in the window (at least 3 rows), then across contract-days. "
             f"{n_rows:,} rows. Only contracts the recorder follows, only moments with a quote; a few days in a rising market.\n",
             "| window | contract-days | median % | mean % | share above 10 % | 90th percentile % |", "|---|---|---|---|---|---|"]
    for _, _, lab in BUCKETS:
        m = sorted(st.median(v) for v in per[lab].values() if len(v) >= 3)
        if m:
            lines.append(f"| {lab} | {len(m)} | {st.median(m):.1f} | {st.mean(m):.1f} | {100 * sum(x > 10 for x in m) / len(m):.0f} % | {m[int(0.9 * (len(m) - 1))]:.1f} |")
    out = "\n".join(lines) + "\n"
    (ROOT / "data" / "results" / "S1_spread_by_time.md").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
