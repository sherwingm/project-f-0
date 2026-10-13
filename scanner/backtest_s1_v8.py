"""S1 v8 · calls on any result (beat or miss) in a strong sector, with the live paper rules (arms A, B) as reference,
on recent data, as strategies/S1_v8_strong_sector_any_result.md pre-registers it (numbers only).

    python -m scanner.backtest_s1_v8                      # day 0 from 2025-04-01 to the last session with closes

The window is the holdout, used by the user's choice on 2026-10-14 (see the strategy file). Every arm trades the
live paper rules (S1 v7 `old_expiry`: strike walk, Rs 600-8,000, 50 % stop, 5 sessions without a new closing high,
T-1) through backtest_s1_v7.simulate; only the signals differ.
"""
from __future__ import annotations

import argparse
import logging
import math
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest_s1_v4 as v4
from . import backtest_s1_v6 as v6
from . import backtest_s1_v7 as v7
from .backtest_s1_v2 import BIAS, Market, _ret, day0_index, load_inputs, md, option_universe
from .build import ROOT
from .results_coverage import benchmark_returns
from .stats import clustered_t

log = logging.getLogger("backtest_s1_v8")

START = "2025-04-01"
RULES = v7.Variant("live", near_expiry=False)            # the live paper rules
ARMS = ("S", "S_miss", "A", "B")
PRIMARY = "S"
ARM_NAMES = {"S": "any result in a strong sector (v8)", "S_miss": "misses in a strong sector",
             "A": "all beats (live arm A)", "B": "beats in a strong sector (live arm B)"}
FUT_COST_PCT = 0.1


# ---------------------------------------------------------------- rules (pure)
def kind_of(ar0: float, raw: float) -> str | None:
    """'beat', 'miss' or None (no signal) from the day-0 move vs the sector (AR0) and the raw move, both in %."""
    if math.isnan(ar0) or math.isnan(raw):
        return None
    if ar0 >= v4.BEAT_PCT and raw < v4.RAW_CAP_PCT:
        return "beat"
    if ar0 <= -v4.BEAT_PCT and raw > -v4.RAW_CAP_PCT:
        return "miss"
    return None


def in_arm(arm: str, kind: str, strong: bool) -> bool:
    return {"S": strong, "S_miss": strong and kind == "miss", "A": kind == "beat",
            "B": strong and kind == "beat"}[arm]


def signals_any(m: Market, results: list, universe: dict[str, set[str]], start: str, last_i: int,
                funnel: Counter) -> list[tuple[v4.Signal, str]]:
    """v4.signals with misses kept: [(signal, 'beat' | 'miss')] in date order."""
    seen, out = set(), []
    for sym, d, t in results:
        i0 = day0_index(m.cal, d, t)
        if i0 is None or i0 < 1 or m.cal[i0] < start or i0 + 1 + v4.MAX_HOLD > last_i or (sym, i0) in seen:
            continue
        seen.add((sym, i0))
        funnel["results_signals"] += 1
        if sym not in universe.get(m.cal[i0], set()) or sym not in m.close:
            funnel["no_options_or_prices_on_day0"] += 1
            continue
        br, _ = benchmark_returns(m, sym)
        raw = _ret(m.close[sym], i0, 1) * 100
        k = kind_of(raw - br[i0] * 100, raw)
        if k is None:
            funnel["no_beat_or_miss"] += 1
            continue
        out.append((v4.Signal(sym, i0, raw - br[i0] * 100, raw, m.state(sym, i0 - 1) if m.loo(sym) is not None
                              else None), k))
    return sorted(out, key=lambda x: (x[0].i0, x[0].symbol))


# ---------------------------------------------------------------- summaries
def halves(df: pd.DataFrame, col: str = "entry_date") -> list[tuple[str, pd.DataFrame]]:
    return [("all", df), ("2025", df[df[col].astype(str) < "2026"]), ("2026", df[df[col].astype(str) >= "2026"])]


def summarise(trades: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{"arm": arm, "period": name, **v7.metrics(g)}
                         for arm in ARMS for name, g in halves(trades[trades["arm"] == arm])])


def gate(trades: pd.DataFrame, arm: str) -> list[dict]:
    g = trades[(trades["arm"] == arm) & (trades["excluded"].fillna("") == "")]
    r = g["net_pct"].astype(float)
    t = clustered_t(r, g["entry_date"]) if len(g) > 1 else None
    rows = [{"test": "net mean > 0 after costs (% of premium)", "value": round(r.mean(), 3) if len(g) else None},
            {"test": "date-clustered t >= 2", "value": t}]
    for name, h in halves(g)[1:]:
        rows.append({"test": f"positive in {name} (mean %)", "value": round(h["net_pct"].astype(float).mean(), 3)
                     if len(h) else None})
    rows.append({"test": "N >= 200", "value": len(g)})
    ok = [(rows[0]["value"] or 0) > 0, (rows[1]["value"] or 0) >= 2, (rows[2]["value"] or 0) > 0,
          (rows[3]["value"] or 0) > 0, rows[4]["value"] >= 200]
    for row, good in zip(rows, ok):
        row["result"] = "pass" if good else "fail"
    rows.append({"test": "OVERALL", "value": "", "result": "PASS" if all(ok) else "FAIL"})
    return rows


def futures_diagnostic(m: Market, by_arm: dict[str, list], ban: dict[str, set[str]]) -> pd.DataFrame:
    """The same signals as a long stock position from the day +1 close, 5 and 20 sessions, net of 0.1 %."""
    rows = []
    for arm, sigs in by_arm.items():
        for s in sigs:
            if s.symbol in ban.get(m.cal[s.i0 + 1], set()):
                continue
            a, e = m.close[s.symbol], s.i0 + 1
            for h in (5, 20):
                r = _ret(a, e + h, h) * 100 - FUT_COST_PCT if e + h < len(m.cal) else math.nan
                rows.append({"arm": arm, "horizon": h, "signal_date": m.cal[s.i0], "net_pct": r})
    df = pd.DataFrame(rows).dropna(subset=["net_pct"])
    return pd.DataFrame([{"arm": arm, "horizon": h, "period": name, "n": len(g),
                          "mean_pct": round(g["net_pct"].mean(), 3) if len(g) else None,
                          "hit_rate_pct": round((g["net_pct"] > 0).mean() * 100, 1) if len(g) else None,
                          "t_clustered": clustered_t(g["net_pct"], g["signal_date"]) if len(g) > 1 else None}
                         for arm in by_arm for h in (5, 20)
                         for name, g in halves(df[(df["arm"] == arm) & (df["horizon"] == h)], "signal_date")])


def breakdown(trades: pd.DataFrame, col: str, groups) -> pd.DataFrame:
    return pd.DataFrame([{"arm": arm, col: grp, **v7.metrics(g[g[col] == grp])}
                         for arm in ARMS for g in [trades[trades["arm"] == arm]] for grp in groups])


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v8: any result in a strong sector, with the live rules, recent data")
    ap.add_argument("--start", default=START)
    ap.add_argument("--end", default=None, help="last session (default: the last with stock closes)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    ap.add_argument("--tag", default="S1_v8", help="output file prefix")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from .nse_fo import BhavcopyUnavailable, download_fo_prices

    universe = option_universe(a.cache_dir, a.start, a.end or "9999-12-31")
    inp = load_inputs(a.eod2_dir, a.cache_dir, set().union(*universe.values()))
    m = Market(inp)
    end = min(a.end or m.cal[-1], m.cal[-1])
    last_i = max(i for i, d in enumerate(m.cal) if d <= end)

    def prices(d: str):
        try:
            return download_fo_prices(date.fromisoformat(d), a.cache_dir)
        except (BhavcopyUnavailable, OSError, ValueError) as exc:
            log.warning("prices %s: %s", d, exc)
            return None

    base = Counter()
    sigs = signals_any(m, inp.results, universe, a.start, last_i, base)
    days = v4.Days(a.cache_dir, prices)
    frames, funnels, by_arm = [], {}, {}
    for arm in ARMS:
        f = Counter(base)
        chosen = []
        for s, k in sigs:
            if in_arm(arm, k, v4.strong_sector(s.state)):
                chosen.append(s)
            else:
                f["not_in_arm"] += 1
        by_arm[arm] = chosen
        t = v7.simulate(m, chosen, "A", RULES, days, inp.ban, universe, inp.category, f, end)
        if not t.empty:
            t["arm"] = arm
            kinds = {(s.symbol, m.cal[s.i0]): k for s, k in sigs}
            t["kind"] = [kinds.get((sym, d0), "") for sym, d0 in zip(t["symbol"], t["signal_date"])]
        frames.append(t)
        funnels[arm] = f
    trades = pd.concat(frames, ignore_index=True)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(a.out_dir / f"{a.tag}_trades.csv", index=False)
    if not trades.empty:
        trades["distance_bin"] = pd.cut(trades["distance_pct"].astype(float), bins=v6.DISTANCE_BINS[0],
                                        labels=v6.DISTANCE_BINS[1]).astype(str)
        trades["held_bin"] = pd.cut(trades["held"].astype(float) + 1, bins=v6.HELD_BINS[0],
                                    labels=v6.HELD_BINS[1]).astype(str)

    filt = ("no_options_or_prices_on_day0", "no_beat_or_miss", "not_in_arm", "in_ban_on_entry_day",
            "position_or_cooldown", "no_strike_or_expiry", "holdout_guard", "no_day1_prices", "lottery_refused",
            "walk_below_band", "walk_no_liquid_strike_in_band")
    funnel = pd.DataFrame([{"arm": arm, "results_signals": f["results_signals"], **{x: f[x] for x in filt},
                            "traded": f["traded"]} for arm, f in funnels.items()])
    sessions = [d for d in m.cal if a.start <= d <= end]
    sec = [
        "## 1. Header\n",
        f"- Window: day 0 from {a.start}; the last session with stock closes is {end} ({len(sessions)} sessions). "
        "Every trade, and its expiry's T-1, completes inside the window. This is the holdout (2025 onward), used by "
        "the user's choice on 2026-10-14; see strategies/S1_v8_strong_sector_any_result.md.",
        f"- Arms: " + "; ".join(f"`{k}` {v}" for k, v in ARM_NAMES.items()) + f". Primary: `{PRIMARY}`.",
        "- Every arm trades the live paper rules (S1 v7 old_expiry): 1 call lot, current monthly if >= 10 sessions "
        "remain else next, walk up from ATM to >= 50 contracts and Rs 600-8,000, VWAP + 1 tick; exits 50 % stop, 5 "
        "sessions without a new closing high, T-1.",
        f"- {BIAS}\n",
        "## 2. Futures diagnostic (not a trade): the signals as a long stock position from the day +1 close, net of "
        f"{FUT_COST_PCT:g} %, % of notional\n\n" + md(futures_diagnostic(m, by_arm, inp.ban)),
        "## 3. Main table: one long call, net of charges and slippage\n\n" + md(summarise(trades)) +
        "\nSignals removed by each filter, in order:\n\n" + md(funnel),
        "## 4. Breakdowns (all of the window)\n\nBy beat / miss:\n\n" + md(breakdown(trades, "kind", ("beat", "miss"))) +
        "\nBy strike distance above spot:\n\n" + md(breakdown(trades, "distance_bin", v6.DISTANCE_BINS[1])) +
        "\nBy sessions held (entry day = 1):\n\n" + md(breakdown(trades, "held_bin", v6.HELD_BINS[1])),
        "## 5. Gate (DECISIONS.md), per arm\n\n" + "\n".join(f"### Arm {arm} · {ARM_NAMES[arm]}\n\n" +
                                                         md(pd.DataFrame(gate(trades, arm))) for arm in ARMS),
    ]
    (a.out_dir / f"{a.tag}_backtest_report.md").write_text(
        "# S1 v8 backtest report (recent data)\n\nNumbers only.\n\n" + "\n".join(sec), encoding="utf-8")
    print("\n".join([sec[5], sec[6], sec[8]]))


if __name__ == "__main__":
    main()
