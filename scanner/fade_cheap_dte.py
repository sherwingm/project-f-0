"""S1 fade · cheap options (< Rs 10) only when >= 7 / >= 10 sessions before expiry, same-day v12 exit (numbers only).

    python -m scanner.fade_cheap_dte

strategies/S1_fade_cheap_dte.md fixes every choice. Writes data/results/S1_fade_cheap_dte.md and _trades.csv.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from .backtest_cheap_options import sessions_to
from .backtest_s1_v2 import md
from .build import ROOT
from .fade_preopen_entry import sessions
from .fade_realistic_studies import HALF, SETS, TICK_CHANGE
from .fade_stop_trail import one
from .stats import clustered_t

RES = ROOT / "data" / "results"
V12 = {"S": 20, "mode": "touch", "start": "09:17", "A": 10, "D": 2, "re": False}


class _R:                                                         # the row one() reads
    def __init__(self, **k):
        self.__dict__.update(k)


def build() -> pd.DataFrame:
    cal = [date.fromisoformat(d) for d in sessions()]
    rows, seen = [], set()
    for s in SETS:
        c = pd.read_csv(RES / f"S1_v10_{s}_contracts.csv")
        mins = pd.read_csv(RES / f"S1_v10_{s}_minutes.csv")
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
            pct = one(m, _R(lot=lot, side=r.side, day0=r.day0, entry_B=eb), V12)
            ste = sessions_to(cal, date.fromisoformat(r.day0), date.fromisoformat(str(r.expiry)[:10]))
            rows.append({"set": s, "symbol": r.symbol, "day0": r.day0, "side": r.side, "expiry": str(r.expiry)[:10],
                         "strike": float(r.strike), "lot": lot, "entry_B": eb, "lot_value": round(eb * lot, 2),
                         "lot_ok": 600 <= eb * lot <= 8000, "sessions_to_expiry": ste, "half": HALF(r.day0),
                         "v12_net_pct": pct, "v12_net": round(pct / 100 * eb * lot, 2)})
    return pd.DataFrame(rows)


def stats(g: pd.DataFrame, **lab) -> dict:
    if g.empty:
        return {**lab, "n": 0}
    return {**lab, "n": len(g), "win %": round((g["v12_net"] > 0).mean() * 100, 1),
            "mean %": round(g["v12_net_pct"].mean(), 2), "median %": round(g["v12_net_pct"].median(), 1),
            "total Rs": round(g["v12_net"].sum()), "t": clustered_t(g["v12_net_pct"], g["day0"]) if len(g) > 1 else None}


def main() -> None:
    t = build()
    t.to_csv(RES / "S1_fade_cheap_dte_trades.csv", index=False)
    ok = t[t["lot_ok"]]
    groups = {"Baseline: B >= Rs 2, any expiry gap": ok[ok["entry_B"] >= 2],
              "Rule-7: B < Rs 10, >= 7 sessions to expiry": ok[(ok["entry_B"] < 10) & (ok["sessions_to_expiry"] >= 7)],
              "Rule-10: B < Rs 10, >= 10 sessions to expiry": ok[(ok["entry_B"] < 10) & (ok["sessions_to_expiry"] >= 10)]}
    main_rows, tests = [], []
    for name, g in groups.items():
        for h in ("all", "Oct24-Oct25", "Nov25-Sep26"):
            main_rows.append(stats(g if h == "all" else g[g["half"] == h], group=name, period=h))
    base = groups["Baseline: B >= Rs 2, any expiry gap"]["v12_net_pct"].mean()
    for name in list(groups)[1:]:
        g = groups[name]
        s, h1, h2 = stats(g), g[g["half"] == "Oct24-Oct25"], g[g["half"] == "Nov25-Sep26"]
        passed = bool(s["n"] and s["mean %"] > 0 and (s["t"] or 0) >= 2 and len(h1) and h1["v12_net_pct"].mean() > 0
                      and len(h2) and h2["v12_net_pct"].mean() > 0 and s["mean %"] > base)
        tests.append({"rule": name, "n": s["n"], "mean %": s.get("mean %"), "t": s.get("t"),
                      "half 1 mean %": round(h1["v12_net_pct"].mean(), 2) if len(h1) else None,
                      "half 2 mean %": round(h2["v12_net_pct"].mean(), 2) if len(h2) else None,
                      "baseline mean %": round(base, 2), "pass": passed})
    under10 = ok[ok["entry_B"] < 10]
    br = [stats(under10[under10["entry_B"] < 2], part="B < Rs 2 (refused today)"),
          stats(under10[under10["entry_B"] >= 2], part="B Rs 2-10")]
    for lo, hi, lab in ((0, 6, "< 7 sessions"), (7, 9, "7-9 sessions"), (10, 999, ">= 10 sessions")):
        g = under10[(under10["sessions_to_expiry"] >= lo) & (under10["sessions_to_expiry"] <= hi)]
        br.append(stats(g, part=f"B < Rs 10, {lab} to expiry"))
        br.append(stats(g[g["entry_B"] < 2], part=f"   of which B < Rs 2, {lab}"))
    text = "\n".join([
        "# S1 fade · cheap options (< Rs 10) only when >= 7 / >= 10 sessions before expiry, same-day v12 exit\n",
        f"Pre-registered: strategies/S1_fade_cheap_dte.md. {len(t)} contracts with day-0 minutes (Oct 2024 - Aug 2026), "
        f"{len(ok)} with one lot Rs 600-8,000 at entry B (09:16 open + 1 tick). v12 exit on 1-minute candles, real "
        "charges. t date-clustered.\n",
        "## The test\n\n" + md(pd.DataFrame(tests)),
        "## Groups\n\n" + md(pd.DataFrame(main_rows)),
        "## Breakdown (one lot Rs 600-8,000)\n\n" + md(pd.DataFrame(br)),
        "\nOptions under Rs 0.50 at the old opening print are not in the minute sets, so the cheapest ones are missing.\n",
    ])
    (RES / "S1_fade_cheap_dte.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
