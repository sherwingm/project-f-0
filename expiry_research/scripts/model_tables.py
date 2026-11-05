"""Report tables of the `model` module (resumed run, 2026-11-05). Reads only results/model/*.csv written by
model_discovery.py, model_validate.py, model_walkforward.py and model_finalize.py; computes no new test.

Writes results/model/tab_*.csv and prints markdown tables (results/model/tables_stdout.txt via the caller).
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from model_common import BIN_TARGETS, OUT  # noqa: E402

DIRECTION = ["gap_up", "ret15_up", "ret30_up", "ret60_up", "oc_up", "gap_filled"]
MAGNITUDE = ["big_exc", "big_cc", "gap_abs", "high_pc", "low_pc"]


def md(df, nd=3):
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.{nd}f}")
    d.columns = [str(c) for c in d.columns]
    cols = list(d.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def root(f):
    f = re.sub(r"^l1_", "", f)
    return f


def feats_of(rule):
    return sorted({root(m.group(1)) for m in re.finditer(r"([a-z0-9_]+) (?:<=|>=|<|>|==)", rule)})


def main():
    H = pd.read_csv(OUT / "hypotheses.csv")
    V = pd.read_csv(OUT / "candidates_validation.csv")
    M = pd.read_csv(OUT / "wf_metrics.csv")
    PI = pd.read_csv(OUT / "wf_perm_importance.csv")

    # ---- family sizes
    fam = H.groupby("stage")["p"].apply(lambda s: int(s.notna().sum()))
    sig = H.groupby("stage")["sig_all"].sum()
    sigd = H.groupby("stage")["sig_disc"].sum()
    F = pd.DataFrame(dict(tests=fam, bh_sig_discovery_family=sigd, bh_sig_whole_log=sig)).reset_index()
    F.to_csv(OUT / "tab_family.csv", index=False)
    print("## family\n" + md(F))

    # ---- discovery: significance by target group and feature root
    D = H[H.stage.isin(["univariate", "pair", "tree"])].copy()
    D["group"] = np.where(D.target.isin(DIRECTION), "direction", "magnitude")
    g = (D.groupby(["ul", "group", "target"]).agg(tests=("p", "count"), bh_sig=("sig_disc", "sum"),
                                                   min_p=("p", "min")).reset_index())
    g.to_csv(OUT / "tab_discovery_by_target.csv", index=False)
    print("## discovery by target\n" + md(g, 4))
    U = D[(D.stage == "univariate") & D.sig_disc.astype(bool)].copy()
    U["feature"] = U.rule.map(lambda r: feats_of(r)[0] if feats_of(r) else "")
    fr = (U.groupby(["group", "feature"]).size().rename("bh_sig_univariate").reset_index()
          .sort_values(["group", "bh_sig_univariate"], ascending=[True, False]))
    fr.to_csv(OUT / "tab_discovery_feature_roots.csv", index=False)
    print("## top feature roots (univariate BH-sig count)\n" + md(fr.groupby("group").head(10)))
    # strongest univariate per directional target (both ULs, all cutoffs) -- what little direction there is
    du = (D[(D.stage == "univariate") & D.target.isin(DIRECTION)].sort_values("p")
          .groupby(["ul", "target"]).head(1)[["ul", "target", "cutoff", "context", "rule", "n", "rate", "base",
                                               "effect", "p", "q_bh_disc"]])
    du.to_csv(OUT / "tab_direction_best_univariate.csv", index=False)
    print("## best univariate per directional target\n" + md(du, 4))

    # ---- frozen candidates: labels
    V["group"] = np.where(V.target.isin(DIRECTION), "direction", "magnitude")
    lab = V.groupby(["ul", "group", "label"]).size().unstack(fill_value=0).reset_index()
    lab.to_csv(OUT / "tab_candidate_labels.csv", index=False)
    print("## candidate labels\n" + md(lab))
    keep = ["cid", "ul", "cutoff", "target", "context", "rule", "direction", "disc_n", "disc_rate", "disc_base",
            "disc_effect", "disc_p", "q_bh_disc", "val_n", "val_rate", "val_base", "val_effect", "val_p_one_sided",
            "label", "robust", "drop1_effect", "years_same_sign", "years_tested", "vix_terciles_same_sign",
            "vix_terciles_tested", "nbm_effect", "nbp_effect"]
    P = V[V.label == "Passed-validation"][keep]
    P.to_csv(OUT / "tab_passed.csv", index=False)
    print("## passed\n" + md(P[["cid", "ul", "cutoff", "target", "rule", "disc_n", "disc_effect", "val_n",
                                 "val_effect", "val_p_one_sided", "robust"]], 3))
    E = V[V.context.isin(["D0", "D0w", "D0m"])]
    e = E.groupby(["ul", "group", "label"]).size().unstack(fill_value=0).reset_index()
    print("## expiry-context candidates\n" + md(e))

    # ---- walk-forward: primary model vs baselines
    m = M[M.kind == "model"].copy()
    bin_ = m[m.target.isin(BIN_TARGETS)]
    pr = bin_[(bin_.model == "logit") & bin_.subset.isin(["all", "D0"])][
        ["ul", "cutoff", "target", "subset", "test_years", "n", "rate", "acc", "acc_majority", "bal_acc", "auc",
         "auc_lo", "auc_hi", "bss", "p_brier", "ece"]]
    pr["predictable"] = (pr.auc_lo > 0.5) & (pr.p_brier < 0.05)
    pr.to_csv(OUT / "tab_wf_primary_binary.csv", index=False)
    print("## WF primary (logit) binary\n" + md(pr.drop(columns=["test_years"]), 3))
    reg = m[~m.target.isin(BIN_TARGETS) & (m.model == "logit") & m.subset.isin(["all", "D0"])][
        ["ul", "cutoff", "target", "subset", "n", "mae", "mae_naive", "mae_ratio", "p_mae", "spearman"]].copy()
    bp = M[(M.kind == "baseline") & (M.model == "persist")][["ul", "cutoff", "target", "subset", "mae"]].rename(
        columns={"mae": "mae_persist"})
    reg = reg.merge(bp, on=["ul", "cutoff", "target", "subset"], how="left")
    reg["predictable"] = reg.p_mae < 0.05
    reg.to_csv(OUT / "tab_wf_primary_reg.csv", index=False)
    print("## WF primary (ridge) regression\n" + md(reg, 3))

    # every model, AUC on all / D0 (comparison only, no selection)
    cmp_ = bin_[bin_.subset.isin(["all", "D0"])].pivot_table(index=["ul", "cutoff", "target", "subset"],
                                                             columns="model", values="auc").reset_index()
    cmp_.to_csv(OUT / "tab_wf_auc_all_models.csv", index=False)
    print("## AUC all models\n" + md(cmp_, 3))
    bss = bin_[bin_.subset.isin(["all", "D0"])].pivot_table(index=["ul", "cutoff", "target", "subset"],
                                                            columns="model", values="bss").reset_index()
    bss.to_csv(OUT / "tab_wf_bss_all_models.csv", index=False)
    print("## Brier skill all models\n" + md(bss, 3))
    regc = m[~m.target.isin(BIN_TARGETS) & m.subset.isin(["all", "D0"])].pivot_table(
        index=["ul", "cutoff", "target", "subset"], columns="model", values="mae_ratio").reset_index()
    regc.to_csv(OUT / "tab_wf_maeratio_all_models.csv", index=False)
    print("## MAE ratio all models\n" + md(regc, 3))

    # baselines: accuracy for directional targets on all / D0
    b = M[(M.kind == "baseline") & M.target.isin(BIN_TARGETS) & M.subset.isin(["all", "D0"])]
    bb = b.pivot_table(index=["ul", "cutoff", "target", "subset"], columns="model", values="acc").reset_index()
    lg = bin_[(bin_.model == "logit") & bin_.subset.isin(["all", "D0"])][["ul", "cutoff", "target", "subset",
                                                                          "acc", "bal_acc"]]
    bb = bb.merge(lg.rename(columns={"acc": "logit_acc", "bal_acc": "logit_bal_acc"}),
                  on=["ul", "cutoff", "target", "subset"], how="left")
    bb.to_csv(OUT / "tab_wf_accuracy_vs_baselines.csv", index=False)
    print("## accuracy vs baselines\n" + md(bb, 3))

    # precision at the 67th-percentile threshold (logit, all)
    pp = bin_[(bin_.model == "logit") & (bin_.subset == "all")][["ul", "cutoff", "target", "rate", "prec_67",
                                                                "rec_67", "n_pos_67", "prec_050", "n_pos_050"]]
    pp.to_csv(OUT / "tab_wf_precision.csv", index=False)
    print("## precision (logit, all)\n" + md(pp, 3))

    # expiry vs non-expiry rows of the same predictions (logit / ridge, all-days training)
    ex = m[(m.model == "logit") & m.subset.isin(["D0", "nonexp", "D0w", "D0m"])]
    exb = ex[ex.target.isin(BIN_TARGETS)].pivot_table(index=["ul", "cutoff", "target"], columns="subset",
                                                       values="auc").reset_index()
    exn = ex[ex.target.isin(BIN_TARGETS)].pivot_table(index=["ul", "cutoff", "target"], columns="subset",
                                                       values="n").reset_index()
    exb = exb.merge(exn, on=["ul", "cutoff", "target"], suffixes=("_auc", "_n"))
    exb.to_csv(OUT / "tab_wf_expiry_vs_nonexpiry.csv", index=False)
    print("## logit AUC on expiry vs non-expiry rows\n" + md(exb, 3))

    # per-fold AUC / Brier skill of the primary model (binary) and MAE ratio (regression)
    W = pd.read_csv(OUT / "wf_folds.csv")
    wl = W[W.model == "logit"].copy()
    wl["bss"] = 1 - wl.brier / wl.brier_base
    wl["mae_ratio"] = wl.mae / wl.mae_naive
    wl["metric"] = np.where(wl.target.isin(BIN_TARGETS), wl.auc, wl.mae_ratio)
    pf = wl.pivot_table(index=["ul", "cutoff", "target"], columns="fold", values="metric").reset_index()
    pf.to_csv(OUT / "tab_wf_fold_primary.csv", index=False)
    print("## per-fold primary metric (AUC for binary, MAE/naive for regression)\n" + md(pf, 3))

    # primary-model AUC per weekday regime x expiry flag (pooled test rows; small cells flagged)
    from model_walkforward import auc
    rr = []
    for f in sorted(OUT.glob("predictions_*_*.csv")):
        ul, cut = f.stem.split("_")[1], f.stem.split("_")[-1]
        tg = f.stem[len(f"predictions_{ul}_"):-len(cut) - 1]
        if tg not in BIN_TARGETS:
            continue
        Dp = pd.read_csv(f, usecols=["regime", "is_expiry", "y", "logit"])
        for (rg, ie), gg in Dp.groupby(["regime", "is_expiry"]):
            rr.append(dict(ul=ul, cutoff=cut, target=tg, regime=rg, is_expiry=ie, n=len(gg),
                           auc=auc(gg.y.values, gg.logit.values), small_n=len(gg) < 30))
    RR = pd.DataFrame(rr)
    RR.to_csv(OUT / "tab_wf_regime_auc.csv", index=False)
    sel = RR[(RR.ul == "BANKNIFTY") & RR.cutoff.isin(["TCLOSE"])
             & RR.target.isin(["gap_up", "oc_up", "big_exc"])]
    print("## BANKNIFTY TCLOSE logit AUC per regime")
    print(md(sel, 3))

    # permutation importance: top 5 per (ul, cutoff, target) for logit, only where the primary model is predictable
    pred_keys = set(map(tuple, pr[pr.predictable & (pr.subset == "all")][["ul", "cutoff", "target"]].values)) | \
        set(map(tuple, reg[reg.predictable & (reg.subset == "all")][["ul", "cutoff", "target"]].values))
    top = (PI[PI.model == "logit"].sort_values("importance", ascending=False)
           .groupby(["ul", "cutoff", "target"]).head(5))
    top = top[[k in pred_keys for k in map(tuple, top[["ul", "cutoff", "target"]].values)]]
    top.to_csv(OUT / "tab_wf_perm_top.csv", index=False)
    print("## permutation importance top 5 (logit, predictable targets only)\n"
          + md(top[["ul", "cutoff", "target", "feature", "importance"]], 4))


if __name__ == "__main__":
    main()
