"""Max up of the four breakout tests (P4, B1, B2, PUT1) on real NIFTY option minutes, while held and without the
exit (the user, 2026-11-04: "i want this all 4 max up with held and without held"). Descriptive only.

Held = entry → the trade's exit minute. Without held = entry → 15:29 of the same session, as if never sold.
Max up = the highest minute close of the bought option after entry, % above the entry fill (scanner.s3_buy_maxup).
PUT1 has no option minutes on its own 2022-24 test window, so its rules on the 2024-10 → 2026-10 option minutes
(S3_PUT1_options_trades.csv) are used. Writes data/results/S3_maxup_breakouts.md and _trades.csv.

    INDEX_STORE=<index-data checkout>/data/index python scripts/s3_maxup_breakouts.py
"""
import sys
from datetime import date, timedelta

import pandas as pd

from index_data import load as L
from scanner.s3_buy_maxup import legs_of, max_up
from scanner.s3_engine import chain_between
from scanner.s3_pods import RES

SOURCES = {"P4": ("S3_P4_trades.csv", "OR 15 min · trail 25 % · stop 25 %"),
           "B1": ("S3_B1_trades.csv", "OR 15 min · volume 2x · stop 25 %"),
           "B2": ("S3_B2_trades.csv", "OR 15 min · accept 15 closes · stop 25 %"),
           "PUT1": ("S3_PUT1_options_trades.csv", None)}


def trades(pod):
    f, cell = SOURCES[pod]
    t = pd.read_csv(RES / f)
    t = t[t["skip"].fillna("") == ""]
    if cell:
        t = t[(t["cell"] == cell) & (t["cost_mult"] == 1.0)]
    if "traded" in t:
        t = t[t["traded"].astype(str) == "True"]
    return t


rows = []
for pod in SOURCES:
    for r in trades(pod).itertuples():
        day, exit_day, expiry = (date.fromisoformat(str(x)[:10]) for x in (r.day, r.exit_day, r.expiry))
        if pod == "PUT1":
            hh, mm = (int(x) for x in r.entry.split(":"))
        else:
            e = pd.Timestamp(f"2000-01-01 {r.signal}") + timedelta(minutes=1)
            hh, mm = e.hour, e.minute
        eh, em = (int(x) for x in str(r.exit_at).split(":"))
        m = max_up(chain_between("NIFTY", expiry, day, exit_day), legs_of(r.legs), L.at(day, hh, mm),
                   L.at(exit_day, eh, em), L.at(exit_day, 15, 29))
        dte = len([d for d in L.trade_days("NIFTY", expiry) if d > day])
        rows.append({"pod": pod, "day": day, "expiry": expiry, "dte": dte, "entry": f"{hh:02d}:{mm:02d}",
                     "exit_at": r.exit_at, "reason": r.reason, "net_pct_premium": r.net_pct_premium, **m})
a = pd.DataFrame(rows)
a.to_csv(RES / "S3_maxup_breakouts_trades.csv", index=False)


def row(name, g):
    h, w = g["max_up_held_pct"], g["max_up_any_pct"]
    return (f"| {name} | {len(g)} | {h.mean():+.0f} / {w.mean():+.0f} % | {h.median():+.0f} / {w.median():+.0f} % | "
            f"{(h >= 50).mean() * 100:.0f} / {(w >= 50).mean() * 100:.0f} % | "
            f"{(h >= 100).mean() * 100:.0f} / {(w >= 100).mean() * 100:.0f} % | {g['net_pct_premium'].mean():+.1f} % |")


HEAD = ["| Group | Trades | Max up mean (held / without) | Median (held / without) | ≥ +50 % | ≥ +100 % | Sold mean |",
        "|---|---|---|---|---|---|---|"]
out = ["# Max up of the four breakout tests, held vs without the exit (NIFTY options, 2024-10 → 2026-10)", "",
       "Held = entry → the trade's own exit (fail / stop / trail / 15:15). Without held = entry → 15:29 the same day, "
       "as if never sold. Max up = best minute close of the bought option, % above the price paid. Sold = the "
       "booked result after costs. PUT1 = its rules on the option minutes (its own test was spot-only 2022-24). "
       "Descriptive only.", "", "## All trades", "", *HEAD]
out += [row(p, a[a["pod"] == p]) for p in SOURCES]
band = lambda x: "4+" if x >= 4 else str(int(x))
for p in SOURCES:
    g = a[a["pod"] == p]
    out += ["", f"## {p} by days to expiry (sessions left after the entry day)", "", *HEAD]
    out += [row(f"DTE {k}", x) for k, x in g.groupby(g["dte"].map(band))]
    out += ["", f"{p} by exit:", "", *HEAD]
    out += [row(k, x) for k, x in g.groupby("reason")]
(RES / "S3_maxup_breakouts.md").write_text("\n".join(out) + "\n", encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
print("\n".join(out))
