"""S1 fade · the three exit versions side by side on minute and second data (numbers only, descriptive).

    python -m scanner.fade_exit_versions <paper_ledger.json>

v10 = hold to the 15:19 / 15:20 close, no stop. v11 = v10 plus the -20 % stop (from 09:16 on the entry day). v12 = v11 plus the trail
(2 % below the high once +10 %): the live rule. Same trades, same entry as the live test (minutes: 09:16 open + 1 tick; seconds: the ask).
No new rule is introduced; this puts the existing versions on the same data.
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
from .fade_entry_time import run_min
from .fade_novolume_test import V10
from .fade_realistic_studies import SETS, TICK_CHANGE
from .fastio import read_table
from .stats import clustered_t

RES = ROOT / "data" / "results"
V11 = {"S": 20, "mode": "touch", "start": "09:17", "A": None, "D": 2, "re": False}
SEC_TIMES = ["09:15:10", "09:16:00"]


def minutes() -> tuple[pd.DataFrame, str]:
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
        c = g[(g["t"] >= "09:16") & (g["t"] <= "15:19")].reset_index(drop=True)
        first = c[c["t"] == "09:16"]
        if first.empty:
            continue
        tick = 0.05 if p.day0 < TICK_CHANGE else 0.01
        e = round(float(first["o"].iloc[0]) + tick, 2)
        if e < 2 or not 600 <= e * lot <= 8000:
            continue
        rows.append({"symbol": p.symbol, "day0": p.day0, "side": p.side, "entry": e, "lot": lot,
                     "v10": run_min(c, e, lot, p.side, p.day0, V10), "v11": run_min(c, e, lot, p.side, p.day0, V11),
                     "v12": run_min(c, e, lot, p.side, p.day0, V12)})
    df = pd.DataFrame(rows)
    tab = []
    for v in ("v10", "v11", "v12"):
        x = df[v]
        net = x / 100 * df["entry"] * df["lot"]
        h = [df.loc[df["day0"] < "2025-11", v].mean(), df.loc[df["day0"] >= "2025-11", v].mean()]
        tab.append({"exit": v, "n": len(x), "win %": round((x > 0).mean() * 100, 1), "mean %": round(x.mean(), 2), "median %": round(x.median(), 1),
                    "total Rs": round(net.sum()), "t": round(clustered_t(x.values, df["day0"].values) or 0, 2),
                    "half 1 mean": round(h[0], 2), "half 2 mean": round(h[1], 2)})
    pr = []
    for a, b in (("v11", "v10"), ("v12", "v11"), ("v12", "v10")):
        d = df[a] - df[b]
        pr.append({"pair": f"{a} minus {b}", "mean diff %": round(d.mean(), 2), "t": round(clustered_t(d.values, df["day0"].values) or 0, 2)})
    out = [f"## Minutes, Oct 2024 - Sep 2026: {len(df)} fade trades (09:16 open + 1 tick, price >= Rs 2, lot Rs 600-8,000)\n", md(pd.DataFrame(tab)),
           "\nPaired differences:\n", md(pd.DataFrame(pr)) + "\n"]
    return df, "\n".join(out)


def seconds(ledger_path: str) -> tuple[pd.DataFrame, str]:
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
        for T in SEC_TIMES:
            prior = [r for r in rs if r["t"] <= T and r.get("a")]
            if not prior:
                continue
            ask, bid0 = float(prior[-1]["a"]), float(prior[-1]["bc"])
            if ask < 2 or not 600 <= ask * lot <= 8000:
                continue
            res = {}
            for v, stop, trail in (("v10", False, False), ("v11", True, False), ("v12", True, True)):
                hi, on, sell = bid0, False, None
                for r in (x for x in rs if "15:20:00" >= x["t"] > T):
                    if stop and float(r["bl"]) <= 0.8 * ask:
                        sell = float(r["bl"])
                        break
                    hi = max(hi, float(r["bh"]))
                    if trail and hi >= 1.10 * ask:
                        on = True
                    if trail and on and float(r["bc"]) <= 0.98 * hi:
                        sell = float(r["bc"])
                        break
                if sell is None:
                    sell = float([x for x in rs if x["t"] <= "15:20:00"][-1]["bc"])
                net = (sell - ask) * lot - fst.ch.leg(side, "BUY", lot, ask)["total"] - fst.ch.leg(side, "SELL", lot, sell)["total"]
                res[v] = round(net / (ask * lot) * 100, 2)
            rows.append({"id": p["id"], "T": T, **res})
    df = pd.DataFrame(rows)
    tab = []
    for T in SEC_TIMES:
        d = df[df["T"] == T]
        for v in ("v10", "v11", "v12"):
            tab.append({"entry at": T, "exit": v, "n": len(d), "win %": round((d[v] > 0).mean() * 100), "mean %": round(d[v].mean(), 1), "median %": round(d[v].median(), 1)})
    live = pd.DataFrame(fade)
    out = [f"## Seconds, 26-30 Oct 2026: {len(fade)} live fade trades; buy at the ask, sell at the bid\n", md(pd.DataFrame(tab)),
           f"\nThe live account's own result on the same trades: mean {live.return_pct.mean():.1f} %, median {live.return_pct.median():.1f} %.\n"]
    return df, "\n".join(out)


def main() -> None:
    d1, t1 = minutes()
    d2, t2 = seconds(sys.argv[1])
    d1.to_csv(RES / "S1_fade_exit_versions_minutes.csv", index=False)
    d2.to_csv(RES / "S1_fade_exit_versions_seconds.csv", index=False)
    rep = "# S1 fade · exits v10, v11, v12 on minute and second data\n\nNumbers only, descriptive; no new rule.\n\n" + t1 + "\n" + t2
    (RES / "S1_fade_exit_versions.md").write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
