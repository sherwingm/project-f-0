"""S1 v10 fade · cheap-option bands on DAILY data, 2022-24: before (15:20 exit) vs after (B30) (numbers only).

    python -m scanner.fade_band_daily

strategies/S1_v10_band12_trail.md, addendum 2. No minute data exists before the Oct 2024 expiries, so the day-0 option
open / high / low / close (cached NSE files, in the contract lists) stand in. B30 = hold until +100 %, then a 30 %
trailing stop: daily data cannot order the prices inside a day, so it is a range (optimistic / pessimistic). The same
calculation on 2025 is set beside the minute-data results as a check. Writes data/results/S1_v10_band_daily_2022_24.md.
"""
from __future__ import annotations

import pandas as pd

from server import charges as ch

from .backtest_s1_v2 import md
from .build import ROOT
from .fade_band050 import costs_real, down_tick, up_tick
from .stats import clustered_t

RES = ROOT / "data" / "results"
TRAIL, MULT = 0.30, 2.0
SETS = {"Rs 1-2": {"2022-24": "S1_v10_band12_contracts_2022_24.csv", "2025": "S1_v10_band12_contracts.csv"},
        "Rs 0.50-1": {"2022-24": "S1_v10_band050_contracts_2022_24.csv", "2025": "S1_v10_band050_contracts.csv"}}
MINUTE_2025 = {"Rs 1-2": ("S1_v10_band12_trades.csv", "B30"), "Rs 0.50-1": ("S1_v10_band050_t100_trades.csv", "B30")}


def exits(r, tick: float, cost: float) -> dict[str, float]:
    """Exit prices for one trade: before (15:20), after optimistic, after pessimistic."""
    entry = round(r.bhav_open + cost, 2)
    before = max(0.0, r.bhav_close - cost)
    target = up_tick(entry * MULT, tick)
    if r.bhav_high >= target + tick - 1e-9:
        opt = max(r.bhav_close, down_tick(r.bhav_high * (1 - TRAIL), tick)) - cost
        pes = min(r.bhav_close, down_tick(target * (1 - TRAIL), tick)) - cost
    else:
        opt = pes = before
    return {"entry": entry, "before": round(before, 2), "after_opt": round(max(0.0, opt), 2),
            "after_pes": round(max(0.0, pes), 2), "armed": r.bhav_high >= target + tick - 1e-9}


def priced(c: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in c.itertuples():
        tick, cost = costs_real(r.day0)                          # 2022-24: Rs 0.05 tick, Rs 0.10 a side
        x = exits(r, tick, cost)
        row = {"symbol": r.symbol, "day0": r.day0, "side": r.side, "lot": int(r.lot), "armed": x["armed"]}
        for k in ("before", "after_opt", "after_pes"):
            c_ = ch.leg(r.side, "BUY", int(r.lot), x["entry"])["total"] + (
                ch.leg(r.side, "SELL", int(r.lot), x[k])["total"] if x[k] > 0 else 0.0)
            net = (x[k] - x["entry"]) * r.lot - c_
            row[f"{k}_net"], row[f"{k}_pct"] = round(net, 2), round(net / (x["entry"] * r.lot) * 100, 3)
        rows.append(row)
    return pd.DataFrame(rows)


def stats(net: pd.Series, pct: pd.Series, day0: pd.Series, order: pd.Series) -> dict:
    if not len(net):
        return {"n": 0}
    cum = net.loc[order].cumsum()
    return {"n": len(net), "win_pct": round((net > 0).mean() * 100, 1), "mean_pct": round(pct.mean(), 2),
            "median_pct": round(pct.median(), 2), "total_rs": round(net.sum()),
            "max_dd_rs": round(float((cum.cummax().clip(lower=0) - cum).max())), "t": clustered_t(pct, day0)}


def table(t: pd.DataFrame) -> pd.DataFrame:
    order = t.sort_values(["day0", "symbol"]).index
    return pd.DataFrame([{"exit": lab, **stats(t[f"{k}_net"], t[f"{k}_pct"], t["day0"], order)}
                         for k, lab in (("before", "BEFORE: 15:20 exit"), ("after_opt", "AFTER: B30, optimistic"),
                                        ("after_pes", "AFTER: B30, pessimistic"))])


def main() -> None:
    v10 = pd.read_csv(RES / "S1_v10_trades_2022_24.csv")
    v10 = v10[(v10["entry"] == "open") & (v10["e1_excluded"].fillna("") == "") & (v10["entry_price"] >= 2)]
    parts, checks, combos = [], [], []
    for band, files in SETS.items():
        t = priced(pd.read_csv(RES / files["2022-24"]))
        tab = table(t)
        tab.insert(0, "band", band)
        parts.append((band, t, tab))
        c25 = priced(pd.read_csv(RES / files["2025"]))
        c25 = c25[c25["day0"] <= "2025-12-31"]
        mt = pd.read_csv(RES / MINUTE_2025[band][0])
        mt = mt[mt["day0"] <= "2025-12-31"]
        for lab, k, var in (("15:20", "before", "baseline 15:20"), ("B30", None, MINUTE_2025[band][1])):
            m = mt[mt["variant"] == var]
            row = {"band": band, "exit": lab, "minute data (real)": round(m["net"].sum()), "minute n": len(m)}
            if k:
                row["daily"] = round(c25["before_net"].sum())
            else:
                row["daily optimistic"], row["daily pessimistic"] = round(c25["after_opt_net"].sum()), round(c25["after_pes_net"].sum())
            row["daily n"] = len(c25)
            checks.append(row)
        for k, lab in (("before", "v10 + band, BEFORE (15:20)"), ("after_opt", "v10 + band, AFTER optimistic"),
                       ("after_pes", "v10 + band, AFTER pessimistic")):
            net = pd.concat([v10["e1_net"], t[f"{k}_net"]], ignore_index=True)
            combos.append({"band": band, "set": lab, "n": len(net), "total_rs": round(net.sum()),
                           "win_pct": round((net > 0).mean() * 100, 1)})
    v = {"band": "-", "set": "v10 as today (Rs 2+ only)", "n": len(v10), "total_rs": round(v10["e1_net"].sum()),
         "win_pct": round((v10["e1_net"] > 0).mean() * 100, 1)}
    by_year = []
    for band, t, _ in parts:
        for y in ("2022", "2023", "2024"):
            g = t[t["day0"].str[:4] == y]
            by_year.append({"band": band, "year": y, "n": len(g), "before_rs": round(g["before_net"].sum()),
                            "after_opt_rs": round(g["after_opt_net"].sum()), "after_pes_rs": round(g["after_pes_net"].sum()),
                            "armed_pct": round(g["armed"].mean() * 100, 1) if len(g) else None})
    text = "\n".join([
        "# S1 v10 fade · cheap-option bands, 2022-24 on daily data: before (15:20) vs after (B30)\n",
        "Numbers only. strategies/S1_v10_band12_trail.md, addendum 2. Daily option open / high / low / close (no minute "
        "data exists before Oct 2024). Entry = day 0's open + Rs 0.10; before = close - Rs 0.10; after = B30 (hold until "
        "+100 %, then a 30 % trailing stop) as a range, because daily data cannot order the prices inside the day. Real "
        "charges. v10's own trades use the backtest's existing costs. t date-clustered.\n",
        "## Before vs after, 2022-24\n\n" + md(pd.concat([p[2] for p in parts], ignore_index=True)),
        "## By year\n\n" + md(pd.DataFrame(by_year)),
        "## With v10's Rs 2+ trades (2022-24)\n\n" + md(pd.DataFrame([v, *combos])),
        "## Check of the daily method on 2025 (where minute data exists)\n\n" + md(pd.DataFrame(checks))
        + "\n\nThe daily 'before' buys at the open; the minute test bought at the 09:15 minute's close (after the opening "
          "spike), so the daily numbers are expected to look better. 2025 Nov-Dec uses the Rs 0.01 tick and Rs 0.04 a side.\n",
    ])
    (RES / "S1_v10_band_daily_2022_24.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
