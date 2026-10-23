"""S1 fade · early decline and recovery on historical 1-minute candles (descriptive; strategies/S1_fade_decline_recovery.md).

    python -m scanner.fade_decline_recovery

1-minute OHLC PROXY: candle lows/highs are not sellable bids. Writes data/results/S1_fade_decline_recovery.md,
_trades.csv and .xlsx. Nothing live changes.
"""
from __future__ import annotations

import pandas as pd

from .build import ROOT
from .fade_entry_quality import md_table, minutes
from .fade_entry_quality_fmt import tidy

RES = ROOT / "data" / "results"
DROPS = (5, 10, 15, 20)
WINDOWS = (1, 3, 5, 10, 15)


def mins(t: str) -> int:
    return int(t[:2]) * 60 + int(t[3:5])


def per_trade(d: pd.DataFrame, by: dict) -> pd.DataFrame:
    out = []
    for _, r in d.iterrows():
        c = by[(r.symbol, r.day0, r.side, float(r.strike))]
        c = c[(c["t"] >= "09:17") & (c["t"] <= "15:19")].reset_index(drop=True)
        e = float(r.entry)
        row = {"day0": r.day0, "half": r.half, "symbol": r.symbol, "side": r.side, "strike": r.strike, "entry": e,
               "v12 why": r["v12 why"], "v12 at": r["v12 at"], "v12 net Rs": r["v12 net Rs"], "v10 net Rs": r["v10 net Rs"],
               "close 15:19 above entry": bool(c["c"].iat[-1] > e)}
        for x in DROPS:
            hit = c.index[c["l"] <= e * (1 - x / 100) + 1e-9]
            if not len(hit):
                row[f"fell {x}% at"] = None
                continue
            i = hit[0]
            t0 = c.at[i, "t"]
            row[f"fell {x}% at"] = t0
            later = c.iloc[i + 1:]
            back = later.index[later["h"] >= e - 1e-9]
            row[f"fell {x}%: minutes to entry"] = mins(c.at[back[0], "t"]) - mins(t0) if len(back) else None
            up10 = later.index[later["h"] >= 1.10 * e - 1e-9]
            row[f"fell {x}%: reached +10% later"] = bool(len(up10))
        if r["v12 why"] == "stop":
            k = c.index[c["t"] == r["v12 at"]]
            later = c.iloc[k[0] + 1:] if len(k) else c.iloc[0:0]
            for lvl, name in ((1.0, "entry"), (1.10, "+10%"), (1.20, "+20%")):
                b = later.index[later["h"] >= lvl * e - 1e-9]
                row[f"after stop: reached {name}"] = bool(len(b))
                row[f"after stop: minutes to {name}"] = mins(c.at[b[0], "t"]) - mins(r["v12 at"]) if len(b) else None
            row["after stop: max up later %"] = round((later["h"].max() / e - 1) * 100, 1) if len(later) else None
        out.append(row)
    return pd.DataFrame(out)


def decline_table(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for x in DROPS:
        f = t[t[f"fell {x}% at"].notna()]
        m = f[f"fell {x}%: minutes to entry"]
        row = {"decline (candle low)": f"-{x} %", "trades that fell": len(f), "of all": len(t),
               "share %": round(len(f) / len(t) * 100, 1)}
        for n in WINDOWS:
            k = int((m <= n).sum())
            row[f"back to entry <= {n} min"] = f"{k} ({k / len(f) * 100:.0f}%)" if len(f) else "-"
        k = int(m.notna().sum())
        row["back to entry by 15:19"] = f"{k} ({k / len(f) * 100:.0f}%)" if len(f) else "-"
        k = int(f[f"fell {x}%: reached +10% later"].sum())
        row["reached +10 % later"] = f"{k} ({k / len(f) * 100:.0f}%)" if len(f) else "-"
        k = int(f["close 15:19 above entry"].sum())
        row["closed above entry"] = f"{k} ({k / len(f) * 100:.0f}%)" if len(f) else "-"
        row["v12 net Rs"] = round(f["v12 net Rs"].sum())
        row["v10 net Rs (hold to 15:19)"] = round(f["v10 net Rs"].sum())
        row["train / test"] = f"{(f.half == 'train').sum()} / {(f.half == 'test').sum()}"
        row["note"] = "inconclusive (< 20)" if len(f) < 20 else ""
        rows.append(row)
    return pd.DataFrame(rows)


def stop_table(t: pd.DataFrame) -> pd.DataFrame:
    s = t[t["v12 why"] == "stop"]
    rows = []
    for half, x in (("all", s), ("train (before 3 Nov 2025)", s[s.half == "train"]), ("test (from 3 Nov 2025)", s[s.half == "test"])):
        row = {"stopped trades": half, "n": len(x)}
        for name in ("entry", "+10%", "+20%"):
            k = int(x[f"after stop: reached {name}"].sum())
            row[f"later reached {name}"] = f"{k} ({k / len(x) * 100:.0f}%)" if len(x) else "-"
            row[f"median minutes to {name}"] = x[f"after stop: minutes to {name}"].median()
        k = int(x["close 15:19 above entry"].sum())
        row["closed above entry 15:19"] = f"{k} ({k / len(x) * 100:.0f}%)" if len(x) else "-"
        row["v12 net Rs"] = round(x["v12 net Rs"].sum())
        row["v10 net Rs (no stop)"] = round(x["v10 net Rs"].sum())
        rows.append(row)
    return pd.DataFrame(rows)


def extended(d: pd.DataFrame, by: dict) -> pd.DataFrame:
    """The addendum's measures, one row per (trade, threshold) that the trade reached."""
    out = []
    for _, r in d.iterrows():
        c = by[(r.symbol, r.day0, r.side, float(r.strike))]
        c = c[(c["t"] >= "09:17") & (c["t"] <= "15:19")].reset_index(drop=True)
        e, xt = float(r.entry), r["v12 at"]
        held = c[c["t"] <= xt]
        same_hl = bool(len(held) and held["h"].idxmax() == held["l"].idxmin())
        for x in DROPS:
            hit = c.index[c["l"] <= e * (1 - x / 100) + 1e-9]
            if not len(hit):
                continue
            i = hit[0]
            t0, low0 = c.at[i, "t"], float(c.at[i, "l"])
            later = c.iloc[i + 1:]
            row = {"day0": r.day0, "half": r.half, "symbol": r.symbol, "exit": r["v12 why"], "threshold %": x,
                   "decline at": t0, "exit at": xt, "post-exit decline": t0 > xt, "decline in exit candle": t0 == xt,
                   "held high and low in one candle": same_hl, "minutes left": len(later),
                   "later best % of entry": round((later["h"].max() / e - 1) * 100, 1) if len(later) else None,
                   "later worst % of entry": round((later["l"].min() / e - 1) * 100, 1) if len(later) else None,
                   "v12 net Rs (realised)": r["v12 net Rs"]}
            for n in WINDOWS:
                w = later[later["t"].map(mins) <= mins(t0) + n]
                row[f"enough for {n} min"] = len(later) >= n
                b = w[w["h"] >= e - 1e-9]
                row[f"to entry <= {n} min"] = None if len(later) < n else ("before exit" if len(b) and b["t"].iat[0] <= xt
                                                                            else "after exit" if len(b) else "no")
                row[f"bounce 10% <= {n} min"] = None if len(later) < n else bool((w["h"] >= low0 * 1.10 - 1e-9).any())
            b = later[later["h"] >= e - 1e-9]
            row["to entry by 15:19"] = "before exit" if len(b) and b["t"].iat[0] <= xt else "after exit" if len(b) else "no"
            row["minutes to entry"] = mins(b["t"].iat[0]) - mins(t0) if len(b) else None
            out.append(row)
    return pd.DataFrame(out)


def ext_table(x: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    for th, g in x.groupby("threshold %"):
        pre = g[~g["post-exit decline"]]
        row = {"group": label, "decline": f"-{th} %", "reached": len(g), "of them after the exit": int(g["post-exit decline"].sum()),
               "decline in the exit candle": int(g["decline in exit candle"].sum())}
        for n in WINDOWS:
            ok = pre[pre[f"enough for {n} min"]]
            k_b = int((ok[f"to entry <= {n} min"] == "before exit").sum())
            k_a = int((ok[f"to entry <= {n} min"] == "after exit").sum())
            k_t = int(ok[f"bounce 10% <= {n} min"].sum())
            row[f"{n} min: n"] = len(ok)
            row[f"{n} min: to entry before exit"] = f"{k_b} ({k_b / len(ok) * 100:.0f}%)" if len(ok) else "-"
            row[f"{n} min: to entry after exit"] = f"{k_a} ({k_a / len(ok) * 100:.0f}%)" if len(ok) else "-"
            row[f"{n} min: 10% bounce from the low"] = f"{k_t} ({k_t / len(ok) * 100:.0f}%)" if len(ok) else "-"
        kb, ka = int((pre["to entry by 15:19"] == "before exit").sum()), int((pre["to entry by 15:19"] == "after exit").sum())
        row["by 15:19: to entry before exit"] = f"{kb} ({kb / len(pre) * 100:.0f}%)" if len(pre) else "-"
        row["by 15:19: to entry after exit (hypothetical)"] = f"{ka} ({ka / len(pre) * 100:.0f}%)" if len(pre) else "-"
        row["median minutes to entry"] = pre["minutes to entry"].median()
        row["median later best %"] = pre["later best % of entry"].median()
        row["median later worst %"] = pre["later worst % of entry"].median()
        row["realised v12 net Rs"] = round(pre["v12 net Rs (realised)"].sum())
        row["note"] = "inconclusive (< 20)" if len(pre) < 20 else ""
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    d = pd.read_csv(RES / "S1_fade_entry_quality_audit_trades.csv")
    by = minutes()
    t = per_trade(d, by)
    ex = extended(d, by)
    ex.to_csv(RES / "S1_fade_decline_recovery_extended.csv", index=False)
    et = pd.concat([ext_table(ex, "all")] + [ext_table(ex[ex.exit == k], f"v12 exit: {k}") for k in ("stop", "trail")]
                   + [ext_table(ex[ex.half == h], f"half: {h}") for h in ("train", "test")])
    amb = {"trades": len(d), "held high and low in one candle": int(ex.drop_duplicates(["day0", "symbol"])["held high and low in one candle"].sum())}
    t.to_csv(RES / "S1_fade_decline_recovery_trades.csv", index=False)
    dt, st = decline_table(t), stop_table(t)
    by_half = pd.concat([decline_table(t[t.half == h]).assign(half=h) for h in ("train", "test")])
    note = ("1-minute OHLC PROXY (candle lows / highs), not sellable bids. 339 trades, day 0 2024-10-17 to 2026-08-17, "
            "entry 09:16 open + 1 tick. Recovery counts start the minute AFTER the decline candle. "
            "Protocol: strategies/S1_fade_decline_recovery.md.")
    md = ["# S1 fade · early decline and recovery (descriptive, candle proxy)", "", note, "",
          "## How often it fell, and how often it came back", "", md_table(dt), "",
          "## The same, by half", "", md_table(by_half), "",
          "## After the actual v12 stop", "", md_table(st), "",
          "## Addendum: before vs after the exit, sufficient windows, bounce from the low (by exit reason and half)", "",
          "Rows count only declines that happened while held; 'after exit' recoveries are hypothetical and never "
          "realised. Each window's n = trades with at least that many minutes left.", "", md_table(et), "",
          f"Same-candle ambiguity: {amb}", ""]
    (RES / "S1_fade_decline_recovery.md").write_text("\n".join(md), encoding="utf-8")
    xl = RES / "S1_fade_decline_recovery.xlsx"
    with pd.ExcelWriter(xl) as w:
        pd.DataFrame({"About this file": [note, "Sheets: Declines (all), Declines by half, After the stop, Trades.",
                                          "Descriptive only: nothing here is a rule. Live best-bid data from 26 Oct will "
                                          "answer the same questions on real bids."]}).to_excel(w, sheet_name="Read me", index=False)
        dt.to_excel(w, sheet_name="Declines", index=False)
        by_half.to_excel(w, sheet_name="Declines by half", index=False)
        st.to_excel(w, sheet_name="After the stop", index=False)
        et.to_excel(w, sheet_name="Before vs after exit", index=False)
        t.to_excel(w, sheet_name="Trades", index=False)
    tidy(xl)
    print(dt.to_string(index=False))
    print(st.to_string(index=False))


if __name__ == "__main__":
    main()
