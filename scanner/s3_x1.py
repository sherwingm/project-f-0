"""S3 X1: NIFTY expiry-day option buy (strategies/S3_X1_expiry_day_buy.md), on daily bhavcopy prices.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_x1 --design   # 2024-10 → 2026-10 grid (in-sample)
    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_x1 --run      # the test, 2022-01 → 2024-09, once

Daily bhavcopy rows (options_daily, back to 2018) make a test before Oct 2024 possible, where no option minutes exist.
Entries are at a price that really traded (the previous session's close, or the expiry day's open), and every later
price of the expiry day comes after the entry, so a sell order resting at a target is filled once the day's high
reaches it (at the open when the day opens above it). A stop cannot be judged from daily prices (the low may come
before or after the high), so there is none.
"""
from __future__ import annotations

import argparse
from datetime import date
from functools import lru_cache

import pandas as pd

from index_data import load as L
from scanner.s3_d6_d7 import lot_for
from scanner.s3_p1 import t_stat
from scanner.s3_pods import RES
from server import charges

PAGE = "strategies/S3_X1_expiry_day_buy.md"
SLIP = 0.01                      # 1 % each way: the close and the open are busy, far strikes are thin
OFFSETS, TARGETS = (0, 1, 2, 3, 4), (0.5, 1.0, 2.0, 3.0, None)
DESIGN = (date(2024, 10, 1), date(2026, 10, 30))
TEST = (date(2022, 1, 3), date(2024, 9, 30))
HALVES = ((date(2022, 1, 3), date(2023, 5, 31)), (date(2023, 6, 1), date(2024, 9, 30)))
STOP = 0.5                                                      # the user, 2026-11-03: "Keep a 50% SL"
PRIMARY = ("overnight", "PE", 0, 2.0, STOP)                     # entry, side, strikes out, target, stop
NEIGHBOURS = [("overnight", "PE", 0, 1.0, STOP), ("overnight", "PE", 0, 3.0, STOP), ("overnight", "PE", 1, 2.0, STOP)]
SIDE = [("overnight", "CE", 0, 2.0, STOP), ("open", "PE", 0, 2.0, STOP), ("overnight", "PE", 0, None, STOP),
        ("overnight", "PE", 0, 2.0, None)]


@lru_cache(maxsize=None)
def _month(ym: str) -> pd.DataFrame:
    p = L._store() / "options_daily" / "NIFTY" / f"{ym}.parquet"
    if not p.exists():
        return pd.DataFrame()
    d = pd.read_parquet(p)
    d = d[d["OptnTp"].isin(["CE", "PE"])].copy()
    d["TradDt"], d["XpryDt"] = (pd.to_datetime(d[c]).dt.date for c in ("TradDt", "XpryDt"))
    return d


def _rows(day: date, expiry: date) -> pd.DataFrame:
    d = _month(f"{day:%Y-%m}")
    return d[(d["TradDt"] == day) & (d["XpryDt"] == expiry)] if len(d) else d


def expiry_days(window) -> list[date]:
    """Sessions on which a NIFTY option expires and trades (from the bhavcopy itself)."""
    out = set()
    for m in pd.period_range(window[0], window[1], freq="M"):
        d = _month(str(m))
        if len(d):
            out |= set(d.loc[d["TradDt"] == d["XpryDt"], "TradDt"])
    return sorted(x for x in out if window[0] <= x <= window[1])


def prev_session(day: date) -> date | None:
    for m in (pd.Period(day, "M"), pd.Period(day, "M") - 1):
        d = _month(str(m))
        if len(d):
            s = d.loc[d["TradDt"] < day, "TradDt"]
            if len(s):
                return s.max()
    return None


def _spot(day: date, which: str) -> float | None:
    sp = L.spot_1m(day, day, "NIFTY50")
    return None if sp.empty else float(sp["open"].iloc[0] if which == "open" else sp["close"].iloc[-1])


def cell_name(c) -> str:
    pct = lambda v: "none" if v is None else f"{int(v * 100)} %"
    stop = c[4] if len(c) > 4 else None
    return f"{c[0]} · {c[1]} · {c[2]} out · target {pct(c[3])}" + (f" · stop {pct(stop)}" if stop else "")


def _exit(entry, fill, op, hi, lo, cl, target, stop, stop_first: bool):
    """The expiry-day exit price and why. Daily rows cannot say whether the low or the high came first, so a day that
    touched both is resolved by stop_first (True: the stop, the worst case; False: the target)."""
    T = None if target is None else fill * (1 + target)
    S = None if stop is None else fill * (1 - stop)
    if entry == "overnight":                                       # the day's first price can jump past either order
        if T is not None and op >= T:
            return max(T, op * (1 - SLIP)), "gap target"
        if S is not None and op <= S:
            return op * (1 - SLIP), "gap stop"
    hit_t, hit_s = T is not None and hi >= T, S is not None and lo <= S
    if hit_s and (stop_first or not hit_t):
        return S * (1 - SLIP), "stop"
    if hit_t:
        return T, "target"
    return cl * (1 - SLIP), "close"


def trade(entry: str, ex: date, opt: str, offset: int, target: float | None, stop: float | None = None) -> dict:
    """One lot. entry 'overnight': the previous session's close, strike from its last spot minute; 'open': the expiry
    day's open, strike from its first spot minute. Out at the stop (the day's low at fill × (1 − stop)), the target
    (the day's high at fill × (1 + target)), the open when it is already past either, or the expiry day's close. A day
    that touched both counts as the stop (worst case); the target-first result is kept as net_pct_best."""
    d0 = prev_session(ex) if entry == "overnight" else ex
    s = _spot(d0, "close" if entry == "overnight" else "open") if d0 else None
    if s is None:
        return {"skip": "no spot"}
    k = round(s / 50) * 50 + (50 * offset if opt == "CE" else -50 * offset)
    r0, r1 = _rows(d0, ex), _rows(ex, ex)
    r0, r1 = r0[(r0["StrkPric"] == k) & (r0["OptnTp"] == opt)], r1[(r1["StrkPric"] == k) & (r1["OptnTp"] == opt)]
    if r0.empty or r1.empty:
        return {"skip": f"no {k:.0f} {opt} row"}
    px0 = r0["ClsPric"].iloc[0] if entry == "overnight" else r0["OpnPric"].iloc[0]
    if not px0 or px0 <= 0 or r0["TtlTradgVol"].iloc[0] <= 0:
        return {"skip": f"{k:.0f} {opt} did not trade"}
    fill = px0 * (1 + SLIP)
    op, hi, lo, cl = (float(r1[c].iloc[0]) for c in ("OpnPric", "HghPric", "LwPric", "ClsPric"))
    lot = lot_for(d0, ex)                       # the bhavcopy lot from 2024-07; before it NSE's 50, then 25 from 2024-04-26

    def net_of(out):
        fees = charges.leg(opt, "BUY", lot, fill)["total"] + charges.leg(opt, "SELL", lot, out)["total"]
        return (out - fill) * lot - fees, fees

    out, why = _exit(entry, fill, op, hi, lo, cl, target, stop, True)
    out_b, why_b = _exit(entry, fill, op, hi, lo, cl, target, stop, False)
    (net, fees), (net_b, _) = net_of(out), net_of(out_b)
    return {"skip": "", "entry_day": d0, "spot": s, "strike": k, "paid": round(fill, 2), "exit": round(out, 2),
            "why": why, "hit": why in ("target", "gap target"), "both_touched": why != why_b,
            "hit_best": why_b in ("target", "gap target"),
            "max_up_pct": (hi / fill - 1) * 100, "lot": lot, "fees_rs": round(fees, 2),
            "net_rs": round(net, 2), "net_pct": net / (fill * lot) * 100,
            "net_rs_best": round(net_b, 2), "net_pct_best": net_b / (fill * lot) * 100}


def collect(window, cells) -> pd.DataFrame:
    rows = []
    for ex in expiry_days(window):
        for c in cells:
            rows.append({"day": ex, "cell": cell_name(c), **trade(c[0], ex, *c[1:])})
    return pd.DataFrame(rows)


HEAD = ["| Cell | Trades | Paid (median ₹) | Mean net | Median | t | Won | Target hit | Max up mean | Max up median | "
        "≥ +100 % | Total ₹ |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]


def _line(name, g) -> str:
    x, mu = g["net_pct"], g["max_up_pct"]
    return (f"| {name} | {len(g)} | {g['paid'].median():.1f} | {x.mean():+.1f} % | {x.median():+.1f} % | {t_stat(x):.2f} | "
            f"{(x > 0).mean() * 100:.0f} % | {g['hit'].mean() * 100:.0f} % | {mu.mean():+.0f} % | {mu.median():+.0f} % | "
            f"{(mu >= 100).mean() * 100:.0f} % | {g['net_rs'].sum():,.0f} |")


def design() -> None:
    cells = [(en, opt, o, tg) for en in ("overnight", "open") for opt in ("CE", "PE") for o in OFFSETS for tg in TARGETS]
    df = collect(DESIGN, cells)
    df.to_csv(RES / "S3_X1_design_trades.csv", index=False)
    ok = df[df["skip"] == ""]
    lines = [f"# S3 X1 design grid · {DESIGN[0]} → {DESIGN[1]} (in-sample, used to pick the primary)", "",
             f"Expiry days: {df['day'].nunique()}; skipped rows: {len(df) - len(ok)}. Net = after 1 % slippage each way "
             "and charges, % of the premium paid, 1 lot. Max up = the expiry day's high over the price paid.", ""] + HEAD
    lines += [_line(cell_name(c), ok[ok["cell"] == cell_name(c)]) for c in cells]
    (RES / "S3_X1_design.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def run() -> dict:
    df = collect(TEST, [PRIMARY, *NEIGHBOURS, *SIDE])
    df.to_csv(RES / "S3_X1_trades.csv", index=False)
    ok = df[df["skip"] == ""]
    p = ok[ok["cell"] == cell_name(PRIMARY)]
    x = p["net_pct"]
    dd = pd.to_datetime(p["day"]).dt.date
    halves = [p[(dd >= a) & (dd <= b)]["net_pct"] for a, b in HALVES]
    month = p.groupby(pd.to_datetime(p["day"]).dt.to_period("M"))["net_rs"].sum().mean()
    checks = [("at least 100 trades", len(p) >= 100), ("mean > 0", x.mean() > 0), ("t ≥ 2", t_stat(x) >= 2),
              ("both halves positive", all(h.mean() > 0 for h in halves)),
              ("worst trade (₹) smaller than the average month's gain", month > 0 and -p["net_rs"].min() < month),
              ("neighbours positive", all(ok[ok["cell"] == cell_name(c)]["net_pct"].mean() > 0 for c in NEIGHBOURS))]
    passed = all(c for _, c in checks)
    sk = df[df["skip"] != ""]
    lines = [f"# S3 X1 · NIFTY expiry-day ATM put, bought the evening before · {TEST[0]} → {TEST[1]}", "",
             f"Pre-registered: `{PAGE}`. Daily bhavcopy prices, 1 lot, 1 % slippage each way, real charges.", "",
             f"## Verdict: **{'PASS' if passed else 'FAIL'}**", ""] + [f"- {'✔' if c else '✘'} {n}" for n, c in checks]
    lines += ["", "- Halves: " + " / ".join(f"{a} → {b}: {h.mean():+.1f} % ({len(h)})" for (a, b), h in zip(HALVES, halves)),
              f"- Average month (primary): ₹{month:,.0f}; worst trade ₹{p['net_rs'].min():,.0f}",
              f"- Expiry days: {df['day'].nunique()}; skipped rows: {len(sk)}"
              + (" (" + "; ".join(f"{r.day} {r.cell}: {r.skip}" for r in sk.itertuples()) + ")" if len(sk) else ""),
              ""] + HEAD
    for tag, c in [("primary (gate)", PRIMARY), *(("neighbour (gate)", c) for c in NEIGHBOURS), *(("side", c) for c in SIDE)]:
        lines.append(_line(f"{tag}: {cell_name(c)}", ok[ok["cell"] == cell_name(c)]))
    best = p.assign(net_pct=p["net_pct_best"], net_rs=p["net_rs_best"], hit=p["hit_best"])
    lines += ["", f"Daily prices cannot show whether the low or the high came first. {p['both_touched'].sum()} of {len(p)} "
              "primary days touched both the stop and the target; the gate counts them as stopped (worst case). "
              "Target first instead (best case, not the gate):", "", *HEAD, _line("primary, target first", best), "",
              "Primary exits: " + ", ".join(f"{k} {v}" for k, v in p["why"].value_counts().items())]
    lines += ["", "| Year | Trades | Mean net | Max up median | ≥ +100 % | Total ₹ |", "|---|---|---|---|---|---|"]
    for y, g in p.groupby(pd.to_datetime(p["day"]).dt.year):
        lines.append(f"| {y} | {len(g)} | {g['net_pct'].mean():+.1f} % | {g['max_up_pct'].median():+.0f} % | "
                     f"{(g['max_up_pct'] >= 100).mean() * 100:.0f} % | {g['net_rs'].sum():,.0f} |")
    (RES / "S3_X1_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return {"pass": passed, "n": len(p), "mean": x.mean(), "t": t_stat(x)}


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
