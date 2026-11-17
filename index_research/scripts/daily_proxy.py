"""Amendment A7: daily-candle analogs of G1 / G1-C / G1-F / XP on NIFTY, 2018-2026, Covid entries (2020-02-15 to 2020-06-30) excluded.
Real daily option prices (bhavcopy). Output: results/DP_trades.csv, DP_summary.md. Run: python daily_proxy.py"""
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

from daily_studies import bhav, index_close
from lib import CH, ROOT, boot_ci, save, summary, tstat

sys.stdout.reconfigure(encoding="utf-8")
COVID = (date(2020, 2, 15), date(2020, 6, 30))
LOT = 65
SLIP = 0.01


def trade(kind, d, e, K, cp, e_px, x_px, lo2, op2, hi2):
    """one long option leg; entry at close of d, exit at close of next session unless the stop is touched."""
    res = {}
    for cm, sfx in ((1.0, ""), (2.0, "_2x")):
        s = SLIP * cm
        ent = e_px * (1 + s)
        stop = 0.5 * e_px
        if lo2 <= stop:
            raw_exit = op2 if op2 <= stop else stop
            reason = "stop"
        else:
            raw_exit = x_px
            reason = "close"
        ex = raw_exit * (1 - s)
        fees = (CH.leg(cp, "BUY", LOT, ent, on=d)["total"] + CH.leg(cp, "SELL", LOT, ex, on=d)["total"]) * cm
        net = (ex - ent) * LOT - fees
        res[f"net_rs{sfx}"] = net
        res[f"net_pct{sfx}"] = net / (ent * LOT) * 100
    res["reason"] = reason
    res["maxup"] = (hi2 / e_px - 1) * 100
    return res


def main():
    b = bhav("NIFTY")
    o = b[b["FinInstrmTp"] == "IDO"].copy()
    ic = index_close()
    spot, vix = ic["NIFTY50"], ic["INDIAVIX"]
    # daily OHLC of the index from the bhavcopy underlying is not stored; use closes plus the day's range from eod2 for the signal
    nd = pd.read_csv(os.path.join(os.path.dirname(ROOT), "data", "eod2", "nifty 50.csv"), parse_dates=["Date"])
    nd["d"] = nd["Date"].dt.date
    nd = nd.set_index("d")[["Open", "High", "Low", "Close"]].astype(float)
    nd = nd[(nd.index >= date(2018, 1, 1)) & (nd.index <= date(2026, 10, 28))]
    ses = sorted(set(o["TradDt"]))
    nd = nd[nd.index.isin(ses)]
    idx = list(nd.index)
    byday = {d: g for d, g in o.groupby("TradDt")}
    rows = []
    for i in range(2, len(idx) - 1):
        d, p, n_ = idx[i], idx[i - 1], idx[i + 1]
        if COVID[0] <= d <= COVID[1]:
            continue
        gd, gn = byday.get(d), byday.get(n_)
        if gd is None or gn is None:
            continue
        S = float(nd.loc[d, "Close"])
        gap = (nd.loc[d, "Open"] / nd.loc[p, "Close"] - 1) * 100
        v_prev = float(vix.get(p, np.nan))
        sigs = []
        if nd.loc[d, "Close"] < nd.loc[p, "Low"]:
            sigs.append(("PUT", "PE"))
        if nd.loc[d, "Close"] > nd.loc[p, "High"]:
            sigs.append(("CALL", "CE"))
        for name, cp in sigs:
            exps = sorted(e for e in set(gd["XpryDt"]) if e > d)
            if not exps:
                continue
            e = exps[0]
            K = round(S / 50) * 50
            a = gd[(gd["XpryDt"] == e) & (gd["StrkPric"] == K) & (gd["OptnTp"] == cp) & (gd["TtlTradgVol"] > 0)]
            c = gn[(gn["XpryDt"] == e) & (gn["StrkPric"] == K) & (gn["OptnTp"] == cp) & (gn["TtlTradgVol"] > 0)]
            if a.empty or c.empty or float(a["ClsPric"].iloc[0]) < 5:
                continue
            r = trade(name, d, e, K, cp, float(a["ClsPric"].iloc[0]), float(c["ClsPric"].iloc[0]), float(c["LwPric"].iloc[0]), float(c["OpnPric"].iloc[0]), float(c["HghPric"].iloc[0]))
            base = {"day": d, "expiry": e, "strike": K, "year": d.year, "weekly_era": int(d >= date(2019, 2, 14)), **r}
            cells = [f"{name}_all"]
            if v_prev < 17:
                cells.append(f"{name}_vix17")
                if name == "PUT" and gap < 0.3:
                    cells.append("PUT_gapvix")
            for cell in cells:
                rows.append({**base, "cell": cell})
    # XP analog: expiry days, ATM straddle open -> close
    exp_days = sorted(set(o["XpryDt"]) & set(idx))
    for d in exp_days:
        if COVID[0] <= d <= COVID[1] or d not in byday:
            continue
        i = idx.index(d)
        if i < 1:
            continue
        S0 = float(nd.loc[idx[i - 1], "Close"])
        K = round(S0 / 50) * 50
        g = byday[d]
        ce = g[(g["XpryDt"] == d) & (g["StrkPric"] == K) & (g["OptnTp"] == "CE") & (g["TtlTradgVol"] > 0)]
        pe = g[(g["XpryDt"] == d) & (g["StrkPric"] == K) & (g["OptnTp"] == "PE") & (g["TtlTradgVol"] > 0)]
        if ce.empty or pe.empty:
            continue
        o_, c_ = float(ce["OpnPric"].iloc[0]) + float(pe["OpnPric"].iloc[0]), float(ce["ClsPric"].iloc[0]) + float(pe["ClsPric"].iloc[0])
        if o_ < 10:
            continue
        rec = {"day": d, "expiry": d, "strike": K, "year": d.year, "weekly_era": int(d >= date(2019, 2, 14)), "cell": "XPD_all", "reason": "close"}
        for cm, sfx in ((1.0, ""), (2.0, "_2x")):
            s = SLIP * cm
            fees = sum(CH.leg(t, sd, LOT, px, on=d)["total"] for t, sd, px in (("CE", "BUY", float(ce["OpnPric"].iloc[0]) * (1 + s)), ("PE", "BUY", float(pe["OpnPric"].iloc[0]) * (1 + s)),
                                                                              ("CE", "SELL", float(ce["ClsPric"].iloc[0]) * (1 - s)), ("PE", "SELL", float(pe["ClsPric"].iloc[0]) * (1 - s)))) * cm
            net = (c_ * (1 - s) - o_ * (1 + s)) * LOT - fees
            rec[f"net_rs{sfx}"], rec[f"net_pct{sfx}"] = net, net / (o_ * (1 + s) * LOT) * 100
        rec["maxup"] = (float(ce["HghPric"].iloc[0]) + float(pe["HghPric"].iloc[0])) / o_ * 100 - 100   # upper bound: highs need not coincide
        rows.append(rec)
    T = pd.DataFrame(rows)
    save(T, "DP_trades.csv")
    pd.set_option("display.width", 250, "display.max_columns", 30)
    md = ["# Daily-candle analogs, 2018-2026, Covid excluded (Amendment A7)", "", "NIFTY, real daily option prices. Net % per trade after costs (1 % slippage a side, dated charges); max up first (day-after high vs entry; XPD: sum of the two highs, an upper bound).", ""]
    for cell in ["PUT_all", "PUT_vix17", "PUT_gapvix", "CALL_all", "CALL_vix17", "XPD_all"]:
        x = T[T["cell"] == cell]
        md.append(f"## {cell}")
        for y, g in x.groupby("year"):
            s = summary(g.assign(day=g["day"]))
            mu = g["maxup"]
            md.append(f"- {y}: n {s['n']}, max up >= +100 % on {(mu >= 100).mean() * 100:.0f} % (mean {mu.mean():.0f} %, median {mu.median():.0f} %), win {s['win_pct']:.0f} %, mean {s['mean_pct']:+.1f} %, median {s['median_pct']:+.1f} %, total Rs {s['total_rs']:,.0f}")
        for lab, lo, hi in (("2018-2021 ex-Covid", 2018, 2021), ("2022-2026", 2022, 2026), ("overlap Oct 2024-Oct 2026", None, None)):
            g = x[(x["year"] >= lo) & (x["year"] <= hi)] if lo else x[x["day"] >= date(2024, 10, 1)]
            if len(g) > 3:
                s = summary(g)
                lo_, hi_ = boot_ci(g)
                md.append(f"- **{lab}:** n {s['n']}, win {s['win_pct']:.0f} %, mean {s['mean_pct']:+.1f} % (t {s['t']:.2f}, 95 % interval {lo_:+.1f} to {hi_:+.1f}), median {s['median_pct']:+.1f} %, at 2x costs {g['net_pct_2x'].mean():+.1f} %, profit factor {s['pf']:.2f}, total Rs {s['total_rs']:,.0f}")
        md.append("")
    open(os.path.join(ROOT, "results", "DP_summary.md"), "w", encoding="utf-8").write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
