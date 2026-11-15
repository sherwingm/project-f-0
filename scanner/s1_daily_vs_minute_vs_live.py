"""S1 live strategies: daily-candle old data vs recent, year by year, plus 1-minute and live. Plan: strategies/S1_daily_vs_minute_vs_live.md (committed before any number).
Output: data/results/S1_daily_vs_minute_vs_live.md and _trades.csv. Descriptive only.
Run: python -m scanner.s1_daily_vs_minute_vs_live"""
import json
import os
import sys

import numpy as np
import pandas as pd

from scanner.stats import clustered_t

sys.stdout.reconfigure(encoding="utf-8")
R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "results")
REPO = os.path.dirname(R if False else os.path.dirname(R))


def stats(x, net="net_pct", day="day0", rs=None):
    x = x[x[net].notna()]
    if len(x) == 0:
        return {"n": 0}
    v = x[net].astype(float)
    t = clustered_t(v.to_numpy(), [str(d) for d in x[day]]) if len(x) > 3 else np.nan
    return {"n": len(x), "win": (v > 0).mean() * 100, "mean": v.mean(), "median": v.median(), "t": t,
            "total_rs": x[rs].sum() if rs and rs in x else np.nan}


def fmt(s):
    if s["n"] == 0:
        return "n 0"
    t = "" if s["t"] is None or s["t"] != s["t"] else f", t {s['t']:.2f}"
    rs = "" if s.get("total_rs") is None or s["total_rs"] != s["total_rs"] else f", Rs {s['total_rs']:,.0f}"
    return f"n {s['n']}, win {s['win']:.0f} %, mean {s['mean']:+.1f} %, median {s['median']:+.1f} %{t}{rs}"


def main():
    old = pd.read_csv(os.path.join(R, "S1_v10_trades_2022_24.csv"))
    new = pd.read_csv(os.path.join(R, "S1_v10_trades.csv"))
    d = pd.concat([old, new[~new["day0"].isin([])]], ignore_index=True).drop_duplicates(subset=["symbol", "day0", "side"])
    d = d[d["e1_excluded"].isna()].copy()
    d["year"] = d["day0"].str[:4]
    d["half"] = d["day0"].str[:4] + np.where(d["day0"].str[5:7].astype(int) <= 6, "H1", "H2")
    out = ["# S1 live strategies: daily-candle old data vs recent vs 1-minute vs live (15 Nov 2026)", "",
           "Plan: `strategies/S1_daily_vs_minute_vs_live.md` (commit fa02bbb6d, before any number). Descriptive only; nothing live changed.",
           "Net % = net of costs, % of the premium. t = date-clustered. `e1` = sold the same day on daily prices; `e2` = daily-candle -20 % stop path.", ""]
    out += ["## 1. S1 fade, daily-candle backtest by year (entry day-0 open + tick; 2022-01 to 2026-08)", ""]
    for col, lab in (("e1", "e1 same-day sale (the v10 rule)"), ("e2", "e2 stop path (v11-like)")):
        out.append(f"**{lab}**")
        for y, g in d.groupby("year"):
            out.append(f"- {y}: " + fmt(stats(g, f"{col}_net_pct", rs=f"{col}_net")))
        o = d[d["day0"] < "2024-10-01"]
        r = d[d["day0"] >= "2024-10-01"]
        so, sr = stats(o, f"{col}_net_pct"), stats(r, f"{col}_net_pct")
        out.append(f"- **Old data (to 2024-09):** " + fmt(so))
        out.append(f"- **Oct 2024 to present:** " + fmt(sr))
        if so["n"] > 3 and sr["n"] > 3:
            a, b = o[f"{col}_net_pct"].dropna().to_numpy(), r[f"{col}_net_pct"].dropna().to_numpy()
            diff = b.mean() - a.mean()
            se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
            out.append(f"- Recent minus old: {diff:+.1f} points (Welch t {diff / se:.2f}); the sign {'is the same' if np.sign(so['mean']) == np.sign(sr['mean']) else 'flips'}.")
        out.append("")
    out += ["Half-years (e1):"]
    for h, g in d.groupby("half"):
        out.append(f"- {h}: " + fmt(stats(g, "e1_net_pct")))
    out.append("")
    # arms A / B recent recomputed, old quoted
    v8 = pd.read_csv(os.path.join(R, "S1_v8_trades.csv"))
    v8 = v8[v8["excluded"].isna() | (v8["excluded"] == False)] if "excluded" in v8 else v8
    out += ["## 2. S1 arms A / B (daily candles, live rules)", "",
            "- **Old data 2021-24 (QUOTED from DECISIONS.md, v7 rules, not recomputed):** arm A 258 trades, -17.3 % a trade, t -1.52; arm B 84 trades, +31.8 %, t 1.07 (median -58 % / -57 %).",
            "- **Recent 2025-04 to 2026-08 (recomputed from the v8 file, live rules, entry day+1):**"]
    for arm in ("A", "B"):
        g = v8[v8["arm"] == arm].copy()
        g["year"] = g["entry_date"].str[:4]
        out.append(f"  - arm {arm}: " + fmt(stats(g.rename(columns={"entry_date": "day0"}), "net_pct", rs="net")))
        for y, gg in g.groupby("year"):
            out.append(f"    - {y}: " + fmt(stats(gg.rename(columns={"entry_date": "day0"}), "net_pct", rs="net")))
    out.append("")
    # minutes
    m = pd.read_csv(os.path.join(R, "S1_fade_minutes_retest_trades.csv"))
    m = m[(m["lot_ok"] == True) & (m["entry_B"] >= 2)].copy()
    m["year"] = m["day0"].str[:4]
    out += ["## 3. The same fade signals on 1-minute candles (entry 09:16 open + tick), Oct 2024 to Aug 2026", "",
            f"Rows passing the live rule: {len(m)} (the retest report quotes 339).", ""]
    for col, lab in (("v10_net_pct", "v10 hold to 15:19"), ("v12_net_pct", "v12 live exit")):
        out.append(f"**{lab}**")
        for y, g in m.groupby("year"):
            out.append(f"- {y}: " + fmt(stats(g, col)) + (f"; max up mean {g['max_up_pct'].mean():.0f} %, median {g['max_up_pct'].median():.0f} %" if col == "v10_net_pct" else ""))
        out.append(f"- all: " + fmt(stats(m, col)))
        out.append("")
    # matched
    dd = d.copy()
    key = dd.merge(m, on=["symbol", "day0"], how="inner", suffixes=("_d", "_m"))
    out += ["## 4. Trade-by-trade match, daily vs minutes (same symbol and day0, from 2024-10-01)", ""]
    rec = d[d["day0"] >= "2024-10-01"]
    out.append(f"- daily trades in the period: {len(rec)}; minute-rule trades: {len(m)}; matched on symbol + day0: {len(key)}.")
    if len(key) > 5:
        diff = key["v10_net_pct"] - key["e1_net_pct"]
        out.append(f"- entry price: minute entry / daily entry median {np.nanmedian(key['entry_B'] / key['entry_price']):.2f} (mean {np.nanmean(key['entry_B'] / key['entry_price']):.2f}); same strike in {int(((key['entry_B'] / key['entry_price']).between(0.9, 1.1)).sum())} of {len(key)} (price within 10 %).")
        out.append(f"- same-day sale net %: daily e1 mean {key['e1_net_pct'].mean():+.1f} %, minute v10 mean {key['v10_net_pct'].mean():+.1f} %; per-trade difference mean {diff.mean():+.1f} points (t {clustered_t(diff.to_numpy(), [str(x) for x in key['day0']]):.2f}).")
        out.append(f"- correlation of the two per-trade results {key['v10_net_pct'].corr(key['e1_net_pct']):.2f}; same sign in {((np.sign(key['v10_net_pct']) == np.sign(key['e1_net_pct'])).mean() * 100):.0f} % of trades.")
    out.append("")
    # live
    led = json.load(open(os.path.join(REPO, "stress_audit", "data", "paper_ledger_snapshot_2026-11-09.json")))
    rows = []
    for x in led["closed"]:
        rl = x.get("rule") or {}
        if rl.get("strategy") != "fade":
            continue
        rows.append({"day0": x["opened_at"][:10], "symbol": x["symbol"], "version": rl.get("version"), "net_pct": x.get("return_pct"), "net": x.get("net_pnl"), "reason": x.get("reason")})
    L = pd.DataFrame(rows)
    out += ["## 5. Live paper fade trades (ledger snapshot of 9 Nov; 15 Oct to 9 Nov 2026; distribution only, no date overlap with sections 1-3)", ""]
    if len(L):
        out.append(f"- all closed fade trades: " + fmt(stats(L, "net_pct", rs="net")))
        for v, g in L.groupby("version", dropna=False):
            out.append(f"- version {v}: " + fmt(stats(g, "net_pct", rs="net")))
    out.append("")
    open(os.path.join(R, "S1_daily_vs_minute_vs_live.md"), "w", encoding="utf-8").write("\n".join(out))
    pd.concat([d.assign(src="daily"), m.assign(src="minute")], ignore_index=True).to_csv(os.path.join(R, "S1_daily_vs_minute_vs_live_trades.csv"), index=False)
    print("\n".join(out))


if __name__ == "__main__":
    main()
