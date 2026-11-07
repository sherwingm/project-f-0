"""How many days of holding gives the good result for G1 / G1-F (the user, 2026-11-07: "check the backtest how many days of
holding makes the good result; first I suggested hold up to next day close; if you found any pattern on holding, try that too").

Same trades as G1's history (scanner.s3_put1_hold signal; ATM put of the nearest weekly; bought the minute after the signal
minute). Fixed holding, 50 % stop on every minute of every held day, slippage and charges as the S3 engine:
  k0     : same day, out 15:15 (PUT1 as first registered, with the stop)
  open   : next session 09:16 (the exit used until 2026-11-06)
  k1..k5 : out at the close (15:29 minute) of the k-th session after the entry day; k <= sessions to expiry
  to expiry : the expiry-day close (k = sessions to expiry)
Also the peak: max up (no stop, no exit) through each day's close.
Conditional holding rules, decided with information known at the decision time only (the put's booked result at that
minute), evaluated from the fixed-hold results above (valid because a held path is the same until the decision):
  C1 : at the next 09:16 keep to the next close only if the put is in profit then, else sell at 09:16
  C2 : at the next close keep to the close after (day 2) only if the put is in profit, else sell at the next close
  C3 : at the next close keep to expiry only if the put is up >= 50 %, else sell at the next close
  C4 : at the next close keep to expiry only if the put is in profit, else sell at the next close
A rule fixed before the numbers; these four are all that were tried. In-sample, history only.
Out: g1_research/data/g1_hold_days_trades.csv, results/g1_hold_days_summary.csv, results/g1_hold_days_rules.csv
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
from scanner.s3_buy_maxup import legs_of, max_up  # noqa: E402
from scanner.s3_engine import Leg, Spec, chain_between, run_day  # noqa: E402

WINDOW = (date(2024, 10, 1), date(2026, 10, 28))


def t_stat(x):
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else np.nan


def one(day, e, ent, exit_day, hh, mm):
    spec = Spec("G1 hold", [Leg("BUY", "PE", 0)], entry=(ent.hour, ent.minute), exit=(hh, mm), stop=0.5)
    r = run_day(spec, day, e, exit_day=exit_day)
    return None if r.get("skip") else r


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
        if e is None:
            continue
        after = [d for d in ses[i + 1:] if d <= e]
        dte = len(after)
        if dte < 1:
            continue
        ent = sg[1] + timedelta(minutes=1)
        base = {"day": day, "expiry": e, "dte": dte, "entry": ent.strftime("%H:%M")}
        r0 = one(day, e, ent, None, 15, 15)
        if r0 is None:
            continue
        res = {"k0": r0, "open": one(day, e, ent, after[0], 9, 16)}
        for k in range(1, min(dte, 5) + 1):
            res[f"k{k}"] = one(day, e, ent, after[k - 1], 15, 29)
        res["expiry"] = res.get(f"k{dte}") if dte <= 5 else one(day, e, ent, after[-1], 15, 29)
        legs = legs_of(res["k1"]["legs"]) if res.get("k1") else None
        chain = chain_between("NIFTY", e, day, e) if legs else None
        t_in = L.at(day, ent.hour, ent.minute)
        for key, r in res.items():
            if r is None:
                continue
            base[f"{key}_net"], base[f"{key}_rs"], base[f"{key}_reason"] = r["net_pct_premium"], r["net_rs"], r["reason"]
        base["prem_rs"] = r0["net_rs"] / r0["net_pct_premium"] * 100 if r0["net_pct_premium"] else np.nan
        if legs is not None:
            for k, d in enumerate(after[:6], start=1):
                base[f"peak_k{k}"] = max_up(chain, legs, t_in, L.at(d, 15, 29), L.at(d, 15, 29))["max_up_any_pct"]
        rows.append(base)
    T = pd.DataFrame(rows)
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    num = lambda c: pd.to_numeric(d[c], errors="coerce")  # noqa: E731
    g, w, v = num("Day-1 gap at open %"), num("OR width %"), num("VIX at signal")
    flag = dict(zip(pd.to_datetime(d["Day"]).dt.date, ~((g >= 0.3) | ((w >= 0.5) & (w < 0.8)) | (v >= 17))))
    T["g1f"] = T["day"].map(flag).fillna(False).astype(int)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    T.to_csv(os.path.join(ROOT, "data", "g1_hold_days_trades.csv"), index=False)

    def stats(x, col):
        v = x[f"{col}_net"].dropna()
        rs = x.loc[v.index, f"{col}_rs"]
        return {"n": len(v), "win_pct": (v > 0).mean() * 100 if len(v) else np.nan, "mean_pct": v.mean(),
                "median_pct": v.median(), "t": t_stat(v), "total_rs": rs.sum(),
                "stop_pct": (x.loc[v.index, f"{col}_reason"] == "stop").mean() * 100 if len(v) else np.nan,
                "worst_rs": rs.min()}
    out, pers = [], (("Oct 2024 → now", date(2024, 1, 1)), ("2025 → now", date(2025, 1, 1)))
    for strat, sel in (("G1-F (main)", T[T["g1f"] == 1]), ("G1", T)):
        for per, lo in pers:
            x = sel[sel["day"] >= lo]
            for col, lab in (("k0", "same day 15:15"), ("open", "next 09:16"), ("k1", "1 day: next close"),
                             ("k2", "2 days: close"), ("k3", "3 days: close"), ("k4", "4 days: close"),
                             ("expiry", "to expiry close")):
                xs = x[x[f"{col}_net"].notna()]
                o = {"strategy": strat, "period": per, "hold": lab, "sample": "all with that many days", **stats(xs, col)}
                if col.startswith("k") and col[1:].isdigit() and int(col[1:]) >= 1:
                    pk = xs.get(f"peak_k{col[1:]}")
                    o["reach100_pct"] = (pk >= 100).mean() * 100 if pk is not None and len(pk.dropna()) else np.nan
                out.append(o)
            c = x[x["dte"] >= 3]
            for col, lab in (("k0", "same day 15:15"), ("open", "next 09:16"), ("k1", "1 day: next close"),
                             ("k2", "2 days: close"), ("k3", "3 days: close")):
                out.append({"strategy": strat, "period": per, "hold": lab, "sample": "only trades with >= 3 days to expiry",
                            **stats(c[c[f"{col}_net"].notna()], col)})
    S = pd.DataFrame(out)
    S.to_csv(os.path.join(ROOT, "results", "g1_hold_days_summary.csv"), index=False)

    rules = []
    for strat, sel in (("G1-F (main)", T[T["g1f"] == 1]), ("G1", T)):
        for per, lo in pers:
            x = sel[sel["day"] >= lo].copy()
            stopped = lambda c: x[f"{c}_reason"] == "stop"  # noqa: E731
            def pick(cond, keep, sell):  # keep where cond is true (and not stopped earlier), else sell
                kp = cond & x[f"{keep}_net"].notna()
                return np.where(kp, x[f"{keep}_net"], x[f"{sell}_net"]), np.where(kp, x[f"{keep}_rs"], x[f"{sell}_rs"])
            defs = {
                "C1 at 09:16 keep to next close only if in profit": (x["open_net"] > 0, "k1", "open"),
                "C2 at next close keep to day-2 close only if in profit": (x["k1_net"] > 0, "k2", "k1"),
                "C3 at next close keep to expiry only if up >= 50 %": (x["k1_net"] >= 50, "expiry", "k1"),
                "C4 at next close keep to expiry only if in profit": (x["k1_net"] > 0, "expiry", "k1"),
            }
            for name, (cond, keep, sell) in defs.items():
                net, rs = pick(cond.fillna(False), keep, sell)
                v = pd.Series(net).dropna()
                rules.append({"strategy": strat, "period": per, "rule": name, "n": len(v), "win_pct": (v > 0).mean() * 100,
                              "mean_pct": v.mean(), "median_pct": v.median(), "t": t_stat(v), "total_rs": float(np.nansum(rs)),
                              "kept_pct": cond.fillna(False).mean() * 100})
    R = pd.DataFrame(rules)
    R.to_csv(os.path.join(ROOT, "results", "g1_hold_days_rules.csv"), index=False)
    pd.set_option("display.width", 250)
    print(S[S["period"] == "2025 → now"].round(1).to_string(index=False))
    print(R[R["period"] == "2025 → now"].round(1).to_string(index=False))
    print(len(T), "trades")


if __name__ == "__main__":
    main()
