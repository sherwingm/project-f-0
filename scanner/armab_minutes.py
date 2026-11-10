"""S1 arms A / B on 1-minute option candles (numbers only).

    python -m scanner.armab_minutes

Pre-registered in strategies/S1_armab_minutes.md. Reads the contracts the daily test picked
(data/results/S1_armb_hold_and_nifty_trades.csv, LIVE variant) and their Upstox 1-minute candles
(data/results/S1_v10_bandarmab2_minutes.csv). Entry = day +1's 09:16 candle open + 1 tick. Exits as pre-registered.
"""
from __future__ import annotations

import glob
import os
from datetime import date

import numpy as np
import pandas as pd

from . import backtest_s1_v4 as v4
from . import backtest_s1_v7 as v7
from .armb_hold_and_nifty import stats
from .backtest_s1_v2 import md
from .build import ROOT
from .option_engine import TICK

RES = ROOT / "data" / "results"
VARIANTS = ("LIVE-CLOSE", "LIVE-INTRA", "H8", "H11", "S8")


def calendar() -> list[str]:
    return sorted(os.path.basename(f)[12:20] for f in glob.glob(str(ROOT / "data/cache/fo_bhavcopy_2*.csv")))


def iso(s: str) -> str:
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def run_one(days: dict, cal: list[str], entry_day: str, expiry: str, variant: str):
    """days: {date: DataFrame of that day's candles (sorted)}. Returns dict or (reason_excluded, None)."""
    ci = {d: i for i, d in enumerate(cal)}
    if entry_day not in days or expiry not in ci or entry_day not in ci:
        return "no_data", None
    first = days[entry_day]
    c0 = first[first["t"] == "09:16"]
    if c0.empty:
        return "no_0916_candle", None
    entry = round(float(c0["o"].iloc[0]) + TICK, 2)
    best, stall = entry, 0
    hi = lo = None
    for d in cal[ci[entry_day]: ci[expiry] + 1]:
        age = ci[d] - ci[entry_day]
        g = days.get(d)
        if g is None or g.empty:
            return "missing_session", None
        to_exp = ci[expiry] - ci[d]
        if d == entry_day:
            g = g[g["t"] >= "09:16"]
        for r in g.itertuples():
            hi = r.h if hi is None else max(hi, r.h)
            lo = r.l if lo is None else min(lo, r.l)
            if variant == "LIVE-INTRA" and r.t >= ("09:17" if d == entry_day else "09:15") and r.l <= v7.STOP * entry:
                px = max(0.0, round(min(v7.STOP * entry, r.o) - TICK, 2))
                return dict(entry=entry, exit_price=px, exit_date=d, reason="0_stop_intra", held=age,
                            up=(hi / entry - 1) * 100, dip=(lo / entry - 1) * 100), None
        close = float(g["c"].iloc[-1])
        reason = None
        if variant in ("H8", "H11"):
            n = 8 if variant == "H8" else 11
            reason = "2_t_minus_1" if to_exp <= v7.T_MINUS else ("3_hold" if age >= n else None)
        elif variant == "S8" and age < 8:
            best = max(best, close)
            reason = "2_t_minus_1" if to_exp <= v7.T_MINUS else None
        else:
            best, stall, reason = v7.exit_step(close, entry, best, stall, to_exp, v7.STOP)
        if reason:
            px = max(0.0, round(close - TICK, 2))
            return dict(entry=entry, exit_price=px, exit_date=d, reason=reason, held=age,
                        up=(hi / entry - 1) * 100, dip=(lo / entry - 1) * 100), None
    return "no_exit_in_data", None


def main() -> None:
    cal = [iso(x) for x in calendar()]
    contracts = pd.read_csv(RES / "S1_v10_bandarmab2_contracts.csv")
    mins = pd.read_csv(RES / "S1_v10_bandarmab2_minutes.csv")
    mins["dt"] = pd.to_datetime(mins["ts"])
    mins["d"] = mins["dt"].dt.strftime("%Y-%m-%d")
    mins["t"] = mins["dt"].dt.strftime("%H:%M")
    mins = mins.sort_values("dt")
    path = {}
    for (sym, day0, strike), g in mins.groupby(["symbol", "day0", "strike"]):
        path[(sym, day0, float(strike))] = {d: x for d, x in g.groupby("d")}
    tr = pd.read_csv(RES / "S1_armb_hold_and_nifty_trades.csv")
    tr = tr[(tr.variant == "LIVE") & tr.arm.isin(["A", "B"]) & tr.excluded.isna() & (tr.expiry >= "2024-10-01")]
    tr = tr.drop_duplicates(["arm", "symbol", "signal_date", "strike", "expiry"])
    rows, excl = [], {}
    for r in tr.itertuples():
        days = path.get((r.symbol, r.signal_date, float(r.strike)))
        for var in VARIANTS:
            if days is None:
                excl[(var, "no_candles")] = excl.get((var, "no_candles"), 0) + 1
                continue
            res, _ = run_one(days, cal, r.entry_date, r.expiry, var)
            if not isinstance(res, dict):
                excl[(var, res)] = excl.get((var, res), 0) + 1
                continue
            slip = v4.SLIPPAGE.get(r.category, v4.SLIPPAGE["unknown"])
            ch, sl, net = v4.net_of(res["entry"], res["exit_price"], r.lot, slip)
            rows.append(dict(arm=r.arm, variant=var, symbol=r.symbol, entry_date=r.entry_date, exit_date=res["exit_date"],
                             exit_reason=res["reason"], held=res["held"], entry=res["entry"], daily_entry=r.entry_price,
                             exit_price=res["exit_price"], lot=r.lot, net=net,
                             net_pct=round(net / (res["entry"] * r.lot) * 100, 3), excluded="",
                             max_up_pct=res["up"], max_dip_pct=res["dip"]))
    t = pd.DataFrame(rows)
    t.to_csv(RES / "S1_armab_minutes_trades.csv", index=False)
    out = []
    for arm in ("A", "B"):
        for var in VARIANTS:
            g = t[(t.arm == arm) & (t.variant == var)]
            out.append({"arm": arm, "variant": var, "period": "all", **stats(g)})
            for nm, gh in (("2024-25", g[g.entry_date < "2026"]), ("2026", g[g.entry_date >= "2026"])):
                out.append({"arm": arm, "variant": var, "period": nm, **stats(gh)})
    gap = t[t.variant == "LIVE-CLOSE"].assign(d=lambda x: (x.entry / x.daily_entry - 1) * 100)
    ex = pd.DataFrame([{"variant": v, "reason": k, "dropped": n} for (v, k), n in sorted(excl.items())])
    rep = ("# S1 arms A / B on 1-minute candles\n\nNumbers only. Pre-registered: strategies/S1_armab_minutes.md. Entry 09:16 open + 1 tick; "
           "max up / dip are intraday (candle high / low) as % of the entry fill. Contracts expiring from Oct 2024 only.\n\n"
           f"## Results\n\n{md(pd.DataFrame(out))}\n\n## Entry: minute entry vs the daily VWAP entry the old test used\n\n"
           f"mean {gap.d.mean():+.1f} %, median {gap.d.median():+.1f} % (n {len(gap)}); minute entry dearer in {int((gap.d > 0).mean() * 100)} % of trades\n\n"
           f"## Dropped\n\n{md(ex) if len(ex) else 'none'}\n")
    (RES / "S1_armab_minutes.md").write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
