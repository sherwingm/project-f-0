"""review_pricepath: assemble per-candidate verdicts from the review CSVs (run after review_pricepath_checks.py).

Verdict rules (fixed before reading the assembled table):
- leak: any input needs data after the decision time (none found -> not used).
- Passed-validation rule: holds = my recompute passes the pass rule AND validation n >= 30 AND the tradeable target
  (excursion >= 1 % from the t+1 open) passes one-sided p < 0.05 raw AND after the VIX/ATR logistic (validation fit).
  Otherwise weaker-than-claimed (the raw label replicates, but not as an incremental, capturable effect).
- Suggestive rule (validation n < 10): weaker-than-claimed (validation untestable; discovery effect is the VIX / ATR
  level, see vol_adjusted.csv); refuted if the recompute does not replicate the discovery numbers.
- PPC009: judged from ppc009_checks.csv.
Writes results/review_pricepath/verdicts.csv.
"""
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "review_pricepath"


def main():
    R = pd.read_csv(OUT / "recompute.csv").set_index("id")
    T = pd.read_csv(OUT / "tradeable_target.csv")
    V = pd.read_csv(OUT / "vol_adjusted.csv")
    rows = []
    for cid, r in R.iterrows():
        to = T[(T["id"] == cid) & (T["target"] == "t_big_open")].iloc[0]
        g1 = T[(T["id"] == cid) & (T["target"] == "t_gap1")].iloc[0]

        def va(tg, sp, fit):
            x = V[(V["id"] == cid) & (V["target"] == tg) & (V["split"] == sp) & (V["model_fit_on"] == fit)]
            return x.iloc[0] if len(x) else None

        vd, vv, vdo, vvo = (va("t_big", "discovery", "discovery"), va("t_big", "validation", "validation"),
                            va("t_big_open", "discovery", "discovery"), va("t_big_open", "validation", "validation"))
        rep = (r["disc_n"] == r["disc_n_theirs"]) and abs(r["disc_rate"] - r["disc_rate_theirs"]) < 1e-9
        s = (f"disc n={r['disc_n']} {r['disc_rate']:.3f} vs {r['disc_base']:.3f} p={r['disc_p']:.2g}; "
             f"val n={r['val_n']} {r['val_rate']:.3f} [{r['val_lo']:.2f}-{r['val_hi']:.2f}] vs {r['val_base']:.3f} "
             f"p1={r['val_p1']:.3g} (identical to theirs: {rep}); from t+1 open: disc {to['disc_rate']:.3f} vs "
             f"{to['disc_base']:.3f}, val {to['val_rate']:.3f} vs {to['val_base']:.3f} p1={to['val_p1']:.3g}; "
             f"VIX/ATR-adjusted disc obs {vd['obs_rate']:.3f} vs exp {vd['exp_rate']:.3f} p={vd['p']:.2g}")
        if vv is not None:
            s += f"; val obs {vv['obs_rate']:.3f} vs exp {vv['exp_rate']:.3f} p1={vv['p']:.2g}"
        if vvo is not None:
            s += f"; open-target val adj p1={vvo['p']:.2g}"
        s += f"; |gap|>=1 % disc {g1['disc_rate']:.2f} vs {g1['disc_base']:.2f}"
        if r["label"] == "Passed-validation":
            ok = (bool(r["pass_mine"]) and r["val_n"] >= 30 and to["val_p1"] < 0.05 and vvo is not None
                  and vvo["p"] < 0.05)
            verdict = "holds" if ok else "weaker-than-claimed"
        else:
            verdict = "weaker-than-claimed" if rep else "refuted"
        rows.append(dict(id=cid, ul=r["ul"], ctx=r["ctx"], rule=r["rule"], their_label=r["label"], verdict=verdict,
                         recomputed=s, val_n=r["val_n"], open_val_p1=to["val_p1"],
                         voladj_disc_p=vd["p"], voladj_val_p=None if vv is None else vv["p"],
                         voladj_open_val_p=None if vvo is None else vvo["p"]))
    P9 = pd.read_csv(OUT / "ppc009_checks.csv")
    rows.append(dict(id="PPC009", ul="NIFTY", ctx="monthly D-3", rule="monthly D-3 o_cc vs calendar shuffle",
                     their_label="Passed-validation", verdict="refuted",
                     recomputed="see ppc009_checks.csv", val_n=18))
    W = pd.DataFrame(rows)
    W.to_csv(OUT / "verdicts.csv", index=False)
    print(W[["id", "ul", "ctx", "their_label", "verdict", "val_n", "open_val_p1", "voladj_disc_p", "voladj_val_p",
             "voladj_open_val_p"]].round(3).to_string(index=False))
    print(W["verdict"].value_counts().to_string())
    print(P9.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
