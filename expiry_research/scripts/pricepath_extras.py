"""pricepath extras (descriptive only, label Observed; run after pricepath_validate.py, nothing here is re-tuned).

1. expiry_vs_nonexpiry.csv: for every Passed-validation rule, the same condition's rate when t+1 is a weekly expiry
   (W0), a monthly expiry (M0) and not an expiry (X), discovery + validation together, with the base of each context.
2. bn_weekday_check.csv: BANKNIFTY validation. From 2023-09 the weekly expiry moved to Wednesday, so Thursdays that
   are not expiries are a same-weekday placebo for the old Thursday expiry. Normalised range, |cc| and persistence on
   expiry Wednesdays, non-expiry Thursdays, and all other sessions of 2023-09-01 .. 2024-06-30.
3. findings.csv: validation.csv plus 95 % intervals of the validation value (Wilson for rules, t interval of the
   position mean for event candidates).
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pricepath_common import OUT, add_quantile_targets, build_features, cond_mask, disc_quantiles, rate_test  # noqa
from pricepath_discovery import QCOLS, positions  # noqa: E402
from stats_utils import mean_ci, wilson  # noqa: E402


def main():
    V = pd.read_csv(OUT / "validation.csv")
    F = pd.read_csv(OUT / "candidates_frozen.csv").set_index("id")
    PP = {}
    for ul in ("NIFTY", "BANKNIFTY"):
        P = build_features(ul)
        add_quantile_targets(P, disc_quantiles(P, QCOLS))
        PP[ul] = P
    rows = []
    for _, v in V[(V["label"] == "Passed-validation") & (V["type"] == "rule")].iterrows():
        c = F.loc[v["id"]]
        P = PP[c["ul"]]
        sig = cond_mask(P, [x[:3] for x in json.loads(c["cond_json"])])
        for ctx in ("W0", "M0", "X"):
            idx = P.index[P["split"].isin(["discovery", "validation"]) & P["usable"] & P[f"ctx_{ctx}"]]
            r = rate_test(P, idx, sig, c["target"])
            rows.append(dict(id=v["id"], ul=c["ul"], rule=c["rule"], target=c["target"], context=ctx, **r))
    E = pd.DataFrame(rows)
    E.to_csv(OUT / "expiry_vs_nonexpiry.csv", index=False)
    print(E[["id", "ul", "rule", "context", "n", "rate", "base", "effect", "p"]].round(3).to_string(index=False))

    P = PP["BANKNIFTY"]
    W = P[(P["date"] >= "2023-09-01") & (P["split"] == "validation")].copy()
    grp = pd.Series("other", index=W.index)
    grp[W["cal_kind"] == "weekly"] = "weekly_expiry_wed"
    grp[(W["cal_dow"] == "Thursday") & (W["cal_kind"] == "none")] = "thursday_not_expiry"
    grp[W["cal_kind"] == "monthly"] = "monthly_expiry"
    W["grp"] = grp
    out = W.groupby("grp").agg(n=("date", "size"), range_n=("range_n", "mean"), cc_n=("cc_n", "mean"),
                               persist=("persist", "mean"), up=("o_up", "mean")).reset_index()
    out.to_csv(OUT / "bn_weekday_check.csv", index=False)
    print(out.round(3).to_string(index=False))

    lo, hi = [], []
    for ul in PP:
        positions(PP[ul], ul)
    for _, v in V.iterrows():
        c = F.loc[v["id"]]
        P = PP[c["ul"]]
        val = P["split"] == "validation"
        if c["type"] == "rule":
            idx = P.index[val & P["usable"] & P[f"ctx_{c['context']}"]]
            sig = cond_mask(P, [x[:3] for x in json.loads(c["cond_json"])])
            r = rate_test(P, idx, sig, c["target"])
            _, a, b = wilson(r["k"], r["n"])
        else:
            k = int(c["pos"])
            if c["kind"] == "weekly":
                xm = val & P[f"wk_{k}"]
            else:
                xm = val & P[f"mo_{k}"]
            _, a, b = mean_ci(P.loc[xm, c["metric"]].values)
        lo.append(a)
        hi.append(b)
    V["val_ci_lo"], V["val_ci_hi"] = lo, hi
    V.to_csv(OUT / "findings.csv", index=False)


if __name__ == "__main__":
    main()
