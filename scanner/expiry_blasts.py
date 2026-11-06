"""Expiry-day option "blasts": how often a cheap out-of-the-money option multiplies 5x / 10x / 20x on its expiry day,
and how big the index move was (descriptive only, no rule chosen).

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.expiry_blasts

The user, 2026-11-05, with screenshots: SENSEX 05 Nov 79000 call ₹12.75 → ₹309.95 (+2,331 %) on expiry day while
SENSEX rose +2.6 %: "check how many have these happens previous".

Part A · 1-minute options, NIFTY and SENSEX, every weekly expiry day in the store (Oct 2024 →). On each expiry day:
  spot at 09:20; calls and puts 0-10 strikes out of the money (NIFTY 50-point steps, SENSEX 100), bought at the 09:20
  close (no slippage: this counts what the market did, not a trade). Only options costing ≥ ₹2 at 09:20 (a price you
  could buy size at). multiple = highest minute high after 09:20 ÷ the 09:20 price; also the 15:15 close ÷ 09:20.
  The day's index move: close vs previous close, and the largest move from 09:20 in either direction.
Part B · NSE daily bhavcopy (NIFTY, BANKNIFTY), every expiry day 2018 →: per contract the day's high ÷ its open and the
  close ÷ the previous close (what the broker app shows as 1D %), for options with open ≥ ₹2 and traded volume.
Writes data/results/expiry_blasts.md, expiry_blasts_days.csv, expiry_blasts_daily.csv.
"""
from __future__ import annotations

from datetime import date, time

import numpy as np
import pandas as pd

from index_data import load as L
from index_data.common import STORE
from scanner.near_expiry_maxup import RES

STEP = {"NIFTY": 50, "SENSEX": 100}
SPOT = {"NIFTY": "NIFTY50", "SENSEX": "SENSEX"}
LEVELS = (2, 3, 5, 10, 20)                    # 2x / 3x added 2026-11-06 (the user: "Check for 2x")
OPTS: list[dict] = []                         # one row per option bought at 09:20 (expiry_blasts_options.csv)
MIN_PX = 2.0


def minute_days(u: str) -> pd.DataFrame:
    sp = L.spot_1m(date(2024, 9, 1), date(2026, 12, 31), SPOT[u])
    sp["d"] = sp["timestamp"].dt.date
    close = sp.groupby("d")["close"].last()
    ses = list(close.index)
    rows = []
    for ex in L.expiries(u):
        ch = L.options_day(u, ex, ex)
        day_sp = sp[sp["d"] == ex]
        if ch.empty or day_sp.empty or ex not in ses or ses.index(ex) == 0:
            continue
        t0 = L.at(ex, 9, 20)
        s0 = day_sp[day_sp["timestamp"] <= t0]
        if s0.empty:
            continue
        s = float(s0["close"].iloc[-1])
        prev = float(close[ses[ses.index(ex) - 1]])
        after = day_sp[day_sp["timestamp"] > t0]
        atm = round(s / STEP[u]) * STEP[u]
        best = {"CE": (0.0, None), "PE": (0.0, None)}
        best_hold = {"CE": None, "PE": None}
        counts = {f"{o}_{lv}x": 0 for o in ("CE", "PE") for lv in LEVELS}
        for opt in ("CE", "PE"):
            for k in range(0, 11):
                kk = atm + STEP[u] * k if opt == "CE" else atm - STEP[u] * k
                px = L.price_at(ch, kk, opt, t0, stale=5)
                if px is None or px < MIN_PX:
                    continue
                g = ch[(ch["strike"] == kk) & (ch["option_type"] == opt) & (ch["timestamp"] > t0)]
                if g.empty:
                    continue
                m = g["high"].max() / px
                o1515 = L.price_at(ch, kk, opt, L.at(ex, 15, 15), stale=30)
                OPTS.append({"index": u, "expiry_day": ex, "opt": opt, "otm": k, "strike": kk, "paid": px, "x": m,
                             "peak_at": g.loc[g["high"].idxmax(), "timestamp"].strftime("%H:%M"),
                             "x_1515": None if o1515 is None else o1515 / px})
                for lv in LEVELS:
                    counts[f"{opt}_{lv}x"] += m >= lv
                if m > best[opt][0]:
                    out = L.price_at(ch, kk, opt, L.at(ex, 15, 15), stale=30)
                    best[opt] = (m, kk)
                    best_hold[opt] = None if out is None else out / px
                    best[opt] = (m, kk, px, g.loc[g["high"].idxmax(), "timestamp"].strftime("%H:%M"))
        rows.append({
            "index": u, "expiry_day": ex, "weekday": ex.strftime("%a"), "spot_0920": s,
            "move_close_pct": (float(day_sp["close"].iloc[-1]) / prev - 1) * 100,
            "up_from_0920_pct": (after["high"].max() / s - 1) * 100 if len(after) else np.nan,
            "down_from_0920_pct": (after["low"].min() / s - 1) * 100 if len(after) else np.nan,
            **{f"best_{o}_x": best[o][0] for o in ("CE", "PE")},
            **{f"best_{o}_strike": best[o][1] if len(best[o]) > 1 else None for o in ("CE", "PE")},
            **{f"best_{o}_paid": best[o][2] if len(best[o]) > 2 else None for o in ("CE", "PE")},
            **{f"best_{o}_peak_at": best[o][3] if len(best[o]) > 3 else None for o in ("CE", "PE")},
            **{f"best_{o}_1515_x": best_hold[o] for o in ("CE", "PE")},
            **counts,
        })
    return pd.DataFrame(rows)


def daily(u: str) -> pd.DataFrame:
    parts = [pd.read_parquet(p) for p in sorted((STORE / "options_daily" / u).glob("*.parquet"))]
    d = pd.concat(parts, ignore_index=True)
    d = d[d["FinInstrmTp"] == "IDO"].copy()
    d["TradDt"], d["XpryDt"] = pd.to_datetime(d["TradDt"]).dt.date, pd.to_datetime(d["XpryDt"]).dt.date
    d = d.sort_values("TradDt")
    key = ["XpryDt", "StrkPric", "OptnTp"]
    d["prev_close"] = d.groupby(key)["ClsPric"].shift(1)
    e = d[(d["TradDt"] == d["XpryDt"]) & (d["TtlTradgVol"] > 0)].copy()
    e["hi_open_x"] = e["HghPric"] / e["OpnPric"]
    e["close_prev_x"] = e["ClsPric"] / e["prev_close"]
    e = e[e["OpnPric"] >= MIN_PX]
    fut = d[(d["TradDt"] == d["XpryDt"])]
    out = []
    for ex, g in e.groupby("XpryDt"):
        row = {"index": u, "expiry_day": ex, "year": ex.year, "contracts": len(g),
               "best_hi_open_x": g["hi_open_x"].max(), "best_close_prev_x": g["close_prev_x"].max()}
        for lv in LEVELS:
            row[f"n_hi_open_{lv}x"] = int((g["hi_open_x"] >= lv).sum())
        out.append(row)
    return pd.DataFrame(out)


def main():
    a = pd.concat([minute_days(u) for u in ("NIFTY", "SENSEX")], ignore_index=True)
    a.to_csv(RES / "expiry_blasts_days.csv", index=False)
    pd.DataFrame(OPTS).to_csv(RES / "expiry_blasts_options.csv", index=False)
    b = pd.concat([daily(u) for u in ("NIFTY", "BANKNIFTY")], ignore_index=True)
    b.to_csv(RES / "expiry_blasts_daily.csv", index=False)
    print(len(a), len(b))


if __name__ == "__main__":
    main()
