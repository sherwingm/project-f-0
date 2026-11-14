"""R01-R05 of index_research/PROGRAM.md on the index 1-minute data as a futures proxy (NIFTY50, NIFTYBANK, SENSEX).
Cells are exactly as in PROGRAM.md. Discovery D (to 2023-12-31) for all cells; validation V (2024-01 to 2025-09) only for cells that pass
discovery (BH 10 % across the study's cells); the late period L only for validation passers (opened inside this script, once).
Usage: python index_research/scripts/spot_studies.py R01 [R02 ...]
"""
import sys

import numpy as np
import pandas as pd

from lib import (LOT, SLIP_STRESS, boot_ci, bh, daily, fut_trade, mc_drawdown, minutes, period, save, summary, validation_pass,
                 vix_daily)

sys.stdout.reconfigure(encoding="utf-8")
INDICES = ("NIFTY50", "NIFTYBANK", "SENSEX")


def bar(g, hm):
    r = g[g["hm"] == hm]
    return None if r.empty else r.iloc[0]


def rec(cell, index, day, direction, entry, exit_):
    n1, p1 = fut_trade(index, day, direction, entry, exit_)
    n2, p2 = fut_trade(index, day, direction, entry, exit_, cost_mult=2.0)
    n3, p3 = fut_trade(index, day, direction, entry, exit_, slip_pts=SLIP_STRESS[index])
    return {"cell": cell, "index": index, "day": day, "dir": direction, "entry": entry, "exit": exit_, "net_rs": n1, "net_pct": p1,
            "net_rs_2x": n2, "net_pct_2x": p2, "net_pct_slip3": p3}


# ---------------- R01 gap-and-go (+ gap fade) ----------------
def r01(index, days, dd):
    sma = dd["close"].rolling(20).mean()
    ses = list(dd.index)
    out = []
    for i in range(21, len(ses)):
        d, prev = ses[i], ses[i - 1]
        g = days[d]
        gap = (dd.loc[d, "open"] / dd.loc[prev, "close"] - 1) * 100
        ext = (dd.loc[prev, "close"] / sma[prev] - 1) * 100
        b916, b1515 = bar(g, 916), bar(g, 1515)
        if b916 is None or b1515 is None:
            continue
        first5 = g[(g["hm"] >= 915) & (g["hm"] <= 919)]
        after = g[(g["hm"] >= 920) & (g["hm"] < 1515)]
        for thr in (0.5, 0.75, 1.0):
            if abs(gap) < thr:
                continue
            dirn = 1 if gap > 0 else -1
            for stop in (False, True):
                ex = float(b1515["open"])
                if stop:
                    lvl = float(first5["low"].min()) if dirn > 0 else float(first5["high"].max())
                    hit = after[(after["low"] <= lvl)] if dirn > 0 else after[(after["high"] >= lvl)]
                    if not hit.empty:
                        h = hit.iloc[0]
                        ex = min(lvl, float(h["open"])) if dirn > 0 else max(lvl, float(h["open"]))
                for skip in (False, True):
                    if skip and ext > 2.5:
                        continue
                    out.append(rec(f"gap{thr}_stop{int(stop)}_skip{int(skip)}", index, d, dirn, float(b916["open"]), ex))
            out.append(rec(f"fade{thr}", index, d, -dirn, float(b916["open"]), float(b1515["open"])))
    return out


# ---------------- R02 overnight and intraday drift ----------------
def r02(index, days, dd, vx):
    ses = list(dd.index)
    vprev = vx["close"].reindex(ses).shift(1)
    dmask = [s for s in ses if period(s) == "D"]
    lo, hi = np.nanpercentile(vprev.loc[dmask], [33.33, 66.67])
    out = []
    for i in range(1, len(ses) - 1):
        d, prev, nxt = ses[i], ses[i - 1], ses[i + 1]
        g, gn = days[d], days[nxt]
        b1525, b916, bn916 = bar(g, 1525), bar(g, 916), bar(gn, 916)
        up_prev = dd.loc[d, "close"] > dd.loc[prev, "close"]
        v = vprev.loc[d]
        filt = {"all": True, "vixlow": v <= lo, "vixhigh": v > hi, "prevup": dd.loc[prev, "close"] > dd.loc[ses[i - 2], "close"] if i >= 2 else False}
        for f, ok in filt.items():
            if not ok:
                continue
            if b916 is not None and b1525 is not None:
                out.append(rec(f"intraday_{f}", index, d, 1, float(b916["open"]), float(b1525["open"])))
        # overnight: decided at 15:25 of d with d's info (previous-day sign = d vs prev)
        v2 = vx["close"].reindex(ses).loc[d] if d in vx.index else np.nan
        filt2 = {"all": True, "vixlow": v2 <= lo, "vixhigh": v2 > hi, "prevup": up_prev}
        for f, ok in filt2.items():
            if ok and b1525 is not None and bn916 is not None:
                out.append(rec(f"overnight_{f}", index, d, 1, float(b1525["open"]), float(bn916["open"])))
    return out


# ---------------- R03 initial-balance breakout and liquidity sweep ----------------
def r03(index, days, dd):
    ses = list(dd.index)
    out = []
    for i in range(1, len(ses)):
        d, prev = ses[i], ses[i - 1]
        g = days[d]
        b1515 = bar(g, 1515)
        if b1515 is None:
            continue
        ex_t = float(b1515["open"])
        ib = g[(g["hm"] >= 915) & (g["hm"] <= 1014)]
        hi, lo = float(ib["high"].max()), float(ib["low"].min())
        mid = (hi + lo) / 2
        rest = g[(g["hm"] >= 1015) & (g["hm"] <= 1400)].reset_index(drop=True)
        for j in range(len(rest) - 1):
            c = float(rest.loc[j, "close"])
            if c > hi or c < lo:
                dirn = 1 if c > hi else -1
                ent = float(rest.loc[j + 1, "open"])
                after = g[(g["timestamp"] > rest.loc[j + 1, "timestamp"]) & (g["hm"] < 1515)]
                for nm, lvl in (("other", lo if dirn > 0 else hi), ("mid", mid)):
                    ex = ex_t
                    hit = after[after["low"] <= lvl] if dirn > 0 else after[after["high"] >= lvl]
                    if not hit.empty:
                        h = hit.iloc[0]
                        ex = min(lvl, float(h["open"])) if dirn > 0 else max(lvl, float(h["open"]))
                    out.append(rec(f"ib_stop_{nm}", index, d, dirn, ent, ex))
                break
        # liquidity sweep of the previous day's high / low
        H, Lw = dd.loc[prev, "high"], dd.loc[prev, "low"]
        w = g[(g["hm"] >= 920) & (g["hm"] <= 1400)].reset_index(drop=True)
        done = False
        for j in range(len(w)):
            if done:
                break
            for side in ("high", "low"):
                if side == "high" and float(w.loc[j, "high"]) > H:
                    win = w.iloc[j:j + 5]
                    if float(win["high"].max()) > H * 1.001:
                        done = True
                        break
                    back = win[win["close"] < H]
                    if not back.empty:
                        k = back.index[0]
                        if k + 1 < len(w):
                            ent, ext_ = float(w.loc[k + 1, "open"]), float(w.loc[j:k, "high"].max())
                            after = g[(g["timestamp"] > w.loc[k + 1, "timestamp"]) & (g["hm"] < 1515)]
                            hit = after[after["high"] >= ext_]
                            ex = ex_t if hit.empty else max(ext_, float(hit.iloc[0]["open"]))
                            for c in ("sweep_both", "sweep_high"):
                                out.append(rec(c, index, d, -1, ent, ex))
                    done = True
                    break
                if side == "low" and float(w.loc[j, "low"]) < Lw:
                    win = w.iloc[j:j + 5]
                    if float(win["low"].min()) < Lw * 0.999:
                        done = True
                        break
                    back = win[win["close"] > Lw]
                    if not back.empty:
                        k = back.index[0]
                        if k + 1 < len(w):
                            ent, ext_ = float(w.loc[k + 1, "open"]), float(w.loc[j:k, "low"].min())
                            after = g[(g["timestamp"] > w.loc[k + 1, "timestamp"]) & (g["hm"] < 1515)]
                            hit = after[after["low"] <= ext_]
                            ex = ex_t if hit.empty else min(ext_, float(hit.iloc[0]["open"]))
                            for c in ("sweep_both", "sweep_low"):
                                out.append(rec(c, index, d, 1, ent, ex))
                    done = True
                    break
    return out


# ---------------- R04 Supertrend pullback ----------------
def resample(all1m, rule_minutes):
    x = all1m.copy()
    x["k"] = ((x["hm"] // 100 - 9) * 60 + x["hm"] % 100 - 15) // rule_minutes
    agg = x.groupby(["d", "k"]).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
                                    end=("timestamp", "last")).reset_index()
    return agg


def supertrend(b, n=10, m=3.0):
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    tr = np.maximum(h - l, np.maximum(abs(h - np.roll(c, 1)), abs(l - np.roll(c, 1))))
    tr[0] = h[0] - l[0]
    atr = pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()
    hl2 = (h + l) / 2
    ub, lb = hl2 + m * atr, hl2 - m * atr
    fu, fl, d = ub.copy(), lb.copy(), np.ones(len(c))
    for i in range(1, len(c)):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        d[i] = 1 if c[i] > fu[i - 1] else (-1 if c[i] < fl[i - 1] else d[i - 1])
    return d


def adx(b, n=14):
    h, l, c = b["high"], b["low"], b["close"]
    up, dn = h.diff(), -l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(pdm).ewm(alpha=1 / n, adjust=False).mean().to_numpy() / atr.to_numpy()
    ndi = 100 * pd.Series(ndm).ewm(alpha=1 / n, adjust=False).mean().to_numpy() / atr.to_numpy()
    dx = 100 * np.abs(pdi - ndi) / np.where(pdi + ndi == 0, np.nan, pdi + ndi)
    return pd.Series(dx).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def r04(index, days, dd):
    all1m = pd.concat([days[d] for d in sorted(days)], ignore_index=True)
    h1, m5 = resample(all1m, 60), resample(all1m, 5)
    h1["dir"], h1["adx"] = supertrend(h1), adx(h1)
    m5["dir"] = supertrend(m5)
    h1 = h1.sort_values("end")
    out = []
    for d, g5 in m5.groupby("d"):
        g = days[d]
        b1515 = bar(g, 1515)
        if b1515 is None:
            continue
        g5 = g5.reset_index(drop=True)
        prev_dirs = m5.loc[m5["end"] < g5["end"].iloc[0], "dir"]
        last = prev_dirs.iloc[-1] if len(prev_dirs) else 0
        against_seen = False
        pos = None
        for j in range(len(g5)):
            t_end = g5.loc[j, "end"]
            hm = t_end.hour * 100 + t_end.minute
            hh = h1[h1["end"] <= t_end]
            if hh.empty:
                continue
            hdir, hadx = hh["dir"].iloc[-1], hh["adx"].iloc[-1]
            d5 = g5.loc[j, "dir"]
            nxt = g[g["timestamp"] > t_end]
            if pos is not None:
                if d5 != pos["dir"] or nxt.empty or hm >= 1514:
                    ex = float(nxt.iloc[0]["open"]) if not nxt.empty and hm < 1514 else float(b1515["open"])
                    for c in pos["cells"]:
                        out.append(rec(c, index, d, pos["dir"], pos["ent"], ex))
                    pos = None
                last = d5
                continue
            if d5 != hdir:
                against_seen = True
            elif against_seen and last != hdir and d5 == hdir and 930 <= hm <= 1430 and not nxt.empty:
                cells = ["st_all"] + (["st_adx25"] if hadx > 25 else [])
                pos = {"dir": int(hdir), "ent": float(nxt.iloc[0]["open"]), "cells": cells}
                against_seen = False
            last = d5
        if pos is not None:
            for c in pos["cells"]:
                out.append(rec(c, index, d, pos["dir"], pos["ent"], float(b1515["open"])))
    return out


# ---------------- R05 TWAP-deviation mean reversion ----------------
def rsi(x, n=14):
    dlt = x.diff()
    up, dn = dlt.clip(lower=0), -dlt.clip(upper=0)
    rs = up.ewm(alpha=1 / n, adjust=False).mean() / dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + rs)


def r05(index, days, dd):
    all1m = pd.concat([days[d] for d in sorted(days)], ignore_index=True)
    m5 = resample(all1m, 5)
    m5["rsi"] = rsi(m5["close"]).to_numpy()
    out = []
    for d, g in days.items():
        b1515 = bar(g, 1515)
        if b1515 is None:
            continue
        c = g["close"].astype(float)
        twap = c.expanding().mean()
        sd = c.expanding().std()
        r5 = m5[m5["d"] == d]
        for k in (3.0, 2.5):
            for use_rsi in (False, True):
                cell = f"mr_k{k}_rsi{int(use_rsi)}"
                for j in range(30, len(g) - 1):
                    if g.loc[j, "hm"] >= 1430:
                        break
                    dev = c[j] - twap[j]
                    if sd[j] == 0 or abs(dev) <= k * sd[j]:
                        continue
                    if use_rsi:
                        rr = r5[r5["end"] <= g.loc[j, "timestamp"]]["rsi"]
                        if rr.empty or not ((dev > 0 and rr.iloc[-1] > 85) or (dev < 0 and rr.iloc[-1] < 15)):
                            continue
                    dirn = -1 if dev > 0 else 1
                    ent = float(g.loc[j + 1, "open"])
                    stop = ent - dirn * abs(dev)
                    ex = float(b1515["open"])
                    for q in range(j + 1, len(g)):
                        if g.loc[q, "hm"] >= 1515:
                            break
                        lo_, hi_ = float(g.loc[q, "low"]), float(g.loc[q, "high"])
                        if (dirn > 0 and lo_ <= stop) or (dirn < 0 and hi_ >= stop):
                            ex = stop
                            break
                        if (dirn > 0 and hi_ >= twap[q]) or (dirn < 0 and lo_ <= twap[q]):
                            ex = float(twap[q])
                            break
                    out.append(rec(cell, index, d, dirn, ent, ex))
                    break
    return out


def evaluate(study, trades):
    T = pd.DataFrame(trades)
    T["period"] = T["day"].map(period)
    T["key"] = T["index"] + "|" + T["cell"]
    save(T, f"{study}_trades.csv")
    rows = []
    for key, x in T[T["period"] == "D"].groupby("key"):
        rows.append({"key": key, **summary(x)})
    C = bh(pd.DataFrame(rows))
    vrows = []
    for key in C.loc[C["discovery_pass"], "key"]:
        x = T[(T["key"] == key) & (T["period"] == "V")]
        s = summary(x)
        s["validation_pass"] = validation_pass(s)
        s["key"] = key
        if s["validation_pass"]:
            lo, hi = boot_ci(x)
            s.update({"boot_lo": lo, "boot_hi": hi, **mc_drawdown(x["net_rs"])})
            xl = T[(T["key"] == key) & (T["period"] == "L")]
            sl = summary(xl)
            s.update({f"L_{k}": v for k, v in sl.items()})
        vrows.append(s)
    save(C, f"{study}_discovery.csv")
    V = pd.DataFrame(vrows)
    if len(V):
        save(V, f"{study}_validation.csv")
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 200)
    cols = ["key", "n", "win_pct", "mean_pct", "median_pct", "total_rs", "t", "pf", "mean_2x", "h1_mean", "h2_mean", "bh_pass", "discovery_pass"]
    print(f"=== {study} DISCOVERY (to 2023-12-31) ===")
    print(C[cols].round(3).to_string(index=False))
    print(f"discovery passes: {int(C['discovery_pass'].sum())}")
    if len(V):
        print(f"=== {study} VALIDATION (2024-01 to 2025-09), discovery passers only ===")
        print(V.round(3).to_string(index=False))


def main(studies):
    vx = vix_daily()
    data = {ix: minutes(ix) for ix in INDICES}
    dds = {ix: daily(data[ix]) for ix in INDICES}
    for st in studies:
        trades = []
        for ix in INDICES:
            f = {"R01": lambda: r01(ix, data[ix], dds[ix]), "R02": lambda: r02(ix, data[ix], dds[ix], vx),
                 "R03": lambda: r03(ix, data[ix], dds[ix]), "R04": lambda: r04(ix, data[ix], dds[ix]),
                 "R05": lambda: r05(ix, data[ix], dds[ix])}[st]
            trades += f()
        evaluate(st, trades)


if __name__ == "__main__":
    main(sys.argv[1:])
