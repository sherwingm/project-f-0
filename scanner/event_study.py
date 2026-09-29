"""Event study over the stored exchange events: market-adjusted returns around each event, T-5 to T+5.

    python -m scanner.event_study --since 2023-01-01 --out data/event_study.csv

For every tier-1/2 event with bucket != ignore: the stock's cumulative return minus NIFTY 50's over
    pre   close T-5 -> close T-1   (the "rumour" window)
    day   close T-1 -> close T     (the event session)
    post  close T+1 -> close T+5   (after the reaction: excludes T+1, the day the results beat/miss
                                    proxy is measured on, so the proxy cannot leak into the post mean)
computed on eod2 closes aligned to the index's calendar. Printed per type, per subtype and per
bucket (always for the sized types in BUCKETED): count, and for every window the mean, median, share
positive, t-statistic of the mean, and the date-clustered t (events on the same day are not independent). For `results`, beat/miss subtype rows use the day+1 reaction as a proxy
(a real beat/miss needs the numbers; the reaction is what the market judged) — stated as a proxy.
The table is printed, never interpreted. data/event_patterns.json carries {type: {pre, day, post,
count}} for the UI's verdict card.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import date
from pathlib import Path

import pandas as pd

from .build import ROOT
from .stats import clustered_t
from .equity import INDEX_FILE, load_symbol

log = logging.getLogger("event_study")
PRE, POST = 5, 5
BUCKETED = ("order_win", "capacity", "block_deal", "bulk_deal", "insider")   # materiality-sized types
REACTION_PCT = 2.0                   # |day + day+1 CAR| beyond this = beat/miss proxy for results


def study(events: list[dict], closes: dict[str, pd.Series], index: pd.Series) -> pd.DataFrame:
    """One row per event with car_pre / car_day / car_post (%, market-adjusted); events whose windows
    the data cannot cover are kept with nulls so the counts are honest."""
    cal = [d.strftime("%Y-%m-%d") for d in index.index]
    pos = {d: i for i, d in enumerate(cal)}
    ix = index.to_numpy(dtype=float)
    aligned: dict[str, pd.Series] = {}
    rows = []
    for e in events:
        sym, d0 = e["symbol"], e["event_date"]
        s = aligned.get(sym)
        if s is None:
            raw = closes.get(sym)
            s = aligned.setdefault(sym, raw.reindex(index.index).ffill() if raw is not None else pd.Series(dtype=float))
        i = pos.get(d0)
        if i is None:                                 # holiday-dated filing: next session
            later = [j for j, day in enumerate(cal) if day > d0]
            i = later[0] if later else None
        row = {"type": e["type"], "subtype": e.get("subtype"), "bucket": e.get("bucket"), "symbol": sym,
               "event_date": d0, "direction": e.get("direction"), "car_pre": None, "car_day": None,
               "car_post": None, "reaction": None}
        if i is not None and s.size:
            v = s.to_numpy(dtype=float)
            row["car_pre"] = _car(v, ix, i - PRE, i - 1)
            row["car_day"] = _car(v, ix, i - 1, i)
            row["car_post"] = _car(v, ix, i + 1, i + POST)
            row["reaction"] = _car(v, ix, i - 1, min(i + 1, len(cal) - 1))
        rows.append(row)
    return pd.DataFrame(rows)


def _car(stock, index, a: int, b: int):
    """Cumulative abnormal return % from session a to b (close-to-close), None when out of range."""
    if a < 0 or b >= len(stock) or a >= b:
        return None
    sa, sb, ia, ib = stock[a], stock[b], index[a], index[b]
    if not (sa and sb and ia and ib) or math.isnan(sa) or math.isnan(sb):
        return None
    return round(((sb / sa) - (ib / ia)) * 100, 3)


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    groups: list[tuple[str, pd.DataFrame]] = []
    for typ, g in df.groupby("type"):
        groups.append((typ, g))
        for sub, gg in g.groupby("subtype", dropna=True):
            if len(gg) and sub:
                groups.append((f"{typ} / {sub}", gg))
        if typ in BUCKETED or g["bucket"].nunique() > 1:   # bucket rows where the type is sized
            for bkt, gg in g.groupby("bucket", dropna=True):
                groups.append((f"{typ} [{bkt}]", gg))
    if "results" in set(df["type"]):
        res = df[df["type"] == "results"].dropna(subset=["reaction"])
        groups.append(("results / beat (day+1 reaction > +2%, a proxy)", res[res["reaction"] > REACTION_PCT]))
        groups.append(("results / miss (day+1 reaction < -2%, a proxy)", res[res["reaction"] < -REACTION_PCT]))
    out = []
    for name, g in groups:
        row = {"group": name, "count": len(g)}
        for w in ("pre", "day", "post"):
            v = g[f"car_{w}"].dropna()
            row[f"{w}_tc"] = clustered_t(v, g.loc[v.index, "event_date"]) if len(v) > 1 else None
            n = len(v)
            mean = float(v.mean()) if n else None
            sd = float(v.std(ddof=1)) if n > 1 else None
            row[f"{w}_n"] = n
            row[f"{w}_mean"] = round(mean, 3) if n else None
            row[f"{w}_median"] = round(float(v.median()), 3) if n else None
            row[f"{w}_pos_pct"] = round(float((v > 0).mean() * 100), 1) if n else None
            row[f"{w}_t"] = round(mean / (sd / math.sqrt(n)), 2) if n > 1 and sd else None
        out.append(row)
    return pd.DataFrame(out)


def patterns(summary: pd.DataFrame) -> dict:
    """data/event_patterns.json: the per-type numbers the verdict card cites."""
    out = {}
    for r in summary.to_dict("records"):
        if "/" in r["group"] or "[" in r["group"]:
            continue
        out[r["group"]] = {"count": int(r["count"]), "pre": r["pre_mean"], "day": r["day_mean"],
                           "post": r["post_mean"], "pre_pos_pct": r["pre_pos_pct"], "post_pos_pct": r["post_pos_pct"]}
    return out


def print_table(summary: pd.DataFrame) -> None:
    """t = ordinary t of the mean; tc = the same with standard errors clustered by event date."""
    print(f"{'group':<46}{'count':>7} | {'pre mean':>9}{'med':>7}{'pos%':>6}{'t':>7}{'tc':>7} | "
          f"{'day mean':>9}{'med':>7}{'pos%':>6}{'t':>7}{'tc':>7} | {'post mean':>10}{'med':>7}{'pos%':>6}{'t':>7}{'tc':>7}")
    f = lambda v, w, p=3: f"{v:>{w}.{p}f}" if v is not None and not (isinstance(v, float) and math.isnan(v)) else f"{'-':>{w}}"
    for r in summary.to_dict("records"):
        cells = [f"{r['group'][:45]:<46}{r['count']:>7}"]
        for w, width in (("pre", 9), ("day", 9), ("post", 10)):
            cells.append(f"{f(r[f'{w}_mean'], width)}{f(r[f'{w}_median'], 7)}{f(r[f'{w}_pos_pct'], 6, 1)}"
                         f"{f(r[f'{w}_t'], 7, 2)}{f(r.get(f'{w}_tc'), 7, 2)}")
        print(" | ".join(cells))


def load_index(eod2_dir: Path) -> pd.Series:
    path = eod2_dir / f"{INDEX_FILE}.csv"
    df = pd.read_csv(path, usecols=["Date", "Close"], parse_dates=["Date"])
    df = df[df["Close"] > 0].set_index("Date").sort_index()
    return df["Close"]


def main() -> None:
    ap = argparse.ArgumentParser(description="event study: market-adjusted returns around stored events")
    ap.add_argument("--since", type=date.fromisoformat, default=date(2023, 1, 1))
    ap.add_argument("--until", type=date.fromisoformat, default=None)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "event_study.csv")
    ap.add_argument("--patterns-out", type=Path, default=ROOT / "data" / "event_patterns.json")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from .events.store import Store
    with Store() as store:
        events = [e for e in store.events_between(a.since, a.until or date.today(), max_tier=2)
                  if e["bucket"] != "ignore"]
    log.info("%d tier-1/2 events since %s", len(events), a.since)
    index = load_index(a.eod2_dir)
    closes: dict[str, pd.Series] = {}
    for sym in sorted({e["symbol"] for e in events}):
        try:
            closes[sym] = load_symbol(sym, a.eod2_dir)["Close"]
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: no eod2 closes (%s)", sym, exc)
    df = study(events, closes, index)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    summary = summarise(df)
    a.patterns_out.write_text(json.dumps(patterns(summary), indent=1), encoding="utf-8")
    print(f"{len(df)} events -> {a.out}; patterns -> {a.patterns_out}")
    print("CAR = stock minus NIFTY 50, close to close. pre = close T-5 -> T-1, day = T-1 -> T, "
          "post = close T+1 -> T+5. results beat/miss uses the T-1 -> T+1 reaction as a proxy.")
    print_table(summary)


if __name__ == "__main__":
    main()
