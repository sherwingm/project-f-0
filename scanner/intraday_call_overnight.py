"""S1 · buy a call one minute after a strong market-hours result, sell at the next open (option backtest; numbers only).

    python -m scanner.intraday_call_overnight

strategies/S1_intraday_strong_call_overnight.md fixes every choice. Reads S1_v10_bandintra_contracts.csv, the option
minutes S1_v10_bandintra_minutes.csv (GitHub: fetch_band_minutes intra), lot sizes from the day's F&O bhavcopy and the
stock path cases. Writes data/results/S1_intraday_call_overnight.md and _trades.csv.
"""
from __future__ import annotations

import math

import pandas as pd

from server import charges as ch

from .backtest_s1_v2 import md
from .build import ROOT
from .results_intraday import hm
from .stats import clustered_t

RES, CACHE = ROOT / "data" / "results", ROOT / "data" / "cache"
BAND, FLOOR, WALK, TICK_CHANGE = (600.0, 8000.0), 2.0, 8, "2025-11-03"


def tick(day: str) -> float:
    return 0.05 if day < TICK_CHANGE else 0.01


def lot_of(sym: str, day: str, exp: str) -> int:
    b = pd.read_csv(CACHE / f"fo_bhavcopy_{day.replace('-', '')}.csv",
                    usecols=["TckrSymb", "FinInstrmTp", "XpryDt", "NewBrdLotQty"])
    x = b[(b["TckrSymb"] == sym) & (b["FinInstrmTp"] == "STO") & (b["XpryDt"].astype(str) == exp)]["NewBrdLotQty"]
    return int(x.iloc[0]) if len(x) else 0


def trade(c: pd.DataFrame, mins: dict, ticks: int = 1) -> dict:
    r0 = c.iloc[0]
    sym, day, nxt, t_in, spot, exp = r0.symbol, r0.day0, r0.to, hm(r0.t0, 1), float(r0.spot), r0.expiry
    out = {"symbol": sym, "day": day, "t0": r0.t0, "entry_time": t_in, "next_day": nxt, "expiry": exp, "spot": spot}
    ks = sorted(c["strike"].astype(float))
    k0 = min(ks, key=lambda k: (abs(k - spot), k))
    lot = lot_of(sym, day, exp)
    if not lot:
        return {**out, "excluded": "no_lot"}
    tk = tick(day)
    for k in ks[ks.index(k0):][:WALK]:
        m = mins.get((sym, day, float(k)))
        if m is None:
            continue
        e = m[(m["date"] == day) & (m["t"] == t_in)]
        if e.empty or not float(e["volume"].iloc[0]) > 0:
            continue
        px = round(float(e["c"].iloc[0]) + ticks * tk, 2)
        if px < FLOOR:
            return {**out, "excluded": "premium_below_2"}
        if px * lot < BAND[0]:
            return {**out, "excluded": "lot_below_600"}
        if px * lot > BAND[1]:
            continue
        x = m[(m["date"] == nxt) & (m["t"] == "09:15")]
        if x.empty:
            return {**out, "strike": k, "excluded": "no_next_0915_candle"}
        xt = tick(nxt)
        sell = max(xt, round(float(x["c"].iloc[0]) - ticks * xt, 2))
        cost = ch.leg("CE", "BUY", lot, px)["total"] + ch.leg("CE", "SELL", lot, sell)["total"]
        net = (sell - px) * lot - cost
        return {**out, "strike": k, "lot": lot, "entry": px, "exit": sell, "premium": round(px * lot, 2),
                "net": round(net, 2), "net_pct": round(net / (px * lot) * 100, 2), "excluded": ""}
    return {**out, "excluded": "no_strike_fits"}


def stats(g: pd.DataFrame) -> dict:
    if g.empty:
        return {"n": 0}
    return {"n": len(g), "win_pct": round((g["net"] > 0).mean() * 100, 1), "mean_pct": round(g["net_pct"].mean(), 2),
            "median_pct": round(g["net_pct"].median(), 2), "total_rs": round(g["net"].sum()),
            "t": clustered_t(g["net_pct"], g["day"]) if len(g) > 1 else None}


def main() -> None:
    con = pd.read_csv(RES / "S1_v10_bandintra_contracts.csv")
    mi = pd.read_csv(RES / "S1_v10_bandintra_minutes.csv")
    mi["date"], mi["t"] = mi["ts"].str[:10], mi["ts"].str[11:16]
    mins = {k: g for k, g in mi.groupby(["symbol", "day0", "strike"])}
    res = {}
    for ticks in (1, 2):
        res[ticks] = pd.DataFrame([trade(g, mins, ticks) for _, g in con.groupby(["symbol", "day0"], sort=False)])
    t = res[1]
    path = pd.read_csv(RES / "S1_intraday_results_path_cases.csv")[["symbol", "day", "next open raw", "next open"]]
    t = t.merge(path, on=["symbol", "day"], how="left")
    t.to_csv(RES / "S1_intraday_call_overnight_trades.csv", index=False)
    ok = t[t["excluded"] == ""]
    ok2 = res[2][res[2]["excluded"] == ""]
    half = lambda g: (g[g["day"] < "2026-01-01"], g[g["day"] >= "2026-01-01"])  # noqa: E731
    a1, b1 = half(ok)
    s, sa, sb = stats(ok), stats(a1), stats(b1)
    test = pd.DataFrame([
        {"test": "1 at least 60 trades", "value": s["n"], "pass": s["n"] >= 60},
        {"test": "2 mean > 0 and t >= 2 (1 tick)", "value": f"{s.get('mean_pct')} % / t {s.get('t')}",
         "pass": bool(s["n"] and s["mean_pct"] > 0 and (s["t"] or 0) >= 2)},
        {"test": "3a mean > 0 in 2024-25", "value": sa.get("mean_pct"), "pass": bool(sa["n"] and sa["mean_pct"] > 0)},
        {"test": "3b mean > 0 in 2026", "value": sb.get("mean_pct"), "pass": bool(sb["n"] and sb["mean_pct"] > 0)},
    ])
    verdict = "PASS (a candidate for paper, the user's decision)" if test["pass"].all() else "FAIL (closed with its numbers)"
    a2, b2 = half(ok2)
    tab = pd.DataFrame([{"costs": c, "period": p, **stats(g)} for c, gs in (("1 tick", (ok, a1, b1)), ("2 ticks", (ok2, a2, b2)))
                        for p, g in zip(("all", "2024-25", "2026"), gs)])
    stock = pd.DataFrame([{"group": lab, "n": len(g), "stock to next open, raw %": round(g["next open raw"].mean(), 3),
                           "adjusted %": round(g["next open"].mean(), 3), "option net %": round(g["net_pct"].mean(), 2)}
                          for lab, g in (("all trades", ok), ("winners", ok[ok["net"] > 0]), ("losers", ok[ok["net"] <= 0]))])
    excl = t["excluded"].replace("", "traded").value_counts().rename_axis("outcome").reset_index(name="cases")
    text = "\n".join([
        "# S1 · call one minute after a strong market-hours result, sold at the next open\n",
        "Pre-registered: strategies/S1_intraday_strong_call_overnight.md. Entry = the close of the minute after the "
        "announcement + 1 tick; exit = the next session's 09:15 minute close - 1 tick; real charges. 1 lot, Rs 600-8,000, "
        ">= Rs 2, from the strike nearest the spot upward. t is date-clustered.\n",
        f"## Test: **{verdict}**\n\n" + md(test),
        "## Results\n\n" + md(tab),
        "## Did the stock move? (stock from the entry minute to the next open, from the path study)\n\n" + md(stock),
        "## Cases\n\n" + md(excl),
        "Trades: data/results/S1_intraday_call_overnight_trades.csv.\n",
    ])
    (RES / "S1_intraday_call_overnight.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
