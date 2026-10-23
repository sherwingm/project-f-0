"""S3 D6-D7 (strategies/S3_D6_D7_daily_shortvol_vix_regime.md): unconditional short vol on the daily bhavcopy, and India
VIX against the following realised vol by regime. Descriptive.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_d6_d7      # -> data/results/s3_d6_d7.md
"""
from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd

from index_data import load as L
from scanner.s3_diagnostics import traded_expiries
from scanner.s3_p1 import t_stat
from scanner.s3_pods import RES
from server import charges

OUT = RES / "s3_d6_d7.md"
START, MAIN_END, TEST_END = date(2021, 10, 21), date(2024, 9, 30), date(2025, 9, 30)
SLIP = 0.01
STEP = 50


def bhav() -> pd.DataFrame:
    parts = [pd.read_parquet(p, columns=["TradDt", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "TtlTradgVol",
                                         "NewBrdLotQty"])
             for p in sorted((L._store() / "options_daily" / "NIFTY").glob("*.parquet"))]
    b = pd.concat(parts)
    b = b[b["FinInstrmTp"] == "IDO"].copy()
    b["TradDt"], b["XpryDt"] = pd.to_datetime(b["TradDt"]).dt.date, pd.to_datetime(b["XpryDt"]).dt.date
    return b


def closes_1529() -> dict:
    s = L.spot_1m(START, TEST_END)
    s = s[s["timestamp"].dt.strftime("%H:%M") <= "15:29"]
    return s.groupby(s["timestamp"].dt.date)["close"].last().to_dict()


def lot_for(day: date, expiry: date) -> int:
    try:
        return L.lot_on(day, "NIFTY", expiry) if day >= date(2024, 7, 5) else (50 if day < date(2024, 4, 26) else 25)
    except ValueError:
        return 50 if day < date(2024, 4, 26) else 25


def quote(b: pd.DataFrame, day: date, expiry: date, k: float, opt: str) -> float | None:
    r = b[(b["TradDt"] == day) & (b["XpryDt"] == expiry) & (b["StrkPric"] == k) & (b["OptnTp"] == opt) & (b["TtlTradgVol"] > 0)]
    return float(r["ClsPric"].iloc[0]) if len(r) and r["ClsPric"].iloc[0] > 0 else None


def short_trade(day, expiry, legs, spot_in, spot_out, margin_pct) -> dict:
    lot = lot_for(day, expiry)
    prem = sum(px for _, _, px in legs) * (1 - SLIP)
    pay = sum(max(0.0, spot_out - k) if o == "CE" else max(0.0, k - spot_out) for k, o, _ in legs)
    fees = sum(charges.leg(o, "SELL", lot, px * (1 - SLIP))["total"] for k, o, px in legs)
    net = (prem - pay) * lot - fees
    return {"day": day, "expiry": expiry, "lot": lot, "credit_rs": prem * lot, "net_rs": net, "pct": net / (prem * lot) * 100,
            "margin_pct": net / (margin_pct * spot_in * lot) * 100, "move_pct": (spot_out / spot_in - 1) * 100}


def d6(b, c) -> list[str]:
    exps = sorted(e for e in traded_expiries("NIFTY") if START <= e <= TEST_END and e in c)
    weekly, puts = [], {0.94: [], 0.98: []}
    for e0, e1 in zip(exps, exps[1:]):
        s0 = c[e0]
        k = round(s0 / STEP) * STEP
        ce, pe = quote(b, e0, e1, k, "CE"), quote(b, e0, e1, k, "PE")
        if ce and pe:
            weekly.append(short_trade(e0, e1, [(k, "CE", ce), (k, "PE", pe)], s0, c[e1], 0.12))
    monthly = [e for e in exps if not any(x.year == e.year and x.month == e.month and x > e for x in exps)]
    for m0, m1 in zip(monthly, monthly[1:]):
        s0 = c[m0]
        for kk in puts:
            k = round(kk * s0 / STEP) * STEP
            px = quote(b, m0, m1, k, "PE")
            if px is None:   # nearest traded strike within 2 steps
                for dk in (STEP, -STEP, 2 * STEP, -2 * STEP):
                    px = quote(b, m0, m1, k + dk, "PE")
                    if px:
                        k += dk
                        break
            if px:
                puts[kk].append(short_trade(m0, m1, [(k, "PE", px)], s0, c[m1], 0.15))
    out = ["## D6 · Unconditional short vol on the daily bhavcopy (NIFTY)", "",
           f"Weekly: {len(weekly)} straddles; monthly put-write: {len(puts[0.94])} (k 0.94) and {len(puts[0.98])} (k 0.98).", "",
           "| Structure | Period | Trades | Win rate | Mean net % of credit | Median | t | Worst | Mean % of margin a trade |",
           "|---|---|---|---|---|---|---|---|---|"]
    for name, rows in [("weekly ATM straddle", weekly), ("monthly put k 0.94", puts[0.94]), ("monthly put k 0.98", puts[0.98])]:
        f = pd.DataFrame(rows)
        if f.empty:
            continue
        for per, m in [("2021-10 → 2024-09", f["expiry"] <= MAIN_END), ("test 2024-10 → 2025-09", f["expiry"] > MAIN_END)]:
            g = f[m]
            if len(g):
                out.append(f"| {name} | {per} | {len(g)} | {(g['net_rs'] > 0).mean() * 100:.0f} % | {g['pct'].mean():+.1f} % | "
                           f"{g['pct'].median():+.1f} % | {t_stat(g['pct']):.2f} | {g['pct'].min():+.0f} % | {g['margin_pct'].mean():+.2f} % |")
    out += ["", "By year (weekly straddle, mean net % of credit · trades):", ""]
    f = pd.DataFrame(weekly)
    out.append(" · ".join(f"{y}: {g['pct'].mean():+.1f} % ({len(g)})" for y, g in f.groupby(pd.to_datetime(f["expiry"]).dt.year)))
    return out


def d7(c) -> list[str]:
    s = L.spot_1m(START, TEST_END)
    s = s[s["timestamp"].dt.strftime("%H:%M") <= "15:29"].copy()
    s["d"] = s["timestamp"].dt.date
    s["r2"] = np.log(s["close"]).diff() ** 2
    day_r2 = s.groupby("d")["r2"].sum()          # includes the overnight gap at each session's first bar
    v = L.vix_1m(START, TEST_END)
    v = v[v["timestamp"].dt.strftime("%H:%M") <= "15:29"]
    vix = v.groupby(v["timestamp"].dt.date)["close"].last()
    days = [d for d in day_r2.index if d in vix.index]
    r2 = day_r2.reindex(days).to_numpy()
    rows = []
    for i, d in enumerate(days[:-21]):
        rv5 = math.sqrt(r2[i + 1:i + 6].sum() * 252 / 5) * 100
        rv21 = math.sqrt(r2[i + 1:i + 22].sum() * 252 / 21) * 100
        chg = vix[d] - vix[days[i - 5]] if i >= 5 else np.nan
        rows.append((d, float(vix[d]), rv5, rv21, chg))
    f = pd.DataFrame(rows, columns=["d", "vix", "rv5", "rv21", "chg"]).dropna()
    f["band"] = pd.cut(f["vix"], [0, 13, 14, 20, 22, 99], labels=["<13", "13-14", "14-20", "20-22", ">22"], right=False)
    f["dir"] = np.where(f["chg"] > 0, "rising", "falling")
    out = ["", "## D7 · India VIX against the realised vol that follows (NIFTY, 2021-10 → 2025-09)", "",
           "| VIX band | 5-day VIX | Days | Mean VIX | Mean RV next 5 | VIX − RV5 | RV5 > VIX | VIX − RV21 |",
           "|---|---|---|---|---|---|---|---|"]
    for (band, dr), g in f.groupby(["band", "dir"], observed=True):
        out.append(f"| {band} | {dr} | {len(g)} | {g['vix'].mean():.1f} | {g['rv5'].mean():.1f} | {(g['vix'] - g['rv5']).mean():+.1f} | "
                   f"{(g['rv5'] > g['vix']).mean() * 100:.0f} % | {(g['vix'] - g['rv21']).mean():+.1f} |")
    out.append(f"| all | | {len(f)} | {f['vix'].mean():.1f} | {f['rv5'].mean():.1f} | {(f['vix'] - f['rv5']).mean():+.1f} | "
               f"{(f['rv5'] > f['vix']).mean() * 100:.0f} % | {(f['vix'] - f['rv21']).mean():+.1f} |")
    return out


def main() -> None:
    b, c = bhav(), closes_1529()
    lines = ["# S3 D6-D7: daily short vol and the VIX regime map (descriptive)", "",
             "Pre-registered: `strategies/S3_D6_D7_daily_shortvol_vix_regime.md`. Script `scanner/s3_d6_d7.py`.", ""]
    lines += d6(b, c) + d7(c)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
