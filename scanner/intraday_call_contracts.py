"""Candidate contracts for strategies/S1_intraday_strong_call_overnight.md (strong market-hours results, Oct 2024+).

    EVENTS_DB=... python -m scanner.intraday_call_contracts

For each strong case: the expiry (current monthly with >= 2 sessions left after the day, else the next), the spot at
t0 + 1 (the stock's minute close), and the call strikes from one below the nearest to 8 above. Writes
data/results/S1_v10_bandintra_contracts.csv (symbol, day0, expiry, side, strike, from, to, t0, spot) for
index_data.fetch_band_minutes intra.
"""
from __future__ import annotations

from collections import Counter

import pandas as pd

from server import sessions

from .build import ROOT
from .events.store import Store
from .option_engine import monthly
from .results_intraday import at, hm

CACHE, RES = ROOT / "data" / "cache", ROOT / "data" / "results"
START, END, MIN_LEFT, UP = "2024-10-01", "2026-09-25", 2, 8


def choose_expiry(expiries, day: str) -> str | None:
    from datetime import date
    for e in monthly(sorted(set(expiries))):
        if e >= day and sessions.sessions_to_expiry(date.fromisoformat(day), date.fromisoformat(e)) >= MIN_LEFT:
            return e
    return None


def main() -> None:
    cases = pd.read_csv(RES / "S1_intraday_results_path_cases.csv")
    cases = cases[(cases["class"] == "strong") & (cases["day"] >= START) & (cases["day"] <= END)]
    mins = pd.read_csv(RES / "S1_intraday_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    stock = {k: g.set_index("t")["c"] for k, g in mins.groupby(["symbol", "day"])}
    days = sorted(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}" for p in CACHE.glob("fo_bhavcopy_*.csv"))
    with Store() as st:
        ban = {(e["symbol"], e["event_date"]) for e in st.all_of_type("ban") if e.get("subtype") == "in"}
    fun, rows = Counter(), []
    for r in cases.itertuples():
        fun["strong_cases"] += 1
        if (r.symbol, r.day) in ban:
            fun["in_ban"] += 1
            continue
        nxt = next((d for d in days if d > r.day), None)
        b = pd.read_csv(CACHE / f"fo_bhavcopy_{r.day.replace('-', '')}.csv",
                        usecols=["TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp"])
        ch = b[(b["TckrSymb"] == r.symbol) & (b["FinInstrmTp"] == "STO") & (b["OptnTp"] == "CE")]
        exp = choose_expiry(ch["XpryDt"].astype(str), r.day) if len(ch) else None
        spot = at(stock[(r.symbol, r.day)], hm(r.t0, 1))
        if exp is None or not nxt or not spot > 0:
            fun["no_expiry_or_spot"] += 1
            continue
        ks = sorted(ch.loc[ch["XpryDt"].astype(str) == exp, "StrkPric"].astype(float).unique())
        k0 = min(ks, key=lambda k: (abs(k - spot), k))
        i = ks.index(k0)
        for k in ks[max(0, i - 1): i + UP]:
            rows.append({"symbol": r.symbol, "day0": r.day, "expiry": exp, "side": "CE", "strike": k, "from": r.day,
                         "to": nxt, "t0": r.t0, "spot": round(spot, 2)})
        fun["cases_listed"] += 1
    out = pd.DataFrame(rows)
    out.to_csv(RES / "S1_v10_bandintra_contracts.csv", index=False)
    print(dict(fun), "contracts", len(out))


if __name__ == "__main__":
    main()
