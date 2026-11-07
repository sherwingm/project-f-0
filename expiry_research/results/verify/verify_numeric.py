"""Independent verifier: recompute selected panel values from raw parquet. Throwaway code, not part of the build."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np, pandas as pd
S = os.environ.get("INDEX_STORE", "../fo-index-data/data/index")
OUT = "expiry_research/results/verify"
rng = np.random.default_rng(20261105)
SPOT = {"NIFTY": "NIFTY50", "BANKNIFTY": "NIFTYBANK"}
BAD = {"2021-11-04", "2021-11-10", "2022-03-07"}
idx = pd.read_parquet(f"{S}/index_close_daily.parquet")

def bhav(u, d):
    b = pd.read_parquet(f"{S}/options_daily/{u}/{d[:7]}.parquet")
    return b[b.TradDt.astype(str) == d].copy()

def minutes(u, d):
    m = pd.read_parquet(f"{S}/spot_1m/{SPOT[u]}/{d[:7]}.parquet")
    m["ts"] = m.timestamp.dt.tz_convert("Asia/Kolkata")
    m = m[m.ts.dt.strftime("%Y-%m-%d") == d]
    hm = m.ts.dt.strftime("%H:%M")
    return m[(hm >= "09:15") & (hm <= "15:29")].assign(hm=hm).sort_values("ts")

def daily(u, d):
    if d >= "2021-10-20" and d not in BAD:
        m = minutes(u, d)
        if len(m):
            return dict(src="spot_1m", o=m.open.iloc[0], h=m.high.max(), l=m.low.min(),
                        c=m[m.hm == "15:29"].close.iloc[0] if (m.hm == "15:29").any() else np.nan, m=m)
    r = idx[(idx["index"] == SPOT[u]) & (idx.date.astype(str) == d)]
    if len(r):
        r = r.iloc[0]; return dict(src="index_close_daily", o=r.open, h=r.high, l=r.low, c=r.close, m=None)
    return None

def opt_stats(b, exp, close):
    o = b[(b.FinInstrmTp == "IDO") & (b.XpryDt.astype(str) == exp)]
    ce = o[o.OptnTp == "CE"].groupby("StrkPric").agg(oi=("OpnIntrst", "sum"), st=("SttlmPric", "max"))
    pe = o[o.OptnTp == "PE"].groupby("StrkPric").agg(oi=("OpnIntrst", "sum"), st=("SttlmPric", "max"))
    pcr = pe.oi.sum() / ce.oi.sum()
    j = ce.join(pe, lsuffix="_ce", rsuffix="_pe", how="outer").fillna({"oi_ce": 0, "oi_pe": 0})
    K = j.index.values
    pay = [(j.oi_ce * np.maximum(k - K, 0)).sum() + (j.oi_pe * np.maximum(K - k, 0)).sum() for k in K]
    pay = np.array(pay); mp = K[np.argmin(pay)]
    ties = K[np.isclose(pay, pay.min())]
    both = j[(j.st_ce > 0) & (j.st_pe > 0)]
    atm = both.index.values[np.argmin(np.abs(both.index.values - close))]
    strad = (both.loc[atm, "st_ce"] + both.loc[atm, "st_pe"]) / close * 100
    return pcr, mp, ties, atm, strad

rows = []
def cmp(u, d, name, mine, panel, tol=1e-6, note=""):
    if isinstance(mine, (float, np.floating, int, np.integer)) and not pd.isna(mine) and not pd.isna(panel):
        ok = abs(float(mine) - float(panel)) <= tol * max(1, abs(float(panel)))
    elif pd.isna(mine) if not isinstance(mine, (str, bool, np.bool_)) else False:
        ok = pd.isna(panel)
    else:
        ok = (str(mine) == str(panel)) if not isinstance(mine, (bool, np.bool_)) else (bool(mine) == bool(panel) if not pd.isna(panel) else False)
    rows.append(dict(underlying=u, date=d, field=name, mine=mine, panel=panel, match=ok, note=note))

for u, n_pre, n_min in [("NIFTY", 3, 5), ("BANKNIFTY", 1, 3)]:
    p = pd.read_parquet(f"expiry_research/data/panel_{u}.parquet")
    p["date"] = p.date.astype(str)
    p = p.iloc[1:-1]   # need prev and next
    pre = p[p.date < "2021-10-20"].date.values; post = p[p.date >= "2021-10-20"].date.values
    picks = sorted(list(rng.choice(pre, n_pre, replace=False)) + list(rng.choice(post, n_min, replace=False)))
    P = pd.read_parquet(f"expiry_research/data/panel_{u}.parquet"); P["date"] = P.date.astype(str)
    for d in picks:
        i = P.index[P.date == d][0]; r = P.loc[i]; dprev = P.loc[i - 1, "date"]; dnext = P.loc[i + 1, "date"]
        print(u, d, "prev", dprev, "next", dnext, "y_date", r.get("y_date"))
        D = daily(u, d); Dp = daily(u, dprev); Dn = daily(u, dnext)
        cmp(u, d, "src", D["src"], r.src)
        for k, c in [("o", "px_open"), ("h", "px_high"), ("l", "px_low"), ("c", "px_close")]:
            cmp(u, d, c, D[k], r[c])
        off = idx[(idx["index"] == SPOT[u]) & (idx.date.astype(str) == d)]
        if len(off):
            cmp(u, d, "px_close_official", off.close.iloc[0], r.px_close_official)
            cmp(u, d, "close_vs_official_pct(info)", (D["c"] / off.close.iloc[0] - 1) * 100, 0, tol=0.1,
                note="info: minute 15:29 close vs official; tol 0.1 %")
        cmp(u, d, "o_gap_pct", (D["o"] / Dp["c"] - 1) * 100, r.o_gap_pct, 1e-9)
        cmp(u, d, "y_gap_pct", (Dn["o"] / D["c"] - 1) * 100, r.y_gap_pct, 1e-9)
        gap = Dn["o"] - D["c"]
        filled = np.nan if gap == 0 else (Dn["l"] <= D["c"] if gap > 0 else Dn["h"] >= D["c"])
        cmp(u, d, "y_gap_filled", filled, r.y_gap_filled)
        if Dn["m"] is not None:
            m = Dn["m"]; c944 = m[m.hm == "09:44"].close
            cmp(u, d, "y_ret30", (c944.iloc[0] / m.open.iloc[0] - 1) * 100 if len(c944) else np.nan, r.y_ret30, 1e-9)
            if gap != 0 and filled:
                hit = m[(m.low <= D["c"]) if gap > 0 else (m.high >= D["c"])]
                fm = (hit.ts.iloc[0] - m.ts.iloc[0]).total_seconds() / 60
                cmp(u, d, "y_gap_fill_min", fm, r.y_gap_fill_min)
        else:
            cmp(u, d, "y_ret30", np.nan, r.y_ret30, note="no minute data for t+1")
        b = bhav(u, d)
        if len(b) == 0:
            cmp(u, d, "bhavcopy", "absent", "absent" if pd.isna(r.f_fut_oi) else "present"); continue
        fut = b[(b.FinInstrmTp == "IDF") & (b.XpryDt.astype(str) > d)].sort_values("XpryDt")
        f0 = fut.iloc[0]
        cmp(u, d, "f_fut_expiry", str(f0.XpryDt), r.f_fut_expiry)
        cmp(u, d, "f_fut_oi", f0.OpnIntrst, r.f_fut_oi)
        cmp(u, d, "f_fut_close", f0.ClsPric, r.f_fut_close)
        allf = b[(b.FinInstrmTp == "IDF") & (b.XpryDt.astype(str) >= d)]
        cmp(u, d, "f_futall_oi", allf.OpnIntrst.sum(), r.f_futall_oi)
        opt_exps = sorted(b[b.FinInstrmTp == "IDO"].XpryDt.astype(str).unique())
        near = [e for e in opt_exps if e > d][0]
        futexp = set(b[b.FinInstrmTp == "IDF"].XpryDt.astype(str))
        mon = [e for e in opt_exps if e > d and e in futexp][0]
        for tag, e in [("near", near), ("mon", mon)]:
            cmp(u, d, f"f_opt_{tag}_expiry", e, r[f"f_opt_{tag}_expiry"])
            pcr, mp, ties, atm, strad = opt_stats(b, e, D["c"])
            cmp(u, d, f"f_opt_{tag}_pcr_oi", pcr, r[f"f_opt_{tag}_pcr_oi"], 1e-9)
            cmp(u, d, f"f_opt_{tag}_maxpain", mp, r[f"f_opt_{tag}_maxpain"],
                note=f"ties={list(ties)}" if len(ties) > 1 else "")
            cmp(u, d, f"f_opt_{tag}_atm_strike", atm, r[f"f_opt_{tag}_atm_strike"])
            cmp(u, d, f"f_opt_{tag}_straddle_pct", strad, r[f"f_opt_{tag}_straddle_pct"], 1e-9)

res = pd.DataFrame(rows)
res.to_csv(f"{OUT}/numeric_checks.csv", index=False)
print(res.to_string(max_colwidth=40))
print("TOTAL", len(res), "MISMATCH", (~res.match).sum())
print(res[~res.match].to_string())
