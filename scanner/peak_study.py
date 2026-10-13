"""Hindsight study of S1 arm A trades: the option's path day by day, what alternative exits would have made on the
same paths, the stock's path, and the quality of the quarterly result behind each trade (QoQ / YoY from
data/financials.json). Not a test of anything: the numbers feed the design of a pre-registered exit rule.

    python -m scanner.peak_study            # -> data/results/S1_armA_peak_study_rows.csv (+ a .json of the paths)

Samples: the live rules' arm A on Apr 2025 - Sep 2026 (S1_v8_trades.csv) and on 2021-2024 (S1_v8_check2124_trades.csv).
"""
from __future__ import annotations

import argparse
import bisect
import json
import logging
import math
from pathlib import Path

import pandas as pd

from . import backtest_s1_v4 as v4
from .build import ROOT
from .financials import load as load_financials
from .financials import pct as fin_pct
from .financials import quarter_back
from .option_engine import TICK
from .trade_sheet import CACHE, bhav_sessions, last_day, option_closes

log = logging.getLogger("peak_study")

SAMPLES = {"2025-26": "S1_v8_trades.csv", "2021-24": "S1_v8_check2124_trades.csv"}
STOP, DECAY = 0.5, 5                                 # the live rules, kept under every alternative unless said
TARGETS, TRAILS, FIXED = (0.25, 0.5, 1.0), (0.3, 0.4, 0.5), (2, 3, 5)


# ---------------------------------------------------------------- exit simulators (pure)
def simulate(closes: list[float], entry: float, rule: str) -> tuple[int, float, str]:
    """Apply an exit rule to the option's closes from the entry day (index 0 = day 1) to the last allowed day
    (T-1). Returns (exit index, exit fill = close - 1 tick, reason). Rules:
      live            50 % stop, 5 sessions without a new closing high, T-1
      target:P        sell at the first close >= entry * (1 + P), else live
      trail:D         sell when a close is D below the running peak (the peak starts at the entry), else T-1
      fixed:N         sell at the close of day N, the 50 % stop before it
      combo:P:D       target P or trail D, whichever comes first; the 50 % stop kept
      half:P:D        half the lot at target P, the rest trails D from the peak: the fill is the average
    """
    kind, *args = rule.split(":")
    best, stall = entry, 0
    peak = entry
    half_sold = None
    for i, c in enumerate(closes):
        last = i == len(closes) - 1
        peak = max(peak, c)
        px = max(0.0, round(c - TICK, 2))
        if kind == "live":
            if c <= STOP * entry:
                return i, px, "stop"
            if c > best:
                best, stall = c, 0
            else:
                stall += 1
            if stall >= DECAY:
                return i, px, "decay"
        elif kind == "target":
            if c >= entry * (1 + float(args[0])):
                return i, px, "target"
            if c <= STOP * entry:
                return i, px, "stop"
            if c > best:
                best, stall = c, 0
            else:
                stall += 1
            if stall >= DECAY:
                return i, px, "decay"
        elif kind == "trail":
            if c <= peak * (1 - float(args[0])):
                return i, px, "trail"
        elif kind == "fixed":
            if c <= STOP * entry:
                return i, px, "stop"
            if i + 1 >= int(args[0]):
                return i, px, "fixed"
        elif kind == "combo":
            if c >= entry * (1 + float(args[0])):
                return i, px, "target"
            if c <= STOP * entry:
                return i, px, "stop"
            if c <= peak * (1 - float(args[1])):
                return i, px, "trail"
        elif kind == "half":
            p, d = float(args[0]), float(args[1])
            if half_sold is None:
                if c >= entry * (1 + p):
                    half_sold = px
                    continue
                if c <= STOP * entry:
                    return i, px, "stop"
                if c > best:
                    best, stall = c, 0
                else:
                    stall += 1
                if stall >= DECAY:
                    return i, px, "decay"
            else:
                if c <= peak * (1 - d):
                    return i, round((half_sold + px) / 2, 2), "half+trail"
        else:
            raise ValueError(rule)
        if last:
            return i, round((half_sold + px) / 2, 2) if half_sold is not None else px, "t1"
    return len(closes) - 1, max(0.0, round(closes[-1] - TICK, 2)), "t1"


def rules() -> list[str]:
    out = ["live"] + [f"target:{p}" for p in TARGETS] + [f"trail:{d}" for d in TRAILS] + [f"fixed:{n}" for n in FIXED]
    out += [f"combo:{p}:{d}" for p in (0.5, 1.0) for d in (0.3, 0.4)] + ["half:0.5:0.4", "half:1.0:0.4"]
    return out


def peak_stats(closes: list[float], entry: float) -> dict:
    """Peak % and day (1 = entry day), the lowest close after the peak as % of the peak, the first day of each
    threshold, and the close the day after the first close >= +50 %."""
    if not closes:
        return {}
    pcts = [(c / entry - 1) * 100 for c in closes]
    ip = max(range(len(pcts)), key=lambda i: pcts[i])
    after = pcts[ip + 1:]
    out = {"peak_pct": round(pcts[ip], 2), "peak_day": ip + 1, "days": len(pcts),
           "dd_after_peak_pct": round((min(closes[ip + 1:]) / closes[ip] - 1) * 100, 2) if after else None,
           "end_pct": round(pcts[-1], 2)}
    for thr in (25, 50, 100):
        first = next((i + 1 for i, p in enumerate(pcts) if p >= thr), None)
        out[f"first_day_{thr}"] = first
        out[f"next_after_{thr}"] = round(pcts[first] - pcts[first - 1], 2) if first and first < len(pcts) else None
    return out


# ---------------------------------------------------------------- result quality
def quarter_of(signal_date: str) -> str:
    """The quarter a results filing on `signal_date` reports: the last quarter end before it."""
    y = int(signal_date[:4])
    for q in (f"{y}-09-30", f"{y}-06-30", f"{y}-03-31", f"{y - 1}-12-31"):
        if q < signal_date:
            return q
    return f"{y - 1}-12-31"


def cat_change(v) -> str:
    if v is None or v == "n/m":
        return "n/a"
    return "up" if v > 0 else "down"


def beat_cat(ar0: float) -> str:
    return "<3%" if ar0 < 3 else "3-5%" if ar0 < 5 else ">5%"


def result_quality(fin: dict, symbol: str, signal_date: str) -> dict:
    q = quarter_of(signal_date)
    qs = (fin.get(symbol) or {}).get("quarters") or {}
    cur, prev, ya = qs.get(q) or {}, qs.get(quarter_back(q, 1)) or {}, qs.get(quarter_back(q, 4)) or {}
    out = {"quarter": q, "basis": (fin.get(symbol) or {}).get("basis")}
    for f in ("revenue", "net_profit", "eps"):
        out[f] = cur.get(f)
        out[f"{f}_qoq"] = fin_pct(cur.get(f), prev.get(f)) if cur else None
        out[f"{f}_yoy"] = fin_pct(cur.get(f), ya.get(f)) if cur else None
        out[f"{f}_qoq_cat"] = cat_change(out[f"{f}_qoq"])
        out[f"{f}_yoy_cat"] = cat_change(out[f"{f}_yoy"])
    out["loss_quarter"] = (cur.get("net_profit") is not None and cur["net_profit"] < 0) if cur else None
    out["turned_to_loss"] = bool(cur and prev and cur.get("net_profit") is not None and prev.get("net_profit") is not None
                                 and cur["net_profit"] < 0 <= prev["net_profit"])
    return out


# ---------------------------------------------------------------- build
def build(samples: dict[str, str] = SAMPLES, out_dir: Path = ROOT / "data" / "results",
          eod2_dir: Path = ROOT / "data" / "eod2") -> pd.DataFrame:
    from .equity import load_symbol
    fin = load_financials()
    sessions = bhav_sessions(CACHE)
    rows, paths = [], {}
    for sample, fname in samples.items():
        t = pd.read_csv(out_dir / fname)
        t = t[(t["arm"] == "A") & (t["excluded"].isna())].copy()
        for c in ("signal_date", "entry_date", "exit_date", "expiry"):
            t[c] = t[c].astype(str).str[:10]
        t["last_day"] = [last_day(sessions, e, 1) for e in t["expiry"]]
        closes = option_closes(t, sessions, CACHE)
        stock: dict[str, pd.Series] = {}
        for sym in t["symbol"].unique():
            try:
                f = load_symbol(sym, eod2_dir)
                f.index = f.index.strftime("%Y-%m-%d")
                stock[sym] = f["Close"]
            except Exception as exc:  # noqa: BLE001
                log.info("%s: no eod2 (%s)", sym, exc)
        for r in t.itertuples():
            key = (r.symbol, r.expiry, float(r.strike))
            days = [d for d in sessions[bisect.bisect_left(sessions, r.entry_date):bisect.bisect_right(sessions, r.last_day)]
                    if (d, *key) in closes]
            cl = [closes[(d, *key)] for d in days]
            if not cl:
                continue
            tid = f"{sample}:{r.symbol}:{r.entry_date}"
            paths[tid] = [[d, c] for d, c in zip(days, cl)]
            slip = v4.SLIPPAGE.get(r.category if isinstance(r.category, str) else "unknown", v4.SLIPPAGE["unknown"])
            row = {"id": tid, "sample": sample, "symbol": r.symbol, "sector": r.sector, "category": r.category,
                   "signal_date": r.signal_date, "entry_date": r.entry_date, "expiry": r.expiry, "strike": r.strike,
                   "distance_pct": r.distance_pct, "lot": r.qty, "entry_price": r.entry_price, "cost": r.premium_rs,
                   "beat_pct": r.ar0_pct, "beat_cat": beat_cat(r.ar0_pct), "raw_move_pct": r.raw0_pct,
                   "live_exit_date": r.exit_date, "live_reason": r.exit_reason, "live_net_pct_backtest": r.net_pct,
                   **peak_stats(cl, r.entry_price)}
            for rule in rules():
                i, px, why = simulate(cl, r.entry_price, rule)
                _, _, net = v4.net_of(r.entry_price, px, int(r.qty), slip)
                row[f"{rule}|net_pct"] = round(net / r.premium_rs * 100, 2)
                row[f"{rule}|day"] = i + 1
                row[f"{rule}|why"] = why
            s = stock.get(r.symbol)
            if s is not None:
                e = s.get(r.entry_date)
                d0i = s.index.get_loc(r.signal_date) if r.signal_date in s.index else None
                pk = days[row["peak_day"] - 1]
                row.update({
                    "stock_pre5_pct": round((s.iloc[d0i - 1] / s.iloc[d0i - 6] - 1) * 100, 2) if d0i and d0i >= 6 else None,
                    "stock_day0_pct": round((s.iloc[d0i] / s.iloc[d0i - 1] - 1) * 100, 2) if d0i else None,
                    "stock_entry_to_peak_pct": round((s.get(pk, float("nan")) / e - 1) * 100, 2) if e else None,
                    "stock_entry_to_exit_pct": round((s.get(r.exit_date, float("nan")) / e - 1) * 100, 2) if e else None,
                    "stock_entry_to_t1_pct": round((s.get(days[-1], float("nan")) / e - 1) * 100, 2) if e else None,
                    "stock_max_pct": round((max(s.get(d, float("nan")) for d in days) / e - 1) * 100, 2) if e else None,
                })
            row.update(result_quality(fin, r.symbol, r.signal_date))
            rows.append(row)
    df = pd.DataFrame(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "S1_armA_peak_study_rows.csv", index=False)
    (out_dir / "S1_armA_peak_study_paths.json").write_text(json.dumps(paths), encoding="utf-8")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 arm A peak / exit / result-quality study (hindsight)")
    ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    df = build()
    ok = (df["live|net_pct"] - df["live_net_pct_backtest"]).abs().max()
    print(f"{len(df)} trades; live rule re-simulated vs backtest: max |diff| = {ok:.3f} % points")
    for sample, g in df.groupby("sample"):
        print(sample, len(g), "mean live", round(g["live|net_pct"].mean(), 1),
              {r: round(g[f"{r}|net_pct"].mean(), 1) for r in rules()})


if __name__ == "__main__":
    main()
