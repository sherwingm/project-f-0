"""G1 / G1-F booked result under the NEW live exit (the user, 2026-11-07: "I want the win rate for the next exit rule").

Same trades as G1's history (scanner.s3_put1_hold: 09:15-09:29 range, first close outside it 09:30-13:00, downside only,
ATM put of the nearest weekly with a session left, bought the minute after the signal minute). Two exits, the same engine
(scanner.s3_engine.run_day: 50 % stop on every minute of both days, slippage and charges as in the whole S3 history):
  old : 50 % stop, else sold at the next session's 09:16 (the exit used until 2026-11-06)
  new : 50 % stop, else sold at the next session's close, the 15:29 minute (the live exit from 2026-11-07)
Minute closes, not bid / ask. G1-F = the trades passing the three skip filters (as in the datasheet).
Writes g1_research/data/g1_exit_compare_trades.csv and g1_research/results/g1_exit_compare_summary.csv.
"""
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from index_data import load as L  # noqa: E402
from scanner import s3_regime as G  # noqa: E402
from scanner.s3_b2 import signal  # noqa: E402
from scanner.s3_buy4 import expiry_after  # noqa: E402
from scanner.s3_engine import Leg, Spec, run_day  # noqa: E402

WINDOW = (date(2024, 10, 1), date(2026, 10, 28))
EXITS = {"old: next 09:16": (9, 16), "new: next close 15:29": (15, 29)}


def t_stat(x):
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else np.nan


def main():
    sp = L.spot_1m(WINDOW[0], WINDOW[1] + timedelta(days=10), "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    days = {d: g for d, g in sp.groupby("d") if len(g) >= G.MIN_BARS}
    ses = sorted(days)
    rows = []
    for i, day in enumerate(ses):
        if not WINDOW[0] <= day <= WINDOW[1]:
            continue
        sg = signal(days[day], 15, None)
        if sg is None or sg[0] != "PE":
            continue
        e = expiry_after(day)
        nxt = ses[i + 1] if i + 1 < len(ses) else None
        if e is None or nxt is None or nxt > e:
            continue
        ent = sg[1] + timedelta(minutes=1)
        for name, (h, m) in EXITS.items():
            spec = Spec(name, [Leg("BUY", "PE", 0)], entry=(ent.hour, ent.minute), exit=(h, m), stop=0.5)
            r = run_day(spec, day, e, exit_day=nxt)
            if r.get("skip"):
                continue
            rows.append({"day": day, "exit_rule": name, "reason": r["reason"], "exit_day": r["exit_day"],
                         "exit_at": r["exit_at"], "net_pct": r["net_pct_premium"], "net_rs": r["net_rs"],
                         "premium_rs": r["net_rs"] / r["net_pct_premium"] * 100 if r["net_pct_premium"] else np.nan})
    T = pd.DataFrame(rows)
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    num = lambda c: pd.to_numeric(d[c], errors="coerce")  # noqa: E731
    g, w, v = num("Day-1 gap at open %"), num("OR width %"), num("VIX at signal")
    d["g1f"] = ~((g >= 0.3) | ((w >= 0.5) & (w < 0.8)) | (v >= 17))
    flag = dict(zip(pd.to_datetime(d["Day"]).dt.date, d["g1f"]))
    T["g1f"] = T["day"].map(flag).fillna(False).astype(int)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    T.to_csv(os.path.join(ROOT, "data", "g1_exit_compare_trades.csv"), index=False)
    out = []
    for strat, sel in (("G1-F (main)", lambda x: x[x["g1f"] == 1]), ("G1", lambda x: x)):
        for per, lo in (("Oct 2024 → now", date(2024, 1, 1)), ("2025 → now", date(2025, 1, 1))):
            for name in EXITS:
                x = T[(T["exit_rule"] == name) & (T["day"] >= lo)]
                x = sel(x)
                v = x["net_pct"].values
                m = x.groupby(pd.to_datetime(x["day"]).dt.to_period("M"))["net_rs"].sum()
                out.append({"strategy": strat, "period": per, "exit_rule": name, "n": len(x),
                            "win_pct": (v > 0).mean() * 100, "mean_pct": v.mean(), "median_pct": np.median(v),
                            "t": t_stat(v), "total_rs": x["net_rs"].sum(), "worst_rs": x["net_rs"].min(),
                            "best_rs": x["net_rs"].max(), "stop_pct": (x["reason"] == "stop").mean() * 100,
                            "neg_months": int((m < 0).sum()), "months": len(m), "avg_month_rs": m.mean()})
    S = pd.DataFrame(out)
    S.to_csv(os.path.join(ROOT, "results", "g1_exit_compare_summary.csv"), index=False)
    pd.set_option("display.width", 220)
    print(S.round(1).to_string(index=False))
    print(T.groupby("exit_rule").size().to_dict())


if __name__ == "__main__":
    main()
