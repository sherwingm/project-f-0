"""S3 D2: expiry natural experiments on spot (strategies/S3_D2_expiry_natural_experiments.md). Descriptive.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_diag2      # -> data/results/s3_diag2.md
"""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from index_data import load as L
from scanner.s3_diagnostics import daily_spot, traded_expiries

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "results" / "s3_diag2.md"
START = date(2021, 10, 20)


def bhav_expiries(under: str) -> set[date]:
    x = traded_expiries(under)
    try:
        x |= set(L.expiries(under))
    except FileNotFoundError:
        pass
    return x


def frame(index: str, exps: set[date]) -> pd.DataFrame:
    f = daily_spot(START, date.today()) if index == "NIFTY50" else _daily(index)
    f["exp"] = f["d"].isin(exps)
    f["wd"] = pd.to_datetime(f["d"]).dt.day_name()
    return f


def _daily(index: str) -> pd.DataFrame:
    s = L.spot_1m(START, date.today(), index)
    s["d"], s["t"] = s["timestamp"].dt.date, s["timestamp"].dt.strftime("%H:%M")
    rows = []
    for d, g in s.groupby("d"):
        g = g.set_index("t")["close"]
        if "15:00" in g.index and "15:29" in g.index:
            rows.append((d, float(g["15:00"]), float(g["15:29"])))
    f = pd.DataFrame(rows, columns=["d", "c1500", "c1529"])
    f["prev"] = f["c1529"].shift()
    f["r_last"] = np.log(f["c1529"] / f["c1500"])
    f["r_day"] = np.log(f["c1500"] / f["prev"])
    return f.dropna().reset_index(drop=True)


def did(treat_b, treat_a, ctrl_b, ctrl_a, seed=3, n=2000) -> tuple[float, float, float]:
    r = lambda tb, ta, cb, ca: (np.mean(ta ** 2) / np.mean(tb ** 2)) / (np.mean(ca ** 2) / np.mean(cb ** 2))  # noqa: E731
    est = r(treat_b, treat_a, ctrl_b, ctrl_a)
    rng = np.random.default_rng(seed)
    bs = [r(*(rng.choice(x, len(x)) for x in (treat_b, treat_a, ctrl_b, ctrl_a))) for _ in range(n)]
    return est, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def row(name, tb, ta, cb, ca) -> str:
    e, lo, hi = did(tb, ta, cb, ca)
    return (f"| {name} | {len(tb)} → {len(ta)} | {np.mean(ta ** 2) / np.mean(tb ** 2):.2f}x | {np.mean(ca ** 2) / np.mean(cb ** 2):.2f}x | "
            f"**{e:.2f}x** ({lo:.2f}-{hi:.2f}) |")


def slope(x, y) -> tuple[float, float]:
    b = np.polyfit(x, y, 1)
    res = y - np.polyval(b, x)
    se = math.sqrt((res ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
    return float(b[0]), float(b[0] / se)


def main() -> None:
    nex = bhav_expiries("NIFTY")
    n = frame("NIFTY50", nex)
    cut = date(2025, 9, 1)
    b, a = n[n["d"] < cut], n[n["d"] >= cut]
    ctrl = ["Monday", "Wednesday", "Friday"]
    cb, ca = b[b["wd"].isin(ctrl)]["r_last"].to_numpy(), a[a["wd"].isin(ctrl)]["r_last"].to_numpy()
    lines = ["# S3 D2: expiry natural experiments (spot, descriptive)", "",
             "Pre-registered: `strategies/S3_D2_expiry_natural_experiments.md`. r_last = 15:00 → 15:29. Ratio = variance after / "
             "before; difference-in-differences (DiD) = weekday ratio / control ratio, with a 95 % bootstrap interval.", "",
             "## 1. NIFTY: Thursday lost the weekly expiry, Tuesday gained it (cut 2025-09-01)", "",
             "| Weekday | Days before → after | Weekday ratio | Control (Mon/Wed/Fri) ratio | DiD |", "|---|---|---|---|---|"]
    thu_b = b[(b["wd"] == "Thursday") & b["exp"]]["r_last"].to_numpy()
    thu_a = a[(a["wd"] == "Thursday") & ~a["exp"]]["r_last"].to_numpy()
    tue_b = b[(b["wd"] == "Tuesday") & ~b["exp"]]["r_last"].to_numpy()
    tue_a = a[(a["wd"] == "Tuesday") & a["exp"]]["r_last"].to_numpy()
    lines += [row("Thursday (expiry → no expiry)", thu_b, thu_a, cb, ca), row("Tuesday (no expiry → expiry)", tue_b, tue_a, cb, ca)]

    bex = bhav_expiries("BANKNIFTY")
    k = frame("NIFTYBANK", bex)
    lw, fw = date(2024, 11, 13), date(2023, 9, 6)
    wb = k[(k["d"] >= fw) & (k["d"] <= lw) & (k["wd"] == "Wednesday") & k["exp"]]["r_last"].to_numpy()
    wa = k[(k["d"] > lw) & (k["wd"] == "Wednesday") & ~k["exp"]]["r_last"].to_numpy()
    ctl = k[~k["exp"] & k["wd"].isin(["Monday", "Tuesday", "Thursday", "Friday"])]
    kb = ctl[(ctl["d"] >= fw) & (ctl["d"] <= lw)]["r_last"].to_numpy()
    ka = ctl[ctl["d"] > lw]["r_last"].to_numpy()
    lines += ["", "## 2. BANKNIFTY: Wednesday lost the weekly expiry (weekly Wednesdays 2023-09-06 → 2024-11-13)", "",
              "| Weekday | Days before → after | Weekday ratio | Control (Mon/Tue/Thu/Fri, no expiry) ratio | DiD |", "|---|---|---|---|---|",
              row("Wednesday (expiry → no expiry)", wb, wa, kb, ka)]

    w = k[(k["d"] >= date(2023, 1, 1)) & (k["d"] <= date(2025, 12, 31))]
    lines += ["", "## 3. BANKNIFTY: does the last half hour reverse the day's move? (2023-2025)", "",
              "| Group | Days | Opposite sign | Slope of r_last on r_day | t |", "|---|---|---|---|---|"]
    for name, m in [("Expiry days", w["exp"]), ("Other days", ~w["exp"])]:
        g = w[m]
        bslope, t = slope(g["r_day"].to_numpy(), g["r_last"].to_numpy())
        lines.append(f"| {name} | {len(g)} | {(np.sign(g['r_last']) != np.sign(g['r_day'])).mean() * 100:.0f} % | {bslope:.3f} | {t:.1f} |")
    for y in (2023, 2024, 2025):
        g = w[w["exp"] & (pd.to_datetime(w["d"]).dt.year == y)]
        if len(g) > 5:
            bslope, t = slope(g["r_day"].to_numpy(), g["r_last"].to_numpy())
            lines.append(f"| Expiry days {y} | {len(g)} | {(np.sign(g['r_last']) != np.sign(g['r_day'])).mean() * 100:.0f} % | {bslope:.3f} | {t:.1f} |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
