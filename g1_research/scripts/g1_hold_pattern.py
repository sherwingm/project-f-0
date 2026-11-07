"""Holding-pattern search (g1_research/HOLD_PATTERN_PREREG.md). Own folder; history only; in-sample caveats apply."""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
SPLIT = pd.Timestamp("2025-10-01")
TARGET = 100.0

D1 = {"dte": "Days to expiry", "mins": "Minutes after 09:30", "width": "OR width %", "depth": "Breakout depth at signal %",
      "gap": "Day-1 gap at open %", "open_entry": "Day-1 open → entry %", "prev1": "Prev day return %",
      "prev5": "Prev 5-day return %", "ema20": "Prev close vs EMA20 %", "vix": "VIX at signal",
      "vixchg": "VIX change since open", "prem": "Premium % of spot"}
D2 = {"d1_1515": "Day-1 entry → 15:15 %", "d1_orlow": "Day-1 15:15 vs OR low %", "gap2": "Next-day gap %", "net_open": None}
D3 = {"net_k1": None, "d2_move": "Next-day open → 15:15 %"}


def bh(p, q=0.10):
    p = np.asarray(p, float)
    m = len(p)
    order = np.argsort(p)
    r = p[order] * m / np.arange(1, m + 1)
    r = np.minimum.accumulate(r[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.minimum(r, 1)
    return out


def main():
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    h = pd.read_csv(os.path.join(ROOT, "data", "g1_hold_days_trades.csv"))
    d["day"] = pd.to_datetime(d["Day"])
    h["day"] = pd.to_datetime(h["day"])
    T = d.merge(h, on="day", suffixes=("", "_h"))
    T["peak_h"] = [row[f"peak_k{min(int(row['dte']), 3)}"] for _, row in T.iterrows()]
    T["reach"] = (T["peak_h"] >= TARGET).astype(int)
    T["net_open"], T["net_k1"] = T["open_net"], T["k1_net"]
    T["alive_d2"] = T["open_reason"] != "stop"
    T["alive_d3"] = (T["k1_reason"] != "stop")
    T["dte"] = T["dte"]
    for k, c in {**D1, **D2, **D3}.items():
        T[k] = pd.to_numeric(T[c] if c in T.columns else T[k], errors="coerce") if c else T[k]
    T["mins"] = pd.to_numeric(T["Minutes after 09:30"], errors="coerce")
    T = T[T["peak_h"].notna()].copy()
    disc, val = T[T["day"] < SPLIT], T[T["day"] >= SPLIT]
    sets = [("D1 entry", list(D1), lambda x: x), ("D2 next 09:16", list(D2), lambda x: x[x["alive_d2"]]),
            ("D3 next close", list(D3), lambda x: x[x["alive_d3"]])]
    rows = []
    for dt, feats, alive in sets:
        dd, vv = alive(disc), alive(val)
        for f in feats:
            x = dd[f].dropna()
            if len(x) < 40 or x.nunique() < 4:
                continue
            p33, p67 = np.percentile(x, [33.3, 66.7])
            for name, cond in (("high", lambda s, t=p67: s >= t), ("low", lambda s, t=p33: s <= t)):
                g = dd[cond(dd[f]) & dd[f].notna()]
                o = dd.drop(g.index)
                if len(g) < 5 or len(o) < 5:
                    continue
                tab = [[g["reach"].sum(), len(g) - g["reach"].sum()], [o["reach"].sum(), len(o) - o["reach"].sum()]]
                p = stats.fisher_exact(tab)[1]
                gv = vv[cond(vv[f]) & vv[f].notna()]
                ov = vv.drop(gv.index)
                rows.append({"time": dt, "feature": f, "bucket": name, "threshold": p67 if name == "high" else p33,
                             "d_n": len(g), "d_reach": g["reach"].mean() * 100, "d_base_out": o["reach"].mean() * 100,
                             "d_peak_mean": g["peak_h"].mean(), "d_peak_median": g["peak_h"].median(), "d_p": p,
                             "v_n": len(gv), "v_reach": gv["reach"].mean() * 100 if len(gv) else np.nan,
                             "v_base_out": ov["reach"].mean() * 100 if len(ov) else np.nan,
                             "v_peak_mean": gv["peak_h"].mean() if len(gv) else np.nan,
                             "v_peak_median": gv["peak_h"].median() if len(gv) else np.nan,
                             "v_tab": [[gv["reach"].sum(), len(gv) - gv["reach"].sum()],
                                       [ov["reach"].sum(), len(ov) - ov["reach"].sum()]]})
    R = pd.DataFrame(rows)
    R["d_q"] = bh(R["d_p"].values)
    R["d_effect"] = R["d_reach"] - R["d_base_out"]
    R["candidate"] = (R["d_q"] <= 0.10) & (R["d_n"] >= 25) & (R["d_effect"] > 0)
    # (the validation columns above are stored but only READ for rules frozen as candidates)
    cand = R[R["candidate"]].copy()
    cand.drop(columns=["v_n", "v_reach", "v_base_out", "v_peak_mean", "v_peak_median", "v_tab"]).to_csv(
        os.path.join(ROOT, "results", "g1_hold_pattern_candidates_frozen.csv"), index=False)
    print("family", len(R), "candidates", len(cand))
    cand["v_effect"] = cand["v_reach"] - cand["v_base_out"]
    cand["v_p1"] = [stats.fisher_exact(t, alternative="greater")[1] for t in cand["v_tab"]]
    cand["passed"] = (cand["v_n"] >= 20) & (cand["v_effect"] > 0) & (cand["v_p1"] < 0.05) & (cand["v_effect"] >= 0.5 * cand["d_effect"])
    keep = ["time", "feature", "bucket", "threshold", "d_n", "d_reach", "d_base_out", "d_p", "d_q", "d_peak_mean", "d_peak_median",
            "v_n", "v_reach", "v_base_out", "v_effect", "v_p1", "v_peak_mean", "v_peak_median", "passed"]
    cand[keep].to_csv(os.path.join(ROOT, "results", "g1_hold_pattern_validation.csv"), index=False)
    R.drop(columns=["v_tab"]).to_csv(os.path.join(ROOT, "results", "g1_hold_pattern_all_rules.csv"), index=False)
    pd.set_option("display.width", 250)
    print("base reach: discovery", round(disc["reach"].mean() * 100), "validation", round(val["reach"].mean() * 100),
          "| peak mean/median", round(disc["peak_h"].mean()), round(disc["peak_h"].median()))
    print(R.sort_values("d_p").head(12)[["time", "feature", "bucket", "d_n", "d_reach", "d_base_out", "d_p", "d_q"]].round(3).to_string(index=False))
    print(cand[keep].round(2).to_string(index=False) if len(cand) else "no candidate")


if __name__ == "__main__":
    main()
