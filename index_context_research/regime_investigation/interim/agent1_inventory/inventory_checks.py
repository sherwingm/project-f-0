"""Agent 1 (data inventory) read-only checks. Prints facts only.
Run: python -W ignore inventory_checks.py > checks_output.txt
Windows python: C:/ paths. read_store is patched to plain read_parquet so no Feather cache is written into the repo."""
import os, sys, json, glob, re
import numpy as np, pandas as pd

R = "C:/Users/sherw/project-f-0"
S = "C:/Users/sherw/fo-index-data/data/index"
X = R + "/index_context_research/regime_investigation/external_data"
sys.path.insert(0, R)
os.environ["INDEX_STORE"] = S
import index_data.load as L
L.read_store = lambda p, columns=None: (pd.read_parquet(p) if columns is None else pd.read_parquet(p)[columns])


def h(t):
    print("\n" + "=" * 8, t)


def span(ds):
    ds = pd.to_datetime(pd.Series(ds)).dt.normalize().drop_duplicates().sort_values()
    return str(ds.iloc[0].date()), str(ds.iloc[-1].date()), len(ds)


def gaps(ds, ref, label, maxshow=15):
    ds = set(pd.to_datetime(pd.Series(ds)).dt.normalize())
    ref = set(pd.to_datetime(pd.Series(ref)).dt.normalize())
    lo, hi = min(ds), max(ds)
    miss = sorted(d for d in ref if lo <= d <= hi and d not in ds)
    extra = sorted(d for d in ds if d not in ref)
    print(f"  [{label}] missing vs session calendar within range: {len(miss)} {[str(d.date()) for d in miss[:maxshow]]}; extra not in calendar: {len(extra)} {[str(d.date()) for d in extra[:maxshow]]}")
    return miss, extra


h("0. reference calendar = NIFTY 50 rows of nse_index_closes.csv")
ic = pd.read_csv(X + "/nse_index_closes.csv", usecols=["date", "index_name", "open", "high", "low", "close", "change_pct", "volume"], low_memory=False)
n50 = ic[ic.index_name == "Nifty 50"].copy()
n50["date"] = pd.to_datetime(n50["date"])
SESS = pd.DatetimeIndex(sorted(n50["date"].unique()))
print("NIFTY 50 sessions in NSE index file:", span(SESS))
print("weekend dates in session list:", [str(d.date()) for d in SESS if d.weekday() >= 5])
print("indices in file:", ic.index_name.nunique(), " dates:", span(ic["date"]))
print("duplicates (date,index):", int(ic.duplicated(["date", "index_name"]).sum()))
nc = n50.set_index("date").close.astype(float)

h("1. spot_1m NIFTY50 / NIFTYBANK / SENSEX / INDIAVIX (raw)")
raw = {}
for idx in ["NIFTY50", "NIFTYBANK", "SENSEX", "INDIAVIX"]:
    fs = sorted(glob.glob(f"{S}/spot_1m/{idx}/*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    df["d"] = df.timestamp.dt.date
    raw[idx] = df
    print(f"{idx}: files {len(fs)} ({os.path.basename(fs[0])}..{os.path.basename(fs[-1])}), rows {len(df)}, dates {span(df.d)}")
    print("   tz:", df.timestamp.dt.tz, " dup timestamps:", int(df.duplicated('timestamp').sum()), " sources:", df.source.value_counts().to_dict())
    per = df.groupby("d").size()
    print("   bars/day: median", per.median(), " days with <375:", int((per < 375).sum()), " days with >375:", int((per > 375).sum()), " min", per.min())
    short = per[per < 375]
    print("   short days (first 12):", {str(k): int(v) for k, v in list(short.items())[:12]})
    fb = df.groupby('d').timestamp.min().dt.time
    lb = df.groupby('d').timestamp.max().dt.time
    print("   first bar time min/max:", fb.min(), fb.max(), " last bar min/max:", lb.min(), lb.max())
    print("   NaN close:", int(df.close.isna().sum()), " close<=0:", int((df.close <= 0).sum()), " high<low:", int((df.high < df.low).sum()))
    gaps(pd.Series(pd.to_datetime(df.d.unique())), SESS, idx + " vs NSE sessions")
    if idx != "INDIAVIX":
        d2 = df.sort_values("timestamp")
        r = d2.close.pct_change().abs()
        print("   1-min abs return > 1%:", int((r > 0.01).sum()), " >3%:", int((r > 0.03).sum()))
    flat = df.groupby("d").close.nunique()
    print("   days with <=3 distinct closes:", int((flat <= 3).sum()))

h("1b. VIX raw corruption vs repaired vix_1m")
v = raw["INDIAVIX"].copy()
vd = pd.read_parquet(S + "/vix_daily.parquet")
vdm = dict(zip(pd.to_datetime(vd["date"]).dt.date, vd["close"]))
v["ref"] = v.d.map(vdm)
for c in ["open", "high", "low", "close"]:
    bad = ((np.log(v[c] / v["ref"]).abs() > 0.5) & v["ref"].notna())
    print(f"  raw {c}: rows >50% off the day's daily close: {int(bad.sum())} of {len(v)}; days affected: {v.loc[bad,'d'].nunique()}; bad dates range: {v.loc[bad,'d'].min()} .. {v.loc[bad,'d'].max()}")
rep = L.vix_1m("2021-10-01", "2026-12-31")
rep["d"] = rep.timestamp.dt.date
rep["ref"] = rep.d.map(vdm)
for c in ["open", "high", "low", "close"]:
    bad = ((np.log(rep[c] / rep["ref"]).abs() > 0.5) & rep["ref"].notna())
    print(f"  repaired {c}: rows >50% off daily close: {int(bad.sum())} of {len(rep)}; max {rep[c].max():.2f} min {rep[c].min():.2f}")
print("  repaired vix_1m dates:", span(rep.d), " bars/day median", rep.groupby('d').size().median())
nr = rep.groupby('d').ref.first()
print("  days with no daily reference:", int(nr.isna().sum()), [str(x) for x in nr[nr.isna()].index[:10]])
print("  repaired 09:16 close non-null:", int(rep[rep.timestamp.dt.strftime('%H:%M') == '09:16'].close.notna().sum()))

h("1c. vix_daily.parquet and index_close_daily.parquet")
print("vix_daily:", span(vd["date"]), " rows", len(vd), " NaN-close dates:", vd[vd.close.isna()]["date"].tolist()[:10])
vdd = vd.dropna(subset=["close"])
print("   last non-null close date:", vdd["date"].iloc[-1], " close range:", vd.close.min(), vd.close.max())
icd = pd.read_parquet(S + "/index_close_daily.parquet")
print("index_close_daily: rows per index", icd["index"].value_counts().to_dict(), " dates", span(icd["date"]))
for k, g in icd.groupby("index"):
    print("   ", k, span(g["date"]), "NaN close", int(g.close.isna().sum()))

h("2. nse_index_closes.csv: key indices")
names = sorted(ic.index_name.unique())
print("all index names (", len(names), "):", names)
for k in ["Nifty 50", "Nifty Bank", "India VIX", "Nifty Next 50", "Nifty Midcap 100", "Nifty Smallcap 100", "Nifty IT", "Nifty Financial Services", "Nifty Auto", "Nifty FMCG", "Nifty Metal", "Nifty Pharma", "Nifty Realty", "Nifty Energy", "Nifty PSU Bank", "Nifty Private Bank", "Nifty Media", "Nifty Infrastructure", "Nifty Oil & Gas", "Nifty Healthcare Index", "Nifty Consumer Durables", "Nifty 500", "Nifty 100", "Nifty 200", "Nifty Midcap 50", "S&P BSE SENSEX", "SENSEX", "BSE SENSEX"]:
    g = ic[ic.index_name == k]
    if len(g):
        print(f"  {k}: {span(g['date'])}, non-numeric close:", int(pd.to_numeric(g.close, errors='coerce').isna().sum()))
    else:
        print(f"  {k}: ABSENT")
gaps(n50["date"], pd.bdate_range(n50["date"].min(), n50["date"].max()), "NIFTY50 file vs all weekdays (holidays expected)")
print("   NIFTY 50 close unchanged vs prior day:", int((n50.sort_values('date').close.astype(float).pct_change() == 0).sum()))
nm = set(pd.to_datetime(pd.Series(raw["NIFTY50"].d.unique())))
print("NSE-file sessions 2021-10-20..2026-10-28 not in minute spot:", sorted(str(d.date()) for d in SESS if pd.Timestamp('2021-10-20') <= d <= pd.Timestamp('2026-10-28') and d not in nm)[:20])

h("3. options_1m (NIFTY, SENSEX) file listing")
import random
for u in ["NIFTY", "SENSEX"]:
    exps = sorted(os.listdir(f"{S}/options_1m/{u}"))
    days = []
    allf = []
    for e in exps:
        for f in os.listdir(f"{S}/options_1m/{u}/{e}"):
            days.append(f.replace(".parquet", ""))
            allf.append((e, f))
    print(u, "expiry dirs", len(exps), exps[0], exps[-1], " contract-day files", len(days), " distinct trading dates", span(days))
    sdt = pd.to_datetime(pd.Series(sorted(set(days))))
    gaps(sdt, SESS, u + " option dates vs NSE sessions")
    random.seed(1)
    sample = random.sample(allf, min(60, len(allf)))
    tot = oi0 = vol0 = bad_px = 0
    srcs = {}
    for e, f in sample:
        d = pd.read_parquet(f"{S}/options_1m/{u}/{e}/{f}")
        tot += len(d)
        oi0 += int((d.oi == 0).sum())
        vol0 += int((d.volume == 0).sum())
        bad_px += int((d.close <= 0).sum())
        for k, c in d.source.value_counts().items():
            srcs[k] = srcs.get(k, 0) + int(c)
    print(f"   sample of {len(sample)} files: rows {tot}; oi==0 share {oi0/tot:.3f}; volume==0 (filler) share {vol0/tot:.3f}; close<=0 {bad_px}; sources {srcs}")
    e, f = allf[-1]
    d = pd.read_parquet(f"{S}/options_1m/{u}/{e}/{f}")
    print("   a late file", e, f, "time span", d.timestamp.min(), d.timestamp.max())
    ed = pd.Series(pd.to_datetime(exps))
    print("   expiry weekdays:", ed.dt.day_name().value_counts().to_dict(), " by year:", ed.dt.year.value_counts().sort_index().to_dict())
    ddays = pd.Series(pd.to_datetime(sorted(set(days))))
    print("   trading-date coverage by year:", ddays.dt.year.value_counts().sort_index().to_dict())

h("4. options_daily (NIFTY, BANKNIFTY bhavcopy-derived), futures?")
for u in ["NIFTY", "BANKNIFTY"]:
    fs = sorted(glob.glob(f"{S}/options_daily/{u}/*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    print(u, "files", len(fs), os.path.basename(fs[0]), os.path.basename(fs[-1]), " rows", len(df), " dates", span(df.TradDt))
    print("   FinInstrmTp counts:", df.FinInstrmTp.value_counts().to_dict())
    fut = df[df.FinInstrmTp == "IDF"]
    print("   futures rows", len(fut), " dates", span(fut.TradDt), " distinct expiries/day median", fut.groupby('TradDt').XpryDt.nunique().median())
    gaps(pd.to_datetime(pd.Series(df.TradDt.unique())), SESS, u + " daily vs NSE sessions")
    print("   futures OpnIntrst==0 share:", float((fut.OpnIntrst == 0).mean()), " options UndrlygPric non-null share:", float(df[df.FinInstrmTp != 'IDF'].UndrlygPric.notna().mean()))

h("5. chain_eod, nifty_1s, expiries, instruments")
cf = sorted(os.listdir(S + "/chain_eod"))
print("chain_eod", len(cf), cf[0], cf[-1])
c0 = pd.read_parquet(S + "/chain_eod/" + cf[-1])
print("   underlyings", c0.underlying.unique(), " rows", len(c0), " bid non-null share", float(c0.bid.notna().mean()))
nf = sorted(os.listdir(S + "/nifty_1s"))
print("nifty_1s", len(nf), nf[0], nf[-1])
n0 = pd.read_parquet(S + "/nifty_1s/" + nf[-1])
print("   kinds", n0.kind.value_counts().to_dict(), " time span", n0.timestamp.min(), n0.timestamp.max())
n1 = pd.read_parquet(S + "/nifty_1s/" + nf[0])
print("   first file", nf[0], "time span", n1.timestamp.min(), n1.timestamp.max(), "rows", len(n1))
ex = pd.read_parquet(S + "/expiries.parquet")
print("expiries.parquet:\n", ex.groupby('underlying').expiry_date.agg(['min', 'max', 'count']).to_string())

h("6. GIFT bhavcopy (new)")
g = pd.read_csv(X + "/gift_bhavcopy_futures.csv", low_memory=False)
g["trade_date"] = pd.to_datetime(g["trade_date"])
print("rows", len(g), "dates", span(g.trade_date))
g["und"] = g.contract.str.extract(r"^FUTIDX([A-Z0-9]+?)\d{2}-[A-Z]{3}-\d{4}$")[0]
print("underlyings:", g.und.value_counts().to_dict())
gn = g[g.und == "NIFTY"].copy()
gn["exp"] = pd.to_datetime(gn.contract.str.extract(r"(\d{2}-[A-Z]{3}-\d{4})$")[0], format="%d-%b-%Y")
gn = gn.sort_values(["trade_date", "exp"])
nmo = gn[gn.exp >= gn.trade_date].groupby("trade_date").head(1)
print("NIFTY contracts per day median", gn.groupby('trade_date').size().median(), " near-month days", len(nmo), "dates", span(nmo.trade_date))
print("  near-month open==0 days:", int((nmo.open == 0).sum()), " settlement null:", int(nmo.settlement.isna().sum()), " prev_settle null:", int(nmo.prev_settle.isna().sum()), " traded_qty==0 days:", int((nmo.traded_qty == 0).sum()))
print("  near-month tail:\n", nmo.tail(4)[["trade_date", "contract", "prev_settle", "open", "high", "low", "close", "settlement", "oi", "traded_qty"]].to_string())
nmo = nmo.set_index("trade_date")
ps = nmo.settlement.shift(1)
same = nmo.contract == nmo.contract.shift(1)
cmp = (nmo.prev_settle - ps)[same]
print("  prev_settle(t) vs settlement(t-1) same contract: n", len(cmp.dropna()), " mismatch>0.5pt", int((cmp.abs() > 0.5).sum()), " first", [str(x.date()) for x in cmp[cmp.abs() > 0.5].index[:8]])
gaps(nmo.index, SESS, "GIFT near-month vs NSE sessions")
nonsess = [d for d in nmo.index if d not in set(SESS)]
print("  GIFT dates that are NSE non-sessions:", len(nonsess), [str(d.date()) for d in nonsess[:10]])
jj = nmo.join(nc.rename("nifty_close"), how="inner")
jj["gap_vs_prev_cash"] = jj.open.replace(0, np.nan) / jj.nifty_close.shift(1) - 1
print("  GIFT open vs previous NSE close: median %.4f, p5 %.4f p95 %.4f; |x|>3%%: %d" % (jj.gap_vs_prev_cash.median(), jj.gap_vs_prev_cash.quantile(.05), jj.gap_vs_prev_cash.quantile(.95), int((jj.gap_vs_prev_cash.abs() > .03).sum())))
print("  GIFT |open/prev_settle-1|>3%:", int(((nmo.open.replace(0, np.nan) / nmo.prev_settle - 1).abs() > .03).sum()))
print("  GIFT high<low or open outside [low,high]:", int(((nmo.high < nmo.low) | (nmo.open > nmo.high) | (nmo.open < nmo.low)).sum()))
print("  near-month distinct contracts:", nmo.contract.nunique())
print("  near-month rows by year:", nmo.groupby(nmo.index.year).size().to_dict())

h("6b. older local GIFT files")
dsp = pd.read_csv(R + "/index_context_research/data/gift/gift_dsp_futures.csv", header=None)
dd = pd.to_datetime(dsp[0], format="%d-%b-%Y")
print("gift_dsp_futures.csv rows", len(dsp), "cols", dsp.shape[1], " NIFTY rows", int((dsp[2] == "NIFTY").sum()), " distinct days", dd.nunique(), span(dd))
oi = open(R + "/index_context_research/data/gift/gift_oi_futures.csv").read().splitlines()
days = [l for l in oi if l.startswith("#DAY")]
print("gift_oi_futures.csv #DAY headers", len(days), days[0], days[-1])
print("progress.txt tail:", open(R + "/index_context_research/data/gift/progress.txt").read()[-200:].replace("\n", " | "))

h("7. breadth (new)")
b = pd.read_csv(X + "/nse_breadth_daily.csv")
b["date"] = pd.to_datetime(b.date)
print("rows", len(b), "dates", span(b.date), " dup", int(b.date.duplicated().sum()))
gaps(b.date, SESS, "breadth vs NSE sessions")
print("  n_eq by year (median):", b.groupby(b.date.dt.year).n_eq.median().to_dict())
print("  n_eq range", b.n_eq.min(), b.n_eq.max(), " adv+dec+unch==n_eq all:", bool((b.advances + b.declines + b.unchanged == b.n_eq).all()))
b["adv_share"] = b.advances / (b.advances + b.declines)
print("  adv_share describe:", b.adv_share.describe().round(3).to_dict())
print("  n_eq jumps >20% day on day:", int((b.n_eq.pct_change().abs() > .2).sum()))
j = b.set_index("date").join(n50.set_index("date").change_pct.astype(float).rename("nr"), how="inner")
print("  corr adv_share vs NIFTY change_pct:", round(j.adv_share.corr(j.nr), 3))
print("  NaN counts:", b.isna().sum()[lambda s: s > 0].to_dict())

h("8. FII/DII cash (stockezee) + participant OI")
f = pd.read_csv(X + "/fii_dii_cash_stockezee.csv")
f["date"] = pd.to_datetime(f.date)
print("rows", len(f), "dates", span(f.date), " NaNs:", f.isna().sum()[lambda s: s > 0].to_dict())
gaps(f.date, SESS, "FII/DII cash vs NSE sessions")
sin = [d for d in SESS if d >= pd.Timestamp("2025-12-01")]
print("  NSE sessions 2025-12-01..2026-11-17:", len(sin), " in file:", len(set(f.date) & set(sin)))
print("  sessions with no FII row (excl. 2026-09):", [str(d.date()) for d in sin if d not in set(f.date) and not (d.year == 2026 and d.month == 9)])
print("  September 2026 sessions missing:", sum(1 for d in sin if d.year == 2026 and d.month == 9 and d not in set(f.date)))
print("  non-session dates in file:", [str(d.date()) for d in f.date if d not in set(SESS)])
print("  fii_cash_net describe:", f.fii_cash_net.describe().round(0).to_dict())
fj = f.set_index("date").join(nc.rename("nse_close"))
dif = (fj.nifty_close / fj.nse_close - 1).abs()
print("  stockezee nifty_close vs NSE: max %.3f%% >0.05%%: %d (NaN-compare rows %d)" % (dif.max() * 100, int((dif > .0005).sum()), int(dif.isna().sum())))
print("  duplicate dates", int(f.date.duplicated().sum()))
po = sorted(glob.glob(R + "/g1_research/data/external/participant_oi/*.csv"))
pdts = pd.to_datetime([os.path.basename(p)[:-4] for p in po])
print("participant_oi files", len(po), span(pdts))
gaps(pdts, SESS, "participant OI vs NSE sessions")


def read_po(p):
    d = pd.read_csv(p, skiprows=1)
    d.columns = [c.strip().strip('\t') for c in d.columns]
    return d


d0 = read_po(po[0])
d1 = read_po(po[-1])
print("  client types first/last:", d0.iloc[:, 0].tolist(), d1.iloc[:, 0].tolist(), " columns identical:", list(d0.columns) == list(d1.columns))
print("  header last:", open(po[-1]).readline().strip()[:120])
mism = []
ncols = {}
totbad = []
for p in po:
    first = open(p).readline()
    m = re.search(r"as on ([A-Za-z]{3}) (\d{1,2}),(\d{4})", first)
    dt = pd.to_datetime(f"{m.group(2)} {m.group(1)} {m.group(3)}") if m else None
    if dt is None or dt != pd.Timestamp(os.path.basename(p)[:-4]):
        mism.append((os.path.basename(p), first[:90]))
    try:
        d = read_po(p)
        ncols[d.shape[1]] = ncols.get(d.shape[1], 0) + 1
        if d.shape[0] != 5:
            totbad.append(os.path.basename(p))
    except Exception as e:
        totbad.append(os.path.basename(p) + ":" + str(e)[:40])
print("  'as on' date != filename:", len(mism), mism[:5], "; column counts:", ncols, "; files without 5 rows:", len(totbad), totbad[:5])
bad = 0
cnt = 0
for p in po[::10]:
    d = read_po(p)
    t = d[d.iloc[:, 0].str.upper() == "TOTAL"].iloc[0]
    cnt += 1
    bad += int(abs(float(t.iloc[1]) - float(t.iloc[2])) > 0)
print("  sample TOTAL index fut long!=short files:", bad, "of", cnt)

h("9. Yahoo daily/hourly")
Y = X + "/yahoo"
for fn in sorted(os.listdir(Y)):
    d = pd.read_csv(f"{Y}/{fn}")
    d["ts"] = pd.to_datetime(d.timestamp_utc)
    off = d.local_offset_s.value_counts().to_dict()
    hrs = d.ts.dt.strftime("%H:%M").value_counts().head(3).to_dict()
    nc_ = int(d.close.isna().sum())
    print(f"{fn}: rows {len(d)} {d.ts.min()} .. {d.ts.max()}; offsets {dict(list(off.items())[:3])}; common UTC times {hrs}; dup ts {int(d.ts.duplicated().sum())}; NaN close {nc_}; volume==0 share {float((d.volume==0).mean()):.2f}")
    if fn.endswith("_1d.csv"):
        ld = d.iloc[-1]
        print("     last row:", ld.ts, "close", ld.close, "vol", ld.volume, "| prev:", d.iloc[-2].ts, d.iloc[-2].close)
        if nc_ > 5:
            print("     NaN-close by year:", d[d.close.isna()].ts.dt.year.value_counts().sort_index().to_dict())
        print("     close unchanged vs prior:", int((d.close.diff() == 0).sum()), " |ret|>10%:", int((d.close.pct_change().abs() > .1).sum()))
d = pd.read_csv(Y + "/US10Y_1d.csv")
print("US10Y close describe:", d.close.describe().round(2).to_dict(), " rows close>20 or <0.01:", int(((d.close > 20) | (d.close < 0.01)).sum()))
print("   US10Y |ret|>20% dates:", d.loc[d.close.pct_change().abs() > .2, "timestamp_utc"].str[:10].tolist()[:12])
d = pd.read_csv(Y + "/WTI_1d.csv")
print("WTI min close:", d.close.min(), d.loc[d.close.idxmin(), "timestamp_utc"], " negative rows:", int((d.close < 0).sum()))
d = pd.read_csv(Y + "/BRENT_1d.csv")
r = d.close.pct_change().abs()
print("BRENT days |ret|>10%:", d.loc[r > .1, "timestamp_utc"].str[:10].tolist()[:20])
d = pd.read_csv(Y + "/DXY_1d.csv")
print("DXY NaN close by year:", pd.to_datetime(d[d.close.isna()].timestamp_utc).dt.year.value_counts().sort_index().to_dict(), " open NaN:", int(d.open.isna().sum()), " rows by year", pd.to_datetime(d.timestamp_utc).dt.year.value_counts().sort_index().to_dict())
d = pd.read_csv(Y + "/VIX_US_1d.csv")
print("VIX_US NaN close by year:", pd.to_datetime(d[d.close.isna()].timestamp_utc).dt.year.value_counts().sort_index().to_dict(), " |ret|>30%:", int((d.close.pct_change().abs() > .3).sum()))

h("9b. Yahoo day alignment vs Indian sessions")


def yd(fn):
    d = pd.read_csv(f"{Y}/{fn}")
    ts = pd.to_datetime(d.timestamp_utc) + pd.to_timedelta(d.local_offset_s, unit="s")
    d["local_date"] = ts.dt.normalize()
    d["local_time"] = ts.dt.strftime("%H:%M")
    return d


for fn in ["GSPC_1d.csv", "IXIC_1d.csv", "N225_1d.csv", "HSI_1d.csv", "DXY_1d.csv", "USDINR_1d.csv", "NSEI_1d.csv", "BRENT_1d.csv", "GOLD_1d.csv", "ES_F_1d.csv", "KOSPI_1d.csv", "ASX200_1d.csv", "SSEC_1d.csv", "TWII_1d.csv", "VIX_US_1d.csv", "US10Y_1d.csv", "WTI_1d.csv"]:
    d = yd(fn)
    print(f"  {fn}: local time-of-day of daily stamp {d.local_time.value_counts().head(2).to_dict()}; weekday counts {d.local_date.dt.dayofweek.value_counts().sort_index().to_dict()}")
n = yd("NSEI_1d.csv")
cmp = n.set_index("local_date").close.to_frame("yahoo").join(nc.rename("nse"), how="inner")
cmp["diff"] = (cmp.yahoo / cmp.nse - 1).abs()
print("  NSEI yahoo close vs NSE file: overlap", len(cmp), " >0.1% days:", int((cmp["diff"] > .001).sum()), " max", float(cmp["diff"].max()))
print("  NSEI yahoo dates not NSE sessions:", [str(x.date()) for x in n.local_date if x not in set(SESS)][:10], " NSE sessions missing in yahoo:", len([x for x in SESS if x not in set(n.local_date)]))
gs = yd("GSPC_1d.csv")
print("  GSPC last 3:\n", gs.tail(3)[["local_date", "local_time", "open", "close", "volume"]].to_string())
print("  GSPC dates all weekdays:", bool((gs.local_date.dt.dayofweek < 5).all()))
for fn in ["ES_F_60m.csv", "NQ_F_60m.csv", "USDINR_60m.csv"]:
    d = pd.read_csv(f"{Y}/{fn}")
    ist = pd.to_datetime(d.timestamp_utc) + pd.Timedelta(hours=5, minutes=30)
    mins = ist.dt.hour * 60 + ist.dt.minute
    per = ((mins >= 390) & (mins < 555)).groupby(ist.dt.date).sum()
    print(f"  {fn}: UTC hours seen {sorted(pd.to_datetime(d.timestamp_utc).dt.hour.unique().tolist())}; offsets {d.local_offset_s.value_counts().to_dict()}; close NaN share {float(d.close.isna().mean()):.3f}; volume==0 share {float((d.volume==0).mean()):.3f}; mean bars 06:30-09:15 IST per day {per.mean():.2f}; first/last IST {ist.min()} {ist.max()}")

h("10. data/parents (old Yahoo caches), GDELT, eod2, events")
for p in sorted(glob.glob(R + "/data/parents/*.csv")):
    d = pd.read_csv(p)
    print(" ", os.path.basename(p), d.shape, list(d.columns)[:4], d.iloc[0, 0], d.iloc[-1, 0])
for yr in range(2021, 2027):
    for k in ["tone", "volraw"]:
        fp = f"{R}/g1_research/data/external/gdelt/timeline{k}_{yr}.json"
        if os.path.exists(fp):
            j = json.load(open(fp))
            data = j["timeline"][0]["data"]
            ds = [x["date"][:8] for x in data]
            vals = [x["value"] for x in data]
            print(f"  gdelt {k} {yr}: query={j['query_details'].get('title')!r} n={len(ds)} {ds[0]}..{ds[-1]} null={sum(1 for v in vals if v is None)} series={j['timeline'][0]['series']}")
print("  gdelt files:", os.listdir(R + "/g1_research/data/external/gdelt"))
fs = glob.glob(R + "/data/eod2/*.csv")
d0 = pd.read_csv(fs[0])
print("eod2 files", len(fs), "cols", list(d0.columns)[:8], d0.iloc[0, 0], d0.iloc[-1, 0])
mx = []
mn = []
for p in fs[:: max(1, len(fs) // 60)]:
    dd_ = pd.read_csv(p, usecols=[0])
    mx.append(str(dd_.iloc[-1, 0]))
    mn.append(str(dd_.iloc[0, 0]))
print("  sample first dates:", pd.Series(mn).value_counts().head(4).to_dict(), " sample last dates:", pd.Series(mx).value_counts().head(4).to_dict())
sm = pd.read_csv(R + "/data/sector_map.csv")
print("sector_map", sm.shape, list(sm.columns))
import sqlite3
con = sqlite3.connect("file:" + R + "/data/events.sqlite?mode=ro", uri=True)
tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
print("events.sqlite tables:", tabs)
for t in tabs[:6]:
    print("  ", t, con.execute(f"select count(*) from {t}").fetchone(), [c[1] for c in con.execute(f"pragma table_info({t})")][:10])
con.close()
print("nse_holidays.json:", json.load(open(R + "/data/nse_holidays.json")).keys(), " years covered:", sorted({x[:4] for x in json.load(open(R + '/data/nse_holidays.json'))['holidays']}))

h("11. trade-set dates and join coverage")
t = pd.read_csv(R + "/g1_research/results/g1_live_replay_trades.csv")
print("G1 replay:", len(t), span(t.day), " g1f==1:", int((t.g1f == 1).sum()), span(t[t.g1f == 1].day))
c = pd.read_csv(R + "/g1_research/data/g1c_opt_trades.csv")
print("G1-C:", len(c), span(c.day), " B_1_net non-null", int(c.B_1_net.notna().sum()))
xp = pd.read_csv(R + "/g1_research/data/xp_history_minute.csv")
print("XP:", len(xp), span(xp.day), " hold_pct non-null", int(xp.hold_pct.notna().sum()))
cd = pd.read_csv(R + "/index_context_research/results/context_dataset.csv")
print("context_dataset:", len(cd), cd.tset.value_counts().to_dict(), span(cd.day))
print("  context_dataset NaN counts:", cd.isna().sum()[lambda s: s > 0].to_dict())
pset = set(pdts)
fset = set(f.date)
for nm_, dts in [("G1F", t[t.g1f == 1].day), ("G1", t.day), ("G1C", c.day), ("XP", xp.day)]:
    dts = pd.to_datetime(dts)
    prevs = [SESS[SESS.searchsorted(d) - 1] for d in dts if SESS.searchsorted(d) > 0]
    print(f"  {nm_}: n={len(dts)}; GIFT row on trade date {int(dts.isin(set(nmo.index)).sum())}; breadth row on trade date {int(dts.isin(set(b.date)).sum())}; breadth prev-session {sum(1 for p in prevs if p in set(b.date))}; participant OI prev-session {sum(1 for p in prevs if p in pset)}; FII cash prev-session {sum(1 for p in prevs if p in fset)}; trades >= 2025-12-01: {int((dts >= '2025-12-01').sum())}; trades with prev-session in Sept 2026: {sum(1 for p in prevs if p.year==2026 and p.month==9)}")
    print("     trade dates vs NIFTY minute spot sessions: missing", int((~dts.isin(nm)).sum()), "; vs VIX repaired:", int((~dts.isin(set(pd.to_datetime(rep.d.unique())))).sum()))
