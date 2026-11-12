"""XP (NIFTY expiry-day ATM straddle, buy 09:16, +20 % on the pair else 15:15) replayed on 1-minute option prices, 2024-10 to 2026-10.
Same engine / fills / charges as the other S3 history (scanner.s3_engine). Max up first. History only."""
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
from scanner.s3_buy_maxup import legs_of, max_up  # noqa: E402
from scanner.s3_engine import Leg, Spec, chain_between, run_day  # noqa: E402

W = (date(2024, 10, 1), date(2026, 10, 28))
rows = []
for e in L.expiries("NIFTY"):
    if not W[0] <= e <= W[1]:
        continue
    if e not in set(L.trade_days("NIFTY", e)):
        continue
    out = {"day": e}
    for tag, tgt, cm in (("tgt20", 0.2, 1.0), ("hold", None, 1.0), ("tgt20_2x", 0.2, 2.0), ("hold_2x", None, 2.0)):
        spec = Spec("XP", [Leg("BUY", "CE", 0), Leg("BUY", "PE", 0)], entry=(9, 16), exit=(15, 15), target=tgt, cost_mult=cm)
        r = run_day(spec, e, e)
        if r.get("skip"):
            out["skip"] = r["skip"]
            break
        out[f"{tag}_pct"], out[f"{tag}_rs"], out[f"{tag}_why"] = r["net_pct_premium"], r["net_rs"], r["reason"]
        if tag == "tgt20":
            lg = legs_of(r["legs"])
            out["paid"] = sum(f for _, _, _, f, _ in lg)
            ch = chain_between("NIFTY", e, e, e)
            out["maxup"] = max_up(ch, lg, L.at(e, 9, 16), L.at(e, 15, 15), L.at(e, 15, 15))["max_up_any_pct"]
    rows.append(out)
T = pd.DataFrame(rows)
T.to_csv(os.path.join(ROOT, "data", "xp_history_minute.csv"), index=False)
T = T[T.get("tgt20_pct").notna()] if "tgt20_pct" in T else T
print("expiry days:", len(T), T.day.min(), T.day.max())
mu = T.maxup
print("MAX UP (no exit, to 15:15): >=+20%", round((mu >= 20).mean() * 100), "% | >=+50%", round((mu >= 50).mean() * 100), "% | >=+100%", round((mu >= 100).mean() * 100), "% | mean", round(mu.mean(), 1), "median", round(mu.median(), 1), "max", round(mu.max()))
for tag, lab in (("tgt20", "+20% target else 15:15 (XP rule)"), ("hold", "hold to 15:15"), ("tgt20_2x", "XP rule at 2x costs"), ("hold_2x", "hold at 2x costs")):
    x = T[f"{tag}_pct"]
    rs = T[f"{tag}_rs"]
    eq = rs.cumsum()
    t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
    print(f"{lab:34s} win {round((x > 0).mean() * 100):3d}% avg {x.mean():6.1f}% median {x.median():6.1f}% t {t:5.2f} total Rs {rs.sum():9.0f} worst day Rs {rs.min():8.0f} maxDD Rs {(eq - eq.cummax()).min():8.0f}" + (f" | target hit {round((T['tgt20_why'] == 'target').mean() * 100)}%" if tag == "tgt20" else ""))
x = T.tgt20_pct
print("distribution of the XP-rule result (%):", {q: round(float(np.percentile(x, q)), 1) for q in (5, 10, 25, 50, 75, 90, 95)})
print("days at or below -72 %:", int((x <= -72).sum()), "of", len(x), "| days below -50 %:", int((x <= -50).sum()))
h = pd.Timestamp("2025-10-01").date()
for lab, g in (("Oct 2024 - Sep 2025", T[T.day < h]), ("Oct 2025 - Oct 2026", T[T.day >= h])):
    print(f"{lab}: n {len(g)} avg {g.tgt20_pct.mean():.1f}% total Rs {g.tgt20_rs.sum():.0f}")
T["yr"] = pd.to_datetime(T.day).dt.year
print(T.groupby("yr").agg(n=("tgt20_pct", "size"), avg=("tgt20_pct", "mean"), total=("tgt20_rs", "sum"), maxup100=("maxup", lambda s: (s >= 100).mean() * 100)).round(1).to_string())
