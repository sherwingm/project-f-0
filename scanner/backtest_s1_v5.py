"""S1 v5 · results-beat continuation, long calls, 1 lot inside the Rs 10,000-30,000 band, as
strategies/S1_v5_results_beat.md pre-registers it (numbers only).

    python -m scanner.backtest_s1_v5          # test window 2021-2024 only

The signal, entry, exits and costs are S1 v4's (scanner/backtest_s1_v4.py); only the sizing differs.
"""
from __future__ import annotations

import argparse
import logging
import math
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

from . import backtest_s1_v4 as v4
from .backtest_s1_v2 import BIAS, CAPITAL, Market, load_inputs, md, option_universe
from .build import ROOT
from .option_engine import split_statement, window

log = logging.getLogger("backtest_s1_v5")
BAND = (10000.0, 30000.0)                          # premium of the one lot at the entry fill (DECISIONS.md)
SENSITIVITY = (0.01, 0.02, 0.03)
FILTERS = tuple(f for f in v4.FILTERS if f != "budget_below_one_lot") + ("premium_below_band", "premium_above_band")


def band_sizer(entry: float, lot: int, own_vol: float, median_vol: float) -> tuple[int, float | None, str | None]:
    """1 lot when fill x lot is within Rs 10,000-30,000."""
    if lot <= 0:
        return 0, None, "premium_below_band"
    cost = entry * lot
    if cost < BAND[0]:
        return 0, None, "premium_below_band"
    if cost > BAND[1]:
        return 0, None, "premium_above_band"
    return 1, None, None


def with_flat_slippage(t: pd.DataFrame, rate: float) -> pd.DataFrame:
    """net and net % recomputed with a flat slippage rate per side (charges unchanged)."""
    t = t.copy()
    ok = t["excluded"].fillna("") == ""
    e, x, q = t["entry_price"].astype(float), t["exit_price"].astype(float), t["qty"].astype(float)
    t.loc[ok, "slippage"] = (rate * q * (e + x)).round(2)[ok]
    t.loc[ok, "net"] = ((x - e) * q - t["charges"].astype(float) - t["slippage"].astype(float)).round(2)[ok]
    t.loc[ok, "net_pct"] = (t["net"].astype(float) / t["premium_rs"].astype(float) * 100).round(3)[ok]
    return t


def breakdown(trades: pd.DataFrame, col: str, groups) -> pd.DataFrame:
    out = []
    for arm in v4.ARMS:
        for v in v4.VARIANTS:
            g0 = trades[(trades["arm"] == arm) & (trades["variant"] == v)] if not trades.empty else trades
            for grp in groups:
                g = g0[g0[col] == grp] if not g0.empty else g0
                for name, gp in v4.periods(g, "entry_date"):
                    out.append({"arm": arm, "exit_after": v, col: grp, "period": name, **v4.metrics(gp)})
    return pd.DataFrame(out)


def equity_curve(t: pd.DataFrame) -> tuple[pd.DataFrame, float, float]:
    t = t[t["excluded"].fillna("") == ""].copy()
    if t.empty:
        return pd.DataFrame(columns=["month", "trades", "net_rs", "cumulative_rs", "drawdown_rs"]), 0.0, 0.0
    t["month"] = t["exit_date"].str[:7]
    g = t.groupby("month").agg(trades=("net", "size"), net_rs=("net", "sum")).reset_index()
    g["cumulative_rs"] = g["net_rs"].cumsum()
    g["drawdown_rs"] = g["cumulative_rs"] - g["cumulative_rs"].cummax().clip(lower=0.0)
    cum = t.sort_values(["exit_date", "entry_date"])["net"].astype(float).cumsum()
    dd = float((cum - cum.cummax().clip(lower=0.0)).min())
    return g.round(2), round(dd, 2), round(dd / CAPITAL * 100, 3)


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v5 results-beat long calls, Rs 10,000-30,000 band (numbers only)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from .nse_fo import BhavcopyUnavailable, download_fo_prices

    start, end = window()                                       # test window only; the holdout is untouched
    universe = option_universe(a.cache_dir, start, end)
    inp = load_inputs(a.eod2_dir, a.cache_dir, set().union(*universe.values()))
    m = Market(inp)
    last_i = max(i for i, d in enumerate(m.cal) if d <= end)

    def prices(d: str):
        try:
            return download_fo_prices(date.fromisoformat(d), a.cache_dir)
        except (BhavcopyUnavailable, OSError, ValueError) as exc:
            log.warning("prices %s: %s", d, exc)
            return None

    base = Counter()
    sigs = v4.signals(m, inp.results, universe, start, last_i, base)
    days = v4.Days(a.cache_dir, prices)
    frames, funnels = [], {}
    for arm in v4.ARMS:
        for v in v4.VARIANTS:
            f = Counter(base)
            frames.append(v4.simulate(m, sigs, arm, v, days, inp.ban, universe, inp.category, f, sizer=band_sizer))
            funnels[(arm, v)] = f
    trades = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(a.out_dir / "S1_v5_trades.csv", index=False)

    sessions = [d for d in m.cal if start <= d <= end]
    sec = {}
    sec["1"] = "\n".join([
        "## 1. Header", "",
        f"- {split_statement((sessions[0], sessions[-1]))} Signals whose day +1 + {v4.MAX_HOLD} sessions falls after "
        f"{end} are not taken, so no trade reads a holdout price.",
        f"- Sessions cached: {sum(d in universe for d in sessions)} of {len(sessions)}.", f"- {BIAS}",
        "- Definition: strategies/S1_v5_results_beat.md (pre-registered). Long calls only; 1 lot when its premium at "
        f"the entry fill is Rs {BAND[0]:,.0f}-{BAND[1]:,.0f}.", ""])
    sec["2"] = ("## 2. Diagnostic: the signals as a 1-lot stock future (not a trade), bought at the day +1 close, "
                f"net of {v4.FUT_COST_PCT:g} % round trip, % of notional\n\n" +
                md(v4.summarise_futures(v4.futures_diagnostic(m, sigs, inp.ban))))
    funnel = pd.DataFrame([{"arm": k[0], "exit_after": k[1], "results_signals": f["results_signals"],
                            "no_options_or_prices_on_day0": f["no_options_or_prices_on_day0"],
                            **{x: f[x] for x in FILTERS}, "traded": f["traded"],
                            "excluded_corporate_action": int(((trades["arm"] == k[0]) & (trades["variant"] == k[1])
                                                              & (trades["excluded"].fillna("") != "")).sum())}
                           for k, f in funnels.items()])
    sec["3"] = ("## 3. Main tables: naked long call, net of charges and slippage by AMFI category\n\n" +
                md(v4.summarise(trades)) + "\nSignals removed by each filter, in order:\n\n" + md(funnel))
    sec["4"] = ("## 4. Breakdowns\n\nBy AMFI category:\n\n" + md(breakdown(trades, "category", ("large", "mid", "small", "unknown"))) +
                "\nBy 20-day volatility tercile (within day 0's universe):\n\n" + md(breakdown(trades, "vol_tercile", ("low", "mid", "high"))))
    sens = []
    for r in SENSITIVITY:
        s = v4.summarise(with_flat_slippage(trades, r))
        sens.append(s.assign(slippage=f"flat {r:.0%}"))
    sec["5"] = "## 5. Sensitivity (flat slippage per side)\n\n" + md(pd.concat(sens, ignore_index=True))
    curve, dd, dd_pct = equity_curve(trades[(trades["arm"] == "A") & (trades["variant"] == 20)])
    sec["6"] = ("## 6. Equity curve (arm A, 20-session exits, by exit month)\n\n" + md(curve) +
                f"\nMaximum drawdown: Rs {dd:,.2f} ({dd_pct:g} % of Rs {CAPITAL:,.0f} paper capital).\n")
    sec["7"] = "## 7. Gate (DECISIONS.md, test window, 20-session exits)\n\n" + "\n".join(
        f"### Arm {arm}\n\n" + md(pd.DataFrame(v4.gate(trades, arm))) for arm in v4.ARMS)
    (a.out_dir / "S1_v5_backtest_report.md").write_text(
        "# S1 v5 backtest report\n\nNumbers only.\n\n" + "\n".join(sec[k] for k in "1234567"), encoding="utf-8")
    print("\n".join(sec[k] for k in "237"))


if __name__ == "__main__":
    main()
