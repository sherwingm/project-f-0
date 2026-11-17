"""Cross-checks of the data downloaded on 17 Nov 2026 against sources already in the project. Output: ../DOWNLOAD_QUALITY_CHECKS.md. Read-only on all data."""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RI = os.path.dirname(HERE)
EX = os.path.join(RI, "external_data")
REPO = os.path.dirname(os.path.dirname(RI))
STORE = os.path.join(os.path.dirname(REPO), "fo-index-data", "data", "index")
out = ["# Download quality checks (17 Nov 2026)", "", "Every number below is computed by `scripts/quality_checks.py` from the downloaded files and existing project files.", ""]


def sec(t):
    out.append(f"## {t}")


# 1 NSE index file vs project NIFTY daily closes
ix = pd.read_csv(os.path.join(EX, "nse_index_closes.csv"))
ix["d"] = pd.to_datetime(ix["date"])
n50 = ix[ix["index_name"].str.strip().str.upper() == "NIFTY 50"].set_index("d")["close"].astype(float)
loc = pd.read_csv(os.path.join(REPO, "data", "eod2", "nifty 50.csv"), parse_dates=["Date"]).set_index("Date")["Close"]
j = pd.concat([n50.rename("nse"), loc.rename("local")], axis=1).dropna()
d = (j["nse"] / j["local"] - 1).abs() * 100
sec("1. NSE all-index file: NIFTY 50 vs data/eod2/nifty 50.csv")
out.append(f"- Overlap {len(j)} days ({j.index.min().date()} to {j.index.max().date()}); median absolute difference {d.median():.4f} %; days differing by more than 0.1 %: {(d > 0.1).sum()}; maximum {d.max():.3f} %.")
out.append(f"- NSE file covers {ix['date'].nunique()} dates, {ix['date'].min()} to {ix['date'].max()}; {ix['index_name'].nunique()} index names (sector, midcap, smallcap, VIX and others).")
# 2 VIX
vx = ix[ix["index_name"].str.strip() == "India VIX"].set_index("d")["close"].astype(float)
vd = pd.read_parquet(os.path.join(STORE, "vix_daily.parquet"))
vd["d"] = pd.to_datetime(vd["date"])
vd = vd.set_index("d")["close"].dropna()
j2 = pd.concat([vx.rename("nse"), vd.rename("store")], axis=1).dropna()
dd = (j2["nse"] / j2["store"] - 1).abs() * 100
sec("2. India VIX: NSE index file vs store vix_daily.parquet")
out.append(f"- Overlap {len(j2)} days; median absolute difference {dd.median():.3f} %; days above 2 %: {(dd > 2).sum()}; maximum {dd.max():.2f} %.")
# 3 stockezee
fd = pd.read_csv(os.path.join(EX, "fii_dii_cash_stockezee.csv"), parse_dates=["date"]).set_index("date")
j3 = pd.concat([fd["nifty_close"].rename("sz"), n50.rename("nse")], axis=1).dropna()
dd3 = (j3["sz"] / j3["nse"] - 1).abs() * 100
j4 = pd.concat([fd["india_vix"].rename("sz"), vx.rename("nse")], axis=1).dropna()
dd4 = (j4["sz"] / j4["nse"] - 1).abs() * 100
sec("3. FII / DII cash (stockezee, third party): its NIFTY close and VIX vs NSE's own files")
out.append(f"- {len(fd)} rows, {fd.index.min().date()} to {fd.index.max().date()}; includes Sunday special sessions (e.g. 2026-02-01, 2026-11-08).")
out.append(f"- NIFTY close: {len(j3)} overlapping days, maximum difference {dd3.max():.3f} %, days above 0.05 %: {(dd3 > 0.05).sum()}. VIX: {len(j4)} days, maximum difference {dd4.max():.2f} %.")
months = fd.groupby(fd.index.to_period("M")).size()
out.append("- Rows per month: " + ", ".join(f"{k} {v}" for k, v in months.items()) + ". **2026-09 has no rows at all (the source archive is empty for September 2026).**")
out.append("- Provenance: FII / DII cash net values equal NSE's combined NSE-BSE-MSEI table on 2026-11-17 (4,195.38 / 196.93 crore); no other day could be compared to an official file, so every other day is unverified.")
# 4 GIFT
g = pd.read_csv(os.path.join(EX, "gift_bhavcopy_futures.csv"))
g["d"] = pd.to_datetime(g["trade_date"])
g["c"] = g["contract"].astype(str)
n = g[g["c"].str.match(r"^FUTIDXNIFTY\d{2}-[A-Z]{3}-\d{4}$")].copy()
n["exp"] = pd.to_datetime(n["c"].str[11:], format="%d-%b-%Y")
n = n.sort_values(["d", "exp"]).groupby("d").first()
sec("4. GIFT NIFTY futures bhavcopy (near-month NIFTY)")
out.append(f"- {len(n)} trading days, {n.index.min().date()} to {n.index.max().date()}; days with a zero open (no trade in session 1): {(n['open'].astype(float) == 0).sum()}.")
for col in ("prev_settle", "open", "settlement"):
    n[col] = n[col].astype(float)
nz = n[n["open"] > 0].copy()
loc_prev = loc.shift(1)
nz["nifty_prev_close"] = loc_prev.reindex(nz.index)
nz["gap_open_vs_prev_nifty_close_pct"] = (nz["open"] / nz["nifty_prev_close"] - 1) * 100
nz["gap_prevsettle_vs_prev_nifty_close_pct"] = (nz["prev_settle"] / nz["nifty_prev_close"] - 1) * 100
nz["nifty_open"] = pd.read_csv(os.path.join(REPO, "data", "eod2", "nifty 50.csv"), parse_dates=["Date"]).set_index("Date")["Open"].reindex(nz.index)
nz["nifty_gap_pct"] = (nz["nifty_open"] / nz["nifty_prev_close"] - 1) * 100
q = nz.dropna(subset=["gap_open_vs_prev_nifty_close_pct", "nifty_gap_pct"])
c1 = q["gap_open_vs_prev_nifty_close_pct"].corr(q["nifty_gap_pct"])
c2 = q["gap_prevsettle_vs_prev_nifty_close_pct"].corr(q["nifty_gap_pct"])
out.append(f"- GIFT 06:30 open vs previous NIFTY cash close (includes futures carry of about 0.2-0.4 %): median {q['gap_open_vs_prev_nifty_close_pct'].median():.2f} %, inter-quartile {q['gap_open_vs_prev_nifty_close_pct'].quantile(.25):.2f} to {q['gap_open_vs_prev_nifty_close_pct'].quantile(.75):.2f} %.")
out.append(f"- Correlation with the ACTUAL NIFTY opening gap (09:15 open vs previous close), {len(q)} days: GIFT open-based {c1:.2f}; GIFT previous-settlement-based {c2:.2f}. (This is a descriptive check that the GIFT fields carry overnight information, not a trading test.)")
out.append("- Timing: `open` is the first trade of the GIFT session that starts 06:30 IST of the trade date (before any 09:30-13:00 IST entry); `prev_settle` is the previous trade date's settlement as published with this file; their exact publication clock times are not stated in the files (stated limitation).")
# 5 breadth
bd = pd.read_csv(os.path.join(EX, "nse_breadth_daily.csv"))
sec("5. Market breadth aggregates (NSE full equity bhavcopy, EQ series)")
out.append(f"- {len(bd)} days, {bd['date'].min()} to {bd['date'].max()}; equities per day median {bd['n_eq'].median():.0f}; advances+declines+unchanged equals n_eq on {(bd['advances'] + bd['declines'] + bd['unchanged'] == bd['n_eq']).mean() * 100:.0f} % of days.")
bd["d"] = pd.to_datetime(bd["date"])
bd = bd.set_index("d")
ret = loc.pct_change().reindex(bd.index)
ad = (bd["advances"] / (bd["advances"] + bd["declines"]))
out.append(f"- Correlation of advance share with that day's NIFTY return: {ad.corr(ret):.2f} (a sanity check; breadth should move with the index).")
# 6 Yahoo
sec("6. Yahoo series (global markets)")
yd = os.path.join(EX, "yahoo")
for f in sorted(os.listdir(yd)):
    y = pd.read_csv(os.path.join(yd, f))
    y["t"] = pd.to_datetime(y["timestamp_utc"])
    c = y["close"].astype(float)
    r = c.pct_change().abs()
    out.append(f"- {f}: {len(y)} rows, {y['t'].min().date()} to {y['t'].max().date()}, missing closes {int(c.isna().sum())}, largest one-step move {r.max() * 100:.1f} %, steps above 10 %: {(r > 0.10).sum()}.")
gs = pd.read_csv(os.path.join(yd, "GSPC_1d.csv"))
gs["d"] = pd.to_datetime(gs["timestamp_utc"]).dt.normalize()
old = pd.read_csv(os.path.join(REPO, "data", "parents", "yf_GSPC.csv"), parse_dates=["Date"]).set_index("Date")["Close"]
jj = pd.concat([gs.set_index("d")["close"].rename("new"), old.rename("old")], axis=1).dropna()
out.append(f"- S&P 500 new download vs the project's cached file: {len(jj)} overlapping days, maximum difference {((jj['new'] / jj['old'] - 1).abs() * 100).max():.3f} %.")
br = pd.read_csv(os.path.join(yd, "BRENT_1d.csv"))
out.append(f"- Brent: DECISIONS.md records Yahoo daily vs hourly Brent disagreeing by 4-7 % on some days; only the daily series was downloaded, and its largest one-day move is {br['close'].astype(float).pct_change().abs().max() * 100:.1f} %. Treat crude with caution.")
open(os.path.join(RI, "DOWNLOAD_QUALITY_CHECKS.md"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
