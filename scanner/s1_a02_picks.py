"""HYP-A-02 picks: the S1 arm A / arm B calls the live expiry rule (>= 2 sessions) would take for the signals of the minute test (numbers = picks only).

    python -m scanner.s1_a02_picks

strategies/S1_armab_gemini_hypotheses.md. Daily files choose the signal and the strike only (the v7 / v8 engines with the near-expiry switch on, the near minimum
changed from 3 to 2 sessions, and the normal price band and contract minimum used for every expiry). Writes the contract list for the Upstox minute fetch
(data/results/S1_v10_bandd2_contracts.csv) for the picks whose expiry differs from the baseline's. No outcome is read here.
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

RES = ROOT / "data" / "results"


def main() -> None:
    from .nse_fo import BhavcopyUnavailable, download_fo_prices
    v7.NEAR_MIN_SESSIONS = 2                    # the live rule: the current monthly down to 2 sessions left
    v7.NEAR_BAND = v7.NORMAL_BAND               # the live band for every expiry
    cache, eod2 = ROOT / "data" / "cache", ROOT / "data" / "eod2"
    t_start, t_end = window()
    universe = option_universe(cache, t_start, "9999-12-31")
    inp = load_inputs(eod2, cache, set().union(*universe.values()))
    m = Market(inp)

    def prices(d: str):
        try:
            return download_fo_prices(date.fromisoformat(d), cache)
        except (BhavcopyUnavailable, OSError, ValueError):
            return None

    days = v4.Days(cache, prices)
    last_t = max(i for i, d in enumerate(m.cal) if d <= t_end)
    sigs_t = [s for s in v4.signals(m, inp.results, universe, t_start, last_t, Counter()) if m.cal[s.i0] >= "2024-09-15"]
    sigs_h = v8.signals_any(m, inp.results, universe, "2025-04-01", len(m.cal) - 1, Counter())
    rules = v7.Variant("d2", near_contracts=50, near_expiry=True)
    frames = []
    for arm in ("A", "B"):
        t = v7.simulate(m, sigs_t, arm, rules, days, inp.ban, universe, inp.category, Counter(), t_end)
        if not t.empty:
            frames.append(t.assign(arm=arm, src="2024"))
        chosen = [s for s, k in sigs_h if v8.in_arm(arm, k, v4.strong_sector(s.state))]
        t = v7.simulate(m, chosen, "A", rules, days, inp.ban, universe, inp.category, Counter(), m.cal[-1])
        if not t.empty:
            frames.append(t.assign(arm=arm, src="2025+"))
    d2 = pd.concat(frames, ignore_index=True)
    base = pd.read_csv(RES / "S1_armb_hold_and_nifty_trades.csv")
    base = base[(base.variant == "LIVE") & base.arm.isin(["A", "B"]) & base.excluded.isna() & (base.expiry >= "2024-10-01")].drop_duplicates(["arm", "symbol", "entry_date"])
    mm = d2.merge(base[["arm", "symbol", "entry_date", "expiry", "strike"]], on=["arm", "symbol", "entry_date"], how="left", suffixes=("", "_base"))
    mm["differs"] = mm["expiry_base"].isna() | (mm["expiry"] != mm["expiry_base"])
    near = mm[mm["differs"] & (mm["expiry"] >= "2024-10-01")]
    print("D2 picks:", {a: int((d2.arm == a).sum()) for a in ("A", "B")}, "| same expiry as the baseline:", int((~mm.differs).sum()),
          "| differ (near-expiry current monthly):", {a: int((near.arm == a).sum()) for a in ("A", "B")},
          "| of which the baseline had no trade for that signal:", int(near["expiry_base"].isna().sum()))
    near.to_csv(RES / "S1_a02_picks.csv", index=False)
    k = near.drop_duplicates(["symbol", "signal_date", "strike", "expiry"])
    pd.DataFrame({"symbol": k.symbol, "day0": k.signal_date, "side": "CE", "expiry": k.expiry, "strike": k.strike, "from": k.entry_date, "to": k.expiry}) \
        .to_csv(RES / "S1_v10_bandd2_contracts.csv", index=False)
    print("contracts to fetch:", len(k))


if __name__ == "__main__":
    main()
