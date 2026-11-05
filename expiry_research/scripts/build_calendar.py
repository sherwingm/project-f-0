"""Historical expiry calendar + per-session expiry tags (see reports/lld/audit_calendar.md).

Run from the repo root:
    INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe expiry_research/scripts/build_calendar.py
Writes expiry_research/data/expiry_calendar.csv, data/expiry_relabels.csv, data/sessions_<UL>.csv,
results/audit/calendar_checks.csv, results/audit/calendar_counts.csv.
"""
import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8")
STORE = Path(os.environ.get("INDEX_STORE", "../fo-index-data/data/index"))
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AUD = ROOT / "results" / "audit"
DATA.mkdir(exist_ok=True)
AUD.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ official regimes
# (underlying, kind, first expiry date covered, last expiry date covered, usual weekday, source id)
# Source ids are explained in reports/EXPIRY_CALENDAR_ANALYSIS.md section 1.
REGIMES = [
    ("NIFTY", "monthly", "2000-01-01", "2025-08-31", "Thursday", "NSE contract spec (last Thursday); NSE/FAOP/68685"),
    ("NIFTY", "monthly", "2025-09-01", "2099-12-31", "Tuesday", "NSE/FAOP/68685 + 68747 (Jun 2025)"),
    ("NIFTY", "weekly", "2019-02-11", "2025-08-31", "Thursday", "NSE PR 11-Feb-2019 (weekly launch); NSE/FAOP/68685"),
    ("NIFTY", "weekly", "2025-09-01", "2099-12-31", "Tuesday", "NSE/FAOP/68685 + 68747 (Jun 2025)"),
    ("BANKNIFTY", "weekly", "2016-05-27", "2023-09-05", "Thursday", "NSE/FAOP/57540 (current day before change)"),
    ("BANKNIFTY", "weekly", "2023-09-06", "2024-11-13", "Wednesday", "NSE/FAOP/57540 (Jul 2023); SEBI CIR/2024/132 end"),
    ("BANKNIFTY", "monthly", "2000-01-01", "2024-02-29", "Thursday", "NSE/FAOP/60011 (current day before change)"),
    ("BANKNIFTY", "monthly", "2024-03-01", "2024-12-31", "Wednesday", "NSE/FAOP/60011 (Dec 2023)"),
    ("BANKNIFTY", "monthly", "2025-01-01", "2025-08-31", "Thursday", "NSE/FAOP/65336 (Nov 2024)"),
    ("BANKNIFTY", "monthly", "2025-09-01", "2099-12-31", "Tuesday", "NSE/FAOP/68685 + 68747 (Jun 2025)"),
    ("SENSEX", "weekly", "2023-05-15", "2025-01-03", "Friday", "BSE notice 28-Nov-2024 (current day; 3-Jan-2025 kept Friday)"),
    ("SENSEX", "weekly", "2025-01-04", "2025-08-31", "Tuesday", "BSE notice 28-Nov-2024"),
    ("SENSEX", "weekly", "2025-09-01", "2099-12-31", "Thursday", "SEBI CIR/2025/76 + BSE notice Jun 2025"),
    ("SENSEX", "monthly", "2023-05-15", "2024-12-31", "Friday", "BSE notice 28-Nov-2024 (current day)"),
    ("SENSEX", "monthly", "2025-01-01", "2025-08-31", "Tuesday", "BSE notice 28-Nov-2024"),
    ("SENSEX", "monthly", "2025-09-01", "2099-12-31", "Thursday", "SEBI CIR/2025/76 + BSE notice Jun 2025"),
]
LIVE = ["expired", "expired_unverified", "future_listed"]
WD = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def regime_for(ul, kind, d):
    for u, k, lo, hi, wd, src in REGIMES:
        if u == ul and k == kind and lo <= d <= hi:
            return wd, src
    return None, None


# ------------------------------------------------------------------ session calendar
def session_calendar():
    """Union of trading days in the core datasets (from 2018) + data-detected special short sessions.

    Special session (e.g. Diwali Muhurat): NIFTY option volume in the bhavcopy < 30 % of the centred 21-session
    median AND the NIFTY50 1-minute file has no day or fewer than 200 bars for it.
    """
    per = {}            # dataset -> set of days
    vol = []
    for ul in ["NIFTY", "BANKNIFTY"]:
        for f in glob.glob(str(STORE / f"options_daily/{ul}/*.parquet")):
            t = pq.read_table(f, columns=["TradDt", "TtlTradgVol"]).to_pandas()
            per.setdefault(f"bhav_{ul}", set()).update(t["TradDt"])
            if ul == "NIFTY":
                vol.append(t.groupby("TradDt")["TtlTradgVol"].sum())
    nbars = {}
    for ix in ["NIFTY50", "NIFTYBANK", "SENSEX", "INDIAVIX"]:
        for f in glob.glob(str(STORE / f"spot_1m/{ix}/*.parquet")):
            ts = pq.read_table(f, columns=["timestamp"]).to_pandas()["timestamp"].dt.tz_convert("Asia/Kolkata")
            ds = ts.dt.strftime("%Y-%m-%d")
            per.setdefault(f"spot_{ix}", set()).update(ds.unique())
            if ix == "NIFTY50":
                nbars.update(ds.value_counts().to_dict())
    per["vix_daily"] = set(pd.read_parquet(STORE / "vix_daily.parquet", columns=["date"])["date"])
    ic = pd.read_parquet(STORE / "index_close_daily.parquet", columns=["date", "index"])
    for ix, g in ic.groupby("index"):
        per[f"idx_{ix}"] = set(g["date"])
    for ul in ["NIFTY", "SENSEX"]:
        per[f"opt1m_{ul}"] = {Path(f).stem for f in glob.glob(str(STORE / f"options_1m/{ul}/*/*.parquet"))}
    cnt = {}
    for st in per.values():
        for d in st:
            cnt[d] = cnt.get(d, 0) + 1
    # a day seen in only one dataset is not trusted as a session (2023-12-23 spot SENSEX, 2025-04-26 option minutes)
    dropped = sorted(d for d, c in cnt.items() if c < 2 and d >= "2018-01-01")
    pd.DataFrame({"date": dropped, "reason": "present in only one dataset"}).to_csv(AUD / "sessions_dropped.csv", index=False)
    sessions = sorted(d for d, c in cnt.items() if c >= 2 and d >= "2018-01-01")
    v = pd.concat(vol).groupby(level=0).sum().sort_index()
    ratio = v / v.rolling(21, center=True, min_periods=5).median()
    special = pd.DataFrame({"date": ratio.index, "nifty_opt_volume_ratio": ratio.values})
    special["spot1m_bars"] = special["date"].map(nbars).fillna(0).astype(int)
    special = special[(special["nifty_opt_volume_ratio"] < 0.3) & (special["spot1m_bars"] < 200)]
    special["weekday"] = pd.to_datetime(special["date"]).dt.day_name()
    return sessions, special.reset_index(drop=True)


# ------------------------------------------------------------------ expiries
def bhav_expiries(ul):
    parts = [pd.read_parquet(f, columns=["TradDt", "FinInstrmTp", "XpryDt", "TtlTradgVol"])
             for f in sorted(glob.glob(str(STORE / f"options_daily/{ul}/*.parquet")))]
    d = pd.concat(parts, ignore_index=True)
    last_bhav = d["TradDt"].max()
    g = d.groupby("XpryDt").agg(first_listed_seen=("TradDt", "min"), last_traded=("TradDt", "max"),
                                n_sessions_traded=("TradDt", "nunique"),
                                has_futures=("FinInstrmTp", lambda s: bool((s == "IDF").any())),
                                has_options=("FinInstrmTp", lambda s: bool((s == "IDO").any())),
                                volume_total=("TtlTradgVol", "sum")).reset_index()
    g = g.rename(columns={"XpryDt": "expiry_date"})
    on_exp = d[d["TradDt"] == d["XpryDt"]].groupby("XpryDt")["TtlTradgVol"].sum()
    g["volume_on_expiry_day"] = g["expiry_date"].map(on_exp)
    g["underlying"] = ul
    g["source"] = "bhavcopy"
    g["status"] = np.where(g["last_traded"] == g["expiry_date"], "expired",
                           np.where(g["last_traded"] == last_bhav, "future_listed", "ghost"))
    return g, last_bhav


def opt1m_expiries(ul):
    rows = []
    for p in sorted(glob.glob(str(STORE / f"options_1m/{ul}/*"))):
        files = sorted(Path(p).glob("*.parquet"))
        if not files:
            continue
        days = [f.stem for f in files]
        rows.append(dict(underlying=ul, expiry_date=Path(p).name, first_listed_seen=days[0], last_traded=days[-1],
                         n_sessions_traded=len(days), last_day_is_expiry=days[-1] == Path(p).name))
    return pd.DataFrame(rows)


def link_ghosts(g, sessions):
    """Map each ghost XpryDt to the expiry its contracts continued under."""
    nxt = {s: sessions[i + 1] for i, s in enumerate(sessions[:-1])}
    out = []
    for _, r in g[g["status"] == "ghost"].iterrows():
        old = pd.Timestamp(r["expiry_date"])
        cand = g[(g["expiry_date"] != r["expiry_date"])
                 & ((pd.to_datetime(g["expiry_date"]) - old).dt.days.abs() <= 10)].copy()
        cand["dist"] = (pd.to_datetime(cand["expiry_date"]) - old).dt.days.abs()
        n = nxt.get(r["last_traded"])
        pick, how = None, "unlinked"
        if len(cand):
            exact = cand[cand["first_listed_seen"] == n]
            if len(exact):
                pick, how = exact.sort_values("dist").iloc[0]["expiry_date"], "nearest date first seen on the next session"
            else:
                live = cand[cand["status"] != "ghost"]
                if len(live):
                    pick, how = live.sort_values("dist").iloc[0]["expiry_date"], "nearest live date within 10 days (weak)"
        out.append(dict(underlying=r["underlying"], old_expiry=r["expiry_date"],
                        old_weekday=old.day_name(), old_first_seen=r["first_listed_seen"],
                        old_last_traded=r["last_traded"], new_expiry=pick,
                        new_weekday=pd.Timestamp(pick).day_name() if pick else None, link_rule=how))
    out = pd.DataFrame(out)
    # follow chains of re-dating to the date the contracts finally carry
    m = dict(zip(out["old_expiry"], out["new_expiry"]))
    fin = []
    for d in out["old_expiry"]:
        x, seen = d, set()
        while x in m and x not in seen and m[x] is not None:
            seen.add(x)
            x = m[x]
        fin.append(x)
    out["final_expiry"] = fin
    return pd.DataFrame(out)


def assign_kind(cal, full):
    """monthly = the expiry on the (holiday-adjusted) last regime weekday of the month; others weekly.

    For each month: w = official monthly weekday in force at month end, target = last w-day of the month; the
    monthly is the latest live expiry in [target - 6 days, target]. A plain "last expiry of the calendar month"
    rule fails when a weekly is pulled back into the month by a holiday (e.g. BANKNIFTY 2024-04-30 for 1 May) or
    when a weekly falls after a monthly in the same month (BANKNIFTY 2024-01-31), so it is kept only as a check.
    """
    cal["kind"] = None
    cal["monthly_target"] = None
    live = cal["status"].isin(LIVE)
    fset = set(full)
    for ul in cal["underlying"].unique():
        m = live & (cal["underlying"] == ul)
        months = sorted(cal.loc[m, "expiry_date"].str[:7].unique())
        for mon in months:
            month_end = (pd.Timestamp(mon + "-01") + pd.offsets.MonthEnd(0))
            w, _ = regime_for(ul, "monthly", month_end.strftime("%Y-%m-%d"))
            if w is None:
                continue
            t = month_end - pd.Timedelta(days=int((month_end.weekday() - WD.index(w)) % 7))
            lo = (t - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
            ts = t.strftime("%Y-%m-%d")
            win = cal[m & (cal["expiry_date"] >= lo) & (cal["expiry_date"] <= ts)]
            if len(win):
                i = win["expiry_date"].idxmax()
                cal.loc[i, "kind"] = "monthly"
                cal.loc[i, "monthly_target"] = ts
        cal.loc[m & cal["kind"].isna(), "kind"] = "weekly"
    month = cal["expiry_date"].str[:7]
    lim = cal[live].groupby([cal["underlying"], month])["expiry_date"].transform("max")
    cal["last_in_month"] = False
    cal.loc[live, "last_in_month"] = cal.loc[live, "expiry_date"] == lim
    return cal


def classify(cal, sessions, special):
    sset = set(sessions)
    spec = set(special["date"])
    full = [x for x in sessions if x not in spec]
    cal = cal.sort_values(["underlying", "expiry_date"]).reset_index(drop=True)
    cal["weekday"] = pd.to_datetime(cal["expiry_date"]).dt.day_name()
    cal = assign_kind(cal, full)
    cal["is_quarterly"] = (cal["kind"] == "monthly") & cal["expiry_date"].str[5:7].isin(["03", "06", "09", "12"])
    uw, src, shifted, reason, reg_date = [], [], [], [], []
    last_sess = sessions[-1]
    for _, r in cal.iterrows():
        if r["kind"] is None:
            uw.append(None); src.append(None); shifted.append(None); reason.append(None); reg_date.append(None)
            continue
        w, s = regime_for(r["underlying"], r["kind"], r["expiry_date"])
        uw.append(w); src.append(s)
        if w is None:
            shifted.append(None); reason.append("no official regime on file"); reg_date.append(None); continue
        if r["weekday"] == w:
            shifted.append(False); reason.append(""); reg_date.append(r["expiry_date"]); continue
        shifted.append(True)
        d = pd.Timestamp(r["expiry_date"])
        k = (WD.index(w) - d.weekday()) % 7          # regime day on/after the actual date
        rd = (d + pd.Timedelta(days=int(k))).strftime("%Y-%m-%d")
        reg_date.append(rd)
        if rd > last_sess:
            reason.append("future: regime day beyond stored sessions, holiday not verifiable")
            continue
        between_full = [x for x in full if r["expiry_date"] < x <= rd]
        if between_full:
            reason.append("unexplained: a full session lies between actual and regime day")
        elif rd in spec:
            reason.append("special session: regime day was a short special session (Muhurat), moved to previous full session")
        elif rd not in sset:
            reason.append("holiday: regime day not a session, moved to previous session")
        else:
            reason.append("unexplained")
    cal["usual_weekday"] = uw
    cal["regime_source"] = src
    cal["regime_date"] = reg_date
    cal["shifted"] = shifted
    cal["shift_reason"] = reason
    return cal


def expected_missing(cal, sessions, special):
    """Regime days (weekly or monthly) that have no live expiry within [day - 4, day + 2] calendar days.

    Only checked between the first live expiry of the underlying and the last stored session.
    """
    spec = set(special["date"])
    full = set(x for x in sessions if x not in spec)
    rows = []
    live = cal[cal["status"].isin(LIVE)]
    for ul in live["underlying"].unique():
        e = pd.to_datetime(live.loc[live["underlying"] == ul, "expiry_date"])
        lo, hi = e.min(), pd.Timestamp(sessions[-1])
        for kind in ["weekly", "monthly"]:
            for u, k, a, b, w, src in REGIMES:
                if u != ul or k != kind:
                    continue
                a_, b_ = max(pd.Timestamp(a), lo), min(pd.Timestamp(b), hi)
                if a_ > b_:
                    continue
                days = pd.date_range(a_, b_, freq="D")
                days = days[days.day_name() == w]
                if kind == "monthly":
                    days = days[(days + pd.Timedelta(days=7)).month != days.month]
                for rd in days:
                    near = e[(e >= rd - pd.Timedelta(days=4)) & (e <= rd + pd.Timedelta(days=2))]
                    wk_full = [x for x in pd.date_range(rd - pd.Timedelta(days=4), rd).strftime("%Y-%m-%d") if x in full]
                    if near.empty and wk_full:
                        rows.append(dict(underlying=ul, kind_expected=kind, regime_date=rd.strftime("%Y-%m-%d"),
                                         weekday=w, note="no stored expiry near this regime day"))
    return pd.DataFrame(rows, columns=["underlying", "kind_expected", "regime_date", "weekday", "note"])


def known_from(cal, gh):
    """First day an expiry is known (see lld/audit_calendar.md, change 2026-11-05).

    Bhavcopy expiries: first_listed_seen, or the earliest first-seen day of a ghost date re-dated into it if earlier.
    Other sources (SENSEX options_1m folders, expiries.parquet): blank, because their first stored day is when
    collection started, not the listing day. No announcement date is used (none was read), so nothing is inferred.
    """
    gfirst = gh.groupby(["underlying", "final_expiry"])["old_first_seen"].min()
    out = []
    for _, r in cal.iterrows():
        if not str(r["source"]).startswith("bhavcopy") or pd.isna(r["first_listed_seen"]):
            out.append(None)
            continue
        k = r["first_listed_seen"]
        g = gfirst.get((r["underlying"], r["expiry_date"]))
        if isinstance(g, str) and g < k:
            k = g
        out.append(k)
    return out


def session_tags(ul, cal, sessions, special, missing):
    e = cal[(cal["underlying"] == ul) & cal["status"].isin(LIVE)]
    first_known = e["first_listed_seen"].dropna().min()
    if ul == "SENSEX":
        # SENSEX history starts with the first stored folder: tags valid only after the first known expiry
        first_known = e["expiry_date"].min()
    spec = set(special["date"])
    full = [x for x in sessions if x not in spec]
    idx = {s: i for i, s in enumerate(full)}       # sessions are counted on full sessions only
    s = pd.DataFrame({"date": [x for x in sessions if x >= first_known]})
    s["weekday"] = pd.to_datetime(s["date"]).dt.day_name()
    s["is_special_session"] = s["date"].isin(spec)
    allx = sorted(e["expiry_date"])
    wk = sorted(e.loc[e["kind"] == "weekly", "expiry_date"])
    mo = sorted(e.loc[e["kind"] == "monthly", "expiry_date"])
    # an expiry counts as "next" on day d only if it was known on d (listed; blank known_from = no listing day stored)
    kf = dict(zip(e["expiry_date"], e["known_from"]))

    def known(x, d):
        k = kf.get(x)
        return not isinstance(k, str) or k <= d

    def nxt(lst, d):
        i = int(np.searchsorted(lst, d, side="left"))
        while i < len(lst) and not known(lst[i], d):
            i += 1
        return lst[i] if i < len(lst) else None

    def nxt_any(lst, d):          # no known-from filter: only finds the span blanked around a missing expiry
        i = np.searchsorted(lst, d, side="left")
        return lst[i] if i < len(lst) else None

    def prv(lst, d):
        i = np.searchsorted(lst, d, side="left") - 1
        return lst[i] if i >= 0 else None

    def dist(a, b):
        if a is None or b is None or a not in idx or b not in idx:
            return np.nan
        return idx[b] - idx[a]

    for name, lst in [("expiry", allx), ("weekly", wk), ("monthly", mo)]:
        s[f"next_{name}"] = [nxt(lst, d) for d in s["date"]]
        s[f"sessions_to_next_{name}"] = [dist(d, n) for d, n in zip(s["date"], s[f"next_{name}"])]
        s[f"next_{name}_known_from"] = [kf.get(n) if n else None for n in s[f"next_{name}"]]
    s["last_expiry"] = [prv(allx, d) for d in s["date"]]
    s["sessions_since_last_expiry"] = [dist(p, d) for d, p in zip(s["date"], s["last_expiry"])]
    s["cal_days_to_next_expiry"] = [(pd.Timestamp(n) - pd.Timestamp(d)).days if n else np.nan
                                    for d, n in zip(s["date"], s["next_expiry"])]
    s["is_expiry_any"] = s["date"].isin(allx)
    s["is_expiry_weekly"] = s["date"].isin(wk)
    s["is_expiry_monthly"] = s["date"].isin(mo)
    s["next_expiry_kind"] = np.where(s["next_expiry"].isin(mo), "monthly",
                                     np.where(s["next_expiry"].isna(), None, "weekly"))
    # blank the tags around expiries that should exist but are not stored (never guessed)
    s["calendar_gap"] = False
    m = missing[missing["underlying"] == ul]
    any_cols = ["next_expiry", "sessions_to_next_expiry", "last_expiry", "sessions_since_last_expiry",
                "cal_days_to_next_expiry", "next_expiry_kind", "next_weekly", "sessions_to_next_weekly",
                "next_expiry_known_from", "next_weekly_known_from"]
    for _, r in m.iterrows():
        rd = r["regime_date"]
        lo_, hi_ = prv(allx, rd), nxt_any(allx, rd)
        sel = (s["date"] >= (lo_ or "0000")) & (s["date"] <= (hi_ or "9999"))
        s.loc[sel, any_cols] = None
        s.loc[sel, "calendar_gap"] = True
        if r["kind_expected"] == "monthly":
            lo_, hi_ = prv(mo, rd), nxt_any(mo, rd)
            sel = (s["date"] >= (lo_ or "0000")) & (s["date"] <= (hi_ or "9999"))
            s.loc[sel, ["next_monthly", "sessions_to_next_monthly", "next_monthly_known_from"]] = None
            s.loc[sel, "calendar_gap"] = True
    s.loc[s["is_special_session"], [c for c in s.columns if c.startswith("sessions_")]] = None
    s.insert(0, "underlying", ul)
    for c in [c for c in s.columns if c.startswith("sessions_") or c == "cal_days_to_next_expiry"]:
        s[c] = pd.to_numeric(s[c]).astype("Int64")
    return s


def main():
    sessions, special = session_calendar()
    special.to_csv(DATA / "special_sessions.csv", index=False)
    last_sess = sessions[-1]
    cals, ghosts, checks = [], [], []
    opt_nifty = opt1m_expiries("NIFTY")
    for ul in ["NIFTY", "BANKNIFTY"]:
        g, last_bhav = bhav_expiries(ul)
        gh = link_ghosts(g, sessions)
        ghosts.append(gh)
        reloc = gh.groupby("final_expiry")["old_expiry"].apply(lambda x: ";".join(sorted(x)))
        g["relabelled_from"] = g["expiry_date"].map(reloc)
        if ul == "NIFTY":
            # expiries after the last stored bhavcopy day: confirm from option-minute folders
            late = opt_nifty[(opt_nifty["expiry_date"] > last_bhav) & opt_nifty["last_day_is_expiry"]]
            for _, r in late.iterrows():
                m = g["expiry_date"] == r["expiry_date"]
                if m.any():
                    g.loc[m, "status"] = "expired"
                    g.loc[m, "last_traded"] = r["expiry_date"]
                    g.loc[m, "source"] = "bhavcopy listing + options_1m expiry-day file"
        cals.append(g)
    sx = opt1m_expiries("SENSEX")
    # a folder without its expiry-day file is still a listed expiry (collection stopped early), not a re-dated one
    sx["status"] = np.where(sx["last_day_is_expiry"], "expired",
                            np.where(sx["expiry_date"] > last_sess, "future_listed", "expired_unverified"))
    sx["source"] = "options_1m folder"
    sx["has_futures"] = np.nan
    sx["has_options"] = True
    cals.append(sx.drop(columns=["last_day_is_expiry"]))
    # future expiries from expiries.parquet not yet seen anywhere (only used for the next-expiry pointer)
    ep = pd.read_parquet(STORE / "expiries.parquet")
    ep = ep[ep["underlying"].isin(["NIFTY", "BANKNIFTY", "SENSEX"])]
    have = set(zip(pd.concat(cals)["underlying"], pd.concat(cals)["expiry_date"]))
    add = ep[[(u, d) not in have for u, d in zip(ep["underlying"], ep["expiry_date"])]]
    if len(add):
        cals.append(pd.DataFrame(dict(underlying=add["underlying"], expiry_date=add["expiry_date"],
                                      status="future_listed", source="expiries.parquet")))
    cal = pd.concat(cals, ignore_index=True)
    cal = classify(cal, sessions, special)
    gh = pd.concat(ghosts, ignore_index=True)
    cal["known_from"] = known_from(cal, gh)
    cols = ["underlying", "expiry_date", "weekday", "kind", "is_quarterly", "status", "source", "has_futures",
            "first_listed_seen", "known_from", "last_traded", "n_sessions_traded", "volume_on_expiry_day", "usual_weekday",
            "regime_date", "shifted", "shift_reason", "regime_source", "monthly_target", "last_in_month",
            "relabelled_from"]
    out = cal[cal["status"] != "ghost"][cols]
    out.to_csv(DATA / "expiry_calendar.csv", index=False)
    gh.to_csv(DATA / "expiry_relabels.csv", index=False)
    missing = expected_missing(out, sessions, special)
    missing.to_csv(DATA / "expiry_missing.csv", index=False)

    # ---------------- checks
    exp = out[out["status"].isin(["expired", "expired_unverified"])]
    sset = set(sessions)
    checks.append(dict(check="expired expiries that are not sessions", n=int((~exp["expiry_date"].isin(sset)).sum())))
    for ul in ["NIFTY", "BANKNIFTY"]:
        e = exp[exp["underlying"] == ul]
        checks.append(dict(check=f"{ul}: monthly without futures", n=int(((e["kind"] == "monthly") & (e["has_futures"] != True)).sum()),
                           detail=";".join(e.loc[(e["kind"] == "monthly") & (e["has_futures"] != True), "expiry_date"])))
        checks.append(dict(check=f"{ul}: weekly with futures", n=int(((e["kind"] == "weekly") & (e["has_futures"] == True)).sum()),
                           detail=";".join(e.loc[(e["kind"] == "weekly") & (e["has_futures"] == True), "expiry_date"])))
        dif = e[(e["kind"] == "monthly") != e["last_in_month"]]
        checks.append(dict(check=f"{ul}: kind differs from plain last-expiry-of-month rule", n=len(dif),
                           detail=";".join(f"{d}({k})" for d, k in zip(dif["expiry_date"], dif["kind"]))))
        checks.append(dict(check=f"{ul}: unlinked ghosts", n=int((gh[(gh["underlying"] == ul)]["new_expiry"].isna()).sum())))
    sset_full = [x for x in sessions if x not in set(special["date"])]
    for ul in ["NIFTY", "BANKNIFTY", "SENSEX"]:
        mm = missing[missing["underlying"] == ul]
        checks.append(dict(check=f"{ul}: official regime days with no stored expiry nearby (missing expiries)", n=len(mm),
                           detail=";".join(f"{d}({k})" for d, k in zip(mm["regime_date"], mm["kind_expected"]))))
        e = exp[exp["underlying"] == ul].sort_values("expiry_date")
        mo_ = e[e["kind"] == "monthly"]
        bad = []
        for d, t in zip(mo_["expiry_date"], mo_["monthly_target"]):
            adj = max(x for x in sset_full if x <= t) if t <= last_sess else None
            if adj and adj != d:
                bad.append(f"{d}(target {t}, adjusted {adj})")
        checks.append(dict(check=f"{ul}: monthly not on the holiday-adjusted last regime weekday", n=len(bad), detail=";".join(bad)))
        if ul == "SENSEX":
            dif = e[(e["kind"] == "monthly") != e["last_in_month"]]
            checks.append(dict(check=f"{ul}: kind differs from plain last-expiry-of-month rule", n=len(dif),
                               detail=";".join(f"{d}({k})" for d, k in zip(dif["expiry_date"], dif["kind"]))))
        gap = pd.to_datetime(e["expiry_date"]).diff().dt.days
        big = e.loc[gap > 8, "expiry_date"]
        checks.append(dict(check=f"{ul}: gaps > 8 calendar days between consecutive expired expiries", n=len(big),
                           detail=";".join(f"{p}->{d}" for p, d in zip(e["expiry_date"].shift().loc[big.index], big))))
        sh = e[e["shifted"] == True]
        checks.append(dict(check=f"{ul}: shifted expiries (weekday differs from official regime)", n=len(sh),
                           detail=";".join(f"{d}({r.split(':')[0]})" for d, r in zip(sh["expiry_date"], sh["shift_reason"]))))
        un = sh[sh["shift_reason"].str.startswith("unexplained")]
        checks.append(dict(check=f"{ul}: shifted and unexplained by a holiday (mismatch vs official regime)", n=len(un),
                           detail=";".join(un["expiry_date"])))
    # options_1m NIFTY folders vs bhavcopy expiries
    bn = set(exp.loc[exp["underlying"] == "NIFTY", "expiry_date"])
    on = set(opt_nifty["expiry_date"])
    lo, hi = min(on), max(exp.loc[exp["underlying"] == "NIFTY", "expiry_date"])
    miss = sorted(x for x in bn if lo <= x <= hi and x not in on)
    extra = sorted(x for x in on if x <= hi and x not in bn)
    checks.append(dict(check="NIFTY: real expiries in options_1m span without an options_1m folder", n=len(miss), detail=";".join(miss)))
    checks.append(dict(check="NIFTY: options_1m folders that are not real bhavcopy expiries", n=len(extra), detail=";".join(extra)))
    checks.append(dict(check="NIFTY: options_1m folders whose last day file is not the expiry",
                       n=int((~opt_nifty["last_day_is_expiry"] & (opt_nifty["expiry_date"] <= last_sess)).sum()),
                       detail=";".join(opt_nifty.loc[~opt_nifty["last_day_is_expiry"] & (opt_nifty["expiry_date"] <= last_sess), "expiry_date"])))
    pd.DataFrame(checks).to_csv(AUD / "calendar_checks.csv", index=False)

    # ---------------- counts per year
    exp2 = exp.assign(year=exp["expiry_date"].str[:4])
    cnt = exp2.pivot_table(index=["underlying", "year"], columns="kind", values="expiry_date", aggfunc="count", fill_value=0)
    wd = exp2.pivot_table(index=["underlying", "year"], columns="weekday", values="expiry_date", aggfunc="count", fill_value=0)
    sh = exp2.groupby(["underlying", "year"])["shifted"].apply(lambda s: int((s == True).sum())).rename("shifted")
    span = exp2.groupby(["underlying", "year"])["expiry_date"].agg(first="min", last="max")
    counts = cnt.join(wd).join(sh).join(span).reset_index()
    counts.to_csv(AUD / "calendar_counts.csv", index=False)

    for ul in ["NIFTY", "BANKNIFTY", "SENSEX"]:
        st = session_tags(ul, out, sessions, special, missing)
        st.to_csv(DATA / f"sessions_{ul}.csv", index=False)
        print(ul, "sessions rows:", len(st), st["date"].min(), "->", st["date"].max())
    pd.set_option("display.width", 250)
    print(counts.to_string())
    print(pd.DataFrame(checks).to_string())
    print("ghost relabels:", len(gh))
    print(special.to_string())
    print(missing.to_string())


if __name__ == "__main__":
    main()
