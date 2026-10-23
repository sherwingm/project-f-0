"""S3 P7: NIFTY expiry-day late short iron fly ±4, no stop, 5 lots (strategies/S3_P7_expiry_late_fly_5lots.md).

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_p7            # test window (in-sample)
    ... python -m scanner.s3_p7 --holdout          # the real test, once, after the review
"""
from __future__ import annotations

import argparse

import pandas as pd

from scanner.s3_engine import Leg, Spec
from scanner.s3_p1 import summary
from scanner.s3_pods import RES, Pod, run_pod, sharpe_of

LOTS = 5
WINDOWS = [((14, 30), (15, 15)), ((14, 30), (15, 25)), ((14, 45), (15, 15)), ((14, 45), (15, 25))]
PRIMARY = WINDOWS[0]
NEIGHBOURS = WINDOWS[1:]


def hm(t):
    return f"{t[0]:02d}:{t[1]:02d}"


def label(c):
    return f"fly ±4 {hm(c[0])}→{hm(c[1])} no stop, {LOTS} lots"


def spec(c, cost_mult=1.0) -> Spec:
    return Spec(label(c), [Leg("SELL", "CE", 0), Leg("SELL", "PE", 0), Leg("BUY", "CE", 4), Leg("BUY", "PE", -4)],
                entry=c[0], exit=c[1], lots=LOTS, cost_mult=cost_mult)


POD = Pod(name="P7", title=f"NIFTY expiry-day short iron fly ±4 14:30 → 15:15, no stop, {LOTS} lots (lead from P2s / P6)",
          page="strategies/S3_P7_expiry_late_fly_5lots.md", cells=WINDOWS, spec=spec, primary=PRIMARY,
          neighbours=NEIGHBOURS, label=label, skip_events=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true")
    a = ap.parse_args()
    if not a.holdout:
        run_pod(POD)
        return
    rep = RES / "S3_P7_report.md"
    if not rep.exists() or "Verdict: **PASS**" not in rep.read_text(encoding="utf-8"):
        raise SystemExit("the holdout runs only after the test window passed the gate (DECISIONS.md)")
    v = run_pod(POD, holdout=True)
    t = pd.read_csv(RES / "S3_P7_holdout_trades.csv")
    p = t[(t["cell"] == label(PRIMARY)) & (t["cost_mult"] == 1.0) & t["traded"]]
    s = summary(p)
    ts = sharpe_of("P7", False, label(PRIMARY))
    ok = s.get("mean_pct", -1) > 0 and v.get("sharpe", -9) >= 0.7 * ts and abs(min(s["worst_rs"], 0)) < s["avg_month_rs"]
    print(f"HOLDOUT {'PASS' if ok else 'FAIL'}: mean {s.get('mean_pct'):.2f} %, Sharpe {v.get('sharpe'):.3f} vs test {ts:.3f}, "
          f"worst {s['worst_rs']:.0f} vs avg month {s['avg_month_rs']:.0f}")


if __name__ == "__main__":
    main()
