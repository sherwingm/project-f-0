"""S1 v4 · results-beat continuation, long calls only, as strategies/S1_v4_results_beat.md pre-registers it.

    python -m scanner.backtest_s1_v4          # test window 2021-2024 only; numbers only

Entry fills and the expiry rule come from scanner/option_engine.py; day-0 and sector machinery from S1 v2.
"""
from __future__ import annotations

import argparse
import logging
import math
from collections import Counter, OrderedDict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from server import charges as ch

from .backtest_cheap_options import sessions_to
from .backtest_s1_v2 import BIAS, Market, _ret, budget, day0_index, load_inputs, lots_for, md, option_universe
from .build import ROOT
from .option_engine import TEST_PERIODS, TICK, choose_expiry, entry_fill, split_statement, window
from .results_coverage import benchmark_returns
from .stats import clustered_t

log = logging.getLogger("backtest_s1_v4")

# ---------------------------------------------------------------- the pre-registered parameters
BEAT_PCT, RAW_CAP_PCT = 2.0, 10.0
COOLDOWN = 10
MIN_PREMIUM = 2.0                                  # ALLOW_LOTTERY=false
STOP, EXPIRY_BUFFER, TRAIL_ARM, TRAIL_KEEP = 0.5, 5, 2.0, 0.75
VARIANTS = (20, 5)                                 # exit 3: sessions since entry
MAX_HOLD = 20                                      # no trade may read a holdout price: day +1 + 20 <= window end
SLIPPAGE = {"large": 0.01, "mid": 0.02, "small": 0.03, "unknown": 0.03}
FUT_COST_PCT = 0.1                                 # diagnostic: round trip, % of notional
CA_TOLERANCE = 0.03
EXIT_REASONS = ("1_stop", "2_expiry", "3_time", "4_trailing")
FILTERS = ("not_a_beat", "raw_move_ge_10", "arm_b_sector_not_strong", "in_ban_on_entry_day", "position_or_cooldown",
           "no_strike_or_expiry", "liquidity_lt_50_contracts", "lottery_refused", "budget_below_one_lot")
ARMS = ("A", "B")


# ---------------------------------------------------------------- rules (pure)
def strong_sector(state) -> bool:
    """Arm B: leave-one-out 21- and 63-session returns above NIFTY 500's and the level above its 50-session average."""
    return state is not None and state[0] > 0 and state[1] > 0 and not state[2]


def call_strike(strikes, spot: float) -> float | None:
    ks = sorted(set(float(k) for k in strikes))
    return min(ks, key=lambda k: (abs(k - spot), k)) if ks and spot else None      # a tie: the lower


def exit_reason(close: float, entry: float, peak: float, held: int, to_expiry: int, max_sessions: int) -> str | None:
    if close <= STOP * entry:
        return "1_stop"
    if to_expiry <= EXPIRY_BUFFER:
        return "2_expiry"
    if held >= max_sessions:
        return "3_time"
    if peak >= TRAIL_ARM * entry and close < TRAIL_KEEP * peak:
        return "4_trailing"
    return None


def blocked(history: list[tuple[int, int]], i0: int) -> bool:
    """One position per stock and a 10-session cooldown: history = [(entry_i, exit_i)] of earlier trades."""
    return any(i0 <= ex + COOLDOWN for _, ex in history)


def net_of(entry: float, exit_: float, qty: int, slip: float) -> tuple[float, float, float]:
    """(charges, slippage, net) for a bought call."""
    c = ch.leg("CE", "BUY", qty, entry)["total"] + (ch.leg("CE", "SELL", qty, exit_)["total"] if exit_ > 0 else 0.0)
    s = slip * qty * (entry + exit_)
    return round(c, 2), round(s, 2), round((exit_ - entry) * qty - c - s, 2)


# ---------------------------------------------------------------- signals
@dataclass
class Signal:
    symbol: str
    i0: int
    ar0: float
    raw: float
    state: tuple | None


def signals(m: Market, results: list, universe: dict[str, set[str]], start: str, last_i: int,
            funnel: Counter) -> list[Signal]:
    """Beats with day 0 in the window and day +1 + 20 sessions inside it, one per stock and day 0, in date order."""
    seen, out = set(), []
    for sym, d, t in results:
        i0 = day0_index(m.cal, d, t)
        if i0 is None or i0 < 1 or m.cal[i0] < start or i0 + 1 + MAX_HOLD > last_i:
            continue
        if (sym, i0) in seen:
            continue
        seen.add((sym, i0))
        funnel["results_signals"] += 1
        if sym not in universe.get(m.cal[i0], set()) or sym not in m.close:
            funnel["no_options_or_prices_on_day0"] += 1
            continue
        br, _ = benchmark_returns(m, sym)
        raw = _ret(m.close[sym], i0, 1) * 100
        ar0 = raw - br[i0] * 100
        if math.isnan(ar0) or ar0 < BEAT_PCT:
            funnel["not_a_beat"] += 1
            continue
        if raw >= RAW_CAP_PCT:
            funnel["raw_move_ge_10"] += 1
            continue
        out.append(Signal(sym, i0, ar0, raw, m.state(sym, i0 - 1) if m.loo(sym) is not None else None))
    return sorted(out, key=lambda s: (s.i0, s.symbol))


# ---------------------------------------------------------------- day data (cached, chronological access)
class Days:
    def __init__(self, cache_dir: Path, prices, size: int = 60):
        self.cache_dir, self.prices, self.size = cache_dir, prices, size
        self._b: OrderedDict = OrderedDict()

    def bhav(self, d: str) -> dict | None:
        """{'calls': {(sym, expiry, strike): close}, 'futs': {(sym, expiry): close}, 'spot': {sym: spot},
        'chain': {sym: DataFrame of calls}, 'lot': {sym: lot}} for session d."""
        if d in self._b:
            self._b.move_to_end(d)
            return self._b[d]
        f = self.cache_dir / f"fo_bhavcopy_{d.replace('-', '')}.csv"
        if not f.exists():
            return None
        cols = ["TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "OpnIntrst", "UndrlygPric",
                "NewBrdLotQty"]
        b = pd.read_csv(f, usecols=lambda c: c in cols)
        b["XpryDt"] = b["XpryDt"].astype(str).str[:10]
        ce = b[(b["FinInstrmTp"] == "STO") & (b["OptnTp"] == "CE")]
        fut = b[b["FinInstrmTp"] == "STF"].sort_values("XpryDt")
        spot = {}
        if "UndrlygPric" in b.columns:
            u = b[(b["FinInstrmTp"] == "STO") & (b["UndrlygPric"] > 0)].drop_duplicates("TckrSymb")
            spot = dict(zip(u["TckrSymb"], u["UndrlygPric"].astype(float)))
        for s, c in zip(fut["TckrSymb"], fut["ClsPric"]):
            spot.setdefault(s, float(c))
        day = {"calls": dict(zip(zip(ce["TckrSymb"], ce["XpryDt"], ce["StrkPric"].astype(float)), ce["ClsPric"].astype(float))),
               "futs": dict(zip(zip(fut["TckrSymb"], fut["XpryDt"]), fut["ClsPric"].astype(float))),
               "spot": spot, "chain": {s: g for s, g in ce.groupby("TckrSymb")}}
        self._b[d] = day
        if len(self._b) > self.size:
            self._b.popitem(last=False)
        return day


# ---------------------------------------------------------------- the simulation
def simulate(m: Market, sigs: list[Signal], arm: str, max_sessions: int, days: Days, ban: dict[str, set[str]],
             universe: dict[str, set[str]], category, funnel: Counter) -> pd.DataFrame:
    history: dict[str, list[tuple[int, int]]] = {}
    rows = []
    for s in sigs:
        if arm == "B" and not strong_sector(s.state):
            funnel["arm_b_sector_not_strong"] += 1
            continue
        d0, d1 = m.cal[s.i0], m.cal[s.i0 + 1]
        if s.symbol in ban.get(d1, set()):
            funnel["in_ban_on_entry_day"] += 1
            continue
        if blocked(history.get(s.symbol, []), s.i0):
            funnel["position_or_cooldown"] += 1
            continue
        b0 = days.bhav(d0)
        chain = b0["chain"].get(s.symbol) if b0 else None
        exp = choose_expiry(chain["XpryDt"], m.cal_dates, m.cal_dates[s.i0]) if chain is not None else None
        k = call_strike(chain.loc[chain["XpryDt"] == exp, "StrkPric"], b0["spot"].get(s.symbol)) if exp else None
        if k is None:
            funnel["no_strike_or_expiry"] += 1
            continue
        p = days.prices(d1)
        row = None if p is None else p[(p["TckrSymb"] == s.symbol) & (p["XpryDt"].astype(str).str[:10] == exp)
                                       & (p["StrkPric"].astype(float) == k) & (p["OptnTp"] == "CE")]
        if row is None or row.empty:
            funnel["liquidity_lt_50_contracts"] += 1
            continue
        r = row.iloc[0]
        lot = int(r["NewBrdLotQty"]) if r["NewBrdLotQty"] == r["NewBrdLotQty"] else 0
        fill = entry_fill(float(r["TtlTradgVol"]), float(r["TtlTrfVal"]), lot, k, float(r["ClsPric"]),
                          float(r["LwPric"]), float(r["HghPric"]))
        if fill is None:
            funnel["liquidity_lt_50_contracts"] += 1
            continue
        entry, src = fill
        if entry < MIN_PREMIUM:
            funnel["lottery_refused"] += 1
            continue
        uv = np.array([m.vol[x][s.i0] for x in universe.get(d0, ()) if x in m.vol and not math.isnan(m.vol[x][s.i0])])
        own = m.vol[s.symbol][s.i0]
        if not len(uv) or math.isnan(own) or own <= 0 or lot <= 0:
            funnel["budget_below_one_lot"] += 1
            continue
        bud = budget(own, float(np.median(uv)))
        lots = lots_for(bud, entry * lot)
        if lots < 1:
            funnel["budget_below_one_lot"] += 1
            continue
        cat, _ = category(s.symbol, d0)
        t = _path(m, s, exp, k, entry, max_sessions, days)
        history.setdefault(s.symbol, []).append((s.i0 + 1, t["exit_i"]))
        qty = lot * lots
        slip = SLIPPAGE.get(cat, SLIPPAGE["unknown"])
        charges = slippage = net = None
        if not t["excluded"]:
            charges, slippage, net = net_of(entry, t["exit_price"], qty, slip)
        rows.append({"arm": arm, "variant": max_sessions, "signal_date": d0, "entry_date": d1, "symbol": s.symbol,
                     "category": cat, "sector": m.sector_of.get(s.symbol, ""), "ar0_pct": round(s.ar0, 3),
                     "raw0_pct": round(s.raw, 3), "expiry": exp, "strike": k, "lot": lot, "lots": lots, "qty": qty,
                     "budget": round(bud, 2), "entry_price": entry, "entry_source": src, "premium_rs": round(entry * qty, 2),
                     "exit_date": m.cal[t["exit_i"]], "exit_reason": t["reason"], "exit_price": t["exit_price"],
                     "held": t["exit_i"] - (s.i0 + 1), "charges": charges, "slippage": slippage, "net": net,
                     "net_pct": None if net is None else round(net / (entry * qty) * 100, 3), "excluded": t["excluded"]})
        funnel["traded"] += 1
    return pd.DataFrame(rows)


def _path(m: Market, s: Signal, exp: str, k: float, entry: float, max_sessions: int, days: Days) -> dict:
    e = s.i0 + 1
    peak = -math.inf
    fut0 = stock0 = None
    j = e
    while j < len(m.cal):
        b = days.bhav(m.cal[j])
        if b is None:
            j += 1
            continue
        c = b["calls"].get((s.symbol, exp, k))
        px = m.close[s.symbol][j]
        f = b["futs"].get((s.symbol, exp))
        if c is None:
            return {"exit_i": j, "reason": None, "exit_price": None, "excluded": "contract_changed"}
        if fut0 is None:
            fut0, stock0 = f, px
        elif f and fut0 and stock0 and not (math.isnan(px) or math.isnan(stock0)):
            if abs((f / fut0) / (px / stock0) - 1) > CA_TOLERANCE:
                return {"exit_i": j, "reason": None, "exit_price": None, "excluded": "price_adjusted"}
        peak = max(peak, c)
        reason = exit_reason(c, entry, peak, j - e, sessions_to(m.cal_dates, m.cal_dates[j], date.fromisoformat(exp)),
                             max_sessions)
        if reason:
            return {"exit_i": j, "reason": reason, "exit_price": max(0.0, round(c - TICK, 2)), "excluded": ""}
        j += 1
    return {"exit_i": len(m.cal) - 1, "reason": None, "exit_price": None, "excluded": "no_exit_in_data"}


# ---------------------------------------------------------------- the futures diagnostic (not a trade)
def futures_diagnostic(m: Market, sigs: list[Signal], ban: dict[str, set[str]]) -> pd.DataFrame:
    rows = []
    for s in sigs:
        if s.symbol in ban.get(m.cal[s.i0 + 1], set()):
            continue
        a, e = m.close[s.symbol], s.i0 + 1
        for arm in ARMS:
            if arm == "B" and not strong_sector(s.state):
                continue
            for h in VARIANTS:
                r = (_ret(a, e + h, h) * 100 - FUT_COST_PCT) if e + h < len(m.cal) else math.nan
                rows.append({"arm": arm, "horizon": h, "signal_date": m.cal[s.i0], "symbol": s.symbol, "net_pct": r})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- summaries
def _dist(v: pd.Series) -> dict:
    n = len(v)
    q = (lambda p: round(float(np.percentile(v, p)), 3)) if n else (lambda p: None)
    return {"p10": q(10), "p90": q(90), "worst_5pct": q(5)}


def metrics(g: pd.DataFrame) -> dict:
    g = g[g["excluded"].fillna("") == ""]
    n = len(g)
    r = g["net_pct"].astype(float)
    row = {"n": n, "hit_rate_pct": round((g["net"] > 0).mean() * 100, 2) if n else None,
           "mean_pct": round(r.mean(), 3) if n else None, "median_pct": round(r.median(), 3) if n else None,
           "mean_rs": round(g["net"].mean(), 2) if n else None, "median_rs": round(g["net"].median(), 2) if n else None,
           "net_per_1000": round(g["net"].sum() / g["premium_rs"].sum() * 1000, 2) if n else None,
           "t_clustered": clustered_t(r, g["entry_date"]) if n > 1 else None, **_dist(r)}
    for reason in EXIT_REASONS:
        row[f"exit_{reason}_pct"] = round((g["exit_reason"] == reason).mean() * 100, 2) if n else None
    return row


def periods(df: pd.DataFrame, col: str) -> list[tuple[str, pd.DataFrame]]:
    return [("2021-24", df)] + [(n, df[df[col].between(a, b)]) for n, a, b in TEST_PERIODS]


def summarise(trades: pd.DataFrame) -> pd.DataFrame:
    out = []
    for arm in ARMS:
        for v in VARIANTS:
            g = trades[(trades["arm"] == arm) & (trades["variant"] == v)] if not trades.empty else trades
            for name, gp in periods(g, "entry_date"):
                out.append({"arm": arm, "exit_after": v, "period": name, **metrics(gp)})
    return pd.DataFrame(out)


def summarise_futures(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for arm in ARMS:
        for h in VARIANTS:
            g = df[(df["arm"] == arm) & (df["horizon"] == h)]
            for name, gp in periods(g, "signal_date"):
                x = gp.dropna(subset=["net_pct"])
                v = x["net_pct"]
                out.append({"arm": arm, "horizon": h, "period": name, "n": len(v),
                            "hit_rate_pct": round((v > 0).mean() * 100, 2) if len(v) else None,
                            "mean_pct": round(v.mean(), 3) if len(v) else None,
                            "median_pct": round(v.median(), 3) if len(v) else None, **_dist(v),
                            "t_clustered": clustered_t(v, x["signal_date"]) if len(v) > 1 else None})
    return pd.DataFrame(out)


def gate(trades: pd.DataFrame, arm: str) -> list[dict]:
    """DECISIONS.md gate on the test window, 20-session exits."""
    g = trades[(trades["arm"] == arm) & (trades["variant"] == 20)] if not trades.empty else trades
    allm = metrics(g) if not g.empty else {"n": 0, "mean_pct": None, "t_clustered": None}
    rows = [{"test": "net mean > 0 after costs (% of premium)", "value": allm["mean_pct"],
             "result": "pass" if (allm["mean_pct"] or 0) > 0 else "fail"},
            {"test": "date-clustered t >= 2", "value": allm["t_clustered"],
             "result": "pass" if (allm["t_clustered"] or 0) >= 2 else "fail"}]
    for n, a, b in TEST_PERIODS:
        gp = g[g["entry_date"].between(a, b)] if not g.empty else g
        v = metrics(gp)["mean_pct"] if not gp.empty else None
        rows.append({"test": f"positive in {n} (mean %)", "value": v, "result": "pass" if (v or 0) > 0 else "fail"})
    rows.append({"test": "N >= 200", "value": allm["n"], "result": "pass" if allm["n"] >= 200 else "fail"})
    rows.append({"test": "OVERALL", "value": "", "result": "PASS" if all(r["result"] == "pass" for r in rows) else "FAIL"})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v4 results-beat long calls (numbers only)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from .nse_fo import BhavcopyUnavailable, download_fo_prices

    start, end = window()                                       # test window only; the holdout is untouched
    universe = option_universe(a.cache_dir, start, end)
    inp = load_inputs(a.eod2_dir, a.cache_dir, set().union(*universe.values()))
    m = Market(inp)
    last_i = max(i for i, d in enumerate(m.cal) if d <= end)

    def prices(d: str):
        try:
            return download_fo_prices(date.fromisoformat(d), a.cache_dir)
        except (BhavcopyUnavailable, OSError, ValueError) as exc:
            log.warning("prices %s: %s", d, exc)
            return None

    base = Counter()
    sigs = signals(m, inp.results, universe, start, last_i, base)
    days = Days(a.cache_dir, prices)
    frames, funnels = [], {}
    for arm in ARMS:
        for v in VARIANTS:
            f = Counter(base)
            frames.append(simulate(m, sigs, arm, v, days, inp.ban, universe, inp.category, f))
            funnels[(arm, v)] = f
    trades = pd.concat([f for f in frames if not f.empty], ignore_index=True) if any(not f.empty for f in frames) \
        else pd.DataFrame(columns=["arm", "variant", "entry_date", "net", "net_pct", "premium_rs", "excluded", "exit_reason"])
    a.out_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(a.out_dir / "S1_v4_trades.csv", index=False)
    fut = summarise_futures(futures_diagnostic(m, sigs, inp.ban))
    main_t = summarise(trades)
    funnel = pd.DataFrame([{"arm": k[0], "exit_after": k[1], "results_signals": f["results_signals"],
                            "no_options_or_prices_on_day0": f["no_options_or_prices_on_day0"],
                            **{x: f[x] for x in FILTERS}, "traded": f["traded"],
                            "excluded_corporate_action": int(((trades["arm"] == k[0]) & (trades["variant"] == k[1])
                                                              & (trades["excluded"].fillna("") != "")).sum())
                            if not trades.empty else 0} for k, f in funnels.items()])
    sessions = [d for d in m.cal if start <= d <= end]
    head = "\n".join([
        "# S1 v4 backtest report", "", "Numbers only.", "", "## 1. Header", "",
        f"- {split_statement((sessions[0], sessions[-1]))} Signals whose day +1 + {MAX_HOLD} sessions falls after "
        f"{end} are not taken, so no trade reads a holdout price.",
        f"- Sessions cached: {sum(d in universe for d in sessions)} of {len(sessions)}.",
        f"- {BIAS}", "- Definition: strategies/S1_v4_results_beat.md (pre-registered). Long calls only.", ""])
    sec2 = ("## 2. Diagnostic: the signals as a 1-lot stock future (not a trade), bought at the day +1 close, "
            f"net of {FUT_COST_PCT:g} % round trip, % of notional\n\n" + md(fut))
    sec3 = "## 3. Main tables: naked long call, net of charges and slippage\n\n" + md(main_t)
    sec4 = "## 4. Signals removed by each filter, in order\n\n" + md(funnel)
    sec7 = "## 5. Gate (DECISIONS.md, test window, 20-session exits)\n\n" + "\n".join(
        f"### Arm {arm}\n\n" + md(pd.DataFrame(gate(trades, arm))) for arm in ARMS)
    (a.out_dir / "S1_v4_backtest_report.md").write_text("\n".join([head, sec2, sec3, sec4, sec7]), encoding="utf-8")
    print("\n".join([sec2, sec3, sec4, sec7]))


if __name__ == "__main__":
    main()
