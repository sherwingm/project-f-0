"""Agent 4 (v2): PRE-ENTRY institutional / global / breadth / news features for every trade, using the FIXED Amendment-1 definitions.
Read-only inputs, no network. Outputs (this folder): external_features.csv, external_level_cuts.csv, data_checks.txt.
Run: python -W ignore build_features.py
"""
import glob, json, os, re
from datetime import date, timedelta
import numpy as np
import pandas as pd

REPO = "C:/Users/sherw/project-f-0"
RI = REPO + "/index_context_research/regime_investigation"
OUT = RI + "/interim/agent4_external"
EXT = RI + "/external_data"
OI_DIR = REPO + "/g1_research/data/external/participant_oi"
GD_DIR = REPO + "/g1_research/data/external/gdelt"
DS = REPO + "/index_context_research/results/context_dataset.csv"
PAR = REPO + "/data/parents"
log = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s); log.append(s)

# ------------------------------------------------------------ trades
ds = pd.read_csv(DS); ds["day"] = pd.to_datetime(ds["day"])
ds = ds[["tset", "day", "entry", "net_pct", "net_rs", "maxup", "half", "dte", "us_prev_ret"]].copy()
say("trades", ds.groupby("tset").size().to_dict(), "last day", ds.day.max().date())

# ------------------------------------------------------------ NSE index closes -> session calendar, bank vs nifty
ix = pd.read_csv(EXT + "/nse_index_closes.csv", usecols=["date", "index_name", "close", "change_pct"], parse_dates=["date"])
nif = ix[ix.index_name == "Nifty 50"].set_index("date")["close"].sort_index()
bank = ix[ix.index_name == "Nifty Bank"].set_index("date")["close"].sort_index()
SES = list(nif.index); SESARR = np.array(SES, dtype="datetime64[ns]"); SESSET = set(SES)
say("session calendar (Nifty 50 rows in nse_index_closes):", len(SES), SES[0].date(), SES[-1].date(),
    "weekend special sessions since 2024-10:", [str(d.date()) for d in SES if d.weekday() >= 5 and d >= pd.Timestamp("2024-10-01")])
chk = ix[ix.index_name == "Nifty 50"].set_index("date").sort_index()
chk["mine"] = chk["close"].pct_change() * 100
chk["change_pct"] = pd.to_numeric(chk["change_pct"], errors="coerce")
say("Nifty 50 change_pct vs close-to-close (max abs diff, pts):", round(float((chk["mine"] - chk["change_pct"]).abs().max()), 3))
nret = nif.pct_change() * 100; bret = bank.pct_change() * 100
BUDGET_SPECIAL = [pd.Timestamp(2025, 2, 1), pd.Timestamp(2026, 2, 1)]   # absent from nse_index_closes, present as real sessions
SESX = sorted(SESSET | set(BUDGET_SPECIAL)); SESXARR = np.array(SESX, dtype="datetime64[ns]")
def prev_session(T, k=1):
    """previous trading session on the calendar INCLUDING the two Budget weekend sessions (their data are then missing = missing)."""
    i = np.searchsorted(SESXARR, np.datetime64(T), side="left")
    return SESX[i - k] if i - k >= 0 else None
miss_cal = [(str(pd.Timestamp(T).date()), sorted(ds[ds.day == T].tset.unique())) for T in ds.day.unique() if pd.Timestamp(T) not in SESSET]
say("trade dates not in the session calendar:", miss_cal)

# ------------------------------------------------------------ Yahoo daily series: local date per file
def load_y(name, kind):
    d = pd.read_csv(f"{EXT}/yahoo/{name}.csv")
    ts = pd.to_datetime(d["timestamp_utc"])
    if kind == "local":      # Asian indices: local exchange date = UTC timestamp + exchange offset
        d["date"] = (ts + pd.to_timedelta(d["local_offset_s"], unit="s")).dt.normalize()
    elif kind == "fx":       # FX daily bars start 23:00 or 00:00 UTC (London midnight): +1h gives the bar's date
        d["date"] = (ts + pd.Timedelta(hours=1)).dt.normalize()
    else:                    # US series: UTC date of the stamp equals the US session / futures-day date
        d["date"] = ts.dt.normalize()
    d = d.drop_duplicates("date", keep="last").set_index("date").sort_index()
    return d
_dx = load_y("DXY_1d", "us"); _nwk = int((_dx.index.weekday >= 5).sum()); _dx = _dx[_dx.index.weekday < 5]
Y = {"N225": load_y("N225_1d", "local"), "HSI": load_y("HSI_1d", "local"), "GSPC": load_y("GSPC_1d", "us"),
     "USDINR": load_y("USDINR_1d", "fx"), "BRENT": load_y("BRENT_1d", "us"), "VIXUS": load_y("VIX_US_1d", "us"),
     "DXY": _dx, "US10Y": load_y("US10Y_1d", "us")}
for k, d in Y.items():
    wk = int((d.index.weekday >= 5).sum())
    say(f"yahoo {k}: rows {len(d)} {d.index[0].date()}..{d.index[-1].date()} weekend-dated rows {wk} missing closes {int(d.close.isna().sum())} missing opens {int(d.open.isna().sum())}")

def prev_row_ret(df, T, col="close"):
    """% change of the last row dated strictly before T vs the row before it. Missing if either close is missing."""
    pos = df.index.searchsorted(T, side="left")
    if pos < 2: return np.nan, pd.NaT
    d = df.index[pos - 1]
    a, b = df[col].iloc[pos - 1], df[col].iloc[pos - 2]
    if (T - d).days > 6: return np.nan, d
    if pd.isna(a) or pd.isna(b) or b == 0: return np.nan, d
    return (a / b - 1) * 100, d
def open_gap(df, T):
    """opening gap of the row dated exactly T vs previous row's close (both Asian markets open before 09:15 IST)."""
    if T not in df.index: return np.nan
    pos = df.index.get_loc(T)
    if pos < 1: return np.nan
    o, c = df["open"].iloc[pos], df["close"].iloc[pos - 1]
    if pd.isna(o) or pd.isna(c) or c == 0: return np.nan
    return (o / c - 1) * 100
def cls3(v, thr):
    if pd.isna(v): return np.nan
    return "down" if v <= -thr else ("up" if v >= thr else "flat")

# Brent quality flag (daily vs 14:00 ET hourly close from data/parents; the DECISIONS.md note)
bh = pd.read_csv(PAR + "/yf_BZ_F_1h.csv"); bh["dt"] = pd.to_datetime(bh["Datetime_ET"])
h14 = bh[bh["dt"].dt.hour == 14].copy(); h14["d"] = h14["dt"].dt.normalize(); h14 = h14.groupby("d")["Close"].last()
cmpb = pd.concat([Y["BRENT"]["close"].rename("daily"), h14.rename("h14")], axis=1).dropna()
cmpb["dis"] = (cmpb["daily"] / cmpb["h14"] - 1) * 100
cmpb = cmpb[cmpb.index >= "2024-09-01"]
BRENT_BAD = set(cmpb.index[cmpb.dis.abs() > 2])
say("BRENT daily(downloaded) vs 14:00-ET hourly (data/parents), 2024-09 on: days", len(cmpb), "|diff|>1%:", int((cmpb.dis.abs() > 1).sum()),
    ">2%:", int((cmpb.dis.abs() > 2).sum()), ">4%:", int((cmpb.dis.abs() > 4).sum()), "max", round(float(cmpb.dis.abs().max()), 2),
    "(hourly file ends", h14.index.max().date(), "; trades after that cannot be flagged)")
pb = pd.read_csv(PAR + "/yf_BZ_F.csv", parse_dates=["Date"]).set_index("Date")["Close"]
cc = pd.concat([Y["BRENT"]["close"], pb], axis=1, keys=["new", "old"]).dropna()
say("BRENT downloaded daily vs data/parents daily: overlap", len(cc), "days differing >0.5%:", int(((cc.new / cc.old - 1).abs() > 0.005).sum()))

# USDINR hourly (robustness only): previous Indian session open (03:00 UTC bar) -> close (09:00 UTC bar)
uh = pd.read_csv(EXT + "/yahoo/USDINR_60m.csv"); uh["ts"] = pd.to_datetime(uh["timestamp_utc"])
uh["d"] = uh.ts.dt.normalize(); uh["h"] = uh.ts.dt.hour
o3 = uh[uh.h == 3].groupby("d")["open"].first(); c9 = uh[uh.h == 9].groupby("d")["close"].last()
usd_ind = ((c9 / o3 - 1) * 100).dropna()
say("USDINR hourly Indian-session change available days", len(usd_ind), usd_ind.index.min().date(), usd_ind.index.max().date())

# ------------------------------------------------------------ breadth
br = pd.read_csv(EXT + "/nse_breadth_daily.csv", parse_dates=["date"]).set_index("date").sort_index()
br["adv_share"] = br.advances / (br.advances + br.declines) * 100
base = br.loc["2021-10-01":"2024-09-30", "adv_share"]
BR_LO, BR_HI = float(np.percentile(base, 25)), float(np.percentile(base, 75))
say(f"breadth advance share percentiles over 2021-10-01..2024-09-30 (n={len(base)}): p25={BR_LO:.2f} p75={BR_HI:.2f}")
say("breadth dates not in session calendar:", [str(d.date()) for d in br.index.difference(pd.DatetimeIndex(SES))][:10])

# ------------------------------------------------------------ FII / DII cash (third party)
fd = pd.read_csv(EXT + "/fii_dii_cash_stockezee.csv", parse_dates=["date"]).set_index("date").sort_index()
fd = fd[["fii_cash_net", "dii_cash_net"]]
say("FII/DII cash rows", len(fd), fd.index.min().date(), fd.index.max().date(), "rows not in session calendar:", [str(d.date()) for d in fd.index if d not in SESSET])

# ------------------------------------------------------------ participant OI
rows = {}; bad_hdr = []
for f in sorted(glob.glob(OI_DIR + "/*.csv")):
    d = os.path.basename(f)[:-4]
    first = open(f, encoding="utf-8", errors="ignore").readline()
    m = re.search(r"as on ([A-Za-z]{3}) (\d{2}),(\d{4})", first)
    if m and pd.to_datetime(f"{m.group(1)} {m.group(2)} {m.group(3)}").strftime("%Y-%m-%d") != d: bad_hdr.append(d)
    t = pd.read_csv(f, skiprows=1); t.columns = [c.strip() for c in t.columns]
    t["Client Type"] = t["Client Type"].astype(str).str.strip().str.upper(); t = t.set_index("Client Type")
    rec = {}
    for who in ["FII", "DII"]:
        r = t.loc[who]
        rec[who] = dict(FL=float(r["Future Index Long"]), FS=float(r["Future Index Short"]), CL=float(r["Option Index Call Long"]),
                        CS=float(r["Option Index Call Short"]), PL=float(r["Option Index Put Long"]), PS=float(r["Option Index Put Short"]))
    rows[pd.Timestamp(d)] = rec
say("participant files", len(rows), min(rows).date(), max(rows).date(), "header-date mismatches", bad_hdr)
def fshare(rec, who):
    d = rec[who]; den = d["FL"] + d["FS"]; return d["FL"] / den * 100 if den > 0 else np.nan
def ostance(rec, who):
    d = rec[who]; den = d["CL"] + d["CS"] + d["PL"] + d["PS"]
    return ((d["PL"] - d["PS"]) - (d["CL"] - d["CS"])) / den if den > 0 else np.nan
OIS = pd.DataFrame({d: dict(fii_share=fshare(r, "FII"), dii_share=fshare(r, "DII"), fii_opt=ostance(r, "FII")) for d, r in rows.items()}).T.sort_index()
win = OIS.loc["2024-10-01":"2025-09-30"]
cuts = []
for c in ["fii_share", "dii_share", "fii_opt"]:
    lo, hi = np.quantile(win[c].dropna(), [1 / 3, 2 / 3])
    cuts.append(dict(variable=c, window="2024-10-01..2025-09-30 (all session files, return-independent)", n=int(win[c].notna().sum()), p33=lo, p67=hi))
CUT = pd.DataFrame(cuts); CUT.to_csv(OUT + "/external_level_cuts.csv", index=False)
say("participant level terciles:", CUT[["variable", "n", "p33", "p67"]].round(3).to_dict("records"))
def lvl(v, c):
    if pd.isna(v): return np.nan
    r = CUT[CUT.variable == c].iloc[0]; return "low" if v <= r.p33 else ("high" if v >= r.p67 else "mid")
def sgn(v): return np.nan if pd.isna(v) else ("up" if v > 0 else ("down" if v < 0 else np.nan))

# ------------------------------------------------------------ events
RBI = [date(2024,10,9),date(2024,12,6),date(2025,2,7),date(2025,4,9),date(2025,6,6),date(2025,8,6),date(2025,10,1),date(2025,12,5),
       date(2026,2,6),date(2026,4,8),date(2026,6,5),date(2026,8,5),date(2026,10,7)]
BUDGET = [date(2025,2,1), date(2026,2,1)]
FOMC = [date(2024,11,7),date(2024,12,18),date(2025,1,29),date(2025,3,19),date(2025,5,7),date(2025,6,18),date(2025,7,30),date(2025,9,17),
        date(2025,10,29),date(2025,12,10),date(2026,1,28),date(2026,3,18),date(2026,4,29),date(2026,6,17),date(2026,7,29),date(2026,9,16)]
USEL = [date(2024,11,5)]
def first_ses_ge(d, strict=False):
    i = np.searchsorted(SESARR, np.datetime64(pd.Timestamp(d)), side="right" if strict else "left"); return SES[i] if i < len(SES) else None
EV = {}
for kind, L, strict in (("RBI", RBI, False), ("Budget", BUDGET, False), ("US_election", USEL, True), ("FOMC", FOMC, True)):
    for d in L:
        e = first_ses_ge(d, strict)
        if e is not None: EV.setdefault(e, []).append(kind)
say("event sessions", len(EV), "(RBI policy, Budget, FOMC statement, US election; the lists come from scanner/s3_buy4.py; the US election entered is 2024-11-05, mapped to the first Indian session after it; no other election exists locally)")
say("Budget special sessions (Sat 2025-02-01, Sun 2026-02-01) are absent from nse_index_closes; added to the calendar (event flags and previous-session look-up; their market data are absent = missing):", [str(d) for d in BUDGET])
def event_class(T):
    i = np.searchsorted(SESXARR, np.datetime64(T), side="left")
    if i >= len(SESX) or SESX[i] != T: return np.nan, ""
    if T in EV: return "event_day", "+".join(EV[T])
    if i + 1 < len(SESX) and SESX[i + 1] in EV: return "day_before", "+".join(EV[SESX[i + 1]])
    if i >= 1 and SESX[i - 1] in EV: return "day_after", "+".join(EV[SESX[i - 1]])
    return "none", ""

# ------------------------------------------------------------ GDELT
gt = []
for f in sorted(glob.glob(GD_DIR + "/timelinetone_*.json")):
    for r in json.load(open(f))["timeline"][0]["data"]: gt.append((pd.to_datetime(r["date"][:8]), r["value"]))
gt = pd.Series(dict(gt)).sort_index()
say("GDELT tone obs", len(gt), gt.index[0].date(), gt.index[-1].date(), "missing calendar days in range", int(len(pd.date_range(gt.index[0], gt.index[-1])) - len(gt)))
def gdelt(T):
    d = T - timedelta(days=1)
    if d not in gt.index: return dict(tone_date="", tone=np.nan, tone_med250=np.nan, tone_class=np.nan)
    prior = gt[gt.index < d].tail(250)
    if len(prior) < 200: return dict(tone_date=d.date(), tone=gt[d], tone_med250=np.nan, tone_class=np.nan)
    med = float(prior.median()); return dict(tone_date=d.date(), tone=float(gt[d]), tone_med250=med, tone_class="above_median" if gt[d] > med else "below_median")

# ------------------------------------------------------------ build
def hy(d): return f"{d.year}H{1 if d.month <= 6 else 2}"
recs = []
for _, r in ds.iterrows():
    T = r["day"]; o = dict(strategy=r["tset"], date=T.date(), entry=r["entry"], half=r["half"], halfyear=hy(T), net_pct=r["net_pct"], net_rs=r["net_rs"], maxup=r["maxup"], dte=r["dte"])
    P = prev_session(T); P2 = prev_session(T, 2)
    o["prev_session"] = P.date() if P is not None else ""
    gn, gh = open_gap(Y["N225"], T), open_gap(Y["HSI"], T)
    o.update(n225_gap=gn, hsi_gap=gh)
    o["asia_avg_gap"] = (gn + gh) / 2 if not (pd.isna(gn) or pd.isna(gh)) else np.nan
    o["asia_class"] = cls3(o["asia_avg_gap"], 0.3)
    sp, spd = prev_row_ret(Y["GSPC"], T); o.update(sp_ret=sp, sp_date=spd.date() if pd.notna(spd) else "", us_class=cls3(sp, 0.3))
    ac, uc = o["asia_class"], o["us_class"]
    if pd.isna(ac) or pd.isna(uc): o["risk_class"] = np.nan
    elif uc == "up" and ac in ("up", "flat"): o["risk_class"] = "risk_on"
    elif uc == "down" and ac in ("down", "flat"): o["risk_class"] = "risk_off"
    else: o["risk_class"] = "mixed"
    u = Y["USDINR"]["close"]; ue = np.nan
    if P is not None and P in u.index:
        pos = u.index.get_loc(P)
        if pos >= 1 and pd.notna(u.iloc[pos]) and pd.notna(u.iloc[pos - 1]): ue = (u.iloc[pos] / u.iloc[pos - 1] - 1) * 100
    uh_ = usd_ind.get(P, np.nan) if P is not None else np.nan
    o.update(usd_chg=uh_, usd_class=cls3(uh_, 0.2), usd_daily_bar_chg_INVALID=ue)   # primary = hourly Indian-session change; Yahoo daily close == open (faulty)
    b, bd = prev_row_ret(Y["BRENT"], T)
    o.update(brent_chg=b, brent_date=bd.date() if pd.notna(bd) else "", brent_class=cls3(b, 1.0), brent_suspect=(np.nan if pd.isna(b) else int(bd in BRENT_BAD)))
    v, vd = prev_row_ret(Y["VIXUS"], T); o.update(usvix_chg=v, usvix_class=(np.nan if pd.isna(v) else ("spike" if v >= 10 else "no_spike")))
    dx, _ = prev_row_ret(Y["DXY"], T); o.update(dxy_chg=dx, dxy_class=(np.nan if pd.isna(dx) else ("up" if dx > 0 else ("down" if dx < 0 else np.nan))))
    ty, _ = prev_row_ret(Y["US10Y"], T); o.update(us10y_chg=ty, us10y_class=(np.nan if pd.isna(ty) else ("up" if ty > 0 else ("down" if ty < 0 else np.nan))))
    if P is not None and P in br.index:
        s_ = br.loc[P, "adv_share"]; o.update(adv_share_prev=s_, breadth_class=("low" if s_ <= BR_LO else ("high" if s_ >= BR_HI else "mid")))
    else: o.update(adv_share_prev=np.nan, breadth_class=np.nan)
    if P is not None and P in bret.index and P in nret.index and pd.notna(bret[P]) and pd.notna(nret[P]):
        d_ = bret[P] - nret[P]; o.update(bank_minus_nifty_prev=d_, sector_class=("bank_leads" if d_ >= 0.3 else ("bank_lags" if d_ <= -0.3 else "in_line")))
    else: o.update(bank_minus_nifty_prev=np.nan, sector_class=np.nan)
    if P is not None and P in fd.index:
        fi, di = fd.loc[P, "fii_cash_net"], fd.loc[P, "dii_cash_net"]
        o.update(fii_cash_prev=fi, dii_cash_prev=di, fii_cash_sign=("buy" if fi > 0 else "sell"), dii_cash_sign=("buy" if di > 0 else "sell"),
                 fiidii_class=("both_buy" if fi > 0 and di > 0 else ("both_sell" if fi < 0 and di < 0 else "diverge")))
    else: o.update(fii_cash_prev=np.nan, dii_cash_prev=np.nan, fii_cash_sign=np.nan, dii_cash_sign=np.nan, fiidii_class=np.nan)
    if P is not None and P in OIS.index and P2 is not None and P2 in OIS.index:
        a, bb = OIS.loc[P], OIS.loc[P2]
        o.update(oi_asof_session=P.date(), fii_fut_share=a.fii_share, fii_fut_share_chg=a.fii_share - bb.fii_share, dii_fut_share=a.dii_share,
                 dii_fut_share_chg=a.dii_share - bb.dii_share, fii_opt_stance=a.fii_opt, fii_opt_stance_chg=a.fii_opt - bb.fii_opt)
        o.update(fii_fut_level_class=lvl(a.fii_share, "fii_share"), fii_fut_chg_class=sgn(o["fii_fut_share_chg"]), dii_fut_level_class=lvl(a.dii_share, "dii_share"),
                 dii_fut_chg_class=sgn(o["dii_fut_share_chg"]), fii_opt_level_class=lvl(a.fii_opt, "fii_opt"), fii_opt_chg_class=sgn(o["fii_opt_stance_chg"]))
    else:
        o.update(oi_asof_session="", fii_fut_share=np.nan, fii_fut_share_chg=np.nan, dii_fut_share=np.nan, dii_fut_share_chg=np.nan, fii_opt_stance=np.nan, fii_opt_stance_chg=np.nan)
        for c in ["fii_fut_level_class", "fii_fut_chg_class", "dii_fut_level_class", "dii_fut_chg_class", "fii_opt_level_class", "fii_opt_chg_class"]: o[c] = np.nan
    o["event_class"], o["event_kind"] = event_class(T)
    o.update(gdelt(T)); o["check_us_prev_ret_ctx"] = r["us_prev_ret"]
    recs.append(o)
F = pd.DataFrame(recs)
F["publication_note"] = ("asia: Nikkei open 05:30 IST, HSI open 07:00 IST on the trade day; US/Brent/VIX/DXY/10Y: previous US session closed before 03:00 IST; "
    "USDINR: daily bar of previous NSE session (ends 05:30 IST trade day); breadth/sector/FII-DII cash: previous session, published evening of that session; "
    "participant OI: previous-session file (evening); events: calendar; GDELT: UTC day before trade date (complete 05:30 IST). All before 09:16 IST.")
F.to_csv(OUT + "/external_features.csv", index=False)
c = F.dropna(subset=["sp_ret", "check_us_prev_ret_ctx"])
say("check: sp_ret (new download) vs context_dataset us_prev_ret: n", len(c), "max abs diff", float((c.sp_ret - c.check_us_prev_ret_ctx).abs().max()),
    "| trades with the context value but no new value:", int((F.sp_ret.isna() & F.check_us_prev_ret_ctx.notna()).sum()))
c = F.dropna(subset=["usd_chg", "usd_daily_bar_chg_INVALID"])
say("check: USDINR daily-bar change (INVALID: Yahoo daily close==open on 100% of 2023-24 days, 92% of 2025, 73% of 2026) vs hourly Indian-session change: n", len(c), "corr", round(float(c.usd_chg.corr(c.usd_daily_bar_chg_INVALID)), 2), "-> daily bar not used")
say("DXY weekend-dated rows (all-NaN junk) dropped before use:", _nwk)
say("missing counts by strategy (feature: G1 / G1C / G1F / XP):")
for k in ["asia_class", "us_class", "risk_class", "usd_class", "brent_class", "usvix_class", "dxy_class", "us10y_class", "breadth_class", "sector_class", "fiidii_class",
          "fii_fut_level_class", "fii_fut_chg_class", "dii_fut_level_class", "fii_opt_level_class", "event_class", "tone_class"]:
    m = F[k].isna().groupby(F.strategy).sum().to_dict(); say("  ", k, {s: m.get(s) for s in ["G1", "G1C", "G1F", "XP"]})
say("brent_suspect trades:", F.groupby("strategy")["brent_suspect"].sum().to_dict())
say("class counts G1F:", {k: F[F.strategy == "G1F"][k].value_counts().to_dict() for k in ["asia_class", "us_class", "risk_class", "breadth_class", "sector_class", "fiidii_class", "event_class"]})
open(OUT + "/data_checks.txt", "w").write("\n".join(log))
