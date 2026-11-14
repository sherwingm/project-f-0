"""S1 arms A / B: the contracts picked for signals from 2026-09-26 (the extension window), numbers = picks only.

    python -m scanner.s1_extension_picks

strategies/S1_extension_oct2026.md. Uses the daily files only to choose the signal and the strike (the v7 / v8 `old_expiry` rules); writes the contract
list for the Upstox minute fetch (data/results/S1_v10_bandext_contracts.csv, columns symbol, day0, side, expiry, strike, from, to) and the picks with lot / category
(data/results/S1_extension_picks.csv). No outcome is read here.
"""
from __future__ import annotations

from collections import Counter
from datetime import date

import pandas as pd

from . import backtest_s1_v4 as v4
from . import backtest_s1_v7 as v7
from . import backtest_s1_v8 as v8
from .backtest_s1_v2 import Market, load_inputs, option_universe
from .build import ROOT
from .option_engine import window

START = "2026-09-26"


def main() -> None:
    from .nse_fo import BhavcopyUnavailable, download_fo_prices
    cache, eod2 = ROOT / "data" / "cache", ROOT / "data" / "eod2"
    t_start, _ = window()
    universe = option_universe(cache, t_start, "9999-12-31")
    inp = load_inputs(eod2, cache, set().union(*universe.values()))
    m = Market(inp)

    def prices(d: str):
        try:
            return download_fo_prices(date.fromisoformat(d), cache)
        except (BhavcopyUnavailable, OSError, ValueError):
            return None

    days = v4.Days(cache, prices)
    last = len(m.cal) - 1
    sigs = v8.signals_any(m, inp.results, universe, START, last, Counter())
    rules = v7.Variant("old_expiry", near_expiry=False)
    frames = []
    for arm in ("B", "A"):
        chosen = [s for s, k in sigs if v8.in_arm(arm, k, v4.strong_sector(s.state))]
        t = v7.simulate(m, chosen, "A", rules, days, inp.ban, universe, inp.category, Counter(), m.cal[-1])
        if not t.empty:
            frames.append(t.assign(arm=arm))
    tr = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    print("signals", len(sigs), "| arm trades picked:", {a: int((tr.arm == a).sum()) for a in ("A", "B")} if len(tr) else 0,
          "| first / last signal:", tr.signal_date.min() if len(tr) else None, tr.signal_date.max() if len(tr) else None,
          "| last session with data", m.cal[-1])
    if tr.empty:
        return
    tr.to_csv(ROOT / "data" / "results" / "S1_extension_picks.csv", index=False)
    k = tr.drop_duplicates(["symbol", "signal_date", "strike", "expiry"])
    out = pd.DataFrame({"symbol": k.symbol, "day0": k.signal_date, "side": "CE", "expiry": k.expiry, "strike": k.strike,
                        "from": k.entry_date, "to": k.expiry})
    out.to_csv(ROOT / "data" / "results" / "S1_v10_bandext_contracts.csv", index=False)
    print("contracts to fetch:", len(out))


if __name__ == "__main__":
    main()
