"""Agent 1, second batch of read-only checks. Output: checks_output2.txt (also printed)."""
import sys, os, glob, io, hashlib
from pathlib import Path
import numpy as np, pandas as pd
REPO = Path("C:/Users/sherw/project-f-0"); S = Path("C:/Users/sherw/fo-index-data/data/index")
OUT = REPO / "index_context_research/regime_investigation/interim/agent1_data_inventory"
sys.path.insert(0, str(REPO)); os.environ.setdefault("INDEX_STORE", str(S))
buf = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")
def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()[:16]
from index_data.load import vix_1m
# --- VIX
v = vix_1m("2021-10-20", "2026-10-30"); v["d"] = v.timestamp.dt.date
rep_last = v.sort_values("timestamp").groupby("d").close.last()
vd = pd.read_parquet(S / "vix_daily.parquet"); vd["d"] = pd.to_datetime(vd.date).dt.date; vdc = vd.set_index("d").close
j = pd.concat([rep_last.rename("rep"), vdc.rename("daily")], axis=1).dropna()
j["pct"] = (j.rep / j.daily - 1) * 100
P("VIX repaired last-minute close vs vix_daily close: n", len(j), "median |diff|%", round(j.pct.abs().median(), 3), "max |diff|%", round(j.pct.abs().max(), 2),
  "days >3%:", int((j.pct.abs() > 3).sum()), j[j.pct.abs() > 3].index.astype(str).tolist()[:10])
P("repaired minute VIX: days", v.d.nunique(), "min/max close", v.close.min(), v.close.max(), "high>40:", int((v.high > 40).sum()), "low<8:", int((v.low < 8).sum()))
raw = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(S / "spot_1m/INDIAVIX/*.parquet")))])
raw["d"] = raw.timestamp.dt.date
bad = (raw.close < 5) | (raw.close > 60)
P("RAW vs repaired: raw rows", len(raw), "rows with close <5 or >60:", int(bad.sum()), "high>60:", int((raw.high > 60).sum()),
  "last raw bad timestamp:", raw[bad].timestamp.max())
m = raw.merge(v[["timestamp", "close"]], on="timestamp", suffixes=("_raw", "_rep"))
dif = (m.close_raw / m.close_rep - 1).abs() > 0.01
P("rows where raw close differs from repaired by >1%:", int(dif.sum()), "of", len(m), "; first/last:", m[dif].timestamp.min(), m[dif].timestamp.max())
iv = pd.read_parquet(REPO / "index_research/data/spot_INDIAVIX.parquet")
P("index_research/data/spot_INDIAVIX.parquet:", iv.shape, "min/max close", iv.close.min(), iv.close.max(), "high>60", int((iv.high > 60).sum()),
  "(a second copy; sha", sha(REPO / "index_research/data/spot_INDIAVIX.parquet"), ")")
# --- daily-vs-minute NIFTY
ic = pd.read_parquet(S / "index_close_daily.parquet"); n = ic[ic["index"] == "NIFTY50"].copy(); n["d"] = pd.to_datetime(n.date).dt.date
sp = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(S / "spot_1m/NIFTY50/*.parquet")))]); sp["d"] = sp.timestamp.dt.date
mc = sp.sort_values("timestamp").groupby("d").close.last()
x = pd.concat([n.set_index("d").close.rename("daily"), mc.rename("min")], axis=1).dropna(); x["p"] = (x["min"] / x.daily - 1) * 100
P("NIFTY daily-file close vs last minute close: n", len(x), ">0.1%:", int((x.p.abs() > 0.1).sum()), ">0.3%:", int((x.p.abs() > 0.3).sum()), x[x.p.abs() > 0.3].index.astype(str).tolist()[:8])
lt = sp.groupby("d").timestamp.max().dt.time.value_counts().head(3).to_dict(); P("last minute of day:", lt)
cnt = sp.groupby("d").size(); P("NIFTY days with <376 minutes:", int((cnt < 376).sum()), {str(k): int(c) for k, c in cnt[cnt < 376].items()})
od = pd.concat([pd.read_parquet(f, columns=["TradDt"]) for f in sorted(glob.glob(str(S / "options_daily/NIFTY/*.parquet")))])
odd = set(pd.to_datetime(od.TradDt).dt.date)
dd = set(n.d)
P("daily-file days", len(dd), "options_daily days in same range", len([d for d in odd if min(dd) <= d <= max(dd)]), "in options_daily not daily-file:", len([d for d in odd if min(dd) <= d <= max(dd) and d not in dd]),
  "in daily-file not options_daily:", len(dd - odd))
P("options_daily trading days after 2025-09-30 (daily file ends there):", len([d for d in odd if d > pd.Timestamp('2025-09-30').date()]))
# --- participant OI anomalies
f = REPO / "g1_research/data/external/participant_oi/2024-02-22.csv"; P("participant 2024-02-22 raw:"); P(open(f).read()[:900])
rows = []
for fp in sorted(glob.glob(str(REPO / "g1_research/data/external/participant_oi/*.csv"))):
    t = pd.read_csv(fp, skiprows=1); t.columns = [c.strip() for c in t.columns]; t["Client Type"] = t["Client Type"].astype(str).str.strip()
    t = t[t["Client Type"].isin(["Client", "DII", "FII", "Pro"])].copy(); t["d"] = os.path.basename(fp)[:-4]; rows.append(t)
po = pd.concat(rows); po["d"] = pd.to_datetime(po.d)
P("participant days whose table has !=4 participant rows:", int((po.groupby("d").size() != 4).sum()))
fii = po[po["Client Type"] == "FII"].set_index("d")
ch = fii["Future Index Long"].pct_change().abs(); P("FII FutIdxLong |1d chg|>60% dates:", ch[ch > 0.6].index.strftime("%Y-%m-%d").tolist())
g = po.groupby("d")[["Future Index Long", "Future Index Short"]].sum(); bal = (g["Future Index Long"] / g["Future Index Short"] - 1).abs()
P("index futures total long vs total short (should balance): max rel gap", float(bal.max()), "days >1%:", int((bal > 0.01).sum()), bal[bal > 0.01].index.strftime("%Y-%m-%d").tolist()[:8])
dates = sorted(po.d.dt.date.unique())
P("participant days vs options_daily calendar:", "in cal not participant:", [str(d) for d in sorted(odd) if d >= dates[0] and d <= dates[-1] and d not in set(dates)][:12],
  " in participant not cal:", [str(d) for d in dates if d not in odd][:12])
# --- eod2 heavyweights
names = ["hdfcbank", "reliance", "icicibank", "infy", "tcs", "itc", "lt", "bhartiartl", "sbin", "axisbank", "kotakbank", "hindunilvr", "m&m", "bajfinance", "maruti"]
have = {nm: os.path.exists(REPO / "data/eod2" / f"{nm}.csv") for nm in names}; P("eod2 heavyweights present:", have)
t = pd.read_csv(REPO / "data/eod2/reliance.csv"); P("reliance.csv", t.Date.iloc[0], t.Date.iloc[-1], len(t), "Series values", t.Series.unique()[:5], "DLV_QTY NaN share", float(t.DLV_QTY.isna().mean()))
t2 = pd.read_csv(REPO / "data/eod2/hdfcbank.csv"); P("hdfcbank.csv", t2.Date.iloc[0], t2.Date.iloc[-1], len(t2))
bf = sorted(glob.glob(str(REPO / "data/cache/fo_bhavcopy_*.csv"))); P("stock fo_bhavcopy files", len(bf), bf[0][-12:-4], bf[-1][-12:-4])
t = pd.read_csv(bf[-1], nrows=3); P("bhavcopy columns", list(t.columns)[:16])
for sub in ["data/cache/intraday", "data/cache/index", "data/forward", "data/s2", "data/live_snapshots", "data/candles_1s"]:
    p = REPO / sub
    if p.exists():
        fs = os.listdir(p); P(sub, len(fs), fs[:3])
gs = pd.read_csv(REPO / "data/parents/yf_GSPC.csv", parse_dates=["Date"]).set_index("Date")
P("GSPC weekday counts", gs.index.dayofweek.value_counts().sort_index().to_dict(), "Open==Close days", int((gs.Open == gs.Close).sum()))
us = pd.read_csv(REPO / "data/parents/yf_USDINR_X.csv", parse_dates=["Date"]).set_index("Date"); P("USDINR close min/max", us.Close.min(), us.Close.max(), "|ret|>2%:", int((us.Close.pct_change().abs() > 0.02).sum()))
for nm in ["HG_F", "ALI_F", "TIO_F"]:
    t = pd.read_csv(REPO / f"data/parents/yf_{nm}.csv", parse_dates=["Date"]).set_index("Date"); P(nm, "close min/max", t.Close.min(), t.Close.max(), "zero-volume share", float((t.Volume == 0).mean()))
t = pd.read_csv(REPO / "data/parents/yf_BZ_F.csv", parse_dates=["Date"]).set_index("Date"); P("BZ=F negative/zero close:", int((t.Close <= 0).sum()), "min", t.Close.min())
open(OUT / "checks_output2.txt", "w", encoding="utf-8").write(buf.getvalue())
