"""S1 · weak-sector put, backtested exactly as strategies/S1_weak_sector_put.md defines it (numbers only).

    python -m scanner.backtest_s1 --since 2021-01-01          # trades + summary -> data/results/s1_*.csv

Signals after each close; entry at the next session's option open + 1 tick (the 09:20 fill); exits on closes.
Everything the definition fixes is a module constant below; nothing here is tuned.
"""
from __future__ import annotations

import argparse
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
M1, M3, SECTOR_DMA, STOCK_DMA = 21, 63, 50, 20          # sessions
RESULTS_LOOKBACK, MISS_PCT = 15, -2.0                   # results miss: day+1 reaction below -2 % in the last 15 sessions
STRIKE_BAND = 0.97                                      # ATM to 3 % OTM
TICK, MIN_PREMIUM, MIN_OI_LOTS = 0.05, 2.0, 50          # engine: one tick adverse; lottery refused; OI floor
TAKE_PROFIT, STOP_LOSS, MAX_SESSIONS, EXPIRY_BUFFER, LOW_WINDOW = 2.5, 0.5, 10, 5, 21
CA_TOLERANCE = 0.03
EXIT_REASONS = ("stock_at_1m_low", "premium_2.5x", "premium_0.5x", "10_sessions", "5_sessions_to_expiry")


# ---------------------------------------------------------------- rules (pure, tested one by one)
def _ret(a: np.ndarray, i: int, n: int) -> float:
    return a[i] / a[i - n] - 1 if i >= n and a[i - n] > 0 and not (math.isnan(a[i]) or math.isnan(a[i - n])) else math.nan


def sector_weak(sector: np.ndarray, bench: np.ndarray, i: int) -> bool:
    """1-month and 3-month returns below NIFTY 500's, and a close below the 50-session average."""
    if i < max(M3, SECTOR_DMA - 1):
        return False
    r1 = _ret(sector, i, M1) - _ret(bench, i, M1)
    r3 = _ret(sector, i, M3) - _ret(bench, i, M3)
    w = sector[i - SECTOR_DMA + 1: i + 1]
    if np.isnan(w).any() or math.isnan(r1) or math.isnan(r3):
        return False
    return r1 < 0 and r3 < 0 and sector[i] < w.mean()


def weak_stock(stock: np.ndarray, sector: np.ndarray, i: int) -> bool:
    """Close below its 20-session average and a 1-month return worse than its sector's."""
    if i < max(M1, STOCK_DMA - 1):
        return False
    w = stock[i - STOCK_DMA + 1: i + 1]
    rs, rk = _ret(stock, i, M1), _ret(sector, i, M1)
    if np.isnan(w).any() or math.isnan(rs) or math.isnan(rk):
        return False
    return stock[i] < w.mean() and rs < rk


def results_miss(stock: np.ndarray, nifty: np.ndarray, result_positions: list[int], i: int) -> bool:
    """A results event at T in [i-14, i] with T+1 <= i and (close T-1 -> T+1, stock minus NIFTY 50) < -2 %."""
    for t in result_positions:
        if i - (RESULTS_LOOKBACK - 1) <= t and t + 1 <= i and t >= 1:
            react = (stock[t + 1] / stock[t - 1] - nifty[t + 1] / nifty[t - 1]) * 100
            if not math.isnan(react) and react < MISS_PCT:
                return True
    return False


def choose_put(chain: dict[tuple, tuple], signal_date: str, spot: float) -> tuple[str, float] | None:
    """chain: {(expiry, strike): (close, oi, lot)} of the stock's puts on the signal day. The second expiry after
    the signal date, and the highest strike in [0.97 x spot, spot]."""
    expiries = sorted({e for e, _ in chain if e > signal_date})
    if len(expiries) < 2 or not spot:
        return None
    nxt = expiries[1]
    strikes = [k for e, k in chain if e == nxt and STRIKE_BAND * spot <= k <= spot]
    return (nxt, max(strikes)) if strikes else None


def exit_reason(stock_close: float, prior_low: float, premium: float, entry: float, held: int,
                to_expiry: int) -> str | None:
    """The first exit rule that holds on this close, in the definition's order."""
    if not math.isnan(prior_low) and stock_close <= prior_low:
        return "stock_at_1m_low"
    if premium >= TAKE_PROFIT * entry:
        return "premium_2.5x"
    if premium <= STOP_LOSS * entry:
        return "premium_0.5x"
    if held >= MAX_SESSIONS:
        return "10_sessions"
    if to_expiry <= EXPIRY_BUFFER:
        return "5_sessions_to_expiry"
    return None


# ---------------------------------------------------------------- the simulation
@dataclass
class Inputs:
    cal: list[str]                                        # eod2 session dates, ISO, full history (for lookbacks)
    bhav: Callable[[str], pd.DataFrame | None]            # the day's F&O bhavcopy (STO/STF rows)
    opens: Callable[[str], pd.DataFrame | None]           # the day's stock-option opens
    stock: dict[str, pd.Series]                           # eod2 closes by date (adjusted)
    sector_of: dict[str, str]
    sector: dict[str, pd.Series]                          # sector index closes
    bench: pd.Series                                      # NIFTY 500
    nifty: pd.Series                                      # NIFTY 50 (results reaction)
    results: dict[str, list[str]] = field(default_factory=dict)
    ban: dict[str, set[str]] = field(default_factory=dict)
    lots: dict[str, int] = field(default_factory=dict)


def _align(s: pd.Series | None, cal: list[str]) -> np.ndarray:
    if s is None or s.empty:
        return np.full(len(cal), np.nan)
    s = s.copy()
    s.index = [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10] for d in s.index]
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(cal).to_numpy(dtype=float)


def _day(b: pd.DataFrame) -> tuple[dict, dict, dict, dict]:
    """puts[sym][(expiry, strike)] = (close, oi, lot), opts[(sym, expiry, strike, type)] = close,
    futs[(sym, expiry)] = close, spot[sym] = underlying (UndrlygPric, else the nearest future)."""
    puts: dict[str, dict] = {}
    opts, futs, spot = {}, {}, {}
    has_lot = "NewBrdLotQty" in b.columns
    has_und = "UndrlygPric" in b.columns
    for r in b.itertuples(index=False):
        sym, exp, typ = r.TckrSymb, str(r.XpryDt)[:10], r.FinInstrmTp
        if typ == "STF":
            futs[(sym, exp)] = float(r.ClsPric)
            continue
        k = float(r.StrkPric)
        opts[(sym, exp, k, r.OptnTp)] = float(r.ClsPric)
        if r.OptnTp == "PE":
            lot = int(r.NewBrdLotQty) if has_lot and r.NewBrdLotQty == r.NewBrdLotQty and r.NewBrdLotQty > 0 else 0
            puts.setdefault(sym, {})[(exp, k)] = (float(r.ClsPric), float(r.OpnIntrst), lot)
        if has_und and r.UndrlygPric == r.UndrlygPric and r.UndrlygPric > 0:
            spot.setdefault(sym, float(r.UndrlygPric))
    for (sym, exp), c in sorted(futs.items()):
        spot.setdefault(sym, c)                           # old format: the nearest future's close
    return puts, opts, futs, spot


def run(inp: Inputs, start: str, end: str) -> tuple[pd.DataFrame, Counter]:
    cal = inp.cal
    pos = {d: i for i, d in enumerate(cal)}
    cal_dates = [date.fromisoformat(d) for d in cal]
    bench, nifty = _align(inp.bench, cal), _align(inp.nifty, cal)
    sectors = {k: _align(v, cal) for k, v in inp.sector.items()}
    stock: dict[str, np.ndarray] = {}
    results_pos = {s: sorted(pos[d] for d in ds if d in pos) for s, ds in inp.results.items()}
    skips: Counter = Counter()
    open_trades: dict[str, dict] = {}
    pending: dict[str, dict] = {}
    done: list[dict] = []
    days = [d for d in cal if start <= d <= end]
    for n_day, d in enumerate(days, 1):
        i = pos[d]
        b = inp.bhav(d)
        if b is None:
            skips["no_bhavcopy_day"] += 1
            continue
        puts, opts, futs, spot = _day(b)

        # 1. yesterday's signals enter at today's open
        if pending:
            o = inp.opens(d)
            omap = {} if o is None else {(r.TckrSymb, str(r.XpryDt)[:10], float(r.StrkPric), r.OptnTp): float(r.OpnPric)
                                         for r in o.itertuples(index=False)}
            for sym, p in pending.items():
                px = omap.get((sym, p["expiry"], p["strike"], "PE"), 0.0)
                if px <= 0:
                    skips["no_opening_trade"] += 1
                    continue
                if px < MIN_PREMIUM:
                    skips["lottery_refused"] += 1
                    continue
                entry = round(px + TICK, 2)
                qty = p["lot"]
                open_trades[sym] = {**p, "entry_date": d, "entry_i": i, "entry_price": entry, "qty": qty,
                                    "buy_charges": ch.leg("PE", "BUY", qty, entry)["total"],
                                    "fut0": futs.get((sym, p["expiry"])), "stock0": None}
            pending = {}

        # 2. exits on today's close
        for sym in list(open_trades):
            t = open_trades[sym]
            a = stock.get(sym)
            c = opts.get((sym, t["expiry"], t["strike"], "PE"))
            excl = None
            if c is None:
                excl = "contract_changed"
            else:
                f1 = futs.get((sym, t["expiry"]))
                if t["stock0"] is None:
                    t["stock0"] = a[i] if a is not None else None
                if f1 and t["fut0"] and a is not None and t["stock0"] and not math.isnan(a[i]):
                    if abs((f1 / t["fut0"]) / (a[i] / t["stock0"]) - 1) > CA_TOLERANCE:
                        excl = "price_adjusted"
            if excl:
                done.append({**t, "exit_date": d, "exit_price": None, "exit_reason": None, "excluded": excl})
                del open_trades[sym]
                continue
            prior_low = np.nanmin(a[i - LOW_WINDOW:i]) if a is not None and i >= LOW_WINDOW else math.nan
            reason = exit_reason(a[i] if a is not None else math.nan, prior_low, c, t["entry_price"], i - t["entry_i"],
                                 sessions_to(cal_dates, cal_dates[i], date.fromisoformat(t["expiry"])))
            if reason:
                done.append({**t, "exit_date": d, "exit_price": max(0.0, round(c - TICK, 2)), "exit_reason": reason,
                             "excluded": ""})
                del open_trades[sym]

        # 3. today's signals (point in time: the stocks with futures today)
        ban = inp.ban.get(d, set())
        for sym in sorted({s for s, _ in futs}):
            k = inp.sector_of.get(sym)
            if not k or k not in sectors or sym in open_trades:
                continue
            if not sector_weak(sectors[k], bench, i):
                continue
            if sym not in stock:
                stock[sym] = _align(inp.stock.get(sym), cal)
            a = stock[sym]
            miss = results_miss(a, nifty, results_pos.get(sym, []), i)
            weak = weak_stock(a, sectors[k], i)
            if not (miss or weak):
                continue
            if sym in ban:
                skips["in_ban"] += 1
                continue
            pick = choose_put(puts.get(sym, {}), d, spot.get(sym))
            if pick is None:
                skips["no_strike_in_band"] += 1
                continue
            close, oi, lot = puts[sym][pick]
            lot = lot or inp.lots.get(sym, 0)
            if not lot:
                skips["no_lot_size"] += 1
                continue
            if oi < MIN_OI_LOTS * lot:
                skips["strike_oi_below_50_lots"] += 1
                continue
            if i + 1 >= len(cal):
                continue
            pending[sym] = {"symbol": sym, "sector": k, "signal_date": d, "expiry": pick[0], "strike": pick[1],
                            "spot": spot.get(sym), "lot": lot,
                            "trigger": "both" if miss and weak else "results_miss" if miss else "weak_stock"}
        if n_day % 50 == 0:
            log.info("%s: %d of %d sessions, %d trades closed, %d open", d, n_day, len(days), len(done), len(open_trades))
    skips["still_open_at_end"] = len(open_trades)
    return _trades_frame(done), skips


def _trades_frame(done: list[dict]) -> pd.DataFrame:
    rows = []
    for t in done:
        qty, entry, ex = t["qty"], t["entry_price"], t["exit_price"]
        cost = entry * qty + t["buy_charges"]
        if ex is None:
            proceeds = sell = None
        else:
            sell = ch.leg("PE", "SELL", qty, ex)["total"] if ex > 0 else 0.0
            proceeds = ex * qty - sell
        net = None if proceeds is None else proceeds - cost
        rows.append({"signal_date": t["signal_date"], "entry_date": t["entry_date"], "exit_date": t["exit_date"],
                     "symbol": t["symbol"], "sector": t["sector"], "trigger": t["trigger"], "expiry": t["expiry"],
                     "strike": t["strike"], "spot": t["spot"], "lot": qty, "entry_price": entry, "exit_price": ex,
                     "exit_reason": t["exit_reason"], "cost": round(cost, 2),
                     "charges": None if sell is None else round(t["buy_charges"] + sell, 2),
                     "net": None if net is None else round(net, 2),
                     "net_return_pct": None if net is None else round(net / cost * 100, 3), "excluded": t["excluded"]})
    return pd.DataFrame(rows, columns=["signal_date", "entry_date", "exit_date", "symbol", "sector", "trigger", "expiry",
                                       "strike", "spot", "lot", "entry_price", "exit_price", "exit_reason", "cost",
                                       "charges", "net", "net_return_pct", "excluded"])


def summarise(trades: pd.DataFrame) -> pd.DataFrame:
    """Per period of the entry date (and all): N, hit rate, net mean / median return, net per Rs 1,000,
    date-clustered t, worst 5 %, each exit reason's share. Excluded trades are left out."""
    t = trades[trades["excluded"].fillna("") == ""]
    out = []
    for name, a, b in (("all", "0000", "9999"),) + PERIODS:
        g = t[(t["entry_date"] >= a) & (t["entry_date"] <= b)]
        n = len(g)
        r = g["net_return_pct"].astype(float)
        row = {"period": name, "n": n, "hit_rate_pct": round((g["net"] > 0).mean() * 100, 2) if n else None,
               "mean_net_return_pct": round(r.mean(), 3) if n else None,
               "median_net_return_pct": round(r.median(), 3) if n else None,
               "net_per_1000": round(g["net"].sum() / g["cost"].sum() * 1000, 2) if n else None,
               "t_clustered": clustered_t(r, g["entry_date"]) if n > 1 else None,
               "worst_5pct_return_pct": round(float(np.percentile(r, 5)), 3) if n else None}
        for reason in EXIT_REASONS:
            row[f"exit_{reason}_pct"] = round((g["exit_reason"] == reason).mean() * 100, 2) if n else None
        out.append(row)
    return pd.DataFrame(out)


# ---------------------------------------------------------------- real inputs
def load_inputs(since: str, eod2_dir: Path, cache_dir: Path) -> Inputs:
    from .backtest_cheap_options import _read_index
    from .equity import load_symbol
    from .events.store import Store
    from .nse_fo import BhavcopyUnavailable, download_fo_opens
    from .sectors import BENCHMARK, index_closes, load_map
    from .universe import fetch_fo_lots

    cal = [t.strftime("%Y-%m-%d") for t in _read_index(eod2_dir).index]
    sector_of = load_map()
    sector = {k: index_closes(k, eod2_dir) for k in sorted(set(sector_of.values()))}
    cols = ["TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "OpnIntrst", "UndrlygPric", "NewBrdLotQty"]

    def bhav(d: str):
        f = cache_dir / f"fo_bhavcopy_{d.replace('-', '')}.csv"
        if not f.exists():
            return None
        b = pd.read_csv(f, usecols=lambda c: c in cols)
        return b[b["FinInstrmTp"].isin(["STF"]) | ((b["FinInstrmTp"] == "STO") & (b["OptnTp"] == "PE"))]

    def opens(d: str):
        try:
            return download_fo_opens(date.fromisoformat(d), cache_dir)
        except (BhavcopyUnavailable, OSError, ValueError) as exc:
            log.warning("opens %s: %s", d, exc)
            return None

    stock = {}
    for sym in sorted(sector_of):
        try:
            stock[sym] = load_symbol(sym, eod2_dir)["Close"]
        except Exception:  # noqa: BLE001 - not every mapped stock has eod2 history
            continue
    with Store() as st:
        results: dict[str, list[str]] = {}
        for e in st.all_of_type("results"):
            results.setdefault(e["symbol"], []).append(e["event_date"])
        ban: dict[str, set[str]] = {}
        for e in st.all_of_type("ban"):
            if e.get("subtype") == "in":
                ban.setdefault(e["event_date"], set()).add(e["symbol"])
    return Inputs(cal=cal, bhav=bhav, opens=opens, stock=stock, sector_of=sector_of, sector=sector,
                  bench=index_closes(BENCHMARK, eod2_dir), nifty=_read_index(eod2_dir)["Close"],
                  results=results, ban=ban, lots=fetch_fo_lots(cache_path=cache_dir / "fo_universe.txt"))


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 weak-sector put backtest (numbers only)")
    ap.add_argument("--since", default="2021-01-01")
    ap.add_argument("--until", default="9999-12-31")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    inp = load_inputs(a.since, a.eod2_dir, a.cache_dir)
    trades, skips = run(inp, a.since, min(a.until, inp.cal[-1]))
    a.out_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(a.out_dir / "s1_trades.csv", index=False)
    summary = summarise(trades)
    summary.to_csv(a.out_dir / "s1_summary.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(f"S1 weak-sector put, {a.since} to {min(a.until, inp.cal[-1])}: {len(trades)} trades "
          f"({(trades['excluded'].fillna('') != '').sum()} excluded for corporate actions)")
    print("signals not traded:", dict(skips))
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
