"""S1 v10 fade · premium-floor sweep: the 2025-26 backtest's trades at each floor side by side (numbers only).

    python -m scanner.fade_floor_sweep

Reads data/results/S1_v10_trades_floor<f>.csv (made by `scanner.backtest_s1_v10 --min-premium <f> --tag _floor<f>`)
and writes S1_v10_floor_sweep.md. strategies/S1_v10_backtest_2025_26.md, addendum 2026-10-19. Entry: day 0's open +
1 tick; trades valid under E1 (v10's same-day exit); E2 shown for reference.
"""
from __future__ import annotations

import pandas as pd

from .backtest_s1_v2 import md
from .backtest_s1_v10 import metrics
from .build import ROOT

FLOORS = (2.0, 1.0, 0.5, 0.25, 0.05)
OUT = ROOT / "data" / "results"
KEEP = ("n", "hit_pct", "mean_pct", "median_pct", "p10", "p90", "t", "total_rs", "avg_lot_rs")


def tag(f: float) -> str:
    return f"{f:g}".replace(".", "p")


def rows(t: pd.DataFrame, label: str, f: float) -> list[dict]:
    out = []
    for ex, name in (("e1", "E1 same day"), ("e2", "E2 carry rule")):
        m = metrics(t, ex)
        out.append({"floor_rs": f"{f:g}", "trades": label, "exit": name, **{k: m.get(k) for k in KEEP}})
    return out


def main() -> None:
    res = []
    for f in FLOORS:
        t = pd.read_csv(OUT / f"S1_v10_trades_floor{tag(f)}.csv")
        t = t[t["entry"] == "open"]
        res += rows(t, "all", f)
        if f < 2.0:
            add = t[t["entry_price"] < 2.0]
            res += rows(add, "added (fill < Rs 2)", f)
            top = add["e1_net"].idxmax()                         # one lottery ticket carries the group: shown without it
            res += rows(add.drop(index=top), f"added, without {add.loc[top, 'symbol']} {add.loc[top, 'day0']}", f)
    tab = pd.DataFrame(res)
    e1 = tab[tab["exit"] == "E1 same day"].drop(columns="exit")
    e2 = tab[tab["exit"] == "E2 carry rule"].drop(columns="exit")
    text = "\n".join([
        "# S1 v10 fade · premium-floor sweep 2025-01-01 .. 2026-09-25\n",
        "Numbers only (strategies/S1_v10_backtest_2025_26.md, addendum 2026-10-19). Not out of sample; five floors on one "
        "window, so the best looks better than it is. Entry day 0's open + 1 tick; net % of premium after charges and "
        "slippage; t date-clustered. \"added\" = the trades with a fill under Rs 2, which only the lower floor takes.\n",
        "## E1 · same-day exit (v10 as written)\n\n" + md(e1),
        "## E2 · carried-trade rule (reference)\n\n" + md(e2),
    ])
    (OUT / "S1_v10_floor_sweep.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
