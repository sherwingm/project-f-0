"""Test 1 of g1_research/VERIFY_PREREG.md: ATM vs ITM (and OTM) strikes on G1's own signals, puts and the call mirror.
Exit = the live rule (50 % stop every minute, else the next session's 15:29). Engine fills / charges; 1x and 2x costs."""
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
HALF = date(2025, 10, 1)
OFFS = {"PE": [-1, 0, 1, 2, 4], "CE": [1, 0, -1, -2, -4]}          # put: + = ITM; call: - = ITM
NAME = {0: "ATM", 1: "1 ITM", 2: "2 ITM", 4: "4 ITM (deep)", -1: "1 OTM"}


def label(side, k):
    return NAME[k if side == "PE" else -k]


def main():
    sp = L.spot_1m(WINDOW[0], WINDOW[1] + timedelta(days=10), "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    days = {d: g for d, g in sp.groupby("d") if len(g) >= G.MIN_BARS}
    ses = sorted(days)
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    num = lambda c: pd.to_numeric(d[c], errors="coerce")  # noqa: E731
    g, w, v = num("Day-1 gap at open %"), num("OR width %"), num("VIX at signal")
    g1f = dict(zip(pd.to_datetime(d["Day"]).dt.date, ~((g >= 0.3) | ((w >= 0.5) & (w < 0.8)) | (v >= 17))))
    rows = []
    for i, day in enumerate(ses):
        if not WINDOW[0] <= day <= WINDOW[1]:
            continue
        sg = signal(days[day], 15, None)
        if sg is None:
            continue
        side = sg[0]
        e = expiry_after(day)
        if e is None:
            continue
        after = [x for x in ses[i + 1:] if x <= e]
        if not after:
            continue
        ent = sg[1] + timedelta(minutes=1)
        t_in = L.at(day, ent.hour, ent.minute)
        chain = None
        for k in OFFS[side]:
            for cm in (1.0, 2.0):
                spec = Spec("verify", [Leg("BUY", side, k)], entry=(ent.hour, ent.minute), exit=(15, 29), stop=0.5, cost_mult=cm)
                r = run_day(spec, day, e, exit_day=after[0])
                if r.get("skip"):
                    continue
                o = {"day": day, "side": side, "strike": label(side, k), "cost": cm, "dte": len(after), "net_pct": r["net_pct_premium"],
                     "net_rs": r["net_rs"], "reason": r["reason"], "g1f": int(bool(g1f.get(day, False))) if side == "PE" else np.nan}
                if cm == 1.0:
                    if chain is None:
                        chain = chain_between("NIFTY", e, day, after[0])
                    lg = legs_of(r["legs"])
                    o["paid"] = sum(f for _, _, _, f, _ in lg)
                    o["peak"] = max_up(chain, lg, t_in, L.at(after[0], 15, 29), L.at(after[0], 15, 29))["max_up_any_pct"]
                rows.append(o)
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(ROOT, "data", "verify_strikes_trades.csv"), index=False)
    pd.set_option("display.width", 250)
    out = []
    for side, sub in (("PE (G1)", T[T.side == "PE"]), ("PE (G1-F)", T[(T.side == "PE") & (T.g1f == 1)]), ("CE (mirror)", T[T.side == "CE"])):
        for cm in (1.0, 2.0):
            x = sub[sub.cost == cm]
            atm = x[x.strike == "ATM"].set_index("day")["net_pct"]
            for s, gg in x.groupby("strike", sort=False):
                p = sub[(sub.cost == 1.0) & (sub.strike == s)]["peak"]
                n = gg.set_index("day")["net_pct"]
                diff = (n - atm).dropna()
                dd = diff.index.map(lambda z: z < HALF)
                t = diff.mean() / (diff.std(ddof=1) / np.sqrt(len(diff))) if len(diff) > 2 and diff.std(ddof=1) > 0 else np.nan
                out.append({"side": side, "cost": cm, "strike": s, "n": len(gg),
                            "maxup_ge100": (p >= 100).mean() * 100, "maxup_mean": p.mean(), "maxup_med": p.median(),
                            "win": (gg.net_pct > 0).mean() * 100, "mean": gg.net_pct.mean(), "median": gg.net_pct.median(),
                            "total_rs": gg.net_rs.sum(), "stopped": (gg.reason == "stop").mean() * 100,
                            "paid_avg": sub[(sub.cost == 1.0) & (sub.strike == s)]["paid"].mean(),
                            "vsATM_mean": diff.mean(), "vsATM_t": t,
                            "vsATM_h1": diff[dd].mean() if dd.any() else np.nan, "vsATM_h2": diff[~dd].mean() if (~dd).any() else np.nan})
    S = pd.DataFrame(out)
    S.to_csv(os.path.join(ROOT, "results", "verify_strikes_summary.csv"), index=False)
    print(S.round(1).to_string(index=False))
    # pre-registered decision
    print("\nDECISION (G1 puts, all signals; calls alongside): strike beats ATM if paired mean > 0, t >= 2, both halves > 0, and > 0 at 2x costs")
    for side in ("PE (G1)", "CE (mirror)"):
        for s in S[(S.side == side) & (S.strike != "ATM")].strike.unique():
            a = S[(S.side == side) & (S.strike == s) & (S.cost == 1.0)].iloc[0]
            b = S[(S.side == side) & (S.strike == s) & (S.cost == 2.0)].iloc[0]
            ok = a.vsATM_mean > 0 and a.vsATM_t >= 2 and a.vsATM_h1 > 0 and a.vsATM_h2 > 0 and b.vsATM_mean > 0
            print(f"  {side:12s} {s:14s} mean {a.vsATM_mean:+.1f} pts t {a.vsATM_t:.2f} halves {a.vsATM_h1:+.1f}/{a.vsATM_h2:+.1f} 2x {b.vsATM_mean:+.1f} -> {'BEATS ATM' if ok else 'no evidence'}")


if __name__ == "__main__":
    main()
