"""Agent 1 data inventory: read-only descriptive checks. Run from the repo root:
  C:/Users/sherw/.venvs/fo/Scripts/python.exe -W ignore index_context_research/regime_investigation/interim/agent1_data_inventory/inventory_checks.py
Writes only checks_output.txt and hashes.txt next to this script. No network, no downloads, nothing modified elsewhere."""
import sys, os, glob, json, hashlib, io, re
from pathlib import Path
import numpy as np, pandas as pd

REPO = Path("C:/Users/sherw/project-f-0")
S = Path("C:/Users/sherw/fo-index-data/data/index")
OUT = REPO / "index_context_research/regime_investigation/interim/agent1_data_inventory"
sys.path.insert(0, str(REPO))
os.environ.setdefault("INDEX_STORE", str(S))
buf = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")
hashes = {}
def H(p):
    p = Path(p); h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    hashes[str(p).replace("\\", "/")] = h.hexdigest()[:16]

def span(dates):
    d = pd.to_datetime(pd.Series(sorted(set(dates))))
    return d.min().date(), d.max().date(), len(d)

def gaps(dates, cal, label, show=15):
    """session days of calendar `cal` (set of date) inside [min,max] of dates that are absent from dates"""
    ds = set(pd.to_datetime(list(dates)).date)
    lo, hi = min(ds), max(ds)
    miss = sorted(d for d in cal if lo <= d <= hi and d not in ds)
    P(f"  [{label}] missing vs NIFTY session calendar inside range: {len(miss)}", [str(x) for x in miss[:show]])
    return miss

# ---------------- NIFTY / BANK / SENSEX / VIX spot minutes ----------------
P("=== SPOT 1m ===")
cal = None
spot = {}
for name in ["NIFTY50", "NIFTYBANK", "SENSEX", "INDIAVIX"]:
    files = sorted(glob.glob(str(S / "spot_1m" / name / "*.parquet")))
    for f in files: H(f) if name == "NIFTY50" and f.endswith(("2021-10.parquet", "2026-10.parquet")) else None
    fr = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    fr["d"] = fr.timestamp.dt.date
    g = fr.groupby("d").size()
    P(name, "files", len(files), "rows", len(fr), "first", g.index.min(), "last", g.index.max(), "days", len(g))
    P("  minutes/day: min", g.min(), "median", g.median(), "max", g.max(), " days with <370 min:", int((g < 370).sum()),
      list(map(str, g[g < 370].index[:12])))
    P("  dup timestamps:", int(fr.timestamp.duplicated().sum()), " NaN close:", int(fr.close.isna().sum()),
      " source counts:", fr.source.value_counts().to_dict())
    fr = fr.sort_values("timestamp")
    r = fr.close.pct_change().abs()
    same_day = fr.d == fr.d.shift()
    big = fr[(r > (0.02 if name != "INDIAVIX" else 0.25)) & same_day]
    P("  1-min |ret| > ", 0.02 if name != "INDIAVIX" else 0.25, "count:", len(big))
    if name == "INDIAVIX":
        P("  RAW VIX: close<5:", int((fr.close < 5).sum()), " close>100:", int((fr.close > 100).sum()), " high>100:", int((fr.high > 100).sum()),
          " months affected(high>100):", sorted(set(fr[fr.high > 100].timestamp.dt.strftime('%Y-%m')))[:40])
    spot[name] = fr
    if name == "NIFTY50":
        cal = set(g.index)
        # daily from minute
        spot["nifty_daily"] = fr.groupby("d").agg(open=("open", "first"), close=("close", "last"), high=("high", "max"), low=("low", "min"))
    first = fr.groupby("d").timestamp.min().dt.time
    P("  first-minute of day: most common", first.value_counts().head(3).to_dict())
for name in ["NIFTYBANK", "SENSEX", "INDIAVIX"]:
    ds = set(spot[name].d)
    P(f"  {name}: dates not in NIFTY50 {len(ds - cal)}, NIFTY50 dates not in {name} {len(cal - ds)}")

# repaired VIX
from index_data.load import vix_1m
v = vix_1m("2021-10-20", "2026-10-30")
P("REPAIRED VIX via vix_1m:", v.shape, list(v.columns))
vc = v["close"] if "close" in v else v.iloc[:, 0]
P("  min", float(vc.min()), "max", float(vc.max()), "NaN", int(vc.isna().sum()))
ts = v.timestamp if "timestamp" in v else v.index.to_series()
P("  days", ts.dt.date.nunique(), "first", ts.min(), "last", ts.max())
rv = vc.pct_change().abs(); P("  1-min |ret| > 0.25:", int((rv > 0.25).sum()))

# daily files
vd = pd.read_parquet(S / "vix_daily.parquet"); H(S / "vix_daily.parquet")
P("vix_daily", vd.shape, vd.date.min(), vd.date.max(), "NaN close:", int(vd.close.isna().sum()), vd[vd.close.isna()].date.tolist()[:10],
  "min", vd.close.min(), "max", vd.close.max())
vd["date"] = pd.to_datetime(vd.date)
sub = vd[(vd.date >= "2021-10-20")]
g = gaps(sub.date.dt.date, cal, "vix_daily")
# compare repaired minute-VIX last close to vix_daily close
vv = v.copy(); vv["d"] = ts.dt.date.values
lastc = vv.groupby("d").apply(lambda x: x.sort_values(x.columns[0] if "timestamp" in x else x.index.name).iloc[-1]["close"]) if False else None
ic = pd.read_parquet(S / "index_close_daily.parquet"); H(S / "index_close_daily.parquet")
P("index_close_daily", ic.shape, ic["index"].value_counts().to_dict(), ic.date.min(), ic.date.max())
for ix, gg in ic.groupby("index"):
    P("  ", ix, gg.date.min(), gg.date.max(), len(gg), "NaN close", int(gg.close.isna().sum()))
nd = ic[ic["index"] == "NIFTY50"].copy(); nd["date"] = pd.to_datetime(nd.date)
nd["ret"] = nd.close.pct_change()
P("  NIFTY daily |ret|>6%:", nd[nd.ret.abs() > 0.06][["date", "close", "ret"]].values.tolist()[:10])
dmin = spot["nifty_daily"]
pass
m = nd.set_index(nd.date.dt.date).close.reindex(dmin.index).dropna()
P("  NIFTY daily-file vs minute-derived close, overlap days", len(m), "max abs diff pct", float(((m - dmin.close.reindex(m.index)).abs() / m).max()) if len(m) else None)
P("  NIFTY daily from 2018-01 to 2021-10 (pre-minute) days:", int((nd.date < "2021-10-20").sum()))
# calendar from daily file, to flag gaps
dcal = set(nd.date.dt.date)

# ---------------- Expiries ----------------
P("=== EXPIRIES ===")
ex = pd.read_parquet(S / "expiries.parquet"); H(S / "expiries.parquet")
P(ex.shape, list(ex.columns)); P(ex.groupby("underlying").expiry_date.agg(["min", "max", "count"]))
od = {}
for u in ["NIFTY", "BANKNIFTY"]:
    files = sorted(glob.glob(str(S / "options_daily" / u / "*.parquet")))
    H(files[0]); H(files[-1])
    fr = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    od[u] = fr
    days = pd.to_datetime(fr.TradDt).dt.date
    P(f"options_daily/{u}: files {len(files)} rows {len(fr)} first {days.min()} last {days.max()} days {days.nunique()}",
      "types", fr.FinInstrmTp.value_counts().to_dict())
    fut = fr[fr.FinInstrmTp.isin(["IDF"])]
    fd = pd.to_datetime(fut.TradDt).dt.date
    P("   futures rows", len(fut), "days", fd.nunique(), "first", fd.min() if len(fut) else None, "OI NaN", int(fut.OpnIntrst.isna().sum()),
      "OI==0 share", float((fut.OpnIntrst == 0).mean()) if len(fut) else None)
    # missing days vs daily-file calendar since 2018
    g = gaps(days.unique(), dcal, f"options_daily {u}")

# ---------------- options_1m ----------------
P("=== options_1m ===")
for u in ["NIFTY", "SENSEX"]:
    dirs = sorted(os.listdir(S / "options_1m" / u))
    days = set()
    nfile = 0
    for d in dirs:
        for f in os.listdir(S / "options_1m" / u / d):
            days.add(f[:10]); nfile += 1
    P(u, "expiry dirs", len(dirs), dirs[0], dirs[-1], "trade-day files", nfile, "distinct trade days", len(days), min(days), max(days))
    g = gaps(pd.to_datetime(sorted(days)).date, cal, f"options_1m {u}")
# one sample for OI completeness
sm = sorted(glob.glob(str(S / "options_1m/NIFTY/*/*.parquet")))
H(sm[0]); H(sm[-1])
t = pd.concat([pd.read_parquet(f) for f in sm[::40]])
P("  sample every 40th file:", len(sm[::40]), "rows", len(t), "oi==0 share", float((t.oi == 0).mean()), "sources", t.source.value_counts().to_dict())
P("  per-contract-day first minute (time) median examples:", t.groupby(t.timestamp.dt.date).timestamp.min().dt.time.value_counts().head(3).to_dict())

# chain / 1s / instruments
for sub in ["chain_eod", "nifty_1s", "instruments"]:
    fs = sorted(os.listdir(S / sub)); P(sub, len(fs), fs[0], fs[-1])

# ---------------- GIFT ----------------
P("=== GIFT ===")
gd = REPO / "index_context_research/data/gift"
for f in ["gift_dsp_futures.csv", "gift_oi_futures.csv", "progress.txt"]: H(gd / f)
P("progress.txt:", (gd / "progress.txt").read_text()[:400].replace("\n", " | "))
df = pd.read_csv(gd / "gift_dsp_futures.csv", header=None)
P("dsp cols", df.shape, df.head(2).values.tolist(), "symbols", sorted(df[2].unique())[:20])
df["d"] = pd.to_datetime(df[0], format="%d-%b-%Y")
gn = df[(df[2] == "NIFTY")]
P("NIFTY rows", len(gn), "days", gn.d.nunique(), gn.d.min().date(), gn.d.max().date(), "weekdays in range",
  len(pd.bdate_range(gn.d.min(), gn.d.max())))
nd2 = set(gn.d.dt.date)
g = gaps(nd2 and [*nd2], dcal | cal, "GIFT NIFTY vs Indian sessions", show=8)
P("  GIFT NIFTY days on which NIFTY has a session:", len(nd2 & (cal | dcal)), "; GIFT days that are not Indian sessions:", len(nd2 - (cal | dcal)))
P("  NIFTY rows per day: ", gn.groupby("d").size().value_counts().to_dict())
oi = open(gd / "gift_oi_futures.csv").read().splitlines()
P("oi file: lines", len(oi), "'#DAY' header lines", sum(l.startswith("#DAY") for l in oi), oi[0], oi[1])

# ---------------- participant OI ----------------
P("=== participant_oi ===")
pf = sorted(glob.glob(str(REPO / "g1_research/data/external/participant_oi/*.csv")))
H(pf[0]); H(pf[-1])
rows = []; bad = []
for f in pf:
    d = os.path.basename(f)[:-4]
    try:
        t = pd.read_csv(f, skiprows=1); t.columns = [c.strip() for c in t.columns]
        t["Client Type"] = t["Client Type"].astype(str).str.strip()
        t = t[t["Client Type"].isin(["Client", "DII", "FII", "Pro"])]
        if len(t) != 4: bad.append((d, "rows", len(t)))
        num = t.drop(columns=["Client Type"]).apply(pd.to_numeric, errors="coerce")
        if num.isna().any().any(): bad.append((d, "nonnumeric"))
        if (num.fillna(0).sum(axis=1) == 0).any(): bad.append((d, "zero row"))
        t["d"] = d; rows.append(t)
    except Exception as e:
        bad.append((d, str(e)[:60]))
po = pd.concat(rows); po["d"] = pd.to_datetime(po.d)
P("files", len(pf), "first", pf[0][-14:-4], "last", pf[-1][-14:-4], "parsed days", po.d.nunique(), "bad:", bad[:10], len(bad))
P("columns:", list(po.columns))
dd = sorted(po.d.dt.date.unique())
miss = [d for d in sorted(cal) if dd[0] <= d <= dd[-1] and d not in set(dd)]
extra = [d for d in dd if d not in cal and d <= max(cal)]
P("  participant days missing vs NIFTY minute calendar (from 2021-10-20):", len([m for m in miss if m >= pd.Timestamp('2021-10-20').date()]), [str(x) for x in miss[:15]])
P("  participant dates that are not NIFTY minute-calendar days (<=2026-10-28):", len(extra), [str(x) for x in extra[:10]])
fii = po[po["Client Type"] == "FII"].set_index("d")
P("  FII index fut long share: min/max", float((fii["Future Index Long"] / (fii["Future Index Long"] + fii["Future Index Short"])).min()),
  float((fii["Future Index Long"] / (fii["Future Index Long"] + fii["Future Index Short"])).max()))
P("  FII option Index Call Long dtype ok; first/last rows:", fii.iloc[0][["Option Index Call Long", "Option Index Put Long"]].to_dict(), fii.iloc[-1][["Option Index Call Long"]].to_dict())
P("  day-over-day jumps (FII Future Index Long |chg|>60%):", int((fii["Future Index Long"].pct_change().abs() > 0.6).sum()))
P("  no volume / turnover / net-buy-sell cash columns; contracts = open interest, end of day")

# ---------------- global daily (yahoo) ----------------
P("=== data/parents ===")
for f in sorted(glob.glob(str(REPO / "data/parents/*.csv"))):
    H(f)
    t = pd.read_csv(f)
    c0 = t.columns[0]
    t[c0] = pd.to_datetime(t[c0], errors="coerce")
    P(os.path.basename(f), "rows", len(t), t[c0].min(), t[c0].max(), "dup", int(t[c0].duplicated().sum()), "NaN close", int(t.Close.isna().sum()),
      "bad dates", int(t[c0].isna().sum()))
    if "1h" not in f:
        t = t.set_index(c0); r = t.Close.pct_change().abs()
        P("   |daily ret|>8%:", int((r > 0.08).sum()), "zero-volume days", int((t.Volume == 0).sum()) if "Volume" in t else None,
          " gaps>5 calendar days:", int((t.index.to_series().diff().dt.days > 5).sum()))
        P("   days since 2021-10-20:", int((t.index >= "2021-10-20").sum()), "Indian sessions without a row:",
          len([d for d in cal if pd.Timestamp(d) not in t.index]))
# Brent daily vs hourly
b = pd.read_csv(REPO / "data/parents/yf_BZ_F.csv", parse_dates=["Date"]).set_index("Date")
bh = pd.read_csv(REPO / "data/parents/yf_BZ_F_1h.csv", parse_dates=["Datetime_ET"])
bh["day"] = bh.Datetime_ET.dt.normalize()
hc = bh.groupby("day").Close.last()
j = pd.concat([b.Close.rename("daily"), hc.rename("hourly_last")], axis=1).dropna()
j["diff%"] = (j.hourly_last / j.daily - 1) * 100
P("Brent daily vs last hourly of the same ET date: overlap", len(j), j.index.min().date() if len(j) else None, j.index.max().date() if len(j) else None,
  " |diff|>2%:", int((j["diff%"].abs() > 2).sum()), " >4%:", int((j["diff%"].abs() > 4).sum()), " median |diff| %", float(j["diff%"].abs().median()))
P("Hourly Brent range:", bh.Datetime_ET.min(), bh.Datetime_ET.max(), "(timestamps are US Eastern, not UTC/IST)")

# ---------------- GDELT ----------------
P("=== GDELT ===")
gdf = []
for f in sorted(glob.glob(str(REPO / "g1_research/data/external/gdelt/*.json"))):
    H(f)
    j = json.load(open(f))
    q = j["query_details"]["title"]
    for s in j["timeline"]:
        t = pd.DataFrame(s["data"]); t["series"] = s["series"]; t["file"] = os.path.basename(f); t["query"] = q; gdf.append(t)
gd2 = pd.concat(gdf); gd2["d"] = pd.to_datetime(gd2.date.str[:8])
P("queries:", gd2["query"].unique().tolist(), "series:", gd2.series.unique().tolist())
for (s, f), g in gd2.groupby(["series", "file"]):
    P(f"  {f} {s}: rows {len(g)} {g.d.min().date()}..{g.d.max().date()} NaN {int(g.value.isna().sum())} zero {int((g.value == 0).sum())}")
tone = gd2[gd2.series == "Average Tone"].drop_duplicates("d").set_index("d")
alld = pd.date_range(tone.index.min(), tone.index.max())
P("tone: days", len(tone), "calendar days in range", len(alld), "missing", len(alld.difference(tone.index)), "min/max", tone.value.min(), tone.value.max())
P("tone coverage on Indian sessions (>=2021-10-20):", sum(pd.Timestamp(d) in tone.index for d in cal), "of", len(cal))

# ---------------- eod2, sectors, universe, events ----------------
P("=== eod2 / sectors ===")
ef = sorted(glob.glob(str(REPO / "data/eod2/*.csv")))
t = pd.read_csv(ef[0]); P("eod2 files", len(ef), "columns", list(t.columns), "example", os.path.basename(ef[0]), t.iloc[0, 0], t.iloc[-1, 0], len(t))
first, last, cnt = [], [], []
for f in ef:
    x = pd.read_csv(f, usecols=[0]); first.append(x.iloc[0, 0]); last.append(x.iloc[-1, 0]); cnt.append(len(x))
P("  first dates min/median/max", min(first), sorted(first)[len(first)//2], max(first), " last dates min/max", min(last), max(last), " rows min/median/max", min(cnt), int(np.median(cnt)), max(cnt))
H(ef[0])
sm_ = pd.read_csv(REPO / "data/sector_map.csv"); H(REPO / "data/sector_map.csv")
P("sector_map rows", len(sm_), sm_.sector_index.value_counts().to_dict())
fu = open(REPO / "data/fo_universe.txt").read().split(); H(REPO / "data/fo_universe.txt")
P("fo_universe symbols", len(fu), "(single list, no dates)")
nif = [f for f in os.listdir(REPO / "data") if "nifty" in f.lower() or "const" in f.lower()]
P("data/ files named nifty*/const*:", nif)
hits = [p for p in glob.glob(str(REPO / "**/*"), recursive=True)
        if re.search(r"(constituent|weight|nifty50_list|nifty_50)", os.path.basename(p), re.I) and "worktrees" not in p and ".venv" not in p][:20]
P("repo files with constituent/weight in name:", hits)

with open(OUT / "checks_output.txt", "w", encoding="utf-8") as f: f.write(buf.getvalue())
with open(OUT / "hashes.txt", "w", encoding="utf-8") as f:
    f.write("# sha256 first 16 hex chars; month/expiry/day-file samples = first and last of the series\n")
    for k, v_ in sorted(hashes.items()): f.write(f"{v_}  {k}\n")
