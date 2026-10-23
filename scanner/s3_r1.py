"""S3 R1: SENSEX replication of the late-expiry premium finding (strategies/S3_R1_sensex_late_expiry_replication.md).

    INDEX_STORE=<index-data checkout with SENSEX>/data/index python -m scanner.s3_r1
"""
from __future__ import annotations

from scanner.s3_engine import Leg, Spec
from scanner.s3_pods import Pod, run_pod

LOT = 20


def hm(t):
    return f"{t[0]:02d}:{t[1]:02d}"


def pod(name, title, legs, entry, exit_, lots, measure="credit") -> Pod:
    lab = f"{title} {hm(entry)}→{hm(exit_)}, {lots} lot{'s' if lots > 1 else ''}"
    cell = (entry, exit_)
    return Pod(name=name, title=f"SENSEX {lab}", page="strategies/S3_R1_sensex_late_expiry_replication.md", cells=[cell],
               spec=lambda c, cm=1.0: Spec(lab, legs, entry=c[0], exit=c[1], lots=lots, cost_mult=cm), primary=cell,
               neighbours=[], label=lambda c: lab, skip_events=True, measure=measure, underlying="SENSEX", index="SENSEX",
               lot=LOT)


STRADDLE_S = [Leg("SELL", "CE", 0), Leg("SELL", "PE", 0)]
STRADDLE_L = [Leg("BUY", "CE", 0), Leg("BUY", "PE", 0)]
FLY = STRADDLE_S + [Leg("BUY", "CE", 4), Leg("BUY", "PE", -4)]
PODS = [pod("R1a_1lot", "short straddle", STRADDLE_S, (14, 30), (15, 15), 1),
        pod("R1a_5lots", "short straddle", STRADDLE_S, (14, 30), (15, 15), 5),
        pod("R1b", "long straddle", STRADDLE_L, (14, 45), (15, 25), 1, measure="premium"),
        pod("R1c", "short iron fly ±4", FLY, (14, 30), (15, 15), 5)]


def main() -> None:
    out = {p.name: run_pod(p) for p in PODS}
    a, b = out["R1a_5lots"], out["R1b"]
    rep = a.get("mean_pct", -1) > 0 and a.get("t_pct", 0) >= 2 and b.get("mean_pct", 1) < 0
    print("R1 mean effect", "REPLICATES" if rep else "DOES NOT replicate", {k: (v.get("mean_pct"), v.get("t_pct")) for k, v in out.items()})


if __name__ == "__main__":
    main()
