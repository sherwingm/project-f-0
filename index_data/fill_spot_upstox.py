"""Repair the index spot / VIX 1-minute store from Upstox's public candle API (no login).

    INDEX_STORE=... python -m index_data.fill_spot_upstox [--write]      (the whole store; nightly: `nightly(day)`,
                                                                          run by index_data.daily_extras)

The store came from Kotak (`index_data.backfill_spot`). Checked against NSE's official daily OHLC
(`index_close_daily.parquet`) and Upstox on 2026-10-30:
- **the 09:15 bar is wrong in Kotak's data**: its open is off by up to ~16 NIFTY points before 2025-09 and its
  high / low miss part of the first minute (Upstox's open, high and low equal NSE's official ones);
- every later minute agrees (closes: median difference 0.00-0.02 %, 99th percentile <= 0.15 %; highs / lows to
  0.01 %; the same minute labels: a 1-minute shift never fits better);
- the weekend Budget sessions (Sat 2025-02-01, Sun 2026-02-01) are missing;
- short special sessions (Muhurat, DR drills) are stored as full 09:15-15:30 days of flat filler at the previous
  close (2024-05-18, 2025-10-21, ...).

The repair, per series, from 2022-01 (Upstox has no minutes before):
- a session with at least REGULAR_MIN Upstox minutes is regular: its 09:15 bar is replaced by Upstox's, and Upstox
  minutes missing in the store (09:15-15:29) are added;
- a stored day where Upstox has fewer minutes and at least SHORT_FLAT_SHARE of the stored bars are flat filler is a
  special short session: its rows are dropped (S3 uses regular sessions only); with less filler it is kept as is;
- a regular Upstox session that the store lacks is added whole;
- a stored day Upstox does not have is kept as it is and listed, unless at least FLAT_SHARE of its bars are flat
  filler (open = high = low = close): then it is dropped too (2022-10-24 Muhurat, a one-bar Saturday 2025-08-23).
Before anything is written, Upstox is compared with the stored rows on CHECK_DAYS (closes 09:16-15:29: median
difference <= 0.02 %, 99th percentile <= 0.2 %, at least 97 % of the stored minutes present); the repair stops if
they disagree. Changed rows get `source="upstox"`. Without --write it only reports.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

import pandas as pd

from .common import STORE

log = logging.getLogger("index_data.fill_spot_upstox")
KEYS = {"NIFTY50": "NSE_INDEX|Nifty 50", "NIFTYBANK": "NSE_INDEX|Nifty Bank", "SENSEX": "BSE_INDEX|SENSEX",
        "INDIAVIX": "NSE_INDEX|India VIX"}
URL = "https://api.upstox.com/v2/historical-candle/{key}/1minute/{b}/{a}"
FIRST_MONTH = "2022-01"
CHECK_DAYS = [date(2025, 1, 31), date(2025, 2, 3), date(2026, 1, 30), date(2026, 2, 2)]
MEDIAN_TOL, P99_TOL, MIN_MATCH = 0.0002, 0.002, 0.97
REGULAR_MIN = 300            # a regular session has 375 one-minute bars
FLAT_SHARE = 0.9
SHORT_FLAT_SHARE = 0.5
COLS = ["timestamp", "open", "high", "low", "close", "volume", "oi", "source"]


def fetch(name: str, a: date, b: date | None = None, tries: int = 4) -> pd.DataFrame:
    """Upstox 1-minute candles a..b (one calendar month at most), 09:15 onwards."""
    url = URL.format(key=urllib.parse.quote(KEYS[name], safe=""), a=a.isoformat(), b=(b or a).isoformat())
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "project-f-0"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                js = json.load(r)
            break
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))
    f = pd.DataFrame(js.get("data", {}).get("candles", []), columns=COLS[:-1])
    if f.empty:
        return pd.DataFrame(columns=COLS)
    f["timestamp"] = pd.to_datetime(f["timestamp"]).dt.tz_convert("Asia/Kolkata").astype("datetime64[ns, Asia/Kolkata]")
    hm = f["timestamp"].dt.strftime("%H:%M")
    f = f[(hm >= "09:15") & (hm <= "15:29")].sort_values("timestamp").reset_index(drop=True)
    f["volume"] = f["volume"].fillna(0).astype("int64")
    f["oi"] = float("nan")
    f["source"] = "upstox"
    return f[COLS]


def stored(name: str, d: date, store=STORE) -> pd.DataFrame:
    p = store / "spot_1m" / name / f"{d:%Y-%m}.parquet"
    if not p.exists():
        return pd.DataFrame(columns=COLS)
    f = pd.read_parquet(p)
    return f[f["timestamp"].dt.date == d].reset_index(drop=True)


def compare(store=STORE, days=None) -> list[dict]:
    out = []
    for name in KEYS:
        for d in (days or CHECK_DAYS):
            u, k = fetch(name, d), stored(name, d, store)
            time.sleep(0.3)
            hm = k["timestamp"].dt.strftime("%H:%M") if len(k) else pd.Series(dtype=str)
            k = k[(hm > "09:15") & (hm <= "15:29")] if len(k) else k
            m = u.merge(k, on="timestamp", suffixes=("_u", "_k")) if len(u) and len(k) else pd.DataFrame()
            rel = ((m["close_u"] - m["close_k"]).abs() / m["close_k"]) if len(m) else pd.Series(dtype=float)
            out.append({"series": name, "day": str(d), "upstox_rows": len(u), "stored_rows": len(k), "matched": len(m),
                        "median_rel_diff_pct": round(float(rel.median()) * 100, 4) if len(rel) else None,
                        "p99_rel_diff_pct": round(float(rel.quantile(0.99)) * 100, 4) if len(rel) else None,
                        "ok": bool(len(rel) and rel.median() <= MEDIAN_TOL and rel.quantile(0.99) <= P99_TOL
                                   and len(m) >= MIN_MATCH * len(k))})
    return out


def repair_month(old: pd.DataFrame, up: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """The repaired month and what changed. `old`: the stored month; `up`: Upstox's month (09:15-15:29)."""
    old = old.copy()
    old["d"] = old["timestamp"].dt.date
    info = {"bar_0915_replaced": 0, "bar_0915_changed": 0, "minutes_added": 0, "days_added": [], "days_dropped": [],
            "days_kept_no_upstox": []}
    if up.empty:
        info["days_kept_no_upstox"] = sorted(str(d) for d in set(old["d"]))
        return old[COLS].sort_values("timestamp").reset_index(drop=True), info
    up = up.copy()
    up["d"] = up["timestamp"].dt.date
    n_up = up.groupby("d").size()
    keep = []
    for d, g in old.groupby("d"):
        n = int(n_up.get(d, 0))
        flat = ((g["open"] == g["high"]) & (g["high"] == g["low"]) & (g["low"] == g["close"])).mean()
        if n == 0 and flat >= FLAT_SHARE:
            info["days_dropped"].append(f"{d} ({len(g)} stored rows of flat filler, no Upstox minutes)")
        elif n == 0:
            info["days_kept_no_upstox"].append(str(d))
            keep.append(g)
        elif n < REGULAR_MIN and flat >= SHORT_FLAT_SHARE:
            info["days_dropped"].append(f"{d} ({len(g)} stored rows, {flat:.0%} flat; {n} Upstox minutes)")
        elif n < REGULAR_MIN:            # a partial Upstox day never removes real stored minutes
            info["days_kept_no_upstox"].append(f"{d} (Upstox {n} minutes)")
            keep.append(g)
        else:
            u = up[up["d"] == d]
            first = u[u["timestamp"].dt.strftime("%H:%M") == "09:15"]
            g = g.set_index("timestamp")
            if len(first):
                t0 = first["timestamp"].iloc[0]
                if t0 in g.index:
                    a = g.loc[t0, ["open", "high", "low", "close"]].to_numpy(float)
                    b = first[["open", "high", "low", "close"]].to_numpy(float)[0]
                    info["bar_0915_changed"] += int(not (abs(a - b) < 0.005).all())
                info["bar_0915_replaced"] += 1
                g = g.drop(index=t0, errors="ignore")
                g = pd.concat([g, first.drop(columns="d").set_index("timestamp")])
            add = u[~u["timestamp"].isin(g.index) & (u["timestamp"].dt.strftime("%H:%M") != "09:15")]
            info["minutes_added"] += len(add)
            g = pd.concat([g, add.drop(columns="d").set_index("timestamp")])
            keep.append(g.reset_index())
    for d in sorted(set(n_up.index) - set(old["d"])):
        if n_up[d] >= REGULAR_MIN:
            info["days_added"].append(str(d))
            keep.append(up[up["d"] == d])
    out = pd.concat(keep, ignore_index=True) if keep else pd.DataFrame(columns=COLS)
    out = out[COLS].sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    return out, info


def official_check(store=STORE) -> dict:
    """Share of sessions 2022-01 → 2025-09 whose stored day open equals NSE's official open (within 0.05 point) and
    whose high / low are within 0.02 % of NSE's (NIFTY 50, Nifty Bank, India VIX)."""
    ic = pd.read_parquet(store / "index_close_daily.parquet")
    ic["date"] = pd.to_datetime(ic["date"]).dt.date
    out = {}
    for name in ("NIFTY50", "NIFTYBANK", "INDIAVIX"):
        f = pd.concat([pd.read_parquet(p) for p in sorted((store / "spot_1m" / name).glob("*.parquet"))
                       if FIRST_MONTH <= p.stem <= "2025-09"], ignore_index=True)
        f["d"] = f["timestamp"].dt.date
        f = f[f.groupby("d")["close"].transform("size") >= 60]
        day = f.groupby("d").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"))
        o = ic[ic["index"] == name].set_index("date")[["open", "high", "low"]]
        m = day.join(o, rsuffix="_nse", how="inner")
        out[name] = {"sessions": len(m), "open_equal_pct": round(float(((m["open"] - m["open_nse"]).abs() <= 0.05).mean()) * 100, 1),
                     "high_ok_pct": round(float(((m["high"] - m["high_nse"]).abs() / m["high_nse"] <= 0.0002).mean()) * 100, 1),
                     "low_ok_pct": round(float(((m["low"] - m["low_nse"]).abs() / m["low_nse"] <= 0.0002).mean()) * 100, 1)}
    return out


def repair(months: list[str] | None = None, write: bool = False, store=STORE) -> dict:
    """Repair each series' month files (all from FIRST_MONTH when `months` is None). Returns the counts."""
    report = {}
    for name in KEYS:
        tot = {"bar_0915_replaced": 0, "bar_0915_changed": 0, "minutes_added": 0, "days_added": [], "days_dropped": [],
               "days_kept_no_upstox": []}
        for p in sorted((store / "spot_1m" / name).glob("*.parquet")):
            if p.stem < FIRST_MONTH or (months is not None and p.stem not in months):
                continue
            m = pd.Period(p.stem, "M")
            up = fetch(name, m.start_time.date(), min(m.end_time.date(), date.today()))
            time.sleep(0.3)
            new, info = repair_month(pd.read_parquet(p), up)
            for k, v in info.items():
                tot[k] += v
            if write:
                new.to_parquet(p, index=False)
        report[name] = tot
    return report


def nightly(day: date, store=STORE) -> dict:
    """The recorder's step (index_data.daily_extras). Upstox's history has no rows for the current session, so the
    months of `day` and of 10 days earlier are repaired (the last sessions of a month are fixed the next night), after
    the 5 days before `day` agree with the stored rows."""
    cmp_ = compare(store, [day - timedelta(days=i) for i in range(1, 6)])
    if any(r["upstox_rows"] and r["stored_rows"] and not r["ok"] for r in cmp_):
        return {"skipped": "Upstox and the stored rows disagree", "check": cmp_}
    rep = repair(sorted({f"{day:%Y-%m}", f"{day - timedelta(days=10):%Y-%m}"}), write=True, store=store)
    return {k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()} for k, v in rep.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("official check before:", official_check())
    cmp_ = compare()
    for r in cmp_:
        print(r)
    if any(not r["ok"] for r in cmp_):
        raise SystemExit("Upstox and the stored rows disagree: nothing written")
    report = repair(None, a.write)
    for name, tot in report.items():
        print(name, {k: (v if not isinstance(v, list) else (len(v), v[:12])) for k, v in tot.items()})
    if a.write:
        print("official check after:", official_check())
    return report


if __name__ == "__main__":
    main()
