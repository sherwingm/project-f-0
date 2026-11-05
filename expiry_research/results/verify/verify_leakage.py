"""Independent look-ahead / leakage verification of data/panel_<UL>.parquet.

Written by the verifier, not the panel author. Reads raw parquet directly; does NOT import build_panel.
Run from the repo root:
    INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe expiry_research/results/verify/verify_leakage.py
Outputs (all in results/verify/):
    recompute_sample.csv     - selected f_/f1515_/y_ values recomputed from raw cut at t (5 random dates per UL)
    calendar_vs_listed.csv   - per row: calendar next expiry / weekly / monthly vs what the bhavcopy of t listed
    calendar_vs_listed_summary.csv
    alignment.csv            - date alignment of vix_daily and bhavcopy vs minute data
    split_check.csv          - split boundaries
    weekend_sessions.csv     - non-weekday sessions that drive cal_days_to_next_session
    verify_stdout.txt (via tee)
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
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
IDX = {"NIFTY": "NIFTY50", "BANKNIFTY": "NIFTYBANK", "SENSEX": "SENSEX"}
BAD = {"NIFTY50": {"2021-11-04", "2021-11-10", "2022-03-07"}, "NIFTYBANK": {"2021-11-04", "2021-11-10", "2022-03-07"},
       "SENSEX": {"2021-11-04", "2021-11-10"}, "INDIAVIX": {"2021-11-04", "2021-11-10"}}
P = {ul: pd.read_parquet(ROOT / "data" / f"panel_{ul}.parquet") for ul in IDX}


# ------------------------------------------------------------------ own raw loaders
def minutes(ix):
    fs = sorted(glob.glob(str(STORE / f"spot_1m/{ix}/*.parquet")))
    d = pd.concat([pq.read_table(f, columns=["timestamp", "open", "high", "low", "close"]).to_pandas() for f in fs])
    ts = d["timestamp"].dt.tz_convert("Asia/Kolkata")
    d["date"] = ts.dt.strftime("%Y-%m-%d")
    d["hm"] = ts.dt.strftime("%H:%M")
    d = d[(d["hm"] >= "09:15") & (d["hm"] <= "15:29")]
    d = d.sort_values("timestamp", kind="stable").drop_duplicates(["date", "hm"], keep="first")
    return d[["date", "hm", "open", "high", "low", "close"]]


def bhav_month(ul, months):
    fs = [STORE / f"options_daily/{ul}/{m}.parquet" for m in months]
    fs = [f for f in fs if f.exists()]
    cols = ["TradDt", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "SttlmPric", "OpnIntrst", "TtlTradgVol"]
    return pd.concat([pq.read_table(f, columns=cols).to_pandas() for f in fs])


icd = pd.read_parquet(STORE / "index_close_daily.parquet")
vixd = pd.read_parquet(STORE / "vix_daily.parquet")
MIN = {ul: minutes(ix) for ul, ix in IDX.items()}
VMIN = minutes("INDIAVIX")


def daily_ohlc(ul, sessions):
    """Own daily OHLC per session (rules of the LLD), using only each session's own data."""
    m = MIN[ul]
    g = m.groupby("date")
    md = pd.DataFrame({"n": g.size(), "first": g["hm"].min(), "last": g["hm"].max(), "o": g["open"].first(),
                       "h": g["high"].max(), "l": g["low"].min(), "c": g["close"].last()})
    ok = (md["n"] >= 370) & (md["first"] == "09:15") & (md["last"] == "15:29") & ~md.index.isin(BAD[IDX[ul]])
    ic = icd[icd["index"] == IDX[ul]].set_index("date")
    rows = []
    for d in sessions:
        if d in md.index and ok[d]:
            r = md.loc[d]
            rows.append((d, r.o, r.h, r.l, r.c))
        elif d in ic.index and pd.notna(ic.loc[d, "close"]):
            r = ic.loc[d]
            rows.append((d, r.open, r.high, r.low, r.close))
        elif d in md.index and md.loc[d, "n"] >= 300:
            r = md.loc[d]
            rows.append((d, r.o, r.h, r.l, r.c))
        else:
            rows.append((d, np.nan, np.nan, np.nan, np.nan))
    return pd.DataFrame(rows, columns=["date", "o", "h", "l", "c"]).set_index("date")


def Pa_sess_all(ul):
    # NSE session list (the calendar is known in advance; only dates <= t are used below)
    return P["NIFTY"]["date"].tolist()


def maxpain(K, ceoi, peoi):
    best, bk = None, None
    for k in K:
        pay = sum(max(k - x, 0) * a for x, a in zip(K, ceoi)) + sum(max(x - k, 0) * b for x, b in zip(K, peoi))
        if best is None or pay < best:
            best, bk = pay, k
    return bk


def recompute(ul, t):
    Pa = P[ul]
    sess = Pa["date"].tolist()
    i = sess.index(t)
    hist = sess[max(0, i - 60):i + 1]                       # cut: sessions <= t only
    D = daily_ohlc(ul, hist)                                # each day uses only its own raw rows (all <= t)
    c, h, l = D["c"], D["h"], D["l"]
    e = {}
    for k in [1, 5, 20]:
        e[f"f_mom{k}"] = (c.iloc[-1] / c.iloc[-1 - k] - 1) * 100
    e["f_dist_high20"] = (c.iloc[-1] / h.iloc[-20:].max() - 1) * 100
    e["f_dist_low55"] = (c.iloc[-1] / l.iloc[-55:].min() - 1) * 100
    lr = np.log(c / c.shift(1))
    e["f_hv20"] = lr.iloc[-20:].std(ddof=1) * np.sqrt(252) * 100
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    e["f_atr14_pct"] = tr.iloc[-14:].mean() / c.iloc[-1] * 100
    sg = np.sign(c.diff()).iloc[1:].to_numpy()
    run = 0
    for s in sg:
        run = 0 if s == 0 else (run + s if np.sign(run) == s else s)
    e["f_streak_close"] = float(run)
    # VIX close of t: vix_daily, then index_close_daily (cut <= t)
    v = vixd[(vixd["date"] <= t)].dropna(subset=["close"]).set_index("date")["close"]
    vi = icd[(icd["index"] == "INDIAVIX") & (icd["date"] <= t)].dropna(subset=["close"]).set_index("date")["close"]
    vix_t = v.get(t, vi.get(t, np.nan))
    e["f_vix_close"] = vix_t
    # pctile among the previous 252 VIX closes (combined series, sessions only from 2018, all before)
    allv = pd.concat([v, vi[~vi.index.isin(v.index)]])
    # third source as in the LLD: clean minute 15:29 close from 2023-08-23 (complete days), only days <= t
    vg = VMIN[(VMIN["date"] >= "2023-08-23") & (VMIN["date"] <= t)].groupby("date")
    vmc = vg["close"].last()[(vg.size() >= 370) & (vg["hm"].min() == "09:15") & (vg["hm"].max() == "15:29")]
    allv = pd.concat([allv, vmc[~vmc.index.isin(allv.index)]]).sort_index()
    if pd.isna(vix_t):
        e["f_vix_close"] = vix_t = vmc.get(t, np.nan)
    allsess = set(Pa_sess_all(ul))
    allv = allv[(allv.index < "2018-01-01") | allv.index.isin(allsess)]
    allv = allv[allv.index <= t]
    if t in allv.index:
        w = allv[allv.index < t].iloc[-252:]
        e["f_vix_pctile_1y"] = (w <= allv[t]).mean() * 100 if len(w) >= 200 else np.nan
    # f1515: minute bars of t up to 15:14 only + close(t-1)
    m = MIN[ul]
    mt = m[(m["date"] == t) & (m["hm"] <= "15:14")]
    if len(mt) >= 355 and mt["hm"].min() == "09:15" and t not in BAD[IDX[ul]]:
        e["f1515_ret_to_1514"] = (mt["close"].iloc[-1] / c.iloc[-2] - 1) * 100
        rr = np.log(mt["close"].to_numpy() / np.r_[mt["open"].iloc[0], mt["close"].to_numpy()[:-1]])
        e["f1515_rv"] = np.sqrt((rr ** 2).sum()) * 100
        hh, ll = mt["high"].max(), mt["low"].min()
        e["f1515_pos_in_range"] = (mt["close"].iloc[-1] - ll) / (hh - ll)
    # y_ labels: t+1 raw only + close(t)
    if i + 1 < len(sess):
        t1 = sess[i + 1]
        D1 = daily_ohlc(ul, [t1]).iloc[0]
        e["y_cc"] = (D1.c / c.iloc[-1] - 1) * 100
        e["y_gap_pct"] = (D1.o / c.iloc[-1] - 1) * 100
    if ul == "SENSEX":
        return e
    # bhavcopy of t (rows TradDt <= t only)
    mo = pd.Period(t, "M")
    b = bhav_month(ul, [str(mo - 2), str(mo - 1), str(mo)])
    b = b[b["TradDt"] <= t]
    bt = b[b["TradDt"] == t]
    if len(bt):
        f = bt[(bt["FinInstrmTp"] == "IDF") & (bt["XpryDt"] > t)].sort_values("XpryDt")
        if len(f):
            e["f_fut_expiry"] = f["XpryDt"].iloc[0]
            e["f_fut_close"] = f["ClsPric"].iloc[0]
            e["f_fut_oi"] = f["OpnIntrst"].iloc[0]
            prevd = [d for d in hist[:-1]][-20:]
            fo = []
            for d in prevd:
                x = b[(b["TradDt"] == d) & (b["FinInstrmTp"] == "IDF") & (b["XpryDt"] > d)].sort_values("XpryDt")
                if len(x):
                    fo.append(x["OpnIntrst"].iloc[0])
            e["f_fut_oi_r20"] = e["f_fut_oi"] / np.mean(fo) if len(fo) >= 15 else np.nan
        o = bt[(bt["FinInstrmTp"] == "IDO") & (bt["XpryDt"] > t)]
        o = o.drop_duplicates(["XpryDt", "StrkPric", "OptnTp"])
        futx = set(bt.loc[bt["FinInstrmTp"] == "IDF", "XpryDt"])
        for tag, ex in [("near", o["XpryDt"].min()), ("mon", min([x for x in o["XpryDt"].unique() if x in futx], default=None))]:
            if ex is None:
                continue
            e[f"f_opt_{tag}_expiry"] = ex
            g = o[o["XpryDt"] == ex]
            ce = g[g["OptnTp"] == "CE"].set_index("StrkPric")
            pe = g[g["OptnTp"] == "PE"].set_index("StrkPric")
            K = sorted(set(ce.index) | set(pe.index))
            co = [ce["OpnIntrst"].get(k, 0.0) for k in K]
            po = [pe["OpnIntrst"].get(k, 0.0) for k in K]
            e[f"f_opt_{tag}_ce_oi"] = sum(co)
            e[f"f_opt_{tag}_pcr_oi"] = sum(po) / sum(co)
            e[f"f_opt_{tag}_maxpain"] = maxpain(K, co, po)
            spot = c.iloc[-1]
            above = [(a, k) for k, a in zip(K, co) if k > spot and a > 0]
            e[f"f_opt_{tag}_callwall"] = max(above, key=lambda z: (z[0], -z[1]))[1] if above else np.nan
            valid = [k for k in K if ce["SttlmPric"].get(k, np.nan) > 0 and pe["SttlmPric"].get(k, np.nan) > 0]
            if valid:
                atm = min(valid, key=lambda k: (abs(k - spot), k))
                e[f"f_opt_{tag}_atm_strike"] = atm
                e[f"f_opt_{tag}_straddle_pct"] = (ce["SttlmPric"][atm] + pe["SttlmPric"][atm]) / spot * 100
    return e


def close_enough(a, b):
    if (a is None or (isinstance(a, float) and np.isnan(a))) and pd.isna(b):
        return True
    if isinstance(a, str) or isinstance(b, str):
        return str(a) == str(b)
    if pd.isna(a) or pd.isna(b):
        return False
    return bool(np.isclose(float(a), float(b), rtol=1e-7, atol=1e-9))


def part_a():
    rng = np.random.default_rng(20261105)
    rows = []
    for ul in IDX:
        d = P[ul]["date"].iloc[60:-1]
        if ul == "SENSEX":
            pick = rng.choice(d.to_numpy(), 5, replace=False)
        else:
            pick = np.r_[rng.choice(d[d < "2021-10-20"].to_numpy(), 2, replace=False),
                         rng.choice(d[d >= "2021-10-20"].to_numpy(), 3, replace=False)]
        for t in sorted(pick):
            e = recompute(ul, t)
            row = P[ul][P[ul]["date"] == t].iloc[0]
            for k, v in e.items():
                rows.append({"underlying": ul, "date": t, "column": k, "panel": row[k], "recomputed": v,
                             "match": close_enough(v, row[k])})
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "recompute_sample.csv", index=False)
    print(f"[A] recompute: {len(R)} comparisons, {int((~R['match']).sum())} mismatches")
    if (~R["match"]).any():
        print(R[~R["match"]].to_string(index=False))
    print(R.groupby("underlying")["date"].unique().to_string())


# ------------------------------------------------------------------ B: calendar tags vs what was listed on t
def part_b():
    out, summ = [], []
    cal = pd.read_csv(ROOT / "data" / "expiry_calendar.csv", dtype=str)
    for ul in ["NIFTY", "BANKNIFTY"]:
        fs = sorted(glob.glob(str(STORE / f"options_daily/{ul}/*.parquet")))
        L = pd.concat([pq.read_table(f, columns=["TradDt", "FinInstrmTp", "XpryDt"]).to_pandas().drop_duplicates()
                       for f in fs])
        opt = L[(L["FinInstrmTp"] == "IDO") & (L["XpryDt"] >= L["TradDt"])]
        fut = L[(L["FinInstrmTp"] == "IDF") & (L["XpryDt"] >= L["TradDt"])]
        lst = opt.groupby("TradDt")["XpryDt"].apply(lambda s: sorted(set(s)))
        flst = fut.groupby("TradDt")["XpryDt"].apply(lambda s: set(s))
        S = pd.read_csv(ROOT / "data" / f"sessions_{ul}.csv", dtype=str).set_index("date")
        for t in P[ul]["date"]:
            if t not in lst.index or t not in S.index:
                continue
            listed = lst[t]
            mon_listed = [x for x in listed if x in flst.get(t, set())]
            r = {"underlying": ul, "date": t}
            for name, col, pool in [("expiry", "next_expiry", listed), ("monthly", "next_monthly", mon_listed),
                                    ("weekly", "next_weekly", None)]:
                tag = S.loc[t, col]
                tag = None if pd.isna(tag) else tag
                r[f"tag_{name}"] = tag
                r[f"tag_{name}_listed_on_t"] = (tag in listed) if tag else None
                if pool is not None:
                    r[f"nearest_listed_{name}"] = pool[0] if pool else None
            r["tag_sessions_to_weekly"] = S.loc[t, "sessions_to_next_weekly"]
            out.append(r)
    B = pd.DataFrame(out)
    B["expiry_tag_differs"] = B["tag_expiry"].notna() & (B["tag_expiry"] != B["nearest_listed_expiry"])
    B["monthly_tag_differs"] = B["tag_monthly"].notna() & (B["tag_monthly"] != B["nearest_listed_monthly"])
    B["weekly_tag_unlisted"] = B["tag_weekly"].notna() & (B["tag_weekly_listed_on_t"] == False)  # noqa: E712
    B.to_csv(OUT / "calendar_vs_listed.csv", index=False)
    for ul, g in B.groupby("underlying"):
        for k in ["expiry_tag_differs", "monthly_tag_differs", "weekly_tag_unlisted"]:
            x = g[g[k]]
            summ.append({"underlying": ul, "check": k, "n_rows": len(x),
                         "first": x["date"].min() if len(x) else None, "last": x["date"].max() if len(x) else None,
                         "distinct_tag_dates": ";".join(sorted(set(x[{"expiry_tag_differs": "tag_expiry",
                                                                       "monthly_tag_differs": "tag_monthly",
                                                                       "weekly_tag_unlisted": "tag_weekly"}[k]])))[:400]})
    Sm = pd.DataFrame(summ)
    Sm.to_csv(OUT / "calendar_vs_listed_summary.csv", index=False)
    print("[B] calendar tags vs listed contracts on t")
    print(Sm.to_string(index=False))
    # per-episode detail for expiry_tag_differs
    d = B[B["expiry_tag_differs"]].groupby(["underlying", "tag_expiry", "nearest_listed_expiry"])["date"].agg(
        ["min", "max", "size"]).reset_index()
    d.to_csv(OUT / "calendar_expiry_tag_episodes.csv", index=False)
    print(d.to_string(index=False))
    d = B[B["monthly_tag_differs"]].groupby(["underlying", "tag_monthly", "nearest_listed_monthly"])["date"].agg(
        ["min", "max", "size"]).reset_index()
    d.to_csv(OUT / "calendar_monthly_tag_episodes.csv", index=False)
    print(d.to_string(index=False))
    # NIFTY weekly tag before the first weekly was listed
    first_wk = B[(B["underlying"] == "NIFTY") & (B["tag_weekly"] == "2019-02-14")]
    print("NIFTY rows whose next_weekly = 2019-02-14:", len(first_wk), first_wk["date"].min(), first_wk["date"].max())
    pn = P["NIFTY"]
    print("panel NIFTY cal_sessions_to_weekly non-null before 2019-02-11:",
          int(pn.loc[pn["date"] < "2019-02-11", "cal_sessions_to_weekly"].notna().sum()), "of",
          int((pn["date"] < "2019-02-11").sum()))
    fl = cal[(cal["underlying"] == "NIFTY") & (cal["expiry_date"] == "2019-02-14")]
    print("expiry_calendar NIFTY 2019-02-14 first_listed_seen:", fl["first_listed_seen"].tolist())


# ------------------------------------------------------------------ C: alignment
def part_c():
    rows = []
    vm = VMIN[VMIN["date"] >= "2023-08-23"]
    g = vm.groupby("date")
    vc = g["close"].last()[g.size() >= 370]
    v = vixd.dropna(subset=["close"]).set_index("date")["close"]
    dates = sorted(set(vc.index) & set(v.index))
    vcs = vc.reindex(sorted(vc.index))
    for lag in [-1, 0, 1]:
        s = vcs.shift(-lag)            # lag +1 = minute close of the next minute day
        x = (v.reindex(dates) / s.reindex(dates) - 1).abs() * 100
        rows.append({"check": "vix_daily close(d) vs minute VIX 15:29 close(d+lag)", "lag": lag,
                     "n": int(x.notna().sum()), "median_abs_pct": x.median()})
    for ul in ["NIFTY", "BANKNIFTY"]:
        Pa = P[ul]
        bs = Pa["f_fut_basis_pct"]
        rows.append({"check": f"{ul} |fut close(t)/px_close(t)-1|", "lag": 0, "n": int(bs.notna().sum()),
                     "median_abs_pct": bs.abs().median()})
        sh = (Pa["f_fut_close"] / Pa["px_close"].shift(-1) - 1).abs() * 100
        rows.append({"check": f"{ul} |fut close(t)/px_close(t+1)-1|", "lag": 1, "n": int(sh.notna().sum()),
                     "median_abs_pct": sh.median()})
        sh = (Pa["f_fut_close"] / Pa["px_close"].shift(1) - 1).abs() * 100
        rows.append({"check": f"{ul} |fut close(t)/px_close(t-1)-1|", "lag": -1, "n": int(sh.notna().sum()),
                     "median_abs_pct": sh.median()})
    C = pd.DataFrame(rows)
    C.to_csv(OUT / "alignment.csv", index=False)
    print("[C] alignment")
    print(C.to_string(index=False))


# ------------------------------------------------------------------ D: splits
def part_d():
    rows = []
    for ul, Pa in P.items():
        for sp, g in Pa.groupby("split"):
            rows.append({"underlying": ul, "split": sp, "rows": len(g), "first": g["date"].min(), "last": g["date"].max(),
                         "max_y_date": g["y_date"].dropna().max(), "n_split_edge": int(g["split_edge"].sum()),
                         "edge_dates": ";".join(g.loc[g["split_edge"], "date"] + "->" + g.loc[g["split_edge"], "y_date"])})
        bad = Pa[((Pa["split"] == "discovery") & (Pa["date"] > "2022-12-31")) |
                 ((Pa["split"] == "validation") & ((Pa["date"] < "2023-01-01") | (Pa["date"] > "2024-06-30"))) |
                 ((Pa["split"] == "final") & (Pa["date"] < "2024-07-01"))]
        rows.append({"underlying": ul, "split": "MISASSIGNED", "rows": len(bad)})
    D = pd.DataFrame(rows)
    D.to_csv(OUT / "split_check.csv", index=False)
    print("[D] splits")
    print(D.to_string(index=False))


# ------------------------------------------------------------------ E: calendar next-session / weekend sessions
def part_e():
    Pa = P["NIFTY"]
    wd = pd.to_datetime(Pa["date"]).dt.dayofweek
    x = Pa.loc[wd >= 5, ["date", "cal_dow"]].copy()
    prev = Pa.set_index("date")["cal_next_date"]
    x["previous_row"] = [Pa["date"].iloc[i - 1] for i in Pa.index[wd >= 5]]
    x["prev_row_cal_days_to_next_session"] = [Pa["cal_days_to_next_session"].iloc[i - 1] for i in Pa.index[wd >= 5]]
    x.to_csv(OUT / "weekend_sessions.csv", index=False)
    print("[E] non-weekday sessions (cal_next_date of the row before points to them)")
    print(x.to_string(index=False))
    # rows around 2024-01-19..23 (short-notice changes)
    print(Pa.loc[Pa["date"].between("2024-01-17", "2024-01-24"),
                 ["date", "cal_next_date", "cal_days_to_next_session", "cal_sessions_to_expiry", "cal_kind"]].to_string(index=False))


if __name__ == "__main__":
    part_d()
    part_c()
    part_e()
    part_b()
    part_a()
