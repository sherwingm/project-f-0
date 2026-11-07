"""Near Tighty (NT) targets: which sell-at level (1.5x, 2x, 3x, 5x, 10x of the price paid) books the best result
(the user, 2026-11-07: "show me the 2x, 3x etc which makes the good returns"). History only, in-sample, descriptive.

    INDEX_STORE=<index-data checkout>/data/index python near_tighty_research/scripts/nt_targets.py

Trades: every G1 history trade (data/results/S3_G1_datasheet.csv, Oct 2024 -> Oct 2026, entry = the engine's fill);
NT = 1-3 sessions to expiry (161 trades), the rest (4-5 sessions) kept for contrast.
Path: the put's minute closes after the entry minute (last traded close carried forward; a mark older than 30 minutes
is not used, as in scanner.s3_buy_maxup), the same marks the max-up measure uses.
Rules per trade: the G1 stop (a mark <= 50 % of the price paid sells at that mark) and, when a target is set, a resting
sell at target x the price paid that fills at the target the first minute a mark reaches it. Otherwise sold at the
window's end. Windows: 'nt_live' = the next session's 09:16 (what Near Tighty sells at today), 'g1_live' = the next
session's 15:29 (what G1 / G1-F sell at since 2026-11-06), 'day1' = same-day 15:29. Every fill gives up the engine's slippage
(0.5 %; 1 % from 2 strikes out of the money, N/A here: ATM). Charges from server/charges.py, the lot of the day.
Writes near_tighty_research/data/nt_target_trades.csv, results/nt_target_summary.csv.
"""
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from index_data import load as L  # noqa: E402
from scanner.s3_engine import chain_between  # noqa: E402
from scanner.stats import clustered_t  # noqa: E402
from server import charges as C  # noqa: E402

STOP, SLIP, STALE_MIN = 0.50, 0.005, 30
TARGETS = (None, 1.5, 2.0, 3.0, 5.0, 10.0)
WINDOWS = {"day1": (0, (15, 29)), "nt_live": (1, (9, 16)), "g1_live": (1, (15, 29))}     # (sessions after day, minute)
SPLIT = "2025-10-01"


def marks(chain: pd.DataFrame, k: float, t_in, t_end) -> pd.Series:
    w = chain[(chain["timestamp"] > t_in) & (chain["timestamp"] <= t_end) & (chain["strike"] == k)
              & (chain["option_type"] == "PE")].drop_duplicates("timestamp", keep="last")
    if w.empty:
        return pd.Series(dtype=float)
    return pd.Series(w["close"].to_numpy(float), index=pd.DatetimeIndex(w["timestamp"])).sort_index()


def simulate(ser: pd.Series, paid: float, t_in, t_end, target):
    """-> (sell price before slippage, reason, time) or None when the window has no usable mark."""
    if ser.empty:
        return None
    last_seen = t_in
    for ts, px in ser.items():
        last_seen = ts
        if px <= paid * STOP:
            return px, "stop", ts
        if target is not None and px >= paid * target:
            return paid * target, "target", ts
    if (t_end - last_seen).total_seconds() > STALE_MIN * 60 and last_seen.date() == t_end.date():
        return None
    return float(ser.iloc[-1]), "end", ser.index[-1]


def main():
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    rows = []
    for r in d.to_dict("records"):
        day, expiry = date.fromisoformat(str(r["Day"])[:10]), date.fromisoformat(str(r["Expiry"])[:10])
        k, paid, dte, lot = float(r["Strike"]), float(r["Premium paid (₹/unit)"]), int(r["Days to expiry"]), int(r["Lot"])
        hh, mm = (int(x) for x in str(r["Entry time"]).split(":"))
        t_in = L.at(day, hh, mm)
        days = [x for x in L.trade_days("NIFTY", expiry) if x > day]
        for wname, (n_after, (eh, em)) in WINDOWS.items():
            end_day = day if n_after == 0 else (days[n_after - 1] if len(days) >= n_after else None)
            if end_day is None:
                continue
            t_end = L.at(end_day, eh, em)
            ser = marks(chain_between("NIFTY", expiry, day, end_day if end_day != day else None), k, t_in, t_end)
            for tg in TARGETS:
                s = simulate(ser, paid, t_in, t_end, tg)
                if s is None:
                    continue
                px, why, ts = s
                sell = px * (1 - SLIP)
                ch = C.leg("PE", "BUY", lot, paid)["total"] + C.leg("PE", "SELL", lot, sell)["total"]
                net = (sell - paid) * lot - ch
                rows.append({"day": day, "dte": dte, "nt": int(1 <= dte <= 3), "window": wname,
                             "target": "none" if tg is None else f"{tg:g}x", "paid": paid, "lot": lot, "sold": sell,
                             "reason": why, "sold_at": ts.strftime("%Y-%m-%d %H:%M"),
                             "max_up_pct": (ser.max() / paid - 1) * 100 if len(ser) else np.nan,
                             "net_rs": net, "net_pct": net / (paid * lot) * 100})
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(ROOT, "data", "nt_target_trades.csv"), index=False)
    out = []
    for (grp, win, tg), g in T.groupby([T["nt"].map({1: "NT 1-3 sessions", 0: "4-5 sessions"}), "window", "target"]):
        x = g["net_pct"]
        h1, h2 = g[g["day"].astype(str) < SPLIT]["net_pct"], g[g["day"].astype(str) >= SPLIT]["net_pct"]
        out.append({"group": grp, "window": win, "target": tg, "n": len(g), "mean_pct": x.mean(), "median_pct": x.median(),
                    "won": (x > 0).mean(), "t": clustered_t(x, g["day"].astype(str)), "total_rs": g["net_rs"].sum(),
                    "half1_pct": h1.mean(), "half2_pct": h2.mean(), "n_half1": len(h1), "n_half2": len(h2),
                    "target_hit": (g["reason"] == "target").mean(), "stop_hit": (g["reason"] == "stop").mean(),
                    "worst_rs": g["net_rs"].min()})
    S = pd.DataFrame(out)
    S.to_csv(os.path.join(ROOT, "results", "nt_target_summary.csv"), index=False)
    pd.set_option("display.width", 250)
    print(S[S["group"] == "NT 1-3 sessions"].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
