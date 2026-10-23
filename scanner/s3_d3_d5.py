"""S3 D3-D5 (strategies/S3_D3_D5_placebo_tail_sensex.md): NIFTY non-expiry placebo, spot tail study, SENSEX natural
experiment. Descriptive.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_d3_d5 [d3|d4|d5]   # -> data/results/s3_d3_d5.md
"""
from __future__ import annotations

import sys
from datetime import date

import numpy as np
import pandas as pd

from index_data import load as L
from scanner import s3_p6
from scanner.s3_diag2 import _daily, row, slope
from scanner.s3_diagnostics import traded_expiries
from scanner.s3_engine import Spec
from scanner.s3_p1 import EVENTS, TEST, t_stat
from scanner.s3_pods import RES, Pod, run_pod

OUT = RES / "s3_d3_d5.md"
SPOT_END = date(2025, 9, 30)


# ---------- D3 ----------
def nifty_expiries() -> list[date]:
    return sorted(traded_expiries("NIFTY") | set(L.expiries("NIFTY")))


def non_expiry_days(window) -> list[date]:
    ex = set(nifty_expiries())
    days = sorted(set(L.spot_1m(*window)["timestamp"].dt.date))
    return [d for d in days if d not in ex]


def nearest_after(d: date) -> date | None:
    for e in L.expiries("NIFTY"):
        if e > d and d in L.trade_days("NIFTY", e):
            return e
    return None


def placebo(lots: int) -> Pod:
    c = s3_p6.PRIMARY
    lab = lambda _c: f"placebo: short straddle 14:30→15:15 on non-expiry days, {lots} lot{'s' if lots > 1 else ''}"  # noqa: E731
    legs = s3_p6.spec(c).legs
    return Pod(name=f"D3_{lots}lot", title=lab(c), page="strategies/S3_D3_D5_placebo_tail_sensex.md", cells=[c],
               spec=lambda _c, cm=1.0: Spec(lab(_c), legs, entry=c[0], exit=c[1], lots=lots, cost_mult=cm), primary=c,
               neighbours=[], label=lab, skip_events=True, days=non_expiry_days, expiry_for=nearest_after)


def d3() -> list[str]:
    out = ["## D3 · NIFTY placebo: the P6 trade on non-expiry days (test window)", "",
           "| Cell | Sessions to expiry | Trades | Net % of credit | t | Win rate |", "|---|---|---|---|---|---|"]
    td = sorted(set(L.spot_1m(*TEST)["timestamp"].dt.date))
    for lots in (1, 5):
        run_pod(placebo(lots))
        t = pd.read_csv(RES / f"S3_D3_{lots}lot_trades.csv")
        p = t[(t["cost_mult"] == 1.0) & t["traded"]].copy()
        p["day"], p["expiry"] = pd.to_datetime(p["day"]).dt.date, pd.to_datetime(p["expiry"]).dt.date
        p["sessions"] = [sum(1 for x in td if d < x <= e) for d, e in zip(p["day"], p["expiry"])]
        for name, g in [("all", p)] + [(("3+" if k >= 3 else str(k)), g) for k, g in p.groupby(p["sessions"].clip(upper=3))]:
            out.append(f"| {lots} lot{'s' if lots > 1 else ''} | {name} | {len(g)} | {g['net_pct_premium'].mean():+.1f} % | "
                       f"{t_stat(g['net_pct_premium']):.2f} | {(g['net_rs'] > 0).mean() * 100:.0f} % |")
    p6 = pd.read_csv(RES / "S3_P6_trades.csv")
    p6 = p6[(p6["cell"] == s3_p6.label(s3_p6.PRIMARY)) & (p6["cost_mult"] == 1.0) & p6["traded"]]
    out += ["", f"P6 on expiry days (1 lot, re-run): {len(p6)} trades, {p6['net_pct_premium'].mean():+.1f} % "
            f"(t {t_stat(p6['net_pct_premium']):.2f})."]
    return out


# ---------- D4 ----------
def afternoon(day: date) -> dict | None:
    s = L.spot_1m(day, day)
    s = s.set_index(s["timestamp"].dt.strftime("%H:%M"))["close"]
    if "14:30" not in s.index or "15:15" not in s.index:
        return None
    a, b = float(s["14:30"]), float(s["15:15"])
    path = s[(s.index >= "14:30") & (s.index <= "15:15")]
    v = L.vix_1m(day, day)
    v = v[v["timestamp"].dt.strftime("%H:%M") <= "14:30"]
    return {"day": day, "s1430": a, "move": abs(b / a - 1) * 100,
            "exc": max(abs(path.max() / a - 1), abs(path.min() / a - 1)) * 100,
            "vix": float(v["close"].iloc[-1]) if len(v) else np.nan}


def d4() -> list[str]:
    p6 = pd.read_csv(RES / "S3_P6_trades.csv")
    p6 = p6[(p6["cell"] == s3_p6.label(s3_p6.PRIMARY)) & (p6["cost_mult"] == 1.0) & p6["traded"]].copy()
    p6["day"] = pd.to_datetime(p6["day"]).dt.date
    days = [e for e in nifty_expiries() if date(2021, 10, 20) <= e <= SPOT_END and e not in EVENTS]
    f = pd.DataFrame([r for r in (afternoon(d) for d in days) if r]).dropna()
    cal = f.merge(p6[["day", "premium", "spot", "net_pct_premium"]], on="day")
    k = float(((cal["premium"] / cal["spot"] * 100) / cal["vix"]).median())
    f["credit"] = k * f["vix"]
    f["proxy"] = (f["credit"] - f["move"]) / f["credit"] * 100
    cal = cal.merge(f[["day", "proxy"]], on="day")
    bias = float((cal["proxy"] - cal["net_pct_premium"]).mean())
    f["proxy_adj"] = f["proxy"] - bias
    out = ["", "## D4 · Tail study: NIFTY expiry-day 14:30 → 15:15 on spot, with a premium proxy", "",
           f"Credit proxy = {k:.4f} × VIX (% of spot), the median over {len(cal)} P6 test-window trades. Against those trades "
           f"the raw proxy is off by {bias:+.1f} points of credit on average (corr {cal['proxy'].corr(cal['net_pct_premium']):.2f}); "
           "the adjusted proxy subtracts that.", "",
           "| Period | Expiry days | Mean move | 95th pct move | Mean adj. proxy % | Loss > 1x credit | Loss > 2x | Worst day | Worst / avg month |",
           "|---|---|---|---|---|---|---|---|---|"]
    for name, m in [("2021-10 → 2024-09", f["day"] < TEST[0]), ("test 2024-10 → 2025-09", f["day"] >= TEST[0])]:
        g = f[m]
        month = g.groupby(pd.to_datetime(g["day"]).dt.to_period("M"))["proxy_adj"].sum().mean()
        out.append(f"| {name} | {len(g)} | {g['move'].mean():.2f} % | {g['move'].quantile(0.95):.2f} % | {g['proxy_adj'].mean():+.1f} | "
                   f"{(g['proxy_adj'] < -100).mean() * 100:.0f} % | {(g['proxy_adj'] < -200).mean() * 100:.0f} % | "
                   f"{g['proxy_adj'].min():+.0f} % | {abs(min(g['proxy_adj'].min(), 0)) / month:.1f}x |" if month > 0 else
                   f"| {name} | {len(g)} | {g['move'].mean():.2f} % | {g['move'].quantile(0.95):.2f} % | {g['proxy_adj'].mean():+.1f} | "
                   f"{(g['proxy_adj'] < -100).mean() * 100:.0f} % | {(g['proxy_adj'] < -200).mean() * 100:.0f} % | {g['proxy_adj'].min():+.0f} % | month ≤ 0 |")
    out += ["", "By year (adjusted proxy, % of credit):", "", "| Year | Days | Mean | Worst |", "|---|---|---|---|"]
    for y, g in f.groupby(pd.to_datetime(f["day"]).dt.year):
        out.append(f"| {y} | {len(g)} | {g['proxy_adj'].mean():+.1f} | {g['proxy_adj'].min():+.0f} |")
    stress = [d for d in f["day"] if d in (date(2022, 2, 24),) or date(2024, 6, 3) <= d <= date(2024, 6, 7)
              or date(2024, 8, 1) <= d <= date(2024, 8, 9)]
    out += ["", "Stress-window expiry days: " + "; ".join(
        f"{r.day} move {r.move:.2f} %, proxy {r.proxy_adj:+.0f} %" for r in f[f["day"].isin(stress)].itertuples())]
    return out


# ---------- D5 ----------
def d5() -> list[str]:
    k = _daily("SENSEX")
    k = k[k["d"] <= SPOT_END]
    k["wd"] = pd.to_datetime(k["d"]).dt.day_name()
    sx = set(L.expiries("SENSEX")) if (L._store() / "options_1m" / "SENSEX").exists() else set()
    names = sorted(_sensex_expiry_names())
    sx |= set(names)
    fri_end, tue_start, tue_end = date(2025, 1, 3), date(2025, 1, 7), date(2025, 8, 26)
    start = date(2023, 5, 15)
    fb = k[(k["d"] >= start) & (k["d"] <= fri_end) & (k["wd"] == "Friday")]["r_last"].to_numpy()
    fa = k[(k["d"] > fri_end) & (k["wd"] == "Friday") & ~k["d"].isin(sx)]["r_last"].to_numpy()
    tb = k[(k["d"] >= start) & (k["d"] < tue_start) & (k["wd"] == "Tuesday")]["r_last"].to_numpy()
    ta = k[(k["d"] >= tue_start) & (k["d"] <= tue_end) & k["d"].isin(sx) & (k["wd"] == "Tuesday")]["r_last"].to_numpy()
    mb = k[(k["d"] >= start) & (k["d"] <= fri_end) & (k["wd"] == "Monday")]["r_last"].to_numpy()
    ma = k[(k["d"] > fri_end) & (k["wd"] == "Monday")]["r_last"].to_numpy()
    mtb = k[(k["d"] >= start) & (k["d"] < tue_start) & (k["wd"] == "Monday")]["r_last"].to_numpy()
    mta = k[(k["d"] >= tue_start) & (k["d"] <= tue_end) & (k["wd"] == "Monday")]["r_last"].to_numpy()
    out = ["", "## D5 · SENSEX natural experiment (spot, to 2025-09-30)", "",
           "| Weekday | Days before → after | Weekday ratio | Control (Monday) ratio | DiD |", "|---|---|---|---|---|",
           row("Friday (expiry → no expiry, cut 2025-01-03)", fb, fa, mb, ma),
           row("Tuesday (no SENSEX expiry → expiry, 2025-01-07 → 08-26)", tb, ta, mtb, mta),
           "", "SENSEX last-half-hour reversal, 2025-01-07 → 2025-09-30:", "",
           "| Group | Days | Opposite sign | Slope | t |", "|---|---|---|---|---|"]
    w = k[(k["d"] >= tue_start)]
    for name, m in [("SENSEX expiry days", w["d"].isin(sx)), ("Other days", ~w["d"].isin(sx))]:
        g = w[m]
        b, t = slope(g["r_day"].to_numpy(), g["r_last"].to_numpy())
        out.append(f"| {name} | {len(g)} | {(np.sign(g['r_last']) != np.sign(g['r_day'])).mean() * 100:.0f} % | {b:.3f} | {t:.1f} |")
    return out


def _sensex_expiry_names() -> list[date]:
    import subprocess
    r = subprocess.run(["git", "ls-tree", "--name-only", "origin/index-data", "data/index/options_1m/SENSEX/"],
                       cwd=RES.parent.parent, capture_output=True, text=True).stdout.split()
    return [date.fromisoformat(x.rsplit("/", 1)[-1]) for x in r]


def main() -> None:
    which = sys.argv[1:] or ["d3", "d4", "d5"]
    parts = {"d3": d3, "d4": d4, "d5": d5}
    lines = ["# S3 D3-D5: placebo, tail study, SENSEX natural experiment (descriptive)", "",
             "Pre-registered: `strategies/S3_D3_D5_placebo_tail_sensex.md`. Script `scanner/s3_d3_d5.py`.", ""]
    for w in which:
        lines += parts[w]()
    out = OUT if which == ["d3", "d4", "d5"] else RES / f"s3_{'_'.join(which)}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
