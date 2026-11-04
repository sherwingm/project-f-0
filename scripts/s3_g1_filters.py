"""G1 with the datasheet's bucket filters (the user, 2026-11-04: "check whether removing the negative mean and
increasing the doubt trade of positive mean help"): skip the negative buckets, trade 2 lots in the positive ones.
In-sample; also a year-1 → year-2 check where the buckets are re-picked on year 1 only. Prints and writes
data/results/S3_G1_filters.md."""
import sys

import numpy as np
import pandas as pd

from scanner.s3_p1 import t_stat
from scanner.s3_pods import RES

sys.stdout.reconfigure(encoding="utf-8")
d = pd.read_csv(RES / "S3_G1_datasheet.csv")
d["Day"] = pd.to_datetime(d["Day"])
Y1 = d["Day"] < "2025-10-01"
SKIP = {"day-1 gap ≥ +0.3 %": d["Day-1 gap at open %"] >= 0.3,
        "OR width 0.5-0.8 %": d["OR width %"].between(0.5, 0.8, inclusive="left"),
        "VIX ≥ 17": d["VIX at signal"] >= 17}
DOUBLE = {"signal 09:45-11:29": d["Minutes after 09:30"].between(15, 120, inclusive="left"),
          "VIX 12-14": d["VIX at signal"].between(12, 14, inclusive="left")}


def stats(name, lots):
    """lots per trade (0 = skipped). ₹ scales with lots; % is the ₹ result over the ₹ paid."""
    m = lots > 0
    rs = d["G1 net ₹"] * lots
    paid = d["Premium (₹/lot)"] * lots
    pct = d["G1 net %"][m]
    eq = rs[m].cumsum()
    y = lambda k: rs[m & k].sum() / paid[m & k].sum() * 100 if (m & k).any() else np.nan
    return (f"| {name} | {int(m.sum())} | {int(lots.sum())} | {rs.sum() / paid.sum() * 100:+.1f} % | {pct.mean():+.1f} % | "
            f"{t_stat(rs[m] / lots[m]):.2f} | {(pct > 0).mean() * 100:.0f} % | ₹{rs.sum():,.0f} | ₹{(eq - eq.cummax()).min():,.0f} | "
            f"₹{rs[m].min():,.0f} | {y(Y1):+.1f} % / {y(~Y1):+.1f} % |")


HEAD = ["| Version | Trades | Lots | Return on ₹ paid | Mean % a trade | t | Won | Total ₹ | Max drawdown | Worst trade | Year 1 / year 2 |",
        "|---|---|---|---|---|---|---|---|---|---|---|"]
one = pd.Series(1, index=d.index)
skip_all = np.logical_or.reduce(list(SKIP.values()))
dbl_any = np.logical_or.reduce(list(DOUBLE.values()))
out = ["# G1 with the datasheet's bucket filters (in-sample, 2024-10 → 2026-10)", "",
       "Skip = no trade; double = 2 lots. Return on ₹ paid = total ₹ ÷ total premium paid. t on ₹ a lot per trade.", "",
       "## Each filter alone, then together", "", *HEAD, stats("G1 as registered (1 lot)", one)]
for k, v in SKIP.items():
    out.append(stats(f"skip {k}", one.where(~v, 0)))
for k, v in DOUBLE.items():
    out.append(stats(f"double {k}", one.where(~v, 2)))
out += [stats("skip all three", one.where(~skip_all, 0)),
        stats("double either", one.where(~dbl_any, 2)),
        stats("skip all three + double either", one.where(~dbl_any, 2).where(~skip_all, 0))]

# honest check: pick buckets on year 1 only, apply to year 2
EDGES = {"Day-1 gap at open %": [-9, -0.3, 0, 0.3, 9], "OR width %": [0, 0.3, 0.5, 0.8, 9],
         "VIX at signal": [0, 12, 14, 17, 99], "Minutes after 09:30": [0, 15, 60, 120, 999],
         "Prev close vs EMA20 %": [-99, -2, 0, 2, 99], "Premium % of spot": [0, 0.3, 0.5, 0.8, 9],
         "Days to expiry": [1, 2, 3, 4, 99]}
lots2 = pd.Series(1, index=d.index)
picked = []
for c, e in EDGES.items():
    b = pd.cut(d[c], e, right=False)
    m1 = d[Y1].groupby(b[Y1], observed=True)["G1 net %"].agg(["mean", "count"])
    for iv, r in m1.iterrows():
        if r["count"] < 15:
            continue
        if r["mean"] < 0:
            lots2[~Y1 & (b == iv)] = 0
            picked.append(f"skip {c} {iv} (year 1 {r['mean']:+.1f} %, {int(r['count'])})")
        elif r["mean"] > 15:
            lots2[~Y1 & (b == iv) & (lots2 > 0)] = 2
            picked.append(f"double {c} {iv} (year 1 {r['mean']:+.1f} %, {int(r['count'])})")
y2 = ~Y1
base2 = d.loc[y2, "G1 net ₹"].sum() / d.loc[y2, "Premium (₹/lot)"].sum() * 100
l2 = lots2[y2]
f2 = (d.loc[y2, "G1 net ₹"] * l2).sum() / (d.loc[y2, "Premium (₹/lot)"] * l2).sum() * 100
out += ["", "## Honest check: buckets picked on year 1 (2024-10 → 2025-09) only, applied to year 2", "",
        "Rule: a bucket with ≥ 15 year-1 trades and a negative year-1 mean is skipped; one above +15 % is doubled.", ""]
out += [f"- {p}" for p in picked]
out += ["", f"Year 2, G1 as registered: {y2.sum()} trades, return on ₹ paid {base2:+.1f} %, ₹{d.loc[y2, 'G1 net ₹'].sum():,.0f}",
        f"Year 2, with the year-1 buckets: {int((l2 > 0).sum())} trades, {int(l2.sum())} lots, return on ₹ paid {f2:+.1f} %, "
        f"₹{(d.loc[y2, 'G1 net ₹'] * l2).sum():,.0f}"]
# the same check for the five filters named in the datasheet reply, scored on each year alone
out += ["", "## The five named filters, bucket mean in each year", "", "| Filter | Year 1 trades | Year 1 mean | Year 2 trades | Year 2 mean |", "|---|---|---|---|---|"]
for k, v in {**{f"skip {a}": b for a, b in SKIP.items()}, **{f"double {a}": b for a, b in DOUBLE.items()}}.items():
    a, b = d.loc[v & Y1, "G1 net %"], d.loc[v & ~Y1, "G1 net %"]
    out.append(f"| {k} | {len(a)} | {a.mean():+.1f} % | {len(b)} | {b.mean():+.1f} % |")
(RES / "S3_G1_filters.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
