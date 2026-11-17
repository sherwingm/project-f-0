"""Agent 1 follow-up 3 (read-only): trade-date calendar problems, breadth holiday rows, manifest hash verification.
Run: python -W ignore inventory_checks3.py > checks_output3.txt"""
import os, glob, json, hashlib
import numpy as np, pandas as pd

R = "C:/Users/sherw/project-f-0"
S = "C:/Users/sherw/fo-index-data/data/index"
X = R + "/index_context_research/regime_investigation/external_data"


def h(t):
    print("\n" + "=" * 8, t)


h("K. manifest hash verification (files unchanged since manifest)")
man = json.load(open(R + "/index_context_research/regime_investigation/DATA_DOWNLOAD_MANIFEST.json"))
bad = 0
for fn, meta in man["files"].items():
    hh = hashlib.sha256(open(f"{X}/{fn}", "rb").read()).hexdigest()[:16]
    ok = hh == meta["sha256_16"]
    bad += (not ok)
    if not ok:
        print("  MISMATCH", fn, hh, meta["sha256_16"])
print("  files checked:", len(man["files"]), " mismatches:", bad)

ic = pd.read_csv(X + "/nse_index_closes.csv", usecols=["date", "index_name", "close"], low_memory=False)
n50 = ic[ic.index_name == "Nifty 50"].copy()
n50["date"] = pd.to_datetime(n50.date)
SESS = pd.DatetimeIndex(sorted(n50.date.unique()))

# minute-store calendar (full sessions with >=300 bars)
fs = sorted(glob.glob(f"{S}/spot_1m/NIFTY50/*.parquet"))
sp = pd.concat([pd.read_parquet(f, columns=["timestamp"]) for f in fs])
per = sp.groupby(sp.timestamp.dt.date).size()
MIN_SESS = pd.DatetimeIndex(pd.to_datetime(per[per >= 300].index))

h("L. trade sets vs calendars")
t = pd.read_csv(R + "/g1_research/results/g1_live_replay_trades.csv")
c = pd.read_csv(R + "/g1_research/data/g1c_opt_trades.csv")
xp = pd.read_csv(R + "/g1_research/data/xp_history_minute.csv")
b = pd.read_csv(X + "/nse_breadth_daily.csv"); b["date"] = pd.to_datetime(b.date)
g = pd.read_csv(X + "/gift_bhavcopy_futures.csv", low_memory=False); g["trade_date"] = pd.to_datetime(g.trade_date)
gdates = set(g.trade_date)
special_missing_from_nse = sorted(set(MIN_SESS) - set(SESS))
print("full sessions in minute store but absent from NSE index file:", [str(x.date()) for x in special_missing_from_nse])
f = pd.read_csv(X + "/fii_dii_cash_stockezee.csv"); f["date"] = pd.to_datetime(f.date)
pdt = set(pd.to_datetime([os.path.basename(p)[:-4] for p in glob.glob(R + "/g1_research/data/external/participant_oi/*.csv")]))
ALL = MIN_SESS.union(SESS[(SESS < "2021-10-20")])  # best available session calendar (minute store from 2021-10-20, NSE file before)
for nm, dts in [("G1F", t[t.g1f == 1].day), ("G1", t.day), ("G1C", c.day), ("XP", xp.day)]:
    dts = pd.to_datetime(dts)
    on_special = [str(d.date()) for d in dts if d in special_missing_from_nse]
    prev_special = []
    prev_calendar_diff = 0
    for d in dts:
        i = ALL.searchsorted(d)
        pm = ALL[i - 1]
        pn = SESS[SESS.searchsorted(d) - 1]
        if pm != pn:
            prev_calendar_diff += 1
            prev_special.append(str(d.date()))
    no_gift = [str(d.date()) for d in dts if d not in gdates]
    print(f"{nm}: n={len(dts)}; trade ON a session absent from NSE index file: {on_special}; trades whose previous full session (minute calendar) != previous NSE-file session: {prev_calendar_diff} {prev_special}; no GIFT row on trade date: {no_gift}")
    # breadth stale rows on previous session
    prevs = [ALL[ALL.searchsorted(d) - 1] for d in dts]
    bset = set(b.date)
    print("     previous full session has no breadth row:", [str(p.date()) for p in prevs if p not in bset][:10], " ; trade dates = Mon after special/holiday etc not examined")
    print("     previous session in FII window with no FII row (excl. Sept 2026):", sum(1 for p in prevs if p >= pd.Timestamp('2025-12-01') and p not in set(f.date) and not (p.year == 2026 and p.month == 9)), " in Sept 2026:", sum(1 for p in prevs if p.year == 2026 and p.month == 9), " before 2025-12:", sum(1 for p in prevs if p < pd.Timestamp('2025-12-01')))
    print("     previous session without participant OI file:", sum(1 for p in prevs if p not in pdt))

h("M. breadth rows on non-session dates that are NOT copies of the previous row")
bb = b.set_index("date")
extra = bb[~bb.index.isin(SESS)]
nd = []
for d in extra.index:
    i = bb.index.get_loc(d)
    same = (bb.iloc[i][["advances", "declines", "unchanged"]].values == bb.iloc[i - 1][["advances", "declines", "unchanged"]].values).all()
    if not same:
        nd.append(str(d.date()))
print("  non-duplicate holiday-dated rows:", nd)
for d in nd:
    i = bb.index.get_loc(pd.Timestamp(d))
    print(bb.iloc[i - 1:i + 2][["n_eq", "advances", "declines", "unchanged", "turnover_lacs"]].to_string())
# are stale copies also in Saturday/Sunday special days?
print("  breadth rows on special sessions absent from NSE file:", [str(d.date()) for d in special_missing_from_nse if d in bb.index])
print("  duplicate-of-previous rows on NSE *session* dates (genuine duplicates?):", int(((bb.loc[bb.index.isin(SESS), ["advances", "declines", "unchanged", "turnover_lacs"]].diff().abs().sum(axis=1)) == 0).sum()))

h("N. GIFT near-month, rows on NSE sessions only: rows missing")
gn = g[g.contract.str.startswith("FUTIDXNIFTY") & ~g.contract.str.contains("NIFTYIT|NIFTYNXT|NIFTYFPI")]
print("  NSE sessions 2023-07-03..2026-11-17 with no GIFT row:", [str(d.date()) for d in SESS if d >= pd.Timestamp('2023-07-03') and d not in gdates])
print("  special sessions (minute store only) with no GIFT row:", [str(d.date()) for d in special_missing_from_nse if d >= pd.Timestamp('2023-07-03') and d not in gdates])
