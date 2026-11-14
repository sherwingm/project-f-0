"""Daily-data studies of index_research/PROGRAM.md (bhavcopy 2018-01 -> 2026-10, NIFTY and BANKNIFTY):
  R02b  overnight drift on the REAL near-month future: buy at the close, sell at the next open (cells all / previous day up). Follow-up of a seen R02 result.
  R09   weekly / nearest ATM short straddle entered at the close 4 sessions before expiry, held to expiry (intrinsic at the expiry-day index close);
        filters none / VIX 1-year percentile > 70 / < 30 / VoV low / VoV high; plus the long-straddle mirror of every cell.
Periods: D = 2018-2021, V = 2022-01 to 2024-09, L = 2024-10 -> (L opened only for V passers).
Fills: close / open of the day with 1 % slippage a side on options (2 % at 2x), 0.02 % a side on futures (0.04 % at 2x); charges server/charges.py dated.
Lots fixed at NIFTY 65, BANKNIFTY 30 (results in % first). Usage: python daily_studies.py R02b | R09
"""
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

from lib import CH, L, ROOT, boot_ci, bh, mc_drawdown, save, summary, validation_pass

sys.stdout.reconfigure(encoding="utf-8")
STORE = os.environ["INDEX_STORE"]
LOTS = {"NIFTY": 65, "BANKNIFTY": 30}
IDX = {"NIFTY": "NIFTY50", "BANKNIFTY": "NIFTYBANK"}


def per(d):
    return "D" if d < date(2022, 1, 1) else ("V" if d < date(2024, 10, 1) else "L")


def bhav(und):
    cache = os.path.join(ROOT, "data", f"bhav_{und}.parquet")
    if os.path.exists(cache):
        return pd.read_parquet(cache)
    folder = os.path.join(STORE, "options_daily", und)
    df = pd.concat([pd.read_parquet(os.path.join(folder, f)) for f in sorted(os.listdir(folder))], ignore_index=True)
    for c in ("TradDt", "XpryDt"):
        df[c] = pd.to_datetime(df[c]).dt.date
    df.to_parquet(cache)
    return df


def index_close():
    c = pd.read_parquet(os.path.join(STORE, "index_close_daily.parquet"))
    c["date"] = pd.to_datetime(c["date"]).dt.date
    out = {k: g.set_index("date")["close"] for k, g in c.groupby("index")}
    for k in ("NIFTY50", "NIFTYBANK", "INDIAVIX"):        # extend after 2025-09-30 with the minute closes
        m = L.spot_1m(date(2025, 9, 1), date(2026, 10, 31), k)
        m["d"] = m["timestamp"].dt.date
        last = m.groupby("d")["close"].last()
        s = out[k]
        out[k] = pd.concat([s, last[last.index > s.index.max()]]).sort_index()
    return out


def fut_cost(px, lot, d, cm):
    return (CH.leg("FUT", "BUY", lot, px, on=d)["total"] + CH.leg("FUT", "SELL", lot, px, on=d)["total"]) * cm


def r02b():
    out = []
    for und in ("NIFTY", "BANKNIFTY"):
        b = bhav(und)
        f = b[b["FinInstrmTp"] == "IDF"].copy()
        f = f[f["XpryDt"] > f["TradDt"]]
        near = f.sort_values("XpryDt").groupby("TradDt").first()
        ds = list(near.index)
        lot = LOTS[und]
        for i in range(1, len(ds) - 1):
            d, nx, pv = ds[i], ds[i + 1], ds[i - 1]
            row = near.loc[d]
            nrow = f[(f["TradDt"] == nx) & (f["XpryDt"] == row["XpryDt"])]
            if nrow.empty or row["ClsPric"] <= 0:
                continue
            c, o = float(row["ClsPric"]), float(nrow["OpnPric"].iloc[0])
            if o <= 0:
                continue
            prev_up = row["ClsPric"] > float(near.loc[pv, "ClsPric"]) if near.loc[pv, "XpryDt"] == row["XpryDt"] else (row["ClsPric"] > near.loc[pv, "ClsPric"])
            for cm, sfx in ((1.0, ""), (2.0, "_2x")):
                s = 0.0002 * cm
                gross = (o * (1 - s) - c * (1 + s)) * lot
                net = gross - fut_cost(c, lot, d, cm)
                if sfx == "":
                    base = {"index": und, "day": d, "net_rs": net, "net_pct": net / (c * lot) * 100}
                else:
                    base["net_rs_2x"], base["net_pct_2x"] = net, net / (c * lot) * 100
            for cell, ok in (("all", True), ("prevup", prev_up)):
                if ok:
                    out.append({**base, "cell": f"{und}|overnight_{cell}"})
    return out


def r09():
    ic = index_close()
    vix = ic["INDIAVIX"]
    vpct = vix.rolling(250, min_periods=200).apply(lambda x: (x[:-1] < x[-1]).mean() * 100, raw=True)
    vov = vix.rolling(5).std()
    vov_med = vov.rolling(250, min_periods=200).median()
    out = []
    for und in ("NIFTY", "BANKNIFTY"):
        b = bhav(und)
        o = b[(b["FinInstrmTp"] == "IDO")].copy()
        spot = ic[IDX[und]]
        ses = sorted(set(o["TradDt"]))
        pos = {d: i for i, d in enumerate(ses)}
        lot = LOTS[und]
        for E in sorted(set(o["XpryDt"])):
            if E not in pos or E not in spot.index or pos[E] < 4:
                continue
            d0 = ses[pos[E] - 4]
            if d0 not in spot.index or d0 not in vix.index:
                continue
            S0, SE = float(spot[d0]), float(spot[E])
            ch = o[(o["TradDt"] == d0) & (o["XpryDt"] == E)]
            if ch.empty:
                continue
            strikes = np.array(sorted(ch["StrkPric"].unique()))
            K = strikes[np.argmin(abs(strikes - S0))]
            ce = ch[(ch["StrkPric"] == K) & (ch["OptnTp"] == "CE") & (ch["TtlTradgVol"] > 0)]
            pe = ch[(ch["StrkPric"] == K) & (ch["OptnTp"] == "PE") & (ch["TtlTradgVol"] > 0)]
            if ce.empty or pe.empty:
                continue
            c, p = float(ce["ClsPric"].iloc[0]), float(pe["ClsPric"].iloc[0])
            intrinsic = max(0.0, SE - K) + max(0.0, K - SE)
            prem = c + p
            rec = {"day": d0, "expiry": E, "index": und}
            for cm, sfx in ((1.0, ""), (2.0, "_2x")):
                s = 0.01 * cm
                fees_s = (CH.leg("CE", "SELL", lot, c * (1 - s), on=d0)["total"] + CH.leg("PE", "SELL", lot, p * (1 - s), on=d0)["total"]) * cm
                fees_b = (CH.leg("CE", "BUY", lot, c * (1 + s), on=d0)["total"] + CH.leg("PE", "BUY", lot, p * (1 + s), on=d0)["total"]) * cm
                short = (prem * (1 - s) - intrinsic) * lot - fees_s
                long_ = (intrinsic - prem * (1 + s)) * lot - fees_b
                rec[f"short_rs{sfx}"], rec[f"short_pct{sfx}"] = short, short / (prem * lot) * 100
                rec[f"long_rs{sfx}"], rec[f"long_pct{sfx}"] = long_, long_ / (prem * lot) * 100
            pv = d0
            flags = {"all": True, "vixpct_gt70": vpct.get(pv, np.nan) > 70, "vixpct_lt30": vpct.get(pv, np.nan) < 30,
                     "vov_low": vov.get(pv, np.nan) < vov_med.get(pv, np.nan), "vov_high": vov.get(pv, np.nan) >= vov_med.get(pv, np.nan)}
            for f, ok in flags.items():
                if ok:
                    for side in ("short", "long"):
                        out.append({**rec, "cell": f"{und}|{side}_{f}", "net_rs": rec[f"{side}_rs"], "net_pct": rec[f"{side}_pct"],
                                    "net_rs_2x": rec[f"{side}_rs_2x"], "net_pct_2x": rec[f"{side}_pct_2x"]})
    return out


def r19():
    """Calendar straddle (Amendment A2): sell the near weekly ATM straddle and buy the next weekly's ATM straddle at the close 4 sessions before
    the near expiry; at the near expiry's close the near legs settle at intrinsic (index close) and the far legs are sold at their close.
    % = net / (far straddle premium x lot). Cells: all, VIX 1-year percentile < 30."""
    ic = index_close()
    vix = ic["INDIAVIX"]
    vpct = vix.rolling(250, min_periods=200).apply(lambda x: (x[:-1] < x[-1]).mean() * 100, raw=True)
    b = bhav("NIFTY")
    o = b[b["FinInstrmTp"] == "IDO"]
    spot = ic["NIFTY50"]
    ses = sorted(set(o["TradDt"]))
    pos = {d: i for i, d in enumerate(ses)}
    exps = sorted(set(o["XpryDt"]))
    lot = LOTS["NIFTY"]
    out = []
    for k, E in enumerate(exps[:-1]):
        E2 = exps[k + 1]
        if E not in pos or E not in spot.index or pos[E] < 4 or (E2 - E).days > 8:
            continue
        d0 = ses[pos[E] - 4]
        if d0 not in spot.index:
            continue
        S0, SE = float(spot[d0]), float(spot[E])
        c0 = o[(o["TradDt"] == d0) & (o["TtlTradgVol"] > 0)]
        n_ = c0[c0["XpryDt"] == E]
        f_ = c0[c0["XpryDt"] == E2]
        if n_.empty or f_.empty:
            continue
        ks = np.array(sorted(set(n_["StrkPric"]) & set(f_["StrkPric"])))
        if not len(ks):
            continue
        K = ks[np.argmin(abs(ks - S0))]
        def px(fr, t):
            r = fr[(fr["StrkPric"] == K) & (fr["OptnTp"] == t)]
            return float(r["ClsPric"].iloc[0]) if len(r) else None
        nc, np_, fc, fp = px(n_, "CE"), px(n_, "PE"), px(f_, "CE"), px(f_, "PE")
        fE = o[(o["TradDt"] == E) & (o["XpryDt"] == E2) & (o["StrkPric"] == K) & (o["TtlTradgVol"] > 0)]
        if None in (nc, np_, fc, fp) or len(fE) < 2:
            continue
        fce, fpe = float(fE[fE["OptnTp"] == "CE"]["ClsPric"].iloc[0]), float(fE[fE["OptnTp"] == "PE"]["ClsPric"].iloc[0])
        intrinsic = max(0.0, SE - K) + max(0.0, K - SE)
        rec = {"day": d0, "expiry": E}
        for cm, sfx in ((1.0, ""), (2.0, "_2x")):
            s = 0.01 * cm
            near = ((nc + np_) * (1 - s) - intrinsic) * lot
            far = ((fce + fpe) * (1 - s) - (fc + fp) * (1 + s)) * lot
            fees = sum(CH.leg(t, sd, lot, p, on=d) ["total"] for t, sd, p, d in
                       (("CE", "SELL", nc, d0), ("PE", "SELL", np_, d0), ("CE", "BUY", fc, d0), ("PE", "BUY", fp, d0),
                        ("CE", "SELL", fce, E), ("PE", "SELL", fpe, E))) * cm
            net = near + far - fees
            rec[f"net_rs{sfx}"], rec[f"net_pct{sfx}"] = net, net / ((fc + fp) * lot) * 100
        out.append({**rec, "cell": "NIFTY|calendar_all"})
        if vpct.get(d0, np.nan) < 30:
            out.append({**rec, "cell": "NIFTY|calendar_lowvix"})
    return out


def evaluate(study, trades):
    T = pd.DataFrame(trades)
    T["period"] = T["day"].map(per)
    save(T, f"{study}_trades.csv")
    C = bh(pd.DataFrame([{"key": k, **summary(x)} for k, x in T[T["period"] == "D"].groupby("cell")]))
    save(C, f"{study}_discovery.csv")
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 200)
    cols = ["key", "n", "win_pct", "mean_pct", "median_pct", "total_rs", "t", "pf", "mean_2x", "h1_mean", "h2_mean", "max_dd_rs", "discovery_pass"]
    print(f"=== {study} DISCOVERY (2018-2021) ===")
    print(C[cols].round(3).to_string(index=False))
    vrows = []
    for key in C.loc[C["discovery_pass"], "key"]:
        x = T[(T["cell"] == key) & (T["period"] == "V")]
        s = {"key": key, **summary(x)}
        s["validation_pass"] = validation_pass(s)
        if s["validation_pass"]:
            lo, hi = boot_ci(x)
            s.update({"boot_lo": lo, "boot_hi": hi, **mc_drawdown(x["net_rs"])})
            xl = T[(T["cell"] == key) & (T["period"] == "L")]
            s.update({f"L_{k}": v for k, v in summary(xl).items()})
        vrows.append(s)
    if vrows:
        V = pd.DataFrame(vrows)
        save(V, f"{study}_validation.csv")
        print(f"=== {study} VALIDATION (2022-01 to 2024-09) [+ L for passers] ===")
        print(V.round(3).to_string(index=False))
    print("discovery passes:", int(C["discovery_pass"].sum()))


if __name__ == "__main__":
    for st in sys.argv[1:]:
        evaluate(st, {"R02b": r02b, "R09": r09, "R19": r19}[st]())
