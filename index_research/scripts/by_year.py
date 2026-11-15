"""Y1 (PROGRAM.md Amendment A6): daily-candle studies by calendar year 2018-2026, entries 2020-02-15 to 2020-06-30 excluded.
Slices saved trade files only (R02b, R09, R14, R15, R17, R18, R19); no re-run. Output: results/Y1_by_year.md and Y1_by_year.csv"""
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

from lib import ROOT, tstat

sys.stdout.reconfigure(encoding="utf-8")
R = os.path.join(ROOT, "results")
COVID = (date(2020, 2, 15), date(2020, 6, 30))
STUDIES = {"R02b": "overnight on the real future (daily)", "R09": "weekly ATM straddle to expiry (daily bhavcopy)", "R14": "trend filters on NIFTY",
           "R15": "short-term reversal on NIFTY", "R17": "calendar effects on NIFTY", "R18": "NIFTY / BANKNIFTY ratio", "R19": "calendar straddle"}


def load(s):
    t = pd.read_csv(os.path.join(R, f"{s}_trades.csv"), parse_dates=["day"])
    t["day"] = t["day"].dt.date
    t = t[(t["day"] >= date(2018, 1, 1)) & ~((t["day"] >= COVID[0]) & (t["day"] <= COVID[1]))]
    t["year"] = [d.year for d in t["day"]]
    return t


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 4 or len(b) < 4:
        return np.nan, np.nan
    d = b.mean() - a.mean()
    return d, d / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def main():
    rows, md = [], ["# Y1: daily-candle studies by year, 2018 to 2026, Covid period (2020-02-15 to 2020-06-30) excluded", "",
                    "Plan: `index_research/PROGRAM.md` Amendment A6 (commit eb2f7437b, before any number). Slices of saved trade files; nothing re-run, nothing promoted.",
                    "Net % per trade after costs (% of notional for futures, of credit / premium for options). Cells with fewer than 8 trades in a year are shown as 'few'.", ""]
    for s, name in STUDIES.items():
        t = load(s)
        md.append(f"## {s}: {name}")
        for cell, g in t.groupby("cell"):
            line, means = [], {}
            for y in range(2018, 2027):
                x = g[g["year"] == y]["net_pct"]
                if len(x) < 8:
                    line.append(f"{y} few" if len(x) else f"{y} -")
                    continue
                means[y] = x.mean()
                rows.append({"study": s, "cell": cell, "year": y, "n": len(x), "mean_pct": x.mean(), "t": tstat(x, g[g["year"] == y]["day"])})
                line.append(f"{y} {x.mean():+.2f}")
            early = g[g["year"] <= 2021]["net_pct"]
            late = g[g["year"] >= 2022]["net_pct"]
            d, t_ = welch(early, late)
            flips = sum(1 for a, b in zip(range(2018, 2026), range(2019, 2027)) if a in means and b in means and np.sign(means[a]) != np.sign(means[b]))
            pos = sum(1 for v in means.values() if v > 0)
            tail = f"; 2018-21 {early.mean():+.2f} (n {len(early)}) vs 2022-26 {late.mean():+.2f} (n {len(late)})" if len(early) and len(late) else ""
            tail += f", diff {d:+.2f} (t {t_:.2f})" if d == d else ""
            md.append(f"- {cell}: " + " | ".join(line) + f" | positive years {pos} of {len(means)}, sign flips between consecutive years {flips}{tail}")
        md.append("")
    pd.DataFrame(rows).to_csv(os.path.join(R, "Y1_by_year.csv"), index=False)
    open(os.path.join(R, "Y1_by_year.md"), "w", encoding="utf-8").write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
