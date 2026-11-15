"""R20 (daily swing setup) and R21 (ADR stretch filter on G1 / G1-C), index_research/PROGRAM.md Amendment A5.
Usage: python swing_adr.py R20 | R21"""
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

from lib import (REPO, ROOT, boot_ci, bh, daily, fut_trade, index_close_vix, mc_drawdown, minutes, save, summary, validation_pass)

sys.stdout.reconfigure(encoding="utf-8")
END = date(2026, 10, 28)


def nifty():
    d = pd.read_csv(os.path.join(REPO, "data", "eod2", "nifty 50.csv"), parse_dates=["Date"])
    d["d"] = d["Date"].dt.date
    return d[d["d"] <= END].set_index("d")[["Open", "High", "Low", "Close"]].astype(float)


def banknifty():
    c = pd.read_parquet(os.path.join(os.environ["INDEX_STORE"], "index_close_daily.parquet"))
    c["d"] = pd.to_datetime(c["date"]).dt.date
    b = c[c["index"] == "NIFTYBANK"].set_index("d")[["open", "high", "low", "close"]]
    m = daily(minutes("NIFTYBANK"))
    m = m[m.index > b.index.max()]
    b = pd.concat([b, m]).sort_index()
    b.columns = ["Open", "High", "Low", "Close"]
    return b[b.index <= END].astype(float)


def swing(df, index, vix, cell):
    O, H, Lo, C = (df[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    idx = list(df.index)
    s50 = df["Close"].rolling(50).mean().to_numpy()
    e10 = df["Close"].ewm(span=10, adjust=False).mean().to_numpy()
    e20 = df["Close"].ewm(span=20, adjust=False).mean().to_numpy()
    rng = H - Lo
    out, i = [], 60
    while i < len(idx) - 2:
        s = i
        trend = C[s] > s50[s] and e10[s] > e10[s - 5] and e20[s] > e20[s - 5]
        contr = (H[s] <= H[s - 1] and Lo[s] >= Lo[s - 1]) or rng[s] <= rng[s - 6:s + 1].min()
        ok = trend and (contr or cell == "nocontr")
        if cell == "vix15":
            v = vix.get(idx[s], np.nan)
            ok = ok and v < 15
        d = s + 1
        if not ok or H[d] <= H[s]:
            i += 1
            continue
        entry = max(O[d], H[s])
        stop = Lo[s]
        R = entry - stop
        if R <= 0:
            i += 1
            continue
        tgt = entry + R
        exits = [None, None]                     # half 1 (target), half 2 (trail)
        j = d
        while j < len(idx) and (exits[0] is None or exits[1] is None):
            first_day = j == d
            if Lo[j] <= stop:                    # the stop first (conservative), for every open half
                px = stop if first_day or O[j] > stop else O[j]
                exits = [e if e is not None else px for e in exits]
                break
            if exits[0] is None and H[j] >= tgt:
                exits[0] = tgt if first_day or O[j] < tgt else O[j]
            if exits[1] is None and (C[j] < e20[j] or j - d >= 29):
                exits[1] = C[j]
            j += 1
        if None in exits:
            exits = [e if e is not None else C[min(j, len(idx) - 1)] for e in exits]
        nets = [fut_trade(index, idx[d], 1, entry, x) for x in exits]
        nets2 = [fut_trade(index, idx[d], 1, entry, x, cost_mult=2.0) for x in exits]
        out.append({"cell": f"{index}|{cell}", "day": idx[d], "entry": entry, "stop": stop, "exit1": exits[0], "exit2": exits[1],
                    "held": j - d + 1, "net_rs": sum(n for n, _ in nets) / 2, "net_pct": sum(p for _, p in nets) / 2,
                    "net_rs_2x": sum(n for n, _ in nets2) / 2, "net_pct_2x": sum(p for _, p in nets2) / 2})
        i = j + 1
    return out


def per_nifty(d):
    return "D" if d < date(2018, 1, 1) else ("V" if d < date(2022, 1, 1) else "L")


def per_bank(d):
    return "D" if d < date(2022, 1, 1) else ("V" if d < date(2024, 10, 1) else "L")


def r20():
    vix = index_close_vix()
    out = []
    for name, df, per in (("NIFTY50", nifty(), per_nifty), ("NIFTYBANK", banknifty(), per_bank)):
        for cell in ("all", "vix15", "nocontr"):
            for t in swing(df, name, vix, cell):
                t["period"] = per(t["day"])
                out.append(t)
    return pd.DataFrame(out)


def r21():
    sys.path.insert(0, REPO)
    from scanner.s3_b2 import signal
    days = minutes("NIFTY50")
    dd = daily(days)
    adr = ((dd["high"] - dd["low"]) / dd["close"]).rolling(20).mean().shift(1)
    ses = list(dd.index)
    st = {}
    for i in range(21, len(ses)):
        d = ses[i]
        if d < date(2024, 10, 1):
            continue
        sg = signal(days[d], 15, None)
        if sg is None:
            continue
        g = days[d]
        c = float(g.loc[g["timestamp"] == sg[1], "close"].iloc[0])
        pc = dd.loc[ses[i - 1], "close"]
        dirn = 1 if sg[0] == "CE" else -1
        st[d] = (sg[0], dirn * (c - pc) / (adr[d] * pc))
    gp = pd.read_csv(os.path.join(REPO, "g1_research", "results", "g1_live_replay_trades.csv"), parse_dates=["day"])
    gp["day"] = gp["day"].dt.date
    gc = pd.read_csv(os.path.join(REPO, "g1_research", "data", "g1c_opt_trades.csv"), parse_dates=["day"])
    gc["day"] = gc["day"].dt.date
    gc = gc.rename(columns={"B_1_net": "net_pct", "B_1_rs": "net_rs", "B_2_net": "net_pct_2x"})
    rows = []
    for nm, t, side in (("G1", gp, "PE"), ("G1C", gc, "CE")):
        t = t[t["net_pct"].notna()].copy()
        t["stretch"] = [st[d][1] if d in st and st[d][0] == side else np.nan for d in t["day"]]
        t = t[t["stretch"].notna()]
        low = t[t["stretch"] <= 0.5]
        high = t[t["stretch"] > 0.5]
        rows += [low.assign(cell=f"{nm}_keep_le50"), high.assign(cell=f"{nm}_keep_gt50")]
        if nm == "G1":
            rows.append(low[low["g1f"] == 1].assign(cell="G1F_keep_le50"))
            rows.append(t.assign(cell="G1_all_reference"))
            rows.append(t[t["g1f"] == 1].assign(cell="G1F_all_reference"))
        else:
            rows.append(t.assign(cell="G1C_all_reference"))
    T = pd.concat(rows, ignore_index=True)
    T["period"] = np.where(T["day"] < date(2025, 10, 1), "D", "V")
    return T[["cell", "day", "stretch", "net_pct", "net_rs", "net_pct_2x", "period"]]


def evaluate(study, T):
    save(T, f"{study}_trades.csv")
    ref = T["cell"].str.contains("reference")
    C = bh(pd.DataFrame([{"key": k, **summary(x)} for k, x in T[(T["period"] == "D") & ~ref].groupby("cell")]))
    R = pd.DataFrame([{"key": k, **summary(x)} for k, x in T[(T["period"] == "D") & ref].groupby("cell")])
    save(C, f"{study}_discovery.csv")
    pd.set_option("display.width", 250, "display.max_columns", 30)
    cols = ["key", "n", "win_pct", "mean_pct", "median_pct", "total_rs", "t", "pf", "mean_2x", "h1_mean", "h2_mean", "max_dd_rs"]
    print(f"=== {study} DISCOVERY ===")
    print(C[cols + ["discovery_pass"]].round(3).to_string(index=False))
    if len(R):
        print("reference (not tested):")
        print(R[cols].round(3).to_string(index=False))
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
        print(f"=== {study} VALIDATION [+ L only for passers] ===")
        print(V.round(3).to_string(index=False))
    print("discovery passes:", int(C["discovery_pass"].sum()))


if __name__ == "__main__":
    for st in sys.argv[1:]:
        evaluate(st, {"R20": r20, "R21": r21}[st]())
