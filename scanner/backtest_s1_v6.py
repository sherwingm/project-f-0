"""S1 v6 · results-beat continuation, long calls, one lot at Rs 600-8,000 found by walking up the strikes, decay
exit, as strategies/S1_v6_results_beat_walk.md pre-registers it (numbers only).

    python -m scanner.backtest_s1_v6          # test window 2021-2024 only

The signal, costs and corporate-action check are S1 v4's (scanner/backtest_s1_v4.py); slippage sensitivity and the
equity curve are v5's. New here: the strike walk and the decay exit.
"""
from __future__ import annotations

import argparse
import logging
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest_s1_v4 as v4
from . import backtest_s1_v5 as v5
from .backtest_cheap_options import sessions_to
from .backtest_s1_v2 import BIAS, CAPITAL, Market, load_inputs, md, option_universe, tercile
from .build import ROOT
from .option_engine import TICK, choose_expiry, premium_vwap, split_statement, window

log = logging.getLogger("backtest_s1_v6")

# ---------------------------------------------------------------- the pre-registered parameters
BAND = (600.0, 8000.0)                             # one lot at the entry fill (DECISIONS.md, from S1 v6)
MIN_PREMIUM = v4.MIN_PREMIUM                       # ALLOW_LOTTERY=false
T_MINUS = 2                                        # last exit: the second session before expiry, as the paper engine


@dataclass(frozen=True)
class Variant:
    name: str
    decay: int                                     # sessions without a new closing high before the exit
    min_contracts: int                             # contracts traded on day +1


VARIANTS = (Variant("d3_c50", 3, 50), Variant("d5_c50", 5, 50), Variant("d3_c20", 3, 20))
PRIMARY = VARIANTS[0].name                         # the gate
EXIT_REASONS = ("1_decay", "2_t_minus_2")
FILTERS = ("not_a_beat", "raw_move_ge_10", "arm_b_sector_not_strong", "in_ban_on_entry_day", "position_or_cooldown",
           "no_strike_or_expiry", "holdout_guard", "no_day1_prices", "lottery_refused", "walk_below_band",
           "walk_no_liquid_strike_in_band")
DISTANCE_BINS = ([-math.inf, 2, 5, 10, math.inf], ["<= 2 %", "2-5 %", "5-10 %", "> 10 %"])
HELD_BINS = ([0, 3, 5, 10, 20, math.inf], ["1-3", "4-5", "6-10", "11-20", "> 20"])
TRADE_COLUMNS = ["arm", "variant", "entry_date", "exit_date", "exit_reason", "net", "net_pct", "premium_rs", "qty",
                 "entry_price", "exit_price", "charges", "slippage", "excluded", "category", "vol_tercile",
                 "distance_pct", "held"]


# ---------------------------------------------------------------- rules (pure)
@dataclass(frozen=True)
class Quote:
    """One call strike on day +1."""
    strike: float
    contracts: float
    turnover: float
    lot: int
    close: float
    low: float | None = None
    high: float | None = None


def fill_at(q: Quote, min_contracts: int) -> tuple[float, str] | None:
    """The engine fill (scanner/option_engine.entry_fill) with the variant's contract minimum: the day's premium VWAP,
    else the close, + 1 tick; None when fewer than `min_contracts` traded."""
    if not q.contracts >= min_contracts:                       # also catches NaN
        return None
    v = premium_vwap(q.turnover, q.contracts, q.lot, q.strike, q.low, q.high)
    base, source = (v, "vwap") if v is not None else (q.close, "close")
    if base is None or (isinstance(base, float) and math.isnan(base)) or base <= 0:
        return None
    return round(base + TICK, 2), source


def walk_strike(strikes, spot: float, quotes: dict[float, Quote], min_contracts: int,
                band: tuple[float, float] = BAND):
    """From the strike nearest spot (a tie: the lower), upward: the first call that traded >= min_contracts with a
    fill >= Rs 2 and one lot within `band` (Rs 600-8,000). Returns (quote, fill, source, strikes walked past) or the filter
    that stopped the walk."""
    ks = sorted(set(float(k) for k in strikes))
    k0 = v4.call_strike(ks, spot)
    if k0 is None:
        return "no_strike_or_expiry"
    for n, k in enumerate(ks[ks.index(k0):]):
        q = quotes.get(k)
        if q is None or not q.lot > 0:                         # no day +1 row: nothing traded there
            continue
        f = fill_at(q, min_contracts)
        if f is None:                                          # too thin: the next strike up
            continue
        px, source = f
        if px < MIN_PREMIUM:
            return "lottery_refused"
        cost = px * q.lot
        if cost < band[0]:                                     # the strikes above are cheaper still
            return "walk_below_band"
        if cost > band[1]:
            continue
        return q, px, source, n
    return "walk_no_liquid_strike_in_band"


def decay_step(close: float, best: float, stall: int, to_expiry: int, n: int,
               t_minus: int = T_MINUS) -> tuple[float, int, str | None]:
    """One close of an open call: (best close so far, sessions without a new high, exit reason or None); the last
    exit is `t_minus` sessions before expiry (reason "2_t_minus_2" whatever the value)."""
    if close > best:
        best, stall = close, 0
    else:
        stall += 1
    if stall >= n:
        return best, stall, "1_decay"
    if to_expiry <= t_minus:
        return best, stall, "2_t_minus_2"
    return best, stall, None


def reads_holdout(cal_dates: list[date], end: str, expiry: str) -> bool:
    """True when the expiry's T-2 session falls after the test window's last day."""
    return sessions_to(cal_dates, date.fromisoformat(end), date.fromisoformat(expiry)) > T_MINUS


# ---------------------------------------------------------------- the simulation
def day1_quotes(p: pd.DataFrame, sym: str, exp: str) -> dict[float, Quote]:
    rows = p[(p["TckrSymb"] == sym) & (p["XpryDt"].astype(str).str[:10] == exp) & (p["OptnTp"] == "CE")]
    num = lambda v: float(v) if v == v else math.nan              # noqa: E731 (NaN-safe)
    return {float(r["StrkPric"]): Quote(float(r["StrkPric"]), num(r["TtlTradgVol"]), num(r["TtlTrfVal"]),
                                        int(r["NewBrdLotQty"]) if r["NewBrdLotQty"] == r["NewBrdLotQty"] else 0,
                                        num(r["ClsPric"]), num(r["LwPric"]), num(r["HghPric"]))
            for _, r in rows.iterrows()}


def simulate(m: Market, sigs: list, arm: str, var: Variant, days: v4.Days, ban: dict[str, set[str]],
             universe: dict[str, set[str]], category, funnel: Counter, end: str) -> pd.DataFrame:
    history: dict[str, list[tuple[int, int]]] = {}
    rows = []
    for s in sigs:
        if arm == "B" and not v4.strong_sector(s.state):
            funnel["arm_b_sector_not_strong"] += 1
            continue
        d0, d1 = m.cal[s.i0], m.cal[s.i0 + 1]
        if s.symbol in ban.get(d1, set()):
            funnel["in_ban_on_entry_day"] += 1
            continue
        if v4.blocked(history.get(s.symbol, []), s.i0):
            funnel["position_or_cooldown"] += 1
            continue
        b0 = days.bhav(d0)
        chain = b0["chain"].get(s.symbol) if b0 else None
        exp = choose_expiry(chain["XpryDt"], m.cal_dates, m.cal_dates[s.i0]) if chain is not None else None
        spot = b0["spot"].get(s.symbol) if b0 else None
        if exp is None or not spot:
            funnel["no_strike_or_expiry"] += 1
            continue
        if reads_holdout(m.cal_dates, end, exp):
            funnel["holdout_guard"] += 1
            continue
        p = days.prices(d1)
        if p is None:
            funnel["no_day1_prices"] += 1
            continue
        w = walk_strike(chain.loc[chain["XpryDt"] == exp, "StrkPric"], spot, day1_quotes(p, s.symbol, exp),
                        var.min_contracts)
        if isinstance(w, str):
            funnel[w] += 1
            continue
        q, entry, src, walked = w
        k, lot = q.strike, q.lot
        uv = np.array([m.vol[x][s.i0] for x in universe.get(d0, ()) if x in m.vol and not math.isnan(m.vol[x][s.i0])])
        own = m.vol[s.symbol][s.i0]
        terc = tercile(own, uv) if len(uv) and not math.isnan(own) else None
        cat, _ = category(s.symbol, d0)
        t = _path(m, s, exp, k, entry, var.decay, days)
        history.setdefault(s.symbol, []).append((s.i0 + 1, t["exit_i"]))
        slip = v4.SLIPPAGE.get(cat, v4.SLIPPAGE["unknown"])
        charges = slippage = net = None
        if not t["excluded"]:
            charges, slippage, net = v4.net_of(entry, t["exit_price"], lot, slip)
        rows.append({"arm": arm, "variant": var.name, "signal_date": d0, "entry_date": d1, "symbol": s.symbol,
                     "category": cat, "sector": m.sector_of.get(s.symbol, ""), "ar0_pct": round(s.ar0, 3),
                     "raw0_pct": round(s.raw, 3), "expiry": exp, "spot0": round(float(spot), 2), "strike": k,
                     "strikes_walked": walked, "distance_pct": round((k / float(spot) - 1) * 100, 3),
                     "contracts_day1": q.contracts, "lot": lot, "lots": 1, "qty": lot, "vol_tercile": terc,
                     "entry_price": entry, "entry_source": src, "premium_rs": round(entry * lot, 2),
                     "exit_date": m.cal[t["exit_i"]], "exit_reason": t["reason"], "exit_price": t["exit_price"],
                     "held": t["exit_i"] - (s.i0 + 1), "charges": charges, "slippage": slippage, "net": net,
                     "net_pct": None if net is None else round(net / (entry * lot) * 100, 3), "excluded": t["excluded"]})
        funnel["traded"] += 1
    return pd.DataFrame(rows, columns=None if rows else TRADE_COLUMNS)


def _path(m: Market, s, exp: str, k: float, entry: float, decay: int, days: v4.Days) -> dict:
    """v4's path (contract and corporate-action checks) with the decay / T-2 exits."""
    e = s.i0 + 1
    best, stall = entry, 0
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
            if abs((f / fut0) / (px / stock0) - 1) > v4.CA_TOLERANCE:
                return {"exit_i": j, "reason": None, "exit_price": None, "excluded": "price_adjusted"}
        best, stall, reason = decay_step(c, best, stall, sessions_to(m.cal_dates, m.cal_dates[j],
                                                                     date.fromisoformat(exp)), decay)
        if reason:
            return {"exit_i": j, "reason": reason, "exit_price": max(0.0, round(c - TICK, 2)), "excluded": ""}
        j += 1
    return {"exit_i": len(m.cal) - 1, "reason": None, "exit_price": None, "excluded": "no_exit_in_data"}


# ---------------------------------------------------------------- summaries
def metrics(g: pd.DataFrame) -> dict:
    """v4's metrics with v6's exit reasons."""
    row = {k: v for k, v in v4.metrics(g).items() if not k.startswith("exit_")}
    ok = g[g["excluded"].fillna("") == ""]
    for reason in EXIT_REASONS:
        row[f"exit_{reason}_pct"] = round((ok["exit_reason"] == reason).mean() * 100, 2) if len(ok) else None
    row["mean_held"] = round(ok["held"].astype(float).mean(), 1) if len(ok) else None
    return row


def _group(trades: pd.DataFrame, arm: str, var: str) -> pd.DataFrame:
    return trades[(trades["arm"] == arm) & (trades["variant"] == var)]


def summarise(trades: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{"arm": arm, "variant": v.name, "period": name, **metrics(gp)}
                         for arm in v4.ARMS for v in VARIANTS
                         for name, gp in v4.periods(_group(trades, arm, v.name), "entry_date")])


def breakdown(trades: pd.DataFrame, col: str, groups) -> pd.DataFrame:
    """Primary variant, overall test window, by `col`."""
    return pd.DataFrame([{"arm": arm, col: grp, **metrics(g[g[col] == grp])}
                         for arm in v4.ARMS for g in [_group(trades, arm, PRIMARY)] for grp in groups])


def gate(trades: pd.DataFrame, arm: str) -> list[dict]:
    """DECISIONS.md gate on the primary variant (v4.gate reads the variant labelled 20)."""
    return v4.gate(_group(trades, arm, PRIMARY).assign(variant=20), arm)


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v6 results-beat long calls, strike walk, decay exit (numbers only)")
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
    sigs = v4.signals(m, inp.results, universe, start, last_i, base)
    days = v4.Days(a.cache_dir, prices)
    frames, funnels = [], {}
    for arm in v4.ARMS:
        for var in VARIANTS:
            f = Counter(base)
            frames.append(simulate(m, sigs, arm, var, days, inp.ban, universe, inp.category, f, end))
            funnels[(arm, var.name)] = f
    trades = pd.concat(frames, ignore_index=True)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(a.out_dir / "S1_v6_trades.csv", index=False)
    if not trades.empty:
        trades["distance_bin"] = pd.cut(trades["distance_pct"].astype(float), bins=DISTANCE_BINS[0],
                                        labels=DISTANCE_BINS[1]).astype(str)
        trades["held_bin"] = pd.cut(trades["held"].astype(float) + 1, bins=HELD_BINS[0], labels=HELD_BINS[1]).astype(str)
    else:
        trades["distance_bin"] = trades["held_bin"] = pd.Series(dtype=str)

    sessions = [d for d in m.cal if start <= d <= end]
    sec = {}
    sec["1"] = "\n".join([
        "## 1. Header", "",
        f"- {split_statement((sessions[0], sessions[-1]))} A signal is taken only if day +1 + {v4.MAX_HOLD} sessions "
        f"and its expiry's T-{T_MINUS} session fall on or before {end}, so no trade reads a holdout price.",
        f"- Sessions cached: {sum(d in universe for d in sessions)} of {len(sessions)}.", f"- {BIAS}",
        "- Definition: strategies/S1_v6_results_beat_walk.md (pre-registered). Long calls only; 1 lot at "
        f"Rs {BAND[0]:,.0f}-{BAND[1]:,.0f}, walking up from the at-the-money strike; exit after N sessions without a "
        f"new closing high, or at T-{T_MINUS}. Variants: " +
        ", ".join(f"{v.name} (decay {v.decay}, >= {v.min_contracts} contracts)" for v in VARIANTS) +
        f"; the gate uses {PRIMARY}.", ""])
    sec["2"] = ("## 2. Diagnostic: the signals as a 1-lot stock future (not a trade), bought at the day +1 close, "
                f"net of {v4.FUT_COST_PCT:g} % round trip, % of notional\n\n" +
                md(v4.summarise_futures(v4.futures_diagnostic(m, sigs, inp.ban))))
    funnel = pd.DataFrame([{"arm": k[0], "variant": k[1], "results_signals": f["results_signals"],
                            "no_options_or_prices_on_day0": f["no_options_or_prices_on_day0"],
                            **{x: f[x] for x in FILTERS}, "traded": f["traded"],
                            "excluded_corporate_action": int((_group(trades, *k)["excluded"].fillna("") != "").sum())}
                           for k, f in funnels.items()])
    sec["3"] = ("## 3. Main tables: one long call, net of charges and slippage by AMFI category\n\n" +
                md(summarise(trades)) + "\nSignals removed by each filter, in order:\n\n" + md(funnel))
    sec["4"] = (f"## 4. Breakdowns ({PRIMARY}, 2021-24)\n\nBy AMFI category:\n\n" +
                md(breakdown(trades, "category", ("large", "mid", "small", "unknown"))) +
                "\nBy 20-day volatility tercile (within day 0's universe):\n\n" +
                md(breakdown(trades, "vol_tercile", ("low", "mid", "high"))) +
                "\nBy strike distance above spot:\n\n" + md(breakdown(trades, "distance_bin", DISTANCE_BINS[1])) +
                "\nBy sessions held (entry day = 1):\n\n" + md(breakdown(trades, "held_bin", HELD_BINS[1])))
    sens = [summarise(v5.with_flat_slippage(trades, r)).assign(slippage=f"flat {r:.0%}") for r in v5.SENSITIVITY]
    sec["5"] = "## 5. Sensitivity (flat slippage per side)\n\n" + md(pd.concat(sens, ignore_index=True))
    curve, dd, dd_pct = v5.equity_curve(_group(trades, "A", PRIMARY))
    sec["6"] = (f"## 6. Equity curve (arm A, {PRIMARY}, by exit month)\n\n" + md(curve) +
                f"\nMaximum drawdown: Rs {dd:,.2f} ({dd_pct:g} % of Rs {CAPITAL:,.0f} paper capital).\n")
    sec["7"] = f"## 7. Gate (DECISIONS.md, test window, {PRIMARY})\n\n" + "\n".join(
        f"### Arm {arm}\n\n" + md(pd.DataFrame(gate(trades, arm))) for arm in v4.ARMS)
    (a.out_dir / "S1_v6_backtest_report.md").write_text(
        "# S1 v6 backtest report\n\nNumbers only.\n\n" + "\n".join(sec[k] for k in "1234567"), encoding="utf-8")
    print("\n".join(sec[k] for k in "237"))


if __name__ == "__main__":
    main()
