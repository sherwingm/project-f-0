"""S1 · the stock's path after an entry at a market-hours results announcement (descriptive; addendum 2026-10-20 of
strategies/S1_intraday_results_reaction.md).

    python -m scanner.results_intraday_path --nifty-dir <folder of spot_1m/NIFTY50/*.parquet>

Entry = the close of the minute t0 + 1. Moves from it at +5 / +15 / +30 / +60 minutes, 15:20, and the next session's
open and close; market-adjusted (minus NIFTY 50) and raw. Writes data/results/S1_intraday_results_path.md.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

from .backtest_s1_v2 import md
from .build import ROOT
from .equity import load_symbol
from .event_screens import strong, weak
from .results_intraday import at, hm
from .stats import clustered_t

RES, EOD2 = ROOT / "data" / "results", ROOT / "data" / "eod2"
HORIZONS = (("+5 min", 5), ("+15 min", 15), ("+30 min", 30), ("+60 min", 60))
COLS = ["+5 min", "+15 min", "+30 min", "+60 min", "15:20", "next open", "next close"]


def pct(a: float, b: float) -> float:
    return (b / a - 1) * 100 if a > 0 and b > 0 and not (math.isnan(a) or math.isnan(b)) else math.nan


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nifty-dir", type=Path, required=True)
    a = ap.parse_args()
    cases = pd.read_csv(RES / "S1_intraday_cases.csv")
    mins = pd.read_csv(RES / "S1_intraday_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    stock = {k: g.set_index("t")["c"] for k, g in mins.groupby(["symbol", "day"])}
    nf = pd.concat([pd.read_parquet(p) for p in sorted(a.nifty_dir.glob("*.parquet"))])
    nf["day"], nf["t"] = nf["timestamp"].dt.strftime("%Y-%m-%d"), nf["timestamp"].dt.strftime("%H:%M")
    nifty = {d: g.drop_duplicates("t").set_index("t") for d, g in nf.groupby("day")}
    ndays = sorted(nifty)
    fin = json.loads((ROOT / "data" / "financials.json").read_text(encoding="utf-8"))
    from .peak_study import result_quality

    daily: dict[str, pd.DataFrame | None] = {}
    rows = []
    for r in cases.itertuples():
        s, n = stock.get((r.symbol, r.day)), nifty.get(r.day)
        if s is None or n is None:
            continue
        nc = n["close"]
        e_t = hm(r.t0, 1)
        pre_s, e_s = at(s, hm(r.t0, -1)), at(s, e_t)
        pre_n, e_n = at(nc, hm(r.t0, -1)), at(nc, e_t)
        if math.isnan(e_s) or math.isnan(at(s, "15:20")) or e_t > "15:20":
            continue
        row = {"symbol": r.symbol, "day": r.day, "t0": r.t0, "window": "2022-24" if r.day < "2025-01-01" else "2025-26"}
        row["missed_raw"] = pct(pre_s, e_s)
        row["missed"] = row["missed_raw"] - pct(pre_n, e_n)
        for lab, k in HORIZONS + (("15:20", None),):
            t = "15:20" if k is None or hm(r.t0, 1 + k) > "15:20" else hm(r.t0, 1 + k)
            raw = pct(e_s, at(s, t))
            row[f"{lab} raw"], row[lab] = raw, raw - pct(e_n, at(nc, t))
        # next session (stock from eod2, NIFTY from its minutes)
        i = ndays.index(r.day) if r.day in ndays else None
        nxt = ndays[i + 1] if i is not None and i + 1 < len(ndays) else None
        if r.symbol not in daily:
            try:
                f = load_symbol(r.symbol, EOD2)
                f.index = f.index.strftime("%Y-%m-%d")
                daily[r.symbol] = f[~f.index.duplicated(keep="last")]
            except Exception:  # noqa: BLE001 - no eod2 file
                daily[r.symbol] = None
        f = daily[r.symbol]
        if nxt and f is not None and nxt in f.index and r.day in f.index:
            # eod2 is adjusted; scale the entry by the day's adjusted / minute close so both are on one basis
            scale = float(f.loc[r.day, "Close"]) / at(s, "15:29") if at(s, "15:29") > 0 else math.nan
            e_adj = e_s * scale
            nn = nifty[nxt]
            for lab, px, npx in (("next open", f.loc[nxt, "Open"], nn["open"].iloc[0]),
                                 ("next close", f.loc[nxt, "Close"], nn["close"].iloc[-1])):
                raw = pct(e_adj, float(px))
                row[f"{lab} raw"], row[lab] = raw, raw - pct(e_n, float(npx))
        q = result_quality(fin, r.symbol, r.day)
        row["class"] = "strong" if strong(q, 10) else "weak" if weak(q) else "neither"
        row["jump"] = "up" if row["missed"] > 0 else "down"
        rows.append(row)
    df = pd.DataFrame(rows)

    def summary(g: pd.DataFrame, cols=COLS) -> list[dict]:
        out = []
        for c in cols:
            x = g.dropna(subset=[c])
            if x.empty:
                continue
            out.append({"from entry to": c, "n": len(x), "mean %": round(x[c].mean(), 3), "median %": round(x[c].median(), 3),
                        "up %": round((x[c] > 0).mean() * 100, 1), "t": clustered_t(x[c], x["day"]) if len(x) > 1 else None})
        return out

    parts = []
    for name, by in (("By the numbers class", "class"), ("By the direction of the missed first-minute jump", "jump")):
        rows_ = []
        for v in sorted(df[by].unique()):
            for w in ("2022-24", "2025-26", "all"):
                g = df[df[by] == v] if w == "all" else df[(df[by] == v) & (df["window"] == w)]
                rows_ += [{by: v, "window": w, **x} for x in summary(g)]
        parts.append(f"## {name} (market-adjusted)\n\n" + md(pd.DataFrame(rows_)))
    allr = [{"window": w, **x} for w in ("2022-24", "2025-26", "all")
            for x in summary(df if w == "all" else df[df["window"] == w])]
    missed = pd.DataFrame([{"class": c, "n": len(g), "mean missed jump %": round(g["missed"].mean(), 3),
                            "mean |missed| %": round(g["missed"].abs().mean(), 3)}
                           for c, g in df.groupby("class")])
    text = "\n".join([
        "# S1 · the stock after an entry at a market-hours results announcement (descriptive)\n",
        "Addendum 2026-10-20 of strategies/S1_intraday_results_reaction.md. Entry = the close of the minute after the "
        "announcement's minute. Moves are % from the entry, minus NIFTY 50's over the same time (market-adjusted). "
        "up % = the share of cases above the entry. t is date-clustered. No pass test.\n",
        f"Cases: {len(df)}.\n",
        "## All cases\n\n" + md(pd.DataFrame(allr)),
        *parts,
        "## The move missed by entering one minute after the announcement\n\n" + md(missed),
    ])
    (RES / "S1_intraday_results_path.md").write_text(text, encoding="utf-8")
    df.to_csv(RES / "S1_intraday_results_path_cases.csv", index=False)
    print(text)


if __name__ == "__main__":
    main()
