"""S1 fade, the live rule re-tested on every contract that has 1-minute candles (numbers only).

    python -m scanner.fade_minutes_retest

Rule = the live fade, nothing new: entry 09:16 candle open + 1 tick, price >= Rs 2, one lot Rs 600-8,000. Exits on 1-minute candles to 15:19:
v12 (live: -20 % stop, 2 % trail once +10 %) and v10 (hold to the 15:19 close). Contracts = every one with day-0 candles in the five band sets
(Oct 2024 - Aug 2026). Also reports intraday max up / dip (candle high / low) and the daily-data entry for the same trades.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from .backtest_s1_v2 import md
from .build import ROOT
from .fade_cheap_dte import V12, _R
from .fade_realistic_studies import HALF, SETS, TICK_CHANGE
from .fade_stop_trail import one
from .fastio import read_table
from .stats import clustered_t

RES = ROOT / "data" / "results"


def build() -> pd.DataFrame:
    rows, seen = [], set()
    for s in SETS:
        c = pd.read_csv(RES / f"S1_v10_{s}_contracts.csv")
        mins = read_table(RES / f"S1_v10_{s}_minutes.csv")
        mins["t"] = mins["ts"].str[11:16]
        by = {k: g.sort_values("ts") for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
        for r in c.itertuples():
            key = (r.symbol, r.day0, r.side, float(r.strike))
            if key in seen or key not in by:
                continue
            seen.add(key)
            m = by[key]
            m = m[(m["t"] >= "09:16") & (m["t"] <= "15:19")].reset_index(drop=True)
            c16 = m[m["t"] == "09:16"]
            if m.empty or c16.empty:
                continue
            tick = 0.05 if r.day0 < TICK_CHANGE else 0.01
            eb = round(float(c16["o"].iloc[0]) + tick, 2)
            lot = int(r.lot)
            v12 = one(m, _R(lot=lot, side=r.side, day0=r.day0, entry_B=eb), V12)
            v10 = one(m, _R(lot=lot, side=r.side, day0=r.day0, entry_B=eb), {"S": 10 ** 6, "mode": "touch", "start": "09:17", "A": 10 ** 6, "D": 2, "re": False})
            rows.append({"set": s, "symbol": r.symbol, "day0": r.day0, "side": r.side, "lot": lot, "entry_B": eb,
                         "lot_ok": 600 <= eb * lot <= 8000, "half": HALF(r.day0), "v12_net_pct": v12,
                         "v10_net_pct": v10, "max_up_pct": (m["h"].max() / eb - 1) * 100, "max_dip_pct": (m["l"].min() / eb - 1) * 100,
                         "daily_entry": getattr(r, "entry_price", None)})
    return pd.DataFrame(rows)


def st(g: pd.DataFrame, col: str, **lab) -> dict:
    if g.empty:
        return {**lab, "n": 0}
    x = g[col]
    net = x / 100 * g["entry_B"] * g["lot"]
    top3 = net.sort_values(ascending=False).head(3).sum()
    return {**lab, "n": len(g), "win %": round((x > 0).mean() * 100, 1), "mean %": round(x.mean(), 2), "median %": round(x.median(), 1),
            "total Rs": round(net.sum()), "t": None if len(g) < 2 else round(clustered_t(x, g["day0"]) or 0, 2),
            "mean ex top3 %": round(x.sort_values(ascending=False).iloc[3:].mean(), 2) if len(g) > 3 else None,
            "max up mean/median %": f"{g['max_up_pct'].mean():.0f} / {g['max_up_pct'].median():.0f}",
            "max dip mean/median %": f"{g['max_dip_pct'].mean():.0f} / {g['max_dip_pct'].median():.0f}"}


def main() -> None:
    t = build()
    t.to_csv(RES / "S1_fade_minutes_retest_trades.csv", index=False)
    live = t[t["lot_ok"] & (t["entry_B"] >= 2)]
    rows = []
    for col, nm in (("v12_net_pct", "v12 (live)"), ("v10_net_pct", "v10 (hold to 15:19)")):
        for h in ("all", "Oct24-Oct25", "Nov25-Sep26"):
            g = live if h == "all" else live[live["half"] == h]
            rows.append(st(g, col, exit=nm, period=h))
        for sd in ("PE", "CE"):
            rows.append(st(live[live["side"] == sd], col, exit=nm, period=f"all, {sd} only"))
    rep = ("# S1 fade · the live rule on every contract with 1-minute candles\n\nNumbers only. Entry 09:16 open + 1 tick, price >= Rs 2, lot Rs 600-8,000, "
           f"candles to 15:19. {len(t)} contracts with a 09:16 candle, {len(live)} pass the live rule. Max up / dip are candle high / low as % of the entry.\n\n"
           + md(pd.DataFrame(rows)) + "\n")
    (RES / "S1_fade_minutes_retest.md").write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
