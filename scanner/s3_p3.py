"""S3 P3: NIFTY 1-3 DTE iron condor (strategies/S3_P3_short_dte_condor.md).

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_p3            # test window
    ... python -m scanner.s3_p3 --holdout          # once, only after the test gate passed and the review
"""
from __future__ import annotations

import argparse
from datetime import date

import pandas as pd

from index_data import load as L
from index_data.instruments import STRIKE_STEP
from scanner import s3_regime as G
from scanner.s3_engine import Leg, Spec, chain_between, simulate, spot_at
from scanner.s3_p1 import EVENTS, HALVES, TEST, vix_at
from scanner.s3_pods import HOLDOUT, HOLDOUT_HALVES, RES, Pod, sharpe_of, write_report

STEP = STRIKE_STEP["NIFTY"]
ENTRY = (15, 0)
KS = [1, 2, 3]
DELTAS = [0.15, 0.175, 0.20]
WINGS = [2, 4]
TARGETS = [0.5, None]
STOPS = [1.0, 2.0, None]
PRIMARY = (2, 0.175, 2, 0.5, 1.0)
NEIGHBOURS = [(2, 0.15, 2, 0.5, 1.0), (2, 0.20, 2, 0.5, 1.0), (1, 0.175, 2, 0.5, 1.0), (3, 0.175, 2, 0.5, 1.0)]
CELLS = [(k, dl, w, tg, sp) for k in KS for dl in DELTAS for w in WINGS for tg in TARGETS for sp in STOPS]


def label(c) -> str:
    k, dl, w, tg, sp = c
    return (f"T-{k} 15:00 · delta {dl:g} · wings {w} · target {'none' if tg is None else f'{int(tg * 100)} %'} · "
            f"stop {'none' if sp is None else f'{int(sp * 100)} %'}")


def condor(c, short_ce: float, short_pe: float, atm: float, cost_mult: float = 1.0) -> Spec:
    k, dl, w, tg, sp = c
    oc, op = int(round((short_ce - atm) / STEP)), int(round((short_pe - atm) / STEP))
    return Spec(label(c), [Leg("SELL", "CE", oc), Leg("SELL", "PE", op), Leg("BUY", "CE", oc + w), Leg("BUY", "PE", op - w)],
                entry=ENTRY, exit=(15, 15), stop=sp, target=tg, cost_mult=cost_mult)


def event_in(a: date, b: date) -> bool:
    return any(a <= e <= b for e in EVENTS)


def collect(window: tuple) -> tuple[pd.DataFrame, int]:
    exps = [e for e in L.expiries("NIFTY") if window[0] <= e <= window[1] and e in L.trade_days("NIFTY", e)]
    rows, vcache = [], {}
    for e in exps:
        for k in KS:
            day = G.days_before(e, k)
            base = {"expiry": e, "k": k}
            if day is None or day not in L.trade_days("NIFTY", e):
                for c in [c for c in CELLS if c[0] == k]:
                    rows.append({**base, "day": day, "cell": label(c), "cost_mult": 1.0, "skip": "no chain on entry day",
                                 "event": False})
                continue
            s = spot_at(day, *ENTRY)
            chain = chain_between("NIFTY", e, day, e)
            at = L.at(day, *ENTRY)
            vix, adx = vix_at(day, *ENTRY, vcache), G.prev_value(day, "adx14")
            meta = {**base, "day": day, "vix": vix, "adx": adx, "event": event_in(day, e), "weekday": day.strftime("%a")}
            day_chain = chain[chain["timestamp"].dt.date == day]
            atm = round(s / STEP) * STEP if s else None
            for dl in DELTAS:
                ce = G.strike_by_delta(day_chain, "CE", s, at, e, dl) if s else None
                pe = G.strike_by_delta(day_chain, "PE", s, at, e, dl) if s else None
                todo = [c for c in CELLS if c[0] == k and c[1] == dl]
                if k == PRIMARY[0] and dl == PRIMARY[1]:
                    todo += [PRIMARY + (2.0,)]
                for c in todo:
                    cell, cm = (c[:5], c[5]) if len(c) > 5 else (c, 1.0)
                    if not (ce and pe):
                        rows.append({**meta, "cell": label(cell), "cost_mult": cm, "skip": f"no strike near delta {dl:g}"})
                        continue
                    r = simulate(chain, s, day, condor(cell, ce[0], pe[0], atm, cm), L.lot_on(day), "NIFTY", e)
                    rows.append({**r, **meta, "cell": label(cell), "cost_mult": cm, "delta_ce": round(ce[1], 3),
                                 "delta_pe": round(pe[1], 3), "short_ce": ce[0], "short_pe": pe[0]})
    return pd.DataFrame(rows), len(exps)


POD = Pod(name="P3", title="NIFTY 1-3 DTE iron condor (T-2 15:00, 0.175 delta, wings 2, 50 % target, 100 % stop)",
          page="strategies/S3_P3_short_dte_condor.md", cells=CELLS, spec=None, primary=PRIMARY, neighbours=NEIGHBOURS,
          label=label, skip_events=True)


def side_lines(allt: pd.DataFrame) -> list[str]:
    p = allt[(allt["cell"] == label(PRIMARY)) & (allt["cost_mult"] == 1.0) & (allt["skip"].fillna("") == "") & ~allt["event"]]
    out = ["", "## Primary cell with the research's regime filters (side report, not the gate)", "",
           "| Filter | Trades | Net % of credit | Win rate |", "|---|---|---|---|"]
    for name, m in [("none", p["vix"].notna()), ("VIX 14-20", p["vix"].between(14, 20)), ("ADX < 20", p["adx"] < 20),
                    ("VIX 14-20 and ADX < 20", p["vix"].between(14, 20) & (p["adx"] < 20))]:
        g = p[m]
        out.append(f"| {name} | {len(g)} | {g['net_pct_premium'].mean():+.1f} % | {(g['net_rs'] > 0).mean() * 100:.0f} % |"
                   if len(g) else f"| {name} | 0 | – | – |")
    if len(p):
        out += ["", f"Average |delta| of the shorts: CE {p['delta_ce'].mean():.3f}, PE {p['delta_pe'].mean():.3f}; average distance "
                f"CE {(p['short_ce'] - p['spot']).mean():+.0f} pts, PE {(p['short_pe'] - p['spot']).mean():+.0f} pts. "
                f"Exits: {p['reason'].value_counts().to_dict()}."]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true")
    a = ap.parse_args()
    if a.holdout:
        rep = RES / "S3_P3_report.md"
        if not rep.exists() or "Verdict: **PASS**" not in rep.read_text(encoding="utf-8"):
            raise SystemExit("the holdout runs only after the test window passed the gate (DECISIONS.md)")
    window, halves = (HOLDOUT, HOLDOUT_HALVES) if a.holdout else (TEST, HALVES)
    allt, n = collect(window)
    v = write_report(POD, allt, n, window, halves, a.holdout, extra=side_lines(allt))
    if a.holdout:
        ts = sharpe_of("P3", False, label(PRIMARY))
        print("holdout", "PASS" if v.get("mean_pct", -1) > 0 and v.get("sharpe", -9) >= 0.7 * ts else "FAIL", v.get("sharpe"), ts)


if __name__ == "__main__":
    main()
