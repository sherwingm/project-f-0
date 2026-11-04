"""S3 V1: buy the NIFTY ATM straddle only when options are cheap: implied vol (IV) at entry below NIFTY's realized
vol (RV) of the sessions before.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_v1 --design   # 2024-10 → 2025-09, picks the rule
    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_v1 --run      # 2025-10 → 2026-10, once

Why: an option buyer pays the implied vol and earns the vol NIFTY then makes. Sellers are usually paid a premium for
the risk (IV above the RV that follows), so a buyer loses on an average day. The only days a buyer starts ahead are
those where IV is below the vol NIFTY is actually making. Every input is known at the entry minute: IV from the entry
minute's ATM call and put (Black-Scholes on spot, `scanner.fade_preopen_entry.iv`), RV from 5-minute NIFTY returns
of the sessions before the entry day plus their overnight gaps.
"""
from __future__ import annotations

import argparse
import math
from datetime import date
from functools import lru_cache

import numpy as np
import pandas as pd

from index_data import load as L
from scanner import s3_engine as E
from scanner.fade_preopen_entry import iv
from scanner.s3_buy_maxup import legs_of, max_up
from scanner.s3_engine import Leg, Spec
from scanner.s3_p1 import t_stat
from scanner.s3_p4 import expiry_after
from scanner.s3_pods import RES
from scanner.s3_regime import trading_days, years_to

DESIGN = (date(2024, 10, 1), date(2025, 9, 30))
TEST = (date(2025, 10, 1), date(2026, 10, 30))
ENTRIES = ((9, 45), (14, 45))
HOLDS = ("next", "expiry")                       # out at 15:15 of the next session, or of the expiry day
RV_DAYS = (5, 10)
BARS = 5                                         # minutes per return in the realized-vol sum


@lru_cache(maxsize=1)
def day_var() -> pd.Series:
    """Each session's realized variance: the sum of squared 5-minute log returns, plus the squared overnight gap."""
    s = L.spot_1m(date(2024, 6, 1), date(2026, 12, 31), "NIFTY50")
    s["d"] = s["timestamp"].dt.date
    s = s[s.groupby("d")["close"].transform("size") >= 60]
    out = {}
    prev_close = None
    for d, g in s.groupby("d"):
        c = g.set_index("timestamp")["close"].resample(f"{BARS}min").last().dropna()
        r = np.diff(np.log(c.to_numpy()))
        v = float((r ** 2).sum())
        if prev_close:
            v += math.log(g["open"].iloc[0] / prev_close) ** 2
        out[d] = v
        prev_close = float(g["close"].iloc[-1])
    return pd.Series(out)


def rv(day: date, n: int) -> float | None:
    """Annualised realized vol of the n sessions before `day` (none of `day` itself)."""
    v = day_var()
    before = v[v.index < day].iloc[-n:]
    return math.sqrt(252 * before.mean()) if len(before) == n else None


def atm_iv(chain: pd.DataFrame, s: float, at: pd.Timestamp, expiry: date) -> float | None:
    k = round(s / 50) * 50
    t = years_to(at, expiry)
    vs = []
    for opt in ("CE", "PE"):
        px = L.price_at(chain, k, opt, at, stale=E.ENTRY_STALE)
        v = iv(opt, px, s, k, t) if px else None
        if not v:
            return None
        vs.append(v)
    return sum(vs) / 2


def move_ratio(v: float, at: pd.Timestamp, expiry: date, dte: int, n: int) -> float | None:
    """The move to expiry the price implies (IV² × calendar time) over the move at the last n sessions' pace (their
    mean variance × the sessions left: the rest of today plus every session up to and including the expiry day),
    as a ratio of standard deviations. Below 1: the options are priced for less movement than NIFTY is making."""
    var = day_var()
    before = var[var.index < at.date()].iloc[-n:]
    if len(before) < n:
        return None
    left_today = max((L.at(at.date(), 15, 30) - at).total_seconds() / (375 * 60), 0.0)
    return math.sqrt(v * v * years_to(at, expiry) / (before.mean() * (left_today + dte)))


def next_session(day: date) -> date | None:
    td = trading_days()
    later = [x for x in td if x > day]
    return later[0] if later else None


def trade(day: date, entry: tuple, hold: str, cost_mult: float = 1.0) -> dict:
    ex = expiry_after(day)
    if ex is None:
        return {"day": day, "skip": "no expiry"}
    out_day = ex if hold == "expiry" else min(next_session(day) or ex, ex)
    sessions = [d for d in L.trade_days("NIFTY", ex) if d >= day]
    dte = len([d for d in sessions if d > day])
    s = E.spot_at(day, *entry)
    if s is None:
        return {"day": day, "expiry": ex, "skip": "no spot"}
    chain = E.chain_between("NIFTY", ex, day, out_day)
    at = L.at(day, *entry)
    v = atm_iv(chain[chain["timestamp"].dt.date == day], s, at, ex)
    row = {"day": day, "expiry": ex, "dte": dte, "entry": f"{entry[0]:02d}:{entry[1]:02d}", "hold": hold,
           "iv": v, **{f"rv{n}": rv(day, n) for n in RV_DAYS},
           **{f"ratio{n}": (move_ratio(v, at, ex, dte, n) if v else None) for n in RV_DAYS}}
    if v is None:
        return {**row, "skip": "no IV"}
    spec = Spec("V1", [Leg("BUY", "CE", 0), Leg("BUY", "PE", 0)], entry=entry, exit=(15, 15), cost_mult=cost_mult)
    t = E.simulate(chain, s, day, spec, L.lot_on(day, "NIFTY", ex), exit_day=out_day)
    if t.get("skip"):
        return {**row, "skip": t["skip"]}
    mu = max_up(chain, legs_of(t["legs"]), at, L.at(out_day, 15, 15), L.at(out_day, 15, 29))
    return {**row, "skip": "", "out_day": out_day, "premium": t["premium"], "net_rs": t["net_rs"],
            "net_pct": t["net_pct_premium"], "reason": t["reason"], "legs": t["legs"], **mu}


def collect(window, entries=ENTRIES, holds=HOLDS) -> pd.DataFrame:
    days = [d for d in trading_days() if window[0] <= d <= window[1]]
    rows = [trade(d, e, h) for d in days for e in entries for h in holds]
    return pd.DataFrame(rows)


HEAD = ["| Group | Trades | Mean net | Median | t | Won | Max up mean | Max up median | ≥ +50 % | ≥ +100 % | Total ₹ |",
        "|---|---|---|---|---|---|---|---|---|---|---|"]


def line(name, g) -> str:
    if not len(g):
        return f"| {name} | 0 | | | | | | | | | |"
    x, mu = g["net_pct"], g["max_up_held_pct"]
    return (f"| {name} | {len(g)} | {x.mean():+.1f} % | {x.median():+.1f} % | {t_stat(x):.2f} | {(x > 0).mean() * 100:.0f} % | "
            f"{mu.mean():+.0f} % | {mu.median():+.0f} % | {(mu >= 50).mean() * 100:.0f} % | {(mu >= 100).mean() * 100:.0f} % | "
            f"{g['net_rs'].sum():,.0f} |")


def dte_band(d: int) -> str:
    return str(d) if d < 4 else "4+"


def design() -> None:
    df = collect(DESIGN)
    df.to_csv(RES / "S3_V1_design_trades.csv", index=False)
    ok = df[df["skip"] == ""].copy()
    lines = [f"# S3 V1 design · {DESIGN[0]} → {DESIGN[1]} (in-sample: picks the rule for the test)", "",
             "Long NIFTY ATM straddle (buy call + put), nearest weekly with a session left. Net after slippage and "
             "charges, % of the premium paid, 1 lot. Ratio = the move to expiry the straddle price implies ÷ the move at "
             "the pace of the sessions before (below 1: options priced for less movement than NIFTY has been making). Max up while held.", "",
             f"Rows: {len(df)}; skipped {len(df) - len(ok)} ({df.loc[df['skip'] != '', 'skip'].value_counts().to_dict()})", ""]
    for (e, h), g in ok.groupby(["entry", "hold"]):
        lines += [f"## Entry {e}, out {h}", "", "IV ÷ RV(10) band:", ""] + HEAD
        lines.append(line("all", g))
        for lo, hi in ((0, 0.8), (0.8, 0.9), (0.9, 1.0), (1.0, 1.1), (1.1, 1.25), (1.25, 9)):
            lines.append(line(f"{lo:.2f}–{hi:.2f}", g[(g["ratio10"] >= lo) & (g["ratio10"] < hi)]))
        lines += ["", "IV ÷ RV(5) band:", ""] + HEAD
        for lo, hi in ((0, 0.8), (0.8, 0.9), (0.9, 1.0), (1.0, 1.1), (1.1, 1.25), (1.25, 9)):
            lines.append(line(f"{lo:.2f}–{hi:.2f}", g[(g["ratio5"] >= lo) & (g["ratio5"] < hi)]))
        lines += ["", "Ratio(10) < 0.9, by days to expiry at entry:", ""] + HEAD
        cheap = g[g["ratio10"] < 0.9]
        for b, gb in cheap.groupby(cheap["dte"].map(dte_band)):
            lines.append(line(f"DTE {b}", gb))
        lines.append("")
    (RES / "S3_V1_design.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


PAGE = "strategies/S3_V1_cheap_straddle.md"
HALVES = ((date(2025, 10, 1), date(2026, 3, 31)), (date(2026, 4, 1), date(2026, 10, 30)))
PRIMARY = ("14:45", "ratio10", 1.0)                              # entry, ratio, buy when below; held to expiry
NEIGHBOURS = [("14:45", "ratio10", 0.9), ("14:45", "ratio10", 1.1), ("14:45", "ratio5", 1.0), ("09:45", "ratio10", 1.0)]
EXPENSIVE = 1.1                                                  # the second claim: ratio10 >= 1.1 loses


def clustered_t(g) -> float:
    """t over expiries: trades held to the same expiry overlap, so each expiry's mean counts once."""
    return t_stat(g.groupby("expiry")["net_pct"].mean())


def pick(ok, c):
    e, col, cut = c
    return ok[(ok["entry"] == e) & (ok[col] < cut)]


def run() -> dict:
    df = collect(TEST, holds=("expiry",))
    ok = df[df["skip"] == ""].copy()
    p = pick(ok, PRIMARY)
    x2 = pd.DataFrame([trade(d, (14, 45), "expiry", cost_mult=2.0) for d in p["day"]])
    x2 = x2[x2["skip"] == ""]
    dd = pd.to_datetime(p["day"]).dt.date
    halves = [p[(dd >= a) & (dd <= b)] for a, b in HALVES]
    exp = ok[(ok["entry"] == "14:45") & (ok["ratio10"] >= EXPENSIVE)]
    checks = [("at least 60 trades", len(p) >= 60), ("mean > 0", p["net_pct"].mean() > 0),
              ("t over expiries ≥ 2", clustered_t(p) >= 2), ("both halves positive", all(h["net_pct"].mean() > 0 for h in halves)),
              ("at 2× costs mean > 0", len(x2) > 0 and x2["net_pct"].mean() > 0),
              ("neighbours positive", all(pick(ok, c)["net_pct"].mean() > 0 for c in NEIGHBOURS))]
    passed = all(c for _, c in checks)
    exp_ok = len(exp) >= 30 and exp["net_pct"].mean() < 0 and clustered_t(exp) <= -2
    pd.concat([df.assign(cost="1x"), x2.assign(cost="2x")]).to_csv(RES / "S3_V1_trades.csv", index=False)
    name = lambda c: f"entry {c[0]} · {c[1]} < {c[2]}"
    lines = [f"# S3 V1 · buy the NIFTY ATM straddle when options are cheap · {TEST[0]} → {TEST[1]}", "",
             f"Pre-registered: `{PAGE}`. Held to the expiry day's 15:15. Net after slippage and charges, % of the premium.", "",
             f"## Claim 1, cheap straddles make money: **{'PASS' if passed else 'FAIL'}**", ""]
    lines += [f"- {'✔' if c else '✘'} {n}" for n, c in checks]
    lines += ["", f"- t over expiries {clustered_t(p):.2f} ({p['expiry'].nunique()} expiries); halves "
              + " / ".join(f"{h['net_pct'].mean():+.1f} % ({len(h)})" for h in halves)
              + (f"; 2× costs {x2['net_pct'].mean():+.1f} %" if len(x2) else ""),
              "", f"## Claim 2, expensive straddles (ratio10 ≥ {EXPENSIVE}, 14:45) lose: **{'CONFIRMED' if exp_ok else 'NOT CONFIRMED'}**",
              f"- {len(exp)} trades, {exp['net_pct'].mean():+.1f} %, t over expiries {clustered_t(exp):.2f} "
              "(needs ≥ 30 trades, mean < 0, t ≤ −2)", "", *HEAD, line("primary: " + name(PRIMARY), p)]
    lines += [line("neighbour: " + name(c), pick(ok, c)) for c in NEIGHBOURS]
    lines += [line(f"expensive: entry 14:45 · ratio10 ≥ {EXPENSIVE}", exp), line("every 14:45 day", ok[ok["entry"] == "14:45"]),
              "", "Primary by days to expiry at entry (max up while held):", "", *HEAD]
    lines += [line(f"DTE {b}", g) for b, g in p.groupby(p["dte"].map(dte_band))]
    lines += ["", f"Skipped: {len(df) - len(ok)} ({df.loc[df['skip'] != '', 'skip'].value_counts().to_dict()})"]
    (RES / "S3_V1_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return {"pass": passed, "expensive_confirmed": exp_ok}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.design:
        design()
    elif a.run:
        run()
    else:
        ap.error("--design or --run")
