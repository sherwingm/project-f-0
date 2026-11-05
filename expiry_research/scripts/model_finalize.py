"""Final bookkeeping of the `model` module: one hypothesis log with BH over the whole family, the descriptive
context profile (discovery tests + validation description) and the summary tables used by the reports."""
import sys
import warnings
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.simplefilter("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from model_common import BIN_TARGETS, CONTEXTS, OUT, TARGETS, ULS, build_frame, ctx_mask  # noqa: E402
from stats_utils import bh, wilson  # noqa: E402


def main():
    H = pd.read_csv(OUT / "hypotheses_discovery.csv")
    V = pd.read_csv(OUT / "candidates_validation.csv")
    W = pd.read_csv(OUT / "wf_tests.csv")
    hv = pd.DataFrame(dict(
        hid=["V" + c[1:] for c in V["cid"]], stage="validation", ul=V["ul"], cutoff=V["cutoff"],
        decision_time=V["decision_time"], target=V["target"], target_type=V["target_type"], context=V["context"],
        rule=V["rule"], rule_json=V["rule_json"], n=V["val_n"], k=V["val_k"], rate=V["val_rate"],
        ci_lo=V["val_ci_lo"], ci_hi=V["val_ci_hi"], base=V["val_base"], effect=V["val_effect"],
        p=V["val_p_one_sided"], direction=V["direction"], small_n=V["val_n"] < 30, note="one-sided; cid " + V["cid"]))
    hw = pd.DataFrame(dict(
        hid=[f"W{i:04d}" for i in range(len(W))], stage="walkforward", ul=W["ul"], cutoff=W["cutoff"],
        target=W["target"], target_type=np.where(W["target"].isin(BIN_TARGETS), "binary", "continuous"),
        context=W["subset"], rule="model " + W["model"] + " vs base rate / naive", n=W["n"], effect=W["effect"],
        p=W["p"], small_n=W["n"] < 30,
        note="effect = Brier skill (binary) or 1 - MAE/MAE_naive; one-sided block-bootstrap p"))
    parts = [H, hv, hw]
    vb = OUT / "wf_vix_baseline.csv"  # added in the resumed run (model_vixbase.py)
    if vb.exists():
        X = pd.read_csv(vb)
        parts.append(pd.DataFrame(dict(
            hid=[f"X{i:04d}" for i in range(len(X))], stage="wf_vixbase", ul=X["ul"], cutoff=X["cutoff"],
            target=X["target"], target_type="binary", context=X["subset"],
            rule="logit (all features) AUC > logit (VIX only) AUC", n=X["n"], effect=X["auc_diff"], p=X["p"],
            small_n=X["n"] < 30, note="one-sided block-bootstrap p of the AUC difference")))
    A = pd.concat(parts, ignore_index=True)
    q, rej = bh(A["p"].values, 0.10)
    A["q_bh_all"] = q
    A["sig_all"] = rej
    A.to_csv(OUT / "hypotheses.csv", index=False)
    fam = {s: int(A.loc[A.stage == s, "p"].notna().sum()) for s in A.stage.unique()}
    print("family sizes:", fam, "total", int(A["p"].notna().sum()))
    print("discovery family (BH over discovery stages):", int(H["p"].notna().sum()),
          "significant", int(H["sig_disc"].sum()))
    print("BH over the whole log: significant", int(rej.sum()))
    print(A.groupby("stage")["sig_all"].sum().to_string())

    # context profile: discovery test (from the log) + validation description (Observed, not a test)
    rows = []
    for ul in ULS:
        F = build_frame(ul, "TCLOSE")
        for tg in TARGETS:
            for sp in ["discovery", "validation"]:
                S = F[(F.split == sp) & F["t_" + tg].notna()]
                y = S["t_" + tg]
                for ctx in CONTEXTS:
                    m = ctx_mask(S, ctx)
                    yy = y[m]
                    r = dict(ul=ul, target=tg, split=sp, context=ctx, n=len(yy), value=float(yy.mean()) if len(yy)
                             else np.nan, base=float(y.mean()))
                    if tg in BIN_TARGETS and len(yy):
                        _, r["ci_lo"], r["ci_hi"] = wilson(int(yy.sum()), len(yy))
                    rows.append(r)
    CP = pd.DataFrame(rows)
    hc = H[H.stage == "context"][["ul", "target", "context", "p", "q_bh_disc"]].rename(
        columns={"p": "disc_p", "q_bh_disc": "disc_q"})
    CP = CP.merge(hc, on=["ul", "target", "context"], how="left")
    CP.to_csv(OUT / "context_profile.csv", index=False)

    # feature-discovery summaries
    D = H[H.stage != "context"]
    s1 = (D.groupby(["ul", "target", "cutoff", "context", "stage"])
          .agg(tests=("p", "count"), bh_sig=("sig_disc", "sum"), min_p=("p", "min")).reset_index())
    s1.to_csv(OUT / "discovery_counts.csv", index=False)
    top = (D[D.stage == "univariate"].sort_values("p").groupby(["ul", "target", "cutoff", "context"]).head(3))
    top[["ul", "target", "cutoff", "context", "rule", "n", "rate", "base", "effect", "p", "q_bh_disc"]].to_csv(
        OUT / "discovery_top_univariate.csv", index=False)
    print("written: hypotheses.csv, context_profile.csv, discovery_counts.csv, discovery_top_univariate.csv")


if __name__ == "__main__":
    main()
