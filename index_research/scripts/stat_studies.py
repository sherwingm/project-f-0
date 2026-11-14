"""R10 (pairs, stock daily) and R11 (simple daily ML, walk-forward) of index_research/PROGRAM.md.
R10: log-price spread y - b x with a rolling 60-session OLS hedge ratio (data up to the previous close), z-score over 20 sessions;
     enter at the next open when |z| > 2 (short the spread when z > 2), exit at the next open after z crosses 0, stop when |z| > 3.5; ADF p < 0.05
     on the previous 250 sessions' spread required (cell 'adf') or not ('raw'). Costs 0.1 % a side a leg (futures-like), 2x = 0.2 %.
     Notional Rs 5 lakh a leg. Periods: D 2012-2018, V 2019-2022, L 2023 ->.
R11: NIFTY next-day direction (open -> close of the next session, futures proxy on the index, 1 point slippage a side + charges) from 12 features
     known at the close; logistic regression and random forest refit every January on all earlier years (eod2 NIFTY starts 2012-02; first test year 2018;
     NIFTY50 daily from data/eod2, VIX daily from 2008). Cells: logit_all, rf_all, logit_conf (p > 0.55 or < 0.45), rf_conf.
     Periods: D 2018-2021, V 2022-01 to 2024-09, L 2024-10 ->.
Usage: python stat_studies.py R10 | R11
"""
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

from lib import CH, REPO, boot_ci, bh, mc_drawdown, save, summary, validation_pass

sys.stdout.reconfigure(encoding="utf-8")


def eod(sym):
    d = pd.read_csv(os.path.join(REPO, "data", "eod2", f"{sym}.csv"), parse_dates=["Date"])
    d["d"] = d["Date"].dt.date
    return d.set_index("d")[["Open", "Close"]]


def adf_p(x):
    """ADF with a constant and one lagged difference, by OLS (statsmodels is not installed). Returns 0.01 when the t of the
    lagged level is below the 5 % MacKinnon critical value -2.86 (stationary at 5 %), else 0.5: used only as p < 0.05 or not."""
    x = np.asarray(x, float)
    dx = np.diff(x)
    y, lag, lvl = dx[1:], dx[:-1], x[1:-1]
    A = np.column_stack([np.ones(len(y)), lvl, lag])
    coef, res, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    s2 = resid @ resid / (len(y) - A.shape[1])
    se = np.sqrt(np.diag(s2 * np.linalg.inv(A.T @ A)))
    return 0.01 if coef[1] / se[1] < -2.86 else 0.5


def per10(d):
    return "D" if d < date(2019, 1, 1) else ("V" if d < date(2023, 1, 1) else "L")


def r10():
    pairs = [("hdfcbank", "icicibank"), ("hdfcbank", "kotakbank"), ("icicibank", "axisbank"), ("sbin", "icicibank")]
    out = []
    for ys, xs in pairs:
        a, b = eod(ys), eod(xs)
        j = a.join(b, lsuffix="_y", rsuffix="_x", how="inner")
        j = j[j.index >= date(2011, 1, 1)]
        ly, lx = np.log(j["Close_y"]), np.log(j["Close_x"])
        beta = (ly.rolling(60).cov(lx) / lx.rolling(60).var()).shift(1)
        spread = ly - beta * lx
        z = (spread - spread.rolling(20).mean()) / spread.rolling(20).std()
        idx = list(j.index)
        adf_cache = {}
        for mode in ("raw", "adf"):
            pos, i = None, 260
            while i < len(idx) - 1:
                d, nd = idx[i], idx[i + 1]
                zz = z.iloc[i]
                if pos is None:
                    if abs(zz) > 2 and d >= date(2012, 1, 1):
                        if mode == "adf":
                            yr = d.year * 100 + d.month
                            if yr not in adf_cache:
                                s = spread.iloc[i - 250:i].dropna()
                                adf_cache[yr] = adf_p(s.to_numpy()) if len(s) > 100 else np.nan
                            if not adf_cache[yr] < 0.05:
                                i += 1
                                continue
                        sgn = -1 if zz > 2 else 1                      # +1 = long y short x
                        pos = {"d": nd, "sgn": sgn, "py": j.loc[nd, "Open_y"], "px": j.loc[nd, "Open_x"], "b": beta.iloc[i]}
                else:
                    if (pos["sgn"] < 0 and zz <= 0) or (pos["sgn"] > 0 and zz >= 0) or abs(zz) > 3.5:
                        ry = j.loc[nd, "Open_y"] / pos["py"] - 1
                        rx = j.loc[nd, "Open_x"] / pos["px"] - 1
                        bb = float(np.clip(pos["b"], 0.2, 3.0))
                        gross = pos["sgn"] * (ry - bb * rx) / (1 + bb) * 100          # % of the total notional (both legs)
                        for cm, sfx in ((1, ""), (2, "_2x")):
                            net = gross - 0.1 * cm * 2                              # 0.1 % a side a leg, both legs entry and exit, averaged over notional
                            if sfx == "":
                                rec = {"cell": f"{ys}-{xs}|{mode}", "day": pos["d"], "exit_day": nd, "net_pct": net,
                                       "net_rs": net / 100 * 1_000_000, "stopped": abs(zz) > 3.5}
                            else:
                                rec["net_pct_2x"] = net
                        out.append(rec)
                        pos = None
                i += 1
    return out, per10


def per11(d):
    return "D" if d < date(2022, 1, 1) else ("V" if d < date(2024, 10, 1) else "L")


def r11():
    n = eod("nifty 50")
    from lib import index_close_vix
    vix = index_close_vix()
    df = n.join(vix.rename("vix"), how="inner").dropna()
    c, o = df["Close"], df["Open"]
    f = pd.DataFrame(index=df.index)
    f["r1"], f["r5"], f["r20"] = c.pct_change(), c.pct_change(5), c.pct_change(20)
    f["gap"] = o / c.shift() - 1
    f["rng"] = (df["Close"] - df["Open"]) / df["Open"]
    f["vix"], f["dvix"] = df["vix"], df["vix"].pct_change()
    f["vov"] = df["vix"].rolling(5).std()
    f["sma20"], f["sma50"] = c / c.rolling(20).mean() - 1, c / c.rolling(50).mean() - 1
    f["sma200"] = c / c.rolling(200).mean() - 1
    f["dow"] = [d.weekday() for d in df.index]
    y_ret = (c.shift(-1) / o.shift(-1) - 1)              # next session open -> close
    data = f.assign(y=(y_ret > 0).astype(int), ret=y_ret, nopen=o.shift(-1)).dropna()
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    X = data.drop(columns=["y", "ret", "nopen"])
    out = []
    for yr in range(2018, 2027):
        tr = data[[d.year < yr for d in data.index]]
        te = data[[d.year == yr for d in data.index]]
        if te.empty or len(tr) < 500:
            continue
        models = {"logit": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
                  "rf": RandomForestClassifier(n_estimators=300, min_samples_leaf=50, random_state=20261114, n_jobs=-1)}
        for nm, m in models.items():
            m.fit(X.loc[tr.index], tr["y"])
            p = m.predict_proba(X.loc[te.index])[:, 1]
            for d, pp, r, op in zip(te.index, p, te["ret"], te["nopen"]):
                sgn = 1 if pp > 0.5 else -1
                lot = 65
                for cm, sfx in ((1, ""), (2, "_2x")):
                    gross = sgn * r * op * lot - 2 * 1.0 * cm * lot
                    fees = (CH.leg("FUT", "BUY", lot, op, on=d)["total"] + CH.leg("FUT", "SELL", lot, op, on=d)["total"]) * cm
                    net = gross - fees
                    if sfx == "":
                        rec = {"day": d, "net_rs": net, "net_pct": net / (op * lot) * 100, "prob": pp}
                    else:
                        rec["net_rs_2x"], rec["net_pct_2x"] = net, net / (op * lot) * 100
                out.append({**rec, "cell": f"{nm}_all"})
                if pp > 0.55 or pp < 0.45:
                    out.append({**rec, "cell": f"{nm}_conf"})
    return out, per11


def evaluate(study, trades, per):
    T = pd.DataFrame(trades)
    T["period"] = T["day"].map(per)
    save(T, f"{study}_trades.csv")
    C = bh(pd.DataFrame([{"key": k, **summary(x)} for k, x in T[T["period"] == "D"].groupby("cell")]))
    save(C, f"{study}_discovery.csv")
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 200)
    cols = ["key", "n", "win_pct", "mean_pct", "median_pct", "total_rs", "t", "pf", "mean_2x", "h1_mean", "h2_mean", "max_dd_rs", "discovery_pass"]
    print(f"=== {study} DISCOVERY ===")
    print(C[cols].round(3).to_string(index=False))
    vrows = []
    for key in C.loc[C["discovery_pass"], "key"]:
        x = T[(T["cell"] == key) & (T["period"] == "V")]
        s = {"key": key, **summary(x)}
        s["validation_pass"] = validation_pass(s)
        if s["validation_pass"]:
            lo, hi = boot_ci(x)
            s.update({"boot_lo": lo, "boot_hi": hi, **mc_drawdown(x["net_rs"])})
            s.update({f"L_{k}": v for k, v in summary(T[(T["cell"] == key) & (T["period"] == "L")]).items()})
        vrows.append(s)
    if vrows:
        V = pd.DataFrame(vrows)
        save(V, f"{study}_validation.csv")
        print(f"=== {study} VALIDATION [+ L for passers] ===")
        print(V.round(3).to_string(index=False))
    print("discovery passes:", int(C["discovery_pass"].sum()))


if __name__ == "__main__":
    for st in sys.argv[1:]:
        tr, per = {"R10": r10, "R11": r11}[st]()
        evaluate(st, tr, per)
