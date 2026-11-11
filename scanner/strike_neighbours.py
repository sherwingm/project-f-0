"""Does a nearer or farther strike do better than the walk's pick? (numbers only; fade and Arm A/B, 1-minute candles)

    python -m scanner.strike_neighbours

Pre-registered: strategies/S1_strike_neighbours.md. Offsets in LISTED strikes: -2, -1 nearer the money (dearer), 0 = the pick, +1, +2 farther (cheaper).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import backtest_s1_v4 as v4
from .armab_minutes import calendar, iso, run_one
from .backtest_s1_v2 import md
from .build import ROOT
from .fade_novolume_test import trade
from .fade_realistic_studies import SETS
from .fastio import read_table
from .stats import clustered_t

RES = ROOT / "data" / "results"
OFFS = (-2, -1, 0, 1, 2)


def summ(df: pd.DataFrame, col: str, off) -> dict:
    d = df[df.offset == off].dropna(subset=[col])
    if d.empty:
        return {"offset": off, "buyable": 0}
    x = d[col]
    net = x / 100 * d["entry"] * d["lot"]
    t = clustered_t(x.values, d["day0"].values) if len(d) > 1 else None
    return {"offset": off, "buyable": len(d), "win %": round((x > 0).mean() * 100, 1), "mean %": round(x.mean(), 1),
            "median %": round(x.median(), 1), "total Rs": round(net.sum()), "t": None if t is None else round(t, 2)}


def paired(df: pd.DataFrame, col: str, off: int) -> dict:
    a = df[df.offset == 0].dropna(subset=[col])[["key", "day0", col]].rename(columns={col: "p"})
    b = df[df.offset == off].dropna(subset=[col])[["key", col]].rename(columns={col: "n"})
    m = a.merge(b, on="key")
    if len(m) < 2:
        return {"offset": off, "pairs": len(m)}
    d = m["n"] - m["p"]
    t = clustered_t(d.values, m["day0"].values)
    h1, h2 = d[m["day0"] < "2025-11"], d[m["day0"] >= "2025-11"]
    return {"offset": off, "pairs": len(m), "mean diff %": round(d.mean(), 1), "t": None if t is None else round(t, 2),
            "half1 diff": None if h1.empty else round(h1.mean(), 1), "half2 diff": None if h2.empty else round(h2.mean(), 1)}


def fade() -> tuple[pd.DataFrame, str]:
    mp = pd.read_csv(RES / "S1_nbr_fade_map.csv")
    nb = read_table(RES / "S1_v10_bandnbrfade_minutes.csv")
    pk = pd.concat([read_table(RES / f"S1_v10_{s}_minutes.csv") for s in SETS]).drop_duplicates(["symbol", "day0", "side", "strike", "ts"])
    lots = {}
    for s in SETS:
        c = pd.read_csv(RES / f"S1_v10_{s}_contracts.csv")
        lots.update({(r.symbol, r.day0, r.side, float(r.strike)): int(r.lot) for r in c.itertuples()})
    rows = []
    picks = mp.drop_duplicates(["symbol", "day0", "side"])
    for p in picks.itertuples():
        lot = lots.get((p.symbol, p.day0, p.side, float(p.pick_strike)))
        if lot is None:
            continue
        key = f"{p.symbol}|{p.day0}|{p.side}"
        for off, strike, src in [(0, p.pick_strike, pk)] + [(r.offset, r.strike, nb) for r in mp[(mp.symbol == p.symbol) & (mp.day0 == p.day0) & (mp.side == p.side)].itertuples()]:
            m = src[(src.symbol == p.symbol) & (src.day0 == p.day0) & (src.side == p.side) & (src.strike == strike)]
            res = trade(m, {"day0": p.day0, "side": p.side, "lot": lot}) if len(m) else {"why": "no candles"}
            rows.append({"key": key, "day0": p.day0, "side": p.side, "offset": off, "lot": lot,
                         "entry": res.get("entry"), "v12": res.get("v12"), "v10": res.get("v10"), "why": res.get("why")})
    df = pd.DataFrame(rows)
    out = ["## Fade (326 live-rule trades; entry 09:16 open + 1 tick; v12 = live exit)\n"]
    for col, nm in (("v12", "v12 (live)"), ("v10", "v10 (hold to 15:19)")):
        out.append(f"### {nm}\n\n" + md(pd.DataFrame([summ(df, col, o) for o in OFFS])) + "\n\nPaired against the pick:\n\n"
                   + md(pd.DataFrame([paired(df, col, o) for o in OFFS if o])) + "\n")
    why = df[df.offset != 0].groupby(["offset", df.why.fillna("buyable").str.replace(r"entry [\d.]+ outside.*", "price/lot band", regex=True)]).size().unstack(fill_value=0)
    out.append("### Why a neighbour was not buyable\n\n" + md(why.reset_index()) + "\n")
    for sd in ("PE", "CE"):
        out.append(f"### v12, {sd} only\n\n" + md(pd.DataFrame([summ(df[df.side == sd], "v12", o) for o in OFFS])) + "\n")
    return df, "\n".join(out)


def arms() -> tuple[pd.DataFrame, str]:
    cal = [iso(x) for x in calendar()]
    mp = pd.read_csv(RES / "S1_nbr_ab_map.csv")
    tr = pd.read_csv(RES / "S1_armb_hold_and_nifty_trades.csv")
    tr = tr[(tr.variant == "LIVE") & tr.arm.isin(["A", "B"]) & (tr.expiry >= "2024-10-01")].drop_duplicates(["symbol", "signal_date", "strike", "expiry"])
    nb, pk = read_table(RES / "S1_v10_bandnbrab_minutes.csv"), read_table(RES / "S1_v10_bandarmab2_minutes.csv")

    def paths(m):
        m = m.copy()
        m["dt"] = pd.to_datetime(m["ts"])
        m["d"], m["t"] = m["dt"].dt.strftime("%Y-%m-%d"), m["dt"].dt.strftime("%H:%M")
        m = m.sort_values("dt")
        return {(s, d0, float(k)): {d: x for d, x in g.groupby("d")} for (s, d0, k), g in m.groupby(["symbol", "day0", "strike"])}

    pp, nn = paths(pk), paths(nb)
    rows = []
    for r in tr.itertuples():
        key = f"{r.symbol}|{r.signal_date}"
        slip = v4.SLIPPAGE.get(r.category, v4.SLIPPAGE["unknown"])
        cands = [(0, float(r.strike), pp)] + [(x.offset, float(x.strike), nn) for x in mp[(mp.symbol == r.symbol) & (mp.day0 == r.signal_date) & (mp.pick_strike == r.strike)].itertuples()]
        for off, strike, src in cands:
            days = src.get((r.symbol, r.signal_date, strike))
            rec = {"key": key, "day0": r.signal_date, "offset": off, "lot": r.lot, "arm": r.arm}
            for var in ("LIVE-CLOSE", "H8"):
                res = run_one(days, cal, r.entry_date, r.expiry, var)[0] if days else "no_candles"
                if isinstance(res, dict) and 600 <= res["entry"] * r.lot <= 8000 and res["entry"] >= 2:
                    _, _, net = v4.net_of(res["entry"], res["exit_price"], r.lot, slip)
                    rec[var] = net / (res["entry"] * r.lot) * 100
                    rec["entry"] = res["entry"]
            rows.append(rec)
    df = pd.DataFrame(rows)
    out = ["## Arm A/B (Oct 2024 on; entry 09:16 open + 1 tick)\n"]
    for col in ("LIVE-CLOSE", "H8"):
        out.append(f"### {col}\n\n" + md(pd.DataFrame([summ(df, col, o) for o in OFFS])) + "\n\nPaired against the pick:\n\n"
                   + md(pd.DataFrame([paired(df, col, o) for o in OFFS if o])) + "\n")
    return df, "\n".join(out)


def main() -> None:
    f, ft = fade()
    a, at = arms()
    f.to_csv(RES / "S1_strike_neighbours_fade_trades.csv", index=False)
    a.to_csv(RES / "S1_strike_neighbours_arms_trades.csv", index=False)
    rep = "# S1 · nearer or farther strike than the walk's pick\n\nNumbers only. Pre-registered: strategies/S1_strike_neighbours.md.\n\n" + ft + "\n" + at
    (RES / "S1_strike_neighbours.md").write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
