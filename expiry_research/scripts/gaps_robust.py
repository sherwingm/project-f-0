"""Gaps module, step 4: robustness of the frozen candidates on discovery + validation (design: reports/lld/gaps.md).

Never changes a label. Slices: all rows, drop the best 1 % of the condition group, per year, per weekday regime,
per VIX tercile (discovery cut points), neighbouring thresholds. Writes results/gaps/robustness.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gaps_common import RES  # noqa: E402
from gaps_eval import evaluate  # noqa: E402
from gaps_specs import all_specs  # noqa: E402
from gaps_validate import check_hash  # noqa: E402


def main():
    F = check_hash()
    specs = {s["id"]: s for s in all_specs()}
    prep = {ul: pd.read_parquet(RES / f"prepared_{ul}.parquet") for ul in ["NIFTY", "BANKNIFTY"]}
    rows = []
    for _, c in F.iterrows():
        sp = specs[c["id"]]
        P = prep[sp["ul"]]
        s = int(c["direction"])

        def add(slice_, val, S, prm=None, drop=False):
            r = evaluate(sp, S, prm=prm, sign=s, drop_best=drop)
            rows.append({"id": c["id"], "slice": slice_, "value": val, "d_effect": c["d_effect"], **r,
                         "same_sign": np.sign(r["effect"]) == s if not np.isnan(r["effect"]) else np.nan,
                         "thin": r["n"] < 30 or (not np.isnan(r["nB"]) and r["nB"] < 30)})

        add("all (disc+val)", "", P)
        add("drop best 1 % of condition group", "", P, drop=True)
        for y in sorted(P["year"].unique()):
            add("year", y, P[P["year"] == y])
        for g in sorted(P["regime"].unique()):
            add("weekday regime", g, P[P["regime"] == g])
        for v in [1, 2, 3]:
            add("VIX tercile", v, P[P["vix_t"] == v])
        for nb in sp["nbrs"]:
            add("neighbour threshold", nb, P, prm=nb)
        for spl in ["discovery", "validation"]:
            add("split", spl, P[P["split"] == spl])
    R = pd.DataFrame(rows)
    R.to_csv(RES / "robustness.csv", index=False)
    pd.set_option("display.width", 250)
    print(R[["id", "slice", "value", "n", "nB", "rate", "base", "effect", "p1", "same_sign", "thin"]]
          .round(4).to_string(index=False))


if __name__ == "__main__":
    main()
