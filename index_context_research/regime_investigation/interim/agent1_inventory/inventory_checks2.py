"""Agent 1 follow-up checks (read-only): data semantics that the first pass raised.
Run: python -W ignore inventory_checks2.py > checks_output2.txt"""
import os, re, glob, sqlite3
import numpy as np, pandas as pd

R = "C:/Users/sherw/project-f-0"
S = "C:/Users/sherw/fo-index-data/data/index"
X = R + "/index_context_research/regime_investigation/external_data"
Y = X + "/yahoo"


def h(t):
    print("\n" + "=" * 8, t)


ic = pd.read_csv(X + "/nse_index_closes.csv", usecols=["date", "index_name", "open", "close", "change_pct"], low_memory=False)
n50 = ic[ic.index_name == "Nifty 50"].copy()
n50["date"] = pd.to_datetime(n50["date"])
n50 = n50.set_index("date").sort_index()
nclose = n50.close.astype(float)
nopen = n50.open.astype(float)
SESS = pd.DatetimeIndex(n50.index)

h("A. GIFT prev_settle semantics")
g = pd.read_csv(X + "/gift_bhavcopy_futures.csv", low_memory=False)
g["trade_date"] = pd.to_datetime(g.trade_date)
g = g[g.contract.str.startswith("FUTIDXNIFTY") & ~g.contract.str.startswith("FUTIDXNIFTYIT") & ~g.contract.str.startswith("FUTIDXNIFTYNXT") & ~g.contract.str.startswith("FUTIDXNIFTYFPI")].copy()
g["exp"] = pd.to_datetime(g.contract.str.extract(r"(\d{2}-[A-Z]{3}-\d{4})$")[0], format="%d-%b-%Y")
print("contracts parsed:", g.contract.str.replace(r"\d{2}-[A-Z]{3}-\d{4}$", "", regex=True).unique())
g = g.sort_values(["trade_date", "exp"])
nm = g[g.exp >= g.trade_date].groupby("trade_date").head(1).set_index("trade_date")
print("near-month rows:", len(nm), " oi non-null:", int(nm.oi.notna().sum()), " oi non-null by year:", nm.oi.notna().groupby(nm.index.year).sum().to_dict())
print("  net_change non-null:", int(nm.net_change.notna().sum()), " traded_value non-null", int(nm.traded_value.notna().sum()))
prev_row_settle = nm.settlement.shift(1)
same = nm.contract == nm.contract.shift(1)
d = ((nm.prev_settle - prev_row_settle) / prev_row_settle)[same]
print("prev_settle(t) / settlement(t-1 row, same contract) - 1: n", d.notna().sum(), " mean %.5f std %.5f abs-median %.5f max %.4f" % (d.mean(), d.std(), d.abs().median(), d.abs().max()))
print("  share with exactly equal:", float((d == 0).mean()))
# relation with S&P US session of calendar day t-1 (closes 01:30-02:30 IST of t)
gs = pd.read_csv(Y + "/GSPC_1d.csv")
gs["d"] = pd.to_datetime(gs.timestamp_utc).dt.normalize()
spr = gs.set_index("d").close.pct_change()
for lag_name, shift_days in [("US date = t-1 cal day (closes ~01:30-02:30 IST of t)", 1), ("US date = t (closes 01:30-02:30 IST of t+1)", 0)]:
    xs = []
    for t_, v in d.dropna().items():
        key = t_ - pd.Timedelta(days=shift_days)
        # use latest US date <= key
        idx = spr.index[spr.index <= key]
        if len(idx): xs.append((v, spr.loc[idx[-1]], idx[-1]))
    a = np.array([(x[0], x[1]) for x in xs])
    print("  corr(prev_settle/settle(t-1)-1, S&P ret) [%s]: %.3f (n=%d)" % (lag_name, np.corrcoef(a[:, 0], a[:, 1])[0, 1], len(a)))
# open-based gaps vs actual NIFTY open gap
nm2 = nm.join(nclose.rename("cash_close"), how="left").join(nopen.rename("cash_open"), how="left")
sess_idx = {t: i for i, t in enumerate(SESS)}
rows = []
for t_ in nm2.index:
    if t_ in sess_idx and sess_idx[t_] > 0:
        pc = nclose.iloc[sess_idx[t_] - 1]
        rows.append((t_, nm2.loc[t_, "open"], nm2.loc[t_, "prev_settle"], prev_row_settle.loc[t_], nopen.loc[t_] / pc - 1, nm2.loc[t_, "settlement"]))
q = pd.DataFrame(rows, columns=["t", "g_open", "g_prev_settle", "g_prev_row_settle", "actual_gap", "g_settle"]).set_index("t")
q["open_vs_prev_settle"] = q.g_open / q.g_prev_settle - 1
q["open_vs_prev_row_settle"] = q.g_open / q.g_prev_row_settle - 1
q["prev_settle_vs_prev_row_settle"] = q.g_prev_settle / q.g_prev_row_settle - 1
q = q.dropna()
print("  n for gap comparison:", len(q), "(NIFTY sessions, GIFT trade date == session date, previous GIFT row exists)")
for c in ["open_vs_prev_settle", "open_vs_prev_row_settle", "prev_settle_vs_prev_row_settle"]:
    print("  %s: std %.5f  corr with actual NIFTY 09:15 gap %.3f" % (c, q[c].std(), q[c].corr(q.actual_gap)))
print("  actual NIFTY gap std %.5f" % q.actual_gap.std())
print("  GIFT open vs 09:15 cash open (T): median diff (futures premium) %.4f" % ((q.g_open / nopen.loc[q.index] - 1).median()))
# is open-based gap robust to previous-row settlement: share with |open-prev_row_settle|/|...|
print("  where open == 0 or settle 0:", int((nm.open == 0).sum()))

h("B. breadth file on NSE non-session dates")
b = pd.read_csv(X + "/nse_breadth_daily.csv")
b["date"] = pd.to_datetime(b.date)
extra = b[~b.date.isin(SESS)]
print("rows on dates not in NSE index file:", len(extra), " weekday dist:", extra.date.dt.dayofweek.value_counts().sort_index().to_dict())
print("first 10:\n", extra.head(10).to_string())
bb = b.set_index("date")
dup_prev = 0
for t_ in extra.date:
    i = bb.index.get_loc(t_)
    if i > 0 and (bb.iloc[i][["advances", "declines", "unchanged"]].values == bb.iloc[i - 1][["advances", "declines", "unchanged"]].values).all():
        dup_prev += 1
print("  of these, rows identical (adv/dec/unch) to the previous file row:", dup_prev)
print("  full duplicates of consecutive rows in whole file:", int((bb[["advances", "declines", "unchanged", "turnover_lacs"]].diff().abs().sum(axis=1) == 0).sum()))
# dates in NSE index file with a NIFTY row but nothing in breadth
print("  NSE sessions without breadth row (2021-10..):", [str(x.date()) for x in SESS if x >= pd.Timestamp("2021-10-01") and x not in set(b.date)][:30])
print("  extra dates list:", [str(x.date()) for x in extra.date][:60])
print("  turnover on extra dates (median) vs normal:", float(extra.turnover_lacs.median()), float(b.turnover_lacs.median()))
# is advance share of an extra date consistent with NIFTY change of the next listed session? (skip) show their NIFTY cash change on same date from Yahoo NSEI
ys = pd.read_csv(Y + "/NSEI_1d.csv")
ys["d"] = (pd.to_datetime(ys.timestamp_utc) + pd.to_timedelta(ys.local_offset_s, unit="s")).dt.normalize()
print("  Yahoo NSEI has rows on these extra dates:", int(extra.date.isin(set(ys.d)).sum()), "of", len(extra))

h("C. participant OI header-date vs filename")
po = sorted(glob.glob(R + "/g1_research/data/external/participant_oi/*.csv"))
bad = []
fmts = {}
for p in po:
    first = open(p).readline().replace('"', "").strip()
    m = re.search(r"as on ([A-Za-z]{3}) (\d{1,2}),\s*(\d{4})", first)
    dt = pd.to_datetime(f"{m.group(2)} {m.group(1)} {m.group(3)}") if m else None
    fn = pd.Timestamp(os.path.basename(p)[:-4])
    if dt is None or dt != fn:
        bad.append((os.path.basename(p), first[:100]))
print("files whose header date != filename (after stripping quotes):", len(bad), bad[:5])
# NaNs / zero totals in index futures
rows = []
for p in po:
    dd_ = pd.read_csv(p, skiprows=1)
    dd_.columns = [c.strip().strip("\t").strip() for c in dd_.columns]
    dd_ = dd_.set_index(dd_.columns[0])
    dd_.index = [str(i).strip().upper() for i in dd_.index]
    r = {"date": os.path.basename(p)[:-4]}
    for who in ["CLIENT", "DII", "FII", "PRO"]:
        r[who + "_idxfut_long"] = float(dd_.loc[who, "Future Index Long"]); r[who + "_idxfut_short"] = float(dd_.loc[who, "Future Index Short"])
        r[who + "_optcalllong"] = float(dd_.loc[who, "Option Index Call Long"])
    rows.append(r)
po_df = pd.DataFrame(rows)
print("parsed", len(po_df), "files; any NaN:", int(po_df.isna().sum().sum()), " FII idx fut long==0 days:", int((po_df.FII_idxfut_long == 0).sum()), " DII idx fut long==0:", int((po_df.DII_idxfut_long == 0).sum()), " DII idx fut zero both sides days:", int(((po_df.DII_idxfut_long == 0) & (po_df.DII_idxfut_short == 0)).sum()))
print("  day-on-day |change| of FII idx fut long > 50%:", int((po_df.FII_idxfut_long.pct_change().abs() > .5).sum()))

h("D. Yahoo day keys (UTC date), weekday check, partial last rows, opens")
for fn in sorted(os.listdir(Y)):
    if not fn.endswith("_1d.csv"):
        continue
    d = pd.read_csv(f"{Y}/{fn}")
    ts = pd.to_datetime(d.timestamp_utc)
    utc_wd = ts.dt.dayofweek.value_counts().sort_index().to_dict()
    # candidate key rule
    key = ts.dt.normalize()
    if fn.startswith(("USDINR", "ASX200")):
        key = (ts + pd.Timedelta(hours=1 if fn.startswith("USDINR") else 12)).dt.normalize()
    wd = key.dt.dayofweek.value_counts().sort_index().to_dict()
    dd2 = d.assign(key=key)
    dup = int(dd2.key.duplicated().sum())
    valid = dd2.dropna(subset=["close"])
    print(f"{fn}: UTC-date weekdays {utc_wd} | chosen key weekdays {wd} | dup keys {dup} | rows with close {len(valid)} | rows w/o close {len(d)-len(valid)} | open NaN {int(d.open.isna().sum())}")
    # open == prev close share (gap info lost?)
    o = d.open.values; c = d.close.shift(1).values
    same_ = np.nanmean(np.isclose(o, c, rtol=0, atol=1e-6))
    print(f"      share of days open==previous close exactly: {same_:.3f};  open==close same day share {np.nanmean(np.isclose(d.open.values, d.close.values, rtol=0, atol=1e-6)):.3f}")
# Asian gap quality
for fn in ["N225_1d.csv", "HSI_1d.csv", "KOSPI_1d.csv", "SSEC_1d.csv", "TWII_1d.csv", "ASX200_1d.csv"]:
    d = pd.read_csv(f"{Y}/{fn}").dropna(subset=["close"])
    gap = d.open / d.close.shift(1) - 1
    print(f"  {fn} open-gap: n {gap.notna().sum()}, std {gap.std():.4f}, zero-gap share {(gap.abs()<1e-9).mean():.3f}, |gap|>5%: {(gap.abs()>.05).sum()}, open==high==low==close days {((d.open==d.high)&(d.high==d.low)).sum()}")

h("E. Oil / gold roll jumps (2026) and WTI-Brent")
br = pd.read_csv(Y + "/BRENT_1d.csv"); br["d"] = pd.to_datetime(br.timestamp_utc).dt.normalize()
wt = pd.read_csv(Y + "/WTI_1d.csv"); wt["d"] = pd.to_datetime(wt.timestamp_utc).dt.normalize()
m = br.set_index("d").close.to_frame("brent").join(wt.set_index("d").close.rename("wti"))
m["br_ret"] = m.brent.pct_change(); m["wt_ret"] = m.wti.pct_change()
big = m[(m.br_ret.abs() > .08) & (m.index >= "2024-01-01")]
print(big.to_string())
print("Brent-WTI spread (>$15 or <$0) days since 2022:", int(((m.brent - m.wti).loc["2022":] .abs() > 15).sum()), " days since 2022 where Brent and WTI returns differ by >5pts:", int(((m.br_ret - m.wt_ret).abs().loc["2022":] > .05).sum()))
print("older cache BZ_F vs new Brent (daily close) overlap diff:")
ob = pd.read_csv(R + "/data/parents/yf_BZ_F.csv"); ob["d"] = pd.to_datetime(ob.Date)
cc = ob.set_index("d").Close.to_frame("old").join(m.brent.rename("new"), how="inner"); cc["rel"] = (cc.old / cc.new - 1).abs()
print("   overlap", len(cc), "max rel diff %.4f; days >1%%: %d" % (cc.rel.max(), int((cc.rel > .01).sum())))

h("F. VIX odd rows and NIFTY big 1-min moves")
import sys
sys.path.insert(0, R); os.environ["INDEX_STORE"] = S
import index_data.load as L
L.read_store = lambda p, columns=None: pd.read_parquet(p)
v = L.vix_1m("2025-04-07", "2025-04-07")
print("repaired VIX 2025-04-07: open/high/low/close range:", v.open.iloc[0], v.high.max(), v.low.min(), v.close.iloc[-1], " rows", len(v))
vd = pd.read_parquet(S + "/vix_daily.parquet"); print(vd[vd.date.astype(str) == "2025-04-07"].to_string())
fs = sorted(glob.glob(f"{S}/spot_1m/NIFTY50/*.parquet"))
sp = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
sp["d"] = sp.timestamp.dt.date
r = sp.sort_values("timestamp").close.pct_change()
same_day = sp.sort_values("timestamp").d == sp.sort_values("timestamp").d.shift(1)
print("NIFTY 1-min within-day |ret|>2%:", int(((r.abs() > .02) & same_day).sum()), sp.sort_values("timestamp").loc[((r.abs() > .02) & same_day), ["timestamp", "close"]].head(8).to_string())
f9 = sp[sp.timestamp.dt.strftime("%H:%M") == "09:15"]
print("09:15 NIFTY bar degenerate (high==low) share:", float((f9.high == f9.low).mean()), " by year:", (f9.high == f9.low).groupby(f9.timestamp.dt.year).mean().round(3).to_dict(), " volume non-zero share", float((f9.volume > 0).mean()))
print("09:15 open vs previous session last close gap sample (first 5 days of 2024):")
sp24 = sp[sp.timestamp.dt.year == 2024]
fo = sp24[sp24.timestamp.dt.strftime("%H:%M") == "09:15"].set_index("d").open
lc = sp24[sp24.timestamp.dt.strftime("%H:%M") == "15:29"].set_index("d").close
print(pd.DataFrame({"open0915": fo, "prev_1529": lc.shift(1)}).head(4).to_string())

h("G. events.sqlite, other event lists")
con = sqlite3.connect("file:" + R + "/data/events.sqlite?mode=ro", uri=True)
print(pd.read_sql("select type, count(*) n, min(event_date) first, max(event_date) last from events group by type", con).to_string())
print(pd.read_sql("select symbol, count(*) n from events group by symbol order by n desc limit 5", con).to_string())
print(pd.read_sql("select count(*) n from events where symbol in ('NIFTY','NIFTY 50','BANKNIFTY','INDIA','MARKET')", con).to_string())
con.close()

h("H. sensex/calls trade-record files in g1_research/data")
for fn in ["sensex_maxup_free_trades.csv", "calls_sensex_maxup_free_trades.csv", "calls_nifty_maxup_free_trades.csv", "g1_maxup_free_trades.csv"]:
    d = pd.read_csv(f"{R}/g1_research/data/{fn}")
    dc = [c for c in d.columns if c in ("day", "date")][0]
    print(fn, len(d), list(d.columns)[:10], d[dc].min(), d[dc].max())

h("I. hourly ES/NQ/USDINR coverage of the 06:30-09:15 IST window per Indian session")
for fn in ["ES_F_60m.csv", "NQ_F_60m.csv", "USDINR_60m.csv"]:
    d = pd.read_csv(f"{Y}/{fn}")
    d = d.dropna(subset=["close"])
    ist = pd.to_datetime(d.timestamp_utc) + pd.Timedelta(hours=5, minutes=30)
    mins = ist.dt.hour * 60 + ist.dt.minute
    win = ist[(mins >= 360) & (mins < 555)].dt.normalize()
    cnt = win.value_counts()
    sess = SESS[(SESS >= ist.min().normalize()) & (SESS <= pd.Timestamp("2026-10-28"))]
    have = sum(1 for t_ in sess if t_ in cnt.index)
    print(f"{fn}: non-NaN bars {len(d)}; IST sessions 2024-11-18..2026-10-28: {len(sess)}; sessions with >=1 non-NaN bar stamped 06:00-09:15 IST: {have}; bar stamps (minutes past hour):", pd.to_datetime(d.timestamp_utc).dt.minute.value_counts().head(3).to_dict())
    if fn.startswith("ES"):
        print("   hours (IST) with most bars:", ist.dt.hour.value_counts().head(8).to_dict(), " (CME Globex closes 03:30 IST daily break 22:30-23:30 IST)")

h("J. FII/DII stockezee: sign convention and Sunday rows")
f = pd.read_csv(X + "/fii_dii_cash_stockezee.csv"); f["date"] = pd.to_datetime(f.date)
print(f[f.date.isin(pd.to_datetime(["2026-02-01", "2026-11-08", "2026-11-17"]))].to_string())
print("rows with NaN nifty_close:", f[f.nifty_close.isna()].date.dt.strftime('%Y-%m-%d').tolist())
nj = f.set_index("date").join(nclose.rename("nse"))
nj["diff"] = (nj.nifty_close / nj.nse - 1).abs() * 100
print("largest 5 close differences vs NSE (%):\n", nj["diff"].nlargest(5).round(3).to_string())
nj["ret_nse"] = nclose.pct_change().reindex(nj.index)
print("corr(fii_cash_net, NIFTY same-day return):", round(nj.fii_cash_net.corr(nj.ret_nse), 3), " corr(dii, ret):", round(nj.dii_cash_net.corr(nj.ret_nse), 3), " corr(fii,dii):", round(nj.fii_cash_net.corr(nj.dii_cash_net), 3))
