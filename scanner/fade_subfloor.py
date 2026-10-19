"""S1 v10 fade · the sub-Rs 2 entries the floor refuses: tick-based costs, bands, expiry and distance splits (numbers only).

    python -m scanner.fade_subfloor

strategies/S1_v10_subfloor_entry.md. Reads the floor-free runs (S1_v10_trades_floor0p05.csv for 2025-26,
S1_v10_trades_2022_24_floor0p05.csv for 2022-24), the >= Rs 2 runs for the comparison line (S1_v10_trades_floor2.csv,
S1_v10_trades_2022_24.csv; not re-run) and the cached option files. Writes data/results/S1_v10_subfloor_entry.md and
S1_v10_subfloor_trades.csv.
"""
from __future__ import annotations

import pandas as pd

from server import charges as ch

from .backtest_s1_v2 import md
from .backtest_s1_v10 import MIN_CONTRACTS, TICK, quotes_of, start_strike
from .build import ROOT
from .fade_floor_sheet import ohlc
from .stats import clustered_t

RES, CACHE = ROOT / "data" / "results", ROOT / "data" / "cache"
WINDOWS = {"2022-24": ("S1_v10_trades_2022_24_floor0p05.csv", "S1_v10_trades_2022_24.csv", "S1_v10_backtest_report_2022_24.md"),
           "2025-26": ("S1_v10_trades_floor0p05.csv", "S1_v10_trades_floor2.csv", "S1_v10_backtest_report_floor2.md")}
BANDS = (("< Rs 0.50", 0.0, 0.5), ("Rs 0.50-1", 0.5, 1.0), ("Rs 1-1.50", 1.0, 1.5), ("Rs 1.50-2", 1.5, 2.0))
DTE = (("<= 2 sessions", 0, 2), ("3-5 sessions", 3, 5), ("> 5 sessions", 6, 10_000))
DIST = (("<= 2 % OTM (incl. ITM)", -1e9, 2.0), ("2-5 % OTM", 2.0, 5.0), ("5-10 % OTM", 5.0, 10.0), ("> 10 % OTM", 10.0, 1e9))
_SESSIONS = sorted(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}" for p in CACHE.glob("fo_bhavcopy_*.csv"))


def sessions_left(day0: str, expiry: str) -> int:
    """Sessions after day 0 up to and including the expiry day (cached bhavcopy dates; weekdays past the cache)."""
    n = sum(1 for d in _SESSIONS if day0 < d <= expiry)
    last = _SESSIONS[-1] if _SESSIONS else day0
    if expiry > last:
        from server.sessions import is_session
        n += sum(1 for d in pd.date_range(max(last, day0), expiry)[1:] if is_session(d.date()))
    return n


def cost(side: str, lot: int, entry: float, exit_: float) -> tuple[float, float]:
    """(charges Rs on both orders, net Rs) for one lot bought at `entry` and sold at `exit_`."""
    c = ch.leg(side, "BUY", lot, entry)["total"] + (ch.leg(side, "SELL", lot, exit_)["total"] if exit_ > 0 else 0.0)
    return round(c, 2), round((exit_ - entry) * lot - c, 2)


def priced(t: pd.DataFrame, ticks: int) -> pd.DataFrame:
    """Entry = day 0's open + `ticks` ticks, exit = day 0's close - `ticks` ticks (not below 0), charges on both."""
    t = t.copy()
    t["entry_px"] = (t["o"] + ticks * TICK).round(2)
    t["exit_px"] = (t["c"] - ticks * TICK).clip(lower=0).round(2)
    cn = [cost(r.side, int(r.lot), r.entry_px, r.exit_px) for r in t.itertuples()]
    t["charges"], t["net"] = [x[0] for x in cn], [x[1] for x in cn]
    t["lot_value"] = t["entry_px"] * t["lot"]
    t["net_pct"] = t["net"] / t["lot_value"] * 100
    t["charges_pct"] = t["charges"] / t["lot_value"] * 100
    t["high_2x"] = t["h"] >= 2 * t["entry_px"]
    return t


def max_dd(g: pd.DataFrame) -> float:
    cum = g.sort_values(["day0", "symbol"])["net"].cumsum()
    peak = cum.cummax().clip(lower=0)
    return round(float((peak - cum).max()), 0) if len(cum) else 0.0


def stats(g: pd.DataFrame) -> dict:
    if not len(g):
        return {"n": 0}
    r = g["net_pct"]
    return {"n": len(g), "win_pct": round((g["net"] > 0).mean() * 100, 1), "mean_pct": round(r.mean(), 2),
            "median_pct": round(r.median(), 2), "total_rs": round(g["net"].sum()), "max_dd_rs": max_dd(g),
            "t": clustered_t(r, g["day0"]) if len(g) > 1 else None,
            "high_2x_pct": round(g["high_2x"].mean() * 100, 1), "charges_pct_of_lot": round(g["charges_pct"].mean(), 2)}


def split(t: pd.DataFrame, col: str, buckets) -> pd.DataFrame:
    rows = [{"group": name, **stats(t[(t[col] >= lo) & (t[col] < hi if col != "dte" else t[col] <= hi)])}
            for name, lo, hi in buckets]
    return pd.DataFrame(rows + [{"group": "all sub-Rs 2", **stats(t)}])


def funnel_refused(report: str) -> int:
    """Signals the Rs 2 floor refused ("premium_below_2", open entry) from a backtest report's funnel table."""
    lines = (RES / report).read_text(encoding="utf-8").split("## Signals removed", 1)[1].splitlines()
    head = next(l for l in lines if l.startswith("| entry"))
    row = next(l for l in lines if l.startswith("| open"))
    cells = dict(zip([c.strip() for c in head.strip("|").split("|")], [c.strip() for c in row.strip("|").split("|")]))
    return int(float(cells["premium_below_2"]))


def path_liquidity(t: pd.DataFrame) -> tuple[int, int]:
    """On each traded sub-Rs 2 signal's walk path (start strike to traded strike, day 0's option file): strikes priced
    below Rs 2 (open + 1 tick), and how many of them had >= 50 contracts."""
    seen = liquid = 0
    for d0, g in t.groupby("day0"):
        p = pd.read_csv(CACHE / f"fo_prices_{d0.replace('-', '')}.csv")
        for r in g.itertuples():
            qs = quotes_of(p, r.symbol, r.expiry, r.side)
            ks = sorted(qs)
            k0 = start_strike(ks, r.spot_prev_close, r.side)
            if k0 is None or float(r.strike) not in qs:
                continue
            i, j = ks.index(k0), ks.index(float(r.strike))
            path = ks[j:i + 1] if r.side == "PE" else ks[i:j + 1]
            for k in path:
                q = qs[k]
                if q.open == q.open and q.open + TICK < 2.0:
                    seen += 1
                    liquid += int(q.contracts >= MIN_CONTRACTS)
    return seen, liquid


def load(window: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    free, base, _ = WINDOWS[window]
    t = pd.read_csv(RES / free)
    t = t[(t["entry"] == "open") & (t["e1_excluded"].fillna("") == "")].reset_index(drop=True)
    b = pd.read_csv(RES / base)
    b = b[(b["entry"] == "open") & (b["e1_excluded"].fillna("") == "") & (b["entry_price"] >= 2)].reset_index(drop=True)
    for x in (t, b):
        x["window"] = window
    return t, b


def existing_line(b: pd.DataFrame) -> dict:
    r = b["e1_net_pct"].astype(float)
    return {"n": len(b), "win_pct": round((b["e1_net"] > 0).mean() * 100, 1), "mean_pct": round(r.mean(), 2),
            "median_pct": round(r.median(), 2), "total_rs": round(b["e1_net"].sum()),
            "t": clustered_t(r, b["day0"]) if len(b) > 1 else None}


def main() -> None:
    subs, bases, fun, sens = [], [], [], []
    for w, (_, _, rep) in WINDOWS.items():
        t, b = load(w)
        t = t.join(ohlc(t))
        sub = t[t["entry_price"] < 2.0].copy()
        sub["dte"] = [sessions_left(r.day0, r.expiry) for r in sub.itertuples()]
        sub["otm_pct"] = [((r.spot_prev_close - r.strike) if r.side == "PE" else (r.strike - r.spot_prev_close))
                          / r.spot_prev_close * 100 for r in sub.itertuples()]
        seen, liquid = path_liquidity(sub)
        fun.append({"window": w, "refused_by_rs2_floor": funnel_refused(rep), "traded_floor_free_sub_rs2": len(sub),
                    "sub_rs2_strikes_on_walk_paths": seen, "with_ge_50_contracts": liquid,
                    "share_liquid_pct": round(liquid / seen * 100, 1) if seen else None,
                    "two_sided_quote": "not in the data"})
        subs.append(sub)
        b = b.join(ohlc(b))
        bases.append(b)
    sub_all, base_all = pd.concat(subs, ignore_index=True), pd.concat(bases, ignore_index=True)
    p2, p1 = priced(sub_all, 2), priced(sub_all, 1)
    b2 = priced(base_all, 2)
    p2.to_csv(RES / "S1_v10_subfloor_trades.csv", index=False)

    def per_window(df, fn):
        return pd.DataFrame([{"window": w, **fn(df[df["window"] == w])} for w in WINDOWS] + [{"window": "pooled", **fn(df)}])

    band_tabs = {w: split(p2[p2["window"] == w] if w != "pooled" else p2, "entry_price", BANDS) for w in (*WINDOWS, "pooled")}
    comp = pd.DataFrame(
        [{"set": f">= Rs 2, existing model (open+1 / close-1 tick, % slippage), {w}", **existing_line(base_all[base_all["window"] == w])}
         for w in WINDOWS]
        + [{"set": f">= Rs 2, this study's tick model (recomputed, not re-run), {w}", **stats(b2[b2["window"] == w])} for w in WINDOWS]
        + [{"set": f"sub-Rs 2, tick model, {w}", **stats(p2[p2["window"] == w])} for w in WINDOWS]
        + [{"set": "sub-Rs 2, tick model, pooled", **stats(p2)}])
    top = p2["net"].idxmax()
    no_top = p2.drop(index=top)
    crit = {
        "1. total > 0 in each window": all(p2[p2["window"] == w]["net"].sum() > 0 for w in WINDOWS),
        "2. pooled mean > 0 with t >= 2": bool(p2["net_pct"].mean() > 0 and (clustered_t(p2["net_pct"], p2["day0"]) or 0) >= 2),
        f"3. pooled total > 0 without the largest winner ({p2.loc[top, 'symbol']} {p2.loc[top, 'day0']}, "
        f"Rs {p2.loc[top, 'net']:,.0f})": bool(no_top["net"].sum() > 0),
    }
    passed = all(crit.values())
    s_all, s_w = stats(p2), {w: stats(p2[p2["window"] == w]) for w in WINDOWS}
    by_w = ", ".join(f"{w}: Rs {s_w[w]['total_rs']:,}" for w in WINDOWS)
    verdict = (
        f"**Verdict: the sub-Rs 2 trades {'add' if passed else 'do not add'} money on top of the >= Rs 2 set.** "
        f"Under the pre-registered tick model (entry = open + Rs 0.10, exit = close - Rs 0.10, real charges), the "
        f"{s_all['n']} sub-Rs 2 trades made Rs {s_all['total_rs']:,} in total "
        f"({by_w}), "
        f"winning {s_all['win_pct']} % of the time, mean {s_all['mean_pct']:+.1f} % a trade (t {s_all['t']}). "
        f"Without the single best trade the pooled total is Rs {round(no_top['net'].sum()):,}. "
        + ("All three pass conditions hold. " if passed else
           f"Conditions failed: {', '.join(k.split('.')[0] for k, v in crit.items() if not v)}. ")
        + f"The result depends on the cost of crossing the spread: with 1 tick each side instead of 2, the same trades make "
          f"Rs {round(p1['net'].sum()):,} (t {clustered_t(p1['net_pct'], p1['day0'])}), still far from the pass bar. "
        + "This is descriptive and not out of sample. The live floor stays at Rs 2; the live shadow-entry track is the fresh test.")
    text = "\n".join([
        "# S1 v10 fade · sub-Rs 2 entries (the trades the Rs 2 floor refuses)\n",
        "Numbers only. Pre-registered: strategies/S1_v10_subfloor_entry.md. Windows: day 0 in 2022-01-01 .. 2024-12-31 and "
        "2025-01-01 .. 2026-09-25. v10's walk with the floor at one tick; the lot-cost rule (Rs 600-8,000) and the liquidity "
        "rule (>= 50 contracts on day 0) unchanged. Sub-Rs 2 = walk fill (open + 1 tick) below Rs 2. Primary cost model: "
        "entry = open + 2 ticks (ask + 1 tick), exit = close - 2 ticks (bid - 1 tick), charges from server/charges.py "
        "(Rs 20 brokerage an order), no % slippage. Net % is of the lot value at entry. t is date-clustered. Max drawdown "
        "is on cumulative net Rs in day-0 order. \"high 2x\" = day 0's option high >= 2 x entry. Trade list: "
        "data/results/S1_v10_subfloor_trades.csv.\n",
        verdict + "\n",
        "## Pass criterion\n\n" + "\n".join(f"- {k}: **{'yes' if v else 'no'}**" for k, v in crit.items()) + "\n",
        "## Comparison with the >= Rs 2 set\n\n" + md(comp),
        *[f"## By entry band, {w}\n\n" + md(band_tabs[w]) for w in (*WINDOWS, "pooled")],
        "## By sessions to expiry after day 0 (pooled)\n\n" + md(split(p2, "dte", DTE)),
        "## By strike distance out of the money from the previous close (pooled)\n\n" + md(split(p2, "otm_pct", DIST)),
        "## Sensitivity: 1 tick each side (open + Rs 0.05, close - Rs 0.05), same charges\n\n"
        + md(per_window(p1, stats)),
        "## Liquidity funnel\n\n" + md(pd.DataFrame(fun))
        + "\n\nThe walk only takes a strike with >= 50 contracts, so every traded strike passed it. The share above "
          "is over all the sub-Rs 2 strikes the walk passed on the way. NSE's bhavcopy has no bid or ask, so whether a "
          "two-sided quote existed cannot be checked; the live shadow-entry track checks it.\n",
    ])
    (RES / "S1_v10_subfloor_entry.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
