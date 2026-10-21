"""S1 fade · refused sub-Rs 2 signals bought anyway if the contract's listing-day price was < Rs 10 / < Rs 7 (v12 exit).

    python -m scanner.fade_refused_listing

strategies/S1_refused_listing_price.md fixes every choice. Reads data/results/S1_fade_cheap_dte_trades.csv (v12 results
on the realistic entry) and the NSE bhavcopy cache for each contract's first traded day. Writes
data/results/S1_refused_listing_price.md, _trades.csv and .xlsx.
"""
from __future__ import annotations

import glob

import pandas as pd

from .backtest_s1_v2 import md
from .build import ROOT
from .stats import clustered_t

RES, CACHE = ROOT / "data" / "results", ROOT / "data" / "cache"


def listing_close(t: pd.DataFrame) -> dict:
    keys = {(r.symbol, r.expiry, float(r.strike), r.side) for r in t.itertuples()}
    syms = {k[0] for k in keys}
    first: dict = {}
    for f in sorted(glob.glob(str(CACHE / "fo_bhavcopy_*.csv"))):
        if f[-12:-4] < "20240601":
            continue
        x = pd.read_csv(f, usecols=["TradDt", "TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric",
                                    "TtlTradgVol"])
        x = x[(x.FinInstrmTp == "STO") & x.TckrSymb.isin(syms) & (x.TtlTradgVol > 0)]
        for r in x.itertuples():
            k = (r.TckrSymb, str(r.XpryDt)[:10], float(r.StrkPric), r.OptnTp)
            if k in keys and k not in first:
                first[k] = (str(r.TradDt)[:10], float(r.ClsPric))
    return first


def stats(g: pd.DataFrame, **lab) -> dict:
    if g.empty:
        return {**lab, "n": 0}
    return {**lab, "n": len(g), "win %": round((g["v12_net"] > 0).mean() * 100, 1),
            "mean %": round(g["v12_net_pct"].mean(), 2), "median %": round(g["v12_net_pct"].median(), 1),
            "total Rs": round(g["v12_net"].sum()), "t": clustered_t(g["v12_net_pct"], g["day0"]) if len(g) > 1 else None}


def main() -> None:
    t = pd.read_csv(RES / "S1_fade_cheap_dte_trades.csv")
    t = t[t["entry_B"] < 2].copy()                                 # refused by the Rs 2 floor today
    first = listing_close(t)
    t["listing_day"] = [first.get((r.symbol, r.expiry, float(r.strike), r.side), (None, None))[0] for r in t.itertuples()]
    t["listing_close"] = [first.get((r.symbol, r.expiry, float(r.strike), r.side), (None, None))[1] for r in t.itertuples()]
    t.to_csv(RES / "S1_refused_listing_price_trades.csv", index=False)
    known = t[t["listing_close"].notna()]
    groups = {"all refused (B < Rs 2)": t, "listing price < Rs 10": known[known.listing_close < 10],
              "listing price < Rs 7": known[known.listing_close < 7], "listing price >= Rs 10": known[known.listing_close >= 10]}
    rows, tests = [], []
    for name, g in groups.items():
        for h in ("all", "Oct24-Oct25", "Nov25-Sep26"):
            rows.append(stats(g if h == "all" else g[g["half"] == h], group=name, period=h))
    for name in ("listing price < Rs 10", "listing price < Rs 7"):
        g = groups[name]
        s = stats(g)
        h1, h2 = (g[g["half"] == h]["v12_net_pct"].mean() for h in ("Oct24-Oct25", "Nov25-Sep26"))
        tests.append({"rule": name, "n": s["n"], "mean %": s.get("mean %"), "t": s.get("t"), "half 1 mean %": round(h1, 2),
                      "half 2 mean %": round(h2, 2),
                      "pass": bool(s["n"] and s["mean %"] > 0 and (s["t"] or 0) >= 2 and h1 > 0 and h2 > 0)})
    text = "\n".join([
        "# S1 fade · refused sub-Rs 2 signals bought anyway if the listing-day price was < Rs 10 / < Rs 7 (v12 exit)\n",
        f"Pre-registered: strategies/S1_refused_listing_price.md. {len(t)} refused contracts (realistic entry under Rs 2, "
        f"Oct 2024 - Aug 2026, no lot cap), listing price found for {len(known)}. Same-day v12 exit, real charges.\n",
        "## The test\n\n" + md(pd.DataFrame(tests)), "## Groups\n\n" + md(pd.DataFrame(rows))])
    (RES / "S1_refused_listing_price.md").write_text(text, encoding="utf-8")
    cols = ["symbol", "side", "strike", "expiry", "day0", "listing_day", "listing_close", "entry_B", "lot", "lot_value",
            "v12_net", "v12_net_pct"]
    with pd.ExcelWriter(RES / "S1_refused_listing_price.xlsx") as xw:
        pd.DataFrame(tests).to_excel(xw, sheet_name="Test", index=False)
        pd.DataFrame(rows).to_excel(xw, sheet_name="Groups", index=False)
        t.sort_values("day0", ascending=False)[cols].rename(columns={
            "symbol": "Stock", "side": "Side", "strike": "Strike", "expiry": "Expiry", "day0": "Signal day",
            "listing_day": "Listing day", "listing_close": "Listing-day price Rs", "entry_B": "Buy Rs (09:16)",
            "lot": "Lot", "lot_value": "Lot cost Rs", "v12_net": "Net Rs (v12)", "v12_net_pct": "Net % (v12)"}).to_excel(
            xw, sheet_name="Trades", index=False)
    print(text)


if __name__ == "__main__":
    main()
