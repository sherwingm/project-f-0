"""Near-expiry NIFTY buys: which entry-time features pick the +100 % trades? A screen on the S3 TEST window only.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.near_expiry_signals

The user, 2026-11-04: "find the signal" (after data/results/near_expiry_maxup.md: +100 % is common near expiry, but
holding and sell-at-+100 % both lose; the question is which trades get the move).

Input: data/results/near_expiry_nifty_trades.csv (09:20 buys, sessions 0-4 to expiry, calls / puts 0-6 strikes out).
Window: S3 test window only, entry day 2024-10-01 → 2025-09-30 (DECISIONS.md "S3 · index options"). The holdout
(2025-10-01 →) is not read here; it may be used once, for one pre-registered pod, after the test gate passes.

Features, all known at 09:20 on the entry day, fixed before the screen ran. "Aligned" = signed in the option's
direction (+ for a call when NIFTY is up, + for a put when NIFTY is down):
  gap_al       D 09:15 open vs the previous session's close, %, aligned
  first5_al    D 09:20 spot vs D 09:15 open, %, aligned
  prev_al      previous session's close-to-close return, %, aligned
  ret5_al      previous close vs the close 5 sessions before, %, aligned
  ema_al       09:20 spot vs the 20-session EMA of closes, %, aligned
  vix          India VIX at 09:20
  vix_chg      VIX 09:20 minus the previous close, points
  prev_range   previous session's high-low range, % of its close
  iv_rv        "is the option cheap?": the 09:20 ATM straddle / spot, over the average |close-to-close| move of the
               last 10 sessions x sqrt(sessions to expiry + 1); < 1 = priced below recent moves
Bins: terciles of each feature over the test window's trade-days (same cut for calls and puts).
Outcomes per trade (1 lot, net of server/charges.py charges, % of premium paid):
  day_net   sold at D 15:15 (intraday);   held_net  sold at expiry-day 15:15;   hit100  max up >= +100 % (gross)
t is date-clustered (scanner.stats.clustered_t). 9 features x 3 bins x 2 sides x 2 exits = 108 cells: about 5 reach
|t| >= 2 by chance alone, so a single cell is a lead, not a finding. Writes data/results/near_expiry_signals.md and
near_expiry_signals_trades.csv.
"""
from __future__ import annotations

from datetime import date, time

import numpy as np
import pandas as pd

from index_data import load as L
from scanner.near_expiry_maxup import RES
from scanner.stats import clustered_t
from server import charges as C

TEST = (date(2024, 10, 1), date(2025, 9, 30))
FEATS = ["gap_al", "first5_al", "prev_al", "ret5_al", "ema_al", "vix", "vix_chg", "prev_range", "iv_rv"]


def day_table() -> pd.DataFrame:
    sp = L.spot_1m(date(2024, 8, 1), date(2025, 10, 10), "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    days = {d: g.reset_index(drop=True) for d, g in sp.groupby("d") if len(g) >= 300}
    ses = sorted(days)
    close = pd.Series({d: float(days[d]["close"].iloc[-1]) for d in ses})
    hi = pd.Series({d: float(days[d]["high"].max()) for d in ses})
    lo = pd.Series({d: float(days[d]["low"].min()) for d in ses})
    ema = close.ewm(span=20, adjust=False).mean()
    absret = close.pct_change().abs() * 100
    vx = L.vix_1m(date(2024, 8, 1), date(2025, 10, 10))
    vx["d"] = vx["timestamp"].dt.date
    vclose = vx.groupby("d")["close"].last()
    rows = {}
    for i, d in enumerate(ses):
        if i < 21:
            continue
        g, p = days[d], ses[i - 1]
        t = g["timestamp"].dt.time
        op = float(g["open"].iloc[0])
        s920 = float(g[t <= time(9, 20)]["close"].iloc[-1])
        v = vx[(vx["d"] == d) & (vx["timestamp"].dt.time <= time(9, 20))]["close"]
        rows[d] = {"gap": (op / close[p] - 1) * 100, "first5": (s920 / op - 1) * 100,
                   "prev": (close[p] / close[ses[i - 2]] - 1) * 100, "ret5": (close[p] / close[ses[i - 6]] - 1) * 100,
                   "ema": (s920 / ema[p] - 1) * 100, "vix": float(v.iloc[-1]) if len(v) else np.nan,
                   "vix_chg": (float(v.iloc[-1]) - float(vclose.get(p, np.nan))) if len(v) else np.nan,
                   "prev_range": (hi[p] - lo[p]) / close[p] * 100, "rv10": absret.iloc[i - 10:i].mean()}
    return pd.DataFrame.from_dict(rows, orient="index")


def net_pct(entry: float, exit_pct: float | None, lot: int) -> float | None:
    if exit_pct is None or pd.isna(exit_pct):
        return None
    ex = max(0.0, entry * (1 + exit_pct / 100))
    ch = C.round_trip("CE", "BUY", lot, entry, ex)["total"]
    return ((ex - entry) * lot - ch) / (entry * lot) * 100


def build() -> pd.DataFrame:
    a = pd.read_csv(RES / "near_expiry_nifty_trades.csv", parse_dates=["day", "expiry"])
    a["day"] = a["day"].dt.date
    a = a[(a["day"] >= TEST[0]) & (a["day"] <= TEST[1])].copy()
    dt = day_table()
    straddle = a[a["otm"] == 0].pivot_table(index="day", columns="opt", values="entry").sum(axis=1, min_count=2)
    sign = np.where(a["opt"] == "CE", 1.0, -1.0)
    f = dt.reindex(a["day"]).reset_index(drop=True)
    a = a.reset_index(drop=True)
    for c in ("gap", "first5", "prev", "ret5", "ema"):
        a[f"{c}_al"] = f[c].to_numpy() * sign
    a["vix"], a["vix_chg"], a["prev_range"] = f["vix"].to_numpy(), f["vix_chg"].to_numpy(), f["prev_range"].to_numpy()
    a["iv_rv"] = (a["day"].map(straddle) / a["spot"] * 100) / (f["rv10"].to_numpy() * np.sqrt(a["k"] + 1))
    lots = {d: L.lot_on(d) for d in a["day"].unique()}
    a["lot"] = a["day"].map(lots)
    a["day_net"] = [net_pct(r.entry, r.sold_day, r.lot) for r in a.itertuples()]
    a["held_net"] = [net_pct(r.entry, r.held, r.lot) for r in a.itertuples()]
    a["hit100"] = a["max_up"] >= 100
    return a


def screen(a: pd.DataFrame) -> pd.DataFrame:
    out = []
    per_day = a.drop_duplicates(["day", "opt"])
    for feat in FEATS:
        cuts = per_day[feat].quantile([1 / 3, 2 / 3]).to_numpy()
        b = np.digitize(a[feat], cuts)                 # 0 low, 1 mid, 2 high; NaN -> 3
        b[a[feat].isna().to_numpy()] = 3
        for opt in ("CE", "PE"):
            for k in range(3):
                g = a[(b == k) & (a["opt"] == opt)]
                if g.empty:
                    continue
                row = {"feature": feat, "bin": ["low", "mid", "high"][k],
                       "range": f"{'≤' if k == 0 else '>'} {cuts[0]:.2f}" if k == 0 else
                       (f"{cuts[0]:.2f} – {cuts[1]:.2f}" if k == 1 else f"> {cuts[1]:.2f}"),
                       "opt": opt, "trades": len(g), "days": g["day"].nunique(), "hit100": g["hit100"].mean() * 100}
                for ex in ("day_net", "held_net"):
                    row[f"{ex}_mean"] = g[ex].mean()
                    row[f"{ex}_t"] = clustered_t(g[ex], g["day"])
                out.append(row)
    return pd.DataFrame(out)


def main():
    a = build()
    a.to_csv(RES / "near_expiry_signals_trades.csv", index=False)
    s = screen(a)
    s.to_csv(RES / "near_expiry_signals_screen.csv", index=False)
    base = a.groupby("opt").agg(trades=("entry", "size"), days=("day", "nunique"),
                                hit100=("hit100", "mean"), day_net=("day_net", "mean"), held_net=("held_net", "mean"))
    print(base)
    pd.set_option("display.width", 250)
    print(s.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
