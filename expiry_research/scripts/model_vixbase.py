"""Extra walk-forward baseline of the `model` module (added in the resumed run, 2026-11-05, before looking at its
result): is the full logistic model better than the VIX level alone?

Same frames, folds, purge and training rows as model_walkforward.py. Baseline = logistic regression on one
feature, the VIX known at the cutoff (TCLOSE: VIX close of t; D2: VIX close of t-1; T1515: VIX at 15:14 of t).
Compared with the primary model (logit, all features) on the same test rows: AUC of each, AUC difference with a
moving-block bootstrap (block 5, 1000 reps) one-sided p (H1: full model AUC > VIX-only AUC), Brier skill of each vs
the training base rate. Targets: every binary target. Writes results/model/wf_vix_baseline.csv.
"""
import sys
import warnings
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.simplefilter("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from model_common import BIN_TARGETS, CUTOFFS, MINUTE_TARGETS, OUT, ULS, build_frame  # noqa: E402
from model_walkforward import SEED, auc, boot_idx  # noqa: E402

VIXCOL = {"TCLOSE": "f_vix_close", "D2": "l1_f_vix_close", "T1515": "f1515_vix_1514"}


def main():
    rows = []
    for ul in ULS:
        for cut in CUTOFFS:
            F = build_frame(ul, cut).sort_values("target_date").reset_index(drop=True)
            vc = VIXCOL[cut]
            for tg in BIN_TARGETS:
                G = F[F["t_" + tg].notna()].reset_index(drop=True)
                late = tg in MINUTE_TARGETS or cut == "T1515"
                years = [2023, 2024] if late else [2020, 2021, 2022, 2023, 2024]
                parts = []
                for Y in years:
                    tr = G[G.year < Y].iloc[:-1]
                    te = G[G.year == Y]
                    if len(tr) < 100 or len(te) < 20:
                        continue
                    trv = tr[tr[vc].notna()]
                    m = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=5000))
                    m.fit(trv[[vc]], trv["t_" + tg])
                    x = te[[vc]].fillna(trv[vc].median())
                    parts.append(pd.DataFrame(dict(target_date=te["target_date"].values,
                                                   p_vix=m.predict_proba(x)[:, 1])))
                if not parts:
                    continue
                Pv = pd.concat(parts)
                P = pd.read_csv(OUT / f"predictions_{ul}_{tg}_{cut}.csv", usecols=["target_date", "y", "logit",
                                                                                   "p_base", "is_expiry"])
                D = P.merge(Pv, on="target_date", how="inner").sort_values("target_date").reset_index(drop=True)
                for sub, S in [("all", D), ("D0", D[D.is_expiry == True])]:  # noqa: E712
                    S = S.reset_index(drop=True)
                    y, pl, pv, pb = S.y.values, S.logit.values, S.p_vix.values, S.p_base.values
                    if len(S) < 20 or len(np.unique(y)) < 2:
                        continue
                    rng = np.random.default_rng(SEED)
                    dif = []
                    for i in boot_idx(len(S), rng):
                        a, b = auc(y[i], pl[i]), auc(y[i], pv[i])
                        if not (np.isnan(a) or np.isnan(b)):
                            dif.append(a - b)
                    dif = np.array(dif)
                    bb = ((pb - y) ** 2).mean()
                    rows.append(dict(ul=ul, cutoff=cut, target=tg, subset=sub, n=len(S), auc_logit=auc(y, pl),
                                     auc_vix=auc(y, pv), auc_diff=auc(y, pl) - auc(y, pv),
                                     diff_lo=float(np.quantile(dif, 0.025)), diff_hi=float(np.quantile(dif, 0.975)),
                                     p=float((dif <= 0).mean()), bss_logit=1 - ((pl - y) ** 2).mean() / bb,
                                     bss_vix=1 - ((pv - y) ** 2).mean() / bb))
            print(ul, cut, "done", flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "wf_vix_baseline.csv", index=False)
    pd.set_option("display.width", 200)
    print(R.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
