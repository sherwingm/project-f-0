"""S1 fade · v11's -20 % stop plus a trailing stop, start A and gap D from 2 % (numbers only).

    python -m scanner.fade_trail20_grid

strategies/S1_fade_trail20_grid.md fixes every choice; mechanics from scanner.fade_stop_trail. Writes
data/results/S1_fade_trail20_grid.md.
"""
from __future__ import annotations

import pandas as pd

from .backtest_s1_v2 import md
from .build import ROOT
from .fade_stop_trail import SPLIT, one
from .stats import clustered_t

RES = ROOT / "data" / "results"


def main() -> None:
    t = pd.read_csv(RES / "S1_fade_realistic_entry_trades.csv")
    t = t[t["B_excluded"].fillna("") == ""].reset_index(drop=True)
    con = pd.read_csv(RES / "S1_v10_bandv10_contracts.csv")
    strike = {(r.symbol, r.day0, r.side): float(r.strike) for r in con.itertuples()}
    mins = pd.read_csv(RES / "S1_v10_bandv10_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    by = {k: g.sort_values("ts") for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
    cs = []
    for r in t.itertuples():
        g = by[(r.symbol, r.day0, r.side, strike[(r.symbol, r.day0, r.side)])]
        cs.append(g[(g["t"] >= "09:16") & (g["t"] <= "15:19")].reset_index(drop=True))
    base = {"name": "v11", "S": 20, "mode": "touch", "start": "09:17", "A": None, "D": None, "re": False}
    vs = [base] + [{"name": f"stop 20 + trail start {a} gap {d}", "S": 20, "mode": "touch", "start": "09:17", "A": a,
                    "D": d, "re": False} for a in (2, 5, 10, 20) for d in (2, 5, 10, 15, 20)]
    res = pd.DataFrame({v["name"]: [one(c, r, v) for c, r in zip(cs, t.itertuples())] for v in vs})
    res["day0"] = t["day0"]
    tr, te = res[res["day0"] < SPLIT], res[res["day0"] >= SPLIT]
    rows = []
    for v in vs:
        n = v["name"]
        d = te[n] - te["v11"]
        rows.append({"variant": n, "train mean %": round(tr[n].mean(), 2), "train t": clustered_t(tr[n], tr["day0"]),
                     "test mean %": round(te[n].mean(), 2), "test t": clustered_t(te[n], te["day0"]),
                     "win % (all)": round((res[n] > 0).mean() * 100, 1), "test diff vs v11": round(d.mean(), 2),
                     "diff t": clustered_t(d, te["day0"]) if d.abs().sum() else None, "all mean %": round(res[n].mean(), 2),
                     "all t": clustered_t(res[n], res["day0"])})
    tab = pd.DataFrame(rows)
    grid = tab[tab["variant"] != "v11"].sort_values("train mean %", ascending=False)
    best = grid.iloc[0]
    passed = bool(best["test mean %"] > 0 and best["test diff vs v11"] > 0 and (best["diff t"] or 0) >= 2)
    heat = pd.DataFrame([{"start A %": a, **{f"gap {d} %": round(res[f'stop 20 + trail start {a} gap {d}'].mean(), 2)
                                           for d in (2, 5, 10, 15, 20)}} for a in (2, 5, 10, 20)])
    text = "\n".join([
        "# S1 fade · the -20 % stop plus a trailing stop (start and gap from 2 %), realistic entry\n",
        f"Pre-registered: strategies/S1_fade_trail20_grid.md. {len(t)} trades; train before {SPLIT} ({len(tr)}), test from "
        f"it ({len(te)}). Net % of premium after charges; t date-clustered. The test half is not fully fresh (see the pre-registration).\n",
        f"## The test: **{'PASS' if passed else 'FAIL'}**\n\nTrain winner: **{best['variant']}**: test mean {best['test mean %']} % "
        f"(t {best['test t']}), vs v11 {best['test diff vs v11']:+} points (t {best['diff t']}).\n",
        "## All trades: mean net % by start and gap (v11 = " + f"{tab.iloc[0]['all mean %']} %)\n\n" + md(heat),
        "## Every variant\n\n" + md(pd.concat([tab.iloc[[0]], grid])),
    ])
    (RES / "S1_fade_trail20_grid.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
