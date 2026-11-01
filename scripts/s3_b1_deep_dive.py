"""B1 (breakout + volume) deep dive: where the primary trades lose. Descriptive only, no rule is changed or chosen.

    INDEX_STORE=<index-data checkout>/data/index python scripts/s3_b1_deep_dive.py

Reads S3_B1_trades.csv, S3_F4_maxup_trades.csv and the NIFTY 50 spot store; writes data/results/S3_B1_deep_dive_2026-11-01.md.
"""
from __future__ import annotations

from datetime import time
from pathlib import Path

import numpy as np
import pandas as pd

from index_data import load as L

RES = Path(__file__).resolve().parents[1] / "data" / "results"
P, B = "OR 15 min · volume 2x · stop 25 %", "OR 15 min · volume none · stop 25 %"


def cell(t, c):
    return t[(t["cell"] == c) & (t["cost_mult"] == 1.0) & (t["skip"].fillna("") == "")].copy()


def spot_path(p: pd.DataFrame) -> pd.DataFrame:
    sp = L.spot_1m("2024-10-01", "2026-10-28", "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date.astype(str)
    rows = []
    for r in p.itertuples():
        g = sp[sp["d"] == r.day].set_index("timestamp")
        tt = g.index.time
        rng = g[(tt >= time(9, 15)) & (tt < time(9, 30))]
        hi, lo = rng["high"].max(), rng["low"].min()
        ts = pd.Timestamp(f"{r.day} {r.signal}", tz=g.index.tz)
        s0, sgn = g["close"].get(ts), (1 if r.side == "CE" else -1)
        a = g[(g.index > ts) & (g.index.time <= time(15, 15))]
        back = (a["close"] < hi) if sgn > 0 else (a["close"] > lo)

        def mv(m):
            x = a["close"][a.index <= ts + pd.Timedelta(minutes=m)]
            return sgn * (x.iloc[-1] / s0 - 1) * 100 if len(x) else np.nan

        rows.append({"range_pct": (hi - lo) / lo * 100, "mv15": mv(15), "mv60": mv(60),
                     "mv_close": sgn * (a["close"].iloc[-1] / s0 - 1) * 100,
                     "back_min": (back.idxmax() - ts).total_seconds() / 60 if back.any() else np.nan,
                     "net": r.net_pct_premium})
    return pd.DataFrame(rows)


def main() -> None:
    t = pd.read_csv(RES / "S3_B1_trades.csv")
    p, b = cell(t, P), cell(t, B)
    both = p.merge(b[["day", "signal"]], on="day", suffixes=("", "_b"))
    same = int((both["signal"] == both["signal_b"]).sum())
    hm = pd.to_datetime(p["signal"], format="%H:%M")
    p["bucket"] = pd.cut(hm.dt.hour * 60 + hm.dt.minute, [0, 574, 584, 599, 629, 689, 781],
                         labels=["09:30-34", "09:35-44", "09:45-59", "10:00-29", "10:30-11:29", "11:30-13:00"])
    p["dte"] = (pd.to_datetime(p["expiry"]) - pd.to_datetime(p["day"])).dt.days
    mu = pd.read_csv(RES / "S3_F4_maxup_trades.csv")
    mu = mu[mu["pod"] == "B1"]
    mu["tpeak"] = (pd.to_datetime(mu["peak_held_at"]) - pd.to_datetime(mu["day"] + " " + mu["entry"])).dt.total_seconds() / 60
    s = spot_path(p)
    tr = p[p["reason"] == "trail"]
    w, lo = p[p["net_pct_premium"] > 0], p[p["net_pct_premium"] <= 0]

    def tbl(g, head):
        out = [f"| {head} | Trades | Mean net % | Median | Win rate |", "|---|---|---|---|---|"]
        for k, x in g:
            out.append(f"| {k} | {len(x)} | {x.mean():+.1f} % | {x.median():+.1f} % | {(x > 0).mean() * 100:.0f} % |")
        return out

    L_ = ["# S3 B1 · breakout + volume: where it loses (deep dive, 2026-11-01)", "",
          "Descriptive only: no rule changed, nothing picked from it. Primary cell `" + P + "`, 488 trades, "
          "2024-10-01 → 2026-10-28, NIFTY, spot store after the 2026-10-30 repair.", "",
          "## 1. The index itself barely follows through",
          f"- Median opening range (09:15-09:29) {s['range_pct'].median():.2f} % of NIFTY.",
          f"- NIFTY's move in the breakout direction after the signal, median: 15 min {s['mv15'].median():+.3f} %, "
          f"60 min {s['mv60'].median():+.3f} %, to 15:15 {s['mv_close'].median():+.3f} % (mean {s['mv_close'].mean():+.3f} %).",
          f"- Ends 15:15 in the breakout direction on {(s['mv_close'] > 0).mean() * 100:.0f} % of days (a coin flip).",
          f"- Closes back inside the range before 15:15 on {s['back_min'].notna().sum()} of {len(s)} days; median "
          f"{s['back_min'].median():.0f} min after the signal; within 30 min on {(s['back_min'] <= 30).sum()}.",
          f"- Net when NIFTY ended in the direction: {s.loc[s['mv_close'] > 0, 'net'].mean():+.1f} % ({(s['mv_close'] > 0).sum()} "
          f"trades); when not: {s.loc[s['mv_close'] <= 0, 'net'].mean():+.1f} %.", "",
          "## 2. The volume test hardly filters",
          f"- First breakout with no volume test: {len(b)} trades, {b['net_pct_premium'].mean():+.1f} % a trade; with 2x volume: "
          f"{len(p)}, {p['net_pct_premium'].mean():+.1f} %.",
          f"- Same signal minute on {same} of {len(both)} common days; otherwise the confirmed minute is usually 1-20 min later.", "",
          "## 3. Exits"]
    L_ += tbl(p.groupby("reason")["net_pct_premium"], "Exit")
    L_ += ["", f"- {(tr['net_pct_premium'] < 0).sum()} of {len(tr)} trail exits are losses ({(tr['net_pct_premium'] <= -15).sum()} "
           "at -15 % or worse): the trail arms on any profit, so a trade that is up 1 % and then falls exits near -25 %, "
           "like a stop.",
           f"- Stops book about -28 %, not -25 %: exit slippage, the minute's move past the level and charges.",
           f"- Wins {len(w)}, average {w['net_pct_premium'].mean():+.1f} %; losses {len(lo)}, average {lo['net_pct_premium'].mean():+.1f} %. "
           f"Break-even at a 30 % win rate needs the average win near 2.3x the average loss; it is "
           f"{w['net_pct_premium'].mean() / -lo['net_pct_premium'].mean():.1f}x.", "",
           "## 4. Max up while held",
           f"- Quartiles {', '.join(f'{x:+.0f} %' for x in mu['max_up_held_pct'].quantile([.25, .5, .75]))}; "
           f"never above +5 %: {(mu['max_up_held_pct'] < 5).sum()} trades; reached +20 % and still booked a loss: "
           f"{((mu['max_up_held_pct'] >= 20) & (mu['net_pct_premium'] < 0)).sum()}.",
           f"- Median {mu['tpeak'].median():.0f} min from entry to the peak; peak within 10 min on {(mu['tpeak'] <= 10).sum()}.", "",
           "## 5. By signal time"]
    L_ += tbl(p.groupby("bucket", observed=True)["net_pct_premium"], "Signal")
    late = int((p["bucket"].isin(["10:30-11:29", "11:30-13:00"])).sum())
    L_ += ["", f"(10:30-13:00 has {late} trades: too few to read as an edge, and choosing it now would be fitting.)", "",
           "## 6. By days to expiry (calendar)"]
    L_ += tbl(p.groupby(pd.cut(p["dte"], [-1, 1, 3, 7, 30]), observed=True)["net_pct_premium"], "Days")
    L_ += ["", "## 7. By opening-range size"]
    L_ += tbl(s.groupby(pd.qcut(s["range_pct"], 3), observed=True)["net"], "Range %")
    out = RES / "S3_B1_deep_dive_2026-11-01.md"
    out.write_text("\n".join(L_) + "\n", encoding="utf-8")
    print("\n".join(L_))


if __name__ == "__main__":
    main()
