"""S3 buy pods, run once on 2024-10-01 → 2026-10-28 (DECISIONS.md "S3 · buy-only, tested on 2024 → today"):

    E1  long ATM straddle across a scheduled event        strategies/S3_E1_event_straddle.md
    Q1  long ATM straddle after a quiet spell (squeeze)    strategies/S3_Q1_squeeze_straddle.md
    B1  opening-range breakout + option volume, long ATM  strategies/S3_B1_orb_volume.md
    G1  big-gap follow-through, long ATM                  strategies/S3_G1_gap_follow.md

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_buy4 [E1 Q1 B1 G1]

Writes data/results/S3_<pod>_report.md and S3_<pod>_trades.csv through `scanner.s3_pods.write_report` (the S3 gate).
"""
from __future__ import annotations

import sys
from datetime import date, time, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

from index_data import load as L
from scanner import s3_regime as G
from scanner.s3_engine import Leg, Spec, run_day, spot_at
from scanner.s3_p1 import summary, t_stat, vix_at
from scanner.s3_p4 import expiry_after
from scanner.s3_pods import Pod, write_report

WINDOW = (date(2024, 10, 1), date(2026, 10, 28))
HALVES = ((date(2024, 10, 1), date(2025, 9, 30)), (date(2025, 10, 1), date(2026, 10, 28)))
STEP = 50

# ---------- E1 events (strategies/S3_E1_event_straddle.md) ----------
RBI = [date(2024, 10, 9), date(2024, 12, 6), date(2025, 2, 7), date(2025, 4, 9), date(2025, 6, 6), date(2025, 8, 6),
       date(2025, 10, 1), date(2025, 12, 5), date(2026, 2, 6), date(2026, 4, 8), date(2026, 6, 5), date(2026, 8, 5),
       date(2026, 10, 7)]
BUDGET = [date(2025, 2, 1), date(2026, 2, 1)]
FOMC_US = [date(2024, 11, 7), date(2024, 12, 18), date(2025, 1, 29), date(2025, 3, 19), date(2025, 5, 7),
           date(2025, 6, 18), date(2025, 7, 30), date(2025, 9, 17), date(2025, 10, 29), date(2025, 12, 10),
           date(2026, 1, 28), date(2026, 3, 18), date(2026, 4, 29), date(2026, 6, 17), date(2026, 7, 29),
           date(2026, 9, 16)]
US_ELECTION = [date(2024, 11, 6)]


def sessions() -> list[date]:
    return G.trading_days()


@lru_cache(maxsize=None)
def _days_of(expiry: date) -> frozenset:
    return frozenset(L.trade_days("NIFTY", expiry))


def expiry_covering(entry: date, exit_day: date) -> date | None:
    """The nearest NIFTY expiry strictly after the exit session with chain files on the entry and exit sessions."""
    for e in L.expiries("NIFTY"):
        if e > exit_day and entry in _days_of(e) and exit_day in _days_of(e):
            return e
    return None


def events(ses: list[date]) -> tuple[list[tuple[date, str]], list[tuple[date, str]]]:
    """([(E, type)], [(date, type) skipped: no session]). FOMC: E is the first session after the US statement date."""
    s = set(ses)
    out, missing = [], []
    for kind, ds in (("RBI", RBI), ("Budget", BUDGET), ("US election", US_ELECTION)):
        for d in ds:
            (out if d in s else missing).append((d, kind))
    for d in FOMC_US:
        nxt = next((x for x in ses if x > d), None)
        (out.append((nxt, "FOMC")) if nxt else missing.append((d, "FOMC")))
    return sorted(out), missing


def straddle(name: str, entry: date, exit_day: date, entry_t=(14, 45), exit_t=(14, 45), cm: float = 1.0) -> dict:
    e = expiry_covering(entry, exit_day)
    if e is None:
        return {"day": entry, "skip": "no expiry with chains on the entry and exit sessions"}
    sp = Spec(name, [Leg("BUY", "CE", 0), Leg("BUY", "PE", 0)], entry=entry_t, exit=exit_t, cost_mult=cm)
    return {**run_day(sp, entry, e, exit_day=exit_day), "expiry": e}


E1_CELLS = {"E-1 → E 14:45": (1, 0, (14, 45)), "E-2 → E 14:45": (2, 0, (14, 45)),
            "E-1 → E+1 14:45": (1, 1, (14, 45)), "E-1 → E 12:00": (1, 0, (12, 0))}
E1_PRIMARY = "E-1 → E 14:45"


def run_e1() -> dict:
    ses = sessions()
    pos = {d: i for i, d in enumerate(ses)}
    evs, missing = events(ses)
    ev_days = {e for e, _ in evs}
    rows, vc = [], {}
    for ev, kind in evs:
        for cell, cm in [(c, 1.0) for c in E1_CELLS] + [(E1_PRIMARY, 2.0)]:
            back, fwd, xt = E1_CELLS[cell]
            i = pos[ev]
            entry, exit_day = ses[i - back], ses[i + fwd] if i + fwd < len(ses) else None
            r = (straddle(cell, entry, exit_day, exit_t=xt, cm=cm) if exit_day and exit_day <= WINDOW[1]
                 else {"day": entry, "skip": "exit after the window"})
            rows.append({**r, "cell": cell, "cost_mult": cm, "event_day": ev, "event_type": kind, "event": True,
                         "vix": vix_at(entry, 14, 45, vc), "weekday": entry.strftime("%a")})
    # baseline: E-1 → E on every ordinary session pair in the window
    base = []
    for i in range(1, len(ses)):
        d = ses[i]
        if not (WINDOW[0] <= ses[i - 1] and d <= WINDOW[1]) or d in ev_days:
            continue
        base.append(straddle("baseline", ses[i - 1], d))
    bt = pd.DataFrame(base)
    pod = Pod(name="E1", title="NIFTY long ATM straddle, 14:45 the session before an event → 14:45 on the event session",
              page="strategies/S3_E1_event_straddle.md", cells=list(E1_CELLS), spec=None, primary=E1_PRIMARY,
              neighbours=[c for c in E1_CELLS if c != E1_PRIMARY], label=lambda c: c, skip_events=False,
              measure="premium")
    allt = pd.DataFrame(rows)
    p = allt[(allt["cell"] == E1_PRIMARY) & (allt["cost_mult"] == 1.0) & (allt["skip"].fillna("") == "")]
    extra = ["", "## E1 side reports (not the gate)", "",
             f"Window {WINDOW[0]} → {WINDOW[1]}; halves {HALVES[0][0]} → {HALVES[0][1]} and {HALVES[1][0]} → {HALVES[1][1]}. "
             f"Events {len(evs)}; without a session in the store: {missing or 'none'}.", "",
             "| Event type | Trades | Net % of premium | Median | Win rate |", "|---|---|---|---|---|"]
    for k, g in p.groupby("event_type"):
        extra.append(f"| {k} | {len(g)} | {g['net_pct_premium'].mean():+.1f} % | {g['net_pct_premium'].median():+.1f} % | "
                     f"{(g['net_rs'] > 0).mean() * 100:.0f} % |")
    extra += _baseline_line("ordinary session pairs, E-1 → E 14:45 (no event)", bt)
    extra += _trade_table(p, ["event_day", "event_type"])
    return write_report(pod, allt, len(evs), WINDOW, HALVES, False, extra=extra)


# ---------- Q1 squeeze ----------
Q1_PRIMARY = (5, 20, 3)
Q1_NEIGHBOURS = [(5, 16, 3), (5, 24, 3), (4, 20, 3), (6, 20, 3), (5, 20, 2), (5, 20, 4)]
VIX_MEDIAN_N, PCT_N, PCT_MIN = 60, 250, 200


def q1_label(c) -> str:
    return f"lookback {c[0]} · pct {c[1]} · hold {c[2]}"


def quiet_days(daily: pd.DataFrame, lb: int, pct: int) -> pd.Series:
    """True on d when the lb-session mean range % ending at d-1 is at or below the pct percentile of that mean over the
    PCT_N sessions ending at d-2 (at least PCT_MIN). Nothing from d itself."""
    rng = (daily["high"] - daily["low"]) / daily["close"] * 100
    m = rng.rolling(lb).mean()
    thr = m.rolling(PCT_N, min_periods=PCT_MIN).quantile(pct / 100)
    return (m.shift(1) <= thr.shift(2)).fillna(False)


@lru_cache(maxsize=1)
def vix_series() -> tuple[pd.Series, pd.Series]:
    """(VIX close per session, VIX last close at or before 14:44 per session)."""
    v = L.vix_1m(date(2021, 10, 1), WINDOW[1])
    v["d"] = v["timestamp"].dt.date
    close = v.groupby("d")["close"].last()
    early = v[v["timestamp"].dt.time <= time(14, 44)].groupby("d")["close"].last()
    return close, early


def low_vix(day: date, close: pd.Series, early: pd.Series) -> bool:
    prev = close[close.index < day].tail(VIX_MEDIAN_N)
    return day in early.index and len(prev) == VIX_MEDIAN_N and float(early[day]) <= float(prev.median())


def run_q1() -> dict:
    daily = G.daily()
    ses = list(daily.index)
    pos = {d: i for i, d in enumerate(ses)}
    close, early = vix_series()
    rows, skipped, vc = [], [], {}
    cells = [Q1_PRIMARY] + Q1_NEIGHBOURS
    for cell, cm in [(c, 1.0) for c in cells] + [(Q1_PRIMARY, 2.0)]:
        lb, pct, hold = cell
        q = quiet_days(daily, lb, pct)
        sig = [d for d in ses if WINDOW[0] <= d <= WINDOW[1] and q[d] and low_vix(d, close, early)]
        last_exit = None
        for d in sig:
            if last_exit is not None and d <= last_exit:
                continue
            i = pos[d]
            if i + hold >= len(ses) or ses[i + hold] > WINDOW[1]:
                if cell == Q1_PRIMARY and cm == 1.0:
                    skipped.append(f"{d}: exit after the window")
                continue
            x = ses[i + hold]
            r = straddle(q1_label(cell), d, x, cm=cm)
            if r.get("skip") == "":
                last_exit = x
            elif cell == Q1_PRIMARY and cm == 1.0:
                skipped.append(f"{d}: {r.get('skip')}")
            rows.append({**r, "cell": q1_label(cell), "cost_mult": cm, "event": False, "exit_session": x,
                         "vix": vix_at(d, 14, 45, vc), "weekday": d.strftime("%a")})
    base = []
    wses = [d for d in ses if WINDOW[0] <= d <= WINDOW[1]]
    for j in range(0, len(wses) - 3, 4):
        base.append(straddle("baseline", wses[j], wses[j + 3]))
    pod = Pod(name="Q1", title="NIFTY long ATM straddle after a quiet spell, 14:45 → 14:45 three sessions later",
              page="strategies/S3_Q1_squeeze_straddle.md", cells=cells, spec=None, primary=Q1_PRIMARY,
              neighbours=Q1_NEIGHBOURS, label=q1_label, skip_events=False, measure="premium")
    allt = pd.DataFrame(rows)
    p = allt[(allt["cell"] == q1_label(Q1_PRIMARY)) & (allt["cost_mult"] == 1.0) & (allt["skip"].fillna("") == "")]
    extra = ["", "## Q1 side reports (not the gate)", "",
             f"Window {WINDOW[0]} → {WINDOW[1]}. Primary signals skipped: {skipped or 'none'}."]
    extra += _baseline_line("every 4th session, 3-session straddle, no filter", pd.DataFrame(base))
    extra += _trade_table(p, ["exit_session"])
    n_sig = int(sum(1 for d in ses if WINDOW[0] <= d <= WINDOW[1]))
    return write_report(pod, allt, n_sig, WINDOW, HALVES, False, extra=extra)


# ---------- B1 opening-range breakout + option volume ----------
B1_PRIMARY = (15, 2.0, 0.25)
B1_NEIGHBOURS = [(12, 2.0, 0.25), (18, 2.0, 0.25), (15, 1.6, 0.25), (15, 2.4, 0.25), (15, 2.0, 0.20), (15, 2.0, 0.30)]
B1_BASE = (15, None, 0.25)
LAST_SIGNAL = time(13, 0)
TRAIL = 0.25


def b1_label(c) -> str:
    o, m, s = c
    return f"OR {o} min · volume {'none' if m is None else f'{m:g}x'} · stop {int(round(s * 100))} %"


def _vol_series(chain: pd.DataFrame, k: float, side: str) -> pd.Series:
    c = chain[(chain["strike"] == k) & (chain["option_type"] == side)]
    return c.groupby("timestamp")["volume"].last()


def b1_signal(day_spot: pd.DataFrame, chain: pd.DataFrame, minutes: int, mult: float | None):
    """(side, signal minute, strike) of the first breakout close beyond the opening range, end of range → 13:00, whose
    ATM option traded at least `mult` x its median per-minute volume of the 30 minutes before (and > 0). `mult` None:
    the first breakout, no volume test."""
    t1 = (pd.Timestamp("2000-01-01 09:15") + pd.Timedelta(minutes=minutes)).time()
    t = day_spot["timestamp"].dt.time
    rng = day_spot[(t >= time(9, 15)) & (t < t1)]
    rest = day_spot[(t >= t1) & (t <= LAST_SIGNAL)]
    if rng.empty or rest.empty:
        return None
    hi, lo = rng["high"].max(), rng["low"].min()
    cache = {}
    for r in rest.itertuples():
        side = "CE" if r.close > hi else ("PE" if r.close < lo else None)
        if side is None:
            continue
        k = round(r.close / STEP) * STEP
        if mult is None:
            return side, r.timestamp, k
        if (k, side) not in cache:
            cache[(k, side)] = _vol_series(chain, k, side)
        vols = cache[(k, side)]
        prior = vols.reindex(pd.date_range(r.timestamp - pd.Timedelta(minutes=30), periods=30, freq="min")).fillna(0)
        v = float(vols.get(r.timestamp, 0) or 0)
        if v > 0 and v >= mult * float(prior.median()):
            return side, r.timestamp, k
    return None


def _long_one(name, day, expiry, side, k_signal, ent, stop, cm) -> dict:
    s = spot_at(day, ent.hour, ent.minute)
    if s is None:
        return {"day": day, "skip": "no spot at entry"}
    off = int(round((k_signal - round(s / STEP) * STEP) / STEP)) if k_signal is not None else 0
    sp = Spec(name, [Leg("BUY", side, off)], entry=(ent.hour, ent.minute), exit=(15, 15), stop=stop, trail=TRAIL,
              cost_mult=cm)
    return run_day(sp, day, expiry)


def run_b1() -> dict:
    sp = L.spot_1m(*WINDOW)
    sp["d"] = sp["timestamp"].dt.date
    rows, n, vc = [], 0, {}
    cells = [B1_PRIMARY] + B1_NEIGHBOURS + [B1_BASE]
    for day, g in sp.groupby("d"):
        if len(g) < G.MIN_BARS:
            continue
        n += 1
        e = expiry_after(day)
        chain = L.options_day("NIFTY", e, day) if e else None
        sigs = {}
        for cell, cm in [(c, 1.0) for c in cells] + [(B1_PRIMARY, 2.0)]:
            o, m, stop = cell
            base = {"day": day, "cell": b1_label(cell), "cost_mult": cm, "event": False, "weekday": day.strftime("%a"),
                    "expiry": e}
            if e is None:
                rows.append({**base, "skip": "no expiry"})
                continue
            if (o, m) not in sigs:
                sigs[(o, m)] = b1_signal(g, chain, o, m)
            sg = sigs[(o, m)]
            if sg is None:
                rows.append({**base, "skip": "no confirmed breakout"})
                continue
            side, ts, k = sg
            ent = ts + timedelta(minutes=1)
            r = _long_one(b1_label(cell), day, e, side, k, ent, stop, cm)
            rows.append({**r, **base, "side": side, "signal": ts.strftime("%H:%M"), "vix": vix_at(day, ts.hour, ts.minute, vc)})
    allt = pd.DataFrame(rows)
    pod = Pod(name="B1", title="NIFTY 15-min opening-range breakout confirmed by 2x option volume, long ATM, 25 % stop + 25 % trail",
              page="strategies/S3_B1_orb_volume.md", cells=[B1_PRIMARY] + B1_NEIGHBOURS, spec=None, primary=B1_PRIMARY,
              neighbours=B1_NEIGHBOURS, label=b1_label, skip_events=False, measure="premium")
    extra = _directional_side(allt, b1_label(B1_PRIMARY), b1_label(B1_BASE), "first breakout, no volume test")
    return write_report(pod, _no_none_skip(allt), n, WINDOW, HALVES, False, extra=extra)


# ---------- G1 gap follow-through ----------
G1_PRIMARY = (0.5, 15, 0.25)
G1_NEIGHBOURS = [(0.4, 15, 0.25), (0.6, 15, 0.25), (0.5, 12, 0.25), (0.5, 18, 0.25), (0.5, 15, 0.20), (0.5, 15, 0.30)]
G1_BASE = (0.5, None, 0.25)


def g1_label(c) -> str:
    gp, cf, s = c
    return f"gap {gp:g} % · confirm {'none' if cf is None else f'{cf} min'} · stop {int(round(s * 100))} %"


def g1_signal(day_spot: pd.DataFrame, prev_close: float, gap_pct: float, confirm: int | None):
    """(side, entry minute, gap %) or None. Gap: the 09:15 bar's open against the previous close. Confirmation: the
    close of the bar at 09:15 + confirm - 1 is beyond the open in the gap's direction. Entry: the next minute.
    `confirm` None: no test, entry at 09:30."""
    first = day_spot.iloc[0]
    if first["timestamp"].time() != time(9, 15):
        return None
    gap = (first["open"] / prev_close - 1) * 100
    if abs(gap) < gap_pct:
        return None
    side = "CE" if gap > 0 else "PE"
    mins = 15 if confirm is None else confirm
    ent = first["timestamp"] + pd.Timedelta(minutes=mins)
    if confirm is not None:
        upto = day_spot[day_spot["timestamp"] <= ent - pd.Timedelta(minutes=1)]
        c = float(upto["close"].iloc[-1])
        if not ((gap > 0 and c > first["open"]) or (gap < 0 and c < first["open"])):
            return None
    return side, ent, gap


def run_g1() -> dict:
    daily = G.daily()
    sp = L.spot_1m(*WINDOW)
    sp["d"] = sp["timestamp"].dt.date
    rows, n, vc = [], 0, {}
    cells = [G1_PRIMARY] + G1_NEIGHBOURS + [G1_BASE]
    for day, g in sp.groupby("d"):
        if len(g) < G.MIN_BARS:
            continue
        n += 1
        prev = daily[daily.index < day]
        if prev.empty:
            continue
        pc = float(prev["close"].iloc[-1])
        e = expiry_after(day)
        for cell, cm in [(c, 1.0) for c in cells] + [(G1_PRIMARY, 2.0)]:
            gp, cf, stop = cell
            base = {"day": day, "cell": g1_label(cell), "cost_mult": cm, "event": False, "weekday": day.strftime("%a"),
                    "expiry": e}
            sg = g1_signal(g.reset_index(drop=True), pc, gp, cf)
            if sg is None or e is None:
                rows.append({**base, "skip": "no confirmed gap" if sg is None else "no expiry"})
                continue
            side, ent, gap = sg
            r = _long_one(g1_label(cell), day, e, side, None, ent, stop, cm)
            rows.append({**r, **base, "side": side, "gap_pct": round(gap, 2), "vix": vix_at(day, ent.hour, ent.minute, vc)})
    allt = pd.DataFrame(rows)
    pod = Pod(name="G1", title="NIFTY big-gap (≥ 0.5 %) follow-through confirmed at 09:30, long ATM, 25 % stop + 25 % trail",
              page="strategies/S3_G1_gap_follow.md", cells=[G1_PRIMARY] + G1_NEIGHBOURS, spec=None, primary=G1_PRIMARY,
              neighbours=G1_NEIGHBOURS, label=g1_label, skip_events=False, measure="premium")
    extra = _directional_side(allt, g1_label(G1_PRIMARY), g1_label(G1_BASE), "every big gap, no confirmation")
    return write_report(pod, _no_none_skip(allt), n, WINDOW, HALVES, False, extra=extra)


# ---------- shared report pieces ----------
def _no_none_skip(allt: pd.DataFrame) -> pd.DataFrame:
    """write_report lists rows with a skip as 'days without prices'; days with no signal are not trades at all."""
    return allt[~allt["skip"].fillna("").isin(["no confirmed breakout", "no confirmed gap"])].copy()


def _baseline_line(name: str, bt: pd.DataFrame) -> list[str]:
    b = bt[bt["skip"].fillna("") == ""] if len(bt) else bt
    if b.empty:
        return ["", f"**Baseline ({name}):** no trades."]
    s = summary(b)
    return ["", f"**Baseline ({name}):** {s['n']} trades, {s['mean_pct']:+.1f} % of the premium a trade (median "
            f"{s['median_pct']:+.1f} %, t {s['t_pct']:.2f}), win rate {s['win'] * 100:.0f} %."]


def _directional_side(allt: pd.DataFrame, prim: str, base: str, base_name: str) -> list[str]:
    ok = allt["skip"].fillna("") == ""
    p = allt[(allt["cell"] == prim) & (allt["cost_mult"] == 1.0) & ok]
    b = allt[(allt["cell"] == base) & (allt["cost_mult"] == 1.0) & ok]
    out = ["", "## Side reports (not the gate)", "",
           f"Window {WINDOW[0]} → {WINDOW[1]}; halves {HALVES[0][0]} → {HALVES[0][1]} and {HALVES[1][0]} → {HALVES[1][1]}."]
    out += _baseline_line(base_name, b)
    if len(p):
        out += ["", "| Side | Trades | Net % of premium | Win rate | t |", "|---|---|---|---|---|"]
        for sd, g in p.groupby("side"):
            out.append(f"| {sd} | {len(g)} | {g['net_pct_premium'].mean():+.1f} % | {(g['net_rs'] > 0).mean() * 100:.0f} % | "
                       f"{t_stat(g['net_pct_premium']):.1f} |")
        out += ["", f"Primary exits: {p['reason'].value_counts().to_dict()}."]
        out += _trade_table(p, [c for c in ("signal", "gap_pct") if c in p])
    return out


def _trade_table(p: pd.DataFrame, cols: list[str]) -> list[str]:
    if p.empty:
        return []
    head = ["day", *cols, "legs", "exit_at", "reason", "net_rs", "net_pct_premium"]
    out = ["", "## Primary trades", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in p.sort_values("day").itertuples():
        vals = [getattr(r, c) for c in head]
        out.append("| " + " | ".join(f"{v:+,.0f}" if c == "net_rs" else f"{v:+.1f} %" if c == "net_pct_premium" else str(v)
                                     for c, v in zip(head, vals)) + " |")
    return out


RUNS = {"E1": run_e1, "Q1": run_q1, "B1": run_b1, "G1": run_g1}

if __name__ == "__main__":
    for name in (sys.argv[1:] or list(RUNS)):
        RUNS[name]()
