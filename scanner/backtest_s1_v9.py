"""S1 v9 option backtest (numbers only): calls bought on the results day itself when the reported numbers are strong.

    python -m scanner.backtest_s1_v9

strategies/S1_v9_and_event_screens.md (addendum). Day 0 = the first full session after the filing; the expiry,
strike and spot come from the previous session's bhavcopy; entry on day 0 at the option's open + 1 tick ("open") or
its premium VWAP + 1 tick ("day"). Methods: v7 (walk Rs 600-8,000, stop / decay / T-1), v4 (at-the-money, vol
budget, 20 sessions), v5 (at-the-money, Rs 10,000-30,000, 20 sessions). Each method x entry runs once over the widest
cell (NP YoY > 10 %); every trade carries its cell and arm flags.
"""
from __future__ import annotations

import argparse
import logging
import math
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest_s1_v4 as v4
from . import backtest_s1_v5 as v5
from . import backtest_s1_v7 as v7
from .backtest_s1_v2 import Market, day0_index, load_inputs, md, option_universe
from .build import ROOT
from .event_screens import END, START, YEARS, num_or_none, strong
from .stats import clustered_t

log = logging.getLogger("backtest_s1_v9")

V7 = v7.Variant("v7", near_expiry=False)
METHODS = ("v7", "v4", "v5")
ENTRIES = ("open", "day")
CELLS = (("NP YoY>10%", "strong10", False), ("NP YoY>10% & gap<=5%", "strong10", True),
         ("NP YoY>25%", "strong25", False), ("NP YoY>25% & gap<=5%", "strong25", True))


def open_prices(p: pd.DataFrame | None) -> pd.DataFrame | None:
    """Day 0's option prices with the open in place of the close and no turnover, so the engines' fill (VWAP, else
    the close, + 1 tick) becomes the open + 1 tick; the contract count stays the day's."""
    if p is None:
        return None
    return p.assign(ClsPric=p["OpnPric"], TtlTrfVal=np.nan)


def signals(m: Market, results, fin: dict, universe: dict, last_i: int, funnel: Counter):
    """Strong-number filings (NP YoY > 10 % & QoQ > 0 & revenue YoY > 0) with day 0 in the window, one per stock and
    day 0, as v4 signals whose i0 is the session BEFORE day 0 (so the engines enter on day 0)."""
    from .peak_study import result_quality
    seen, out, info = set(), [], {}
    for sym, d, t in results:
        i = day0_index(m.cal, d, t)
        if i is None or i < 2 or not START <= m.cal[i] <= END or i + 1 + v4.MAX_HOLD > last_i or (sym, i) in seen:
            continue
        seen.add((sym, i))
        funnel["results_filings"] += 1
        if sym not in universe.get(m.cal[i - 1], set()) or sym not in m.close:
            funnel["no_options_or_prices"] += 1
            continue
        q = result_quality(fin, sym, d)
        if num_or_none(q.get("net_profit_yoy")) is None:
            funnel["numbers_unknown"] += 1
            continue
        if not strong(q, 10):
            funnel["numbers_not_strong"] += 1
            continue
        state = m.state(sym, i - 1) if m.loo(sym) is not None else None
        out.append(v4.Signal(sym, i - 1, math.nan, math.nan, state))
        info[(sym, m.cal[i])] = {"filed": d, "np_yoy": num_or_none(q.get("net_profit_yoy")),
                                 "np_qoq": num_or_none(q.get("net_profit_qoq")),
                                 "rev_yoy": num_or_none(q.get("revenue_yoy")), "strong25": strong(q, 25),
                                 "armB": v4.strong_sector(state)}
    return sorted(out, key=lambda s: (s.i0, s.symbol)), info


def summary(g: pd.DataFrame, cell: dict) -> dict:
    x = g[(g["excluded"].fillna("") == "") & g["net_pct"].notna()]
    r = x["net_pct"].astype(float)
    yrs = {y: (round(r[x["entry_date"].str[:4] == y].mean(), 1) if (x["entry_date"].str[:4] == y).any() else None)
           for y in YEARS}
    t = clustered_t(r, x["entry_date"]) if len(x) > 1 else None
    pos = sum(1 for y in YEARS if (yrs[y] or 0) > 0)
    ok = len(x) >= 50 and r.mean() > 0 and (t or 0) >= 2 and pos >= 5 and (yrs["2025"] or 0) > 0 \
        and (yrs["2026"] or 0) > 0
    return {**cell, "n": len(x), "mean_pct": round(r.mean(), 1) if len(r) else None,
            "median_pct": round(r.median(), 1) if len(r) else None,
            "hit": round((r > 0).mean() * 100, 1) if len(r) else None,
            "total_rs": round(x["net"].astype(float).sum()) if len(x) else 0,
            "avg_premium_rs": round(x["premium_rs"].astype(float).mean()) if len(x) else None,
            "t": t, **yrs, "years_pos": pos, "PASS": "PASS" if ok else ""}


def table(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method in METHODS:
        for entry in ENTRIES:
            for name, thr, gap in CELLS:
                for arm in ("A", "B"):
                    g = trades[(trades["method"] == method) & (trades["entry"] == entry)]
                    if thr == "strong25":
                        g = g[g["strong25"].fillna(False).astype(bool)]
                    if gap:
                        g = g[g["gap_pct"] <= 5]
                    if arm == "B":
                        g = g[g["armB"].fillna(False).astype(bool)]
                    rows.append(summary(g, {"method": method, "entry": entry, "cell": name, "arm": arm}))
    return pd.DataFrame(rows)


_OPENS: dict[str, pd.Series] = {}


def stock_open(eod2: Path, sym: str, d: str) -> float | None:
    """The stock's day-0 open (eod2), for the opening-gap test."""
    if sym not in _OPENS:
        from .equity import load_symbol
        try:
            f = load_symbol(sym, eod2)
            f.index = f.index.strftime("%Y-%m-%d")
            _OPENS[sym] = f["Open"][~f.index.duplicated(keep="last")]
        except Exception:  # noqa: BLE001
            _OPENS[sym] = pd.Series(dtype=float)
    v = _OPENS[sym].get(d)
    return float(v) if v is not None and v == v else None


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v9: calls on the results day on strong numbers (numbers only)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from .financials import load as load_fin
    from .nse_fo import BhavcopyUnavailable, download_fo_prices

    universe = option_universe(a.cache_dir, "2020-12-01", END)
    inp = load_inputs(a.eod2_dir, a.cache_dir, set().union(*universe.values()))
    m = Market(inp)
    last_i = max(i for i, d in enumerate(m.cal) if d <= END)

    def prices(d: str):
        try:
            return download_fo_prices(date.fromisoformat(d), a.cache_dir)
        except (BhavcopyUnavailable, OSError, ValueError) as exc:
            log.warning("prices %s: %s", d, exc)
            return None

    funnel = Counter()
    sigs, info = signals(m, inp.results, load_fin(), universe, last_i, funnel)
    log.info("signals: %d (%s)", len(sigs), dict(funnel))
    frames, funnels = [], {}
    for entry in ENTRIES:
        px = prices if entry == "day" else (lambda d: open_prices(prices(d)))
        days = v4.Days(a.cache_dir, px, size=120)
        for method in METHODS:
            f = Counter()
            if method == "v7":
                t = v7.simulate(m, sigs, "A", V7, days, inp.ban, universe, inp.category, f, END)
            elif method == "v4":
                t = v4.simulate(m, sigs, "A", v4.MAX_HOLD, days, inp.ban, universe, inp.category, f)
            else:
                t = v4.simulate(m, sigs, "A", v4.MAX_HOLD, days, inp.ban, universe, inp.category, f,
                                sizer=v5.band_sizer)
            t = t.assign(method=method, entry=entry)
            if entry == "open" and "entry_source" in t:
                t["entry_source"] = "open"
            frames.append(t)
            funnels[(method, entry)] = f
            log.info("%s / %s: %d trades", method, entry, len(t))
    trades = pd.concat(frames, ignore_index=True)
    trades = trades.drop(columns=[c for c in ("ar0_pct", "raw0_pct", "signal_date") if c in trades])
    extra = pd.DataFrame([{"symbol": k[0], "entry_date": k[1], **v} for k, v in info.items()])
    trades = trades.merge(extra, on=["symbol", "entry_date"], how="left")
    gaps = []
    for r in trades.itertuples():
        op, c = stock_open(a.eod2_dir, r.symbol, r.entry_date), m.close[r.symbol][m.pos[r.entry_date] - 1]
        gaps.append(round((op / c - 1) * 100, 3) if op and c == c and c > 0 else math.nan)
    trades["gap_pct"] = gaps
    a.out_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(a.out_dir / "S1_v9_trades.csv", index=False)
    tab = table(trades)
    tab.to_csv(a.out_dir / "S1_v9_summary.csv", index=False)
    fun = pd.DataFrame([{"method": k[0], "entry": k[1], **dict(funnel), **dict(f)} for k, f in funnels.items()])
    text = ("# S1 v9 option backtest: calls bought on the results day, strong numbers\n\nNumbers only. "
            f"Window {START} .. {END}. strategies/S1_v9_and_event_screens.md (addendum).\n\n## Groups\n\n" + md(tab) +
            "\n## Signals removed, in order\n\n" + md(fun.fillna(0)))
    (a.out_dir / "S1_v9_backtest_report.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
