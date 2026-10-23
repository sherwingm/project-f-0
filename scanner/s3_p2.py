"""S3 P2: NIFTY expiry-day last-30-minutes long straddle, as pre-registered in strategies/S3_P2_expiry_last30_straddle.md.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_p2            # test window only
    ... python -m scanner.s3_p2 --holdout          # once, and only after the test gate passed

Gate maths, Monte Carlo and the summary are shared with P1 (`scanner/s3_p1.py`).
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from index_data import load as L
from scanner.s3_engine import Leg, Spec, run_day
from scanner.s3_p1 import EVENTS, HALVES, TEST, gate, monte_carlo, summary, vix_at

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "data" / "results"
ENTRIES = [(14, 30), (14, 45), (15, 0)]
EXITS = [(15, 15), (15, 25)]
TARGETS = [None, 0.5, 1.0]
PRIMARY = ((14, 45), (15, 25), None)
NEIGHBOURS = [((14, 30), (15, 25), None), ((15, 0), (15, 25), None), ((14, 45), (15, 15), None)]


def hm(t: tuple) -> str:
    return f"{t[0]:02d}:{t[1]:02d}"


def spec(entry: tuple, exit_: tuple, target: float | None, cost_mult: float = 1.0) -> Spec:
    return Spec(f"long_straddle_{hm(entry)}_{hm(exit_)}_{'none' if target is None else int(target * 100)}",
                [Leg("BUY", "CE", 0), Leg("BUY", "PE", 0)], entry=entry, exit=exit_, target=target, cost_mult=cost_mult)


def spot_close(day: date, at: str, cache: dict) -> float | None:
    if day not in cache:
        s = L.spot_1m(day, day)
        cache[day] = s.set_index(s["timestamp"].dt.strftime("%H:%M"))["close"]
    s = cache[day]
    s = s[s.index <= at]
    return float(s.iloc[-1]) if len(s) else None


def run(window: tuple[date, date], holdout: bool) -> None:
    days = [e for e in L.expiries("NIFTY") if window[0] <= e <= window[1] and e in L.trade_days("NIFTY", e)]
    cells = [(en, ex, tg) for en in ENTRIES for ex in EXITS for tg in TARGETS]
    rows, vcache, scache = [], {}, {}
    for d in days:
        for cell in cells + [PRIMARY + (2.0,)]:
            en, ex, tg = cell[:3]
            cm = cell[3] if len(cell) > 3 else 1.0
            r = run_day(spec(en, ex, tg, cm), d, d)
            s_exit = spot_close(d, r.get("exit_at") or hm(ex), scache) if not r.get("skip") else None
            rows.append({**r, "entry": hm(en), "exit": hm(ex), "target": tg, "cost_mult": cm, "vix": vix_at(d, *en, vcache),
                         "event": d in EVENTS, "weekday": d.strftime("%a"),
                         "move": abs(s_exit - r["atm"]) if s_exit is not None else None})
    allt = pd.DataFrame(rows)
    allt["target"] = allt["target"].astype(object)
    allt.to_csv(RES / f"S3_P2_{'holdout_' if holdout else ''}trades.csv", index=False)

    def cell(en, ex, tg, cm=1.0):
        m = (allt["entry"] == hm(en)) & (allt["exit"] == hm(ex)) & (allt["cost_mult"] == cm) & (allt["skip"] == "")
        m &= allt["target"].isna() if tg is None else (allt["target"] == tg)
        return allt[m]

    prim, prim2 = cell(*PRIMARY), cell(*PRIMARY, cm=2.0)
    halves = HALVES if not holdout else ((window[0], date(2026, 3, 31)), (date(2026, 4, 1), window[1]))
    g = gate(prim, prim2, [cell(*n) for n in NEIGHBOURS], halves)
    s = summary(prim)
    pall = allt[(allt["entry"] == "14:45") & (allt["exit"] == "15:25") & allt["target"].isna() & (allt["cost_mult"] == 1.0)]
    lines = [f"# S3 P2 · NIFTY expiry-day long straddle 14:45 → 15:25: {'HOLDOUT' if holdout else 'test window'} "
             f"{window[0]} → {window[1]}", "",
             "Pre-registered: `strategies/S3_P2_expiry_last30_straddle.md`. Engine `scanner/s3_engine.py`. Mean, t and halves on "
             "net % of the premium paid; rupees at 1 lot.", "",
             f"Expiry days {len(days)}. Primary cell: {s['n']} trades; {int((pall['skip'] != '').sum())} without prices.", "",
             f"## Verdict: **{'PASS' if g['pass'] else 'FAIL'}**", ""]
    lines += [f"- {'✔' if ok else '✘'} {k}" for k, ok in g["checks"].items()]
    if s["n"]:
        be = (prim["move"] > prim["premium"]).mean()
        p5, p50, p95 = monte_carlo(prim["net_rs"])
        lines += ["", "## Primary cell (buy the ATM CE + PE at 14:45, sell at 15:25)", "",
                  f"- Trades {s['n']}, **win rate {s['win'] * 100:.0f} %**; the index moved more than the premium paid on "
                  f"{be * 100:.0f} % of days (break-even before costs).",
                  f"- Net per trade: **{s['mean_pct']:+.1f} % of the premium** (median {s['median_pct']:+.1f} %), t {s['t_pct']:.2f}; "
                  f"₹{s['mean_rs']:+,.0f} a trade (t {s['t_rs']:.2f}), total ₹{s['total_rs']:+,.0f}.",
                  f"- Average premium paid {prim['premium'].mean():.1f} points (₹{prim['premium_rs'].mean():,.0f}); fees "
                  f"₹{prim['fees_rs'].mean():,.0f} a trade.",
                  f"- Halves: {g['halves'][0]:+.1f} % / {g['halves'][1]:+.1f} %.",
                  f"- Worst day ₹{s['worst_rs']:,.0f}; average month ₹{s['avg_month_rs']:+,.0f}; deepest drawdown ₹{s['max_dd_rs']:,.0f}.",
                  f"- At 2x costs: {summary(prim2).get('mean_pct', float('nan')):+.1f} % of the premium.",
                  f"- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹{p5:,.0f}, median ₹{p50:,.0f}, 95th ₹{p95:,.0f}."]
    lines += ["", "## Grid (net % of premium per trade · trades · win rate · t)", "",
              "| Entry | Exit | Target | Result |", "|---|---|---|---|"]
    for en, ex, tg in cells:
        x = summary(cell(en, ex, tg))
        res = f"{x['mean_pct']:+.1f} % · {x['n']} · {x['win'] * 100:.0f} % · {x['t_pct']:.1f}" if x["n"] else "–"
        lines.append(f"| {hm(en)} | {hm(ex)} | {'none' if tg is None else f'+{int(tg * 100)} %'} | {res} |")
    side = prim.copy()
    side["band"] = pd.cut(side["vix"], [0, 13, 20, 99], labels=["VIX <13", "VIX 13-20", "VIX >20"], right=False)
    side["ev"] = side["event"].map({True: "event day", False: "other day"})
    lines += ["", "## Primary cell by group (side report)", "", "| Group | Trades | Net % of premium | Win rate |", "|---|---|---|---|"]
    for col in ("band", "weekday", "ev"):
        for name, grp in side.groupby(col, observed=True):
            lines.append(f"| {name} | {len(grp)} | {grp['net_pct_premium'].mean():+.1f} % | {(grp['net_rs'] > 0).mean() * 100:.0f} % |")
    sk = pall[pall["skip"] != ""]
    if len(sk):
        lines += ["", "## Days without prices (primary cell)", ""] + [f"- {r.day}: {r.skip}" for r in sk.itertuples()]
    out = RES / f"S3_P2_{'holdout' if holdout else 'report'}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}: {'PASS' if g['pass'] else 'FAIL'}", {k: round(v, 3) if isinstance(v, float) else v for k, v in s.items()})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true", help="the holdout, once, only after the test gate passed")
    a = ap.parse_args()
    if a.holdout:
        rep = RES / "S3_P2_report.md"
        if not rep.exists() or "Verdict: **PASS**" not in rep.read_text(encoding="utf-8"):
            raise SystemExit("the holdout runs only after the test window passed the gate (DECISIONS.md)")
        run((date(2025, 10, 1), date.today()), holdout=True)
    else:
        run(TEST, holdout=False)


if __name__ == "__main__":
    main()
