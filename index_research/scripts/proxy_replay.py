"""Amendment A8: model-priced (proxy) replay of G1, G1-F, G1-C and XP on NIFTY spot minutes, Oct 2021 to Oct 2026.
Outputs: results/PX_trades.csv, results/PX_summary.md, results/PX_calibration.md. Run: python proxy_replay.py"""
import math
import os
import sys
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from lib import CH, REPO, ROOT, boot_ci, minutes, save, summary, tstat

sys.path.insert(0, REPO)
from scanner.s3_b2 import signal  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
R_RATE = 0.065
LOT = 65
BUCKETS = [(0, 1), (2, 3), (4, 6), (7, 999)]
SLIP = 0.005


def N(x):
    return 0.5 * np.vectorize(math.erfc)(-x / math.sqrt(2))


def bs(S, K, T, sig, cp):
    """vectorised Black-Scholes; S, T, sig arrays."""
    S, T, sig = np.asarray(S, float), np.asarray(T, float), np.asarray(sig, float)
    out = np.empty_like(S)
    live = T > 1e-9
    intr = np.maximum(0.0, (S - K) if cp == "CE" else (K - S))
    out[~live] = intr[~live]
    if live.any():
        s, t, v = S[live], T[live], sig[live]
        d1 = (np.log(s / K) + (R_RATE + 0.5 * v * v) * t) / (v * np.sqrt(t))
        d2 = d1 - v * np.sqrt(t)
        out[live] = s * N(d1) - K * np.exp(-R_RATE * t) * N(d2) if cp == "CE" else K * np.exp(-R_RATE * t) * N(-d2) - s * N(-d1)
    return out


def bucket(days):
    for i, (a, b) in enumerate(BUCKETS):
        if a <= days <= b:
            return i
    return len(BUCKETS) - 1


def calibrate():
    c = pd.read_csv(os.path.join(ROOT, "..", "index_context_research", "results", "context_dataset.csv"), parse_dates=["day", "expiry"])
    c = c[c["tset"].isin(["G1", "G1C"]) & c["atm_iv"].notna() & c["vix_signal"].notna() & c["expiry"].notna()].copy()
    c["dte_cal"] = (c["expiry"] - c["day"]).dt.days
    c["ratio"] = c["atm_iv"] / c["vix_signal"]
    d = c[c["day"] <= "2025-09-30"]
    k = {b: float(d[d["dte_cal"].map(bucket) == b]["ratio"].median()) for b in range(len(BUCKETS))}
    t = c[c["day"] > "2025-09-30"]
    err = np.mean([abs(r - k[bucket(x)]) / r for r, x in zip(t["ratio"], t["dte_cal"])])
    return k, len(d), len(t), err


def expiries():
    b = pd.read_parquet(os.path.join(ROOT, "data", "bhav_NIFTY.parquet"), columns=["TradDt", "XpryDt", "FinInstrmTp"])
    return sorted(set(b[b["FinInstrmTp"] == "IDO"]["XpryDt"]))


def sim_long(frames, d, nxt, ts_entry, cp, K, E, k, cm):
    """price path from the entry minute to the next session's 15:29 for one long option; returns dict."""
    g, gn = frames["spot"][d], frames["spot"][nxt]
    vd, vn = frames["vix"][d], frames["vix"][nxt]
    s = pd.concat([g[g["timestamp"] >= ts_entry][["timestamp", "close"]], gn[["timestamp", "close"]]], ignore_index=True)
    v = pd.concat([vd, vn]).set_index("timestamp")["close"].reindex(s["timestamp"]).ffill().bfill().to_numpy()
    exp_ts = pd.Timestamp(datetime.combine(E, datetime.min.time()), tz=s["timestamp"].iloc[0].tz) + pd.Timedelta(hours=15, minutes=30)
    T = np.maximum((exp_ts - s["timestamp"]).dt.total_seconds().to_numpy() / (365 * 24 * 3600), 0)
    px = bs(s["close"].to_numpy(), K, T, k * v / 100, cp)
    slip = SLIP * cm
    paid = px[0] * (1 + slip)
    bid = px * (1 - slip)
    stop = np.where(bid[1:] <= 0.5 * paid)[0]
    if len(stop):
        j = stop[0] + 1
        exit_px, reason = bid[j], "stop"
    else:
        exit_px, reason = bid[-1], "close"
    maxup = (px[1:].max() / paid - 1) * 100 if len(px) > 1 else np.nan
    return paid, exit_px, reason, maxup


def main():
    k, n_cal, n_test, err = calibrate()
    spot = minutes("NIFTY50")
    # VIX from the loader that repairs the x100 / /100 rows of 2021-10 to 2023-08 (the raw cached minutes contain values such as 0.24 and 3079)
    from lib import L
    vx = L.vix_1m(date(2021, 10, 1), date(2026, 10, 31))
    vx["d"] = vx["timestamp"].dt.date
    vixm = {d: g[["timestamp", "close"]] for d, g in vx.groupby("d")}
    frames = {"spot": spot, "vix": {d: g[["timestamp", "close"]] for d, g in vixm.items()}}
    ses = sorted(spot)
    exps = expiries()
    dclose = {d: float(spot[d]["close"].iloc[-1]) for d in ses}
    rows = []
    for i in range(1, len(ses) - 1):
        d, nxt = ses[i], ses[i + 1]
        if d not in frames["vix"] or nxt not in frames["vix"] or d < date(2021, 10, 21) or d > date(2026, 10, 27):
            continue
        g = spot[d]
        E = next((e for e in exps if e > d), None)
        if E is None:
            continue
        sg = signal(g, 15, None)
        if sg is not None:
            side, ts, hi, lo = sg
            cp = "PE" if side == "PE" else "CE"
            ent = ts + pd.Timedelta(minutes=1)
            if ent in set(g["timestamp"]):
                S = float(g.loc[g["timestamp"] == ent, "close"].iloc[0])
                K = round(S / 50) * 50
                kk = k[bucket((E - d).days)]
                gap = (float(g["open"].iloc[0]) / dclose[ses[i - 1]] - 1) * 100
                width = (hi / lo - 1) * 100
                vsig = float(frames["vix"][d].loc[frames["vix"][d]["timestamp"] <= ts, "close"].iloc[-1])
                out = {}
                for cm, sfx in ((1.0, ""), (2.0, "_2x")):
                    paid, ex, reason, mu = sim_long(frames, d, nxt, ent, cp, K, E, kk, cm)
                    fees = (CH.leg(cp, "BUY", LOT, paid, on=d)["total"] + CH.leg(cp, "SELL", LOT, ex, on=nxt)["total"]) * cm
                    net = (ex - paid) * LOT - fees
                    out[f"net_rs{sfx}"], out[f"net_pct{sfx}"] = net, net / (paid * LOT) * 100
                out.update({"reason": reason, "maxup": mu, "paid": paid})
                base = {"day": d, "year": d.year, "expiry": E, "strike": K, **out}
                rows.append({**base, "cell": "G1" if cp == "PE" else "G1C"})
                if cp == "PE" and gap < 0.3 and not (0.5 <= width < 0.8) and vsig < 17:
                    rows.append({**base, "cell": "G1F"})
        # XP-P: expiry days
        if d in set(exps):
            e9 = pd.Timestamp(datetime.combine(d, datetime.min.time()), tz=g["timestamp"].iloc[0].tz) + pd.Timedelta(hours=9, minutes=16)
            gg = g[g["timestamp"] >= e9]
            if len(gg) > 10 and gg["timestamp"].iloc[0] == e9:
                S = float(gg["close"].iloc[0])
                K = round(S / 50) * 50
                v = frames["vix"][d].set_index("timestamp")["close"].reindex(gg["timestamp"]).ffill().bfill().to_numpy()
                exp_ts = e9.normalize() + pd.Timedelta(hours=15, minutes=30)
                T = np.maximum((exp_ts - gg["timestamp"]).dt.total_seconds().to_numpy() / (365 * 24 * 3600), 0)
                kk = k[0]
                pair = bs(gg["close"].to_numpy(), K, T, kk * v / 100, "CE") + bs(gg["close"].to_numpy(), K, T, kk * v / 100, "PE")
                if pair[0] >= 10:
                    out = {}
                    for cm, sfx in ((1.0, ""), (2.0, "_2x")):
                        s = SLIP * cm
                        paid = pair[0] * (1 + s)
                        bid = pair * (1 - s)
                        hit = np.where(bid[1:] >= 1.2 * paid)[0]
                        t15 = np.where(gg["timestamp"].dt.hour.to_numpy() * 100 + gg["timestamp"].dt.minute.to_numpy() >= 1515)[0]
                        j = (hit[0] + 1) if len(hit) and (len(t15) == 0 or hit[0] + 1 <= t15[0]) else (t15[0] if len(t15) else len(bid) - 1)
                        ex = bid[j]
                        half_p, half_x = paid / 2, ex / 2
                        fees = sum(CH.leg(t, sd, LOT, px, on=d)["total"] for t, sd, px in (("CE", "BUY", half_p), ("PE", "BUY", half_p), ("CE", "SELL", half_x), ("PE", "SELL", half_x))) * cm
                        net = (ex - paid) * LOT - fees
                        out[f"net_rs{sfx}"], out[f"net_pct{sfx}"] = net, net / (paid * LOT) * 100
                    out.update({"reason": "target" if len(hit) and j == hit[0] + 1 else "time", "maxup": (pair[1:].max() / (pair[0] * (1 + SLIP)) - 1) * 100, "paid": pair[0] * (1 + SLIP)})
                    rows.append({"day": d, "year": d.year, "expiry": d, "strike": K, "cell": "XPP", **out})
    T = pd.DataFrame(rows)
    save(T, "PX_trades.csv")
    # calibration report
    cal = ["# Proxy replay: calibration and checks (Amendment A8)", "",
           f"k (model IV / VIX) from {n_cal} real G1 / G1-C trades to 2025-09-30, by calendar days to expiry: " + ", ".join(f"{a}-{b if b < 999 else '+'}: {k[i]:.3f}" for i, (a, b) in enumerate(BUCKETS)) + f". Mean absolute error of the ratio on the {n_test} later trades: {err * 100:.0f} %.", ""]
    # entry price check vs the real G1 replay
    rg = pd.read_csv(os.path.join(REPO, "g1_research", "results", "g1_live_replay_trades.csv"), parse_dates=["day"])
    rg["day"] = rg["day"].dt.date
    m = T[T["cell"] == "G1"].merge(rg[["day", "paid", "net_pct", "net_rs", "reason"]], on="day", suffixes=("_px", "_real"))
    if len(m):
        ratio = m["paid_px"] / m["paid_real"]
        cal.append(f"**Entry price, model vs real (G1, {len(m)} matched days Oct 2024-Oct 2026):** median model/real {ratio.median():.2f}, middle 50 % of days {ratio.quantile(.25):.2f}-{ratio.quantile(.75):.2f}.")
        cal.append(f"**Per-trade net %, proxy vs real:** correlation {m['net_pct_px'].corr(m['net_pct_real']):.2f}; proxy mean {m['net_pct_px'].mean():+.1f} % vs real {m['net_pct_real'].mean():+.1f} %; win {(m['net_pct_px'] > 0).mean() * 100:.0f} % vs {(m['net_pct_real'] > 0).mean() * 100:.0f} %; stops {(m['reason_px'] == 'stop').mean() * 100:.0f} % vs {(m['reason_real'] == 'stop').mean() * 100:.0f} %.")
    open(os.path.join(ROOT, "results", "PX_calibration.md"), "w", encoding="utf-8").write("\n".join(cal))
    print("\n".join(cal))
    md = ["# Model-priced (proxy) replay, NIFTY, Oct 2021 to Oct 2026 (Amendment A8)", "", "Option prices are a Black-Scholes model scaled to India VIX; NOT real prices. Net % after 0.5 % slippage a side and dated charges; max up first.", ""]
    for cell in ["G1", "G1F", "G1C", "XPP"]:
        x = T[T["cell"] == cell]
        md.append(f"## {cell}")
        for y, g in x.groupby("year"):
            s = summary(g)
            mu = g["maxup"]
            md.append(f"- {y}{' (partial)' if y in (2021, 2026) else ''}: n {s['n']}, max up >= +100 % on {(mu >= 100).mean() * 100:.0f} % (mean {mu.mean():.0f} %, median {mu.median():.0f} %), win {s['win_pct']:.0f} %, mean {s['mean_pct']:+.1f} %, median {s['median_pct']:+.1f} %, total Rs {s['total_rs']:,.0f}")
        for lab, a, b in (("Oct 2021-Sep 2024 (proxy years)", date(2021, 10, 1), date(2024, 9, 30)), ("Oct 2024-Oct 2026 (real years, same model)", date(2024, 10, 1), date(2026, 10, 31))):
            g = x[(x["day"] >= a) & (x["day"] <= b)]
            if len(g) > 3:
                s = summary(g)
                lo_, hi_ = boot_ci(g)
                md.append(f"- **{lab}:** n {s['n']}, win {s['win_pct']:.0f} %, mean {s['mean_pct']:+.1f} % (t {s['t']:.2f}, 95 % interval {lo_:+.1f} to {hi_:+.1f}), median {s['median_pct']:+.1f} %, at 2x costs {g['net_pct_2x'].mean():+.1f} %, profit factor {s['pf']:.2f}, total Rs {s['total_rs']:,.0f}")
        md.append("")
    open(os.path.join(ROOT, "results", "PX_summary.md"), "w", encoding="utf-8").write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
