"""Audit of the 1-minute data behind the G1 / G1-F history: NIFTY spot, India VIX, and the option minutes on G1 days.
Read-only. Prints findings and writes g1_research/results/data_audit_*.csv. INDEX_STORE=../fo-index-data/data/index"""
import json
import os
import sys
import warnings
from datetime import date, time, timedelta

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from index_data import load as L  # noqa: E402

STORE = os.environ.get("INDEX_STORE", os.path.join(REPO, "..", "fo-index-data", "data", "index"))
START, END = date(2021, 10, 20), date(2026, 10, 28)
OPEN, CLOSE = time(9, 15), time(15, 29)
pd.set_option("display.width", 250)


def spot_audit():
    s = L.spot_1m(START, END, "NIFTY50")
    s["d"] = s["timestamp"].dt.date
    s["t"] = s["timestamp"].dt.time
    print("== NIFTY spot 1-minute ==  rows", len(s), "| days", s.d.nunique(), "| from", s.d.min(), "to", s.d.max())
    rows = []
    for d, g in s.groupby("d"):
        g = g.sort_values("timestamp")
        inside = g[(g.t >= OPEN) & (g.t <= CLOSE)]
        mins = pd.date_range(pd.Timestamp.combine(d, OPEN), pd.Timestamp.combine(d, CLOSE), freq="1min", tz=g["timestamp"].dt.tz)
        missing = len(set(mins) - set(inside["timestamp"]))
        ohlc_bad = int(((g.low > g[["open", "close"]].min(axis=1) + 1e-9) | (g.high < g[["open", "close"]].max(axis=1) - 1e-9) | (g.low > g.high)).sum())
        zero = int(((g[["open", "high", "low", "close"]] <= 0) | g[["open", "high", "low", "close"]].isna()).any(axis=1).sum())
        r = g["close"].pct_change().abs()
        rows.append({"day": d, "n": len(g), "outside_hours": len(g) - len(inside), "dup": int(g.timestamp.duplicated().sum()), "missing_min": missing,
                     "ohlc_bad": ohlc_bad, "zero_nan": zero, "max_min_move_pct": r.max() * 100, "first": g.t.iloc[0], "last": g.t.iloc[-1],
                     "day_open": g.open.iloc[0], "day_close": g.close.iloc[-1], "day_high": g.high.max(), "day_low": g.low.min()})
    A = pd.DataFrame(rows)
    A.to_csv(os.path.join(ROOT, "results", "data_audit_spot_days.csv"), index=False)
    full = A[A.n >= 370]
    print(" sessions with >= 370 bars:", len(full), "| partial sessions (< 370 bars):", len(A) - len(full))
    part = A[A.n < 370]
    print(part[["day", "n", "first", "last", "missing_min"]].to_string(index=False) if len(part) else " none")
    print(" bars/session: min", A.n.min(), "median", int(A.n.median()), "max", A.n.max())
    print(" total missing minutes in full sessions:", int(full.missing_min.sum()), "| sessions with any missing:", int((full.missing_min > 0).sum()))
    print(" duplicates:", int(A.dup.sum()), "| outside-hours rows:", int(A.outside_hours.sum()), "| OHLC inconsistent rows:", int(A.ohlc_bad.sum()), "| zero/NaN rows:", int(A.zero_nan.sum()))
    big = A[A.max_min_move_pct > 0.8].sort_values("max_min_move_pct", ascending=False).head(8)
    print(" biggest 1-minute moves (> 0.8 %):\n", big[["day", "max_min_move_pct"]].round(2).to_string(index=False) if len(big) else " none")
    # weekday sessions vs the calendar
    hol = set(date.fromisoformat(x) for x in json.load(open(os.path.join(REPO, "data", "nse_holidays.json")))["holidays"])
    exp = [START + timedelta(days=i) for i in range((END - START).days + 1)]
    exp = [x for x in exp if x.weekday() < 5 and x not in hol]
    have = set(A.day)
    miss = [x for x in exp if x not in have and x.year >= 2026]
    print(" 2026 weekdays (not in the holiday list) with NO spot data:", [str(x) for x in miss] or "none")
    wk = sorted(x for x in have if x.weekday() >= 5)
    print(" weekend sessions in the data:", [str(x) for x in wk] or "none")
    # against the independent daily file (to 2025-09-30)
    dd = pd.read_parquet(os.path.join(STORE, "index_close_daily.parquet"))
    dd = dd[dd["index"] == "NIFTY50"].copy()
    dd["day"] = pd.to_datetime(dd["date"]).dt.date
    dd = dd[(dd.day >= START) & (dd.day <= date(2025, 9, 30))].set_index("day")
    j = A.set_index("day").join(dd[["open", "high", "low", "close"]], rsuffix="_daily", how="outer")
    only_daily = j[j.day_close.isna()].index.tolist()
    only_min = j[j.close.isna() & j.day_close.notna()].index.tolist()
    print(" vs the independent daily file (to 2025-09-30): days only in daily file:", [str(x) for x in only_daily][:12], "| only in minute file:", [str(x) for x in only_min][:12])
    both = j.dropna(subset=["day_close", "close"])
    both["dc"] = (both.day_close / both.close - 1) * 100
    both["dh"] = (both.day_high / both.high - 1) * 100
    both["dl"] = (both.day_low / both.low - 1) * 100
    print(f" minute-derived daily close vs daily file: median diff {both.dc.abs().median():.3f} %, days > 0.1 %: {(both.dc.abs() > 0.1).sum()} of {len(both)}, > 0.5 %: {(both.dc.abs() > 0.5).sum()}")
    print(f" minute-derived high / low vs daily file: days high off by > 0.3 %: {(both.dh.abs() > 0.3).sum()}, low off by > 0.3 %: {(both.dl.abs() > 0.3).sum()}")
    bad = both[(both.dc.abs() > 0.5) | (both.dh.abs() > 0.5) | (both.dl.abs() > 0.5)]
    print(bad[["day_close", "close", "dc", "dh", "dl"]].round(2).to_string() if len(bad) else " no day differs by more than 0.5 %")
    return A, s


def vix_audit():
    v = L.vix_1m(START, END)
    v["d"] = v["timestamp"].dt.date
    v["t"] = v["timestamp"].dt.time
    print("\n== India VIX 1-minute ==  rows", len(v), "| days", v.d.nunique())
    g = v.groupby("d")
    cnt = g.size()
    print(" bars/day: min", cnt.min(), "median", int(cnt.median()), "| days < 300 bars:", int((cnt < 300).sum()))
    print(" value range:", round(v.close.min(), 2), "to", round(v.close.max(), 2), "| zero/NaN:", int((v.close.isna() | (v.close <= 0)).sum()))
    jump = (v.groupby("d")["close"].pct_change().abs() * 100)
    print(f" minute-to-minute jumps > 5 %: {(jump > 5).sum()} (max {jump.max():.1f} %)")
    daily = pd.read_parquet(os.path.join(STORE, "vix_daily.parquet"))
    print(" vix_daily columns:", list(daily.columns)[:6])
    ccol = "close" if "close" in daily.columns else daily.columns[-1]
    dcol = "date" if "date" in daily.columns else daily.columns[0]
    dd = daily.copy()
    dd["day"] = pd.to_datetime(dd[dcol]).dt.date
    dd = dd.set_index("day")[ccol]
    last = g["close"].last()
    j = pd.concat([last.rename("m"), dd.rename("d")], axis=1).dropna()
    j = j[(j.index >= START) & (j.index <= END)]
    diff = (j.m / j.d - 1).abs() * 100
    print(f" minute last close vs daily close: median {diff.median():.2f} %, days > 2 %: {(diff > 2).sum()} of {len(j)}")
    return v


def option_audit(spot):
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    d["day"] = pd.to_datetime(d["Day"]).dt.date
    sp = spot.copy()
    spk = {k: g.set_index("t")["close"] for k, g in sp.groupby("d")}
    rows, probs = [], []
    n_days = n_both = 0
    for r in d.to_dict("records"):
        day, e, k = r["day"], pd.Timestamp(str(r["Expiry"])[:10]).date(), float(r["Strike"])
        for dd_ in (day,):
            c = L.options_day("NIFTY", e, dd_)
            n_days += 1
            if c.empty:
                probs.append((day, "no option file", ""))
                continue
            c = c.copy()
            c["t"] = c["timestamp"].dt.time
            ent = pd.Timestamp(f"{day} {r['Entry time']}").time()
            raw = c
            # sources
            if raw["source"].nunique() > 1:
                n_both += 1
            x = c[(c.strike == k) & (c.option_type == "PE")].sort_values("timestamp")
            inw = x[(x.t >= ent) & (x.t <= CLOSE)]
            ohlc_bad = int(((x.low > x[["open", "close"]].min(axis=1) + 1e-9) | (x.high < x[["open", "close"]].max(axis=1) - 1e-9)).sum())
            neg = int((x[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())
            dup = int(x.timestamp.duplicated().sum())
            has_ent = ent in set(x.t)
            gap = max(((a - b).total_seconds() / 60 for a, b in zip(inw.timestamp.iloc[1:], inw.timestamp.iloc[:-1])), default=0)
            jump = x.close.pct_change().abs().max() * 100 if len(x) > 1 else np.nan
            # price below intrinsic at each minute (puts): intrinsic = K - S
            s = spk.get(day)
            below = 0
            if s is not None and len(x):
                ss = s.reindex(x.t.values).values
                intr = np.maximum(k - ss, 0)
                below = int(((x.close.values < intr - max(0.5, 0.01 * k * 0.0)) & ~np.isnan(ss)).sum())
            rows.append({"day": day, "expiry": e, "strike": k, "bars_after_entry": len(inw), "has_entry_bar": has_ent, "max_gap_min": gap,
                         "ohlc_bad": ohlc_bad, "neg_zero": neg, "dup": dup, "max_min_jump_pct": jump, "below_intrinsic": below, "sources": "+".join(sorted(raw["source"].unique()))})
    A = pd.DataFrame(rows)
    A.to_csv(os.path.join(ROOT, "results", "data_audit_option_days.csv"), index=False)
    print("\n== Option minutes on the 259 G1 days (the traded ATM put) ==")
    print(" days checked:", len(A), "| days with no option file:", len([p for p in probs if p[1] == 'no option file']))
    print(" entry minute bar present:", int(A.has_entry_bar.sum()), "of", len(A), "| days where the entry bar is missing:", int((~A.has_entry_bar).sum()))
    print(" bars from entry to 15:29: median", int(A.bars_after_entry.median()), "min", int(A.bars_after_entry.min()), "| days with a gap > 10 min between bars:", int((A.max_gap_min > 10).sum()), "(max gap", int(A.max_gap_min.max()), "min)")
    print(" OHLC-inconsistent bars:", int(A.ohlc_bad.sum()), "| zero / negative prices:", int(A.neg_zero.sum()), "| duplicate timestamps:", int(A.dup.sum()))
    print(" minute-to-minute jumps > 50 %:", int((A.max_min_jump_pct > 50).sum()), "days | > 100 %:", int((A.max_min_jump_pct > 100).sum()), "days")
    print(" bars priced below intrinsic value (K - spot): total", int(A.below_intrinsic.sum()), "on", int((A.below_intrinsic > 0).sum()), "days")
    print(" sources on the day's chain:", A.sources.value_counts().to_dict())
    return A


if __name__ == "__main__":
    sa, spot = spot_audit()
    vix_audit()
    option_audit(spot)
