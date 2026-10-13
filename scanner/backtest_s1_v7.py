"""S1 v7 · results-beat continuation, long calls, near-expiry calls allowed, 5-session decay exit + 50 % stop, as
strategies/S1_v7_results_beat_near_expiry.md pre-registers it (numbers only).

    python -m scanner.backtest_s1_v7          # test window 2021-2024 only

The signal, costs and corporate-action check are S1 v4's; the strike walk, fill and decay rule are v6's
(scanner/backtest_s1_v6.py). New here: the current monthly expiry down to 3 sessions left (near-expiry trades: >= 500
contracts, Rs 600-3,000 a lot), the 50 % stop and the T-1 last exit.
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
from . import backtest_s1_v6 as v6
from .backtest_cheap_options import sessions_to
from .backtest_s1_v2 import BIAS, CAPITAL, Market, load_inputs, md, option_universe, tercile
from .build import ROOT
from .option_engine import MIN_SESSIONS_CURRENT, TICK, monthly, split_statement, window

log = logging.getLogger("backtest_s1_v7")

# ---------------------------------------------------------------- the pre-registered parameters
NEAR_MIN_SESSIONS = 3                              # the current monthly is kept down to 3 sessions left
NORMAL_BAND, NEAR_BAND = v6.BAND, (600.0, 3000.0)  # one lot at the entry fill
NORMAL_CONTRACTS = 50
STOP = 0.5                                         # exit when the close <= 50 % of the entry fill
DECAY = 5                                          # sessions without a new closing high
T_MINUS = 1                                        # last exit: the session before expiry


@dataclass(frozen=True)
class Variant:
    name: str
    near_contracts: int = 500                      # contracts on day +1 for a near-expiry strike
    stop: float | None = STOP
    near_expiry: bool = True                       # False: v6's expiry rule (no near-expiry trades)


VARIANTS = (Variant("primary"), Variant("near_c50", near_contracts=50), Variant("no_stop", stop=None),
            Variant("old_expiry", near_expiry=False))
PRIMARY = VARIANTS[0].name
EXIT_REASONS = ("0_stop", "1_decay", "2_t_minus_1")
FILTERS = ("not_a_beat", "raw_move_ge_10", "arm_b_sector_not_strong", "in_ban_on_entry_day", "position_or_cooldown",
           "no_strike_or_expiry", "holdout_guard", "no_day1_prices", "lottery_refused", "walk_below_band",
           "walk_no_liquid_strike_in_band")
TRADE_COLUMNS = ["arm", "variant", "entry_date", "exit_date", "exit_reason", "net", "net_pct", "premium_rs", "qty",
                 "entry_price", "exit_price", "charges", "slippage", "excluded", "category", "vol_tercile",
                 "distance_pct", "held", "near_expiry", "sessions_left"]


# ---------------------------------------------------------------- rules (pure)
def choose_expiry(expiries, cal_dates: list[date], d: date, near_ok: bool = True) -> tuple[str, bool, int] | None:
    """(expiry, near-expiry trade?, sessions left after day 0) for signal day d: the current monthly if >= 10
    sessions remain (normal) or 3-9 remain (near-expiry, when `near_ok`), else the next monthly (normal)."""
    ahead = [e for e in monthly(expiries) if e > d.isoformat()]
    if not ahead:
        return None
    n = sessions_to(cal_dates, d, date.fromisoformat(ahead[0]))
    if n >= MIN_SESSIONS_CURRENT:
        return ahead[0], False, n
    if near_ok and n >= NEAR_MIN_SESSIONS:
        return ahead[0], True, n
    if len(ahead) < 2:
        return None
    return ahead[1], False, sessions_to(cal_dates, d, date.fromisoformat(ahead[1]))


def walk(strikes, spot: float, quotes: dict, near: bool, var: Variant):
    """v6's strike walk with the near-expiry or normal liquidity minimum and band."""
    if near:
        return v6.walk_strike(strikes, spot, quotes, var.near_contracts, band=NEAR_BAND)
    return v6.walk_strike(strikes, spot, quotes, NORMAL_CONTRACTS, band=NORMAL_BAND)


def exit_step(close: float, entry: float, best: float, stall: int, to_expiry: int,
              stop: float | None = STOP) -> tuple[float, int, str | None]:
    """One close of an open call, in the pre-registered order: stop, decay (5), T-1."""
    if stop is not None and close <= stop * entry:
        return best, stall, "0_stop"
    best, stall, reason = v6.decay_step(close, best, stall, to_expiry, DECAY, t_minus=T_MINUS)
    return best, stall, ("2_t_minus_1" if reason == "2_t_minus_2" else reason)


def reads_holdout(cal_dates: list[date], end: str, expiry: str) -> bool:
    """True when the expiry's T-1 session falls after the test window's last day."""
    return sessions_to(cal_dates, date.fromisoformat(end), date.fromisoformat(expiry)) > T_MINUS


# ---------------------------------------------------------------- the simulation
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
        ch = choose_expiry(chain["XpryDt"], m.cal_dates, m.cal_dates[s.i0], var.near_expiry) \
            if chain is not None else None
        spot = b0["spot"].get(s.symbol) if b0 else None
        if ch is None or not spot:
            funnel["no_strike_or_expiry"] += 1
            continue
        exp, near, left = ch
        if reads_holdout(m.cal_dates, end, exp):
            funnel["holdout_guard"] += 1
            continue
        p = days.prices(d1)
        if p is None:
            funnel["no_day1_prices"] += 1
            continue
        w = walk(chain.loc[chain["XpryDt"] == exp, "StrkPric"], spot, v6.day1_quotes(p, s.symbol, exp), near, var)
        if isinstance(w, str):
            funnel[w] += 1
            continue
        q, entry, src, walked = w
        k, lot = q.strike, q.lot
        uv = np.array([m.vol[x][s.i0] for x in universe.get(d0, ()) if x in m.vol and not math.isnan(m.vol[x][s.i0])])
        own = m.vol[s.symbol][s.i0]
        terc = tercile(own, uv) if len(uv) and not math.isnan(own) else None
        cat, _ = category(s.symbol, d0)
        t = _path(m, s, exp, k, entry, var.stop, days)
        history.setdefault(s.symbol, []).append((s.i0 + 1, t["exit_i"]))
        slip = v4.SLIPPAGE.get(cat, v4.SLIPPAGE["unknown"])
        charges = slippage = net = None
        if not t["excluded"]:
            charges, slippage, net = v4.net_of(entry, t["exit_price"], lot, slip)
        rows.append({"arm": arm, "variant": var.name, "signal_date": d0, "entry_date": d1, "symbol": s.symbol,
                     "category": cat, "sector": m.sector_of.get(s.symbol, ""), "ar0_pct": round(s.ar0, 3),
                     "raw0_pct": round(s.raw, 3), "expiry": exp, "near_expiry": near, "sessions_left": left,
                     "spot0": round(float(spot), 2), "strike": k, "strikes_walked": walked,
                     "distance_pct": round((k / float(spot) - 1) * 100, 3), "contracts_day1": q.contracts,
                     "lot": lot, "lots": 1, "qty": lot, "vol_tercile": terc, "entry_price": entry,
                     "entry_source": src, "premium_rs": round(entry * lot, 2), "exit_date": m.cal[t["exit_i"]],
                     "exit_reason": t["reason"], "exit_price": t["exit_price"], "held": t["exit_i"] - (s.i0 + 1),
                     "charges": charges, "slippage": slippage, "net": net,
                     "net_pct": None if net is None else round(net / (entry * lot) * 100, 3), "excluded": t["excluded"]})
        funnel["traded"] += 1
    return pd.DataFrame(rows, columns=None if rows else TRADE_COLUMNS)


def _path(m: Market, s, exp: str, k: float, entry: float, stop: float | None, days: v4.Days) -> dict:
    """v6's path (contract and corporate-action checks) with the stop / decay / T-1 exits."""
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
        best, stall, reason = exit_step(c, entry, best, stall,
                                        sessions_to(m.cal_dates, m.cal_dates[j], date.fromisoformat(exp)), stop)
        if reason:
            return {"exit_i": j, "reason": reason, "exit_price": max(0.0, round(c - TICK, 2)), "excluded": ""}
        j += 1
    return {"exit_i": len(m.cal) - 1, "reason": None, "exit_price": None, "excluded": "no_exit_in_data"}


# ---------------------------------------------------------------- summaries
def metrics(g: pd.DataFrame) -> dict:
    """v4's metrics with v7's exit reasons."""
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
    ap = argparse.ArgumentParser(description="S1 v7 results-beat long calls, near-expiry allowed, 5-session decay + "
                                             "50 % stop (numbers only)")
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
    trades.to_csv(a.out_dir / "S1_v7_trades.csv", index=False)
    if not trades.empty:
        trades["distance_bin"] = pd.cut(trades["distance_pct"].astype(float), bins=v6.DISTANCE_BINS[0],
                                        labels=v6.DISTANCE_BINS[1]).astype(str)
        trades["held_bin"] = pd.cut(trades["held"].astype(float) + 1, bins=v6.HELD_BINS[0],
                                    labels=v6.HELD_BINS[1]).astype(str)
        trades["trade_type"] = np.where(trades["near_expiry"].astype(bool), "near-expiry", "normal")
    else:
        trades["distance_bin"] = trades["held_bin"] = trades["trade_type"] = pd.Series(dtype=str)

    sessions = [d for d in m.cal if start <= d <= end]
    sec = {}
    sec["1"] = "\n".join([
        "## 1. Header", "",
        f"- {split_statement((sessions[0], sessions[-1]))} A signal is taken only if day +1 + {v4.MAX_HOLD} sessions "
        f"and its expiry's T-{T_MINUS} session fall on or before {end}, so no trade reads a holdout price.",
        f"- Sessions cached: {sum(d in universe for d in sessions)} of {len(sessions)}.", f"- {BIAS}",
        "- Definition: strategies/S1_v7_results_beat_near_expiry.md (pre-registered). Long calls only; 1 lot. Current "
        f"monthly expiry if >= {MIN_SESSIONS_CURRENT} sessions remain (normal: >= {NORMAL_CONTRACTS} contracts, "
        f"Rs {NORMAL_BAND[0]:,.0f}-{NORMAL_BAND[1]:,.0f}) or {NEAR_MIN_SESSIONS}-{MIN_SESSIONS_CURRENT - 1} remain "
        f"(near-expiry: Rs {NEAR_BAND[0]:,.0f}-{NEAR_BAND[1]:,.0f}), else the next monthly; walking up from the "
        f"at-the-money strike. Exits: close <= {STOP:.0%} of entry, {DECAY} sessions without a new closing high, "
        f"T-{T_MINUS}. Variants: " + ", ".join(v.name for v in VARIANTS) + f"; the gate uses {PRIMARY}.",
        "- 2021-2024 has been looked at for S1 v2-v6 and what-ifs on v6's trades; a pass here is a first filter only.",
        ""])
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
    sec["4"] = (f"## 4. Breakdowns ({PRIMARY}, 2021-24)\n\nNear-expiry vs normal trades:\n\n" +
                md(breakdown(trades, "trade_type", ("normal", "near-expiry"))) +
                "\nBy AMFI category:\n\n" + md(breakdown(trades, "category", ("large", "mid", "small", "unknown"))) +
                "\nBy 20-day volatility tercile (within day 0's universe):\n\n" +
                md(breakdown(trades, "vol_tercile", ("low", "mid", "high"))) +
                "\nBy strike distance above spot:\n\n" + md(breakdown(trades, "distance_bin", v6.DISTANCE_BINS[1])) +
                "\nBy sessions held (entry day = 1):\n\n" + md(breakdown(trades, "held_bin", v6.HELD_BINS[1])))
    sens = [summarise(v5.with_flat_slippage(trades, r)).assign(slippage=f"flat {r:.0%}") for r in v5.SENSITIVITY]
    sec["5"] = "## 5. Sensitivity (flat slippage per side)\n\n" + md(pd.concat(sens, ignore_index=True))
    curve, dd, dd_pct = v5.equity_curve(_group(trades, "A", PRIMARY))
    sec["6"] = (f"## 6. Equity curve (arm A, {PRIMARY}, by exit month)\n\n" + md(curve) +
                f"\nMaximum drawdown: Rs {dd:,.2f} ({dd_pct:g} % of Rs {CAPITAL:,.0f} paper capital).\n")
    sec["7"] = f"## 7. Gate (DECISIONS.md, test window, {PRIMARY})\n\n" + "\n".join(
        f"### Arm {arm}\n\n" + md(pd.DataFrame(gate(trades, arm))) for arm in v4.ARMS)
    (a.out_dir / "S1_v7_backtest_report.md").write_text(
        "# S1 v7 backtest report\n\nNumbers only.\n\n" + "\n".join(sec[k] for k in "1234567"), encoding="utf-8")
    print("\n".join(sec[k] for k in "2347"))


if __name__ == "__main__":
    main()
