"""Results events: coverage by year and the day-0 move, plus the post-results drift after a beat (numbers only).

    python -m scanner.results_coverage

Day 0 = the first full session after the filing time (S1 v2 rule). Abnormal = stock minus the leave-one-out
equal-weight sector (data/sector_map.csv), or minus NIFTY 500 for a stock without a sector. No sector filter
in the coverage table.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest_s1_v2 import (Market, _ret, abnormal_pct, compound, day0_index, load_inputs, md, sector_state,
                             sector_weak)
from .build import ROOT
from .option_engine import TEST_PERIODS, TEST_WINDOW
from .stats import clustered_t

HORIZONS = (5, 20)


def benchmark_returns(m: Market, sym: str) -> tuple[np.ndarray, str]:
    """Daily benchmark returns for the stock: its leave-one-out sector, else NIFTY 500."""
    lr = m.loo(sym)
    if lr is not None:
        return lr, "sector"
    b = m.bench
    r = np.full(len(b), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        r[1:] = b[1:] / b[:-1] - 1
    return r, "nifty500"


def day0_table(m: Market, results: list[tuple[str, str, str | None]]) -> pd.DataFrame:
    """One row per stored results event: symbol, event date, day 0, benchmark, day-0 abnormal %."""
    rows = []
    for sym, d, t in results:
        i = day0_index(m.cal, d, t)
        ab, kind = math.nan, None
        if i is not None and sym in m.close:
            br, kind = benchmark_returns(m, sym)
            if i >= 1:
                ab = (_ret(m.close[sym], i, 1) - br[i]) * 100
        rows.append({"symbol": sym, "event_date": d, "day0": m.cal[i] if i is not None else None,
                     "day0_i": i, "benchmark": kind, "abnormal_pct": ab})
    return pd.DataFrame(rows)


def coverage(t: pd.DataFrame) -> pd.DataFrame:
    t = t.assign(year=t["event_date"].str[:4])
    out = []
    for y, g in t.groupby("year"):
        a = g["abnormal_pct"]
        out.append({"year": y, "results_events": len(g), "with_day0_move": int(a.notna().sum()),
                    "vs_sector": int((g["benchmark"] == "sector").sum()), "vs_nifty500": int((g["benchmark"] == "nifty500").sum()),
                    "day0_le_-2pct": int((a <= -2).sum()), "day0_ge_+2pct": int((a >= 2).sum())})
    return pd.DataFrame(out)


def beat_drift(m: Market, t: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Day-0 abnormal >= +2 % in [start, end] (one per stock and day 0): h-session return net of the benchmark,
    with the strong-sector flag (leave-one-out 21- and 63-session relative > 0, level above its 50-session average)."""
    g = t[(t["abnormal_pct"] >= 2) & t["day0"].between(start, end)].drop_duplicates(["symbol", "day0"])
    rows = []
    for r in g.itertuples(index=False):
        i, sym = int(r.day0_i), r.symbol
        br, kind = benchmark_returns(m, sym)
        st = m.state(sym, i) if kind == "sector" else None
        strong = st is not None and st[0] > 0 and st[1] > 0 and not st[2]
        row = {"day0": r.day0, "symbol": sym, "benchmark": kind, "strong_sector": strong}
        for h in HORIZONS:
            row[f"ex{h}"] = ((_ret(m.close[sym], i + h, h) - compound(br, i + h, h)) * 100
                             if i + h < len(m.cal) else math.nan)
        rows.append(row)
    return pd.DataFrame(rows)


def drift_summary(d: pd.DataFrame) -> pd.DataFrame:
    out = []
    for subset, g0 in (("(a) all", d), ("(b) strong sector", d[d["strong_sector"]])):
        for name, a, b in (("2021-24", *TEST_WINDOW),) + TEST_PERIODS:
            g = g0[g0["day0"].between(a, b)]
            for h in HORIZONS:
                x = g[[f"ex{h}", "day0"]].dropna()
                v = x[f"ex{h}"]
                out.append({"subset": subset, "period": name, "horizon": h, "n": len(v),
                            "mean_pct": round(v.mean(), 3) if len(v) else None,
                            "median_pct": round(v.median(), 3) if len(v) else None,
                            "share_positive_pct": round((v > 0).mean() * 100, 2) if len(v) else None,
                            "t_clustered": clustered_t(v, x["day0"]) if len(v) > 1 else None})
    return pd.DataFrame(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="results coverage and post-beat drift (numbers only)")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    a = ap.parse_args()
    from .events.store import Store
    with Store() as st:
        syms = {e["symbol"] for e in st.all_of_type("results")}
    inp = load_inputs(a.eod2_dir, a.cache_dir, syms)
    m = Market(inp)
    t = day0_table(m, inp.results)
    print("Results events by year (event date), day-0 abnormal move, no sector filter:\n")
    print(md(coverage(t)))
    print(f"Post-results drift after a day-0 abnormal move >= +2 %, test window {TEST_WINDOW[0]} to {TEST_WINDOW[1]} "
          "(return close day 0 -> close day 0 + h, net of the benchmark):\n")
    print(md(drift_summary(beat_drift(m, t, *TEST_WINDOW))))


if __name__ == "__main__":
    main()
