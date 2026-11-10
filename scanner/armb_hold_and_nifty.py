"""S1 Arm B longer-hold exits, and is the profit just the NIFTY rising? (numbers only)

    EVENTS_DB=<events.sqlite with 2023+ results> python -m scanner.armb_hold_and_nifty

Pre-registered in strategies/S1_armb_hold_and_nifty.md. Part 1 re-runs Arm B with the exit changed (LIVE, H8, H11, S8)
on 2023-24 (v7 signals) and on the 2025-26 holdout (v8 signals). Part 2 sets every trade's net % against NIFTY's return
over the trade's life, and splits the live paper account around 28 Oct 2026.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import backtest_s1_v4 as v4
from . import backtest_s1_v7 as v7
from . import backtest_s1_v8 as v8
from .backtest_cheap_options import sessions_to
from .backtest_s1_v2 import Market, load_inputs, md, option_universe
from .build import ROOT
from .option_engine import TICK, window
from .stats import clustered_t

log = logging.getLogger("armb_hold")
HOLDOUT_START = "2025-04-01"
NIFTY_URL = "https://api.upstox.com/v3/historical-candle/NSE_INDEX%7CNifty%2050/days/1/{to}/{frm}"
SHIFT = "2026-10-28"

# --------------------------------------------------------------- exits (the only thing that changes)
VARIANTS = {"LIVE": (None, None), "H8": ("hold", 8), "H11": ("hold", 11), "S8": ("grace", 8)}
_orig_path = v7._path
CUR = {"mode": None, "n": None, "name": "LIVE"}
EXTREMES: dict = {}          # (variant, symbol, day 0) -> (highest close, lowest close) as % of the entry fill


def path(m, s, exp, k, entry, stop, days):
    mode, n = CUR["mode"], CUR["n"]
    e = s.i0 + 1
    hi = lo = None
    best, stall = entry, 0
    fut0 = stock0 = None
    j = e
    while j < len(m.cal):
        b = days.bhav(m.cal[j])
        if b is None:
            j += 1
            continue
        c = b["calls"].get((s.symbol, exp, k))
        px = m.close[s.symbol][j]
        f = b["futs"].get((s.symbol, exp))
        if c is None:
            return {"exit_i": j, "reason": None, "exit_price": None, "excluded": "contract_changed"}
        if fut0 is None:
            fut0, stock0 = f, px
        elif f and fut0 and stock0 and not (math.isnan(px) or math.isnan(stock0)):
            if abs((f / fut0) / (px / stock0) - 1) > v4.CA_TOLERANCE:
                return {"exit_i": j, "reason": None, "exit_price": None, "excluded": "price_adjusted"}
        to_exp = sessions_to(m.cal_dates, m.cal_dates[j], date.fromisoformat(exp))
        age = j - e
        reason = None
        hi, lo = (c, c) if hi is None else (max(hi, c), min(lo, c))
        EXTREMES[(CUR["name"], s.symbol, m.cal[s.i0])] = ((hi / entry - 1) * 100, (lo / entry - 1) * 100)
        if mode is None:
            best, stall, reason = v7.exit_step(c, entry, best, stall, to_exp, v7.STOP)
        elif mode == "hold":
            if to_exp <= v7.T_MINUS:
                reason = "2_t_minus_1"
            elif age >= n:
                reason = "3_hold"
        else:                                           # grace: nothing but T-1 for the first n sessions
            if age < n:
                best = max(best, c)
                reason = "2_t_minus_1" if to_exp <= v7.T_MINUS else None
            else:
                best, stall, reason = v7.exit_step(c, entry, best, stall, to_exp, v7.STOP)
        if reason:
            return {"exit_i": j, "reason": reason, "exit_price": max(0.0, round(c - TICK, 2)), "excluded": ""}
        j += 1
    return {"exit_i": len(m.cal) - 1, "reason": None, "exit_price": None, "excluded": "no_exit_in_data"}


v7._path = path


# --------------------------------------------------------------- statistics
def stats(g: pd.DataFrame) -> dict:
    g = g[g["excluded"].fillna("") == ""]
    if g.empty:
        return {"n": 0}
    x = g["net_pct"].astype(float)
    top = g.sort_values("net", ascending=False)
    ex3 = top.iloc[3:]["net_pct"].astype(float)
    tot = g["net"].sum()
    t = clustered_t(x.values, g["entry_date"].values)
    return {"n": len(g), "win_pct": round((x > 0).mean() * 100, 1), "mean_pct": round(x.mean(), 1),
            "median_pct": round(x.median(), 1), "total_rs": round(tot), "t": None if t is None else round(t, 2),
            "at_or_below_-50_pct": round((x <= -50).mean() * 100, 1), "worst_pct": round(x.min(), 1),
            "top3_share_of_profit_pct": round(top["net"].head(3).sum() / tot * 100) if tot > 0 else None,
            "mean_ex_top3_pct": None if ex3.empty else round(ex3.mean(), 1),
            "max_up_mean": round(g["max_up_pct"].astype(float).mean(), 1), "max_up_median": round(g["max_up_pct"].astype(float).median(), 1),
            "max_dip_mean": round(g["max_dip_pct"].astype(float).mean(), 1), "max_dip_median": round(g["max_dip_pct"].astype(float).median(), 1)}


# --------------------------------------------------------------- NIFTY
def nifty(frm: str, to: str) -> pd.Series:
    r = requests.get(NIFTY_URL.format(frm=frm, to=to), timeout=60).json()
    c = r["data"]["candles"]
    return pd.Series({x[0][:10]: float(x[4]) for x in c}).sort_index()


def nifty_ret(nf: pd.Series, a: str, b: str) -> float | None:
    """Return from the close on/before day a to the close on/before day b."""
    ia, ib = nf.index.searchsorted(a, side="right") - 1, nf.index.searchsorted(b, side="right") - 1
    if ia < 0 or ib < 0 or ib >= len(nf):
        return None
    return (nf.iloc[ib] / nf.iloc[ia] - 1) * 100


def regime(df: pd.DataFrame, label: str) -> list[dict]:
    d = df.dropna(subset=["net_pct", "nifty"])
    if len(d) < 8:
        return []
    out = []
    lo, hi = d["nifty"].quantile([1 / 3, 2 / 3])
    slope, icpt = np.polyfit(d["nifty"], d["net_pct"], 1)
    resid = d["net_pct"] - (slope * d["nifty"] + icpt)
    se_i = float(resid.std(ddof=2) * math.sqrt(1 / len(d) + d["nifty"].mean() ** 2 / ((d["nifty"] - d["nifty"].mean()) ** 2).sum()))
    row = {"group": label, "n": len(d), "corr": round(d["net_pct"].corr(d["nifty"]), 2),
           "slope_per_1pct_nifty": round(slope, 1), "intercept_flat_nifty": round(icpt, 1),
           "intercept_ci95": f"{icpt - 1.96 * se_i:+.0f} .. {icpt + 1.96 * se_i:+.0f}"}
    for nm, part in (("down", d[d["nifty"] <= lo]), ("flat", d[(d["nifty"] > lo) & (d["nifty"] <= hi)]),
                     ("up", d[d["nifty"] > hi])):
        row[f"{nm}_n"], row[f"{nm}_mean"], row[f"{nm}_win"] = len(part), round(part["net_pct"].mean(), 1), \
            round((part["net_pct"] > 0).mean() * 100)
    row["tercile_cuts_nifty_pct"] = f"{lo:+.1f} / {hi:+.1f}"
    out.append(row)
    return out


# --------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    ap.add_argument("--ledger", type=Path, required=True, help="a copy of the live paper_ledger.json")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from .nse_fo import BhavcopyUnavailable, download_fo_prices

    cache, eod2 = ROOT / "data" / "cache", ROOT / "data" / "eod2"
    t_start, t_end = window()
    universe = option_universe(cache, t_start, "9999-12-31")
    inp = load_inputs(eod2, cache, set().union(*universe.values()))
    m = Market(inp)

    def prices(d: str):
        try:
            return download_fo_prices(date.fromisoformat(d), cache)
        except (BhavcopyUnavailable, OSError, ValueError) as exc:
            log.warning("prices %s: %s", d, exc)
            return None

    days = v4.Days(cache, prices)
    last_t = max(i for i, d in enumerate(m.cal) if d <= t_end)
    last_h = len(m.cal) - 1
    base = Counter()
    sigs_t = v4.signals(m, inp.results, universe, t_start, last_t, base)
    sigs_h = v8.signals_any(m, inp.results, universe, HOLDOUT_START, last_h, Counter())
    rules = v7.Variant("old_expiry", near_expiry=False)

    frames = []
    for name, (mode, n) in VARIANTS.items():
        CUR.update(mode=mode, n=n, name=name)
        for period, sigs, end in (("2023-24", sigs_t, t_end), ("2025-26", None, m.cal[-1])):
            if period == "2023-24":
                t = v7.simulate(m, sigs, "B", rules, days, inp.ban, universe, inp.category, Counter(base), end)
                arms = {"B": t}
            else:
                arms = {}
                for arm in ("B", "A", "S", "S_miss") if name == "LIVE" else ("B",):
                    chosen = [s for s, k in sigs_h if v8.in_arm(arm, k, v4.strong_sector(s.state))]
                    arms[arm] = v7.simulate(m, chosen, "A", rules, days, inp.ban, universe, inp.category, Counter(),
                                            end)
            if period == "2023-24" and name == "LIVE":
                arms["A"] = v7.simulate(m, sigs, "A", rules, days, inp.ban, universe, inp.category, Counter(base), end)
            for arm, t in arms.items():
                if not t.empty:
                    ex_ = [EXTREMES.get((name, sy, d0), (None, None)) for sy, d0 in zip(t["symbol"], t["signal_date"])]
                    frames.append(t.assign(variant=name, period=period, arm=arm,
                                           max_up_pct=[x[0] for x in ex_], max_dip_pct=[x[1] for x in ex_]))
    CUR.update(mode=None, n=None)
    tr = pd.concat(frames, ignore_index=True)
    a.out_dir.mkdir(parents=True, exist_ok=True)

    # ---- Part 1
    rows = []
    for name in VARIANTS:
        for period in ("2023-24", "2025-26"):
            g = tr[(tr.variant == name) & (tr.arm == "B") & (tr.period == period)]
            rows.append({"variant": name, "period": period, **stats(g)})
            if period == "2025-26":
                for half, gh in (("2025", g[g.entry_date.astype(str) < "2026"]), ("2026", g[g.entry_date.astype(str) >= "2026"])):
                    rows.append({"variant": name, "period": half, **stats(gh)})
    p1 = pd.DataFrame(rows)
    ex = tr[(tr.variant == "LIVE") & (tr.arm == "B")].assign(h=lambda d: pd.cut(d.held.astype(float), [-1, 3, 7, 10, 99]))
    p1b = ex.groupby(["period", "h"], observed=True)["net_pct"].agg(["count", "mean", "median"]).round(1).reset_index()

    # ---- Part 2
    nf = nifty("2022-12-01", "2026-11-09")
    t2 = tr[tr.variant == "LIVE"].copy()
    t2["nifty"] = [nifty_ret(nf, str(e), str(x)) for e, x in zip(t2.entry_date, t2.exit_date)]
    reg = []
    for (period, arm), g in t2.groupby(["period", "arm"]):
        reg += regime(g[g["excluded"].fillna("") == ""], f"{period} arm {arm} (LIVE exit)")
    for name in ("H8", "H11", "S8"):
        g = tr[(tr.variant == name) & (tr.arm == "B")].copy()
        g["nifty"] = [nifty_ret(nf, str(e), str(x)) for e, x in zip(g.entry_date, g.exit_date)]
        reg += regime(g[g["excluded"].fillna("") == ""], f"B {name}, both periods")
    # NIFTY itself: the same windows' mean return
    p2 = pd.DataFrame(reg)

    L = json.loads(args_ledger(a.ledger))
    live = []
    for c in L["closed"]:
        r = c.get("rule") or {}
        live.append({"id": c["id"], "kind": "closed", "strat": r.get("strategy") or "s1", "arms": "".join(r.get("arms") or []),
                     "entry": c["opened_at"][:10], "exit": c["closed_at"][:10], "net_pct": c["return_pct"], "net_rs": c["net_pnl"]})
    for p in L["positions"]:
        r = p.get("rule") or {}
        base_rs = (p.get("max_loss_at_entry") or 0) - (p.get("entry_charges_open") or 0)
        live.append({"id": p["id"], "kind": "open", "strat": r.get("strategy") or "s1", "arms": "".join(r.get("arms") or []),
                     "entry": p["opened_at"][:10], "exit": "2026-11-09",
                     "net_pct": round(p["unrealised"] / base_rs * 100, 1) if base_rs else None, "net_rs": p["unrealised"]})
    lv = pd.DataFrame(live)
    lv["nifty"] = [nifty_ret(nf, e, x) for e, x in zip(lv.entry, lv.exit)]
    lv["since_28oct"] = [nifty_ret(nf, SHIFT, x) for x in lv.exit]
    lv["opened"] = np.where(lv.entry < SHIFT, "before 28 Oct", "28 Oct or later")
    lv_sum = lv.groupby(["strat", "opened", "kind"]).agg(n=("id", "count"), mean_pct=("net_pct", "mean"),
                                                         win=("net_pct", lambda s: round((s > 0).mean() * 100)),
                                                         total_rs=("net_rs", "sum")).round(1).reset_index()
    tr.to_csv(a.out_dir / "S1_armb_hold_and_nifty_trades.csv", index=False)
    lv.to_csv(a.out_dir / "S1_armb_hold_and_nifty_live.csv", index=False)

    n28 = nifty_ret(nf, SHIFT, "2026-11-09")
    rep = (f"# S1 Arm B longer-hold exits, and NIFTY\n\nNumbers only. Pre-registered: strategies/S1_armb_hold_and_nifty.md. "
           f"2023-24 uses the results events from 2023 on (2021-22 events are not available here). NIFTY 28 Oct -> 9 Nov 2026: {n28:+.1f} %.\n\n"
           f"## Part 1 · Arm B by exit\n\n{md(p1)}\n\nLIVE exit by sessions held:\n\n{md(p1b)}\n\n"
           f"## Part 2 · net % against the NIFTY window return (LIVE exit unless named)\n\n{md(p2)}\n\n"
           f"## Live paper ledger around 28 Oct\n\n{md(lv_sum)}\n")
    (a.out_dir / "S1_armb_hold_and_nifty.md").write_text(rep, encoding="utf-8")
    print(rep)


def args_ledger(p: Path) -> str:
    return p.read_text(encoding="utf-8")


if __name__ == "__main__":
    main()
