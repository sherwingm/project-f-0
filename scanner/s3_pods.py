"""Shared runner for S3 single-day pods (one trade a day on a chosen set of days), with the DECISIONS.md S3 gate.

A pod module gives: the days, the grid cells, a cell -> Spec function, the primary cell, its neighbours and its skip
rules; `run_pod` runs every cell on every day (plus the primary at 2x costs), applies the skips, scores the gate and
writes data/results/S3_<name>_report.md (or _holdout.md) and the trades CSV.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd

from index_data import load as L
from scanner.s3_engine import Spec, run_day
from scanner.s3_p1 import EVENTS, HALVES, TEST, gate, monte_carlo, summary, vix_at

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "data" / "results"
HOLDOUT = (date(2025, 10, 1), date(2026, 10, 31))
HOLDOUT_HALVES = ((date(2025, 10, 1), date(2026, 3, 31)), (date(2026, 4, 1), date(2026, 10, 31)))


@dataclass
class Pod:
    name: str                                   # e.g. "P2s"
    title: str
    page: str                                   # strategies/...md
    cells: list                                 # hashable cell keys
    spec: Callable[[tuple, float], Spec]        # (cell, cost_mult) -> Spec
    primary: tuple
    neighbours: list
    label: Callable[[tuple], str]               # cell -> table label
    skip_events: bool = True
    vix: tuple | None = None                    # (lo, hi) inclusive at the entry minute, None = no filter
    days: Callable[[tuple], list] | None = None # window -> days (default: NIFTY expiry days)
    expiry_for: Callable[[date], date] | None = None   # day -> expiry traded (default: the day itself)
    measure: str = "credit"
    extra: dict = field(default_factory=dict)


def expiry_days(window: tuple) -> list[date]:
    return [e for e in L.expiries("NIFTY") if window[0] <= e <= window[1] and e in L.trade_days("NIFTY", e)]


def run_pod(pod: Pod, holdout: bool = False) -> dict:
    window = HOLDOUT if holdout else TEST
    halves = HOLDOUT_HALVES if holdout else HALVES
    days = (pod.days or expiry_days)(window)
    rows, vcache = [], {}
    for d in days:
        exp = pod.expiry_for(d) if pod.expiry_for else d
        for cell, cm in [(c, 1.0) for c in pod.cells] + [(pod.primary, 2.0)]:
            sp = pod.spec(cell, cm)
            r = run_day(sp, d, exp) if exp else {"day": d, "skip": "no expiry"}
            rows.append({**r, "cell": pod.label(cell), "cost_mult": cm, "vix": vix_at(d, *sp.entry, vcache),
                         "event": d in EVENTS, "weekday": d.strftime("%a"), "expiry": exp})
    return write_report(pod, pd.DataFrame(rows), len(days), window, halves, holdout)


def write_report(pod: Pod, allt: pd.DataFrame, n_days: int, window: tuple, halves: tuple, holdout: bool,
                 extra: list | None = None) -> dict:
    """Apply the pod's skips, score the gate on the primary cell, write the report and the trades CSV."""
    allt = allt.copy()
    allt["skip"] = allt["skip"].fillna("")
    keep = allt["skip"] == ""
    if pod.skip_events:
        keep &= ~allt["event"]
    if pod.vix:
        keep &= allt["vix"].between(*pod.vix)
    allt["traded"] = keep
    allt.to_csv(RES / f"S3_{pod.name}_{'holdout_' if holdout else ''}trades.csv", index=False)

    def cell(c, cm=1.0, filtered=True):
        m = (allt["cell"] == pod.label(c)) & (allt["cost_mult"] == cm)
        return allt[m & allt["traded"]] if filtered else allt[m & (allt["skip"] == "")]

    prim, prim2 = cell(pod.primary), cell(pod.primary, 2.0)
    g = gate(prim, prim2, [cell(n) for n in pod.neighbours], halves)
    s = summary(prim)
    pall = allt[(allt["cell"] == pod.label(pod.primary)) & (allt["cost_mult"] == 1.0)]
    unit = "the credit" if pod.measure == "credit" else "the premium paid"
    lines = [f"# S3 {pod.name} · {pod.title}: {'HOLDOUT' if holdout else 'test window'} {window[0]} → {window[1]}", "",
             f"Pre-registered: `{pod.page}`. Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves "
             f"on net % of {unit}; rupees at 1 lot.", "",
             f"Days {n_days}. Primary cell: {s['n']} trades. Not traded: {int((pall['skip'] != '').sum())} without prices"
             + (f", {int((pall['event'] & (pall['skip'] == '')).sum())} event days" if pod.skip_events else "")
             + (f", {int(((pall['skip'] == '') & ~pall['vix'].between(*pod.vix)).sum())} with VIX outside "
                f"{pod.vix[0]:g}-{pod.vix[1]:g}" if pod.vix else "") + ".", "",
             f"## Verdict: **{'PASS' if g['pass'] else 'FAIL'}**", ""]
    lines += [f"- {'✔' if ok else '✘'} {k}" for k, ok in g["checks"].items()]
    if s["n"]:
        p5, p50, p95 = monte_carlo(prim["net_rs"])
        mg = prim["net_pct_margin"].dropna()
        lines += ["", f"## Primary cell ({pod.label(pod.primary)})", "",
                  f"- Trades {s['n']}, **win rate {s['win'] * 100:.0f} %**, stop hit {s['stop_rate'] * 100:.0f} %.",
                  f"- Net per trade: **{s['mean_pct']:+.1f} % of {unit}** (median {s['median_pct']:+.1f} %), t {s['t_pct']:.2f}; "
                  f"₹{s['mean_rs']:+,.0f} a trade (t {s['t_rs']:.2f}), total ₹{s['total_rs']:+,.0f}.",
                  f"- Average {pod.measure} {prim['premium'].mean():.1f} points (₹{prim['premium_rs'].mean():,.0f}); fees "
                  f"₹{prim['fees_rs'].mean():,.0f} a trade; net {mg.mean():+.2f} % of margin a trade.",
                  f"- Halves: {g.get('halves', [float('nan')] * 2)[0]:+.1f} % / {g.get('halves', [float('nan')] * 2)[1]:+.1f} %.",
                  f"- Worst day ₹{s['worst_rs']:,.0f}; average month ₹{s['avg_month_rs']:+,.0f}; deepest drawdown ₹{s['max_dd_rs']:,.0f}.",
                  f"- At 2x costs: {summary(prim2).get('mean_pct', float('nan')):+.1f} % of {unit}.",
                  f"- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹{p5:,.0f}, median ₹{p50:,.0f}, 95th ₹{p95:,.0f}."]
    lines += ["", f"## Grid (net % of {unit} per trade · trades · win rate · t)", "", "| Cell | Result |", "|---|---|"]
    for c in pod.cells:
        x = summary(cell(c))
        lines.append(f"| {pod.label(c)} | " + (f"{x['mean_pct']:+.1f} % · {x['n']} · {x['win'] * 100:.0f} % · {x['t_pct']:.1f}"
                                               if x["n"] else "–") + " |")
    side = cell(pod.primary, filtered=False).copy()
    side["band"] = pd.cut(side["vix"], [0, 13, 20, 99], labels=["VIX <13", "VIX 13-20", "VIX >20"], right=False)
    lines += ["", "## Primary cell without the VIX / event filters, by group (side report)", "",
              "| Group | Trades | Net % | Win rate |", "|---|---|---|---|"]
    for col in ("band", "weekday", "event"):
        for name, grp in side.groupby(col, observed=True):
            nm = ("event day" if name else "other day") if col == "event" else name
            lines.append(f"| {nm} | {len(grp)} | {grp['net_pct_premium'].mean():+.1f} % | {(grp['net_rs'] > 0).mean() * 100:.0f} % |")
    lines += extra or []
    sk = pall[pall["skip"] != ""]
    if len(sk):
        lines += ["", "## Days without prices (primary cell)", ""] + [f"- {r.day}: {r.skip}" for r in sk.itertuples()]
    out = RES / f"S3_{pod.name}_{'holdout' if holdout else 'report'}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    verdict = {"pass": g["pass"], **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()}}
    if holdout and s["n"]:
        verdict["sharpe"] = float(prim["net_pct_premium"].mean() / prim["net_pct_premium"].std(ddof=1))
    print(f"wrote {out}: {'PASS' if g['pass'] else 'FAIL'}", verdict)
    return verdict


def sharpe_of(name: str, holdout: bool, label: str) -> float:
    t = pd.read_csv(RES / f"S3_{name}_{'holdout_' if holdout else ''}trades.csv")
    p = t[(t["cell"] == label) & (t["cost_mult"] == 1.0) & t["traded"]]
    return float(p["net_pct_premium"].mean() / p["net_pct_premium"].std(ddof=1))
