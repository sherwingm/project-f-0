"""PUT1's rules on 2025-01-01 → 2026-10-29 NIFTY spot (the user, 2026-11-03: "Get the result between 2025-2026").

Descriptive only, not a gate: PUT1 closed on 2022-24 and is not reopened by another window, and the put lead itself
was found on 2024-26 options, so these years are not unseen. Writes data/results/S3_PUT1_2025-26.md.
"""
from datetime import date

import pandas as pd

from scanner.s3_p1 import t_stat
from scanner.s3_pods import RES
from scanner.s3_put1 import collect

WINDOW = (date(2025, 1, 1), date(2026, 10, 29))

allt = collect(WINDOW)
p = allt[allt["cell"] == "primary"]
filt = p[(p["trend_down"] == True) & (p["vix"] < 14)]  # noqa: E712
out = [f"# S3 PUT1 rules on NIFTY spot {WINDOW[0]} → {WINDOW[1]} (descriptive, not a gate)", "",
       "Same code and rules as `scanner/s3_put1.py`; only the window differs. PUT1 stays closed on its 2022-24 result. "
       "These years overlap the options data the put lead came from, so they are not a fair test. Hurdle +0.10 % a trade.",
       "", "| Cell | Trades | Mean move | Median | t | In direction |", "|---|---|---|---|---|---|"]
cells = [("puts, OR 15 (primary rules)", p["move_pct"]),
         *((f"puts, OR {n}", allt[allt["cell"] == f"OR {n}"]["move_pct"]) for n in (12, 18)),
         ("calls, same rules", allt[allt["cell"] == "calls (control)"]["move_pct"]),
         ("puts + P4 filters (trend down, VIX < 14)", filt["move_pct"]),
         ("puts, failure exit", allt[allt["cell"] == "puts, failure exit"]["move_pct"])]
for name, x in cells:
    out.append(f"| {name} | {len(x)} | {x.mean():+.3f} % | {x.median():+.3f} % | {t_stat(x):.2f} | "
               f"{(x > 0).mean() * 100:.0f} % |")
out += ["", "| Year | Put trades | Mean | t | Call trades | Mean | t |", "|---|---|---|---|---|---|---|"]
c = allt[allt["cell"] == "calls (control)"]
for y in (2025, 2026):
    a = p[pd.to_datetime(p["day"]).dt.year == y]["move_pct"]
    b = c[pd.to_datetime(c["day"]).dt.year == y]["move_pct"]
    out.append(f"| {y} | {len(a)} | {a.mean():+.3f} % | {t_stat(a):.2f} | {len(b)} | {b.mean():+.3f} % | {t_stat(b):.2f} |")
(RES / "S3_PUT1_2025-26.md").write_text("\n".join(out) + "\n", encoding="utf-8")
allt.to_csv(RES / "S3_PUT1_2025-26_trades.csv", index=False)
print("\n".join(out))
