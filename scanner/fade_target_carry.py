"""S1 fade · carry with a profit-target sell, held to T-1 (numbers only).

    python -m scanner.fade_target_carry

strategies/S1_fade_target_carry.md fixes every choice. Reads the 339 v12 backtest trades
(data/results/S1_fade_entry_quality_audit_trades.csv) and their 1-minute candles from day 0 to expiry
(data/results/S1_v10_bandcarry_minutes.csv, fetched on GitHub: `fetch_band_minutes carry`). Writes
data/results/S1_fade_target_carry.md and S1_fade_target_carry_trades.csv.
"""
from __future__ import annotations

import bisect
import math

import pandas as pd

from .backtest_s1_v2 import md
from .build import ROOT
from .fade_indicators import V12, net_pct
from .fade_stop_trail import SPLIT, one
from .fastio import read_table
from .stats import clustered_t
from .trade_sheet import CACHE, bhav_sessions

RES = ROOT / "data" / "results"
TARGETS = {"C50": 0.50, "C100": 1.00}
RULES = ("v12", "C50", "C100", "H50")


def carry(m: pd.DataFrame, entry: float, tick: float, target: float, t1: str) -> tuple[float, str, str]:
    """A sell limit at entry x (1 + target), resting from day 0's 09:17 candle to T-1's 15:19: fills at the limit on the
    first candle whose high >= limit + 1 tick; else T-1's last close - 1 tick. (sell, "target" | "T-1", sell date)."""
    lim = math.ceil(round(entry * (1 + target) / tick, 6)) * tick
    x = m[(m["d"] <= t1)]
    x = x.iloc[int(((x["d"] == x["d"].iloc[0]) & (x["t"] < "09:17")).sum()):]
    hit = x[x["h"] >= lim + tick - 1e-9]
    if not hit.empty:
        return round(lim, 2), "target", hit["d"].iloc[0]
    return max(tick, round(float(x["c"].iloc[-1]) - tick, 2)), "T-1", t1


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    t = pd.read_csv(RES / "S1_fade_entry_quality_audit_trades.csv")
    mins = read_table(RES / "S1_v10_bandcarry_minutes.csv")
    mins["d"], mins["t"] = mins["ts"].str[:10], mins["ts"].str[11:16]
    mins = mins[(mins["t"] >= "09:15") & (mins["t"] <= "15:19")]
    by = {k: g.sort_values("ts").reset_index(drop=True) for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
    sessions = bhav_sessions(CACHE)
    rows, dropped = [], []
    for r in t.itertuples(index=False):
        key = (r.symbol, r.day0, r.side, float(r.strike))
        m = by.get(key)
        t1 = sessions[bisect.bisect_left(sessions, r.expiry) - 1]          # the calendar session before expiry
        lab = {"symbol": r.symbol, "day0": r.day0, "side": r.side, "strike": r.strike, "expiry": r.expiry, "T-1": t1}
        if m is None or not (m["d"] == r.day0).any():
            dropped.append({**lab, "why": "no day-0 candles"})
            continue
        if t1 < r.day0 or not (m["d"] == t1).any():
            dropped.append({**lab, "why": f"no candles on T-1 ({t1})"})
            continue
        tick = 0.05 if r.day0 < SPLIT else 0.01
        d0 = m[m["d"] == r.day0].reset_index(drop=True)
        c16 = d0[d0["t"] == "09:16"]
        e = float(r.entry)
        row = {**lab, "half": r.half, "lot": int(r.lot), "entry": e,
               "entry_recomputed": round(float(c16["o"].iloc[0]) + tick, 2) if not c16.empty else None,
               "v12 net % (file)": getattr(r, "_21")}
        v = one(d0, type("R", (), {"lot": r.lot, "side": r.side, "day0": r.day0, "entry_B": e})(), V12)
        row["v12 net %"] = v
        row["v12 net Rs"] = round(v / 100 * e * int(r.lot), 2)
        days = sorted(m.loc[(m["d"] >= r.day0) & (m["d"] <= t1), "d"].unique())
        for name, x in TARGETS.items():
            sell, how, when = carry(m, e, tick, x, t1)
            rs, pct = net_pct(r.side, int(r.lot), e, sell)
            row.update({f"{name} sell": sell, f"{name} how": how, f"{name} on": when, f"{name} net Rs": round(rs, 2),
                        f"{name} net %": round(pct, 3), f"{name} sessions": days.index(when) + 1})
        row["H50 net %"] = round((row["v12 net %"] + row["C50 net %"]) / 2, 3)
        row["H50 net Rs"] = round((row["v12 net Rs"] + row["C50 net Rs"]) / 2, 2)
        rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(dropped)


def stats(g: pd.DataFrame, rule: str, **lab) -> dict:
    x = g[f"{rule} net %"]
    out = {**lab, "rule": rule, "n": len(g), "win %": round((x > 0).mean() * 100, 1), "mean %": round(x.mean(), 2),
           "median %": round(x.median(), 1), "total Rs": round(g[f"{rule} net Rs"].sum()),
           "t": clustered_t(x, g["day0"]), "worst %": round(x.min(), 1)}
    if rule != "v12":
        d = x - g["v12 net %"]
        out.update({"vs v12 mean diff": round(d.mean(), 2), "vs v12 t": clustered_t(d, g["day0"])})
    if rule in TARGETS:
        hit = g[f"{rule} how"] == "target"
        out.update({"filled at target": int(hit.sum()), "mean % at target": round(x[hit].mean(), 1) if hit.any() else None,
                    "sold at T-1": int((~hit).sum()), "mean % at T-1": round(x[~hit].mean(), 1) if (~hit).any() else None,
                    "median sessions held": float(g[f"{rule} sessions"].median())})
    return out


def verdict(t: pd.DataFrame, rule: str) -> tuple[bool, str]:
    a = stats(t, rule)
    halves = {h: (stats(g, rule), g) for h, g in t.groupby("half")}
    checks = [("mean > 0 with t >= 2", a["mean %"] > 0 and (a["t"] or 0) >= 2),
              ("above v12, paired t >= 2", a["vs v12 mean diff"] > 0 and (a["vs v12 t"] or 0) >= 2)]
    for h, (s, g) in halves.items():
        checks.append((f"{h}: mean > 0 and above v12", s["mean %"] > 0 and s["mean %"] > g["v12 net %"].mean()))
    ok = all(c for _, c in checks)
    return ok, "; ".join(f"{n}: {'yes' if c else 'NO'}" for n, c in checks)


def main() -> None:
    t, dropped = build()
    t.to_csv(RES / "S1_fade_target_carry_trades.csv", index=False)
    n0 = len(t) + len(dropped)
    same = (t["v12 net %"] - t["v12 net % (file)"]).abs() <= 0.05
    ent = (t["entry_recomputed"] - t["entry"]).abs() <= 1e-6
    whole = [stats(t, r) for r in RULES]
    halves = [stats(g, r, half=h) for h, g in t.groupby("half") for r in RULES]
    parts = ["# S1 fade · carry with a profit-target sell, held to T-1\n",
             "Pre-registered: strategies/S1_fade_target_carry.md (4df933e7, before the candles were fetched). Numbers only; "
             "nothing live changes. Real charges both legs, one lot. Net % of the premium paid.\n",
             f"## Data\n\n{len(t)} of {n0} trades complete ({len(t) / n0 * 100:.1f} %; the bar is 90 %). T-1 = the trading-calendar "
             f"session before expiry (bhavcopy calendar), and the trade needs candles on day 0 and on that day. Checks: v12 recomputed "
             f"equals the file's v12 net % (± 0.05) on {same.mean() * 100:.1f} % of trades (bar 95 %); the 09:16 open + 1 tick equals "
             f"the file's entry on {ent.mean() * 100:.1f} %.\n"]
    if len(dropped):
        parts.append("Dropped:\n\n" + md(dropped.groupby("why").size().rename("trades").reset_index()) + "\n")
    parts += ["## Whole sample\n\n" + md(pd.DataFrame(whole)) + "\n", "## Halves (train before 2025-11-03, test from it)\n\n"
              + md(pd.DataFrame(halves)) + "\n", "## Verdict (pre-registered bar)\n"]
    data_ok = len(t) / n0 >= 0.90 and same.mean() >= 0.95
    for r in ("C50", "C100", "H50"):
        ok, why = verdict(t, r)
        tag = "" if r == "C50" else " (secondary)"
        parts.append(f"- **{r}{tag}: {'PASS' if ok and data_ok else 'no verdict (data)' if not data_ok else 'FAIL'}** — {why}")
    parts.append("\nH50 needs two lots live (half by v12, half carried); only 17 % of these trades fit two lots in ₹8,000, so a pass "
                 "would need a ₹16,000 cap per signal. A pass on C50 / C100 / H50 only justifies a paper shadow record (the user's call); "
                 "the idea came from looking at this data's max up, so a pass is weaker than an out-of-sample one.")
    (RES / "S1_fade_target_carry.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
    print("\n".join(parts).encode("ascii", "replace").decode())        # Windows consoles: the Rs sign is not cp1252


if __name__ == "__main__":
    main()
