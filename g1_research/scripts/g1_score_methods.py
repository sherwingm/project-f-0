"""Score methods search (g1_research/SCORE_METHODS_PREREG.md). History only; record-only score. Run once, nothing re-tuned."""
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
SPLIT = pd.Timestamp("2025-10-01")
A = {"depth": "Breakout depth at signal %", "time": "Minutes after 09:30", "width": "OR width %", "gap": "Day-1 gap at open %",
     "vix": "VIX at signal", "prev5": "Prev 5-day return %", "ema20": "Prev close vs EMA20 %"}
B = {**A, "dte": "Days to expiry", "open_entry": "Day-1 open → entry %", "prev1": "Prev day return %",
     "vixchg": "VIX change since open", "prem": "Premium % of spot"}
N_PERM = 5000


def load():
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    h = pd.read_csv(os.path.join(ROOT, "data", "g1_hold_days_trades.csv"))
    d["day"], h["day"] = pd.to_datetime(d["Day"]), pd.to_datetime(h["day"])
    T = d.merge(h[["day", "peak_k1", "k1_net", "k1_reason", "g1f"]], on="day").sort_values("day").reset_index(drop=True)
    for k, c in B.items():
        T[k] = pd.to_numeric(T[c], errors="coerce")
    return T


def signs(tr, keys):
    return {k: np.sign(stats.spearmanr(tr[k], tr["peak_k1"])[0]) for k in keys}


def m1(tr):
    th = {k: tr[k].median() for k in A}

    def f(df):
        s = (df["depth"] >= th["depth"]).astype(int) + (df["time"] <= th["time"]) + (df["width"] <= th["width"]) \
            + (df["gap"] <= th["gap"]) + (df["vix"] < 17) + (df["prev5"] <= th["prev5"]) + (df["ema20"] <= th["ema20"])
        return s.values.astype(float)
    return f


def checklist(keys):
    def fit(tr):
        sg, cut = signs(tr, keys), {k: tr[k].median() for k in keys}

        def f(df):
            return sum(((df[k] >= cut[k]) if sg[k] >= 0 else (df[k] <= cut[k])).astype(int).values for k in keys).astype(float)
        return f
    return fit


def terciles(keys):
    def fit(tr):
        sg = signs(tr, keys)
        q = {k: np.percentile(tr[k], [33.3, 66.7]) for k in keys}

        def f(df):
            s = np.zeros(len(df))
            for k in keys:
                x = df[k].values
                up = (x >= q[k][1]).astype(int) - (x <= q[k][0]).astype(int)
                s += up if sg[k] >= 0 else -up
            return s
        return f
    return fit


def rank_avg(keys, weighted=False):
    def fit(tr):
        sg = signs(tr, keys)
        ref = {k: np.sort(tr[k].values) for k in keys}
        w = {k: (abs(stats.spearmanr(tr[k], tr["peak_k1"])[0]) if weighted else 1.0) for k in keys}

        def f(df):
            s = np.zeros(len(df))
            for k in keys:
                r = np.searchsorted(ref[k], df[k].values, side="right") / len(ref[k])
                s += w[k] * (r if sg[k] >= 0 else 1 - r)
            return s / sum(w.values())
        return f
    return fit


def model(kind, keys):
    def fit(tr):
        y = (tr["peak_k1"] >= 100).astype(int).values
        if kind == "lr":
            mdl = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=1000))
        else:
            mdl = RandomForestClassifier(n_estimators=200, max_depth=3, min_samples_leaf=10, random_state=0, n_jobs=-1)
        mdl.fit(tr[keys].values, y)
        return lambda df: mdl.predict_proba(df[keys].values)[:, 1]
    return fit


KA, KB = list(A), list(B)
METHODS = {"M1 old checklist": m1, "M2 checklist, learned direction (A)": checklist(KA),
           "M3 same on set B": checklist(KB), "M4 checklist without EMA20": checklist([k for k in KA if k != "ema20"]),
           "M5 terciles +1/0/-1 (A)": terciles(KA), "M6 rank average (A)": rank_avg(KA), "M7 rank average (B)": rank_avg(KB),
           "M8 rank, |rho| weights (A)": rank_avg(KA, True), "M9 logistic (B)": model("lr", KB), "M10 random forest (B)": model("rf", KB)}


def thirds(df, s):
    q = np.percentile(s, [33.3, 66.7])
    return df[s <= q[0]], df[s >= q[1]]


def main():
    T = load()
    disc, val = T[T["day"] < SPLIT].copy(), T[T["day"] >= SPLIT].copy()
    yv = val["peak_k1"].values
    rows, vscores = [], {}
    for name, fit in METHODS.items():
        f = fit(disc)
        sd, sv = f(disc), f(val)
        vscores[name] = sv
        rd = stats.spearmanr(sd, disc["peak_k1"])[0]
        rho, p2 = stats.spearmanr(sv, yv)
        p1 = p2 / 2 if rho > 0 else 1 - p2 / 2
        lo, hi = thirds(val, sv)
        rows.append({"method": name, "disc_rho_in_sample": rd, "val_rho": rho, "val_p1": p1,
                     "top3_ge100": (hi["peak_k1"] >= 100).mean() * 100, "bot3_ge100": (lo["peak_k1"] >= 100).mean() * 100,
                     "top3_med": hi["peak_k1"].median(), "bot3_med": lo["peak_k1"].median(),
                     "top3_mean": hi["peak_k1"].mean(), "bot3_mean": lo["peak_k1"].mean(),
                     "top3_booked": hi["k1_net"].mean(), "bot3_booked": lo["k1_net"].mean()})
    R = pd.DataFrame(rows)
    wf = {}
    for name, fit in METHODS.items():
        sc = [float(fit(T.iloc[:i])(T.iloc[[i]])[0]) for i in range(60, len(T))]
        wf[name] = stats.spearmanr(sc, T["peak_k1"].iloc[60:])[0]
    R["walk_fwd_rho"] = R["method"].map(wf)
    pd.set_option("display.width", 250)
    print("discovery n =", len(disc), "| validation n =", len(val), "| walk-forward scores n =", len(T) - 60)
    print(R[["method", "disc_rho_in_sample", "val_rho", "val_p1", "walk_fwd_rho"]].round(3).to_string(index=False))
    print("\nTop third vs bottom third of the score, validation (max up through next close):")
    print(R[["method", "top3_ge100", "bot3_ge100", "top3_med", "bot3_med", "top3_mean", "bot3_mean", "top3_booked", "bot3_booked"]].round(1).to_string(index=False))
    rng = np.random.default_rng(0)
    rk = {}
    for n, s in vscores.items():
        r = stats.rankdata(s)
        rk[n] = (r - r.mean()) / np.linalg.norm(r - r.mean())
    ry = stats.rankdata(yv)
    best_obs = R["val_rho"].max()
    cnt = 0
    for _ in range(N_PERM):
        p = rng.permutation(ry)
        p = (p - p.mean()) / np.linalg.norm(p - p.mean())
        cnt += max(float(r @ p) for r in rk.values()) >= best_obs
    pperm = (cnt + 1) / (N_PERM + 1)
    print(f"\nSelection check: best validation rho of the 10 = {best_obs:.3f}; chance of a best this big from pure noise = {pperm:.3f}")
    R["works"] = (R["val_p1"] < 0.005) & (R["top3_ge100"] > R["bot3_ge100"]) & (R["val_rho"] > 0)
    print("\nPasses the pre-registered bar (p1 < 0.005 and top > bottom):", R.loc[R["works"], "method"].tolist() or "none")
    R.to_csv(os.path.join(ROOT, "results", "g1_score_methods.csv"), index=False)
    for name in R.loc[R["val_p1"] < 0.05, "method"]:
        s = pd.Series(vscores[name], index=val.index)
        print(f"\n-- hiding checks: {name}")
        for yr, g in val.groupby(val["day"].dt.year):
            print(f"   {yr}: n={len(g)} rho={stats.spearmanr(s[g.index], g['peak_k1'])[0]:.3f}")
        gf = val[val["g1f"] == 1]
        print(f"   G1-F only: n={len(gf)} rho={stats.spearmanr(s[gf.index], gf['peak_k1'])[0]:.3f}")
        keep = val.drop(val["peak_k1"].nlargest(10).index)
        print(f"   without the 10 largest max-ups: rho={stats.spearmanr(s[keep.index], keep['peak_k1'])[0]:.3f}")


if __name__ == "__main__":
    main()
