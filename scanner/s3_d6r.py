"""S3 D6R (strategies/S3_D6R_shortvol_2018_2021.md): D6's weekly short straddle and monthly put-write re-run on
2018-2021 with NSE's official NIFTY close for strike and settlement. Descriptive.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_d6r      # -> data/results/s3_d6r.md
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from index_data.index_close import load as index_close
from scanner.s3_d6_d7 import SLIP, STEP, bhav, closes_1529, quote
from scanner.s3_diagnostics import traded_expiries
from scanner.s3_l1 import lot_for
from scanner.s3_p1 import t_stat
from scanner.s3_pods import RES, page_commit
from server import charges

PAGE = "strategies/S3_D6R_shortvol_2018_2021.md"
START, END, FIRST_WEEKLY = date(2018, 1, 1), date(2021, 12, 31), date(2019, 2, 14)
OVERLAP = date(2021, 10, 21)
OUT = RES / "s3_d6r.md"


def short_trade(day, expiry, legs, spot_in, spot_out, margin_pct) -> dict:
    """D6's short_trade with the lot from NSE's circulars (75, then 50 for expiries from 2021-07-29)."""
    lot = lot_for(expiry)
    prem = sum(px for _, _, px in legs) * (1 - SLIP)
    pay = sum(max(0.0, spot_out - k) if o == "CE" else max(0.0, k - spot_out) for k, o, _ in legs)
    fees = sum(charges.leg(o, "SELL", lot, px * (1 - SLIP))["total"] for k, o, px in legs)
    net = (prem - pay) * lot - fees
    return {"day": day, "expiry": expiry, "lot": lot, "credit_rs": prem * lot, "net_rs": net, "pct": net / (prem * lot) * 100,
            "margin_pct": net / (margin_pct * spot_in * lot) * 100, "move_pct": (spot_out / spot_in - 1) * 100}


def trades(b: pd.DataFrame, c: dict, lo: date, hi: date) -> dict[str, list[dict]]:
    exps = sorted(e for e in traded_expiries("NIFTY") if lo <= e <= hi and e in c)
    weekly, puts = [], {0.94: [], 0.98: []}
    for e0, e1 in zip(exps, exps[1:]):
        k = round(c[e0] / STEP) * STEP
        ce, pe = quote(b, e0, e1, k, "CE"), quote(b, e0, e1, k, "PE")
        if ce and pe:
            weekly.append(short_trade(e0, e1, [(k, "CE", ce), (k, "PE", pe)], c[e0], c[e1], 0.12))
    monthly = [e for e in exps if not any(x.year == e.year and x.month == e.month and x > e for x in exps)]
    for m0, m1 in zip(monthly, monthly[1:]):
        for kk in puts:
            k = round(kk * c[m0] / STEP) * STEP
            px = quote(b, m0, m1, k, "PE")
            if px is None:
                for dk in (STEP, -STEP, 2 * STEP, -2 * STEP):
                    px = quote(b, m0, m1, k + dk, "PE")
                    if px:
                        k += dk
                        break
            if px:
                puts[kk].append(short_trade(m0, m1, [(k, "PE", px)], c[m0], c[m1], 0.15))
    return {"weekly ATM straddle": weekly, "monthly put k 0.94": puts[0.94], "monthly put k 0.98": puts[0.98]}


def _line(name, per, g) -> str:
    return (f"| {name} | {per} | {len(g)} | {(g['net_rs'] > 0).mean() * 100:.0f} % | {g['pct'].mean():+.1f} % | "
            f"{g['pct'].median():+.1f} % | {t_stat(g['pct']):.2f} | {g['pct'].min():+.0f} % | {g['margin_pct'].mean():+.2f} % |")


def main() -> None:
    commit = page_commit(PAGE)
    b = bhav()
    b = b[b["TradDt"] <= END]
    ic = index_close()
    c = ic[ic["index"] == "NIFTY50"].set_index("date")["close"].to_dict()
    res = trades(b, c, START, END)
    out = ["# S3 D6R: D6's selling structures re-run on 2018-2021 (descriptive)", "",
           f"Page `{PAGE}` at commit `{commit}`. Script `scanner/s3_d6r.py`. Spot = NSE official NIFTY 50 close.", "",
           "| Structure | Period | Trades | Win rate | Mean net % of credit | Median | t | Worst | Mean % of margin |",
           "|---|---|---|---|---|---|---|---|---|"]
    for name, rows in res.items():
        f = pd.DataFrame(rows)
        if f.empty:
            continue
        out.append(_line(f"**{name}**", "2018-01 → 2021-12", f))
        mo = f[f["day"] < FIRST_WEEKLY]
        if len(mo) and name.startswith("weekly"):
            out.append(_line(name, "monthly-only, to Feb 2019", mo))
        for y, g in f.groupby(pd.to_datetime(f["expiry"]).dt.year):
            out.append(_line(name, str(y), g))
    # the substitution check: official close vs the 15:29 minute close on the overlap
    c1529 = closes_1529()
    a = pd.DataFrame(trades(b, c, OVERLAP, END)["weekly ATM straddle"])
    m = pd.DataFrame(trades(b, c1529, OVERLAP, END)["weekly ATM straddle"])
    out += ["", "## Check: official close vs the 15:29 minute close (weekly straddle, expiries 2021-10-21 → 2021-12-31)", ""]
    if len(a) and len(m):
        j = a.merge(m, on=["day", "expiry"], suffixes=("_off", "_1529"))
        out.append(f"{len(j)} common trades. Mean net % of credit: official {j['pct_off'].mean():+.1f} %, 15:29 "
                   f"{j['pct_1529'].mean():+.1f} %; mean |difference| {(j['pct_off'] - j['pct_1529']).abs().mean():.1f} points.")
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    pd.concat([pd.DataFrame(v).assign(structure=k) for k, v in res.items()]).to_csv(RES / "s3_d6r_trades.csv", index=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
