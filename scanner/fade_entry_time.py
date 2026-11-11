"""S1 fade · entry at 09:15 or 09:16? Minutes (Oct 2024 - Sep 2026) and seconds (26-30 Oct 2026). Numbers only.

    python -m scanner.fade_entry_time <paper_ledger.json>

Pre-registered: strategies/S1_fade_entry_0915_0916.md.
"""
from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict

import pandas as pd

from . import fade_stop_trail as fst
from .backtest_s1_v2 import md
from .build import ROOT
from .fade_cheap_dte import V12
from .fade_novolume_test import V10
from .fade_realistic_studies import SETS, TICK_CHANGE
from .fastio import read_table
from .stats import clustered_t

RES = ROOT / "data" / "results"
TIMES = ["09:15:01", "09:15:10", "09:15:30", "09:15:55", "09:16:00", "09:16:30", "09:17:00"]


def run_min(c: pd.DataFrame, e: float, lot: int, side: str, day0: str, v: dict) -> float:
    """v12 / v10 on candles that START with the entry candle; checks begin with the next candle."""
    tick = 0.05 if day0 < fst.SPLIT else 0.01

    def net(buy, sell):
        return (sell - buy) * lot - fst.ch.leg(side, "BUY", lot, buy)["total"] - fst.ch.leg(side, "SELL", lot, sell)["total"]
    sell, _ = fst.walk(c, e, tick, v, 1)
    return round(net(e, sell) / (e * lot) * 100, 3)


def part1() -> tuple[pd.DataFrame, str]:
    mp = pd.read_csv(RES / "S1_nbr_fade_map.csv").drop_duplicates(["symbol", "day0", "side"])
    pk = pd.concat([read_table(RES / f"S1_v10_{s}_minutes.csv") for s in SETS]).drop_duplicates(["symbol", "day0", "side", "strike", "ts"])
    pk["t"] = pk["ts"].str[11:16]
    by = {k: g.sort_values("ts") for k, g in pk.groupby(["symbol", "day0", "side", "strike"])}
    lots = {}
    for s in SETS:
        c = pd.read_csv(RES / f"S1_v10_{s}_contracts.csv")
        lots.update({(r.symbol, r.day0, r.side, float(r.strike)): int(r.lot) for r in c.itertuples()})
    rows = []
    for p in mp.itertuples():
        key = (p.symbol, p.day0, p.side, float(p.pick_strike))
        g, lot = by.get(key), lots.get(key)
        if g is None or not lot:
            continue
        tick = 0.05 if p.day0 < TICK_CHANGE else 0.01
        rec = {"symbol": p.symbol, "day0": p.day0, "side": p.side, "lot": lot}
        for nm, t0 in (("E15", "09:15"), ("E16", "09:16")):
            c = g[(g["t"] >= t0) & (g["t"] <= "15:19")].reset_index(drop=True)
            first = c[c["t"] == t0]
            if first.empty:
                continue
            e = round(float(first["o"].iloc[0]) + tick, 2)
            if e < 2 or not 600 <= e * lot <= 8000:
                continue
            rec[f"{nm}_entry"] = e
            rec[f"{nm}_v12"] = run_min(c, e, lot, p.side, p.day0, V12)
            rec[f"{nm}_v10"] = run_min(c, e, lot, p.side, p.day0, V10)
            if nm == "E15":
                rec["range15_pct"] = (float(first["h"].iloc[0]) / float(first["l"].iloc[0]) - 1) * 100
        rows.append(rec)
    df = pd.DataFrame(rows)
    both = df.dropna(subset=["E15_v12", "E16_v12"]).copy()
    out = [f"## Part 1 · minutes, {len(df)} fade trades; {len(both)} buyable at BOTH 09:15 and 09:16\n"]
    tab = []
    for ex in ("v12", "v10"):
        d = both[f"E15_{ex}"] - both[f"E16_{ex}"]
        t = clustered_t(d.values, both["day0"].values)
        for nm in ("E15", "E16"):
            x = both[f"{nm}_{ex}"]
            tab.append({"exit": ex, "entry": nm, "n": len(x), "win %": round((x > 0).mean() * 100, 1), "mean %": round(x.mean(), 2),
                        "median %": round(x.median(), 1), "t": round(clustered_t(x.values, both["day0"].values) or 0, 2)})
        h1, h2 = d[both["day0"] < "2025-11"], d[both["day0"] >= "2025-11"]
        tab.append({"exit": ex, "entry": "E15 minus E16 (paired)", "n": len(d), "mean %": round(d.mean(), 2), "t": None if t is None else round(t, 2),
                    "half1 diff": round(h1.mean(), 2), "half2 diff": round(h2.mean(), 2)})
    out.append(md(pd.DataFrame(tab)) + "\n")
    gap = (both.E15_entry / both.E16_entry - 1) * 100
    out.append(f"Entry price E15 / E16 - 1: mean {gap.mean():+.1f} %, median {gap.median():+.1f} %; "
               f"the 09:15 candle's range: mean {df.range15_pct.mean():.0f} %, median {df.range15_pct.median():.0f} % of its low; "
               f"trades with no usable 09:15 candle or entry: {int(df.E15_v12.isna().sum())}, with no usable 09:16 candle or entry: {int(df.E16_v12.isna().sum())}.\n")
    return df, "\n".join(out)


def part2(ledger_path: str) -> tuple[pd.DataFrame, str]:
    L = json.load(open(ledger_path, encoding="utf-8"))
    fade = [p for p in L["closed"] if (p.get("rule") or {}).get("strategy") == "fade" and "2026-10-26" <= p["opened_at"][:10] <= "2026-10-30"]
    data = defaultdict(list)
    for f in sorted(glob.glob(str(ROOT / "data/candles_1s/*.jsonl"))):
        day = f[-16:-6]
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            data[(day, r["ts"])].append(r)
    rows = []
    for p in fade:
        day, sym, lot, side = p["opened_at"][:10], p["tradingsymbol"], int(p["lot_size"]), p["instrument"]
        rs = sorted(data[(day, sym)], key=lambda r: r["t"])
        for T in TIMES:
            prior = [r for r in rs if r["t"] <= T and r.get("a")]
            if not prior:
                rows.append({"id": p["id"], "T": T, "why": "no ask"})
                continue
            ask, bid0 = float(prior[-1]["a"]), float(prior[-1]["bc"])
            if ask < 2 or not 600 <= ask * lot <= 8000:
                rows.append({"id": p["id"], "T": T, "why": "outside Rs 2 / lot band"})
                continue
            hi, on, sell = bid0, False, None
            for r in (x for x in rs if "15:20:00" >= x["t"] > T):
                if float(r["bl"]) <= 0.8 * ask:
                    sell = float(r["bl"])
                    break
                hi = max(hi, float(r["bh"]))
                if hi >= 1.10 * ask:
                    on = True
                if on and float(r["bc"]) <= 0.98 * hi:
                    sell = float(r["bc"])
                    break
            if sell is None:
                last = [x for x in rs if x["t"] <= "15:20:00"]
                sell = float(last[-1]["bc"])
            net = (sell - ask) * lot - fst.ch.leg(side, "BUY", lot, ask)["total"] - fst.ch.leg(side, "SELL", lot, sell)["total"]
            rows.append({"id": p["id"], "day": day, "T": T, "ask": ask, "spread_pct": round((ask - bid0) / ask * 100, 1),
                         "net_pct": round(net / (ask * lot) * 100, 2), "net_rs": round(net)})
    df = pd.DataFrame(rows)
    ok = df.dropna(subset=["net_pct"])
    tab = []
    for T in TIMES:
        d = ok[ok["T"] == T]
        tab.append({"entry time": T, "buyable": len(d), "of": len(fade), "win %": round((d.net_pct > 0).mean() * 100) if len(d) else None,
                    "mean %": round(d.net_pct.mean(), 1) if len(d) else None, "median %": round(d.net_pct.median(), 1) if len(d) else None,
                    "total Rs": round(d.net_rs.sum()) if len(d) else None, "mean spread paid %": round(d.spread_pct.mean(), 1) if len(d) else None})
    live = pd.DataFrame(fade)
    fills = sorted(p["opened_at"][11:19] for p in fade)
    out = [f"## Part 2 · seconds, 26-30 Oct 2026, {len(fade)} live fade trades; buy at the ask, sell at the bid\n", md(pd.DataFrame(tab)) + "\n",
           f"The live account's own result on the same {len(fade)} trades: mean {live.return_pct.mean():.1f} %, median {live.return_pct.median():.1f} %; "
           f"live fills between {fills[0]} and {fills[-1]} (median {fills[len(fills) // 2]}).\n"]
    if "why" in df:
        why = df[df["why"].notna()].groupby(["T", "why"]).size().reset_index(name="n")
        if len(why):
            out.append("Not buyable:\n\n" + md(why) + "\n")
    return df, "\n".join(out)


def main() -> None:
    d1, t1 = part1()
    d2, t2 = part2(sys.argv[1])
    d1.to_csv(RES / "S1_fade_entry_time_minutes.csv", index=False)
    d2.to_csv(RES / "S1_fade_entry_time_seconds.csv", index=False)
    rep = "# S1 fade · entry at 09:15 or 09:16\n\nNumbers only. Pre-registered: strategies/S1_fade_entry_0915_0916.md.\n\n" + t1 + "\n" + t2
    (RES / "S1_fade_entry_time.md").write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
