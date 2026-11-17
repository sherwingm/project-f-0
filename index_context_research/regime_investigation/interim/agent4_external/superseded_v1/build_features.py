"""Agent 4: build PRE-ENTRY external features (participant OI, global markets, events, GDELT tone) for every trade.
Inputs are read-only local files. Nothing is downloaded. Output: external_features.csv, data_checks.txt (in this folder).
Alignment rules (fixed before any return was looked at) are in availability_table.md.
"""
import glob
import json
import os
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd

REPO = "C:/Users/sherw/project-f-0"
OUT = os.path.join(REPO, "index_context_research/regime_investigation/interim/agent4_external")
OI_DIR = os.path.join(REPO, "g1_research/data/external/participant_oi")
GD_DIR = os.path.join(REPO, "g1_research/data/external/gdelt")
PAR = os.path.join(REPO, "data/parents")
DS = os.path.join(REPO, "index_context_research/results/context_dataset.csv")
log = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log.append(s)


# ---------------------------------------------------------------- trades
ds = pd.read_csv(DS)
ds["day"] = pd.to_datetime(ds["day"])
ds = ds[["tset", "day", "entry", "net_pct", "net_rs", "maxup", "half", "dte", "expiry_day", "event_window",
         "us_prev_ret", "fii_fut_longshare", "fii_fut_chg"]].copy()
say("trades", ds.groupby("tset").size().to_dict())

# ---------------------------------------------------------------- participant OI
rows = {}
bad_hdr = []
for f in sorted(glob.glob(OI_DIR + "/*.csv")):
    d = os.path.basename(f)[:-4]
    with open(f, encoding="utf-8", errors="ignore") as fh:
        first = fh.readline()
    m = re.search(r"as on ([A-Za-z]{3}) (\d{2}),(\d{4})", first)
    if m:
        hd = pd.to_datetime(f"{m.group(1)} {m.group(2)} {m.group(3)}").strftime("%Y-%m-%d")
        if hd != d:
            bad_hdr.append((d, hd))
    t = pd.read_csv(f, skiprows=1)
    t.columns = [c.strip() for c in t.columns]
    t["Client Type"] = t["Client Type"].astype(str).str.strip().str.upper()
    t = t.set_index("Client Type")
    rec = {}
    for who in ["FII", "DII", "CLIENT", "PRO"]:
        r = t.loc[who]
        rec[who] = dict(FL=float(r["Future Index Long"]), FS=float(r["Future Index Short"]),
                        CL=float(r["Option Index Call Long"]), CS=float(r["Option Index Call Short"]),
                        PL=float(r["Option Index Put Long"]), PS=float(r["Option Index Put Short"]))
    rows[pd.Timestamp(d)] = rec
oi_dates = sorted(rows)
say("participant files", len(oi_dates), oi_dates[0].date(), oi_dates[-1].date(), "header-date mismatches", bad_hdr[:5], len(bad_hdr))
hol = set(json.load(open(os.path.join(REPO, "data/nse_holidays.json")))["holidays"])
allwd = pd.bdate_range(oi_dates[0], oi_dates[-1])
missing_wd = [d for d in allwd if d not in rows and d.strftime("%Y-%m-%d") not in hol]
say("weekdays without a participant file and not in nse_holidays.json:", len(missing_wd), [str(d.date()) for d in missing_wd][:15])
say("note: nse_holidays.json (fetched 2026-10-14) may not list earlier-year holidays; the count above is an upper bound on real gaps")
ses = oi_dates  # session calendar
sesarr = np.array(ses, dtype="datetime64[ns]")


def prev_sessions(T):
    i = np.searchsorted(sesarr, np.datetime64(T), side="left")
    return (ses[i - 1] if i >= 1 else None, ses[i - 2] if i >= 2 else None)


def share(rec, who):
    d = rec[who]
    den = d["FL"] + d["FS"]
    return d["FL"] / den * 100 if den > 0 else np.nan


def oi_feats(T):
    p1, p2 = prev_sessions(T)
    out = {"oi_asof": p1}
    if p1 is None or p2 is None or (T - p1).days > 5:
        return out
    a, b = rows[p1], rows[p2]
    for who, k in [("FII", "fii"), ("DII", "dii"), ("CLIENT", "client"), ("PRO", "pro")]:
        out[f"{k}_fut_net"] = a[who]["FL"] - a[who]["FS"]
        out[f"{k}_fut_share"] = share(a, who)
        out[f"{k}_fut_net_chg"] = (a[who]["FL"] - a[who]["FS"]) - (b[who]["FL"] - b[who]["FS"])
        out[f"{k}_fut_share_chg"] = share(a, who) - share(b, who)
        out[f"{k}_call_net"] = a[who]["CL"] - a[who]["CS"]
        out[f"{k}_put_net"] = a[who]["PL"] - a[who]["PS"]
        bear = (a[who]["PL"] - a[who]["PS"]) - (a[who]["CL"] - a[who]["CS"])
        bearb = (b[who]["PL"] - b[who]["PS"]) - (b[who]["CL"] - b[who]["CS"])
        out[f"{k}_opt_bear_net"] = bear  # net put minus net call position (contracts): bigger = more bearish option stance
        out[f"{k}_opt_bear_chg"] = bear - bearb
    return out


# ---------------------------------------------------------------- global series
def load_px(name):
    s = pd.read_csv(os.path.join(PAR, f"yf_{name}.csv"), parse_dates=["Date"]).set_index("Date")["Close"].astype(float)
    return s.sort_index()


GL = {"sp": load_px("GSPC"), "usd": load_px("USDINR_X"), "brent": load_px("BZ_F"), "copper": load_px("HG_F"),
      "alu": load_px("ALI_F"), "iron": load_px("TIO_F")}


def prev_wd(T):
    d = T - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def glob_ret(s, T):
    """1-session % change of the last bar dated strictly before T. Missing if the series ended before the previous weekday."""
    idx = s.index
    pos = idx.searchsorted(T, side="left")  # first bar >= T
    if pos < 2:
        return np.nan, pd.NaT
    d = idx[pos - 1]
    if pos == len(idx) and prev_wd(T) > d:
        return np.nan, d
    return (s.iloc[pos - 1] / s.iloc[pos - 2] - 1) * 100, d


b = GL["brent"]
br = b.pct_change() * 100
say("BRENT daily: bars", len(b), b.index[0].date(), b.index[-1].date(), "min", b.min(), "max", b.max(),
    "|ret|>8%:", int((br.abs() > 8).sum()), "|ret|>5%:", int((br.abs() > 5).sum()), "zero-change days:", int((br == 0).sum()))
h = pd.read_csv(os.path.join(PAR, "yf_BZ_F_1h.csv"))
h["dt"] = pd.to_datetime(h["Datetime_ET"])
h14 = h[h["dt"].dt.hour == 14].copy()
h14["d"] = h14["dt"].dt.normalize()
h14 = h14.groupby("d")["Close"].last()
cmp = pd.concat([b.rename("daily"), h14.rename("h14")], axis=1).dropna()
cmp["dis"] = (cmp["daily"] / cmp["h14"] - 1) * 100
cmp = cmp[cmp.index >= "2024-09-01"]
say("BRENT daily vs 14:00-ET hourly close (2024-09 on): days compared", len(cmp), "|diff|>1%:", int((cmp.dis.abs() > 1).sum()),
    ">2%:", int((cmp.dis.abs() > 2).sum()), ">4%:", int((cmp.dis.abs() > 4).sum()), "max", round(cmp.dis.abs().max(), 2))
say("BRENT days with |diff|>2%:", [(str(i.date()), round(v, 1)) for i, v in cmp.dis[cmp.dis.abs() > 2].items()][:30])
brent_bad = set(cmp.index[cmp.dis.abs() > 2])
for k in ["usd", "copper", "alu", "iron", "sp"]:
    s = GL[k]
    r = s.pct_change() * 100
    say(k.upper(), "bars", len(s), s.index[0].date(), s.index[-1].date(), "|ret|>8%:", int((r.abs() > 8).sum()), "zero-change days:", int((r == 0).sum()),
        "last-30-bars zero-change share:", round(float((r.tail(30) == 0).mean()), 2))

# ---------------------------------------------------------------- events (copied from scanner/s3_buy4.py lines 44-52)
RBI = [date(2024, 10, 9), date(2024, 12, 6), date(2025, 2, 7), date(2025, 4, 9), date(2025, 6, 6), date(2025, 8, 6),
       date(2025, 10, 1), date(2025, 12, 5), date(2026, 2, 6), date(2026, 4, 8), date(2026, 6, 5), date(2026, 8, 5),
       date(2026, 10, 7)]
BUDGET = [date(2025, 2, 1), date(2026, 2, 1)]
FOMC_US = [date(2024, 11, 7), date(2024, 12, 18), date(2025, 1, 29), date(2025, 3, 19), date(2025, 5, 7),
           date(2025, 6, 18), date(2025, 7, 30), date(2025, 9, 17), date(2025, 10, 29), date(2025, 12, 10),
           date(2026, 1, 28), date(2026, 3, 18), date(2026, 4, 29), date(2026, 6, 17), date(2026, 7, 29),
           date(2026, 9, 16)]
US_ELECTION = [date(2024, 11, 6)]


def next_session(d, strict=False):
    i = np.searchsorted(sesarr, np.datetime64(pd.Timestamp(d)), side="right" if strict else "left")
    return ses[i] if i < len(ses) else None


EV = {}
for kind, ds_ in (("RBI", RBI), ("US_election", US_ELECTION)):
    for d in ds_:
        e = next_session(d)
        if e is not None:
            EV.setdefault(e, []).append(kind)
for d in BUDGET:  # Budget fell on a Saturday (2025-02-01) / Sunday (2026-02-01): NSE held special sessions (G1-C traded both days)
    EV.setdefault(pd.Timestamp(d), []).append("Budget")
for d in FOMC_US:
    e = next_session(d, strict=True)  # first Indian session after the US statement date
    if e is not None:
        EV.setdefault(e, []).append("FOMC")
ses_ext = sorted(set(ses) | {pd.Timestamp(d) for d in BUDGET})
sesarr_ext = np.array(ses_ext, dtype="datetime64[ns]")
say("event sessions", len(EV), "Budget kept on its own (weekend special-session) date:", [str(d) for d in BUDGET])
say("event list gaps: no FOMC after 2026-09-16 in the repo list; no CPI / GDP / geopolitical dates exist anywhere locally")


def event_class(T):
    i = np.searchsorted(sesarr_ext, np.datetime64(T), side="left")
    if i >= len(ses_ext) or ses_ext[i] != T:
        return np.nan, ""
    if T in EV:
        return "event_day", "+".join(EV[T])
    if i + 1 < len(ses_ext) and ses_ext[i + 1] in EV:
        return "day_before", "+".join(EV[ses_ext[i + 1]])
    if i >= 1 and ses_ext[i - 1] in EV:
        return "day_after", "+".join(EV[ses_ext[i - 1]])
    return "none", ""


# ---------------------------------------------------------------- GDELT tone
gt = []
for f in sorted(glob.glob(GD_DIR + "/timelinetone_*.json")):
    for r in json.load(open(f))["timeline"][0]["data"]:
        gt.append((pd.to_datetime(r["date"][:8]), r["value"]))
gt = pd.Series(dict(gt)).sort_index()
say("GDELT tone: observations", len(gt), gt.index[0].date(), gt.index[-1].date(),
    "missing calendar days in range:", int(len(pd.date_range(gt.index[0], gt.index[-1])) - len(gt)))


def gdelt_feats(T):
    d = T - timedelta(days=1)
    if d not in gt.index:
        return dict(tone_date="", tone=np.nan, tone_med250=np.nan, tone_class=np.nan)
    prior = gt[gt.index < d].tail(250)
    if len(prior) < 200:
        return dict(tone_date=d.date(), tone=gt[d], tone_med250=np.nan, tone_class=np.nan)
    med = float(prior.median())
    return dict(tone_date=d.date(), tone=float(gt[d]), tone_med250=med, tone_class="above_median" if gt[d] > med else "below_median")


def cls3(v, lo, hi):
    if pd.isna(v):
        return np.nan
    return "down" if v <= lo else ("up" if v >= hi else "flat")


recs = []
for _, r in ds.iterrows():
    T = r["day"]
    o = dict(strategy=r["tset"], date=T.date(), entry=r["entry"], half=r["half"], net_pct=r["net_pct"], net_rs=r["net_rs"],
             maxup=r["maxup"], dte=r["dte"])
    f = oi_feats(T)
    oa = f.get("oi_asof")
    o["oi_asof_session"] = oa.date() if oa is not None else ""
    for k, v in f.items():
        if k != "oi_asof":
            o[k] = v
    for k in ["fii_fut_share_chg", "dii_fut_share_chg", "client_fut_share_chg", "pro_fut_share_chg", "fii_opt_bear_chg"]:
        v = o.get(k, np.nan)
        o[k.replace("_chg", "_chgsign")] = np.nan if pd.isna(v) else ("up" if v > 0 else ("down" if v < 0 else "zero"))
    fa, da = o.get("fii_fut_share_chg", np.nan), o.get("dii_fut_share_chg", np.nan)
    if pd.isna(fa) or pd.isna(da):
        o["fii_dii_diverge"] = np.nan
    elif fa == 0 or da == 0:
        o["fii_dii_diverge"] = "other"
    elif fa * da < 0:
        o["fii_dii_diverge"] = "divergent"
    else:
        o["fii_dii_diverge"] = "both_up" if fa > 0 else "both_down"
    sp, sp_d = glob_ret(GL["sp"], T)
    us, us_d = glob_ret(GL["usd"], T)
    br_, br_d = glob_ret(GL["brent"], T)
    cu, cu_d = glob_ret(GL["copper"], T)
    al, al_d = glob_ret(GL["alu"], T)
    io, io_d = glob_ret(GL["iron"], T)
    dd = lambda x: "" if pd.isna(x) else x.date()
    o.update(sp_ret=sp, sp_date=dd(sp_d), sp_class=cls3(sp, -0.3, 0.3),
             usd_chg=us, usd_date=dd(us_d), usd_class=cls3(us, -0.2, 0.2),
             brent_chg=br_, brent_date=dd(br_d), brent_class=cls3(br_, -1, 1),
             brent_suspect=(np.nan if pd.isna(br_) else int(br_d in brent_bad)),
             copper_chg=cu, copper_class=cls3(cu, -1, 1), alu_chg=al, iron_chg=io)
    if pd.isna(sp) or pd.isna(us):
        o["risk_class"] = np.nan
    elif sp >= 0.3 and us < 0.2:
        o["risk_class"] = "risk_on"
    elif sp <= -0.3 and us > -0.2:
        o["risk_class"] = "risk_off"
    else:
        o["risk_class"] = "mixed"
    o["event_class"], o["event_kind"] = event_class(T)
    o.update(gdelt_feats(T))
    o["check_us_prev_ret_ctx"] = r["us_prev_ret"]
    o["check_fii_share_ctx"] = r["fii_fut_longshare"]
    o["check_fii_chg_ctx"] = r["fii_fut_chg"]
    recs.append(o)

F = pd.DataFrame(recs)
F["pub_oi"] = "after close of oi_asof_session (evening, NSE archives); known before entry"
F["pub_sp"] = "US close 16:00 ET of sp_date = 01:30/02:30 IST next calendar day; before 09:15 IST"
F["pub_fx_cmd"] = "daily bar of usd_date / brent_date complete by about 05:30 IST on the trade day (Yahoo; see notes)"
F["pub_event"] = "scheduled calendar dates; known in advance (list from scanner/s3_buy4.py, Budget re-mapped)"
F["pub_gdelt"] = "UTC day tone_date complete 05:30 IST on trade day; retrieved later (possible revision), see notes"
F.to_csv(os.path.join(OUT, "external_features.csv"), index=False)

c = F.dropna(subset=["sp_ret", "check_us_prev_ret_ctx"])
say("check: sp_ret vs dataset us_prev_ret: n", len(c), "max abs diff", float((c.sp_ret - c.check_us_prev_ret_ctx).abs().max()),
    "n differing >0.01:", int(((c.sp_ret - c.check_us_prev_ret_ctx).abs() > 0.01).sum()))
c = F.dropna(subset=["fii_fut_share", "check_fii_share_ctx"])
say("check: fii_fut_share vs dataset fii_fut_longshare: n", len(c), "max abs diff", float((c.fii_fut_share - c.check_fii_share_ctx).abs().max()))
c = F.dropna(subset=["fii_fut_share_chg", "check_fii_chg_ctx"])
say("check: fii chg vs dataset: n", len(c), "max abs diff", float((c.fii_fut_share_chg - c.check_fii_chg_ctx).abs().max()))
say("missing counts by strategy:")
for k in ["oi_asof_session", "fii_fut_share", "sp_ret", "usd_chg", "brent_chg", "copper_chg", "risk_class", "event_class", "tone_class"]:
    x = F[k].replace("", np.nan)
    say("  ", k, x.isna().groupby(F.strategy).sum().to_dict())
say("brent_suspect trades:", F.groupby("strategy")["brent_suspect"].sum().to_dict())
g = F[F.strategy == "G1F"]
say("event class counts G1F:", g.event_class.value_counts().to_dict(), "kinds", g.event_kind.value_counts().to_dict())
open(os.path.join(OUT, "data_checks.txt"), "w").write("\n".join(log))
