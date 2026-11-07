"""Full-sample vectorised recompute of daily OHLC, gaps, y_ret30, y_gap_filled, fut OI, near PCR / straddle / maxpain."""
import sys, os, glob
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np, pandas as pd
S = os.environ.get("INDEX_STORE", "../fo-index-data/data/index")
OUT = "expiry_research/results/verify"
SPOT = {"NIFTY": "NIFTY50", "BANKNIFTY": "NIFTYBANK"}
BAD = {"2021-11-04", "2021-11-10", "2022-03-07"}
idx = pd.read_parquet(f"{S}/index_close_daily.parquet"); idx["date"] = idx.date.astype(str)
summ = []; bad_rows = []
for u in ["NIFTY", "BANKNIFTY"]:
    P = pd.read_parquet(f"expiry_research/data/panel_{u}.parquet"); P["date"] = P.date.astype(str)
    m = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{S}/spot_1m/{SPOT[u]}/*.parquet"))])
    m["ts"] = m.timestamp.dt.tz_convert("Asia/Kolkata"); m["d"] = m.ts.dt.strftime("%Y-%m-%d"); m["hm"] = m.ts.dt.strftime("%H:%M")
    m = m[(m.hm >= "09:15") & (m.hm <= "15:29")].sort_values("ts")
    g = m.groupby("d")
    md = pd.DataFrame({"o": g.open.first(), "h": g.high.max(), "l": g.low.min(),
                       "c": m[m.hm == "15:29"].groupby("d").close.last(),
                       "c944": m[m.hm == "09:44"].groupby("d").close.last(), "t0": g.hm.first()})
    off = idx[idx["index"] == SPOT[u]].set_index("date")[["open", "high", "low", "close"]].rename(columns=dict(open="o", high="h", low="l", close="c"))
    rows = []
    for d in P.date:
        if d >= "2021-10-20" and d not in BAD and d in md.index:
            r = md.loc[d]; rows.append((d, "spot_1m", r.o, r.h, r.l, r.c, r.c944, r.t0))
        elif d in off.index:
            r = off.loc[d]; rows.append((d, "index_close_daily", r.o, r.h, r.l, r.c, np.nan, None))
        else:
            rows.append((d, "none", np.nan, np.nan, np.nan, np.nan, np.nan, None))
    M = pd.DataFrame(rows, columns=["date", "src", "o", "h", "l", "c", "c944", "t0"])
    M["prev_c"] = M.c.shift(1)
    M["gap"] = (M.o / M.prev_c - 1) * 100
    M["ret30"] = np.where(M.src == "spot_1m", (M.c944 / M.o - 1) * 100, np.nan)
    gp = M.o - M.prev_c
    M["filled"] = np.where(gp > 0, M.l <= M.prev_c, np.where(gp < 0, M.h >= M.prev_c, np.nan))
    M.loc[gp.isna(), "filled"] = np.nan
    M["v_ygap"] = M.gap.shift(-1); M["v_yret30"] = M.ret30.shift(-1); M["v_yfilled"] = M.filled.shift(-1)
    J = P.merge(M, on="date")
    def chk(name, a, b, tol=1e-9):
        a = pd.to_numeric(pd.Series(np.asarray(a)), errors="coerce").astype(float); b = pd.to_numeric(pd.Series(np.asarray(b)), errors="coerce").astype(float)
        both_na = a.isna() & b.isna(); close = (a - b).abs() <= tol * np.maximum(1, b.abs())
        ok = both_na | close
        summ.append(dict(underlying=u, field=name, n=len(a), n_nonnull_panel=int(b.notna().sum()), mismatches=int((~ok).sum())))
        for i in np.where(~ok)[0][:20]:
            bad_rows.append(dict(underlying=u, field=name, date=J.date.iloc[i], mine=a.iloc[i], panel=b.iloc[i]))
    chk("src==", (J.src_x == J.src_y).astype(float), pd.Series(1.0, index=J.index))
    for k, c in [("o", "px_open"), ("h", "px_high"), ("l", "px_low"), ("c", "px_close")]:
        chk(c, J[k], J[c])
    chk("o_gap_pct", J.gap, J.o_gap_pct); chk("y_gap_pct", J.v_ygap, J.y_gap_pct)
    chk("o_ret30", J.ret30, J.o_ret30); chk("y_ret30", J.v_yret30, J.y_ret30)
    chk("y_gap_filled", J.v_yfilled, J.y_gap_filled.astype(float))
    print(u, "first minute bar not 09:15 on", int((M.t0.notna() & (M.t0 != "09:15")).sum()), "days")
    # bhavcopy
    B = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{S}/options_daily/{u}/*.parquet"))])
    B["TradDt"] = B.TradDt.astype(str); B["XpryDt"] = B.XpryDt.astype(str)
    F = B[(B.FinInstrmTp == "IDF") & (B.XpryDt > B.TradDt)].sort_values(["TradDt", "XpryDt"]).groupby("TradDt").first()
    J2 = P.set_index("date").join(F[["OpnIntrst", "XpryDt"]])
    chk("f_fut_oi", J2.OpnIntrst.values, J2.f_fut_oi.values)
    O = B[B.FinInstrmTp == "IDO"]
    near = O[O.XpryDt > O.TradDt].groupby("TradDt").XpryDt.min()
    pcr, mp, strad, atm = {}, {}, {}, {}
    pc = P.set_index("date").px_close
    for (d, e), x in O[O.XpryDt > O.TradDt].merge(near.rename("ne"), left_on="TradDt", right_index=True).query("XpryDt == ne").groupby(["TradDt", "XpryDt"]):
        ce = x[x.OptnTp == "CE"].groupby("StrkPric").agg(oi=("OpnIntrst", "sum"), st=("SttlmPric", "max"))
        pe = x[x.OptnTp == "PE"].groupby("StrkPric").agg(oi=("OpnIntrst", "sum"), st=("SttlmPric", "max"))
        pcr[d] = pe.oi.sum() / ce.oi.sum() if ce.oi.sum() > 0 else np.nan
        j = ce.join(pe, lsuffix="_ce", rsuffix="_pe", how="outer").fillna({"oi_ce": 0, "oi_pe": 0})
        K = j.index.values; KK = K[:, None]
        pay = (j.oi_ce.values[None, :] * np.maximum(KK - K[None, :], 0)).sum(1) + (j.oi_pe.values[None, :] * np.maximum(K[None, :] - KK, 0)).sum(1)
        mp[d] = K[np.argmin(pay)] if (j.oi_ce.sum() + j.oi_pe.sum()) > 0 else np.nan
        if d in pc.index and not np.isnan(pc[d]):
            both = j[(j.st_ce > 0) & (j.st_pe > 0)]
            if len(both):
                a = both.index.values[np.argmin(np.abs(both.index.values - pc[d]))]
                atm[d] = a; strad[d] = (both.loc[a, "st_ce"] + both.loc[a, "st_pe"]) / pc[d] * 100
    Pi = P.set_index("date")
    chk("f_opt_near_expiry==", pd.Series([float(str(near.get(d)) == str(v)) if d in near.index else float(pd.isna(v)) for d, v in Pi.f_opt_near_expiry.items()]), pd.Series(1.0, index=range(len(Pi))))
    chk("f_opt_near_pcr_oi", pd.Series(pcr).reindex(Pi.index).values, Pi.f_opt_near_pcr_oi.values)
    chk("f_opt_near_maxpain", pd.Series(mp).reindex(Pi.index).values, Pi.f_opt_near_maxpain.values)
    chk("f_opt_near_atm_strike", pd.Series(atm).reindex(Pi.index).values, Pi.f_opt_near_atm_strike.values)
    chk("f_opt_near_straddle_pct", pd.Series(strad).reindex(Pi.index).values, Pi.f_opt_near_straddle_pct.values)
s = pd.DataFrame(summ); s.to_csv(f"{OUT}/fullsample_summary.csv", index=False); print(s.to_string())
b = pd.DataFrame(bad_rows); b.to_csv(f"{OUT}/fullsample_mismatches.csv", index=False); print(b.to_string())
