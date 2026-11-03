"""Expiry-day intraday option buying, a first look (the user, 2026-11-03: screenshots of the NIFTY 03 Nov 23700 call,
"this is all what am planning, it is an intraday method"). Descriptive only, no rule is chosen from it.

On every NIFTY expiry day with option minutes (Oct 2024 → Oct 2026): at 09:20 take the spot, then for the call and the
put 0-6 strikes out of the money (50-point steps), buy at the 09:20 close + slippage (s3_engine's rule: 0.5 %, 1 % for
2+ strikes out), and record: max up (highest minute high to 15:29, % over the fill), and the 15:15 close sold − slippage
(charges not included; they are ~₹40-60 a lot, large against a ₹2-10 option). Writes data/results/S3_expiry_day_scan.md
and S3_expiry_day_scan_trades.csv.
"""
import pandas as pd

from index_data import load as L
from scanner.s3_engine import spot_at
from scanner.s3_pods import RES

OFFSETS = range(0, 7)
rows = []
for ex in L.expiries("NIFTY"):
    if not (pd.Timestamp("2024-10-01").date() <= ex <= pd.Timestamp("2026-10-30").date()):
        continue
    s = spot_at(ex, 9, 20)
    ch = L.options_day("NIFTY", ex, ex)
    if s is None or ch.empty:
        continue
    atm = round(s / 50) * 50
    for opt in ("CE", "PE"):
        for o in OFFSETS:
            k = atm + 50 * o if opt == "CE" else atm - 50 * o
            px = L.price_at(ch, k, opt, L.at(ex, 9, 20), stale=3)
            if px is None or px <= 0:
                continue
            fill = px * (1.005 if o < 2 else 1.01)
            g = ch[(ch["strike"] == k) & (ch["option_type"] == opt) & (ch["timestamp"] > L.at(ex, 9, 20))]
            out = L.price_at(ch, k, opt, L.at(ex, 15, 15), stale=30)
            if g.empty or out is None:
                continue
            hi = g.loc[g["high"].idxmax()]
            rows.append({"day": ex, "weekday": ex.strftime("%a"), "opt": opt, "otm_strikes": o, "strike": k, "spot_0920": s,
                         "entry": round(fill, 2), "max_up_pct": (hi["high"] / fill - 1) * 100,
                         "peak_at": hi["timestamp"].strftime("%H:%M"),
                         "sold_1515_pct": (out * (0.995 if o < 2 else 0.99) / fill - 1) * 100})
df = pd.DataFrame(rows)
df.to_csv(RES / "S3_expiry_day_scan_trades.csv", index=False)
out = ["# Expiry-day option buying at 09:20, NIFTY, Oct 2024 → Oct 2026 (descriptive)", "",
       f"{df['day'].nunique()} expiry days. Buy at the 09:20 close + slippage; max up = highest minute high to 15:29; "
       "sold = 15:15 close − slippage, before charges.", ""]
for opt, name in (("CE", "Calls"), ("PE", "Puts")):
    d = df[df["opt"] == opt]
    out += [f"## {name}", "", "| Strikes out | Days | Paid (median ₹) | Max up mean | Max up median | ≥ +100 % | ≥ +500 % | "
            "Sold 15:15 mean | Sold median | Went below −90 % at 15:15 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for o, g in d.groupby("otm_strikes"):
        mu, so = g["max_up_pct"], g["sold_1515_pct"]
        out.append(f"| {o} | {len(g)} | {g['entry'].median():.1f} | {mu.mean():+.0f} % | {mu.median():+.0f} % | "
                   f"{(mu >= 100).mean() * 100:.0f} % | {(mu >= 500).mean() * 100:.0f} % | {so.mean():+.0f} % | "
                   f"{so.median():+.0f} % | {(so <= -90).mean() * 100:.0f} % |")
    out.append("")
both = df.pivot_table(index=["day", "otm_strikes"], columns="opt", values=["entry", "sold_1515_pct"]).dropna()
out += ["## Call + put together (no direction picked), sold 15:15", "", "| Strikes out | Days | Mean | Median | Won |",
        "|---|---|---|---|---|"]
for o, g in both.groupby(level="otm_strikes"):
    paid = g[("entry", "CE")] + g[("entry", "PE")]
    back = g[("entry", "CE")] * (1 + g[("sold_1515_pct", "CE")] / 100) + g[("entry", "PE")] * (1 + g[("sold_1515_pct", "PE")] / 100)
    r = (back / paid - 1) * 100
    out.append(f"| {o} | {len(g)} | {r.mean():+.0f} % | {r.median():+.0f} % | {(r > 0).mean() * 100:.0f} % |")
(RES / "S3_expiry_day_scan.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
