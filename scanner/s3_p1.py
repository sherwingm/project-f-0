"""S3 P1: NIFTY expiry-day iron fly, exactly as pre-registered in strategies/S3_P1_expiry_day_fly.md.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_p1            # test window only
    ... python -m scanner.s3_p1 --holdout          # once, and only after the test gate passed (DECISIONS.md)

Writes data/results/S3_P1_report.md (or S3_P1_holdout.md) and the trades CSV. Mean, t and halves are on net % of the
credit (lot-free: the NIFTY lot went 25 → 75 on 2025-01-31); the worst day vs the average month is in rupees.
"""
from __future__ import annotations

import argparse
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from index_data import load as L
from scanner.s3_engine import Leg, Spec, run_day

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "data" / "results"
TEST = (date(2024, 10, 1), date(2025, 9, 30))
HALVES = ((date(2024, 10, 1), date(2025, 3, 31)), (date(2025, 4, 1), date(2025, 9, 30)))
EVENTS = {date(2025, 2, 1), date(2024, 10, 9), date(2024, 12, 6), date(2025, 2, 7), date(2025, 4, 9), date(2025, 6, 6),
          date(2025, 8, 7), date(2025, 10, 1), date(2025, 12, 5), date(2026, 2, 6)}
VIX_LO, VIX_HI = 13.0, 20.0
ENTRIES = [(9, 20), (10, 0), (11, 15)]
STOPS = [0.20, 0.25, 0.30, 0.35, None]
PRIMARY = ("fly", (11, 15), 0.30)
NEIGHBOURS = [("fly", (11, 15), 0.25), ("fly", (11, 15), 0.35), ("fly", (10, 0), 0.30)]
MIN_TRADES = 30


def legs(structure: str) -> list[Leg]:
    core = [Leg("SELL", "CE", 0), Leg("SELL", "PE", 0)]
    return core + ([Leg("BUY", "CE", 4), Leg("BUY", "PE", -4)] if structure == "fly" else [])


def spec(structure: str, entry: tuple, stop: float | None, cost_mult: float = 1.0) -> Spec:
    return Spec(f"{structure}_{entry[0]:02d}{entry[1]:02d}_{'none' if stop is None else int(stop * 100)}",
                legs(structure), entry=entry, exit=(14, 45), stop=stop, cost_mult=cost_mult)


def t_stat(x) -> float:
    x = np.asarray(x, float)
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else float("nan")


def max_drawdown(pnl) -> float:
    eq = np.cumsum(np.asarray(pnl, float))
    return float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min()) if len(eq) else 0.0


def summary(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"n": 0}
    months = t.groupby(pd.to_datetime(t["day"]).dt.to_period("M"))["net_rs"].sum()
    return {"n": len(t), "win": float((t["net_rs"] > 0).mean()), "mean_pct": float(t["net_pct_premium"].mean()),
            "median_pct": float(t["net_pct_premium"].median()), "t_pct": t_stat(t["net_pct_premium"]),
            "mean_rs": float(t["net_rs"].mean()), "t_rs": t_stat(t["net_rs"]), "total_rs": float(t["net_rs"].sum()),
            "worst_rs": float(t["net_rs"].min()), "avg_month_rs": float(months.mean()),
            "stop_rate": float((t["reason"] == "stop").mean()), "max_dd_rs": max_drawdown(t["net_rs"])}


def half_means(t: pd.DataFrame, halves=HALVES) -> list[float]:
    d = pd.to_datetime(t["day"]).dt.date
    return [float(t.loc[(d >= a) & (d <= b), "net_pct_premium"].mean()) for a, b in halves]


def gate(primary: pd.DataFrame, primary_2x: pd.DataFrame, neighbours: list[pd.DataFrame], halves=HALVES) -> dict:
    s, s2 = summary(primary), summary(primary_2x)
    if s["n"] < MIN_TRADES:
        return {"pass": False, "checks": {f"at least {MIN_TRADES} trades": False}, "n": s["n"]}
    hm = half_means(primary, halves)
    checks = {
        "net mean > 0": s["mean_pct"] > 0,
        "net mean > 0 at 2x costs": s2["mean_pct"] > 0,
        "t >= 2": s["t_pct"] >= 2,
        "positive in each half": all(h > 0 for h in hm),
        "worst day smaller than the average month": abs(min(s["worst_rs"], 0)) < s["avg_month_rs"],
        "neighbours net positive": all(summary(n).get("mean_pct", -1) > 0 for n in neighbours),
        f"at least {MIN_TRADES} trades": s["n"] >= MIN_TRADES,
    }
    return {"pass": all(checks.values()), "checks": checks, "halves": hm}


def monte_carlo(pnl, n: int = 10000, seed: int = 11) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    x = np.asarray(pnl, float)
    dd = [max_drawdown(rng.permutation(x)) for _ in range(n)]
    return tuple(float(np.percentile(dd, q)) for q in (5, 50, 95))


def vix_at(day: date, hh: int, mm: int, cache: dict) -> float | None:
    if day not in cache:
        v = L.vix_1m(day, day)
        cache[day] = v.set_index("timestamp")["close"] if len(v) else None
    s = cache[day]
    if s is None:
        return None
    s = s[s.index <= L.at(day, hh, mm)]
    return float(s.iloc[-1]) if len(s) else None


def run(window: tuple[date, date], holdout: bool) -> None:
    days = [e for e in L.expiries("NIFTY") if window[0] <= e <= window[1] and e in L.trade_days("NIFTY", e)]
    cells = [(st, en, sp) for st in ("fly", "straddle") for en in ENTRIES for sp in STOPS]
    rows, vcache = [], {}
    for d in days:
        for cell in cells + [PRIMARY + (2.0,)]:
            st, en, sp = cell[:3]
            cm = cell[3] if len(cell) > 3 else 1.0
            r = run_day(spec(st, en, sp, cm), d, d)
            v = vix_at(d, *en, vcache)
            rows.append({**r, "structure": st, "entry": f"{en[0]:02d}:{en[1]:02d}", "stop": sp, "cost_mult": cm,
                         "vix": v, "event": d in EVENTS, "weekday": d.strftime("%a")})
    allt = pd.DataFrame(rows)
    allt["in_vix"] = allt["vix"].between(VIX_LO, VIX_HI)
    allt["stop"] = allt["stop"].astype(object)
    tag = "holdout" if holdout else "report"
    allt.to_csv(RES / f"S3_P1_{'holdout_' if holdout else ''}trades.csv", index=False)

    def cell(st, en, sp, cm=1.0, vix=True):
        m = (allt["structure"] == st) & (allt["entry"] == f"{en[0]:02d}:{en[1]:02d}") & (allt["cost_mult"] == cm)
        m &= allt["stop"].isna() if sp is None else (allt["stop"] == sp)
        m &= (allt["skip"] == "") & ~allt["event"]
        if vix:
            m &= allt["in_vix"]
        return allt[m]

    prim, prim2 = cell(*PRIMARY), cell(*PRIMARY, cm=2.0)
    halves = HALVES if not holdout else ((window[0], date(2026, 3, 31)), (date(2026, 4, 1), window[1]))
    g = gate(prim, prim2, [cell(*n) for n in NEIGHBOURS], halves)
    s = summary(prim)
    pskip = allt[(allt["structure"] == "fly") & (allt["entry"] == "11:15") & (allt["stop"] == 0.30) & (allt["cost_mult"] == 1.0)]
    lines = [f"# S3 P1 · NIFTY expiry-day iron fly: {'HOLDOUT' if holdout else 'test window'} {window[0]} → {window[1]}", "",
             "Pre-registered: `strategies/S3_P1_expiry_day_fly.md`. Engine `scanner/s3_engine.py`. Mean, t and halves on net % of the "
             "credit; rupees at 1 lot (25 before 2025-01-31, 65-75 after).", "",
             f"Expiry days {len(days)}. Primary cell: {s['n']} trades. Not traded: "
             f"{int((pskip['skip'] != '').sum())} without prices, {int(pskip['event'].sum())} event days, "
             f"{int(((pskip['skip'] == '') & ~pskip['event'] & ~pskip['in_vix']).sum())} with VIX outside 13-20.", "",
             f"## Verdict: **{'PASS' if g['pass'] else 'FAIL'}**", ""]
    for k, ok in g["checks"].items():
        lines.append(f"- {'✔' if ok else '✘'} {k}")
    if s["n"]:
        lines += ["", "## Primary cell (fly, 11:15, stop 30 %, exit 14:45, VIX 13-20)", "",
                  f"- Trades {s['n']}, **win rate {s['win'] * 100:.0f} %**, stop hit {s['stop_rate'] * 100:.0f} %.",
                  f"- Net per trade: **{s['mean_pct']:+.1f} % of the credit** (median {s['median_pct']:+.1f} %), t {s['t_pct']:.2f}; "
                  f"₹{s['mean_rs']:+,.0f} a trade (t {s['t_rs']:.2f}), total ₹{s['total_rs']:+,.0f}.",
                  f"- Halves: {g.get('halves', [float('nan')] * 2)[0]:+.1f} % / {g.get('halves', [float('nan')] * 2)[1]:+.1f} %.",
                  f"- Worst day ₹{s['worst_rs']:,.0f}; average month ₹{s['avg_month_rs']:+,.0f}; deepest drawdown ₹{s['max_dd_rs']:,.0f}.",
                  f"- At 2x costs: {summary(prim2).get('mean_pct', float('nan')):+.1f} % of the credit."]
        p5, p50, p95 = monte_carlo(prim["net_rs"])
        lines.append(f"- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹{p5:,.0f}, median ₹{p50:,.0f}, 95th ₹{p95:,.0f}.")
    lines += ["", "## Grid (net % of credit per trade · trades · win rate · t)", "",
              "| Structure | Entry | Stop | VIX 13-20 | All VIX |", "|---|---|---|---|---|"]
    for st, en, sp in cells:
        a, b = summary(cell(st, en, sp)), summary(cell(st, en, sp, vix=False))
        f = lambda x: f"{x['mean_pct']:+.1f} % · {x['n']} · {x['win'] * 100:.0f} % · {x['t_pct']:.1f}" if x["n"] else "–"  # noqa: E731
        lines.append(f"| {st} | {en[0]:02d}:{en[1]:02d} | {'none' if sp is None else f'{int(sp * 100)} %'} | {f(a)} | {f(b)} |")
    lines += ["", "## Primary cell without the VIX filter, by VIX band and weekday (side report)", "",
              "| Group | Trades | Net % of credit | Win rate |", "|---|---|---|---|"]
    nv = cell(*PRIMARY, vix=False).copy()
    nv["band"] = pd.cut(nv["vix"], [0, 13, 20, 99], labels=["<13", "13-20", ">20"], right=False)
    for name, grp in list(nv.groupby("band", observed=True)) + list(nv.groupby("weekday")):
        lines.append(f"| {name} | {len(grp)} | {grp['net_pct_premium'].mean():+.1f} % | {(grp['net_rs'] > 0).mean() * 100:.0f} % |")
    sk = pskip[pskip["skip"] != ""]
    if len(sk):
        lines += ["", "## Days without prices (primary cell)", ""] + [f"- {r.day}: {r.skip}" for r in sk.itertuples()]
    out = RES / f"S3_P1_{tag if holdout else 'report'}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}: {'PASS' if g['pass'] else 'FAIL'}", {k: round(v, 3) if isinstance(v, float) else v for k, v in s.items()})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true", help="the holdout, once, only after the test gate passed")
    a = ap.parse_args()
    if a.holdout:
        rep = RES / "S3_P1_report.md"
        if not rep.exists() or "Verdict: **PASS**" not in rep.read_text(encoding="utf-8"):
            raise SystemExit("the holdout runs only after the test window passed the gate (DECISIONS.md)")
        run((date(2025, 10, 1), date.today()), holdout=True)
    else:
        run(TEST, holdout=False)


if __name__ == "__main__":
    main()
