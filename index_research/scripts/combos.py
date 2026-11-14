"""Combination study, index_research/PROGRAM.md Amendment A4. Built only from the saved trade files (R01, R02, R11) and eod2 NIFTY closes.
Usage: python combos.py"""
import os
import sys

import numpy as np
import pandas as pd

from lib import REPO, ROOT, boot_ci, bh, mc_drawdown, period, save, summary, validation_pass

sys.stdout.reconfigure(encoding="utf-8")
R = os.path.join(ROOT, "results")


def load(name):
    t = pd.read_csv(os.path.join(R, name), parse_dates=["day"])
    t["day"] = t["day"].dt.date
    return t


def main():
    r02, r01, r11 = load("R02_trades.csv"), load("R01_trades.csv"), load("R11_trades.csv")
    n = r02[r02["index"] == "NIFTY50"]
    A = n[n["cell"] == "overnight_prevup"].set_index("day")
    O = n[n["cell"] == "overnight_all"].set_index("day")
    I = n[n["cell"] == "intraday_vixlow"].set_index("day")
    G = r01[(r01["index"] == "NIFTY50") & (r01["cell"] == "gap1.0_stop0_skip0")].set_index("day")
    rf = r11[r11["cell"] == "rf_all"].set_index("day")["prob"]
    e = pd.read_csv(os.path.join(REPO, "data", "eod2", "nifty 50.csv"), parse_dates=["Date"])
    e["d"] = e["Date"].dt.date
    c = e.set_index("d")["Close"]
    tr_close = (c > c.rolling(200).mean())                        # known at the close of d
    tr_prev = tr_close.shift(1)                                    # known at the open of d
    ses = sorted(set(O.index))
    month = {d: d.year * 100 + d.month for d in ses}
    tom = set()
    for i, d in enumerate(ses):
        if i + 1 < len(ses) and month[ses[i + 1]] != month[d]:
            tom.update(ses[max(0, i - 3):i + 1])                   # last 4 sessions of the month
            tom.add(ses[i + 1])                                    # first session of the next
    cols = ["net_rs", "net_pct", "net_rs_2x", "net_pct_2x"]
    cells = {}

    def pick(df, mask_days, name):
        x = df.loc[[d for d in df.index if d in mask_days]][cols].copy()
        x["day"] = x.index
        cells[name] = x.reset_index(drop=True)

    alld = set(ses)
    pick(A, alld, "C1_A")
    pick(A, tom, "C2_A_tom")
    pick(A, {d for d in ses if tr_close.get(d) is True or tr_close.get(d) == 1}, "C3_A_trend")
    pick(A, {d for d in ses if rf.get(d, 0) > 0.5}, "C4_A_rf")
    pick(O, {d for d in ses if tr_close.get(d) == 1}, "C5_O_trend")
    pick(O, tom, "C6_O_tom")
    pick(O, {d for d in ses if rf.get(d, 0) > 0.5}, "C7_O_rf")
    g = r01[(r01["index"] == "NIFTY50") & (r01["cell"] == "gap1.0_stop0_skip0")]
    g = g[[(dr > 0) == bool(tr_prev.get(d, False)) for d, dr in zip(g["day"], g["dir"])]]
    cells["C8_gap_trend"] = g[cols + ["day"]].reset_index(drop=True)
    pick(I, {d for d in ses if tr_prev.get(d) == 1}, "C9_I_trend")
    pick(O, {d for d in tom if tr_close.get(d) == 1}, "C10_O_tom_trend")

    def port(parts, name):
        s = pd.concat([p.set_index("day")[cols] for p in parts]).groupby(level=0).sum()
        s["day"] = s.index
        cells[name] = s.reset_index(drop=True)

    port([cells["C1_A"], I.assign(day=I.index)[cols + ["day"]]], "P1_A+I")
    port([cells["C1_A"], G.assign(day=G.index)[cols + ["day"]], I.assign(day=I.index)[cols + ["day"]]], "P2_A+G+I")
    port([cells["C1_A"], G.assign(day=G.index)[cols + ["day"]], I.assign(day=I.index)[cols + ["day"]], cells["C8_gap_trend"]], "P3_A+G+I+C8")

    T = pd.concat([x.assign(cell=k) for k, x in cells.items()], ignore_index=True)
    T["period"] = T["day"].map(period)
    save(T, "C_trades.csv")
    C = bh(pd.DataFrame([{"key": k, **summary(x)} for k, x in T[T["period"] == "D"].groupby("cell")]))
    save(C, "C_discovery.csv")
    pd.set_option("display.width", 250, "display.max_columns", 30)
    show = ["key", "n", "win_pct", "mean_pct", "median_pct", "total_rs", "t", "pf", "mean_2x", "h1_mean", "h2_mean", "max_dd_rs", "discovery_pass"]
    print("=== COMBINATIONS, DISCOVERY (2021-10 to 2023-12), NIFTY50 ===")
    print(C[show].round(3).to_string(index=False))
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
        save(V, "C_validation.csv")
        print("=== VALIDATION (2024-01 to 2025-09) for discovery passers [+ L only for validation passers] ===")
        print(V.round(3).to_string(index=False))
    print("discovery passes:", int(C["discovery_pass"].sum()))


if __name__ == "__main__":
    main()
