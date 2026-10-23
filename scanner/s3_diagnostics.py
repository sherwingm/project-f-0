"""S3 step 2: NIFTY diagnostics before any pod backtest (DECISIONS.md "S3 · index options"). Descriptive, no trades.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_diagnostics   # -> data/results/s3_diagnostics.md

1. Last 30 minutes on expiry days (spot, 2021-10 → latest): variance of 15:00 → 15:29 returns, expiry vs other days and
   vs the same weekday without an expiry; does the last half hour reverse the day's move?
2. Round-number pinning (spot, 2021-10 → latest): is the 15:29 close nearer a multiple of 100 / 500 on expiry days?
3. Option diagnostics, TEST WINDOW ONLY (2024-10-01 → 2025-09-30; the holdout stays unseen):
   a. ATM straddle at 15:00 vs its payoff at expiry and IV vs realised vol, by India VIX band;
   b. expiry-day ATM straddle value by time of day (strike fixed at 09:20);
   c. max pain at 09:20 vs the close.
"""
from __future__ import annotations

import math
from datetime import date, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from index_data import load as L
from scanner.fade_preopen_entry import iv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "results" / "s3_diagnostics.md"
TEST = (date(2024, 10, 1), date(2025, 9, 30))
STEP = 50
T1500, T1529, T0920 = time(15, 0), time(15, 29), time(9, 20)
TIMES = [(9, 20), (10, 0), (11, 15), (12, 30), (13, 30), (14, 15), (14, 45), (15, 0), (15, 15), (15, 25)]


def vix_band(v: float) -> str:
    return "<13" if v < 13 else ("13-20" if v <= 20 else ">20")


def expiry_dates() -> list[date]:
    """NIFTY option expiries as traded (bhavcopy XpryDt), 2021 →; plus those with 1-minute files."""
    parts = [pd.read_parquet(p, columns=["XpryDt"]) for p in sorted((L._store() / "options_daily" / "NIFTY").glob("*.parquet"))]
    x = set(pd.to_datetime(pd.concat(parts)["XpryDt"]).dt.date)
    return sorted(x | set(L.expiries("NIFTY")))


def t_clustered(g: pd.DataFrame, col: str = "edge", by: str = "e") -> float:
    """t of the mean with days sharing an expiry averaged first (they overlap: one expiry, one outcome)."""
    return t_stat(g.groupby(by)[col].mean())


def t_stat(x) -> float:
    x = np.asarray(x, float)
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else float("nan")


# ---------- 1 and 2: spot ----------
def daily_spot(start: date, end: date) -> pd.DataFrame:
    s = L.spot_1m(start, end)
    s["d"] = s["timestamp"].dt.date
    s["t"] = s["timestamp"].dt.time
    rows = []
    for d, g in s.groupby("d"):
        g = g.set_index("t")["close"]
        if T1500 not in g.index or T1529 not in g.index:
            continue
        rows.append((d, float(g.iloc[0]), float(g[T1500]), float(g[T1529])))
    f = pd.DataFrame(rows, columns=["d", "first", "c1500", "c1529"])
    f["prev"] = f["c1529"].shift()
    f["r_last"] = np.log(f["c1529"] / f["c1500"])
    f["r_day"] = np.log(f["c1500"] / f["prev"])
    return f.dropna().reset_index(drop=True)


def last_half_hour(f: pd.DataFrame) -> list[str]:
    f = f.copy()
    f["wd"] = pd.to_datetime(f["d"]).dt.day_name()
    f["year"] = pd.to_datetime(f["d"]).dt.year
    out = ["## 1. Last 30 minutes (15:00 → 15:29), NIFTY spot",
           f"{f['d'].min()} → {f['d'].max()}: {int(f['exp'].sum())} expiry days, {int((~f['exp']).sum())} other days.",
           "", "| Group | Days | Std of 15:00→15:29 return | Variance vs other days |", "|---|---|---|---|"]
    base = (f.loc[~f["exp"], "r_last"] ** 2).mean()
    for name, m in [("Expiry days", f["exp"]), ("Other days", ~f["exp"])]:
        v = (f.loc[m, "r_last"] ** 2).mean()
        out.append(f"| {name} | {int(m.sum())} | {math.sqrt(v) * 100:.3f} % | {v / base:.2f}x |")
    out += ["", "Same weekday, expiry vs not (controls for a weekday effect):", "",
            "| Weekday | Expiry days | Other days | Variance ratio |", "|---|---|---|---|"]
    for wd, g in f.groupby("wd"):
        e, o = g[g["exp"]], g[~g["exp"]]
        if len(e) >= 10 and len(o) >= 10:
            out.append(f"| {wd} | {len(e)} | {len(o)} | {(e['r_last'] ** 2).mean() / (o['r_last'] ** 2).mean():.2f}x |")
    out += ["", "By year:", "", "| Year | Expiry days | Variance ratio |", "|---|---|---|"]
    for y, g in f.groupby("year"):
        e, o = g[g["exp"]], g[~g["exp"]]
        if len(e) >= 5:
            out.append(f"| {y} | {len(e)} | {(e['r_last'] ** 2).mean() / (o['r_last'] ** 2).mean():.2f}x |")
    # bootstrap of the pooled ratio
    rng = np.random.default_rng(7)
    e2, o2 = (f.loc[f["exp"], "r_last"] ** 2).to_numpy(), (f.loc[~f["exp"], "r_last"] ** 2).to_numpy()
    boots = [rng.choice(e2, len(e2)).mean() / rng.choice(o2, len(o2)).mean() for _ in range(2000)]
    out.append(f"\nPooled ratio 95 % bootstrap interval: {np.percentile(boots, 2.5):.2f}x to {np.percentile(boots, 97.5):.2f}x.")
    out += ["", "Does the last half hour reverse the day's move (prev close → 15:00)?", "",
            "| Group | Days | Opposite sign | Slope of r_last on r_day | t |", "|---|---|---|---|---|"]
    for name, m in [("Expiry days", f["exp"]), ("Other days", ~f["exp"])]:
        g = f[m]
        opp = (np.sign(g["r_last"]) != np.sign(g["r_day"])).mean()
        x, y = g["r_day"].to_numpy(), g["r_last"].to_numpy()
        b = np.polyfit(x, y, 1)[0]
        res = y - np.polyval(np.polyfit(x, y, 1), x)
        se = math.sqrt((res ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
        out.append(f"| {name} | {len(g)} | {opp * 100:.0f} % | {b:.3f} | {b / se:.1f} |")
    return out


def pinning(f: pd.DataFrame) -> list[str]:
    out = ["", "## 2. Round-number pinning (the number check), NIFTY spot at 15:29",
           "Share of days whose close is within 10 points of a multiple. With no pinning it is 20 % for 100 and 4 % "
           "for 500; the 15:00 column shows where the index was half an hour earlier.", "",
           "| Multiple | Group | Days | Within 10 pts at 15:29 | at 15:00 | z vs chance (15:29) |", "|---|---|---|---|---|---|"]
    for m in (100, 500):
        p0 = 20 / m
        for name, mask in [("Expiry days", f["exp"]), ("Other days", ~f["exp"])]:
            g = f[mask]
            near = lambda s: np.minimum(s % m, m - s % m) <= 10  # noqa: E731
            a, b = near(g["c1529"]).mean(), near(g["c1500"]).mean()
            z = (a - p0) / math.sqrt(p0 * (1 - p0) / len(g))
            out.append(f"| {m} | {name} | {len(g)} | {a * 100:.1f} % | {b * 100:.1f} % | {z:+.1f} |")
    return out


# ---------- 3: options, test window only ----------
def straddle(df: pd.DataFrame, k: float, at) -> tuple[float | None, float | None]:
    return L.price_at(df, k, "CE", at), L.price_at(df, k, "PE", at)


def spot_minutes(d: date) -> pd.Series:
    s = L.spot_1m(d, d)
    return s.set_index(s["timestamp"].dt.time)["close"]


def vrp(exps: list[date]) -> tuple[list[str], dict]:
    vix = L.vix_1m(*TEST)
    vix = vix.set_index("timestamp")["close"]
    days = sorted({d for d in pd.to_datetime(L.spot_1m(*TEST)["timestamp"]).dt.date})
    rows, miss = [], 0
    for d in days:
        e = next((x for x in exps if x > d), None)
        if e is None or e > TEST[1] + timedelta(days=10):
            continue
        sp = spot_minutes(d)
        if T1500 not in sp.index:
            continue
        s = float(sp[T1500])
        k = round(s / STEP) * STEP
        df = L.options_day("NIFTY", e, d)
        ce, pe = straddle(df, k, L.at(d, 15, 0))
        se = spot_minutes(e)
        if ce is None or pe is None or T1529 not in se.index:
            miss += 1
            continue
        s_exp = float(se[T1529])
        t = ((e - d).days + (15.5 - 15.0) / 24) / 365
        ivs = [v for v in (iv("CE", ce, s, k, t), iv("PE", pe, s, k, t)) if v]
        # realised: 1-minute log returns from d 15:00 to e 15:29, overnight gaps included
        path = L.spot_1m(d, e)
        path = path[(path["timestamp"] >= L.at(d, 15, 0)) & (path["timestamp"] <= L.at(e, 15, 29))]["close"]
        rv = math.sqrt(float((np.diff(np.log(path.to_numpy())) ** 2).sum()) / t)
        v = vix.asof(L.at(d, 15, 0))
        p = ce + pe
        rows.append(dict(d=d, e=e, dte=(e - d).days, s=s, k=k, p=p, payoff=abs(s_exp - k), iv=np.mean(ivs) if ivs else np.nan,
                         rv=rv, vix=v, band=vix_band(v)))
    f = pd.DataFrame(rows)
    f["edge"] = (f["p"] - f["payoff"]) / f["p"]
    out = ["", "## 3a. ATM straddle at 15:00 vs its payoff at expiry (test window 2024-10 → 2025-09)",
           "`edge` = (straddle price − |expiry close − strike|) / straddle price: what a seller held to expiry keeps, "
           f"before costs and slippage. Days without both ATM prices at 15:00: {miss}.", "",
           "| VIX band | Days | Mean edge | Median edge | Seller wins | t by expiry | Mean IV | Mean RV | IV − RV |",
           "|---|---|---|---|---|---|---|---|---|"]
    for band, g in [("All", f)] + list(f.groupby("band")):
        out.append(f"| {band} | {len(g)} | {g['edge'].mean() * 100:+.1f} % | {g['edge'].median() * 100:+.1f} % | "
                   f"{(g['edge'] > 0).mean() * 100:.0f} % | {t_clustered(g):.1f} | {g['iv'].mean() * 100:.1f} | "
                   f"{g['rv'].mean() * 100:.1f} | {(g['iv'] - g['rv']).mean() * 100:+.1f} |")
    out += ["", "By days to expiry:", "", "| DTE | Days | Mean edge | Worst | t by expiry |", "|---|---|---|---|---|"]
    for dte, g in f.groupby(pd.cut(f["dte"], [0, 1, 2, 4, 7, 40], labels=["1", "2", "3-4", "5-7", "8+"]), observed=True):
        out.append(f"| {dte} | {len(g)} | {g['edge'].mean() * 100:+.1f} % | {g['edge'].min() * 100:+.0f} % | {t_clustered(g):.1f} |")
    return out, {"vrp_days": len(f), "vrp_missing": miss}


def expiry_day(exps: list[date]) -> tuple[list[str], dict]:
    rows, mp_rows, miss = [], [], []
    for e in [x for x in exps if TEST[0] <= x <= TEST[1]]:
        sp = spot_minutes(e)
        if T0920 not in sp.index or T1529 not in sp.index:
            miss.append(e)
            continue
        s = float(sp[T0920])
        k = round(s / STEP) * STEP
        df = L.options_day("NIFTY", e, e)
        vals = {}
        for hh, mm in TIMES:
            ce, pe = straddle(df, k, L.at(e, hh, mm))
            vals[f"{hh:02d}:{mm:02d}"] = (ce + pe) if ce is not None and pe is not None else np.nan
        if np.isnan(vals["09:20"]):
            miss.append(e)
            continue
        rows.append(dict(e=e, k=k, s920=s, close=float(sp[T1529]), **vals))
        # max pain from the open interest at 09:20, over the strikes we hold
        oi = df[df["timestamp"] <= L.at(e, 9, 20)].groupby(["strike", "option_type"])["oi"].last().unstack().fillna(0)
        if {"CE", "PE"} <= set(oi.columns) and len(oi) >= 10:
            ks = oi.index.to_numpy()
            pain = [(oi["CE"].to_numpy() * np.maximum(0, x - ks) + oi["PE"].to_numpy() * np.maximum(0, ks - x)).sum() for x in ks]
            mp = float(ks[int(np.argmin(pain))])
            mp_rows.append(dict(e=e, s920=s, close=float(sp[T1529]), mp=mp))
    f = pd.DataFrame(rows)
    out = ["", "## 3b. Expiry-day ATM straddle by time of day (test window; strike fixed at the 09:20 ATM)",
           f"{len(f)} expiry days; {len(miss)} without the ATM strike or spot at 09:20 "
           f"({', '.join(str(x) for x in miss)}).", "",
           "| Time | Median value vs 09:20 | Mean | Days below 09:20 |", "|---|---|---|---|"]
    for c in [f"{h:02d}:{m:02d}" for h, m in TIMES]:
        r = f[c] / f["09:20"]
        out.append(f"| {c} | {r.median() * 100:.0f} % | {r.mean() * 100:.0f} % | {(r < 1).mean() * 100:.0f} % |")
    sell = (f["09:20"] - f["14:45"]) / f["09:20"]
    out += ["", f"Short straddle 09:20 → 14:45 held without a stop, before costs: mean {sell.mean() * 100:+.1f} %, median "
            f"{sell.median() * 100:+.1f} %, wins {(sell > 0).mean() * 100:.0f} %, worst {sell.min() * 100:+.0f} %, t {t_stat(sell.dropna()):.1f} "
            f"({sell.notna().sum()} days). Descriptive only: P1 is judged on its pre-registered page with stops and costs."]
    m = pd.DataFrame(mp_rows)
    out += ["", "## 3c. Max pain at 09:20 vs the close (test window)"]
    if len(m):
        nearer = (abs(m["close"] - m["mp"]) < abs(m["s920"] - m["mp"])).mean()
        mirror = 2 * m["s920"] - m["mp"]
        toward = (abs(m["close"] - m["mp"]) < abs(m["close"] - mirror)).mean()
        out += [f"{len(m)} expiry days. The close was nearer max pain than the 09:20 index was on {nearer * 100:.0f} % of days. "
                f"Placebo: a point the same distance on the other side of 09:20. The close ended nearer max pain than "
                f"that point on {toward * 100:.0f} % of days (50 % = no pull). Mean |close − max pain| "
                f"{abs(m['close'] - m['mp']).mean():.0f} pts vs |09:20 − max pain| {abs(m['s920'] - m['mp']).mean():.0f} pts. "
                "Max pain uses only the strikes in our ±5 % band."]
    return out, {"expiry_days": len(f), "expiry_missing": len(miss)}


def main() -> None:
    exps = expiry_dates()
    f = daily_spot(date(2021, 10, 20), date.today())
    f["exp"] = f["d"].isin(set(exps))
    lines = ["# S3 diagnostics: NIFTY (descriptive, no trades)", "",
             "DECISIONS.md \"S3 · index options\". Spot sections use 2021-10 → latest; option sections use the test "
             "window 2024-10-01 → 2025-09-30 only. Script: `python -m scanner.s3_diagnostics`.", "",
             "Data: after the Upstox path-band re-fill (2026-10-22), 107 of 108 NIFTY expiry days have the ATM and "
             "±4-strike prices at 09:20 / 10:00 / 11:15 / 14:45; 2024-12-26 has one strike only. Before the re-fill the "
             "missing days were the weeks after a > 5 % move, and the straddle edge read +13 % (t 0.7) instead of the "
             "figures below.", ""]
    lines += last_half_hour(f)
    lines += pinning(f)
    a, ia = vrp(exps)
    b, ib = expiry_day(exps)
    lines += a + b
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}", {**ia, **ib})


if __name__ == "__main__":
    main()
