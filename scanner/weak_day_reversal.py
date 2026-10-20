"""S1 fade · weak results filed in market hours: does an "already corrected" filing day predict the next day's call?

    python -m scanner.weak_day_reversal --nifty-dir <folder of spot_1m/NIFTY50/*.parquet>

strategies/S1_weak_result_day_reversal.md fixes every choice. Reads the weak cases of
S1_intraday_results_path_cases.csv, the stock minutes S1_intraday_minutes.csv, NIFTY 50 minutes, eod2 daily files,
the v10 backtest trades and (for v11) the fade minute trades. Writes data/results/S1_weak_day_reversal.md / _cases.csv.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

from .backtest_s1_v2 import md
from .build import ROOT
from .equity import load_symbol
from .results_intraday import at, hm
from .stats import clustered_t

RES, EOD2 = ROOT / "data" / "results", ROOT / "data" / "eod2"
CUT = -2.0
BUCKETS = [(-1e9, -3, "<= -3 %"), (-3, -1, "-3..-1 %"), (-1, 1, "-1..+1 %"), (1, 1e9, "> +1 %")]


def pct(a: float, b: float) -> float:
    return (b / a - 1) * 100 if a > 0 and b > 0 and not (math.isnan(a) or math.isnan(b)) else math.nan


def bucket(x: float) -> str:
    return next(n for lo, hi, n in BUCKETS if lo < x <= hi) if not math.isnan(x) else ""


def mstats(g: pd.DataFrame, col: str) -> dict:
    x = g.dropna(subset=[col])
    if x.empty:
        return {"n": 0}
    return {"n": len(x), "mean": round(x[col].mean(), 3), "median": round(x[col].median(), 3),
            "up %": round((x[col] > 0).mean() * 100, 1), "t": clustered_t(x[col], x["day"]) if len(x) > 1 else None}


def tstats(g: pd.DataFrame, net: str, pct_col: str) -> dict:
    x = g.dropna(subset=[pct_col])
    if x.empty:
        return {"n": 0}
    return {"n": len(x), "win %": round((x[net] > 0).mean() * 100, 1), "mean net %": round(x[pct_col].mean(), 2),
            "median net %": round(x[pct_col].median(), 2), "total Rs": round(x[net].sum()),
            "t": clustered_t(x[pct_col], x["day"]) if len(x) > 1 else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nifty-dir", type=Path, required=True)
    a = ap.parse_args()
    cases = pd.read_csv(RES / "S1_intraday_results_path_cases.csv")
    cases = cases[cases["class"] == "weak"][["symbol", "day", "t0", "window"]].reset_index(drop=True)
    mins = pd.read_csv(RES / "S1_intraday_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    stock = {k: g.drop_duplicates("t").set_index("t")["c"] for k, g in mins.groupby(["symbol", "day"])}
    nf = pd.concat([pd.read_parquet(p) for p in sorted(a.nifty_dir.glob("*.parquet"))])
    nf["day"], nf["t"] = nf["timestamp"].dt.strftime("%Y-%m-%d"), nf["timestamp"].dt.strftime("%H:%M")
    nifty = {d: g.drop_duplicates("t").set_index("t") for d, g in nf.groupby("day")}
    # the next session from the F&O bhavcopy calendar (it has the special sessions, e.g. Muhurat 2023-11-12 and the
    # Budget Sunday 2026-02-01, that the NIFTY minute files lack; such a day gets no market-adjusted next-day value)
    ndays = sorted(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}" for p in (ROOT / "data" / "cache").glob("fo_bhavcopy_*.csv"))

    rows = []
    for r in cases.itertuples():
        s, n = stock.get((r.symbol, r.day)), nifty.get(r.day)
        row = {"symbol": r.symbol, "day": r.day, "t0": r.t0, "window": r.window}
        pre_t = hm(r.t0, -1)
        d_raw = pct(at(s, pre_t), at(s, "15:29")) if s is not None else math.nan
        d_mkt = pct(at(n["close"], pre_t), at(n["close"], "15:29")) if n is not None else math.nan
        row["D_raw"], row["D"] = d_raw, d_raw - d_mkt
        i = ndays.index(r.day) if r.day in ndays else None
        nxt = ndays[i + 1] if i is not None and i + 1 < len(ndays) else None
        row["next_day"] = nxt
        try:
            f = load_symbol(r.symbol, EOD2)
            f.index = f.index.strftime("%Y-%m-%d")
            f = f[~f.index.duplicated(keep="last")]
        except Exception:  # noqa: BLE001 - no eod2 file
            f = None
        if nxt and f is not None and r.day in f.index and nxt in f.index:
            row["gap_raw"] = pct(float(f.loc[r.day, "Close"]), float(f.loc[nxt, "Open"]))
            row["day_raw"] = pct(float(f.loc[nxt, "Open"]), float(f.loc[nxt, "Close"]))
            nn = nifty.get(nxt)
            if nn is not None and n is not None:
                n_close_d, n_open, n_close = float(n["close"].iloc[-1]), float(nn["open"].iloc[0]), float(nn["close"].iloc[-1])
                row["gap"] = row["gap_raw"] - pct(n_close_d, n_open)
                row["next_day_move"] = row["day_raw"] - pct(n_open, n_close)
            else:
                row["gap"] = row["next_day_move"] = math.nan       # no NIFTY minutes that session
        rows.append(row)
    df = pd.DataFrame(rows)
    df["group"] = ["corrected (D <= -2 %)" if x <= CUT else "not corrected (D > -2 %)" if not math.isnan(x) else ""
                   for x in df["D"]]
    df["bucket"] = df["D"].map(bucket)

    # the fade's real call trades for these filings (v10 E1), and v11 on minutes where they exist
    ft = pd.concat([pd.read_csv(RES / "S1_v10_trades_2022_24.csv"), pd.read_csv(RES / "S1_v10_trades.csv")])
    ft = ft[(ft["entry"] == "open") & (ft["e1_excluded"].fillna("") == "") & (ft["side"] == "CE")]
    tr = ft.merge(df[["symbol", "day", "D", "group", "bucket", "window"]], left_on=["symbol", "filed"],
                  right_on=["symbol", "day"], how="inner")
    tr["net_pct"] = tr["e1_net_pct"].astype(float)
    try:
        from .fade_armA_filter import v11_minutes
        v11 = v11_minutes()
        v11 = v11[v11["side"] == "CE"][["symbol", "day0", "v11_net", "entry", "lot"]]
        tr = tr.merge(v11.rename(columns={"entry": "v11_entry", "lot": "v11_lot"}), on=["symbol", "day0"], how="left")
        tr["v11_pct"] = tr["v11_net"] / (tr["v11_entry"] * tr["v11_lot"]) * 100
    except Exception as exc:  # noqa: BLE001 - minute file missing: v11 not reported
        print("v11 not available:", exc)
        tr["v11_net"], tr["v11_pct"] = math.nan, math.nan
    tr["day"] = tr["day0"]                                     # cluster the trade results on the trade date

    groups = ["corrected (D <= -2 %)", "not corrected (D > -2 %)"]
    wins = ("2022-24", "2025-26", "all")
    stock_rows, trade_rows, v11_rows, bucket_rows = [], [], [], []
    for gname in groups:
        for w in wins:
            g = df[(df["group"] == gname) & ((df["window"] == w) | (w == "all"))]
            stock_rows.append({"group": gname, "window": w, "N": len(g), **{f"gap {k}": v for k, v in mstats(g, "gap").items() if k != "n"},
                               **{f"next day {k}": v for k, v in mstats(g, "next_day_move").items() if k != "n"}})
            gt = tr[(tr["group"] == gname) & ((tr["window"] == w) | (w == "all"))]
            trade_rows.append({"group": gname, "window": w, **tstats(gt, "e1_net", "net_pct")})
            gv = gt.dropna(subset=["v11_pct"])
            if w == "all":
                v11_rows.append({"group": gname, **tstats(gv, "v11_net", "v11_pct")})
    for b in [n for _, _, n in BUCKETS]:
        g, gt = df[df["bucket"] == b], tr[tr["bucket"] == b]
        bucket_rows.append({"D bucket": b, "cases": len(g), "next-day move mean %": mstats(g, "next_day_move").get("mean"),
                            **{f"call {k}": v for k, v in tstats(gt, "e1_net", "net_pct").items()}})

    t = pd.DataFrame(trade_rows).set_index(["group", "window"])
    c, nc = groups
    get = lambda gname, w, k: t.loc[(gname, w)].get(k) if (gname, w) in t.index else None  # noqa: E731
    n_all = get(c, "all", "n") or 0
    m1, m2 = get(c, "2022-24", "mean net %"), get(c, "2025-26", "mean net %")
    d1 = (m1 - get(nc, "2022-24", "mean net %")) if m1 is not None and get(nc, "2022-24", "mean net %") is not None else None
    d2 = (m2 - get(nc, "2025-26", "mean net %")) if m2 is not None and get(nc, "2025-26", "mean net %") is not None else None
    tt = get(c, "all", "t")
    test = pd.DataFrame([
        {"test": "1 at least 20 corrected call trades", "value": n_all, "pass": n_all >= 20},
        {"test": "2a corrected calls mean > 0 in 2022-24", "value": m1, "pass": bool(m1 is not None and m1 > 0)},
        {"test": "2b corrected calls mean > 0 in 2025-26", "value": m2, "pass": bool(m2 is not None and m2 > 0)},
        {"test": "3a corrected - not corrected > 0 in 2022-24", "value": None if d1 is None else round(d1, 2), "pass": bool(d1 is not None and d1 > 0)},
        {"test": "3b corrected - not corrected > 0 in 2025-26", "value": None if d2 is None else round(d2, 2), "pass": bool(d2 is not None and d2 > 0)},
        {"test": "4 pooled corrected t >= 2", "value": tt, "pass": bool(tt is not None and tt >= 2)},
    ])
    verdict = "PASS (a candidate filter for the user's decision)" if test["pass"].all() else "FAIL (nothing changes)"
    df.to_csv(RES / "S1_weak_day_reversal_cases.csv", index=False)
    tr.to_csv(RES / "S1_weak_day_reversal_trades.csv", index=False)
    text = "\n".join([
        "# S1 fade · weak results in market hours: does an already-corrected filing day predict the next day's call?\n",
        "Pre-registered: strategies/S1_weak_result_day_reversal.md. D = the stock's move from the minute before the "
        "announcement to the filing day's 15:29 close, minus NIFTY 50's. Corrected = D <= -2 %. Next day = the fade's "
        "day 0: gap = close to next open; next day = next open to next close (market-adjusted). Calls = the v10 "
        "backtest's real call trades for these filings (entry at the open, sold 15:20, net of charges). t date-clustered.\n",
        f"Weak market-hours cases: {len(df)}; matched fade call trades: {len(tr)}.\n",
        f"## Test: **{verdict}**\n\n" + md(test),
        "## The fade's call trades (v10, 15:20 exit)\n\n" + md(pd.DataFrame(trade_rows)),
        "## The stock the next day (market-adjusted %)\n\n" + md(pd.DataFrame(stock_rows)),
        "## By filing-day move\n\n" + md(pd.DataFrame(bucket_rows)),
        "## The same calls with v11's exit (minutes, Oct 2024 on; descriptive)\n\n" + md(pd.DataFrame(v11_rows)),
        "Cases: data/results/S1_weak_day_reversal_cases.csv; trades: S1_weak_day_reversal_trades.csv.\n",
    ])
    (RES / "S1_weak_day_reversal.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
