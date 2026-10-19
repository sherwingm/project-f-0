"""S1 v10 fade · sub-Rs 2 trades only when no Rs 2+ option can fit Rs 600-8,000 (numbers only).

    python -m scanner.fade_subfloor_neverfits      # after scanner.fade_subfloor

strategies/S1_v10_subfloor_entry.md, addendum 2. Reads data/results/S1_v10_subfloor_trades.csv (the sub-Rs 2 trades
of both windows, with `e1_net` under the backtest's existing costs and `net` under the +-2 tick model) and the cached
option files; writes data/results/S1_v10_subfloor_neverfits.md.
"""
from __future__ import annotations

import pandas as pd

from .backtest_s1_v2 import md
from .backtest_s1_v10 import BAND, MIN_CONTRACTS, TICK, quotes_of, start_strike
from .build import ROOT
from .stats import clustered_t

RES, CACHE = ROOT / "data" / "results", ROOT / "data" / "cache"


def passed_dear(t: pd.DataFrame) -> pd.Series:
    """True when the walk, before the traded strike, passed a liquid Rs 2+ strike whose lot cost more than Rs 8,000."""
    out = {}
    for d0, g in t.groupby("day0"):
        p = pd.read_csv(CACHE / f"fo_prices_{d0.replace('-', '')}.csv")
        for i, r in g.iterrows():
            qs = quotes_of(p, r["symbol"], r["expiry"], r["side"])
            ks = sorted(qs)
            k0 = start_strike(ks, r["spot_prev_close"], r["side"])
            if k0 is None or float(r["strike"]) not in qs:
                out[i] = False
                continue
            a, b = ks.index(k0), ks.index(float(r["strike"]))
            path = ks[b + 1:a + 1] if r["side"] == "PE" else ks[a:b]
            out[i] = any(qs[k].contracts >= MIN_CONTRACTS and qs[k].open == qs[k].open and qs[k].open + TICK >= 2
                         and (qs[k].open + TICK) * qs[k].lot > BAND[1] for k in path)
    return pd.Series(out)


def stats(g: pd.DataFrame, col: str, pct: pd.Series) -> dict:
    if not len(g):
        return {"n": 0}
    cum = g.sort_values(["day0", "symbol"])[col].cumsum()
    top = g[col].idxmax()
    return {"n": len(g), "win_pct": round((g[col] > 0).mean() * 100, 1), "mean_pct": round(pct.mean(), 2),
            "median_pct": round(pct.median(), 2), "total_rs": round(g[col].sum()),
            "max_dd_rs": round(float((cum.cummax().clip(lower=0) - cum).max())),
            "t": clustered_t(pct, g["day0"]) if len(g) > 1 else None,
            "total_without_best_rs": round(g.drop(index=top)[col].sum()),
            "best": f"{g.loc[top, 'symbol']} {g.loc[top, 'day0']}"}


def table(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, col, pcol in (("existing rules (open+1 / close-1 tick, % slippage)", "e1_net", "e1_net_pct"),
                             ("tick model (+-2 ticks of Rs 0.05)", "net", "net_pct")):
        for w in ("2022-24", "2025-26", "pooled"):
            g = t if w == "pooled" else t[t["window"] == w]
            rows.append({"costs": label, "window": w, **stats(g, col, g[pcol].astype(float))})
    return pd.DataFrame(rows)


def verdict(tab: pd.DataFrame) -> str:
    e = tab[tab["costs"].str.startswith("existing")].set_index("window")
    ok = (all(e.loc[w, "total_rs"] > 0 for w in ("2022-24", "2025-26") if e.loc[w, "n"])
          and e.loc["pooled", "mean_pct"] > 0 and (e.loc["pooled", "t"] or 0) >= 2
          and e.loc["pooled", "total_without_best_rs"] > 0)
    return "passes" if ok else "does not pass"


def main() -> None:
    t = pd.read_csv(RES / "S1_v10_subfloor_trades.csv")
    t["never_fits"] = 2 * t["lot"] > BAND[1]
    t["passed_dear"] = passed_dear(t)
    nf, pdr = t[t["never_fits"]], t[t["passed_dear"]]
    tn, tp, ta = table(nf), table(pdr), table(t)
    text = "\n".join([
        "# S1 v10 fade · sub-Rs 2 trades only when no Rs 2+ option fits Rs 600-8,000\n",
        "Numbers only. strategies/S1_v10_subfloor_entry.md, addendum 2. Primary (\"never fits\"): Rs 2 x lot > Rs 8,000. "
        "Secondary: the walk passed a liquid Rs 2+ strike costing more than Rs 8,000. Existing rules = the backtest's own "
        "costs (the >= Rs 2 line: 2025-26 434 trades +Rs 1,26,164; 2022-24 436 trades +Rs 24,190). Tick model = this "
        "study's +-2 ticks of Rs 0.05, which overstates the spread from Nov 2025 (the tick became Rs 0.01). t is "
        "date-clustered.\n",
        f"**Primary (never fits), existing rules: {verdict(tn)} the pass test.** "
        f"**Secondary (passed a dear Rs 2+ strike), existing rules: {verdict(tp)}.**\n",
        f"## Primary: never fits ({len(nf)} of {len(t)} sub-Rs 2 trades)\n\n" + md(tn),
        f"## Secondary: passed a dear Rs 2+ strike ({len(pdr)} of {len(t)})\n\n" + md(tp),
        f"## For reference: all sub-Rs 2 trades ({len(t)})\n\n" + md(ta),
        "## The never-fits trades\n\n" + md(nf.sort_values("day0")[["window", "symbol", "day0", "side", "strike", "lot",
                                                                     "entry_price", "e1_net", "e1_net_pct", "net"]]),
    ])
    (RES / "S1_v10_subfloor_neverfits.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
