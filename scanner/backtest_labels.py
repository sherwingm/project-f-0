"""Label backtest: the scanner's labels against the market-adjusted move that followed (numbers only).

    python -m scanner.backtest_labels --horizon 3 --threshold 0.5 1 2 --out data/backtest_labels.csv

For every session with a cached F&O bhavcopy (data/cache/fo_bhavcopy_*.csv; nothing is downloaded) and every
stock in the F&O universe: the scanner label that day (scanner.classify on the bhavcopy's futures OI/PCR plus
eod2 price change and volume ratio, the same code path as the cheap-option backtest) and the stock's return
over the next `horizon` sessions minus NIFTY 50's over the same sessions (eod2 closes).

Scored by the page's scoreboard rules (templates/index.html, Scoring.score): a Bullish/Bearish label is a hit
when |move| > threshold and the move goes its way; smaller moves are not scored; only the first label on a
stock in any 3 sessions counts. Neutral stock-days are scored the same way twice, as if bullish and as if
bearish: the base rate each label is read against. The table is printed, never interpreted.
"""
from __future__ import annotations

import argparse
import logging
import math
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd

from .backtest_cheap_options import _label, _read_index
from .binomial import binomial_line, hits_needed
from .build import ROOT
from .classify import BEARISH, BULLISH, NEUTRAL, UNCLASSIFIED
from .equity import load_symbol
from .nse_fo import download_fo_bhavcopy, fo_metrics
from .universe import fetch_fo_lots

log = logging.getLogger("backtest_labels")
HORIZON = 3
GAP = 3
# (label, scored as, row name)
GROUPS = ((BULLISH, "bullish", "Bullish setup"),
          (NEUTRAL, "bullish", "Neutral scored as if bullish (base rate)"),
          (BEARISH, "bearish", "Bearish setup"),
          (NEUTRAL, "bearish", "Neutral scored as if bearish (base rate)"))


def run(days: list[date], cal: list[date], bhav: Callable[[date], pd.DataFrame | None],
        equity: Callable[[str], pd.DataFrame | None], symbols: list[str], index: pd.Series,
        horizon: int = HORIZON) -> pd.DataFrame:
    """One row per stock-day: date, symbol, label, move (market-adjusted %, None when the horizon is past the data)."""
    pos = {d: i for i, d in enumerate(cal)}
    idx = {d.date() if hasattr(d, "date") else d: float(v) for d, v in index.items()}
    frames: dict[str, pd.DataFrame | None] = {}
    closes: dict[str, dict[date, float]] = {}
    rows = []
    for n, d in enumerate(days, 1):
        b = bhav(d)
        fo = {} if b is None else {r["symbol"]: r for r in fo_metrics(b).to_dict("records")}
        j = pos[d] + horizon
        to = cal[j] if j < len(cal) else None
        for sym in symbols:
            if sym not in frames:
                frames[sym] = equity(sym)
                f = frames[sym]
                closes[sym] = {} if f is None else {t.date(): float(c) for t, c in f["Close"].items()}
            label = _label(sym, d, frames[sym], fo.get(sym))
            c0, c1 = closes[sym].get(d), closes[sym].get(to) if to else None
            move = None
            if c0 and c1 and idx.get(d) and idx.get(to):
                move = round(((c1 / c0) - (idx[to] / idx[d])) * 100, 3)
            rows.append({"date": d.isoformat(), "symbol": sym, "label": label, "to": to.isoformat() if to else None,
                         "move": move})
        if n % 25 == 0:
            log.info("%s: %d of %d sessions", d, n, len(days))
    return pd.DataFrame(rows, columns=["date", "symbol", "label", "to", "move"])


def score(items: pd.DataFrame, direction: str, threshold: float, cal_pos: dict[str, int], gap: int = GAP) -> dict:
    """Scoring.score from the page, for one stream of calls that all point `direction`."""
    last: dict[str, int] = {}
    c = {"hit": 0, "miss": 0, "dup": 0, "small": 0, "pending": 0}
    for r in items.sort_values(["date", "symbol"]).itertuples(index=False):
        p = cal_pos[r.date]
        if r.symbol in last and p - last[r.symbol] < gap:
            c["dup"] += 1
            continue
        last[r.symbol] = p
        if r.move is None or (isinstance(r.move, float) and math.isnan(r.move)):
            c["pending"] += 1
        elif abs(r.move) <= threshold:
            c["small"] += 1
        else:
            c["hit" if (r.move > 0) == (direction == "bullish") else "miss"] += 1
    n = c["hit"] + c["miss"]
    return {"n": n, "hits": c["hit"], "hit_pct": round(c["hit"] / n * 100, 2) if n else None,
            "needed": hits_needed(n), "clears": c["hit"] >= hits_needed(n) if n else None,
            "dup": c["dup"], "small": c["small"], "pending": c["pending"], "binomial": binomial_line(c["hit"], n)}


def summarise(df: pd.DataFrame, cal: list[date], threshold: float, gap: int = GAP) -> list[dict]:
    cal_pos = {d.isoformat(): i for i, d in enumerate(cal)}
    out = []
    for label, direction, name in GROUPS:
        sub = df[df["label"] == label]
        out.append({"group": name, "stock_days": len(sub), **score(sub, direction, threshold, cal_pos, gap)})
    return out


def print_table(summary: list[dict], threshold: float, horizon: int) -> None:
    print()
    print(f"move = {horizon}-session return minus NIFTY 50's; hit = |move| > {threshold:g}% in the label's direction")
    print(f"{'group':<44}{'stock-days':>11}{'scored':>8}{'hits':>7}{'hit %':>8}{'dup':>8}{'small':>8}{'pending':>9}")
    for r in summary:
        pct = f"{r['hit_pct']:>8.2f}" if r["hit_pct"] is not None else f"{'-':>8}"
        print(f"{r['group']:<44}{r['stock_days']:>11}{r['n']:>8}{r['hits']:>7}{pct}{r['dup']:>8}{r['small']:>8}{r['pending']:>9}")
        print(f"    {r['binomial']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Backtest the scanner's labels on the cached F&O bhavcopies (numbers only)")
    ap.add_argument("--horizon", type=int, default=HORIZON, help="sessions until the move is measured")
    ap.add_argument("--threshold", type=float, nargs="+", default=[1.0], help="move %% a label must beat (page: 0.5 1 2)")
    ap.add_argument("--gap", type=int, default=GAP, help="sessions before a stock's next label is scored again")
    ap.add_argument("--since", type=date.fromisoformat, default=None)
    ap.add_argument("--until", type=date.fromisoformat, default=None)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "backtest_labels.csv")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    index = _read_index(a.eod2_dir)["Close"]
    cal = [t.date() for t in index.index]
    cached = sorted(date.fromisoformat(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}")
                    for p in a.cache_dir.glob("fo_bhavcopy_*.csv"))
    cached = [d for d in cached if (a.since is None or d >= a.since) and (a.until is None or d <= a.until)]
    in_cal = set(cal)
    days = [d for d in cached if d in in_cal]
    skipped = [d for d in cached if d not in in_cal]          # after eod2's last date (or not an eod2 session)
    symbols = sorted(fetch_fo_lots(cache_path=a.cache_dir / "fo_universe.txt"))

    def equity(sym: str) -> pd.DataFrame | None:
        try:
            return load_symbol(sym, a.eod2_dir)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: no eod2 data (%s)", sym, exc)
            return None

    df = run(days, cal, lambda d: download_fo_bhavcopy(d, cache_dir=a.cache_dir), equity, symbols, index, a.horizon)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    counts = df["label"].value_counts().to_dict()
    print(f"Labels on {len(days)} cached bhavcopy sessions, {days[0] if days else '-'} to {days[-1] if days else '-'}, "
          f"{len(symbols)} stocks, {len(df)} stock-days -> {a.out}")
    print("label counts: " + ", ".join(f"{k} {counts.get(k, 0)}" for k in (BULLISH, BEARISH, NEUTRAL, UNCLASSIFIED)))
    if skipped:
        print(f"skipped {len(skipped)} cached session(s) with no eod2 close: {', '.join(map(str, skipped[:8]))}")
    for th in a.threshold:
        print_table(summarise(df, cal, th, a.gap), th, a.horizon)


if __name__ == "__main__":
    main()
