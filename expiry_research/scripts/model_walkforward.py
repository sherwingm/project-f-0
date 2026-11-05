"""Stage 3 of the `model` module: chronological expanding-window walk-forward inside discovery + validation
(design: reports/lld/model.md). Fixed hyper-parameters, no shuffling, one-session purge at each fold edge.

Writes results/model/predictions_<UL>_<target>_<cutoff>.csv, wf_metrics.csv (pooled), wf_folds.csv (per fold),
wf_calibration.csv, wf_perm_importance.csv, wf_tests.csv.
"""
import math
import sys
import time
import warnings
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.simplefilter("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import rankdata, spearmanr  # noqa: E402
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,  # noqa: E402
                              RandomForestClassifier, RandomForestRegressor)
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.linear_model import LogisticRegression, Ridge  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor  # noqa: E402

from model_common import (BIN_TARGETS, CUTOFFS, MINUTE_TARGETS, OUT, TARGETS, ULS, build_frame,  # noqa: E402
                          feature_cols)

SEED = 20261105
REPS = 1000
BLOCK = 5
DIRECTION_TARGETS = ["gap_up", "ret15_up", "ret30_up", "ret60_up", "oc_up"]


def make_models(binary):
    imp = lambda: SimpleImputer(strategy="median")  # noqa: E731
    if binary:
        return {
            "logit": lambda: make_pipeline(imp(), StandardScaler(), LogisticRegression(C=0.1, max_iter=5000)),
            "tree": lambda: make_pipeline(imp(), DecisionTreeClassifier(max_depth=3, min_samples_leaf=40,
                                                                        random_state=0)),
            "rf": lambda: make_pipeline(imp(), RandomForestClassifier(
                n_estimators=300, max_depth=5, min_samples_leaf=20, max_features="sqrt", n_jobs=-1,
                random_state=0)),
            "hgb": lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
                                                          min_samples_leaf=30, l2_regularization=1.0,
                                                          early_stopping=False, random_state=0),
        }
    return {
        "logit": lambda: make_pipeline(imp(), StandardScaler(), Ridge(alpha=10.0)),  # "ridge", same slot
        "tree": lambda: make_pipeline(imp(), DecisionTreeRegressor(max_depth=3, min_samples_leaf=40,
                                                                   random_state=0)),
        "rf": lambda: make_pipeline(imp(), RandomForestRegressor(
            n_estimators=300, max_depth=5, min_samples_leaf=20, max_features="sqrt", n_jobs=-1, random_state=0)),
        "hgb": lambda: HistGradientBoostingRegressor(loss="absolute_error", max_depth=3, learning_rate=0.05,
                                                     max_iter=200, min_samples_leaf=30, l2_regularization=1.0,
                                                     early_stopping=False, random_state=0),
    }


def predict(m, X, binary):
    return m.predict_proba(X)[:, 1] if binary else m.predict(X)


def auc(y, s):
    y = np.asarray(y)
    pos = y == 1
    n1, n0 = pos.sum(), (~pos).sum()
    if n1 == 0 or n0 == 0:
        return np.nan
    r = rankdata(s)
    return float((r[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def boot_idx(n, rng):
    if n < 2 * BLOCK:
        return [rng.integers(0, n, n) for _ in range(REPS)]
    starts = np.arange(n - BLOCK + 1)
    nb = math.ceil(n / BLOCK)
    out = []
    for _ in range(REPS):
        s = rng.choice(starts, nb)
        out.append((s[:, None] + np.arange(BLOCK)[None, :]).ravel()[:n])
    return out


def ece(y, p, bins=5):
    q = pd.qcut(p, bins, labels=False, duplicates="drop")
    e = 0.0
    for b in np.unique(q):
        m = q == b
        e += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(e)


def bin_metrics(D, col, thr_col):
    """D sorted by target_date, has y, p_base and the model column."""
    d = D[D[col].notna()]
    n = len(d)
    if n < 10 or d["y"].nunique() < 2:
        return dict(n=n)
    y, p, pb = d["y"].values, d[col].values.clip(1e-6, 1 - 1e-6), d["p_base"].values.clip(1e-6, 1 - 1e-6)
    yhat = (p >= 0.5).astype(int)
    tp = lambda yh: ((yh == 1) & (y == 1)).sum()  # noqa: E731
    rec1 = y.sum()

    def bal(yh):
        return 0.5 * (((yh == 1) & (y == 1)).sum() / max(rec1, 1) + ((yh == 0) & (y == 0)).sum() / max(n - rec1, 1))
    se, seb = (p - y) ** 2, (pb - y) ** 2
    rng = np.random.default_rng(SEED)
    idx = boot_idx(n, rng)
    aucs = np.array([auc(y[i], p[i]) for i in idx])
    dif = np.array([se[i].mean() - seb[i].mean() for i in idx])
    thr = d[thr_col].values if thr_col in d else np.full(n, np.nan)
    yh67 = (p >= thr).astype(int)
    maj = d["pred_majority"].values
    out = dict(n=n, rate=float(y.mean()), acc=float((yhat == y).mean()), acc_majority=float((maj == y).mean()),
               bal_acc=float(bal(yhat)), auc=auc(y, p), auc_lo=float(np.nanquantile(aucs, 0.025)),
               auc_hi=float(np.nanquantile(aucs, 0.975)), brier=float(se.mean()), brier_base=float(seb.mean()),
               bss=float(1 - se.mean() / seb.mean()), p_brier=float((dif >= 0).mean()),
               logloss=float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()),
               logloss_base=float(-(y * np.log(pb) + (1 - y) * np.log(1 - pb)).mean()), ece=ece(y, p),
               prec_050=float(tp(yhat) / yhat.sum()) if yhat.sum() else np.nan,
               rec_050=float(tp(yhat) / rec1) if rec1 else np.nan,
               n_pos_050=int(yhat.sum()),
               prec_67=float(tp(yh67) / yh67.sum()) if yh67.sum() else np.nan,
               rec_67=float(tp(yh67) / rec1) if rec1 else np.nan, n_pos_67=int(yh67.sum()))
    return out


def hard_metrics(D, col):
    d = D[D[col].notna()]
    n = len(d)
    if n < 10 or d["y"].nunique() < 2:
        return dict(n=n)
    y, yh = d["y"].values, d[col].values.astype(int)
    r1 = y.sum()
    tp = ((yh == 1) & (y == 1)).sum()
    return dict(n=n, rate=float(y.mean()), acc=float((yh == y).mean()),
                acc_majority=float((d["pred_majority"].values == y).mean()),
                bal_acc=float(0.5 * (tp / r1 + ((yh == 0) & (y == 0)).sum() / (n - r1))), auc=auc(y, yh),
                prec_050=float(tp / yh.sum()) if yh.sum() else np.nan, rec_050=float(tp / r1), n_pos_050=int(yh.sum()))


def reg_metrics(D, col):
    d = D[D[col].notna() & D["naive"].notna()]
    n = len(d)
    if n < 10:
        return dict(n=n)
    y, f, nv = d["y"].values, d[col].values, d["naive"].values
    ae, aen = np.abs(f - y), np.abs(nv - y)
    rng = np.random.default_rng(SEED)
    dif = np.array([ae[i].mean() - aen[i].mean() for i in boot_idx(n, rng)])
    rho = spearmanr(f, y).statistic if np.std(f) > 0 else np.nan
    return dict(n=n, mae=float(ae.mean()), mae_naive=float(aen.mean()), mae_ratio=float(ae.mean() / aen.mean()),
                p_mae=float((dif >= 0).mean()), spearman=float(rho))


SUBSETS = {"all": lambda D: D, "D0": lambda D: D[D.is_expiry == True],  # noqa: E712
           "D0w": lambda D: D[(D.is_expiry == True) & (D.kind == "weekly")],  # noqa: E712
           "D0m": lambda D: D[(D.is_expiry == True) & (D.kind == "monthly")],  # noqa: E712
           "nonexp": lambda D: D[D.is_expiry == False]}  # noqa: E712


def main():
    t0 = time.time()
    met, folds, calib, perm = [], [], [], []
    for ul in ULS:
        for cut in CUTOFFS:
            F = build_frame(ul, cut).sort_values("target_date").reset_index(drop=True)
            feats_all = feature_cols(F)
            for tg in TARGETS:
                binary = tg in BIN_TARGETS
                G = F[F["t_" + tg].notna()].reset_index(drop=True)
                late = tg in MINUTE_TARGETS or cut == "T1515"
                years = [2023, 2024] if late else [2020, 2021, 2022, 2023, 2024]
                preds = []
                for Y in years:
                    tr = G[G.year < Y]
                    tr = tr.iloc[:-1]  # purge the last session before the test year
                    te = G[G.year == Y]
                    if len(tr) < 100 or len(te) < 20:
                        continue
                    na = tr[feats_all].isna().mean()
                    feats = [c for c in feats_all if na[c] <= 0.30 and tr[c].nunique() > 1]
                    ytr, yte = tr["t_" + tg].values, te["t_" + tg].values
                    P = te[["date_t", "target_date", "year", "is_expiry", "kind", "s_to_exp", "regime"]].copy()
                    P["fold"] = Y
                    P["n_train"] = len(tr)
                    P["n_features"] = len(feats)
                    P["y"] = yte
                    models = make_models(binary)
                    fitted = {}
                    for name, mk in models.items():
                        m = mk().fit(tr[feats], ytr)
                        fitted[name] = m
                        P[name] = predict(m, te[feats], binary)
                        if binary:
                            P["thr67_" + name] = float(np.quantile(predict(m, tr[feats], binary), 2 / 3))
                    trd = tr[tr.is_expiry == True]  # noqa: E712
                    ted = te.is_expiry == True  # noqa: E712
                    for name in ["logit", "tree"]:
                        col = name + "_D0"
                        P[col] = np.nan
                        ok = len(trd) >= 60 and (not binary or len(np.unique(trd["t_" + tg])) == 2) and ted.any()
                        if ok:
                            m = models[name]().fit(trd[feats], trd["t_" + tg].values)
                            P.loc[ted.values, col] = predict(m, te.loc[ted, feats], binary)
                            if binary:
                                P["thr67_" + col] = float(np.quantile(predict(m, trd[feats], binary), 2 / 3))
                    if binary:
                        base = float(ytr.mean())
                        P["p_base"] = base
                        P["pred_majority"] = int(base >= 0.5)
                        pg = te["b_prevgap"].values
                        P["pred_prevgap"] = np.where(np.isnan(pg), np.nan, (pg > 0).astype(float))
                        P["pred_persist"] = te["b_persist_" + tg].values
                    else:
                        P["naive"] = float(np.median(ytr))
                        P["persist"] = te["b_persist_" + tg].values
                    preds.append(P)
                    # per-fold metrics (no bootstrap needed for the CI here; keep pooled CI below)
                    for name in list(models) + ["logit_D0", "tree_D0"]:
                        if binary:
                            d = P[P[name].notna()]
                            if len(d) >= 10 and d.y.nunique() == 2:
                                pp = d[name].clip(1e-6, 1 - 1e-6)
                                folds.append(dict(ul=ul, cutoff=cut, target=tg, model=name, fold=Y, n=len(d),
                                                  n_train=len(tr), auc=auc(d.y.values, pp.values),
                                                  brier=float(((pp - d.y) ** 2).mean()),
                                                  brier_base=float(((d.p_base - d.y) ** 2).mean()),
                                                  acc=float(((pp >= 0.5) == d.y).mean()),
                                                  acc_majority=float((d.pred_majority == d.y).mean())))
                        else:
                            d = P[P[name].notna()]
                            if len(d) >= 10:
                                folds.append(dict(ul=ul, cutoff=cut, target=tg, model=name, fold=Y, n=len(d),
                                                  n_train=len(tr), mae=float((d[name] - d.y).abs().mean()),
                                                  mae_naive=float((d.naive - d.y).abs().mean()),
                                                  mae_persist=float((d.persist - d.y).abs().mean())))
                    # permutation importance on the test fold (logit and hgb, all-days training)
                    if (not binary) or len(np.unique(yte)) == 2:
                        sc = "roc_auc" if binary else "neg_mean_absolute_error"
                        for name in ["logit", "hgb"]:
                            pi = permutation_importance(fitted[name], te[feats], yte, scoring=sc, n_repeats=5,
                                                        random_state=0)
                            for f, v in zip(feats, pi.importances_mean):
                                perm.append(dict(ul=ul, cutoff=cut, target=tg, model=name, fold=Y, n=len(te),
                                                 feature=f, importance=float(v)))
                if not preds:
                    continue
                D = pd.concat(preds).sort_values("target_date").reset_index(drop=True)
                D.to_csv(OUT / f"predictions_{ul}_{tg}_{cut}.csv", index=False)
                mcols = ["logit", "tree", "rf", "hgb", "logit_D0", "tree_D0"]
                for sname, fn in SUBSETS.items():
                    S = fn(D)
                    for mc in mcols:
                        if binary:
                            r = bin_metrics(S, mc, "thr67_" + mc)
                        else:
                            r = reg_metrics(S, mc)
                        met.append(dict(ul=ul, cutoff=cut, target=tg, subset=sname, model=mc, kind="model",
                                        test_years=",".join(map(str, sorted(D.fold.unique()))), **r))
                    if binary:
                        for bc in ["pred_majority", "pred_prevgap", "pred_persist"]:
                            if bc == "pred_prevgap" and tg not in DIRECTION_TARGETS:
                                continue
                            met.append(dict(ul=ul, cutoff=cut, target=tg, subset=sname, model=bc.replace("pred_", ""),
                                            kind="baseline", **hard_metrics(S, bc)))
                    else:
                        for bc in ["persist"]:
                            met.append(dict(ul=ul, cutoff=cut, target=tg, subset=sname, model=bc, kind="baseline",
                                            **reg_metrics(S, bc)))
                    if binary and sname == "all":
                        for mc in ["logit", "hgb"]:
                            d = S[S[mc].notna()]
                            q = pd.qcut(d[mc], 5, labels=False, duplicates="drop")
                            for b, g in d.groupby(q):
                                calib.append(dict(ul=ul, cutoff=cut, target=tg, model=mc, bin=int(b), n=len(g),
                                                  mean_pred=float(g[mc].mean()), obs_rate=float(g.y.mean())))
                print(f"{ul} {cut} {tg}: rows {len(D)} folds {sorted(D.fold.unique())} "
                      f"[{time.time() - t0:.0f}s]", flush=True)
    M = pd.DataFrame(met)
    M.to_csv(OUT / "wf_metrics.csv", index=False)
    pd.DataFrame(folds).to_csv(OUT / "wf_folds.csv", index=False)
    pd.DataFrame(calib).to_csv(OUT / "wf_calibration.csv", index=False)
    PI = pd.DataFrame(perm)
    PI["w"] = PI["n"]
    agg = (PI.assign(wi=PI.importance * PI.w).groupby(["ul", "cutoff", "target", "model", "feature"])
           .agg(wi=("wi", "sum"), w=("w", "sum"), folds=("fold", "nunique")).reset_index())
    agg["importance"] = agg.wi / agg.w
    agg = agg.drop(columns=["wi", "w"]).sort_values(["ul", "cutoff", "target", "model", "importance"],
                                                     ascending=[True, True, True, True, False])
    agg.to_csv(OUT / "wf_perm_importance.csv", index=False)
    # walk-forward tests for the hypothesis log
    T = M[(M.kind == "model") & M.subset.isin(["all", "D0"])].copy()
    T["p"] = T["p_brier"].where(T["target"].isin(BIN_TARGETS), T.get("p_mae"))
    T["effect"] = T["bss"].where(T["target"].isin(BIN_TARGETS), 1 - T.get("mae_ratio"))
    T = T[T["p"].notna()]
    T[["ul", "cutoff", "target", "subset", "model", "n", "effect", "p", "auc", "auc_lo", "auc_hi"]].to_csv(
        OUT / "wf_tests.csv", index=False)
    # pre-stated rule: primary model = logit (ridge); predictable = AUC CI low > 0.5 and Brier p < 0.05
    prim = M[(M.kind == "model") & (M.model == "logit")].copy()
    if "auc_lo" in prim:
        prim["predictable"] = np.where(prim.target.isin(BIN_TARGETS),
                                       (prim.auc_lo > 0.5) & (prim.p_brier < 0.05), prim.get("p_mae") < 0.05)
    prim.to_csv(OUT / "wf_primary.csv", index=False)
    print("done", f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
