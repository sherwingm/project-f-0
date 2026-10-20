"""S1 fade · the floor, band, target and Arm-A-filter studies re-run with the realistic entry (numbers only).

    python -m scanner.fade_realistic_studies

strategies/S1_fade_realistic_entry_studies.md fixes every choice. Entry A = the old backtest entry (day-0 open + 1 tick),
B = the 09:16 candle's open + 1 tick; the same exit code for both. Writes data/results/S1_fade_realistic_studies.md and
_trades.csv.
"""
from __future__ import annotations

import math

import pandas as pd

from server import charges as ch

from .backtest_s1_v2 import md
from .build import ROOT
from .fade_armA_filter import Prices, flag
from .stats import clustered_t

RES = ROOT / "data" / "results"
TICK_CHANGE = "2025-11-03"
SETS = ("bandv10", "band12", "band12q4", "band050", "band050q4")
TARGETS = (0.25, 0.50, 1.00, 2.00)
HALF = lambda d: "Oct24-Oct25" if d < TICK_CHANGE else "Nov25-Sep26"        # noqa: E731


def exit_price(m: pd.DataFrame, entry: float, tick: float, start: str, stop_on: bool, target: float | None) -> float:
    """First candle from `start` that hits the stop (if on) or the target decides; else the 15:19 close - 1 tick."""
    stop = 0.80 * entry
    tp = math.ceil(round(entry * (1 + target) / tick, 6)) * tick if target else None
    for r in m[m["t"] >= start].itertuples():
        if stop_on and r.l <= stop + 1e-9:
            return max(tick, round(min(stop, r.o) - tick, 2))
        if tp is not None and r.h >= tp + tick - 1e-9:
            return round(tp, 2)
    return max(tick, round(float(m["c"].iloc[-1]) - tick, 2))


def nets(m: pd.DataFrame, side: str, lot: int, entry: float, tick: float, start: str) -> dict:
    def net(sell: float) -> float:
        return (sell - entry) * lot - ch.leg(side, "BUY", lot, entry)["total"] - ch.leg(side, "SELL", lot, sell)["total"]
    out = {"v10": net(exit_price(m, entry, tick, start, False, None)), "v11": net(exit_price(m, entry, tick, start, True, None))}
    for T in TARGETS:
        out[f"T{T * 100:g}"] = net(exit_price(m, entry, tick, start, False, T))
        out[f"T{T * 100:g}+stop"] = net(exit_price(m, entry, tick, start, True, T))
    return {k: round(v, 2) for k, v in out.items()}


def build() -> pd.DataFrame:
    rows = []
    for s in SETS:
        c = pd.read_csv(RES / f"S1_v10_{s}_contracts.csv")
        mins = pd.read_csv(RES / f"S1_v10_{s}_minutes.csv")
        mins["t"] = mins["ts"].str[11:16]
        by = {k: g.sort_values("ts").reset_index(drop=True) for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
        for r in c.itertuples():
            m = by.get((r.symbol, r.day0, r.side, float(r.strike)))
            m = None if m is None else m[(m["t"] >= "09:15") & (m["t"] <= "15:19")]
            if m is None or m.empty:
                continue
            tick = 0.05 if r.day0 < TICK_CHANGE else 0.01
            ea = float(r.entry_price) if hasattr(r, "entry_price") else round(float(r.bhav_open) + tick, 2)
            base = {"set": s, "symbol": r.symbol, "day0": r.day0, "side": r.side, "lot": int(r.lot), "entry_A": ea,
                    "half": HALF(r.day0), **{f"A_{k}": v for k, v in nets(m, r.side, int(r.lot), ea, tick, "09:16").items()}}
            c16 = m[m["t"] == "09:16"]
            if c16.empty:
                rows.append({**base, "B_excluded": "no_0916_candle"})
                continue
            eb = round(float(c16["o"].iloc[0]) + tick, 2)
            rows.append({**base, "B_excluded": "", "entry_B": eb,
                         **{f"B_{k}": v for k, v in nets(m, r.side, int(r.lot), eb, tick, "09:17").items()}})
    return pd.DataFrame(rows)


def lot_ok(entry: pd.Series, lot: pd.Series) -> pd.Series:
    v = entry * lot
    return (v >= 600) & (v <= 8000)


def line(g: pd.DataFrame, e: str, x: str, **lab) -> dict:
    if g.empty:
        return {**lab, "n": 0}
    prem = g[f"entry_{e}"] * g["lot"]
    pct = g[f"{e}_{x}"] / prem * 100
    return {**lab, "n": len(g), "win %": round((g[f"{e}_{x}"] > 0).mean() * 100, 1), "mean %": round(pct.mean(), 2),
            "median %": round(pct.median(), 1), "total Rs": round(g[f"{e}_{x}"].sum()),
            "t": clustered_t(pct, g["day0"]) if len(g) > 1 else None}


def main() -> None:
    t = build()
    t.to_csv(RES / "S1_fade_realistic_studies_trades.csv", index=False)
    ok = t[t["B_excluded"] == ""].copy()
    for e in ("A", "B"):
        ok[f"ok_{e}"] = lot_ok(ok[f"entry_{e}"], ok["lot"])
    parts = ["# S1 fade · the floor, band, target and filter studies with the realistic entry (09:16 candle)\n",
             "Pre-registered: strategies/S1_fade_realistic_entry_studies.md. Descriptive; nothing live changes. Only "
             f"contracts with day-0 minute candles (Oct 2024 - Sep 2026): {len(ok)} contracts "
             f"({len(t) - len(ok)} without a 09:16 candle excluded). A = old entry, B = 09:16 open + 1 tick, same exit "
             "code; real charges, no extra % slippage. The 2022-24 daily-data parts of the old studies cannot be "
             "re-priced (no minute data). t is date-clustered; real only with t >= 2 and the same sign in both halves.\n"]

    # 1 floor
    rows = []
    for fl in (2.0, 1.0, 0.5):
        for e in ("A", "B"):
            g = ok[(ok[f"entry_{e}"] >= fl) & ok[f"ok_{e}"]]
            for x in ("v10", "v11"):
                for h in ("all", "Oct24-Oct25", "Nov25-Sep26"):
                    rows.append(line(g if h == "all" else g[g["half"] == h], e, x, floor=fl, entry=e, exit=x, period=h))
    parts.append("## 1. Floor\n\n" + md(pd.DataFrame(rows)))

    # 2 band
    rows = []
    for lo, hi in ((2.0, 1e9), (1.0, 2.0), (0.5, 1.0)):
        for e in ("A", "B"):
            g = ok[(ok[f"entry_{e}"] >= lo) & (ok[f"entry_{e}"] < hi) & ok[f"ok_{e}"]]
            for x in ("v10", "v11"):
                rows.append(line(g, e, x, band=f"{lo:g}-{'up' if hi > 1e8 else f'{hi:g}'}", entry=e, exit=x))
    parts.append("## 2. Band\n\n" + md(pd.DataFrame(rows)))

    # 3 target
    rows = []
    for fl in (2.0, 1.0):
        for e in ("A", "B"):
            g = ok[(ok[f"entry_{e}"] >= fl) & ok[f"ok_{e}"]]
            for x in ["v10", "v11"] + [f"T{T * 100:g}{s}" for T in TARGETS for s in ("", "+stop")]:
                rows.append(line(g, e, x, floor=fl, entry=e, exit=x))
    parts.append("## 3. Target (resting sell at entry x (1+T))\n\n" + md(pd.DataFrame(rows)))

    # 4 filter
    px = Prices(set(ok["symbol"]))
    f = ok[(ok["entry_B"] >= 2.0) & ok["ok_B"]].copy()
    ar = pd.DataFrame([px.ar(s, d) for s, d in zip(f["symbol"], f["day0"])], index=f.index)
    f["O"] = [flag(a, r) for a, r in zip(ar["ar_open"], ar["raw_open"])]
    rows = []
    for side in ("all", "PE", "CE"):
        gs = f if side == "all" else f[f["side"] == side]
        for grp in ("keep", "drop", "unknown"):
            for x in ("v10", "v11"):
                for h in ("all", "Oct24-Oct25", "Nov25-Sep26"):
                    g = gs[gs["O"] == grp]
                    rows.append(line(g if h == "all" else g[g["half"] == h], "B", x, side=side, O=grp, exit=x, period=h))
    parts.append("## 4. Arm-A-overlap filter O (B trades, fill >= Rs 2)\n\n" + md(pd.DataFrame(rows)))
    d = f[f["O"] == "drop"]
    pc = d["B_v11"] / (d["entry_B"] * d["lot"]) * 100
    h1, h2 = (d[d["half"] == h] for h in ("Oct24-Oct25", "Nov25-Sep26"))
    tt = clustered_t(pc, d["day0"]) if len(d) > 1 else None
    m1 = (h1["B_v11"] / (h1["entry_B"] * h1["lot"]) * 100).mean() if len(h1) else None
    m2 = (h2["B_v11"] / (h2["entry_B"] * h2["lot"]) * 100).mean() if len(h2) else None
    passed = len(h1) >= 20 and len(h2) >= 20 and m1 < 0 and m2 < 0 and tt is not None and tt <= -2
    parts.append(f"### Filter test (v11, B): **{'PASS' if passed else 'FAIL (not established)'}**\n\n"
                 f"O-dropped: n {len(d)} (halves {len(h1)} / {len(h2)}); mean {m1} / {m2}; pooled t {tt}.\n")
    (RES / "S1_fade_realistic_studies.md").write_text("\n".join(parts), encoding="utf-8")
    print("\n".join(parts))


if __name__ == "__main__":
    main()
