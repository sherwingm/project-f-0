"""Amendment 2: VIX change after entry as a holding feature (own folder, history only). Same procedure as g1_hold_pattern2."""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLIT = pd.Timestamp("2025-10-01")


def bh(p):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p)
    r = np.minimum.accumulate((p[o] * m / np.arange(1, m + 1))[::-1])[::-1]
    out = np.empty(m); out[o] = np.minimum(r, 1); return out


T = pd.read_csv(os.path.join(ROOT, "data", "g1_ivcrush_trades.csv"))
T["day"] = pd.to_datetime(T["day"])
T["dvix_d2"], T["dvix_d3"] = T["vix_d2"] - T["vix_in"], T["vix_d3"] - T["vix_in"]
old = pd.read_csv(os.path.join(ROOT, "results", "g1_hold_pattern2_all_rules.csv"))
rows = []
for tag, f, tcol in (("D2", "dvix_d2", "fu_d2"), ("D3", "dvix_d3", "fu_d3")):
    x = T.dropna(subset=[f, tcol]).copy()
    x["t"] = (x[tcol] >= 50).astype(int)
    dd, vv = x[x["day"] < SPLIT], x[x["day"] >= SPLIT]
    p33, p67 = np.percentile(dd[f], [33.3, 66.7])
    for name, c in (("high", lambda s, t=p67: s >= t), ("low", lambda s, t=p33: s <= t)):
        g, o = dd[c(dd[f])], dd[~c(dd[f])]
        p = stats.fisher_exact([[g.t.sum(), len(g) - g.t.sum()], [o.t.sum(), len(o) - o.t.sum()]])[1]
        gv, ov = vv[c(vv[f])], vv[~c(vv[f])]
        rows.append({"time": tag, "feature": f, "bucket": name, "thr": round((p67 if name == "high" else p33), 2),
                     "d_n": len(g), "d_rate": g.t.mean() * 100, "d_out": o.t.mean() * 100, "d_p": p,
                     "d_fu_mean": g[tcol].mean(), "d_fu_median": g[tcol].median(),
                     "v_n": len(gv), "v_rate": gv.t.mean() * 100 if len(gv) else np.nan, "v_out": ov.t.mean() * 100 if len(ov) else np.nan})
R = pd.DataFrame(rows)
allp = np.concatenate([old["d_p"].values, R["d_p"].values])
R["d_q"] = bh(allp)[len(old):]
R["candidate"] = (R["d_q"] <= 0.10) & (R["d_n"] >= 25) & (R["d_rate"] > R["d_out"])
R.to_csv(os.path.join(ROOT, "results", "g1_ivcrush_rules.csv"), index=False)
pd.set_option("display.width", 220)
print("family", len(allp)); print(R.round(3).to_string(index=False))
