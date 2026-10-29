"""S1 v12 fade · how high and how low did the option go after the buy: while held, after the sale, overall (numbers only)

    python -m scanner.fade_overall_max

For each of the 339 v12 backtest trades, from the 09:16 buy price:
  held        = the 1-minute highs / lows from the 09:16 candle to the v12 exit minute;
  after sale  = day 0 after the exit minute to 15:29 (1-minute highs / lows), then each later session's CLOSE from the
                F&O bhavcopy up to T-2 (two sessions before expiry, as the results page's Overall max up). Later days
                have closes only (the cached bhavcopies hold no high / low), so their peaks and dips are understated;
  overall     = the higher peak / lower dip of the two.
Grouped by the market pattern (Nifty up yesterday + gap down today vs the rest), side and win / fail.
Writes data/results/S1_fade_overall_max.xlsx.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment

from .build import ROOT
from .fade_indicators import RES, minute_book
from .fade_indicators_xlsx import F, FB, sheet
from .fade_market_pattern import market

CACHE = ROOT / "data" / "cache"


def calendar() -> list[pd.Timestamp]:
    return sorted(pd.Timestamp(p.stem[12:20]) for p in CACHE.glob("fo_bhavcopy_*.csv"))


def closes(need: dict[pd.Timestamp, set]) -> dict[tuple, float]:
    """(day, symbol, expiry, strike, side) -> that session's close, read once per bhavcopy."""
    out = {}
    for d, keys in sorted(need.items()):
        p = CACHE / f"fo_bhavcopy_{d:%Y%m%d}.csv"
        b = pd.read_csv(p, usecols=["FinInstrmTp", "TckrSymb", "XpryDt", "StrkPric", "OptnTp", "ClsPric"])
        b = b[b["FinInstrmTp"] == "STO"]
        syms = {k[0] for k in keys}
        b = b[b["TckrSymb"].isin(syms)]
        for r in b.itertuples(index=False):
            k = (r.TckrSymb, str(r.XpryDt)[:10], float(r.StrkPric), r.OptnTp)
            if k in keys:
                out[(d,) + k] = float(r.ClsPric)
    return out


def chg(x: float, e: float) -> float:
    return (x / e - 1) * 100


def main() -> None:
    t = pd.read_feather(RES / "S1_fade_market_direction_trades.feather").sort_values("day0").reset_index(drop=True)
    f = market(t)
    f["fail"] = f["fail"].astype(bool)
    book = minute_book()
    cal = calendar()
    later = {}
    for i, r in f.iterrows():
        d0, ex = pd.Timestamp(r["day0"]), pd.Timestamp(r["expiry"])
        sess = [d for d in cal if d0 < d <= ex]
        later[i] = sess[:-2] if len(sess) > 2 else []                      # up to T-2, as the page
    need: dict[pd.Timestamp, set] = {}
    for i, days in later.items():
        r = f.loc[i]
        for d in days:
            need.setdefault(d, set()).add((r["symbol"], str(r["expiry"])[:10], float(r["strike"]), r["side"]))
    cl = closes(need)
    rows = []
    for i, r in f.iterrows():
        e = float(r["entry 09:16+tick"])
        m = book.get((r["symbol"], r["day0"], r["side"], float(r["strike"])))
        x = {"held max up %": None, "held max dip %": None, "after sale max up %": None, "after sale max dip %": None,
             "later days found": 0, "later days to T-2": len(later[i])}
        if m is not None:
            m = m[m["t"] >= "09:16"]
            held, after = m[m["t"] <= r["v12 at"]], m[m["t"] > r["v12 at"]]
            if len(held):
                x["held max up %"], x["held max dip %"] = chg(held["h"].max(), e), chg(held["l"].min(), e)
                x["held max up at"] = held.loc[held["h"].idxmax(), "t"]
            hi = [after["h"].max()] if len(after) else []
            lo = [after["l"].min()] if len(after) else []
            for d in later[i]:
                c = cl.get((d, r["symbol"], str(r["expiry"])[:10], float(r["strike"]), r["side"]))
                if c is not None:
                    hi.append(c), lo.append(c)
                    x["later days found"] += 1
            if hi:
                x["after sale max up %"], x["after sale max dip %"] = chg(max(hi), e), chg(min(lo), e)
        ups = [v for v in (x["held max up %"], x["after sale max up %"]) if v is not None]
        dns = [v for v in (x["held max dip %"], x["after sale max dip %"]) if v is not None]
        x["overall max up %"] = max(ups) if ups else None
        x["overall max dip %"] = min(dns) if dns else None
        x["overall peak came"] = None if not ups else ("while held" if x["overall max up %"] == x["held max up %"] else "after the sale")
        rows.append(x)
    f = pd.concat([f, pd.DataFrame(rows)], axis=1)
    f["pattern"] = np.where((f["nifty prev day %"] > 0) & (f["nifty gap %"] < 0), "Nifty up yesterday + gap down", "all other trades")
    f["result"] = np.where(f["fail"], "failed", "won")

    def summ(g: pd.DataFrame) -> dict:
        o = {"trades": len(g), "fail %": g["fail"].mean() * 100, "mean net %": g["v12 net %"].mean(), "median net %": g["v12 net %"].median()}
        for w in ("held", "after sale", "overall"):
            for s in ("max up", "max dip"):
                c = g[f"{w} {s} %"].dropna()
                o[f"{w} {s} % mean"], o[f"{w} {s} % median"] = c.mean(), c.median()
        o["peak came after the sale %"] = (g["overall peak came"] == "after the sale").mean() * 100
        o["overall up ≥ +50 %, share %"] = (g["overall max up %"] >= 50).mean() * 100
        return o

    tabs = []
    for by in (["pattern"], ["pattern", "side"], ["pattern", "result"], ["pattern", "half"]):
        for k, g in f.groupby(by, sort=False):
            tabs.append({"group": " · ".join(k if isinstance(k, tuple) else (k,)), **summ(g)})
    tab = pd.DataFrame(tabs)
    write(RES / "S1_fade_overall_max.xlsx", f, tab)
    pd.set_option("display.width", 250)
    print(tab.round(1).T.to_string())
    print("later sessions found / expected:", int(f["later days found"].sum()), "/", int(f["later days to T-2"].sum()))


def write(path: Path, f: pd.DataFrame, tab: pd.DataFrame) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    p = tab.set_index("group")
    a, b = p.loc["Nifty up yesterday + gap down"], p.loc["all other trades"]
    lines = [("S1 v12 fade · how high and how low the option went after the buy: while held, after the sale, overall", FB),
             ("From the 09:16 buy price. Held = 1-minute highs/lows to the v12 exit. After sale = the rest of day 0 (1-minute highs/lows), "
              "then each later session's close up to T-2 (closes only, so later peaks/dips are understated). Overall = the higher / lower of the two.", F),
             ("", F)]
    for nm, r in (("Nifty up yesterday + gap down", a), ("All other trades", b)):
        lines.append((f"{nm} ({int(r['trades'])} trades, fail {r['fail %']:.0f} %, mean net {r['mean net %']:+.1f} %): "
                      f"max up held {r['held max up % mean']:.0f} % (median {r['held max up % median']:.0f} %), after sale "
                      f"{r['after sale max up % mean']:.0f} % (median {r['after sale max up % median']:.0f} %), overall {r['overall max up % mean']:.0f} % "
                      f"(median {r['overall max up % median']:.0f} %); max dip held {r['held max dip % mean']:.0f} %, after sale "
                      f"{r['after sale max dip % mean']:.0f} %, overall {r['overall max dip % mean']:.0f} % (median {r['overall max dip % median']:.0f} %). "
                      f"The overall peak came after the sale on {r['peak came after the sale %']:.0f} % of trades.", F))
    lines += [("", F), ("Sheets: Groups (pattern, side, win/fail, halves) · Trades (every trade's held / after-sale / overall peak and dip).", F)]
    for i, (txt, font) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=txt)
        c.font = font
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 170
    sheet(wb, "Groups", tab, "Mean and median of each window's max up and max dip, % of the buy price.")
    cols = ["day0", "half", "pattern", "symbol", "side", "strike", "expiry", "entry 09:16+tick", "v12 at", "v12 why", "v12 net %", "result",
            "held max up %", "held max up at", "held max dip %", "after sale max up %", "after sale max dip %", "overall max up %",
            "overall max dip %", "overall peak came", "later days found", "later days to T-2"]
    sheet(wb, "Trades", f[cols], "Every trade. Later days found = sessions after day 0 (to T-2) whose close was in the bhavcopy.")
    wb.save(path)


if __name__ == "__main__":
    main()
