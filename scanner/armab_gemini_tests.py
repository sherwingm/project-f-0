"""S1 Arm A / Arm B: the Gemini-handoff hypotheses on 1-minute candles (numbers only).

    python -m scanner.armab_gemini_tests a01 b01        # 15:20 entry; underlying stop
    python -m scanner.armab_gemini_tests a02            # needs the fetched near-expiry minutes (S1_v10_bandd2_minutes.csv)

Pre-registered: strategies/S1_armab_gemini_hypotheses.md. Baseline = S1_armab_minutes_trades.csv, variant LIVE-CLOSE (reproduced here and checked).
Arm A and Arm B are always separate. Holm over the three hypotheses is computed per arm from the three p-values (see the note in the result file).
"""
from __future__ import annotations

import math
import sys

import pandas as pd

from . import backtest_s1_v4 as v4
from . import backtest_s1_v7 as v7
from .armab_minutes import calendar, iso
from .backtest_s1_v2 import md
from .build import ROOT
from .equity import load_symbol
from .option_engine import TICK
from .stats import clustered_t

RES = ROOT / "data" / "results"
HALF = "2025-10-01"


def vwap_to_1520(g: pd.DataFrame) -> float | None:
    x = g[g["t"] <= "15:20"]
    v = x["volume"].astype(float)
    if x.empty:
        return None
    if v.sum() <= 0:
        return float(x["c"].iloc[-1])
    typ = (x["h"] + x["l"] + x["c"]) / 3.0
    return float((typ * v).sum() / v.sum())


def simulate(days: dict, cal: list[str], entry_day: str, expiry: str, entry: str = "open16", stop: str = "option50",
             und_close: dict | None = None, day0_low: float | None = None):
    """One trade. entry: open16 | vwap1520. stop: option50 | underlying. Returns a dict or a reason string."""
    ci = {d: i for i, d in enumerate(cal)}
    if entry_day not in days or expiry not in ci or entry_day not in ci:
        return "no_data"
    g0 = days[entry_day]
    if entry == "open16":
        c0 = g0[g0["t"] == "09:16"]
        if c0.empty:
            return "no_0916_candle"
        e = round(float(c0["o"].iloc[0]) + TICK, 2)
    else:
        w = vwap_to_1520(g0)
        if w is None:
            return "no_candles"
        e = round(w + TICK, 2)
    best, stall = e, 0
    for d in cal[ci[entry_day]: ci[expiry] + 1]:
        g = days.get(d)
        if g is None or g.empty:
            return "missing_session"
        to_exp = ci[expiry] - ci[d]
        close = float(g["c"].iloc[-1])
        age = ci[d] - ci[entry_day]
        if stop == "option50":
            best, stall, reason = v7.exit_step(close, e, best, stall, to_exp, v7.STOP)
        else:
            best, stall, reason = v7.exit_step(close, e, best, stall, to_exp, None)
            u = (und_close or {}).get(d)
            if reason is None and u is not None and day0_low is not None and u < day0_low:
                reason = "0_ustop"
        if reason:
            return dict(entry=e, exit_price=max(0.0, round(close - TICK, 2)), exit_date=d, reason=reason, held=age)
    return "no_exit_in_data"


def load() -> tuple[dict, list[str], pd.DataFrame]:
    mins = pd.read_csv(RES / "S1_v10_bandarmab2_minutes.csv")
    mins["dt"] = pd.to_datetime(mins["ts"])
    mins["d"], mins["t"] = mins["dt"].dt.strftime("%Y-%m-%d"), mins["dt"].dt.strftime("%H:%M")
    mins = mins.sort_values("dt")
    path = {(s, d0, float(k)): {d: x for d, x in g.groupby("d")} for (s, d0, k), g in mins.groupby(["symbol", "day0", "strike"])}
    tr = pd.read_csv(RES / "S1_armb_hold_and_nifty_trades.csv")
    tr = tr[(tr.variant == "LIVE") & tr.arm.isin(["A", "B"]) & tr.excluded.isna() & (tr.expiry >= "2024-10-01")].drop_duplicates(["arm", "symbol", "entry_date"])
    return path, [iso(x) for x in calendar()], tr


def net_pct(res: dict, lot: int, cat: str) -> tuple[float, float]:
    slip = v4.SLIPPAGE.get(cat, v4.SLIPPAGE["unknown"])
    _, _, net = v4.net_of(res["entry"], res["exit_price"], lot, slip)
    return net, net / (res["entry"] * lot) * 100


def band_ok(e: float, lot: int) -> bool:
    return e >= 2 and 600 <= e * lot <= 8000


def stat_line(x: pd.DataFrame, col: str) -> dict:
    x = x.sort_values("entry_date")
    p = x["net_" + col]
    w, l = p[p > 0].sum(), -p[p <= 0].sum()
    eq = p.cumsum()
    return {"n": len(x), "win %": round((x["pct_" + col] > 0).mean() * 100, 1), "mean %": round(x["pct_" + col].mean(), 1),
            "median %": round(x["pct_" + col].median(), 1), "total Rs": round(p.sum()), "PF": round(w / l, 2) if l else None,
            "max DD Rs": round((eq - eq.cummax()).min())}


def paired(df: pd.DataFrame) -> dict:
    d = df["pct_v"] - df["pct_b"]
    t = clustered_t(d.values, df["entry_date"].values) if len(d) > 1 else None
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2)))) if t is not None else None
    h1, h2 = d[df["entry_date"] < HALF], d[df["entry_date"] >= HALF]
    return {"pairs": len(d), "mean diff %": round(d.mean(), 2), "t": None if t is None else round(t, 2), "p": None if p is None else round(p, 4),
            "half 1 diff": None if h1.empty else round(h1.mean(), 2), "n1": len(h1), "half 2 diff": None if h2.empty else round(h2.mean(), 2), "n2": len(h2)}


def run(kind: str) -> pd.DataFrame:
    path, cal, tr = load()
    base = pd.read_csv(RES / "S1_armab_minutes_trades.csv")
    base = base[base.variant == "LIVE-CLOSE"].set_index(["arm", "symbol", "entry_date"])
    rows = []
    for r in tr.itertuples():
        days = path.get((r.symbol, r.signal_date, float(r.strike)))
        if days is None or (r.arm, r.symbol, r.entry_date) not in base.index:
            continue
        b = base.loc[(r.arm, r.symbol, r.entry_date)]
        if isinstance(b, pd.DataFrame):
            b = b.iloc[0]
        rb = simulate(days, cal, r.entry_date, r.expiry)
        if not isinstance(rb, dict):
            continue
        nb, pb = net_pct(rb, r.lot, r.category)
        rep_ok = bool(abs(pb - b.net_pct) < 0.01)
        if kind == "a01":
            rv = simulate(days, cal, r.entry_date, r.expiry, entry="vwap1520")
        else:
            try:
                f = load_symbol(r.symbol, ROOT / "data" / "eod2")
                f.index = f.index.strftime("%Y-%m-%d")
                uc = f["Close"].to_dict()
                low0 = float(f.loc[r.signal_date, "Low"])
            except Exception:
                continue
            rv = simulate(days, cal, r.entry_date, r.expiry, stop="underlying", und_close=uc, day0_low=low0)
        if not isinstance(rv, dict) or (kind == "a01" and not band_ok(rv["entry"], r.lot)):
            rows.append(dict(arm=r.arm, why=rv if isinstance(rv, str) else "outside price/lot band"))
            continue
        nv, pv = net_pct(rv, r.lot, r.category)
        rows.append(dict(arm=r.arm, symbol=r.symbol, entry_date=r.entry_date, net_b=nb, pct_b=pb, net_v=nv, pct_v=pv, reason_b=rb["reason"],
                         reason_v=rv["reason"], held_b=rb["held"], held_v=rv["held"], rep_ok=rep_ok, entry_b=rb["entry"], entry_v=rv["entry"], why=""))
    df = pd.DataFrame(rows)
    df.to_csv(RES / f"S1_armab_gemini_{kind}_trades.csv", index=False)
    return df


def report(kind: str, df: pd.DataFrame) -> str:
    title = {"a01": "HYP-A-01 · entry at the 15:20 average price (day +1) instead of the 09:16 open",
             "b01": "HYP-B-01 · underlying-stock stop (close below the day-0 low) instead of the 50 % option stop"}[kind]
    out = [f"## {title}\n"]
    for arm in ("A", "B"):
        d = df[(df.arm == arm) & (df.why == "")]
        dropped = df[(df.arm == arm) & (df.why != "")]
        out.append(f"### Arm {arm}: {len(d)} paired trades (dropped {len(dropped)}: {dict(dropped.why.value_counts())})\n")
        out.append(f"Baseline reproduced exactly on {int(d.rep_ok.astype(bool).sum())} of {len(d)} trades.\n")
        tab = pd.DataFrame([{"rule": "baseline (09:16 entry, 50 % option stop)", **stat_line(d, "b")}, {"rule": "variant", **stat_line(d, "v")}])
        out.append(md(tab) + "\n")
        out.append("Paired difference (variant minus baseline):\n\n" + md(pd.DataFrame([paired(d)])) + "\n")
        out.append(f"Exit mix baseline {dict(d.reason_b.value_counts())}; variant {dict(d.reason_v.value_counts())}; mean sessions held baseline {d.held_b.mean():.1f}, variant {d.held_v.mean():.1f}.\n")
        if kind == "b01":
            s = d[d.reason_b == "0_stop"]
            out.append(f"On the baseline's {len(s)} stopped trades alone: baseline mean {s.pct_b.mean():.1f} %, variant mean {s.pct_v.mean():.1f} %, paired difference {(s.pct_v - s.pct_b).mean():+.1f} points.\n")
    return "\n".join(out)


def run_a02() -> pd.DataFrame:
    """HYP-A-02: the near-expiry current-monthly pick (live rule, >= 2 sessions) against the baseline's next-monthly pick for the same signal."""
    mins = pd.read_csv(RES / "S1_v10_bandd2_minutes.csv")
    mins["dt"] = pd.to_datetime(mins["ts"])
    mins["d"], mins["t"] = mins["dt"].dt.strftime("%Y-%m-%d"), mins["dt"].dt.strftime("%H:%M")
    mins = mins.sort_values("dt")
    path = {(s, d0, float(k)): {d: x for d, x in g.groupby("d")} for (s, d0, k), g in mins.groupby(["symbol", "day0", "strike"])}
    cal = [iso(x) for x in calendar()]
    picks = pd.read_csv(RES / "S1_a02_picks.csv")
    base = pd.read_csv(RES / "S1_armab_minutes_trades.csv")
    base = base[base.variant == "LIVE-CLOSE"].set_index(["arm", "symbol", "entry_date"])
    rows = []
    for r in picks.itertuples():
        days = path.get((r.symbol, r.signal_date, float(r.strike)))
        rec = dict(arm=r.arm, symbol=r.symbol, entry_date=r.entry_date, sessions_left=r.sessions_left)
        if days is None:
            rows.append({**rec, "why": "no candles"})
            continue
        rv = simulate(days, cal, r.entry_date, r.expiry)
        if not isinstance(rv, dict):
            rows.append({**rec, "why": rv})
            continue
        nv, pv = net_pct(rv, r.lot, r.category)
        paired_base = (r.arm, r.symbol, r.entry_date) in base.index
        rec.update(net_v=nv, pct_v=pv, reason_v=rv["reason"], held_v=rv["held"], why="", paired=paired_base)
        if paired_base:
            b = base.loc[(r.arm, r.symbol, r.entry_date)]
            b = b.iloc[0] if isinstance(b, pd.DataFrame) else b
            rec.update(net_b=float(b.net), pct_b=float(b.net_pct), reason_b=b.exit_reason, held_b=float(b.held))
        rows.append(rec)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "S1_armab_gemini_a02_trades.csv", index=False)
    return df


def report_a02(df: pd.DataFrame) -> str:
    out = ["## HYP-A-02 · the live 2-session expiry rule (current monthly down to 2 sessions) against the tested 10-session rule (next monthly), same signals, 09:16 entry\n"]
    for arm in ("A", "B"):
        x = df[df.arm == arm]
        ok = x[x.why == ""]
        pr = ok[ok.paired == True].copy()  # noqa: E712
        out.append(f"### Arm {arm}: {len(x)} near-expiry picks, {len(ok)} with minute candles and a 09:16 trade (dropped: {dict(x[x.why != ''].why.value_counts())}); "
                   f"{len(pr)} paired with the baseline's trade for the same signal, {len(ok) - len(pr)} have no baseline trade\n")
        if len(pr) > 1:
            tab = pd.DataFrame([{"rule": "baseline (next monthly, >= 10 sessions)", **stat_line(pr, "b")},
                                {"rule": "variant (current monthly, >= 2 sessions)", **stat_line(pr, "v")}])
            out.append(md(tab) + "\n")
            out.append("Paired difference (variant minus baseline):\n\n" + md(pd.DataFrame([paired(pr)])) + "\n")
            out.append(f"Exit mix baseline {dict(pr.reason_b.value_counts())}; variant {dict(pr.reason_v.value_counts())}; mean sessions held baseline {pr.held_b.mean():.1f}, "
                       f"variant {pr.held_v.mean():.1f}; mean sessions to expiry at day 0 {pr.sessions_left.mean():.1f}.\n")
        un = ok[ok.paired != True]  # noqa: E712
        if len(un):
            out.append(f"Picks the baseline did not trade (descriptive only, no pair): n {len(un)}, win {(un.pct_v > 0).mean() * 100:.0f} %, mean {un.pct_v.mean():.1f} %, "
                       f"median {un.pct_v.median():.1f} %, total Rs {un.net_v.sum():,.0f}.\n")
    return "\n".join(out)


def main() -> None:
    kinds = sys.argv[1:] or ["a01", "b01"]
    if kinds == ["a02"]:
        rep = ("# S1 Arm A and Arm B · HYP-A-02 (minute candles)\n\nNumbers only. Pre-registered: strategies/S1_armab_gemini_hypotheses.md. "
               "Arm A and Arm B separate.\n\n" + report_a02(run_a02()))
        (RES / "S1_armab_gemini_a02.md").write_text(rep, encoding="utf-8")
        print(rep)
        return
    text = ["# S1 Arm A and Arm B · Gemini-handoff hypotheses (minute candles)\n\nNumbers only. Pre-registered: strategies/S1_armab_gemini_hypotheses.md. "
            "Arm A and Arm B separate. Holm over the three hypotheses is applied when all three are in.\n"]
    for k in kinds:
        text.append(report(k, run(k)))
    rep = "\n".join(text)
    (RES / f"S1_armab_gemini_{'_'.join(kinds)}.md").write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
