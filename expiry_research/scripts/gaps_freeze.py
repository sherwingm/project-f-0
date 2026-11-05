"""Gaps module, step 2: freeze candidates BEFORE any validation statistic (design: reports/lld/gaps.md).

Fixed rule: BH q < 0.10 over the whole discovery family, n >= 30 in the condition group (and >= 30 in the
comparison group for 2-group tests), decision time not a label. Records sha256 of the spec / data / evaluation code.
"""
import datetime as dt
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gaps_common import RES  # noqa: E402

CODE = ["gaps_specs.py", "gaps_common.py", "gaps_eval.py"]


def code_hash():
    h = hashlib.sha256()
    for f in CODE:
        h.update((HERE / f).read_bytes())
    return h.hexdigest()


def main():
    out = RES / "candidates_frozen.csv"
    if out.exists() and "--force" not in sys.argv:
        raise SystemExit(f"{out} exists; candidates are frozen once")
    if (RES / "validation.csv").exists():
        raise SystemExit("validation.csv exists: freezing after validation is not allowed")
    H = pd.read_csv(RES / "hypotheses.csv")
    sel = H["d_bh_sig"] & ~H["d_thin"] & (H["decision_time"] != "label")
    F = H[sel].copy()
    F["rule_exact"] = [r.replace("prm", f"{p:g}") if pd.notna(p) else r for r, p in zip(F["rule"], F["prm"])]
    F["direction"] = np.sign(F["d_effect"]).astype(int)
    F["code_sha256"] = code_hash()
    F["frozen_at"] = dt.datetime.now().isoformat(timespec="seconds")
    cols = ["id", "ul", "group", "rule_exact", "prm", "decision_time", "target", "kind", "direction", "d_n", "d_nB",
            "d_rate", "d_base", "d_effect", "d_ci_lo", "d_ci_hi", "d_p", "d_q", "code_sha256", "frozen_at"]
    F[cols].to_csv(out, index=False)
    print(f"frozen {len(F)} of {len(H)} hypotheses -> {out}")
    print(F[["id", "rule_exact", "d_n", "d_effect", "d_q"]].to_string(index=False))


if __name__ == "__main__":
    main()
