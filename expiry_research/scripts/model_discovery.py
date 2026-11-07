"""Stage 1 of the `model` module: feature discovery on DISCOVERY rows only (design: reports/lld/model.md).

Writes results/model/hypotheses_discovery.csv (every discovery test), results/model/candidates_frozen.csv,
results/model/discovery_stdout.txt (via the caller's redirect). No validation statistic is computed here.
"""
import hashlib
import itertools
import sys
import warnings
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.simplefilter("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402
from sklearn.tree import DecisionTreeClassifier  # noqa: E402

from model_common import (BIN_TARGETS, CONTEXTS, CUTOFFS, OUT, TARGETS, ULS, apply_rule, build_frame,  # noqa: E402
                          ctx_mask, discover_cols, dumps, rule_text)
from stats_utils import bh, binom_p, mean_ci, wilson  # noqa: E402

DT = {"CAL": "calendar (known in advance)", "D2": "close of t-1 (D-2 if s is the expiry)",
      "TCLOSE": "close of t (D-1), entry from the open of s", "T1515": "15:15 of t (D-1)"}
SCOPE_CTX = ["all", "D0", "D0m"]
ROWS = []


def test(cond_y, base_y, binary):
    """cond_y: outcomes in the condition; base_y: outcomes of the base rows (same context, same period)."""
    cond_y = np.asarray(cond_y, float)
    base_y = np.asarray(base_y, float)
    n = len(cond_y)
    if binary:
        k = int(cond_y.sum())
        base = float(base_y.mean()) if len(base_y) else np.nan
        r, lo, hi = wilson(k, n) if n else (np.nan,) * 3
        p = binom_p(k, n, base) if n and 0 < base < 1 else np.nan
        return dict(n=n, k=k, rate=r, ci_lo=lo, ci_hi=hi, base=base, effect=r - base, p=p)
    base = float(base_y.mean()) if len(base_y) else np.nan
    m, lo, hi = mean_ci(cond_y) if n else (np.nan,) * 3
    p = float(stats.ttest_1samp(cond_y, base).pvalue) if n >= 3 else np.nan
    return dict(n=n, k=np.nan, rate=m, ci_lo=lo, ci_hi=hi, base=base, effect=m - base, p=p)


def add(stage, ul, cutoff, target, ctx, rule, res, **extra):
    row = dict(stage=stage, ul=ul, cutoff=cutoff, decision_time=DT[cutoff], target=target,
               target_type="binary" if target in BIN_TARGETS else "continuous", context=ctx,
               rule=rule_text(rule), rule_json=dumps(rule), **res)
    row["direction"] = "higher" if row["effect"] > 0 else "lower"
    row["small_n"] = row["n"] < 30
    row.update(extra)
    ROWS.append(row)


def is_bool(x):
    v = pd.unique(x.dropna())
    return len(v) <= 2 and set(v) <= {0.0, 1.0}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = {(ul, c): build_frame(ul, c) for ul in ULS for c in CUTOFFS}

    # 1. context profile (calendar only): every target, every context vs the all-days rate
    for ul in ULS:
        F = frames[(ul, "TCLOSE")]
        D = F[F.split == "discovery"]
        for tg in TARGETS:
            y = D["t_" + tg]
            ok = y.notna()
            for ctx in CONTEXTS[1:]:
                m = ctx_mask(D, ctx) & ok
                add("context", ul, "CAL", tg, ctx, [], test(y[m], y[ok], tg in BIN_TARGETS))
    print("context tests:", len(ROWS))

    # 2. univariate, 3. pairs, 4. honest trees
    for (ul, cut), F in frames.items():
        D = F[F.split == "discovery"].sort_values("target_date")
        cols = discover_cols(D)
        for tg in TARGETS:
            binary = tg in BIN_TARGETS
            yall = D["t_" + tg]
            okt = yall.notna()
            if okt.sum() < 60:
                continue
            elig = [c for c in cols if D.loc[okt, c].notna().mean() >= 0.7 and D.loc[okt, c].nunique() > 1]
            thr = {}
            for c in elig:
                x = D.loc[okt, c].dropna()
                if is_bool(x):
                    thr[c] = ("bool", None)
                else:
                    thr[c] = ("q", (float(x.quantile(1 / 3)), float(x.quantile(2 / 3)), float(x.median())))
            for ctx in SCOPE_CTX:
                cm = ctx_mask(D, ctx) & okt
                if cm.sum() < 30:
                    continue
                best = {}
                for c in elig:
                    pres = cm & D[c].notna()
                    yb = yall[pres]
                    if thr[c][0] == "bool":
                        rules = [[{"f": c, "op": "==", "v": 1.0}], [{"f": c, "op": "==", "v": 0.0}]]
                    else:
                        q1, q2, _ = thr[c][1]
                        rules = [[{"f": c, "op": "<=", "v": q1}], [{"f": c, "op": ">=", "v": q2}]]
                    for r in rules:
                        mm, _ = apply_rule(D, r)
                        res = test(yall[mm & pres], yb, binary)
                        add("univariate", ul, cut, tg, ctx, r, res)
                        if not np.isnan(res["p"]):
                            best[c] = min(best.get(c, 1.0), res["p"])
                if ctx in ("all", "D0"):
                    top = [c for c, _ in sorted(best.items(), key=lambda kv: kv[1])[:6]]
                    for a, b in itertools.combinations(top, 2):
                        pres = cm & D[a].notna() & D[b].notna()
                        yb = yall[pres]

                        def halves(c):
                            if thr[c][0] == "bool":
                                return [{"f": c, "op": "==", "v": 0.0}, {"f": c, "op": "==", "v": 1.0}]
                            md = thr[c][1][2]
                            return [{"f": c, "op": "<=", "v": md}, {"f": c, "op": ">", "v": md}]
                        for ca in halves(a):
                            for cb in halves(b):
                                r = [ca, cb]
                                mm, _ = apply_rule(D, r)
                                add("pair", ul, cut, tg, ctx, r, test(yall[mm & pres], yb, binary))
                    if binary:
                        tree_rules(D[cm], ul, cut, tg, ctx, elig)
        print(ul, cut, "cumulative tests:", len(ROWS))

    H = pd.DataFrame(ROWS)
    H.insert(0, "hid", [f"H{i:05d}" for i in range(len(H))])
    q, rej = bh(H["p"].values, 0.10)
    H["q_bh_disc"] = q
    H["sig_disc"] = rej
    H.to_csv(OUT / "hypotheses_discovery.csv", index=False)
    print("discovery family size (tests with a p-value):", int(H["p"].notna().sum()), "of", len(H), "rows")
    print("BH-significant at 10 %:", int(rej.sum()))

    # freeze
    S = H[H["sig_disc"] & (H["n"] >= 30)].copy()
    S["complexity"] = S["stage"].map({"context": 0, "univariate": 1, "pair": 2, "tree": 3})
    S = S.sort_values(["p", "complexity"])
    C = S.groupby(["ul", "cutoff", "target", "context"], sort=False).head(3).copy()
    C = C.sort_values(["ul", "target", "cutoff", "context", "p"]).reset_index(drop=True)
    C.insert(0, "cid", [f"M{i:03d}" for i in range(len(C))])
    keep = ["cid", "hid", "stage", "ul", "cutoff", "decision_time", "target", "target_type", "context", "rule",
            "rule_json", "direction", "n", "k", "rate", "ci_lo", "ci_hi", "base", "effect", "p", "q_bh_disc"]
    C = C[keep].rename(columns={c: "disc_" + c for c in ["n", "k", "rate", "ci_lo", "ci_hi", "base", "effect", "p"]})
    C.to_csv(OUT / "candidates_frozen.csv", index=False)
    h = hashlib.sha256((OUT / "candidates_frozen.csv").read_bytes()).hexdigest()
    (OUT / "candidates_frozen.sha256").write_text(h + "\n")
    print("frozen candidates:", len(C), "sha256", h)
    print(C.groupby(["ul", "target"]).size().to_string())


def tree_rules(Dc, ul, cut, tg, ctx, elig):
    """Honest depth-3 tree: fit on the first 60 % of the rows (by date), test each leaf on the last 40 %."""
    Dc = Dc.sort_values("target_date")
    nfit = int(len(Dc) * 0.6)
    fit, hold = Dc.iloc[:nfit], Dc.iloc[nfit:]
    feats = [c for c in elig if fit[c].notna().mean() >= 0.95]
    fitc = fit.dropna(subset=feats)
    if len(fitc) < 80 or len(hold) < 40:
        return
    y = fitc["t_" + tg].values
    leaf = max(20, int(0.08 * len(fitc)))
    clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=leaf, random_state=0).fit(fitc[feats].values, y)
    t = clf.tree_
    paths = []

    def walk(node, conds):
        if t.children_left[node] == -1:
            paths.append((node, conds))
            return
        f, v = feats[t.feature[node]], float(t.threshold[node])
        walk(t.children_left[node], conds + [{"f": f, "op": "<=", "v": v}])
        walk(t.children_right[node], conds + [{"f": f, "op": ">", "v": v}])
    walk(0, [])
    for node, conds in paths:
        rule = simplify(conds)
        mfit, _ = apply_rule(fitc, rule)
        pres_h = hold[[c["f"] for c in rule]].notna().all(axis=1) if rule else pd.Series(True, index=hold.index)
        yh = hold["t_" + tg]
        okh = pres_h & yh.notna()
        mh, _ = apply_rule(hold, rule)
        res = test(yh[mh & okh], yh[okh], True)
        add("tree", ul, cut, tg, ctx, rule, res, n_fit=int(mfit.sum()),
            rate_fit=float(fitc.loc[mfit, "t_" + tg].mean()) if mfit.any() else np.nan,
            fit_end=str(fit["target_date"].iloc[-1]))


def simplify(conds):
    out = {}
    for c in conds:
        key = (c["f"], c["op"])
        if key not in out:
            out[key] = c
        elif c["op"] == "<=":
            out[key] = c if c["v"] < out[key]["v"] else out[key]
        else:
            out[key] = c if c["v"] > out[key]["v"] else out[key]
    return list(out.values())


if __name__ == "__main__":
    main()
