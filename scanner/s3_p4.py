"""S3 P4: NIFTY opening-range breakout, long ATM option with a trailing stop (strategies/S3_P4_orb_directional.md).

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_p4            # test window
    ... python -m scanner.s3_p4 --holdout          # once, only after the test gate passed and the review
"""
from __future__ import annotations

import argparse
from datetime import date, time, timedelta

import pandas as pd

from index_data import load as L
from scanner import s3_regime as G
from scanner.s3_engine import Leg, Spec, run_day
from scanner.s3_p1 import EVENTS, HALVES, TEST, t_stat, vix_at
from scanner.s3_pods import HOLDOUT, HOLDOUT_HALVES, RES, Pod, sharpe_of, write_report

ORS = [15, 30]
TRAILS = [0.20, 0.25, 0.30]
STOPS = [0.20, 0.25, 0.30, None]
PRIMARY = (15, 0.25, 0.25)
NEIGHBOURS = [(15, 0.20, 0.25), (15, 0.30, 0.25), (15, 0.25, 0.20), (15, 0.25, 0.30)]
CELLS = [(o, tr, sp) for o in ORS for tr in TRAILS for sp in STOPS]
LAST_SIGNAL = time(13, 0)
VIX_MAX = 14.0


def label(c) -> str:
    o, tr, sp = c
    return f"OR {o} min · trail {int(round(tr * 100))} % · stop {'none' if sp is None else f'{int(round(sp * 100))} %'}"


def signal(day_spot: pd.DataFrame, minutes: int):
    """(side, signal minute) of the first close beyond the opening range, 09:15 + `minutes` → 13:00; else None."""
    t1 = (pd.Timestamp("2000-01-01 09:15") + pd.Timedelta(minutes=minutes)).time()
    t = day_spot["timestamp"].dt.time
    rng = day_spot[(t >= time(9, 15)) & (t < t1)]
    rest = day_spot[(t >= t1) & (t <= LAST_SIGNAL)]
    if rng.empty or rest.empty:
        return None
    hi, lo = rng["high"].max(), rng["low"].min()
    for r in rest.itertuples():
        if r.close > hi:
            return "CE", r.timestamp
        if r.close < lo:
            return "PE", r.timestamp
    return None


def expiry_after(day: date) -> date | None:
    """The nearest weekly expiry with at least one session left after `day`, with a chain file on `day`."""
    for e in L.expiries("NIFTY"):
        if e > day and day in L.trade_days("NIFTY", e):
            return e
    return None


def spec(c, side: str, entry: tuple, cost_mult: float = 1.0) -> Spec:
    o, tr, sp = c
    return Spec(label(c), [Leg("BUY", side, 0)], entry=entry, exit=(15, 15), stop=sp, trail=tr, cost_mult=cost_mult)


def collect(window: tuple) -> tuple[pd.DataFrame, int]:
    sp = L.spot_1m(*window)
    sp["d"] = sp["timestamp"].dt.date
    daily = G.daily()
    rows, vcache, n = [], {}, 0
    for day, g in sp.groupby("d"):
        n += 1
        prev = daily[daily.index < day].iloc[-1]
        trend = "CE" if prev["close"] > prev["ema20"] else "PE"
        e = expiry_after(day)
        for o in ORS:
            sg = signal(g, o)
            cells = [c for c in CELLS if c[0] == o] + ([PRIMARY + (2.0,)] if o == PRIMARY[0] else [])
            for c in cells:
                cell, cm = (c[:3], c[3]) if len(c) > 3 else (c, 1.0)
                base = {"day": day, "cell": label(cell), "cost_mult": cm, "event": day in EVENTS,
                        "weekday": day.strftime("%a"), "expiry": e}
                if sg is None or e is None:
                    rows.append({**base, "skip": "no breakout" if sg is None else "no expiry", "eligible": False})
                    continue
                side, ts = sg
                ent = ts + timedelta(minutes=1)
                r = run_day(spec(cell, side, (ent.hour, ent.minute), cm), day, e)
                rows.append({**r, **base, "side": side, "signal": ts.strftime("%H:%M"),
                             "vix": vix_at(day, ts.hour, ts.minute, vcache), "trend_agrees": side == trend,
                             "eligible": side == trend})
    return pd.DataFrame(rows), n


POD = Pod(name="P4", title="NIFTY 15-min opening-range breakout, long ATM option, 25 % stop + 25 % trail",
          page="strategies/S3_P4_orb_directional.md", cells=CELLS, spec=None, primary=PRIMARY, neighbours=NEIGHBOURS,
          label=label, skip_events=False, vix=(0.0, VIX_MAX - 0.001), measure="premium")


def side_lines(allt: pd.DataFrame) -> list[str]:
    p = allt[(allt["cell"] == label(PRIMARY)) & (allt["cost_mult"] == 1.0) & (allt["skip"].fillna("") == "")]
    ta = p["trend_agrees"].fillna(False).astype(bool)
    lowv = p["vix"] < VIX_MAX
    out = ["", "## Primary cell by filter (side report, not the gate)", "",
           "| Filter | Trades | Net % of premium | Win rate | t |", "|---|---|---|---|---|"]
    for name, m in [("no filter", pd.Series(True, index=p.index)), ("trend only", ta), ("VIX < 14 only", lowv),
                    ("both (primary)", ta & lowv), ("both, calls", ta & lowv & (p["side"] == "CE")),
                    ("both, puts", ta & lowv & (p["side"] == "PE"))]:
        g = p[m]
        out.append(f"| {name} | {len(g)} | {g['net_pct_premium'].mean():+.1f} % | {(g['net_rs'] > 0).mean() * 100:.0f} % | "
                   f"{t_stat(g['net_pct_premium']):.1f} |" if len(g) else f"| {name} | 0 | – | – | – |")
    q = p[ta & lowv]
    if len(q):
        out += ["", f"Primary exits: {q['reason'].value_counts().to_dict()}; median signal time "
                f"{sorted(q['signal'])[len(q) // 2]}."]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true")
    a = ap.parse_args()
    if a.holdout:
        rep = RES / "S3_P4_report.md"
        if not rep.exists() or "Verdict: **PASS**" not in rep.read_text(encoding="utf-8"):
            raise SystemExit("the holdout runs only after the test window passed the gate (DECISIONS.md)")
    window, halves = (HOLDOUT, HOLDOUT_HALVES) if a.holdout else (TEST, HALVES)
    allt, n = collect(window)
    v = write_report(POD, allt, n, window, halves, a.holdout, extra=side_lines(allt))
    if a.holdout:
        ts = sharpe_of("P4", False, label(PRIMARY))
        print("holdout", "PASS" if v.get("mean_pct", -1) > 0 and v.get("sharpe", -9) >= 0.7 * ts else "FAIL",
              v.get("sharpe"), ts)


if __name__ == "__main__":
    main()
