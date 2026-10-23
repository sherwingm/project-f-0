"""S3 R1: SENSEX replication of the late-expiry premium finding (strategies/S3_R1_sensex_late_expiry_replication.md,
with its 2026-10-23 amendment).

    INDEX_STORE=<index-data checkout with SENSEX>/data/index python -m scanner.s3_r1
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from index_data import load as L
from scanner.s3_engine import Leg, Spec
from scanner.s3_p1 import TEST, summary, t_stat
from scanner.s3_pods import RES, Pod, expiry_days, run_pod

LOT = 20
NIFTY_EXP = set()


def hm(t):
    return f"{t[0]:02d}:{t[1]:02d}"


def straddle(side):
    return [Leg(side, "CE", 0), Leg(side, "PE", 0)]


def fly(w):
    return straddle("SELL") + [Leg("BUY", "CE", w), Leg("BUY", "PE", -w)]


def pod(name, title, legs, cells, lots, skip_events=True, measure="credit", days=None, expiry_for=None) -> Pod:
    lab = lambda c: f"{title} {hm(c[0])}→{hm(c[1])}, {lots} lot{'s' if lots > 1 else ''}"  # noqa: E731
    return Pod(name=name, title=f"SENSEX {lab(cells[0])}", page="strategies/S3_R1_sensex_late_expiry_replication.md",
               cells=cells, spec=lambda c, cm=1.0: Spec(lab(c), legs, entry=c[0], exit=c[1], lots=lots, cost_mult=cm),
               primary=cells[0], neighbours=cells[1:], label=lab, skip_events=skip_events, measure=measure,
               underlying="SENSEX", index="SENSEX", lot=LOT, days=days, expiry_for=expiry_for)


SHORT = [((14, 30), (15, 15)), ((14, 30), (15, 25)), ((14, 45), (15, 15)), ((14, 45), (15, 25))]
LONG = [((14, 45), (15, 25)), ((14, 30), (15, 25)), ((15, 0), (15, 25)), ((14, 45), (15, 15))]


def non_expiry_days(window):
    exps = set(L.expiries("SENSEX"))
    sp = L.spot_1m(*window, "SENSEX")
    days = sorted(set(sp["timestamp"].dt.date))
    return [d for d in days if d not in exps and next((e for e in sorted(exps) if e > d), None)]


def nearest_after(d: date) -> date | None:
    for e in L.expiries("SENSEX"):
        if e > d and d in L.trade_days("SENSEX", e):
            return e
    return None


PODS = [pod("R1a_1lot", "short straddle", straddle("SELL"), SHORT, 1),
        pod("R1a_5lots", "short straddle", straddle("SELL"), SHORT, 5),
        pod("R1b", "long straddle", straddle("BUY"), LONG, 1, skip_events=False, measure="premium"),
        pod("R1c", "short iron fly ±6", fly(6), SHORT, 5)]
PLACEBO = [pod("R1d_1lot", "placebo short straddle (non-expiry day, nearest weekly)", straddle("SELL"), SHORT[:1], 1,
               days=non_expiry_days, expiry_for=nearest_after),
           pod("R1d_5lots", "placebo short straddle (non-expiry day, nearest weekly)", straddle("SELL"), SHORT[:1], 5,
               days=non_expiry_days, expiry_for=nearest_after)]


def overlap_lines(name: str, nifty: set) -> list[str]:
    t = pd.read_csv(RES / f"S3_{name}_trades.csv")
    lab = t["cell"].iloc[0] if len(t) else ""
    p = t[(t["cell"] == lab) & (t["cost_mult"] == 1.0) & t["traded"]]
    p["day"] = pd.to_datetime(p["day"]).dt.date
    both = p[p["day"].isin(nifty)]
    rest = p[~p["day"].isin(nifty)]
    return [f"- {name}: {len(both)} days are also NIFTY expiries ({', '.join(str(d) for d in both['day'])}); "
            f"without them {len(rest)} trades, {rest['net_pct_premium'].mean():+.1f} % (t {t_stat(rest['net_pct_premium']):.2f})."]


def placebo_lines(name: str) -> list[str]:
    t = pd.read_csv(RES / f"S3_{name}_trades.csv")
    p = t[(t["cost_mult"] == 1.0) & t["traded"]].copy()
    p["day"], p["expiry"] = pd.to_datetime(p["day"]).dt.date, pd.to_datetime(p["expiry"]).dt.date
    td = sorted(set(L.spot_1m(*TEST, "SENSEX")["timestamp"].dt.date))
    p["sessions"] = [sum(1 for x in td if d < x <= e) for d, e in zip(p["day"], p["expiry"])]
    out = [f"| {name} | all | {len(p)} | {p['net_pct_premium'].mean():+.1f} % | {t_stat(p['net_pct_premium']):.2f} |"]
    for k, g in p.groupby(p["sessions"].clip(upper=3)):
        out.append(f"| {name} | {'3+' if k >= 3 else k} | {len(g)} | {g['net_pct_premium'].mean():+.1f} % | {t_stat(g['net_pct_premium']):.2f} |")
    return out


def main() -> None:
    from scanner.s3_diagnostics import traded_expiries
    nifty = traded_expiries("NIFTY") | set(L.expiries("NIFTY"))
    out = {p.name: run_pod(p) for p in PODS + PLACEBO}
    a, b = out["R1a_5lots"], out["R1b"]
    rep = a.get("mean_pct", -1) > 0 and a.get("t_pct", 0) >= 2 and b.get("mean_pct", 1) < 0
    lines = ["# S3 R1 · SENSEX replication of the late-expiry premium: summary", "",
             f"Mean effect (R1a 5 lots net > 0 with t >= 2, and R1b < 0): **{'REPLICATES' if rep else 'DOES NOT REPLICATE'}**.", "",
             "| Cell | Trades | Net % | t | Win rate | Gate |", "|---|---|---|---|---|---|"]
    for k, v in out.items():
        lines.append(f"| {k} | {v.get('n')} | {v.get('mean_pct', float('nan')):+.1f} % | {v.get('t_pct', float('nan')):.2f} | "
                     f"{v.get('win', float('nan')) * 100:.0f} % | {'PASS' if v.get('pass') else 'FAIL'} |")
    lines += ["", "## Overlap with NIFTY expiry days", ""]
    for k in ("R1a_1lot", "R1a_5lots", "R1b", "R1c"):
        lines += overlap_lines(k, nifty)
    lines += ["", "## Placebo: the same short straddle on non-expiry days, by sessions left to the expiry", "",
              "| Cell | Sessions to expiry | Trades | Net % of credit | t |", "|---|---|---|---|---|"]
    for k in ("R1d_1lot", "R1d_5lots"):
        lines += placebo_lines(k)
    (RES / "S3_R1_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("R1 mean effect", "REPLICATES" if rep else "DOES NOT replicate", {k: (v.get("mean_pct"), v.get("t_pct")) for k, v in out.items()})


if __name__ == "__main__":
    main()
