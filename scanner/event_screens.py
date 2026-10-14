"""Stock-level event screens, as strategies/S1_v9_and_event_screens.md pre-registers them (numbers only).

    python -m scanner.event_screens [--only results blocks dividends qip]

1. S1 v9 results day: long at day 0's open on strong reported numbers, arms A and B.
2. Block deals: entry at the next session's open, by size and the deal day's move.
3. Ex-dividend: the stock short across the ex-date (and its excess over the dividend), and the put across it.
4. QIP: short at day 0's open after the first notice of an issue.
Each cell: N, mean, median, hit rate, date-clustered t, mean per year 2021-2026, and the pass test.
"""
from __future__ import annotations

import argparse
import logging
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .build import ROOT
from .stats import clustered_t

log = logging.getLogger("event_screens")

START, END = "2021-01-01", "2026-09-25"
COST, YEARS, HOLDS = 0.1, tuple(str(y) for y in range(2021, 2027)), (0, 1, 3, 5)
TICK = 0.05


# ---------------------------------------------------------------- pure helpers
def open_entry_return(opens: np.ndarray, closes: np.ndarray, i: int, h: int, direction: int) -> float:
    """Enter at the open of session i, exit at the close of session i+h; signed, net of COST."""
    if i + h >= len(closes) or not opens[i] > 0 or not closes[i + h] > 0 or math.isnan(opens[i]) or math.isnan(closes[i + h]):
        return math.nan
    return direction * (closes[i + h] / opens[i] - 1) * 100 - COST


def num_or_none(v):
    try:
        return None if v in (None, "n/m") or (isinstance(v, float) and math.isnan(v)) else float(v)
    except (TypeError, ValueError):
        return None


def strong(q: dict, np_yoy_min: float) -> bool:
    """NP YoY > np_yoy_min AND NP QoQ > 0 AND revenue YoY > 0 (a missing or not-meaningful number fails)."""
    a, b, c = num_or_none(q.get("net_profit_yoy")), num_or_none(q.get("net_profit_qoq")), num_or_none(q.get("revenue_yoy"))
    return a is not None and b is not None and c is not None and a > np_yoy_min and b > 0 and c > 0


def weak(q: dict) -> bool:
    a, b = num_or_none(q.get("net_profit_yoy")), num_or_none(q.get("net_profit_qoq"))
    return a is not None and b is not None and a < -10 and b < 0


def summarise(df: pd.DataFrame, cell: dict, col: str, min_mean: float, direction_free: bool = False) -> dict:
    x = df.dropna(subset=[col])
    r = x[col].astype(float)
    sign = 1
    if direction_free and len(r) and r.mean() < 0:
        sign, r = -1, -r - 2 * COST                       # the other side, net of its own cost
    yrs = {y: (round(r[x["date"].str[:4] == y].mean(), 3) if (x["date"].str[:4] == y).any() else None) for y in YEARS}
    t = clustered_t(r, x["date"]) if len(x) > 1 else None
    pos = sum(1 for y in YEARS if (yrs[y] or 0) > 0)
    ok = len(x) >= 100 and (t or 0) >= 3 and (r.mean() if len(r) else 0) >= min_mean and pos >= 5 \
        and (yrs["2025"] or 0) > 0 and (yrs["2026"] or 0) > 0
    return {**cell, **({"side": "long" if sign > 0 else "short"} if direction_free else {}), "n": len(x),
            "mean": round(r.mean(), 3) if len(r) else None, "median": round(r.median(), 3) if len(r) else None,
            "hit": round((r > 0).mean() * 100, 1) if len(r) else None, "t": t, **yrs, "years_pos": pos,
            "PASS": "PASS" if ok else ""}


# ---------------------------------------------------------------- data
class Prices:
    """eod2 open / close aligned to one calendar (NIFTY 50's sessions)."""

    def __init__(self, symbols, eod2: Path, cal: list[str]):
        from .equity import load_symbol
        self.cal, self.pos = cal, {d: i for i, d in enumerate(cal)}
        self.o, self.c = {}, {}
        for s in sorted(set(symbols)):
            try:
                f = load_symbol(s, eod2)
            except Exception:  # noqa: BLE001
                continue
            f.index = f.index.strftime("%Y-%m-%d")
            f = f[~f.index.duplicated(keep="last")]
            self.o[s] = f["Open"].reindex(cal).to_numpy(dtype=float)
            self.c[s] = f["Close"].reindex(cal).to_numpy(dtype=float)


def calendar(eod2: Path) -> list[str]:
    from .backtest_cheap_options import _read_index
    return [d.strftime("%Y-%m-%d") for d in _read_index(eod2).index if START <= d.strftime("%Y-%m-%d") <= END]


def fo_universe(cache: Path) -> dict[str, set[str]]:
    from .s2_screen import oi_panel
    panel, _ = oi_panel(cache)
    return {d: set(row.dropna().index[row.dropna() > 0]) for d, row in panel.iterrows()}


# ---------------------------------------------------------------- 1. results day
def screen_results(px: Prices, uni: dict, eod2: Path, cache: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    from . import backtest_s1_v4 as v4
    from .backtest_s1_v2 import Market, day0_index, load_inputs
    from .events.store import Store
    from .financials import load as load_fin
    from .peak_study import result_quality
    fin = load_fin()
    with Store() as st:
        results = [(e["symbol"], e["event_date"], e.get("event_time")) for e in st.all_of_type("results")]
    inp = load_inputs(eod2, cache, set(px.c))
    m = Market(inp)
    rows, seen = [], set()
    for sym, d, t in results:
        i = day0_index(px.cal, d, t)
        if i is None or i < 1 or (sym, i) in seen or sym not in px.c or sym not in uni.get(px.cal[i], ()):
            continue
        seen.add((sym, i))
        o, c = px.o[sym], px.c[sym]
        if not (c[i - 1] > 0 and o[i] > 0):
            continue
        q = result_quality(fin, sym, d)
        j = m.pos.get(px.cal[i - 1])
        state = m.state(sym, j) if j is not None and m.loo(sym) is not None else None
        rows.append({"symbol": sym, "date": px.cal[i], "filed": d, "gap_pct": round((o[i] / c[i - 1] - 1) * 100, 3),
                     "strong10": strong(q, 10), "strong25": strong(q, 25), "weak": weak(q),
                     "known": num_or_none(q.get("net_profit_yoy")) is not None, "armB": v4.strong_sector(state),
                     **{f"l{h}": open_entry_return(o, c, i, h, 1) for h in HOLDS}})
    ev = pd.DataFrame(rows)
    out = []
    for thr in ("strong10", "strong25"):
        for gap in (False, True):
            for arm in ("A", "B"):
                g = ev[ev[thr] & (ev["armB"] if arm == "B" else True) & ((ev["gap_pct"] <= 5) if gap else True)]
                for h in HOLDS:
                    out.append(summarise(g, {"cell": f"{thr.replace('strong', 'NP YoY>')}% & QoQ>0 & rev YoY>0"
                                                     + (" & gap<=5%" if gap else ""), "arm": arm, "h": h,
                                             "side": "long"}, f"l{h}", 1.0 if h >= 3 else 0.6))
    for arm in ("A", "B"):
        g = ev[ev["weak"] & (ev["armB"] if arm == "B" else True)]
        for h in HOLDS:
            g2 = g.assign(**{f"s{h}": -g[f"l{h}"] - 2 * COST})
            out.append(summarise(g2, {"cell": "weak: NP YoY<-10% & QoQ<0 (side report)", "arm": arm, "h": h,
                                      "side": "short"}, f"s{h}", 0.6))
    return ev, pd.DataFrame(out)


# ---------------------------------------------------------------- 2. block deals
def screen_blocks(px: Prices, uni: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    from .events.store import Store
    with Store() as st:
        deals = pd.DataFrame([{"symbol": e["symbol"], "d": e["event_date"], "v": e.get("value_cr") or 0.0}
                              for e in st.all_of_type("block_deal")])
    deals = deals.groupby(["symbol", "d"], as_index=False)["v"].sum()
    rows = []
    for r in deals.itertuples():
        i = px.pos.get(r.d)
        if i is None or i < 1 or r.symbol not in px.c or r.symbol not in uni.get(r.d, ()):
            continue
        o, c = px.o[r.symbol], px.c[r.symbol]
        if not (c[i - 1] > 0 and c[i] > 0) or i + 1 >= len(c):
            continue
        rows.append({"symbol": r.symbol, "date": px.cal[i + 1], "deal_date": r.d, "value_cr": r.v,
                     "deal_day_pct": round((c[i] / c[i - 1] - 1) * 100, 3),
                     **{f"l{h}": open_entry_return(o, c, i + 1, h, 1) for h in HOLDS}})
    ev = pd.DataFrame(rows)
    out = []
    for size in (100, 500, 1000):
        for move in ("up", "down"):
            g = ev[(ev["value_cr"] >= size) & ((ev["deal_day_pct"] > 0) if move == "up" else (ev["deal_day_pct"] < 0))]
            for h in HOLDS:
                out.append(summarise(g, {"cell": f">= Rs {size} cr, deal day {move}", "h": h}, f"l{h}", 0.6,
                                     direction_free=True))
    return ev, pd.DataFrame(out)


# ---------------------------------------------------------------- 3. ex-dividend
def _lot_from_oi(oi: pd.Series) -> int:
    v = oi[oi > 0].astype("int64").to_numpy()
    return int(np.gcd.reduce(v)) if len(v) else 0


def put_across(sym: str, prev: str, ex: str, spot: float, cache: Path) -> dict | None:
    """The put of the first monthly expiry after the ex-date, nearest `spot`, bought at prev's close + 1 tick and
    sold at the ex-date close - 1 tick; net % of premium with charges and 2 % slippage per side."""
    from . import backtest_s1_v4 as v4
    from .option_engine import monthly
    fa, fb = cache / f"fo_bhavcopy_{prev.replace('-', '')}.csv", cache / f"fo_bhavcopy_{ex.replace('-', '')}.csv"
    if not (fa.exists() and fb.exists()):
        return None
    cols = lambda c: c in ("TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "OpnIntrst", "NewBrdLotQty")  # noqa: E731
    a, b = pd.read_csv(fa, usecols=cols), pd.read_csv(fb, usecols=cols)
    pa = a[(a["FinInstrmTp"] == "STO") & (a["OptnTp"] == "PE") & (a["TckrSymb"] == sym)].copy()
    if pa.empty:
        return None
    pa["XpryDt"] = pa["XpryDt"].astype(str).str[:10]
    exps = [e for e in monthly(pa["XpryDt"]) if e > ex]
    if not exps:
        return None
    ch = pa[pa["XpryDt"] == exps[0]]
    k = min(ch["StrkPric"].astype(float), key=lambda s: (abs(s - spot), -s))
    buy = float(ch.loc[ch["StrkPric"].astype(float) == k, "ClsPric"].iloc[0])
    pb = b[(b["FinInstrmTp"] == "STO") & (b["OptnTp"] == "PE") & (b["TckrSymb"] == sym)
           & (b["XpryDt"].astype(str).str[:10] == exps[0]) & (b["StrkPric"].astype(float) == k)]
    if pb.empty or not buy > 0:
        return None
    sell = float(pb["ClsPric"].iloc[0])
    lot = int(pa["NewBrdLotQty"].dropna().iloc[0]) if "NewBrdLotQty" in pa and pa["NewBrdLotQty"].notna().any() \
        else _lot_from_oi(a[(a["TckrSymb"] == sym) & (a["FinInstrmTp"] == "STO")]["OpnIntrst"])
    if not lot:
        return None
    entry, exit_ = round(buy + TICK, 2), max(0.0, round(sell - TICK, 2))
    _, _, net = v4.net_of(entry, exit_, lot, 0.02)
    return {"put_strike": k, "put_expiry": exps[0], "put_entry": entry, "put_exit": exit_, "lot": lot,
            "put_pct": round(net / (entry * lot) * 100, 3), "lot_cost": round(entry * lot)}


def screen_dividends(px: Prices, uni: dict, cache: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    ca = pd.read_csv(cache / "corp_actions.csv")
    ca = ca[(ca["kind"] == "dividend") & ca["dividend_rs"].notna()]
    ca = ca.groupby(["symbol", "ex_date"], as_index=False)["dividend_rs"].sum()
    rows = []
    for r in ca.itertuples():
        i = px.pos.get(r.ex_date)
        if i is None or i < 1 or r.symbol not in px.c or r.symbol not in uni.get(px.cal[i - 1], ()):
            continue
        o, c = px.o[r.symbol], px.c[r.symbol]
        if not (c[i - 1] > 0 and c[i] > 0 and o[i] > 0):
            continue
        y = r.dividend_rs / c[i - 1] * 100
        ret = (c[i] / c[i - 1] - 1) * 100
        row = {"symbol": r.symbol, "date": px.cal[i], "dividend_rs": r.dividend_rs, "yield_pct": round(y, 3),
               "stock_short_pct": round(-ret - COST, 3), "open_short_pct": round(-(o[i] / c[i - 1] - 1) * 100 - COST, 3),
               "excess_short_pct": round(-(ret + y) - COST, 3)}
        put = put_across(r.symbol, px.cal[i - 1], px.cal[i], float(c[i - 1]), cache)
        rows.append({**row, **(put or {})})
    ev = pd.DataFrame(rows)
    out = []
    for lo, hi, name in ((0, 1, "< 1 %"), (1, 2, "1-2 %"), (2, 100, ">= 2 %")):
        g = ev[(ev["yield_pct"] >= lo) & (ev["yield_pct"] < hi)]
        out.append(summarise(g, {"cell": f"yield {name}", "measure": "stock short, close to ex-date close"}, "stock_short_pct", 0.6))
        out.append(summarise(g, {"cell": f"yield {name}", "measure": "excess over the dividend (short)"}, "excess_short_pct", 0.6))
        if "put_pct" in g:
            out.append(summarise(g, {"cell": f"yield {name}", "measure": "put across the ex-date, % of premium"}, "put_pct", 0.0))
    return ev, pd.DataFrame(out)


# ---------------------------------------------------------------- 4. QIP
def screen_qip(px: Prices, uni: dict, cache: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    from .backtest_s1_v2 import day0_index
    from .qip import first_per_issue
    q = first_per_issue(pd.read_csv(cache / "qip_events.csv", dtype=str))
    rows = []
    for r in q.itertuples():
        i = day0_index(px.cal, r.date, r.time if isinstance(r.time, str) else None)
        if i is None or i < 1 or r.symbol not in px.c or r.symbol not in uni.get(px.cal[i], ()):
            continue
        o, c = px.o[r.symbol], px.c[r.symbol]
        rows.append({"symbol": r.symbol, "date": px.cal[i], "filed": r.date,
                     **{f"s{h}": open_entry_return(o, c, i, h, -1) for h in HOLDS}})
    ev = pd.DataFrame(rows)
    out = [summarise(ev, {"cell": "QIP first notice, short", "h": h}, f"s{h}", 0.6) for h in HOLDS] if len(ev) else []
    return ev, pd.DataFrame(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Stock-level event screens (S1 v9 results day, block deals, ex-dividend, QIP)")
    ap.add_argument("--only", nargs="*", default=["results", "blocks", "dividends", "qip"])
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from .backtest_s1_v2 import md
    cal = calendar(a.eod2_dir)
    uni = fo_universe(a.cache_dir)
    px = Prices(set().union(*uni.values()), a.eod2_dir, cal)
    runs = {"results": lambda: screen_results(px, uni, a.eod2_dir, a.cache_dir), "blocks": lambda: screen_blocks(px, uni),
            "dividends": lambda: screen_dividends(px, uni, a.cache_dir), "qip": lambda: screen_qip(px, uni, a.cache_dir)}
    a.out_dir.mkdir(parents=True, exist_ok=True)
    for name in a.only:
        ev, tab = runs[name]()
        ev.to_csv(a.out_dir / f"event_screen_{name}_events.csv", index=False)
        tab.to_csv(a.out_dir / f"event_screen_{name}.csv", index=False)
        passed = tab[tab["PASS"] == "PASS"] if len(tab) else tab
        text = f"## {name}: {len(ev)} events, {len(passed)} of {len(tab)} cells pass\n\n" + md(tab)
        (a.out_dir / f"event_screen_{name}.md").write_text(text, encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
