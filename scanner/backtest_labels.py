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

from .backtest_cheap_options import _read_index
from .binomial import binomial_line, hits_needed
from .build import ROOT
from .classify import BEARISH, BULLISH, NEUTRAL, UNCLASSIFIED, classify
from .stats import clustered_diff_t, clustered_t
from .equity import equity_metrics_one, load_symbol
from .nse_fo import download_fo_bhavcopy, fo_metrics
from .universe import fetch_fo_lots

log = logging.getLogger("backtest_labels")
HORIZON = 3
GAP = 3
RETURN_HORIZONS = (1, 3, 5)          # market-adjusted returns reported per label (adj_1, adj_3, adj_5)
# (label, scored as, row name)
GROUPS = ((BULLISH, "bullish", "Bullish setup"),
          (NEUTRAL, "bullish", "Neutral scored as if bullish (base rate)"),
          (BEARISH, "bearish", "Bearish setup"),
          (NEUTRAL, "bearish", "Neutral scored as if bearish (base rate)"))


def run(days: list[date], cal: list[date], bhav: Callable[[date], pd.DataFrame | None],
        equity: Callable[[str], pd.DataFrame | None], symbols: list[str] | dict[str, set[str]], index: pd.Series,
        horizon: int = HORIZON, extra_horizons: tuple[int, ...] = RETURN_HORIZONS) -> pd.DataFrame:
    """One row per stock-day: date, symbol, label, the four inputs the label was computed from, and the stock's
    and NIFTY's returns over the horizon with move = their difference (%, None when the horizon is past the data),
    plus adj_<h> = the same difference over each of `extra_horizons` sessions.
    symbols: one list for every day, or a point-in-time map {YYYY-MM-DD: symbols in F&O that day}; with the map, a
    stock with no eod2 history is skipped rather than counted as Unclassified."""
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
        ends = {h: (cal[pos[d] + h] if pos[d] + h < len(cal) else None) for h in extra_horizons}
        pit = isinstance(symbols, dict)
        for sym in (sorted(symbols.get(d.isoformat(), ())) if pit else symbols):
            if sym not in frames:
                frames[sym] = equity(sym)
                f = frames[sym]
                closes[sym] = {} if f is None else {t.date(): float(c) for t, c in f["Close"].items()}
            if pit and frames[sym] is None:
                continue
            inputs = label_inputs(sym, d, frames[sym], fo.get(sym))
            c0, c1 = closes[sym].get(d), closes[sym].get(to) if to else None
            ret = nifty = move = None
            if c0 and c1 and idx.get(d) and idx.get(to):
                ret, nifty = round((c1 / c0 - 1) * 100, 3), round((idx[to] / idx[d] - 1) * 100, 3)
                move = round(((c1 / c0) - (idx[to] / idx[d])) * 100, 3)
            adj = {}
            for h, e in ends.items():
                ce = closes[sym].get(e) if e else None
                adj[f"adj_{h}"] = round(((ce / c0) - (idx[e] / idx[d])) * 100, 3) \
                    if c0 and ce and idx.get(d) and idx.get(e) else None
            rows.append({"date": d.isoformat(), "symbol": sym, **inputs, "to": to.isoformat() if to else None,
                         "fwd_return": ret, "nifty_fwd_return": nifty, "move": move, **adj})
        if n % 25 == 0:
            log.info("%s: %d of %d sessions", d, n, len(days))
    return pd.DataFrame(rows, columns=["date", "symbol", "label", "price_change_pct", "volume_ratio", "oi_change_pct",
                                       "pcr", "to", "fwd_return", "nifty_fwd_return", "move",
                                       *(f"adj_{h}" for h in extra_horizons)])


def label_inputs(sym: str, d: date, frame: pd.DataFrame | None, fo: dict | None) -> dict:
    """The label and the four numbers it came from (same path as backtest_cheap_options._label)."""
    out = {"label": UNCLASSIFIED, "price_change_pct": None, "volume_ratio": None, "oi_change_pct": None, "pcr": None}
    m = equity_metrics_one(sym, frame, as_of=pd.Timestamp(d)) if frame is not None else None
    if not m or m["date"] != d.isoformat():
        return out
    clean = lambda v: None if v is None or pd.isna(v) else float(v)
    fo = fo or {}
    row = {**m, "oi_change_pct": clean(fo.get("oi_change_pct")), "pcr": clean(fo.get("pcr"))}
    return {"label": classify(row)["label"], "price_change_pct": m["price_change_pct"], "volume_ratio": m["volume_ratio"],
            "oi_change_pct": None if row["oi_change_pct"] is None else round(row["oi_change_pct"], 3),
            "pcr": None if row["pcr"] is None else round(row["pcr"], 4)}


def statuses(items: pd.DataFrame, direction: str, threshold: float, cal_pos: dict[str, int], gap: int = GAP):
    """(row index, status) for one stream of calls pointing `direction`, by the page's Scoring.score rules:
    dup (within `gap` sessions of the stock's previous scored call), pending (no move yet), small
    (|move| <= threshold), hit or miss."""
    last: dict[str, int] = {}
    for i, r in items.sort_values(["date", "symbol"]).iterrows():
        p = cal_pos[r["date"]]
        if r["symbol"] in last and p - last[r["symbol"]] < gap:
            yield i, "dup"
            continue
        last[r["symbol"]] = p
        mv = r["move"]
        if mv is None or (isinstance(mv, float) and math.isnan(mv)):
            yield i, "pending"
        elif abs(mv) <= threshold:
            yield i, "small"
        else:
            yield i, "hit" if (mv > 0) == (direction == "bullish") else "miss"


def score(items: pd.DataFrame, direction: str, threshold: float, cal_pos: dict[str, int], gap: int = GAP) -> dict:
    """Scoring.score from the page, for one stream of calls that all point `direction`."""
    c = {"hit": 0, "miss": 0, "dup": 0, "small": 0, "pending": 0}
    for _, st in statuses(items, direction, threshold, cal_pos, gap):
        c[st] += 1
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


def annotate(df: pd.DataFrame, cal: list[date], threshold: float, gap: int = GAP) -> pd.DataFrame:
    """Per stock-day: scored Y/N, scored_reason (dup / small / pending / neutral / unclassified) and hit Y/N
    (blank unless scored). Bullish and Bearish labels are scored as calls; Neutral and Unclassified are not."""
    cal_pos = {d.isoformat(): i for i, d in enumerate(cal)}
    out = df.copy()
    out["scored"], out["scored_reason"], out["hit"] = "N", "", ""
    out.loc[out["label"] == NEUTRAL, "scored_reason"] = "neutral"
    out.loc[out["label"] == UNCLASSIFIED, "scored_reason"] = "unclassified"
    for label, direction in ((BULLISH, "bullish"), (BEARISH, "bearish")):
        for i, st in statuses(out[out["label"] == label], direction, threshold, cal_pos, gap):
            if st in ("hit", "miss"):
                out.at[i, "scored"], out.at[i, "hit"] = "Y", "Y" if st == "hit" else "N"
            else:
                out.at[i, "scored_reason"] = st
    return out


def versus_base(df: pd.DataFrame, cal: list[date], thresholds, gap: int = GAP) -> list[dict]:
    """Per label x threshold: the label's hit rate against Neutral scored the same way (the base rate),
    the difference in points, a two-proportion z, and the hits needed to beat a coin at that N."""
    cal_pos = {d.isoformat(): i for i, d in enumerate(cal)}
    out = []
    for th in thresholds:
        for label, direction in ((BULLISH, "bullish"), (BEARISH, "bearish")):
            sub = df[df["label"] == label]
            s = score(sub, direction, th, cal_pos, gap)
            b = score(df[df["label"] == NEUTRAL], direction, th, cal_pos, gap)
            hs, hb = _hits(sub, direction, th, cal_pos, gap), _hits(df[df["label"] == NEUTRAL], direction, th, cal_pos, gap)
            out.append({"label": label, "threshold_pct": th, "stock_days": len(sub), "scored_n": s["n"],
                        "hits": s["hits"], "hit_pct": s["hit_pct"], "base_n": b["n"], "base_hits": b["hits"],
                        "base_hit_pct": b["hit_pct"],
                        "diff_pts": round(s["hit_pct"] - b["hit_pct"], 2) if s["n"] and b["n"] else None,
                        "z_vs_base": two_prop_z(s["hits"], s["n"], b["hits"], b["n"]),
                        "z_vs_base_clustered": clustered_diff_t(hs[1], hs[0], hb[1], hb[0]), "needs_vs_coin": s["needed"]})
    return out


def non_overlapping(items: pd.DataFrame, cal_pos: dict[str, int], gap: int) -> pd.DataFrame:
    """At most one row per stock in any `gap` sessions (the first), so a stock's h-session windows do not overlap."""
    keep, last = [], {}
    for i, r in items.sort_values(["date", "symbol"]).iterrows():
        p = cal_pos[r["date"]]
        if r["symbol"] in last and p - last[r["symbol"]] < gap:
            continue
        last[r["symbol"]] = p
        keep.append(i)
    return items.loc[keep]


def _stats(v: pd.Series) -> dict:
    v = v.dropna().astype(float)
    n = len(v)
    sd = float(v.std(ddof=1)) if n > 1 else None
    return {"n": n, "mean": round(float(v.mean()), 4) if n else None, "median": round(float(v.median()), 4) if n else None,
            "t": round(float(v.mean()) / (sd / math.sqrt(n)), 3) if n > 1 and sd else None, "sd": sd}


def returns_vs_base(df: pd.DataFrame, cal: list[date], horizons=RETURN_HORIZONS) -> list[dict]:
    """Per label x horizon: mean / median market-adjusted return with its t, the same for Neutral, and Welch's t of
    the difference. Rows are non-overlapping per stock (one per `h` sessions); columns adj_<h> from run()."""
    cal_pos = {d.isoformat(): i for i, d in enumerate(cal)}
    out = []
    for h in horizons:
        col = f"adj_{h}"
        bdf = non_overlapping(df[(df["label"] == NEUTRAL) & df[col].notna()], cal_pos, h)
        base = _stats(bdf[col])
        for label in (BULLISH, BEARISH):
            sdf = non_overlapping(df[(df["label"] == label) & df[col].notna()], cal_pos, h)
            s = _stats(sdf[col])
            welch = None
            if s["n"] > 1 and base["n"] > 1 and s["sd"] and base["sd"]:
                welch = round((s["mean"] - base["mean"]) / math.sqrt(s["sd"] ** 2 / s["n"] + base["sd"] ** 2 / base["n"]), 3)
            out.append({"label": label, "horizon_sessions": h, "stock_days": int((df["label"] == label).sum()),
                        "n_returns": s["n"], "mean_adj_return": s["mean"], "median_adj_return": s["median"],
                        "t_mean": s["t"], "base_n_returns": base["n"], "base_mean_adj_return": base["mean"],
                        "base_median_adj_return": base["median"], "base_t_mean": base["t"],
                        "diff_mean": round(s["mean"] - base["mean"], 4) if s["n"] and base["n"] else None,
                        "welch_t_vs_base": welch,
                        "t_mean_clustered": clustered_t(sdf[col], sdf["date"]),
                        "base_t_mean_clustered": clustered_t(bdf[col], bdf["date"]),
                        "diff_t_clustered": clustered_diff_t(sdf[col], sdf["date"], bdf[col], bdf["date"])})
    return out


def _hits(items: pd.DataFrame, direction: str, threshold: float, cal_pos: dict[str, int], gap: int):
    """(dates, 1/0 hit) of the scored rows, for the date-clustered difference in hit rates."""
    dates, hits = [], []
    for i, st in statuses(items, direction, threshold, cal_pos, gap):
        if st in ("hit", "miss"):
            dates.append(items.at[i, "date"])
            hits.append(1.0 if st == "hit" else 0.0)
    return dates, hits


def two_prop_z(h1: int, n1: int, h0: int, n0: int) -> float | None:
    """z for p1 - p0 with the pooled standard error; None when either side is empty or the pool is degenerate."""
    if not n1 or not n0:
        return None
    p = (h1 + h0) / (n1 + n0)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n0))
    return round((h1 / n1 - h0 / n0) / se, 3) if se else None


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
