"""Gaps module, step 3: evaluate ONLY the frozen candidates on validation rows, once (design: reports/lld/gaps.md).

Pass rule (fixed in advance): same sign as discovery, one-sided p < 0.05 vs the validation base / comparison group,
and |effect| >= half the discovery |effect|. Refuses to run if the spec / data / evaluation code changed since
freezing, or if validation.csv already exists (use --force only to reproduce the identical file).
Writes results/gaps/validation.csv, results/gaps/predictions/<id>.csv and adds label columns to hypotheses.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gaps_common import RES  # noqa: E402
from gaps_eval import evaluate, masks, passes  # noqa: E402
from gaps_freeze import code_hash  # noqa: E402
from gaps_specs import all_specs  # noqa: E402


def check_hash():
    F = pd.read_csv(RES / "candidates_frozen.csv")
    if set(F["code_sha256"]) != {code_hash()}:
        raise SystemExit("code changed since freezing: validation refused")
    return F


def main():
    F = check_hash()
    out = RES / "validation.csv"
    if out.exists() and "--force" not in sys.argv:
        raise SystemExit(f"{out} exists; validation is run once")
    specs = {s["id"]: s for s in all_specs()}
    prep = {ul: pd.read_parquet(RES / f"prepared_{ul}.parquet") for ul in ["NIFTY", "BANKNIFTY"]}
    (RES / "predictions").mkdir(exist_ok=True)
    rows = []
    for _, c in F.iterrows():
        sp = specs[c["id"]]
        P = prep[sp["ul"]]
        V = P[P["split"] == "validation"]
        r = evaluate(sp, V, sign=int(c["direction"]))
        ok, s_ok, p_ok, size_ok = passes(c["d_effect"], r)
        rows.append({"id": c["id"], "ul": c["ul"], "rule_exact": c["rule_exact"], "direction": c["direction"],
                     "d_n": c["d_n"], "d_rate": c["d_rate"], "d_base": c["d_base"], "d_effect": c["d_effect"],
                     "d_p": c["d_p"], "d_q": c["d_q"], **{f"v_{k}": v for k, v in r.items()},
                     "same_sign": s_ok, "p1_lt_05": p_ok, "half_effect": size_ok,
                     "label": "Passed-validation" if ok else "Rejected"})
        # per-row predictions (both splits): rows in condition group A and comparison group B
        for nm, S in [("discovery", P[P["split"] == "discovery"]), ("validation", V)]:
            A, B, _ = masks(sp, S)
            o = S.loc[A | (B if B is not None else False), ["y_date", "split", "k", "d0", "dplus1", "kind_ctx",
                                                            "regime", "y_gap_pct", sp["outcome"]]].copy()
            o["group"] = np.where(A[o.index], "condition", "comparison")
            o.to_csv(RES / "predictions" / f"{c['id']}_{nm}.csv", index=False)
    Vd = pd.DataFrame(rows)
    Vd.to_csv(out, index=False)
    H = pd.read_csv(RES / "hypotheses.csv")
    H = H.drop(columns=[c for c in H.columns if c.startswith("v_") or c in ("label", "frozen")], errors="ignore")
    H["frozen"] = H["id"].isin(F["id"])
    H = H.merge(Vd[["id", "v_n", "v_nB", "v_rate", "v_base", "v_effect", "v_p1", "label"]], on="id", how="left")
    H["label"] = H["label"].fillna(pd.Series(np.where(H["d_thin"], "Observed (thin, n < 30)", "Observed (not BH-significant)"), index=H.index))
    H.to_csv(RES / "hypotheses.csv", index=False)
    pd.set_option("display.width", 250)
    print(Vd[["id", "rule_exact", "d_effect", "v_n", "v_nB", "v_rate", "v_base", "v_effect", "v_p1", "label"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
