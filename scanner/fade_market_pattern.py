"""S1 v12 fade · market only, no indicators: what does the market do on the days the fade fails? (numbers only)

    python -m scanner.fade_market_pattern

Same 339 v12 backtest trades. Only the market's own moves: Nifty's previous day, the 09:15 gap, the move after the open
(open -> close), the day's high / low from the open, and the stock's own 09:15 gap. No RSI / EMA / Supertrend.
Two kinds of input, kept apart:
  A = known at 09:16 (previous day, the gaps): could be used live;
  B = the whole day (adds the move after the open): explains WHY a trade failed, but is only known after the close.
Part 1: pattern tables (fail % per market path, both halves, Fisher p). Part 2: the three models from scanner.fade_ml on
A and on B, scored only on trades they never saw; the small tree's boxes as readable patterns, train vs test half.
Writes data/results/S1_fade_market_pattern.xlsx.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .fade_indicators import EOD, RES, nifty, stat
from .fade_ml import evaluate, explain, models, walk_forward


def pct(a, b) -> float:
    return (a / b - 1) * 100


def market(t: pd.DataFrame) -> pd.DataFrame:
    n = nifty()
    n.index = pd.to_datetime(n.index)
    rows = []
    for r in t.itertuples():
        d0 = pd.Timestamp(r.day0)
        x = {}
        i = n.index.get_indexer([d0])[0]
        if i >= 2:
            o, h, lo, c, c1, c2 = (n["Open"].iloc[i], n["High"].iloc[i], n["Low"].iloc[i], n["Close"].iloc[i],
                                   n["Close"].iloc[i - 1], n["Close"].iloc[i - 2])
            x |= {"nifty prev day %": pct(c1, c2), "nifty gap %": pct(o, c1), "nifty open to close %": pct(c, o),
                  "nifty close move %": pct(c, c1), "nifty high from open %": pct(h, o), "nifty low from open %": pct(lo, o)}
        s = pd.read_csv(EOD / f"{r.symbol.lower()}.csv", parse_dates=["Date"]).drop_duplicates("Date").set_index("Date")
        j = s.index.get_indexer([d0])[0]
        if j >= 2:
            x |= {"stock gap %": pct(s["Open"].iloc[j], s["Close"].iloc[j - 1]),
                  "stock prev day %": pct(s["Close"].iloc[j - 1], s["Close"].iloc[j - 2])}
        rows.append(x)
    f = pd.concat([t.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    return f.dropna(subset=["nifty gap %", "nifty open to close %", "stock gap %"]).reset_index(drop=True)


def inputs(f: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A = known at 09:16, B = A + the rest of the day. 'toward the trade' = the move signed so + helps the option."""
    sgn = np.where(f["side"] == "PE", -1, 1)
    a = pd.DataFrame({"put": (f["side"] == "PE").astype(int)})
    for c in ("nifty prev day %", "nifty gap %", "stock gap %", "stock prev day %"):
        a[c] = f[c]
        a[c.replace(" %", " toward the trade %")] = f[c] * sgn
    a["stock gap same way as nifty"] = (np.sign(f["stock gap %"]) == np.sign(f["nifty gap %"])).astype(int)
    b = a.copy()
    for c in ("nifty open to close %", "nifty close move %", "nifty high from open %", "nifty low from open %"):
        b[c] = f[c]
    b["nifty open to close toward the trade %"] = f["nifty open to close %"] * sgn
    b["nifty close move toward the trade %"] = f["nifty close move %"] * sgn
    return a, b


def patterns(f: pd.DataFrame) -> pd.DataFrame:
    gd, ad = f["nifty gap %"] < 0, f["nifty open to close %"] < 0
    put = f["side"] == "PE"
    sgn = np.where(put, -1, 1)
    gw, dw = f["nifty gap %"] * sgn > 0, f["nifty open to close %"] * sgn > 0
    pd_dn = f["nifty prev day %"] < 0
    g = {}
    g["Nifty day path"] = {"gap up, then rose": ~gd & ~ad, "gap up, then fell": ~gd & ad,
                           "gap down, then rose (recovered)": gd & ~ad, "gap down, then kept falling": gd & ad}
    g["Nifty day path × side"] = {f"{k} · {s}": m & (put if s == "puts" else ~put) for k, m in g["Nifty day path"].items() for s in ("puts", "calls")}
    g["With / against the trade"] = {"gap with, day with": gw & dw, "gap with, day against": gw & ~dw,
                                     "gap against, day with": ~gw & dw, "gap against, day against": ~gw & ~dw}
    gp = f["nifty gap %"]
    g["Nifty gap size"] = {"gap below -0.5 %": gp < -0.5, "gap -0.5 to 0 %": (gp >= -0.5) & (gp < 0),
                           "gap 0 to +0.5 %": (gp >= 0) & (gp < 0.5), "gap above +0.5 %": gp >= 0.5}
    oc = f["nifty open to close %"]
    g["Nifty move after the open"] = {"fell more than 0.5 %": oc < -0.5, "fell 0 to 0.5 %": (oc >= -0.5) & (oc < 0),
                                      "rose 0 to 0.5 %": (oc >= 0) & (oc < 0.5), "rose more than 0.5 %": oc >= 0.5}
    rng = f["nifty high from open %"] - f["nifty low from open %"]
    g["Nifty day range (high - low from the open)"] = {"quiet: under 0.8 %": rng < 0.8, "normal: 0.8 to 1.3 %": (rng >= 0.8) & (rng < 1.3),
                                                       "wild: 1.3 % or more": rng >= 1.3}
    g["Previous day × gap"] = {"prev day down, gap down": pd_dn & gd, "prev day down, gap up": pd_dn & ~gd,
                               "prev day up, gap down": ~pd_dn & gd, "prev day up, gap up": ~pd_dn & ~gd}
    sg = np.sign(f["stock gap %"]) == np.sign(f["nifty gap %"])
    g["Stock gap vs Nifty gap"] = {"stock gapped the same way as Nifty": sg, "stock gapped against Nifty": ~sg}
    rows = []
    for grp, ms in g.items():
        for k, m in ms.items():
            if m.sum():
                rows.append({"group": grp, **stat(f, m, k)})
    return pd.DataFrame(rows)


def leaves(tree, x: pd.DataFrame, f: pd.DataFrame, tr: np.ndarray, te: np.ndarray) -> pd.DataFrame:
    """Each box of the tree as a plain pattern, with its fail % on the half it learned from and on the half it never saw."""
    t, names = tree.tree_, list(x.columns)
    path = {0: []}
    for node in range(t.node_count):
        if t.children_left[node] != -1:
            nm, th = names[t.feature[node]], t.threshold[node]
            flag = set(x.iloc[:, t.feature[node]].unique()) <= {0, 1}
            lo, hi = (f"NOT {nm}", nm) if flag else (f"{nm} ≤ {th:.2f}", f"{nm} > {th:.2f}")
            path[t.children_left[node]] = path[node] + [lo]
            path[t.children_right[node]] = path[node] + [hi]
    leaf = tree.apply(x)
    y, net = f["fail"].to_numpy(), f["v12 net %"].to_numpy()
    rows = []
    for lf in sorted(set(leaf)):
        m = leaf == lf
        rows.append({"pattern": "  AND  ".join(path[lf]), "train trades": int((m & tr).sum()),
                     "train fail %": y[m & tr].mean() * 100 if (m & tr).any() else None,
                     "test trades": int((m & te).sum()), "test fail %": y[m & te].mean() * 100 if (m & te).any() else None,
                     "test mean net %": net[m & te].mean() if (m & te).any() else None})
    out = pd.DataFrame(rows)
    out["held in the test half"] = np.where((out["train fail %"] > 50) == (out["test fail %"] > 50), "yes", "no")
    return out.sort_values("train fail %", ascending=False)


def run(f: pd.DataFrame, x: pd.DataFrame, rl: dict, tag: str) -> dict:
    tr, te = (f["half"] == "train").to_numpy(), (f["half"] == "test").to_numpy()
    rows, _ = evaluate(f, x, tr, te, f"{tag} · test half", rl)
    wf, _ = walk_forward(f, x, rl)
    wf["test"] = f"{tag} · " + wf["test"]
    w, txt, imp = explain(f, x, tr, te)
    tree = models()["Small decision tree"]().fit(x[tr], f.loc[tr, "fail"].astype(int))
    return {"halves": pd.DataFrame(rows), "wf": wf, "weights": w, "tree": txt, "imp": imp, "leaves": leaves(tree, x, f, tr, te)}


def main() -> None:
    t = pd.read_feather(RES / "S1_fade_market_direction_trades.feather").sort_values("day0").reset_index(drop=True)
    f = market(t)
    f["fail"] = f["fail"].astype(bool)
    a, b = inputs(f)
    pat = patterns(f)
    gd, ad = f["nifty gap %"] < 0, f["nifty open to close %"] < 0
    ra = {"Rule: Nifty gap down": gd}
    rb = {"Rule: Nifty gap down, then kept falling": gd & ad, "Rule: Nifty gap down": gd}
    A, B = run(f, a, ra, "A (known at 09:16)"), run(f, b, rb, "B (whole day)")
    from .fade_market_pattern_xlsx import write
    write(RES / "S1_fade_market_pattern.xlsx", f, pat, A, B)
    cols = ["group", "condition", "trades", "fail %", "fail % rest", "mean net %", "train fail %", "test fail %", "p (fail vs rest)", "same way both halves"]
    print(pat[cols].round(3).to_string())
    for k, R in (("A", A), ("B", B)):
        print(k)
        c2 = ["test", "method", "trades", "AUC", "flagged trades", "fail % flagged", "fail % kept", "mean net % all", "mean net % kept"]
        print(pd.concat([R["halves"], R["wf"]])[c2].round(3).to_string())
        print(R["leaves"].round(1).to_string())
        print(R["weights"].round(3).to_string())


if __name__ == "__main__":
    main()
