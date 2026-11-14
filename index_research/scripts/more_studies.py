"""R13-R18 of index_research/PROGRAM.md (Amendment A2). Usage: python more_studies.py R13 [R14 ...]
R16 mirror cell = SHORT for 5 sessions after VIX falls >= 20 % below its 20-day mean (the fear-buying cell's mirror).
R18 costs: 0.03 % a side a leg (futures, charges included), 2x = 0.06 %.
"""
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

from lib import (REPO, boot_ci, bh, daily, fut_trade, index_close_vix, mc_drawdown, minutes, period, save, summary, validation_pass)

sys.stdout.reconfigure(encoding="utf-8")
END = date(2026, 10, 28)


def perD(d):
    return "D" if d < date(2018, 1, 1) else ("V" if d < date(2022, 1, 1) else "L")


def per18(d):
    return "D" if d < date(2022, 1, 1) else ("V" if d < date(2024, 10, 1) else "L")


def rec(cell, day, dirn, pin, pout, index="NIFTY50"):
    n1, p1 = fut_trade(index, day, dirn, pin, pout)
    n2, p2 = fut_trade(index, day, dirn, pin, pout, cost_mult=2.0)
    return {"cell": cell, "day": day, "net_rs": n1, "net_pct": p1, "net_rs_2x": n2, "net_pct_2x": p2}


def nifty_daily():
    d = pd.read_csv(os.path.join(REPO, "data", "eod2", "nifty 50.csv"), parse_dates=["Date"])
    d["d"] = d["Date"].dt.date
    d = d[d["d"] <= END].set_index("d")[["Open", "High", "Low", "Close"]].astype(float)
    return d


# ---------- R13 intraday momentum ----------
def r13():
    out = []
    for ix in ("NIFTY50", "NIFTYBANK", "SENSEX"):
        days = minutes(ix)
        dd = daily(days)
        ses = list(dd.index)
        for i in range(1, len(ses)):
            d = ses[i]
            g = days[d].set_index("hm")
            if not all(k in g.index for k in (944, 1430, 1500)):
                continue
            first = g.loc[944, "close"] / dd.loc[ses[i - 1], "close"] - 1
            mid = g.loc[1500, "open"] / g.loc[1430, "open"] - 1
            pin, pout = float(g.loc[1500, "open"]), float(g["close"].iloc[-1])
            dirn = 1 if first > 0 else -1
            for cell, ok in (("all", True), ("big", abs(first) > 0.005), ("agree", np.sign(mid) == np.sign(first))):
                if ok and first != 0:
                    out.append({**rec(f"{ix}|im_{cell}", d, dirn, pin, pout, ix)})
    return out, period


# ---------- R14 trend filters ----------
def spells(sig, df, cell, ls=False):
    """sig: Series of +1/0/-1 decided at each close; position taken at the next open, closed at the next open after it changes."""
    out, pos, entry, eday = [], 0, None, None
    idx = list(df.index)
    for i in range(len(idx) - 1):
        want = int(sig.iloc[i]) if not np.isnan(sig.iloc[i]) else 0
        if not ls and want < 0:
            want = 0
        if want != pos:
            nxt = idx[i + 1]
            px = float(df.loc[nxt, "Open"])
            if pos != 0:
                out.append(rec(cell, eday, pos, entry, px))
            pos, entry, eday = want, px, nxt
    return out


def r14():
    df = nifty_daily()
    c = df["Close"]
    s200, s50 = c.rolling(200).mean(), c.rolling(50).mean()
    out = []
    out += spells(pd.Series(np.where(c > s200, 1, 0), index=df.index).where(s200.notna()), df, "sma200")
    out += spells(pd.Series(np.where(s50 > s200, 1, 0), index=df.index).where(s200.notna()), df, "cross")
    out += spells(pd.Series(np.where(c > s200, 1, -1), index=df.index).where(s200.notna()), df, "sma200_ls", ls=True)
    hi20, lo10 = c.rolling(20).max().shift(1), c.rolling(10).min().shift(1)
    st, sig = 0, []
    for x, h, l in zip(c, hi20, lo10):
        if np.isnan(h):
            sig.append(np.nan)
            continue
        if st == 0 and x > h:
            st = 1
        elif st == 1 and x < l:
            st = 0
        sig.append(st)
    out += spells(pd.Series(sig, index=df.index), df, "donchian")
    for p in ("D", "V", "L"):
        x = df[[perD(d) == p for d in df.index]]
        print(f"buy and hold {p}: {(x['Close'].iloc[-1] / x['Open'].iloc[0] - 1) * 100:.1f} %")
    return out, perD


# ---------- R15 short-term reversal ----------
def rsi(x, n=2):
    dl = x.diff()
    up, dn = dl.clip(lower=0), -dl.clip(upper=0)
    rs = up.ewm(alpha=1 / n, adjust=False).mean() / dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + rs)


def r15():
    df = nifty_daily()
    c = df["Close"]
    r2, s200, s5 = rsi(c), c.rolling(200).mean(), c.rolling(5).mean()
    idx = list(df.index)
    out = []
    for cell, cond_in, cond_out, dirn in (("rsi2", lambda i: r2.iloc[i] < 10 and c.iloc[i] > s200.iloc[i], lambda i: c.iloc[i] > s5.iloc[i], 1),
                                          ("rsi2_short", lambda i: r2.iloc[i] > 90 and c.iloc[i] < s200.iloc[i], lambda i: c.iloc[i] < s5.iloc[i], -1)):
        i = 200
        while i < len(idx) - 1:
            if cond_in(i):
                j = i + 1
                while j < len(idx) - 1 and not cond_out(j):
                    j += 1
                out.append(rec(cell, idx[i], dirn, float(c.iloc[i]), float(c.iloc[j])))
                i = j + 1
            else:
                i += 1
    dn = c.diff() < 0
    up = c.diff() > 0
    for i in range(3, len(idx) - 1):
        if dn.iloc[i] and dn.iloc[i - 1] and dn.iloc[i - 2]:
            out.append(rec("down3", idx[i], 1, float(c.iloc[i]), float(c.iloc[i + 1])))
        if up.iloc[i] and up.iloc[i - 1] and up.iloc[i - 2]:
            out.append(rec("up3_short", idx[i], -1, float(c.iloc[i]), float(c.iloc[i + 1])))
    return out, perD


# ---------- R16 VIX spikes ----------
def r16():
    df = nifty_daily()
    v = index_close_vix().reindex(df.index).ffill()
    m20 = v.rolling(20).mean().shift(1)
    c = df["Close"]
    idx = list(df.index)
    out = []
    for cell, cond, hold, dirn in (("spike_h5", v >= 1.3 * m20, 5, 1), ("spike_h10", v >= 1.3 * m20, 10, 1), ("calm_short_h5", v <= 0.8 * m20, 5, -1)):
        armed, i = True, 20
        while i < len(idx) - 1:
            if cond.iloc[i] and armed:
                j = min(i + hold, len(idx) - 1)
                out.append(rec(cell, idx[i], dirn, float(c.iloc[i]), float(c.iloc[j])))
                armed = False
                i = j
                continue
            if not cond.iloc[i]:
                armed = True
            i += 1
    return out, perD


# ---------- R17 calendar anomalies ----------
def r17():
    df = nifty_daily()
    c, o = df["Close"], df["Open"]
    idx = list(df.index)
    out = []
    month = pd.Series([d.year * 100 + d.month for d in idx], index=idx)
    # turn of month: enter at the close of the 4th-last session of month m, exit at the close of the 2nd session of m+1
    groups = {}
    for i, d in enumerate(idx):
        groups.setdefault(month.iloc[i], []).append(i)
    ms = sorted(groups)
    for a, b in zip(ms[:-1], ms[1:]):
        ia, ib = groups[a], groups[b]
        if len(ia) >= 4 and len(ib) >= 2:
            i0, i1 = ia[-4], ib[1]
            out.append(rec("tom", idx[i0], 1, float(c.iloc[i0]), float(c.iloc[i1])))
    for i, d in enumerate(idx):
        if d.weekday() == 0:
            out.append(rec("mon_short", d, -1, float(o.iloc[i]), float(c.iloc[i])))
            if i and idx[i - 1].weekday() == 4:
                out.append(rec("weekend", idx[i - 1], 1, float(c.iloc[i - 1]), float(o.iloc[i])))
    return out, perD


# ---------- R18 NIFTY / BANKNIFTY ratio ----------
def r18():
    from daily_studies import index_close
    ic = index_close()
    a, b = ic["NIFTYBANK"], ic["NIFTY50"]
    j = pd.concat([a.rename("y"), b.rename("x")], axis=1).dropna()
    j = j[j.index <= END]
    ly, lx = np.log(j["y"]), np.log(j["x"])
    beta = (ly.rolling(60).cov(lx) / lx.rolling(60).var()).shift(1)
    sp = ly - beta * lx
    z = (sp - sp.rolling(20).mean()) / sp.rolling(20).std()
    idx = list(j.index)
    out, pos = [], None
    for i in range(80, len(idx)):
        zz, d = z.iloc[i], idx[i]
        if pos is None and abs(zz) > 2:
            pos = {"i": i, "sgn": -1 if zz > 2 else 1, "b": float(np.clip(beta.iloc[i], 0.2, 3))}
        elif pos is not None and ((pos["sgn"] < 0 and zz <= 0) or (pos["sgn"] > 0 and zz >= 0) or abs(zz) > 3.5 or i == len(idx) - 1):
            k = pos["i"]
            ry, rx = j["y"].iloc[i] / j["y"].iloc[k] - 1, j["x"].iloc[i] / j["x"].iloc[k] - 1
            g = pos["sgn"] * (ry - pos["b"] * rx) / (1 + pos["b"]) * 100
            out.append({"cell": "ratio", "day": idx[k], "net_pct": g - 0.06, "net_pct_2x": g - 0.12, "net_rs": (g - 0.06) / 100 * 1_000_000})
            pos = None
    return out, per18


def evaluate(study, trades, per):
    T = pd.DataFrame(trades)
    T["period"] = T["day"].map(per)
    save(T, f"{study}_trades.csv")
    C = bh(pd.DataFrame([{"key": k, **summary(x)} for k, x in T[T["period"] == "D"].groupby("cell")]))
    save(C, f"{study}_discovery.csv")
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 200)
    cols = ["key", "n", "win_pct", "mean_pct", "median_pct", "total_rs", "t", "pf", "mean_2x", "h1_mean", "h2_mean", "max_dd_rs", "discovery_pass"]
    print(f"=== {study} DISCOVERY ===")
    print(C[cols].round(3).to_string(index=False))
    vrows = []
    for key in C.loc[C["discovery_pass"], "key"]:
        x = T[(T["cell"] == key) & (T["period"] == "V")]
        s = {"key": key, **summary(x)}
        s["validation_pass"] = validation_pass(s)
        if s["validation_pass"]:
            lo, hi = boot_ci(x)
            s.update({"boot_lo": lo, "boot_hi": hi, **mc_drawdown(x["net_rs"])})
            s.update({f"L_{k}": v for k, v in summary(T[(T["cell"] == key) & (T["period"] == "L")]).items()})
        vrows.append(s)
    if vrows:
        V = pd.DataFrame(vrows)
        save(V, f"{study}_validation.csv")
        print(f"=== {study} VALIDATION [+ L for passers] ===")
        print(V.round(3).to_string(index=False))
    print("discovery passes:", int(C["discovery_pass"].sum()))


if __name__ == "__main__":
    for st in sys.argv[1:]:
        tr, per = {"R13": r13, "R14": r14, "R15": r15, "R16": r16, "R17": r17, "R18": r18}[st]()
        evaluate(st, tr, per)
