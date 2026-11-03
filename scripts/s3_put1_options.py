"""PUT1's puts on REAL NIFTY option minutes, 2024-10-01 → 2026-10-28 (the user, 2026-11-03: "download the option
histories"). Descriptive only, PUT1 stays closed. Option minutes exist only from Oct 2024 (Upstox's expired API and
Kotak serve nothing older), so 2022-24 cannot be priced this way.

Each trade: PUT1's signal (first close below the 09:15-09:29 range, 09:30-13:00), buy 1 lot of the at-the-money put of
the nearest weekly expiry (P4's rule) at the next minute's close + slippage, sell at the 15:15 close − slippage, real
charges (scanner.s3_engine, no stop, no target). Max up: the put's highest minute high (and highest minute close)
between entry and 15:15, against the entry fill. Writes data/results/S3_PUT1_options.md and S3_PUT1_options_trades.csv.
"""
from datetime import date

import pandas as pd

from index_data import load as L
from scanner import s3_engine as E
from scanner.s3_buy4 import WINDOW, expiry_after
from scanner.s3_p1 import t_stat
from scanner.s3_pods import RES
from scanner.s3_put1 import collect

allt = collect(WINDOW)
p = allt[allt["cell"] == "primary"]
rows = []
for _, r in p.iterrows():
    day = r["day"]
    ex = expiry_after(day)
    h, m = map(int, r["entry"].split(":"))
    if ex is None:
        rows.append({"day": day, "skip": "no expiry"}); continue
    spec = E.Spec("PUT1", [E.Leg("BUY", "PE", 0)], entry=(h, m), exit=(15, 15))
    t = E.run_day(spec, day, ex)
    if t.get("skip"):
        rows.append({"day": day, "skip": t["skip"]}); continue
    ch = L.options_day("NIFTY", ex, day)
    g = ch[(ch["strike"] == t["atm"]) & (ch["option_type"] == "PE") & (ch["timestamp"] > L.at(day, h, m))
           & (ch["timestamp"] <= L.at(day, 15, 15))]
    fill = t["premium"]
    rows.append({**t, "expiry": ex, "days_to_expiry": len([d for d in L.trade_days("NIFTY", ex) if d > day]),
                 "signal": r["signal"], "entry": r["entry"], "nifty_move_pct": r["move_pct"],
                 "max_up_high_pct": (g["high"].max() / fill - 1) * 100 if len(g) else None,
                 "max_up_close_pct": (g["close"].max() / fill - 1) * 100 if len(g) else None})
df = pd.DataFrame(rows)
df.to_csv(RES / "S3_PUT1_options_trades.csv", index=False)
ok = df[df["skip"].fillna("") == ""].copy()
x, mu, mc = ok["net_pct_premium"], ok["max_up_high_pct"], ok["max_up_close_pct"]
out = [f"# S3 PUT1 puts on real NIFTY option prices · {WINDOW[0]} → {WINDOW[1]} (descriptive, not a gate)", "",
       "At-the-money put, nearest weekly expiry, 1 lot, bought the minute after the downside breakout, sold at 15:15. "
       "No stop, no target. Real minute prices, slippage and charges (`scanner/s3_engine.py`).", "",
       f"- Breakout days: {len(df)}; priced: {len(ok)}; skipped: {len(df) - len(ok)} "
       f"({', '.join(sorted(set(df['skip'].dropna()) - {''})) or 'none'})",
       f"- **Sold at 15:15, after costs:** mean {x.mean():+.1f} % of premium, median {x.median():+.1f} %, "
       f"t {t_stat(x):.2f}, won {(x > 0).mean() * 100:.0f} %, total ₹{ok['net_rs'].sum():,.0f} "
       f"(average premium paid ₹{ok['premium_rs'].mean():,.0f} a lot)",
       f"- **Max up (highest minute high after entry):** mean {mu.mean():+.0f} %, median {mu.median():+.0f} %; "
       f"by minute closes: mean {mc.mean():+.0f} %, median {mc.median():+.0f} %", "",
       "| Max up reached (minute high) | Trades | Share |", "|---|---|---|"]
for lvl in (0, 25, 50, 100, 200, 400):
    n = int((mu >= lvl).sum())
    out.append(f"| ≥ +{lvl} % | {n} | {n / len(ok) * 100:.0f} % |")
out += ["", "| Days to expiry | Trades | Mean at 15:15 | Max up mean | Max up median |", "|---|---|---|---|---|"]
for k, g in ok.groupby(ok["days_to_expiry"].clip(upper=4)):
    out.append(f"| {k if k < 4 else '4+'} | {len(g)} | {g['net_pct_premium'].mean():+.1f} % | "
               f"{g['max_up_high_pct'].mean():+.0f} % | {g['max_up_high_pct'].median():+.0f} % |")
out += ["", "| Year | Trades | Mean at 15:15 | Total ₹ |", "|---|---|---|---|"]
for y, g in ok.groupby(pd.to_datetime(ok["day"]).dt.year):
    out.append(f"| {y} | {len(g)} | {g['net_pct_premium'].mean():+.1f} % | {g['net_rs'].sum():,.0f} |")
top = ok.nlargest(5, "max_up_high_pct")[["day", "entry", "premium", "max_up_high_pct", "net_pct_premium"]]
out += ["", "Biggest max-up days:", "", "| Day | Entry | Paid | Max up | At 15:15 |", "|---|---|---|---|---|"]
out += [f"| {r.day} | {r.entry} | {r.premium:.1f} | {r.max_up_high_pct:+.0f} % | {r.net_pct_premium:+.0f} % |"
        for r in top.itertuples()]
(RES / "S3_PUT1_options.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
