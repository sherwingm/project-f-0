"""S1 fade · what the 50-lot rule changed: the 22 new picks against the old picks, on 1-minute candles (numbers only).
Pre-registered: strategies/S1_fade_novolume.md."""
from __future__ import annotations

import sys

import pandas as pd

from .backtest_s1_v2 import md
from .build import ROOT
from .fade_cheap_dte import V12, _R
from .fade_realistic_studies import SETS, TICK_CHANGE
from .fade_stop_trail import one
from .fastio import read_table

RES = ROOT / "data" / "results"
TAG = sys.argv[1] if len(sys.argv) > 1 else "novolume"        # novolume: S1_fade_novolume_picks.csv ... ; vol100: S1_fade_vol100_picks.csv ...
PICKS = RES / ("S1_fade_novolume_picks.csv" if TAG == "novolume" else f"S1_fade_{TAG}_picks.csv")
MINS = RES / ("S1_v10_bandnovol_minutes.csv" if TAG == "novolume" else f"S1_v10_band{TAG}_minutes.csv")
OUT = "S1_fade_novolume" if TAG == "novolume" else f"S1_fade_{TAG}"
V10 = {"S": 10 ** 6, "mode": "touch", "start": "09:17", "A": 10 ** 6, "D": 2, "re": False}


def trade(m: pd.DataFrame, r: dict):
    m = m.copy()
    m["t"] = m["ts"].str[11:16]
    m = m[(m["t"] >= "09:16") & (m["t"] <= "15:19")].sort_values("ts").reset_index(drop=True)
    c16 = m[m["t"] == "09:16"]
    if c16.empty:
        return {"why": "no 09:16 candle"}
    tick = 0.05 if r["day0"] < TICK_CHANGE else 0.01
    eb = round(float(c16["o"].iloc[0]) + tick, 2)
    if eb < 2 or not 600 <= eb * r["lot"] <= 8000:
        return {"why": f"entry {eb} outside the live price/lot band"}
    x = _R(lot=r["lot"], side=r["side"], day0=r["day0"], entry_B=eb)
    return {"entry": eb, "v12": one(m, x, V12), "v10": one(m, x, V10),
            "lots_by_0916": round(m[m["t"] <= "09:16"]["volume"].sum() / r["lot"], 1)}


def main() -> None:
    picks = pd.read_csv(PICKS)
    new = read_table(MINS)
    old = pd.concat([read_table(RES / f"S1_v10_{s}_minutes.csv") for s in SETS]).drop_duplicates(["symbol", "day0", "side", "strike", "ts"])
    lots = {}
    for s in SETS:
        c = pd.read_csv(RES / f"S1_v10_{s}_contracts.csv")
        lots.update({(r.symbol, r.day0, r.side, float(r.strike)): int(r.lot) for r in c.itertuples()})
    nl = {}
    rows = []
    for p in picks.itertuples():
        mn = new[(new.symbol == p.symbol) & (new.day0 == p.day0) & (new.side == p.side) & (new.strike == p.strike)]
        lot = None
        # lot size of the stock from any old contract on the same stock (lots do not change within weeks)
        for (s_, d_, sd_, k_), l in lots.items():
            if s_ == p.symbol and abs((pd.Timestamp(d_) - pd.Timestamp(p.day0)).days) < 120:
                lot = l
                break
        row = {"symbol": p.symbol, "day0": p.day0, "side": p.side, "new_strike": p.strike, "old_strike": p.old_strike, "lots_day0_daily": p.lots_day0}
        if mn.empty or lot is None:
            row["new"] = "no candles" if mn.empty else "no lot size"
        else:
            row["new"] = trade(mn, {"day0": p.day0, "side": p.side, "lot": lot})
        if pd.notna(p.old_strike):
            mo = old[(old.symbol == p.symbol) & (old.day0 == p.day0) & (old.side == p.side) & (old.strike == p.old_strike)]
            row["old"] = "no candles" if mo.empty or lot is None else trade(mo, {"day0": p.day0, "side": p.side, "lot": lot})
        rows.append(row)
    flat = []
    for r in rows:
        f = {k: r[k] for k in ("symbol", "day0", "side", "new_strike", "old_strike", "lots_day0_daily")}
        for w in ("new", "old"):
            v = r.get(w)
            if isinstance(v, dict) and "v12" in v:
                f.update({f"{w}_entry": v["entry"], f"{w}_v12": round(v["v12"], 1), f"{w}_v10": round(v["v10"], 1), f"{w}_lots_by_0916": v["lots_by_0916"]})
            else:
                f[f"{w}_status"] = v["why"] if isinstance(v, dict) else v
        flat.append(f)
    df = pd.DataFrame(flat)
    df.to_csv(RES / f"{OUT}_trades.csv", index=False)
    both = df.dropna(subset=["new_v12", "old_v12"]) if "old_v12" in df and "new_v12" in df else df.iloc[0:0]
    n_new = df["new_v12"].notna().sum() if "new_v12" in df else 0
    rep = (f"# S1 fade · what the volume rule changed ({TAG})\n\nNumbers only. Pre-registered: strategies/S1_fade_{'novolume' if TAG == 'novolume' else TAG}.md. {len(df)} new picks: {n_new} testable on minutes; "
           f"{len(both)} with the old pick also testable on the same day. Net % of premium after charges and slippage.\n\n{md(df)}\n\n")
    if len(both):
        rep += ("## New strike against old strike, same signal and day\n\n"
                + md(pd.DataFrame([{"exit": e, "n": len(both), "new mean %": round(both[f'new_{e}'].mean(), 1), "new median %": round(both[f'new_{e}'].median(), 1),
                                    "new win %": round((both[f'new_{e}'] > 0).mean() * 100), "old mean %": round(both[f'old_{e}'].mean(), 1),
                                    "old median %": round(both[f'old_{e}'].median(), 1), "old win %": round((both[f'old_{e}'] > 0).mean() * 100)} for e in ("v12", "v10")])) + "\n")
    (RES / f"{OUT}.md").write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
