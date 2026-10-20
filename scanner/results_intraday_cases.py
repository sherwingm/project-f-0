"""Case list for strategies/S1_intraday_results_reaction.md: results filed 09:15-14:50 IST on a session day, F&O stocks.

    EVENTS_DB=... python -m scanner.results_intraday_cases

One row per stock and day (the earliest filing time, NSE or BSE). F&O = the stock has option contracts in that day's
F&O bhavcopy (data/cache/fo_bhavcopy_YYYYMMDD.csv). Writes data/results/S1_intraday_cases.csv (symbol, day, t0).
"""
from __future__ import annotations

from collections import Counter

import pandas as pd

from .build import ROOT
from .events.store import Store

CACHE, RES = ROOT / "data" / "cache", ROOT / "data" / "results"
START, END, FIRST, LAST = "2022-01-01", "2026-09-25", "09:15", "14:50"


def main() -> None:
    sessions = {f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}": p for p in CACHE.glob("fo_bhavcopy_*.csv")}
    with Store() as st:
        ev = [(e["symbol"], e["event_date"], (e.get("event_time") or "")[:5]) for e in st.all_of_type("results")]
    fun, best = Counter(), {}
    for sym, d, t in ev:
        if not (START <= d <= END) or not t:
            continue
        fun["results_with_time"] += 1
        if not (FIRST <= t <= LAST):
            continue
        fun["in_09:15-14:50"] += 1
        if d not in sessions:
            fun["not_a_session_or_no_bhavcopy"] += 1
            continue
        k = (sym, d)
        best[k] = min(best.get(k, t), t)
    fo: dict[str, set[str]] = {}
    rows = []
    for (sym, d), t in sorted(best.items(), key=lambda x: (x[0][1], x[0][0])):
        if d not in fo:
            b = pd.read_csv(sessions[d], usecols=["TckrSymb", "FinInstrmTp"])
            fo[d] = set(b.loc[b["FinInstrmTp"] == "STO", "TckrSymb"])
        if sym not in fo[d]:
            fun["not_fo_that_day"] += 1
            continue
        rows.append({"symbol": sym, "day": d, "t0": t})
    out = pd.DataFrame(rows)
    out.to_csv(RES / "S1_intraday_cases.csv", index=False)
    print(dict(fun), "cases", len(out))
    print(out.groupby(out["day"].str[:4]).size().to_dict())


if __name__ == "__main__":
    main()
