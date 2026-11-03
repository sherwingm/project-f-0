"""Max up of every S3 buy idea's primary trades on real NIFTY option minutes (the user, 2026-11-03: "using the option
data available from all the previous tests give me the max up mean and median"). Descriptive only.

E1, Q1, B1, G1, P4: S3_F4_maxup_trades.csv (scanner/s3_buy_maxup.py). B2 and P2 are measured here the same way
(s3_buy_maxup.max_up). PUT1: S3_PUT1_options_trades.csv (minute closes). L1 (multi-day straddle, its own file format)
is not included. Writes data/results/S3_maxup_all.md and S3_maxup_B2_P2_trades.csv.
"""
from datetime import date, timedelta

import pandas as pd

from index_data import load as L
from scanner.s3_buy_maxup import legs_of, max_up
from scanner.s3_engine import chain_between
from scanner.s3_pods import RES

SPECS = {"B2": ("OR 15 min · accept 15 closes · stop 25 %", "cell", None),
         "P2": ("long_straddle_14:45_15:25_none", "pod", (14, 45))}

rows = []
for pod, (prim, col, fixed) in SPECS.items():
    t = pd.read_csv(RES / f"S3_{pod}_trades.csv")
    t = t[(t[col] == prim) & (t["cost_mult"] == 1.0) & (t["skip"].fillna("") == "")]
    if "traded" in t:
        t = t[t["traded"].astype(str) == "True"]
    for r in t.itertuples():
        day = date.fromisoformat(str(r.day)[:10])
        exit_day = date.fromisoformat(str(r.exit_day)[:10])
        expiry = date.fromisoformat(str(r.expiry)[:10]) if hasattr(r, "expiry") else None
        if expiry is None:                      # P2 has no expiry column: the nearest expiry on or after the day
            expiry = min(e for e in L.expiries("NIFTY") if e >= day)
        if fixed:
            hh, mm = fixed
        else:
            e = pd.Timestamp(f"2000-01-01 {r.signal}") + timedelta(minutes=1)
            hh, mm = e.hour, e.minute
        eh, em = (int(x) for x in str(r.exit_at).split(":"))
        m = max_up(chain_between("NIFTY", expiry, day, exit_day), legs_of(r.legs), L.at(day, hh, mm),
                   L.at(exit_day, eh, em), L.at(exit_day, 15, 29))
        rows.append({"pod": pod, "day": day, "net_pct_premium": r.net_pct_premium, **m})
new = pd.DataFrame(rows)
new.to_csv(RES / "S3_maxup_B2_P2_trades.csv", index=False)

f4 = pd.read_csv(RES / "S3_F4_maxup_trades.csv")
put = pd.read_csv(RES / "S3_PUT1_options_trades.csv")
put = put[put["skip"].fillna("") == ""].rename(columns={"max_up_close_pct": "max_up_held_pct"})
put["pod"] = "PUT1"
a = pd.concat([f4[["pod", "net_pct_premium", "max_up_held_pct"]], new[["pod", "net_pct_premium", "max_up_held_pct"]],
               put[["pod", "net_pct_premium", "max_up_held_pct"]]], ignore_index=True)
out = ["# Max up of every S3 buy idea (real NIFTY option minutes, Oct 2024 → Oct 2026)", "",
       "Max up = the highest value of the bought option(s) after entry, while held, in % above the price paid "
       "(minute closes). Sold = the booked result after costs. Descriptive only.", "",
       "| Idea | Trades | Max up mean | Max up median | ≥ +50 % | ≥ +100 % | Sold mean | Sold median |",
       "|---|---|---|---|---|---|---|---|"]
for pod in ["P2", "P4", "E1", "Q1", "B1", "G1", "B2", "PUT1"]:
    g = a[a["pod"] == pod]
    mu = g["max_up_held_pct"]
    out.append(f"| {pod} | {len(g)} | {mu.mean():+.1f} % | {mu.median():+.1f} % | {(mu >= 50).mean() * 100:.0f} % | "
               f"{(mu >= 100).mean() * 100:.0f} % | {g['net_pct_premium'].mean():+.1f} % | "
               f"{g['net_pct_premium'].median():+.1f} % |")
(RES / "S3_maxup_all.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
