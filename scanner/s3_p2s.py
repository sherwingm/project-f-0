"""S3 P2s: NIFTY expiry-day last-40-minutes short iron fly with a stop (strategies/S3_P2s_expiry_last40_short.md).

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_p2s            # test window
    ... python -m scanner.s3_p2s --holdout          # once, only after the test gate passed and the review
"""
from __future__ import annotations

import argparse

from scanner.s3_engine import Leg, Spec
from scanner.s3_pods import RES, Pod, run_pod, sharpe_of

STRUCTURES = {"fly4": 4, "fly2": 2, "straddle": 0}
ENTRIES = [(14, 30), (14, 45), (15, 0)]
EXITS = [(15, 15), (15, 25)]
STOPS = [0.25, 0.30, 0.35, 0.50, 1.00, None]
PRIMARY = ("fly4", (14, 45), (15, 25), 0.30)
NEIGHBOURS = [("fly4", (14, 45), (15, 25), 0.25), ("fly4", (14, 45), (15, 25), 0.35), ("fly4", (14, 30), (15, 25), 0.30),
              ("fly4", (15, 0), (15, 25), 0.30), ("fly4", (14, 45), (15, 15), 0.30)]


def hm(t):
    return f"{t[0]:02d}:{t[1]:02d}"


def label(c):
    st, en, ex, sp = c
    return f"{st} {hm(en)}→{hm(ex)} stop {'none' if sp is None else f'{int(round(sp * 100))} %'}"


def spec(c, cost_mult=1.0) -> Spec:
    st, en, ex, sp = c
    w = STRUCTURES[st]
    legs = [Leg("SELL", "CE", 0), Leg("SELL", "PE", 0)] + ([Leg("BUY", "CE", w), Leg("BUY", "PE", -w)] if w else [])
    return Spec(label(c), legs, entry=en, exit=ex, stop=sp, cost_mult=cost_mult)


POD = Pod(name="P2s", title="NIFTY expiry-day short iron fly 14:45 → 15:25, 30 % stop",
          page="strategies/S3_P2s_expiry_last40_short.md",
          cells=[(st, en, ex, sp) for st in STRUCTURES for en in ENTRIES for ex in EXITS for sp in STOPS],
          spec=spec, primary=PRIMARY, neighbours=NEIGHBOURS, label=label, skip_events=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true")
    a = ap.parse_args()
    if a.holdout:
        rep = RES / "S3_P2s_report.md"
        if not rep.exists() or "Verdict: **PASS**" not in rep.read_text(encoding="utf-8"):
            raise SystemExit("the holdout runs only after the test window passed the gate (DECISIONS.md)")
        v = run_pod(POD, holdout=True)
        test_sharpe = sharpe_of("P2s", False, label(PRIMARY))
        ok = v.get("mean_pct", -1) > 0 and v.get("sharpe", -9) >= 0.7 * test_sharpe
        print(f"holdout: mean {v.get('mean_pct')} %, Sharpe {v.get('sharpe'):.3f} vs test {test_sharpe:.3f} -> "
              f"{'PASS' if ok else 'FAIL'}")
    else:
        run_pod(POD)


if __name__ == "__main__":
    main()
