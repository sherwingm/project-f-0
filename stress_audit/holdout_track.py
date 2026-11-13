"""Prospective-holdout tracker (offline). Reads a paper-ledger JSON file given on the command line and counts the trades that count as holdout.

    python -m stress_audit.holdout_track <ledger.json> [fade|g1]

Counting rule (stress_audit/FREEZE.json): a trade counts only if it was ENTERED after freeze_time_ist and was made under the frozen rule
(S1: rule.strategy == 'fade' and rule.version == 'v12'; G1 ledgers: any closed trade entered after the freeze). Trades before the freeze are
printed as "previously seen - descriptive only". Verdict label = stress_audit/common.verdict (section 7 of PREREG.md), which needs n >= 30.
Reads nothing but the file named; connects to nothing.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import common as C

FREEZE = json.loads((Path(__file__).parent / "FREEZE.json").read_text(encoding="utf-8"))


def main(path: str, kind: str = "fade") -> None:
    cut = pd.Timestamp(FREEZE["freeze_time_ist"])
    L = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = L.get("closed") or L.get("trades") or []
    out = []
    for t in rows:
        opened = t.get("opened_at") or t.get("entry_time") or t.get("entered_at")
        pct = t.get("return_pct", t.get("net_pct"))
        rs = t.get("net_pnl", t.get("net_rs"))
        if kind == "fade" and not ((t.get("rule") or {}).get("strategy") == "fade" and (t.get("rule") or {}).get("version") == "v12"):
            continue
        if opened is None or pct is None:
            continue
        out.append({"opened": pd.Timestamp(opened), "net_pct": float(pct), "net_rs": float(rs or 0.0), "day0": str(pd.Timestamp(opened).date())})
    d = pd.DataFrame(out)
    print(f"file {path}: saved_at {L.get('saved_at')}; freeze {FREEZE['freeze_time_ist']}")
    if d.empty:
        print("no usable closed trades of this kind in the file (keys seen:", sorted(L.keys()), ")")
        return
    after, before = d[d["opened"] > cut], d[d["opened"] <= cut]
    print(f"before the freeze (previously seen, descriptive only): n={len(before)}, mean {before.net_pct.mean():.2f} %, win {100 * (before.net_pct > 0).mean():.0f} %")
    print(f"AFTER the freeze (prospective holdout): n={len(after)}")
    if len(after):
        s = C.summarize(after, rs="net_rs")
        print({k: s.get(k) for k in ("n", "exp_pct", "win_pct", "net_rs", "t_clustered")}, "->", C.verdict(s))
    else:
        print("-> insufficient evidence (n = 0): no trade entered after the freeze is in this file")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "fade")
