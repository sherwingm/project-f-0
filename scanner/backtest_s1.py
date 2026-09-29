"""S1 v2 · weak-sector results-miss put debit spread, with S1-alt (naked put) and the secondary technical arm,
backtested exactly as strategies/S1_weak_sector_put.md pre-registers them (numbers only).

    python -m scanner.backtest_s1 --diagnostic          # the stock-level diagnostic only (run first)
    python -m scanner.backtest_s1 --since 2021-01-01    # diagnostic, then the three arms -> data/results/

Signals after each close; entry at the next session's option open +/- 1 tick per leg; exits on closes.
Every choice the definition fixes is a module constant below; nothing here is tuned.
"""
from __future__ import annotations

import argparse
import bisect
import logging
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from server import charges as ch

from .backtest_cheap_options import sessions_to
from .build import ROOT
from .stats import PERIODS, clustered_t

log = logging.getLogger("backtest_s1")

# ---------------------------------------------------------------- the pre-registered parameters
M1, M3, SECTOR_DMA, STOCK_DMA = 21, 63, 50, 20          # sessions
MIN_PEERS = 3                                           # leave-one-out sector needs >= 3 other constituents that day
SESSION_OPEN = (9, 15)                                  # a filing before 09:15 on a session day: day 0 is that day
MISS_PCT = -2.0                                         # day-0 abnormal return (stock - leave-one-out sector) <= -2 %
COOLDOWN = 10                                           # sessions after an exit in which a new signal is ignored
MIN_SESSIONS_TO_EXPIRY = 25                             # spread expiry: first with >= 25 sessions after the signal day
SHORT_BAND, SHORT_TARGET = (0.93, 0.95), 0.94           # short strike 5-7 % below spot, nearest 6 %
NAKED_BAND = 0.97                                       # S1-alt: ATM to 3 % below spot
DEBIT_MIN, DEBIT_MAX = 2000.0, 8000.0                   # spread net debit per lot at the entry fill (Rs)
TICK, MIN_PREMIUM = 0.05, 2.0                           # one tick adverse per leg; naked put < Rs 2 refused (lottery)
STOP, EXPIRY_BUFFER, MAX_SESSIONS = 0.5, 5, 20
TRAIL_ARM, TRAIL_KEEP = 2.0, 0.75
SLIPPAGE, SENSITIVITY = 0.02, (0.01, 0.02, 0.03)        # of premium, per leg per side
EXTREME_REL63 = -15.0                                   # pre-registered subgroup: sector 63-session relative return
DIAG_HORIZONS = (10, 20)
CA_TOLERANCE = 0.03
EXIT_REASONS = ("1_stop", "2_expiry", "3_20_sessions", "4_trailing")
ARMS = {"S1v2": ("results", "spread"), "S1alt": ("results", "naked"), "technical": ("technical", "spread")}


# ---------------------------------------------------------------- rules (pure, tested one by one)
def daily_returns(close: np.ndarray) -> np.ndarray:
    r = np.full(len(close), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        r[1:] = close[1:] / close[:-1] - 1
    r[~np.isfinite(r)] = np.nan
    return r


def peer_sums(returns: list[np.ndarray], n: int) -> tuple[np.ndarray, np.ndarray]:
    """Sum and count of the constituents' daily returns per session (equal weight)."""
    if not returns:
        return np.zeros(n), np.zeros(n)
    m = np.vstack(returns)
    return np.nansum(m, axis=0), (~np.isnan(m)).sum(axis=0)


def leave_one_out(total: np.ndarray, count: np.ndarray, own: np.ndarray) -> np.ndarray:
    """The sector's equal-weight daily return without the stock; NaN with fewer than MIN_PEERS others."""
    has = ~np.isnan(own)
    s = total - np.where(has, own, 0.0)
    c = count - has
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(c >= MIN_PEERS, s / np.maximum(c, 1), np.nan)


def _ret(a: np.ndarray, i: int, n: int) -> float:
    if i < n or math.isnan(a[i]) or math.isnan(a[i - n]) or a[i - n] <= 0:
        return math.nan
    return a[i] / a[i - n] - 1


def compound(r: np.ndarray, i: int, n: int) -> float:
    """Return over the n sessions ending at i from daily returns r (NaN if any is missing)."""
    if i - n + 1 < 0:
        return math.nan
    w = r[i - n + 1: i + 1]
    return math.nan if np.isnan(w).any() else float(np.prod(1 + w) - 1)


def sector_state(loo: np.ndarray, bench: np.ndarray, i: int) -> tuple[float, float, bool] | None:
    """(21-session relative return %, 63-session relative return %, level below its 50-session average)
    of the leave-one-out sector against NIFTY 500 at the close of i; None without full data."""
    if i < M3:
        return None
    w = loo[i - M3 + 1: i + 1]
    b21, b63 = _ret(bench, i, M1), _ret(bench, i, M3)
    if np.isnan(w).any() or math.isnan(b21) or math.isnan(b63):
        return None
    lvl = np.cumprod(1 + w)                               # level at i-62..i, 1 = the close of i-63
    r21, r63 = lvl[-1] / lvl[-1 - M1] - 1, lvl[-1] - 1
    return (r21 - b21) * 100, (r63 - b63) * 100, bool(lvl[-1] < lvl[-SECTOR_DMA:].mean())


def sector_weak(state) -> bool:
    return state is not None and state[0] < 0 and state[1] < 0 and state[2]


def day0_index(cal: list[str], event_date: str, event_time: str | None) -> int | None:
    """First full session after the filing: the filing day itself if filed before 09:15 on a session day."""
    i = bisect.bisect_left(cal, event_date)
    if i < len(cal) and cal[i] == event_date and event_time:
        try:
            h, m = (int(x) for x in str(event_time).split(":")[:2])
        except ValueError:
            h, m = 99, 0
        if (h, m) < SESSION_OPEN:
            return i
    j = bisect.bisect_right(cal, event_date)
    return j if j < len(cal) else None


def abnormal_pct(close: np.ndarray, loo: np.ndarray, i: int) -> float:
    """Day-i return of the stock minus the leave-one-out sector's, in %."""
    if i < 1:
        return math.nan
    return (_ret(close, i, 1) - loo[i]) * 100


def technical(close: np.ndarray, loo: np.ndarray, i: int) -> bool:
    """Close below its 20-session average and a 21-session return worse than the leave-one-out sector's."""
    if i < max(M1, STOCK_DMA - 1):
        return False
    w = close[i - STOCK_DMA + 1: i + 1]
    rs, rk = _ret(close, i, M1), compound(loo, i, M1)
    if np.isnan(w).any() or math.isnan(rs) or math.isnan(rk):
        return False
    return bool(close[i] < w.mean() and rs < rk)


def choose_spread(chain: dict, cal_dates: list[date], d: date, spot: float) -> tuple[str, float, float] | None:
    """chain {(expiry, strike): ...} of the stock's puts on signal day d. The first expiry with >= 25 sessions
    after d; long = the strike nearest spot (a tie: the higher); short = the strike in [0.93, 0.95] x spot
    nearest 0.94 x spot (a tie: the higher), below the long strike."""
    if not spot:
        return None
    iso = d.isoformat()
    exp = next((e for e in sorted({e for e, _ in chain if e > iso})
                if sessions_to(cal_dates, d, date.fromisoformat(e)) >= MIN_SESSIONS_TO_EXPIRY), None)
    if exp is None:
        return None
    ks = sorted(k for e, k in chain if e == exp)
    long_k = min(ks, key=lambda k: (abs(k - spot), -k))
    shorts = [k for k in ks if SHORT_BAND[0] * spot <= k <= SHORT_BAND[1] * spot and k < long_k]
    if not shorts:
        return None
    return exp, long_k, min(shorts, key=lambda k: (abs(k - SHORT_TARGET * spot), -k))


def choose_put(chain: dict, d: date, spot: float) -> tuple[str, float] | None:
    """S1-alt: the second expiry after d (next month) and the highest strike in [0.97 x spot, spot]."""
    expiries = sorted({e for e, _ in chain if e > d.isoformat()})
    if len(expiries) < 2 or not spot:
        return None
    strikes = [k for e, k in chain if e == expiries[1] and NAKED_BAND * spot <= k <= spot]
    return (expiries[1], max(strikes)) if strikes else None


def exit_reason(value: float, debit: float, peak: float, held: int, to_expiry: int) -> str | None:
    """The first exit rule that holds on this close, in the pre-registered order. value / debit / peak per share."""
    if value <= STOP * debit:
        return "1_stop"
    if to_expiry <= EXPIRY_BUFFER:
        return "2_expiry"
    if held >= MAX_SESSIONS:
        return "3_20_sessions"
    if peak >= TRAIL_ARM * debit and value < TRAIL_KEEP * peak:
        return "4_trailing"
    return None


# ---------------------------------------------------------------- inputs
@dataclass
class Inputs:
    cal: list[str]                                        # eod2 session dates, ISO, full history (for lookbacks)
    bhav: Callable[[str], pd.DataFrame | None]            # the day's STF + STO PE rows
    opens: Callable[[str], pd.DataFrame | None]           # the day's stock-option opens
    stock: dict[str, pd.Series]                           # eod2 closes by date (adjusted)
    sector_of: dict[str, str]                             # stock -> sector (today's lists)
    bench: pd.Series                                      # NIFTY 500
    results: list[tuple[str, str, str | None]] = field(default_factory=list)   # (symbol, date, time)
    ban: dict[str, set[str]] = field(default_factory=dict)
    lots: dict[str, int] = field(default_factory=dict)


def _align(s: pd.Series | None, cal: list[str]) -> np.ndarray:
    if s is None or s.empty:
        return np.full(len(cal), np.nan)
    s = s.copy()
    s.index = [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10] for d in s.index]
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(cal).to_numpy(dtype=float)


class Market:
    """Aligned closes, daily returns and leave-one-out sector returns, computed once."""

    def __init__(self, inp: Inputs):
        self.cal = inp.cal
        self.pos = {d: i for i, d in enumerate(inp.cal)}
        self.cal_dates = [date.fromisoformat(d) for d in inp.cal]
        self.bench = _align(inp.bench, inp.cal)
        self.close = {s: _align(v, inp.cal) for s, v in inp.stock.items()}
        self.ret = {s: daily_returns(a) for s, a in self.close.items()}
        self.sector_of = {s: k for s, k in inp.sector_of.items() if s in self.close}
        n = len(inp.cal)
        members: dict[str, list[str]] = {}
        for s, k in self.sector_of.items():
            members.setdefault(k, []).append(s)
        self.sums = {k: peer_sums([self.ret[s] for s in m], n) for k, m in members.items()}
        self._loo: dict[str, np.ndarray] = {}

    def loo(self, sym: str) -> np.ndarray | None:
        k = self.sector_of.get(sym)
        if k is None:
            return None
        if sym not in self._loo:
            total, count = self.sums[k]
            self._loo[sym] = leave_one_out(total, count, self.ret[sym])
        return self._loo[sym]

    def state(self, sym: str, i: int):
        lr = self.loo(sym)
        return None if lr is None else sector_state(lr, self.bench, i)


def results_signals(m: Market, results: list[tuple[str, str, str | None]]) -> dict[int, dict[str, float]]:
    """{day-0 index: {symbol: abnormal %}} for results filings whose day-0 abnormal return is <= -2 %."""
    out: dict[int, dict[str, float]] = {}
    for sym, d, t in results:
        lr = m.loo(sym)
        i = day0_index(m.cal, d, t)
        if lr is None or i is None:
            continue
        ab = abnormal_pct(m.close[sym], lr, i)
        if not math.isnan(ab) and ab <= MISS_PCT:
            out.setdefault(i, {})[sym] = ab
    return out


# ---------------------------------------------------------------- the diagnostic
def excess_return(m: Market, sym: str, i: int, h: int) -> float:
    """Stock return close i -> close i+h minus the leave-one-out sector's, in %."""
    if i + h >= len(m.cal):
        return math.nan
    return (_ret(m.close[sym], i + h, h) - compound(m.loo(sym), i + h, h)) * 100


def diagnostic(m: Market, results: list, universe: dict[str, set[str]], start: str, end: str) -> pd.DataFrame:
    """Every results-miss signal that passes the sector filter (one per stock and day 0), and every onset of the
    technical trigger with the sector filter (true today, false the session before), in that day's universe."""
    miss = results_signals(m, results)
    rows = []
    for d in (d for d in m.cal if start <= d <= end):
        i = m.pos[d]
        for sym in sorted(universe.get(d, ())):
            lr = m.loo(sym)
            if lr is None:
                continue
            st = m.state(sym, i)
            if not sector_weak(st):
                continue
            trig = []
            if sym in miss.get(i, {}):
                trig.append("results")
            if technical(m.close[sym], lr, i) and not (sector_weak(m.state(sym, i - 1))
                                                         and technical(m.close[sym], lr, i - 1)):
                trig.append("technical")
            for t in trig:
                rows.append({"signal_date": d, "symbol": sym, "trigger": t, "rel63": st[1],
                             **{f"ex{h}": excess_return(m, sym, i, h) for h in DIAG_HORIZONS}})
    return pd.DataFrame(rows, columns=["signal_date", "symbol", "trigger", "rel63"] + [f"ex{h}" for h in DIAG_HORIZONS])


def summarise_diagnostic(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for trig in ("results", "technical"):
        for name, a, b in (("all", "0000", "9999"),) + PERIODS:
            g = df[(df["trigger"] == trig) & (df["signal_date"] >= a) & (df["signal_date"] <= b)]
            for h in DIAG_HORIZONS:
                x = g[[f"ex{h}", "signal_date"]].dropna()
                v = x[f"ex{h}"]
                out.append({"trigger": trig, "period": name, "horizon": h, "n": len(v),
                            "mean_pct": round(v.mean(), 3) if len(v) else None,
                            "median_pct": round(v.median(), 3) if len(v) else None,
                            "share_negative_pct": round((v < 0).mean() * 100, 2) if len(v) else None,
                            "t_clustered": clustered_t(v, x["signal_date"]) if len(v) > 1 else None})
    return pd.DataFrame(out)


# ---------------------------------------------------------------- the simulation
def _lot_from_oi(rows: pd.DataFrame) -> int:
    """Old-format files carry no lot size: open interest is always a whole number of lots, so the lot is the
    greatest common divisor of the stock's non-zero open interests that day."""
    oi = [int(x) for x in rows["OpnIntrst"].fillna(0) if x > 0]
    return int(np.gcd.reduce(oi)) if oi else 0


class Day:
    """One bhavcopy: the universe, spots, futures and each stock's put rows."""

    def __init__(self, b: pd.DataFrame):
        self.b = b
        self.groups = {s: g for s, g in b.groupby("TckrSymb", sort=False)}
        opt = b[b["FinInstrmTp"] == "STO"]
        self.universe = set(opt["TckrSymb"])
        fut = b[b["FinInstrmTp"] == "STF"]
        self.futs = {(s, str(e)[:10]): float(c) for s, e, c in zip(fut["TckrSymb"], fut["XpryDt"], fut["ClsPric"])}
        self.spot: dict[str, float] = {}
        if "UndrlygPric" in b.columns:
            u = opt[opt["UndrlygPric"] > 0].drop_duplicates("TckrSymb")
            self.spot = dict(zip(u["TckrSymb"], u["UndrlygPric"].astype(float)))
        for (s, e), c in sorted(self.futs.items()):
            self.spot.setdefault(s, c)                    # old format: the nearest future's close

    def chain(self, sym: str) -> dict:
        """{(expiry, strike): (close, oi, contracts traded)} of the stock's puts."""
        g = self.groups.get(sym)
        if g is None:
            return {}
        g = g[(g["FinInstrmTp"] == "STO") & (g["OptnTp"] == "PE")]
        vol = g["TtlTradgVol"] if "TtlTradgVol" in g.columns else pd.Series(0, index=g.index)
        return {(str(e)[:10], float(k)): (float(c), float(o), float(v))
                for e, k, c, o, v in zip(g["XpryDt"], g["StrkPric"], g["ClsPric"], g["OpnIntrst"].fillna(0), vol.fillna(0))}

    def lot(self, sym: str, fallback: dict[str, int]) -> int:
        g = self.groups.get(sym)
        if g is None:
            return 0
        if "NewBrdLotQty" in g.columns:
            v = pd.to_numeric(g["NewBrdLotQty"], errors="coerce").dropna()
            if len(v) and v.iloc[0] > 0:
                return int(v.iloc[0])
        return _lot_from_oi(g) or fallback.get(sym, 0)


@dataclass
class Arm:
    name: str
    trigger: str                                          # results / technical
    structure: str                                        # spread / naked
    open: dict = field(default_factory=dict)
    pending: dict = field(default_factory=dict)
    last_exit: dict = field(default_factory=dict)
    done: list = field(default_factory=list)
    skips: Counter = field(default_factory=Counter)


def run(inp: Inputs, start: str, end: str, arms: tuple[str, ...] = tuple(ARMS)) -> dict[str, tuple[pd.DataFrame, Counter]]:
    m = Market(inp)
    cal, cal_dates = m.cal, m.cal_dates
    miss = results_signals(m, inp.results)
    state = {a: Arm(a, *ARMS[a]) for a in arms}
    days = [d for d in cal if start <= d <= end]
    for n_day, d in enumerate(days, 1):
        i = m.pos[d]
        b = inp.bhav(d)
        if b is None:
            for a in state.values():
                a.skips["no_bhavcopy_on_entry_day"] += len(a.pending)
                a.pending = {}
            continue
        day = Day(b)

        # 1. yesterday's signals enter at today's open
        if any(a.pending for a in state.values()):
            o = inp.opens(d)
            omap = {} if o is None else {(s, str(e)[:10], float(k)): float(p) for s, e, k, t, p in
                                         zip(o["TckrSymb"], o["XpryDt"], o["StrkPric"], o["OptnTp"], o["OpnPric"]) if t == "PE"}
            for a in state.values():
                for sym, p in a.pending.items():
                    _enter(a, sym, p, omap, day, d, i, m)
                a.pending = {}

        # 2. exits on today's close
        for a in state.values():
            for sym in list(a.open):
                _check_exit(a, sym, day, d, i, m)

        # 3. today's signals
        if i + 1 >= len(cal):
            continue
        ban_next = inp.ban.get(cal[i + 1], set())
        for sym in sorted(day.universe):
            lr = m.loo(sym)
            if lr is None:
                continue
            st = m.state(sym, i)
            if not sector_weak(st):
                continue
            fired = {"results": sym in miss.get(i, {}), "technical": technical(m.close[sym], lr, i)}
            for a in state.values():
                if not fired[a.trigger]:
                    continue
                if sym in a.open or sym in a.pending or (sym in a.last_exit and i <= a.last_exit[sym] + COOLDOWN):
                    a.skips["position_or_cooldown"] += 1
                    continue
                if sym in ban_next:
                    a.skips["in_ban_on_entry_day"] += 1
                    continue
                chain = day.chain(sym)
                pick = (choose_spread(chain, cal_dates, cal_dates[i], day.spot.get(sym)) if a.structure == "spread"
                        else choose_put(chain, cal_dates[i], day.spot.get(sym)))
                if pick is None:
                    a.skips["no_strikes"] += 1
                    continue
                lot = day.lot(sym, inp.lots)
                if not lot:
                    a.skips["no_lot_size"] += 1
                    continue
                a.pending[sym] = {"symbol": sym, "sector": m.sector_of[sym], "trigger": a.trigger,
                                  "structure": a.structure, "signal_date": d, "signal_i": i, "expiry": pick[0],
                                  "long_k": pick[1], "short_k": pick[2] if a.structure == "spread" else None,
                                  "spot": day.spot.get(sym), "lot": lot, "rel21": st[0], "rel63": st[1]}
        if n_day % 100 == 0:
            log.info("%s: %d of %d sessions; %s", d, n_day, len(days),
                     ", ".join(f"{a.name} {len(a.done)} closed" for a in state.values()))
    out = {}
    for a in state.values():
        a.skips["still_open_at_end"] = len(a.open)
        out[a.name] = (trades_frame(a.done), a.skips)
    return out


def _enter(a: Arm, sym: str, p: dict, omap: dict, day: Day, d: str, i: int, m: Market) -> None:
    lo = omap.get((sym, p["expiry"], p["long_k"]), 0.0)
    so = omap.get((sym, p["expiry"], p["short_k"]), 0.0) if a.structure == "spread" else 0.0
    if lo <= 0 or (a.structure == "spread" and so <= 0):
        a.skips["no_opening_trade"] += 1
        return
    long_in = round(lo + TICK, 2)
    short_in = round(max(so - TICK, 0.0), 2) if a.structure == "spread" else 0.0
    debit = round(long_in - short_in, 2)
    if a.structure == "naked" and lo < MIN_PREMIUM:
        a.skips["lottery_refused"] += 1
        return
    if a.structure == "spread" and not DEBIT_MIN <= debit * p["lot"] <= DEBIT_MAX:
        a.skips["debit_outside_2000_8000"] += 1
        return
    lots = 1
    a.open[sym] = {**p, "entry_date": d, "entry_i": i, "lots": lots, "qty": p["lot"] * lots, "long_in": long_in,
                   "short_in": short_in, "debit": debit, "peak": -math.inf,
                   "fut0": day.futs.get((sym, p["expiry"])), "stock0": m.close[sym][i]}


def _check_exit(a: Arm, sym: str, day: Day, d: str, i: int, m: Market) -> None:
    t = a.open[sym]
    chain = day.chain(sym)
    lc = chain.get((t["expiry"], t["long_k"]))
    sc = chain.get((t["expiry"], t["short_k"])) if t["structure"] == "spread" else (0.0,)
    excl = None
    if lc is None or sc is None:
        excl = "contract_changed"
    else:
        f1, px = day.futs.get((sym, t["expiry"])), m.close[sym][i]
        if f1 and t["fut0"] and t["stock0"] and not math.isnan(px) and not math.isnan(t["stock0"]):
            if abs((f1 / t["fut0"]) / (px / t["stock0"]) - 1) > CA_TOLERANCE:
                excl = "price_adjusted"
    if excl:
        a.done.append({**t, "exit_date": d, "exit_i": i, "long_out": None, "short_out": None, "value": None,
                       "exit_reason": None, "excluded": excl})
        a.last_exit[sym] = i
        del a.open[sym]
        return
    value = lc[0] - sc[0]
    t["peak"] = max(t["peak"], value)
    reason = exit_reason(value, t["debit"], t["peak"], i - t["entry_i"],
                         sessions_to(m.cal_dates, m.cal_dates[i], date.fromisoformat(t["expiry"])))
    if reason:
        long_out = max(0.0, round(lc[0] - TICK, 2))
        short_out = round(sc[0] + TICK, 2) if t["structure"] == "spread" else 0.0
        a.done.append({**t, "exit_date": d, "exit_i": i, "long_out": long_out, "short_out": short_out,
                       "value": round(value, 2), "exit_reason": reason, "excluded": ""})
        a.last_exit[sym] = i
        del a.open[sym]


def _charges(qty: int, long_in: float, short_in: float, long_out: float, short_out: float, spread: bool) -> float:
    c = ch.leg("PE", "BUY", qty, long_in)["total"]
    if long_out > 0:
        c += ch.leg("PE", "SELL", qty, long_out)["total"]
    if spread:
        c += ch.leg("PE", "SELL", qty, short_in)["total"] + ch.leg("PE", "BUY", qty, short_out)["total"]
    return c


TRADE_COLUMNS = ["signal_date", "entry_date", "exit_date", "symbol", "sector", "trigger", "structure", "expiry",
                 "long_k", "short_k", "spot", "lot", "lots", "qty", "long_in", "short_in", "debit", "debit_rs",
                 "long_out", "short_out", "value", "exit_reason", "held", "rel21", "rel63", "charges", "premium_turnover",
                 "slip_rate", "slippage", "net", "net_pct", "excluded"]


def trades_frame(done: list[dict]) -> pd.DataFrame:
    rows = []
    for t in done:
        spread = t["structure"] == "spread"
        qty = t["qty"]
        r = {k: t.get(k) for k in TRADE_COLUMNS}
        r["debit_rs"] = round(t["debit"] * qty, 2)
        r["held"] = t["exit_i"] - t["entry_i"]
        r["slip_rate"] = SLIPPAGE
        if t["long_out"] is not None:
            r["charges"] = round(_charges(qty, t["long_in"], t["short_in"], t["long_out"], t["short_out"], spread), 2)
            r["premium_turnover"] = round(qty * (t["long_in"] + t["short_in"] + t["long_out"] + t["short_out"]), 2)
        rows.append(r)
    df = pd.DataFrame(rows, columns=TRADE_COLUMNS)
    return with_slippage(df)


def with_slippage(df: pd.DataFrame, rate: float | None = None) -> pd.DataFrame:
    """net and net % of debit at the trade's slippage rate (or a flat `rate`): gross - charges - slippage."""
    df = df.copy()
    for c in ("qty", "long_in", "short_in", "long_out", "short_out", "charges", "premium_turnover", "slip_rate",
              "debit_rs"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if rate is not None:
        df["slip_rate"] = rate
    gross = df["qty"] * ((df["long_out"] - df["long_in"]) - (df["short_out"] - df["short_in"]))
    df["slippage"] = (df["slip_rate"] * df["premium_turnover"]).round(2)
    df["net"] = (gross - df["charges"] - df["slippage"]).round(2)
    df["net_pct"] = (df["net"] / df["debit_rs"] * 100).round(3)
    return df


# ---------------------------------------------------------------- summaries
def metrics(g: pd.DataFrame) -> dict:
    """N, hit rate, mean / median net return (% of debit and Rs), net per Rs 1,000 risked (risked = entry debit),
    date-clustered t of the % return, the 5th percentile %, and each exit reason's share."""
    g = g[g["excluded"].fillna("") == ""]
    n = len(g)
    r = g["net_pct"].astype(float)
    row = {"n": n, "hit_rate_pct": round((g["net"] > 0).mean() * 100, 2) if n else None,
           "mean_pct": round(r.mean(), 3) if n else None, "median_pct": round(r.median(), 3) if n else None,
           "mean_rs": round(g["net"].mean(), 2) if n else None, "median_rs": round(g["net"].median(), 2) if n else None,
           "net_per_1000": round(g["net"].sum() / g["debit_rs"].sum() * 1000, 2) if n else None,
           "t_clustered": clustered_t(r, g["entry_date"]) if n > 1 else None,
           "worst_5pct": round(float(np.percentile(r, 5)), 3) if n else None}
    for reason in EXIT_REASONS:
        row[f"exit_{reason}_pct"] = round((g["exit_reason"] == reason).mean() * 100, 2) if n else None
    return row


def by_period(trades: pd.DataFrame, **extra) -> list[dict]:
    out = []
    for name, a, b in (("all", "0000", "9999"),) + PERIODS:
        g = trades[(trades["entry_date"] >= a) & (trades["entry_date"] <= b)]
        out.append({**extra, "period": name, **metrics(g)})
    return out


def summarise(trades: pd.DataFrame) -> pd.DataFrame:
    rows = by_period(trades, group="all")
    ext = trades[trades["rel63"] < EXTREME_REL63]
    rows += by_period(ext, group="extreme_rel63_below_-15")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- real inputs
def option_universe(cache_dir: Path, since: str) -> dict[str, set[str]]:
    """{date: stocks with option contracts in that day's cached bhavcopy}."""
    out = {}
    for f in sorted(Path(cache_dir).glob("fo_bhavcopy_*.csv")):
        d = f"{f.stem[-8:-4]}-{f.stem[-4:-2]}-{f.stem[-2:]}"
        if d < since:
            continue
        b = pd.read_csv(f, usecols=["TckrSymb", "FinInstrmTp"])
        out[d] = set(b.loc[b["FinInstrmTp"] == "STO", "TckrSymb"].astype(str).str.strip())
    return out


def load_inputs(eod2_dir: Path, cache_dir: Path, symbols: set[str]) -> Inputs:
    from .backtest_cheap_options import _read_index
    from .equity import load_symbol
    from .events.store import Store
    from .nse_fo import BhavcopyUnavailable, download_fo_opens
    from .sectors import BENCHMARK, index_closes, load_map
    from .universe import fetch_fo_lots

    cal = [t.strftime("%Y-%m-%d") for t in _read_index(eod2_dir).index]
    sector_of = load_map()
    cols = ["TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "OpnIntrst", "UndrlygPric",
            "NewBrdLotQty", "TtlTradgVol"]

    def bhav(d: str):
        f = cache_dir / f"fo_bhavcopy_{d.replace('-', '')}.csv"
        if not f.exists():
            return None
        b = pd.read_csv(f, usecols=lambda c: c in cols)
        return b[(b["FinInstrmTp"] == "STF") | ((b["FinInstrmTp"] == "STO") & (b["OptnTp"] == "PE"))]

    def opens(d: str):
        try:
            return download_fo_opens(date.fromisoformat(d), cache_dir)
        except (BhavcopyUnavailable, OSError, ValueError) as exc:
            log.warning("opens %s: %s", d, exc)
            return None

    stock = {}
    for sym in sorted(set(sector_of) | set(symbols)):
        try:
            stock[sym] = load_symbol(sym, eod2_dir)["Close"]
        except Exception:  # noqa: BLE001 - not every stock has eod2 history
            continue
    with Store() as st:
        results = [(e["symbol"], e["event_date"], e.get("event_time")) for e in st.all_of_type("results")]
        ban: dict[str, set[str]] = {}
        for e in st.all_of_type("ban"):
            if e.get("subtype") == "in":                  # one "in" row per trade date in the ban
                ban.setdefault(e["event_date"], set()).add(e["symbol"])
    return Inputs(cal=cal, bhav=bhav, opens=opens, stock=stock, sector_of=sector_of,
                  bench=index_closes(BENCHMARK, eod2_dir), results=results, ban=ban,
                  lots=fetch_fo_lots(cache_path=cache_dir / "fo_universe.txt"))


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v2 backtest (numbers only)")
    ap.add_argument("--since", default="2021-01-01")
    ap.add_argument("--until", default="9999-12-31")
    ap.add_argument("--diagnostic", action="store_true", help="the stock-level diagnostic only")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    universe = option_universe(a.cache_dir, a.since)
    inp = load_inputs(a.eod2_dir, a.cache_dir, set().union(*universe.values()))
    end = min(a.until, inp.cal[-1])
    a.out_dir.mkdir(parents=True, exist_ok=True)
    m = Market(inp)
    diag = diagnostic(m, inp.results, universe, a.since, end)
    diag.to_csv(a.out_dir / "s1_diagnostic_signals.csv", index=False)
    print(summarise_diagnostic(diag).to_string(index=False))
    if a.diagnostic:
        return
    for name, (trades, skips) in run(inp, a.since, end).items():
        trades.to_csv(a.out_dir / f"s1_{name}_trades.csv", index=False)
        print(f"\n{name}: {len(trades)} trades; signals not traded: {dict(skips)}")
        print(summarise(trades).to_string(index=False))


if __name__ == "__main__":
    main()
