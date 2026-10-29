"""S1 v12 fade · can a model learn which trades fail? Logistic regression, gradient boosting, one small tree (numbers only)

    python -m scanner.fade_ml

Same 339 v12 backtest trades and the same pre-09:16 features as scanner.fade_indicators (RSI, EMA 50/100/200,
Supertrend, 09:15 gaps for Nifty and the stock, plus side, entry price and days to expiry). Target: fail = v12 net < 0.
Two honest tests, the models never see the trades they are scored on:
  1. halves: train before 2025-11-03, test after (the split every fade study uses);
  2. walk-forward: for each quarter, train on every earlier trade, predict that quarter.
Each model must beat the simple rules already found (Nifty Supertrend down + Nifty gap down, and Supertrend + gap with
the trade); those rules were found on all 339 trades, so they get a head start. Writes data/results/S1_fade_ml.xlsx.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegressionCV
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

from .fade_indicators import RES, conditions, features

MIN_TRAIN = 80


def matrix(f: pd.DataFrame) -> pd.DataFrame:
    """Every column known before the 09:16 buy, as numbers (flags 0/1, missing RSI = 50, missing gap = 0)."""
    put = (f["side"] == "PE").astype(int)
    x = pd.DataFrame({"put": put})
    for pre in ("nifty", "stock"):
        x[f"{pre} RSI"] = f[f"{pre}_rsi"].astype(float).fillna(50)
        x[f"{pre} gap %"] = f[f"{pre}_gap_pct"].astype(float).fillna(0)
        for n in (50, 100, 200):
            x[f"{pre} above EMA {n}"] = (f[f"{pre}_above_ema{n}"] == True).astype(int)            # noqa: E712
        st = (f[f"{pre}_supertrend_up"] == True).astype(int)                                     # noqa: E712
        x[f"{pre} Supertrend up"] = st
        x[f"{pre} Supertrend with the trade"] = np.where(put == 1, 1 - st, st)
        x[f"{pre} gap with the trade"] = np.where(put == 1, x[f"{pre} gap %"] < 0, x[f"{pre} gap %"] > 0).astype(int)
    x["entry price (log)"] = np.log(f["entry 09:16+tick"].astype(float))
    x["days to expiry"] = (pd.to_datetime(f["expiry"]) - pd.to_datetime(f["day0"])).dt.days
    return x


def models() -> dict:
    return {
        "Logistic regression": lambda: make_pipeline(StandardScaler(), LogisticRegressionCV(
            Cs=10, cv=5, penalty="l1", solver="liblinear", scoring="neg_log_loss", max_iter=2000)),
        "Gradient boosting": lambda: GradientBoostingClassifier(
            n_estimators=150, learning_rate=0.03, max_depth=2, subsample=0.8, min_samples_leaf=10, random_state=0),
        "Small decision tree": lambda: DecisionTreeClassifier(max_depth=3, min_samples_leaf=15, random_state=0),
    }


def rules(f: pd.DataFrame) -> dict[str, pd.Series]:
    c = conditions(f)
    return {"Rule: Nifty Supertrend down AND Nifty gap down": (~c["nifty Supertrend up"]) & c["nifty gap down"],
            "Rule: Nifty Supertrend AND gap with the trade": c["nifty Supertrend with the trade"] & c["nifty gap with the trade"]}


def score(name: str, test: pd.DataFrame, p: np.ndarray, k: int) -> dict:
    """p = chance of failing. Flag the k riskiest trades (k = what the first rule flags on these trades) and skip them."""
    y = test["fail"].to_numpy().astype(int)
    net, rs = test["v12 net %"].to_numpy(), test["v12 net Rs"].to_numpy()
    order = np.argsort(-p, kind="stable")
    flag = np.zeros(len(p), bool)
    flag[order[:k]] = True
    if set(np.unique(p)) <= {0.0, 1.0}:                                  # a rule: flag exactly what it says
        flag = p == 1
    base = y.mean()
    return {"method": name, "trades": len(y), "AUC": roc_auc_score(y, p) if 0 < y.sum() < len(y) else None,
            "Brier": brier_score_loss(y, p) if not set(np.unique(p)) <= {0.0, 1.0} else None,
            "Brier of guessing the fail rate": brier_score_loss(y, np.full(len(y), base)),
            "flagged trades": int(flag.sum()), "fail % flagged": y[flag].mean() * 100 if flag.any() else None,
            "fail % kept": y[~flag].mean() * 100, "fail % all": base * 100,
            "mean net % all": net.mean(), "mean net % kept": net[~flag].mean(), "mean net % flagged": net[flag].mean() if flag.any() else None,
            "total Rs all": rs.sum(), "total Rs kept (skip flagged)": rs[~flag].sum()}


def evaluate(f: pd.DataFrame, x: pd.DataFrame, tr: np.ndarray, te: np.ndarray, label: str) -> tuple[list[dict], dict]:
    test = f[te]
    rl = rules(f)
    k = int(rl[next(iter(rl))][te].sum())
    rows, probs = [], {}
    for name, m in rl.items():
        rows.append(score(name, test, m[te].to_numpy().astype(float), k))
    for name, mk in models().items():
        m = mk().fit(x[tr], f.loc[tr, "fail"].astype(int))
        probs[name] = m.predict_proba(x[te])[:, 1]
        rows.append(score(name, test, probs[name], k))
    for r in rows:
        r["test"] = label
    return rows, probs


def walk_forward(f: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    q = pd.to_datetime(f["day0"]).dt.to_period("Q")
    oos = pd.DataFrame(index=f.index, columns=list(models()), dtype=float)
    for qq in sorted(q.unique()):
        tr, te = (q < qq).to_numpy(), (q == qq).to_numpy()
        if tr.sum() < MIN_TRAIN:
            continue
        for name, mk in models().items():
            m = mk().fit(x[tr], f.loc[tr, "fail"].astype(int))
            oos.loc[te, name] = m.predict_proba(x[te])[:, 1]
    done = oos.notna().all(axis=1).to_numpy()
    test = f[done]
    rl = rules(f)
    k = int(rl[next(iter(rl))][done].sum())
    rows = [score(n, test, m[done].to_numpy().astype(float), k) for n, m in rl.items()]
    rows += [score(n, test, oos.loc[done, n].to_numpy(), k) for n in models()]
    for r in rows:
        r["test"] = f"walk-forward {test['day0'].min()} to {test['day0'].max()}"
    return pd.DataFrame(rows), oos


def explain(f: pd.DataFrame, x: pd.DataFrame, tr: np.ndarray, te: np.ndarray) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    y = f["fail"].astype(int)
    lr = models()["Logistic regression"]().fit(x[tr], y[tr])
    coef = lr[-1].coef_[0]
    w = pd.DataFrame({"feature": x.columns, "weight (train half, scaled)": coef,
                      "reads as": ["fail MORE when higher / true" if c > 0 else "fail LESS when higher / true" if c < 0 else "switched off" for c in coef]})
    w = w.reindex(w["weight (train half, scaled)"].abs().sort_values(ascending=False).index)
    tree = models()["Small decision tree"]().fit(x[tr], y[tr])
    txt = export_text(tree, feature_names=list(x.columns), show_weights=True, decimals=2).splitlines()
    gb = models()["Gradient boosting"]().fit(x[tr], y[tr])
    pi = permutation_importance(gb, x[te], y[te], scoring="roc_auc", n_repeats=30, random_state=0)
    imp = pd.DataFrame({"feature": x.columns, "AUC lost when shuffled (test half)": pi.importances_mean,
                        "spread": pi.importances_std}).sort_values("AUC lost when shuffled (test half)", ascending=False)
    return w, txt, imp


def main() -> None:
    t = pd.read_feather(RES / "S1_fade_market_direction_trades.feather").sort_values("day0").reset_index(drop=True)
    f = features(t)
    f["fail"] = f["fail"].astype(bool)
    x = matrix(f)
    tr, te = (f["half"] == "train").to_numpy(), (f["half"] == "test").to_numpy()
    rows, probs = evaluate(f, x, tr, te, f"test half {f.loc[te, 'day0'].min()} to {f.loc[te, 'day0'].max()}")
    halves = pd.DataFrame(rows)
    wf, oos = walk_forward(f, x)
    w, txt, imp = explain(f, x, tr, te)
    per = f[["day0", "half", "symbol", "side", "v12 net %", "v12 net Rs", "fail"]].copy()
    for n, m in rules(f).items():
        per[n.replace("Rule: ", "rule · ")] = m.map({True: "flag", False: ""})
    for n, p in probs.items():
        per.loc[te, f"{n}: fail chance % (halves)"] = p * 100
    for n in models():
        per[f"{n}: fail chance % (walk-forward)"] = oos[n] * 100
    per["fail"] = per["fail"].map({True: "fail", False: ""})
    from .fade_ml_xlsx import write
    write(RES / "S1_fade_ml.xlsx", halves, wf, w, txt, imp, per, x.columns)
    cols = ["method", "trades", "AUC", "flagged trades", "fail % flagged", "fail % kept", "mean net % all", "mean net % kept",
            "total Rs all", "total Rs kept (skip flagged)"]
    print(halves[cols].round(3).to_string())
    print(wf[cols].round(3).to_string())
    print(w.round(3).to_string())
    print("\n".join(txt))
    print(imp.round(3).head(10).to_string())


if __name__ == "__main__":
    main()
