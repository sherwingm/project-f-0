"""Skeptical review of the final test + tradeability (design: reports/lld/review_final.md).

Own code from raw files only; compares with results/final and results/tradeability. Writes results/review_final/.
Run from the repo root (Git Bash):
  INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe expiry_research/scripts/review_final_checks.py
"""
import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stats_utils as su  # noqa: E402

ROOT = os.path.dirname(HERE)
STORE = os.environ.get("INDEX_STORE", "../fo-index-data/data/index")
RES = os.path.join(ROOT, "results")
OUT = os.path.join(RES, "review_final")
os.makedirs(OUT, exist_ok=True)
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 300)

IDX = {"NIFTY": "NIFTY50", "BANKNIFTY": "NIFTYBANK"}
MONTHS = [f"{y}-{m:02d}" for y in (2024, 2025, 2026) for m in range(1, 13) if f"{y}-{m:02d}" <= "2026-10"]
MONTHS = [m for m in MONTHS if m >= "2024-03"]

# ---------------------------------------------------------------- raw: sessions, spot daily, bhavcopy
ses = pd.read_csv(os.path.join(ROOT, "data", "sessions_NIFTY.csv"), dtype=str)
SES = ses[(ses["is_special_session"] == "False") & (ses["date"] >= "2024-03-01")]["date"].tolist()
SI = {d: i for i, d in enumerate(SES)}


def spot_daily(ix):
    rows, dup = [], []
    for ym in MONTHS:
        p = os.path.join(STORE, "spot_1m", ix, f"{ym}.parquet")
        if not os.path.exists(p):
            continue
        s = pd.read_parquet(p, columns=["timestamp", "open", "high", "low", "close", "source"])
        ts = s["timestamp"].dt.tz_convert("Asia/Kolkata")
        s["day"] = ts.dt.strftime("%Y-%m-%d")
        s["hm"] = ts.dt.strftime("%H:%M")
        s = s[(s["hm"] >= "09:15") & (s["hm"] <= "15:29")]
        d = s.duplicated(["day", "hm"], keep=False)
        if d.any():
            g = s[d].groupby(["day", "hm"])
            x = g.agg(n=("open", "size"), o_rng=("open", lambda v: v.max() - v.min()),
                      c_rng=("close", lambda v: v.max() - v.min())).reset_index()
            x["ix"] = ix
            dup.append(x)
        s = s.drop_duplicates(["day", "hm"], keep="first").sort_values(["day", "hm"])
        g = s.groupby("day")
        rows.append(pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                                  "close": g["close"].last(), "n_bars": g.size(), "last_hm": g["hm"].last()}))
    D = pd.concat(rows)
    D = D[D.index.isin(SES)].reindex(SES)
    return D, (pd.concat(dup) if dup else pd.DataFrame())


def bhav(ul):
    fr = []
    for ym in MONTHS:
        p = os.path.join(STORE, "options_daily", ul, f"{ym}.parquet")
        if os.path.exists(p):
            fr.append(pd.read_parquet(p))
    b = pd.concat(fr, ignore_index=True)
    b["TradDt"] = b["TradDt"].astype(str).str[:10]
    b["XpryDt"] = b["XpryDt"].astype(str).str[:10]
    return b


def raw_features(ul):
    D, dup = spot_daily(IDX[ul])
    c, h, l, o = D["close"], D["high"], D["low"], D["open"]
    F = pd.DataFrame(index=D.index)
    F["close"] = c
    F["n_bars"] = D["n_bars"]
    F["o_cc"] = (c / c.shift(1) - 1) * 100
    F["f_mom5"] = (c / c.shift(5) - 1) * 100
    sg = np.sign(F["o_cc"]).fillna(0).values
    st = np.zeros(len(sg))
    for i in range(len(sg)):
        if sg[i] == 0:
            st[i] = 0
        elif i > 0 and np.sign(st[i - 1]) == sg[i]:
            st[i] = st[i - 1] + sg[i]
        else:
            st[i] = sg[i]
    F["f_streak_close"] = st
    pc = c.shift(1)
    tr = np.fmax(h - l, np.fmax((h - pc).abs(), (l - pc).abs()))
    F["f_atr14_pct"] = tr.rolling(14).mean() / c * 100
    # targets of t+1 (vs close t)
    hn, ln = h.shift(-1), l.shift(-1)
    F["y_max_exc"] = np.fmax((hn / c - 1) * 100, -(ln / c - 1) * 100)
    F["y_range_pct"] = (hn - ln) / c * 100
    F["y_low_pc"] = (ln / c - 1) * 100
    # bhavcopy
    B = bhav(ul)
    fut = B[(B["FinInstrmTp"] == "IDF") & (B["XpryDt"] > B["TradDt"])].sort_values(["TradDt", "XpryDt"])
    fv = fut.groupby("TradDt").head(1).set_index("TradDt")["TtlTradgVol"].astype(float).reindex(D.index)
    F["f_fut_vol_r20"] = fv / fv.shift(1).rolling(20, min_periods=15).mean()
    opt = B[(B["FinInstrmTp"] == "IDO") & (B["XpryDt"] > B["TradDt"])]
    near = opt.groupby("TradDt")["XpryDt"].min()
    out = {}
    for d in D.index:
        if d not in near.index or pd.isna(c[d]):
            continue
        e = near[d]
        g = opt[(opt["TradDt"] == d) & (opt["XpryDt"] == e)].drop_duplicates(["StrkPric", "OptnTp"])
        ce = g[g["OptnTp"] == "CE"].set_index("StrkPric")
        pe = g[g["OptnTp"] == "PE"].set_index("StrkPric")
        S = c[d]
        a = ce[(ce.index > S) & (ce["OpnIntrst"] > 0)]
        cw = a["OpnIntrst"].astype(float).sort_index().idxmax() if len(a) else np.nan
        b = pe[(pe.index < S) & (pe["OpnIntrst"] > 0)].sort_index(ascending=False)
        pw = b["OpnIntrst"].astype(float).idxmax() if len(b) else np.nan
        pcr = pe["OpnIntrst"].sum() / ce["OpnIntrst"].sum()
        K = sorted(set(ce.index) & set(pe.index))
        kv = [k for k in K if ce.loc[k, "SttlmPric"] > 0 and pe.loc[k, "SttlmPric"] > 0]
        katm = min(kv, key=lambda k: (abs(k - S), k)) if kv else np.nan
        strd = (ce.loc[katm, "SttlmPric"] + pe.loc[katm, "SttlmPric"]) / S * 100 if kv else np.nan
        dte = (pd.Timestamp(e) - pd.Timestamp(d)).days
        nsess = np.busday_count(np.datetime64(d, "D") + np.timedelta64(1, "D"), np.datetime64(e, "D") + np.timedelta64(1, "D"))
        tv = strd - abs(katm / S - 1) * 100
        out[d] = dict(expiry=e, callwall=cw, putwall=pw, pcr=pcr, atm=katm, straddle_pct=strd, dte=dte,
                      n_sess=nsess, iv_proxy=tv / 0.7979 / math.sqrt(max(nsess, 1)) * math.sqrt(252))
    O = pd.DataFrame(out).T.reindex(D.index)
    for k in O.columns:
        F[k] = O[k]
    cwd = (O["callwall"].astype(float) / c - 1) * 100
    pwd = (O["putwall"].astype(float) / c - 1) * 100
    F["wall_width"] = cwd - pwd
    F["wall_near"] = np.minimum(cwd, -pwd)
    F["d_opt_near_straddle_daily"] = O["straddle_pct"].astype(float) / np.sqrt(O["dte"].astype(float).clip(lower=1))
    same = O["expiry"].eq(O["expiry"].shift(1))
    F["iv_chg"] = (O["iv_proxy"].astype(float) - O["iv_proxy"].astype(float).shift(1)).where(same)
    F["f_opt_near_pcr_oi"] = O["pcr"].astype(float)
    return F, dup


CANDS = {  # id: (ul, feature col in my frame, op, threshold, target kind, feature2 rule)
    "PPC032": ("NIFTY", "f_mom5", "<=", -1.3828258481362399, "big_exc", None),
    "PPC062": ("NIFTY", "f_streak_close", ">=", 3.0, "big_exc", None),
    "PPC092": ("BANKNIFTY", "o_cc", "<=", -0.9087533825375083, "big_exc", None),
    "PPC098": ("BANKNIFTY", "f_mom5", "<=", -2.116335470530819, "big_exc", None),
    "PPC129": ("BANKNIFTY", "f_fut_vol_r20", ">=", 1.210769328253805, "big_exc", None),
    "OC08": ("BANKNIFTY", "wall_width", ">=", 5.289397, "range_big", None),
    "OC13": ("NIFTY", "wall_near", ">=", 1.834408, "range_big", None),
    "OC17": ("NIFTY", "wall_width", ">=", 6.037371, "range_big", None),
    "OC21": ("NIFTY", "wall_near", ">=", 1.834408, "big_exc", None),
    "OC118": ("BANKNIFTY", "iv_chg", ">=", 0.651378, "range_big", None),
    "M143": ("NIFTY", "d_opt_near_straddle_daily", ">=", 0.7671357712351159, "big_exc", None),
    "M218": ("NIFTY", "d_opt_near_straddle_daily", "<=", 0.6674562366087547, "low_pc",
             ("f_opt_near_pcr_oi", ">", 1.0061658482556393)),
    "M220": ("NIFTY", "f_atr14_pct", "<=", 1.2314184064646032, "low_pc", ("f_opt_near_pcr_oi", ">", 1.0061658482556393)),
}
RMED = {"NIFTY": 1.028672, "BANKNIFTY": 1.461234}
OPS = {"<=": np.less_equal, ">=": np.greater_equal, ">": np.greater, "<": np.less}


def part1():
    print("== 1. features / flags / targets recomputed from raw (5 sessions per candidate) ==")
    RF, DUPS = {}, []
    for ul in ["NIFTY", "BANKNIFTY"]:
        RF[ul], dp = raw_features(ul)
        if len(dp):
            DUPS.append(dp)
    FL = {ul: pd.read_csv(os.path.join(RES, "final", f"flags_{ul}.csv"), dtype={"date": str, "y_date": str})
          for ul in RF}
    rng = np.random.default_rng(20261105)
    rows = []
    for cid, (ul, col, op, thr, tk, f2) in CANDS.items():
        fl = FL[ul].dropna(subset=[f"{cid}_flag"]).copy()
        fl["dist"] = (fl[f"{cid}_feature"] - thr).abs()
        fg = fl[fl[f"{cid}_flag"] == 1]
        ufg = fl[fl[f"{cid}_flag"] == 0]
        pick = list(rng.choice(fg["date"].values, 2, replace=False))
        pick += list(fg.sort_values("dist")["date"].head(1))
        pick += list(ufg.sort_values("dist")["date"].head(2))
        for d in pick:
            r = fl[fl["date"] == d].iloc[0]
            x = RF[ul].loc[d]
            mine_f = float(x[col])
            mine_flag = bool(OPS[op](mine_f, thr))
            if f2:
                mine_flag = mine_flag and bool(OPS[f2[1]](float(x[f2[0]]), f2[2]))
            if tk == "big_exc":
                mine_y = float(x["y_max_exc"] >= 1)
            elif tk == "range_big":
                mine_y = float(x["y_range_pct"] > RMED[ul])
            else:
                mine_y = float(x["y_low_pc"])
            their_f, their_flag, their_y = float(r[f"{cid}_feature"]), bool(r[f"{cid}_flag"]), float(r[f"{cid}_target"])
            f_ok = math.isclose(mine_f, their_f, rel_tol=1e-6, abs_tol=1e-9)
            y_ok = math.isclose(mine_y, their_y, rel_tol=1e-6, abs_tol=1e-9)
            row = dict(cid=cid, ul=ul, date=d, y_date=r["y_date"], feature=col, mine=mine_f, theirs=their_f,
                       feat_ok=f_ok, flag_mine=mine_flag, flag_theirs=their_flag, flag_ok=mine_flag == their_flag,
                       y_mine=mine_y, y_theirs=their_y, y_ok=y_ok, n_bars_t=x["n_bars"])
            if f2:
                row["f2_mine"], row["f2_theirs"] = float(x[f2[0]]), float(r[f"{cid}_feature2"])
                row["feat_ok"] = f_ok and math.isclose(row["f2_mine"], row["f2_theirs"], rel_tol=1e-6)
            rows.append(row)
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(OUT, "feature_recompute.csv"), index=False)
    print(R.round(5).to_string(index=False))
    print(f"feature ok {R.feat_ok.sum()}/{len(R)}, flag ok {R.flag_ok.sum()}/{len(R)}, target ok {R.y_ok.sum()}/{len(R)}")
    # whole-period flag agreement (all final rows) as a wider check
    agg = []
    for cid, (ul, col, op, thr, tk, f2) in CANDS.items():
        fl = FL[ul].dropna(subset=[f"{cid}_flag"])
        x = RF[ul].reindex(fl["date"])
        mf = OPS[op](x[col].values.astype(float), thr)
        if f2:
            mf = mf & OPS[f2[1]](x[f2[0]].values.astype(float), f2[2])
        ok = x[col].notna().values
        agg.append(dict(cid=cid, rows=len(fl), mine_present=int(ok.sum()),
                        flag_agree=int((mf[ok] == fl[f"{cid}_flag"].values[ok].astype(bool)).sum()),
                        feat_maxdiff=float(np.nanmax(np.abs(x[col].values.astype(float) - fl[f"{cid}_feature"].values)))))
    A = pd.DataFrame(agg)
    A.to_csv(os.path.join(OUT, "flag_agreement_all_rows.csv"), index=False)
    print(A.to_string(index=False))
    if DUPS:
        Dp = pd.concat(DUPS)
        Dp.to_csv(os.path.join(OUT, "spot_duplicate_minutes.csv"), index=False)
        f = Dp[Dp["day"] >= "2024-07-01"]
        print(f"spot duplicate minutes (final period): {len(f)}; open differs on {(f.o_rng > 0).sum()}, "
              f"close differs on {(f.c_rng > 0).sum()}; 09:15 dups {(f.hm == '09:15').sum()}")
    return RF


def part2():
    print("\n== 2. gates and BH recomputed ==")
    R = pd.read_csv(os.path.join(RES, "final", "final_results.csv"))
    q, rej = su.bh(R["fin_p_one_sided"].values, 0.10)
    # independent BH
    p = R["fin_p_one_sided"].values
    m = len(p)
    o = np.argsort(p)
    qq = np.empty(m)
    run = 1.0
    for j in range(m - 1, -1, -1):
        run = min(run, p[o[j]] * m / (j + 1))
        qq[o[j]] = run
    FL = {ul: pd.read_csv(os.path.join(RES, "final", f"flags_{ul}.csv"), dtype={"date": str}) for ul in
          ["NIFTY", "BANKNIFTY"]}
    out = []
    for _, r in R.iterrows():
        cid = r["id"]
        fl = FL[r["ul"]].dropna(subset=[f"{cid}_flag", f"{cid}_target"])
        y = fl[f"{cid}_target"].values
        f = fl[f"{cid}_flag"].values == 1
        d = np.sign(r["disc_effect"])
        alt = "greater" if d > 0 else "less"
        if CANDS[cid][4] == "low_pc":
            rate, base = y[f].mean(), y.mean()
            pv = stats.ttest_1samp(y[f], base, alternative=alt).pvalue
            k = np.nan
        else:
            k, n = int(y[f].sum()), int(f.sum())
            rate, base = k / n, y.mean()
            pv = stats.binomtest(k, n, base, alternative=alt).pvalue
        eff = rate - base
        g1 = (np.sign(eff) == d) and pv < 0.05 and abs(eff) >= 0.5 * abs(r["disc_effect"])
        out.append(dict(id=cid, n=int(f.sum()), k=k, rows=len(fl), rate=rate, base=base, eff=eff,
                        half_disc=0.5 * abs(r["disc_effect"]), p=pv, p_ok=math.isclose(pv, r["fin_p_one_sided"],
                                                                                         rel_tol=1e-9),
                        n_ok=int(f.sum()) == r["fin_n"], gate1=g1, gate1_ok=g1 == r["gate1"], q=qq[_],
                        q_ok=math.isclose(qq[_], r["bh_q"], rel_tol=1e-9),
                        label=("Validated (size)" if g1 and qq[_] <= 0.10 else "Rejected"),
                        label_ok=("Validated (size)" if g1 and qq[_] <= 0.10 else "Rejected") == r["label"]))
    G = pd.DataFrame(out)
    G.to_csv(os.path.join(OUT, "gate_recompute.csv"), index=False)
    print(G.round(5).to_string(index=False))
    # OC13 vs OC21 identical flags
    fn = FL["NIFTY"]
    print("OC13 flags == OC21 flags:", bool((fn["OC13_flag"].fillna(-1) == fn["OC21_flag"].fillna(-1)).all()))
    # BH without the duplicate OC21 (12 tests) and with PPC062 margin
    keep = R["id"] != "OC21"
    q12, _ = su.bh(R.loc[keep, "fin_p_one_sided"].values, 0.10)
    print("BH q without OC21:", dict(zip(R.loc[keep, "id"], np.round(q12, 4))))


# ---------------------------------------------------------------- 3. fills by hand
OPT_BROKERAGE, OPT_STT, NSE_LAKH, SEBI_CR, STAMP, GST = 20.0, 0.15, 35.53, 10.0, 0.003, 18.0


def leg(side, qty, px):
    v = qty * px
    parts = [OPT_BROKERAGE, OPT_STT / 100 * v if side == "SELL" else 0.0, NSE_LAKH * v / 1e5, SEBI_CR * v / 1e7,
             STAMP / 100 * v if side == "BUY" else 0.0, GST / 100 * (OPT_BROKERAGE + NSE_LAKH * v / 1e5 + SEBI_CR * v / 1e7)]
    return round(sum(round(x, 2) for x in parts), 2)


def opt_raw(e, d):
    p = os.path.join(STORE, "options_1m", "NIFTY", e, f"{d}.parquet")
    if not os.path.exists(p):
        return None
    x = pd.read_parquet(p)
    x["hm"] = x["timestamp"].dt.tz_convert("Asia/Kolkata").dt.strftime("%H:%M")
    return x


def px(x, K, t, hm):
    y = x[(x["strike"] == K) & (x["option_type"] == t) & (x["hm"] == hm) & (x["close"] > 0)]
    if len(y) > 1:
        y = y[y["source"] == "upstox"] if (y["source"] == "upstox").any() else y
    return float(y["close"].iloc[0]) if len(y) else np.nan


def part3():
    print("\n== 3. eight trades recomputed by hand from options_1m ==")
    T = pd.read_csv(os.path.join(RES, "tradeability", "trades.csv"), dtype={"trade_date": str, "expiry": str,
                                                                          "signal_date": str, "exit_date": str})
    cal = pd.read_csv(os.path.join(ROOT, "data", "expiry_calendar.csv"), dtype=str)
    EXP = sorted(cal[cal["underlying"] == "NIFTY"]["expiry_date"].unique())
    rng = np.random.default_rng(7)
    picks = []
    sel = [("a", "i_1515", "D0", None), ("a", "ii_tgt20", "D0", "hit"), ("b", "iii_d2_0916", "other", None),
           ("a", "i_1515", "other", None), ("b", "ii_tgt20", "D-1", "hit"), ("a", "iii_d2_0916", "D-1", None),
           ("b", "i_1515", "D0", None), ("a", "ii_tgt20", "other", "miss")]
    for ech, ex, cx, tg in sel:
        g = T[(T.exp_choice == ech) & (T.exit == ex) & (T.ctx == cx)]
        if tg == "hit":
            g = g[g.exit_hm != "15:15"]
        elif tg == "miss":
            g = g[g.exit_hm == "15:15"]
        picks.append(g.iloc[int(rng.integers(len(g)))])
    # plus the worst D0 trade the report names
    w = T[(T.exp_choice == "a") & (T.ctx == "D0") & (T.exit == "ii_tgt20")].sort_values("net_0.5").iloc[0]
    picks.append(w)
    rows = []
    sp_cache = {}
    for r in picks:
        d, e = r["trade_date"], r["expiry"]
        ym = d[:7]
        if ym not in sp_cache:
            s = pd.read_parquet(os.path.join(STORE, "spot_1m", "NIFTY50", f"{ym}.parquet"))
            ts = s["timestamp"].dt.tz_convert("Asia/Kolkata")
            s["day"], s["hm"] = ts.dt.strftime("%Y-%m-%d"), ts.dt.strftime("%H:%M")
            sp_cache[ym] = s
        s = sp_cache[ym]
        o915 = s[(s.day == d) & (s.hm == "09:15")]
        so = float(o915["open"].iloc[0])
        K = round(so / 50) * 50 if abs(so / 50 - math.floor(so / 50) - 0.5) > 1e-12 else math.floor(so / 50) * 50
        ea = next(x for x in EXP if x >= d)
        eb = next(x for x in EXP if x > d)
        e_mine = ea if r["exp_choice"] == "a" else eb
        x = opt_raw(e, d)
        ce0, pe0 = px(x, K, "CE", "09:16"), px(x, K, "PE", "09:16")
        ent = ce0 + pe0
        # path / exit
        if r["exit"] == "iii_d2_0916":
            d2 = r["exit_date"]
            x2 = opt_raw(e, d2)
            ce1, pe1, hm_out = px(x2, K, "CE", "09:16"), px(x2, K, "PE", "09:16"), "09:16"
            hms = sorted(x[(x.hm >= "09:17") & (x.hm <= "15:29")]["hm"].unique())
            path = [px(x, K, "CE", h) + px(x, K, "PE", h) for h in hms] + [px(x2, K, "CE", h) + px(x2, K, "PE", h)
                                                                           for h in ["09:15", "09:16"]]
        else:
            hms = sorted(x[(x.hm >= "09:17") & (x.hm <= "15:15")]["hm"].unique())
            path, hm_out = [], "15:15"
            for h in hms:
                v = px(x, K, "CE", h) + px(x, K, "PE", h)
                path.append(v)
                if r["exit"] == "ii_tgt20" and v >= 1.2 * ent - 1e-9:
                    hm_out = h
                    break
            ce1, pe1 = px(x, K, "CE", hm_out), px(x, K, "PE", hm_out)
        path = np.array([v for v in path if not np.isnan(v)])
        mx = (path.max() / ent - 1) * 100
        lot = r["lot"]
        si = (1.0 if True else 0.5) / 100  # 09:16 entry is before 09:30: 2 x 0.5 %
        so_ = (1.0 if (hm_out < "09:30" or hm_out >= "15:00") else 0.5) / 100
        bce, bpe, sce, spe = ce0 * (1 + si), pe0 * (1 + si), ce1 * (1 - so_), pe1 * (1 - so_)
        ch = leg("BUY", lot, bce) + leg("BUY", lot, bpe) + leg("SELL", lot, sce) + leg("SELL", lot, spe)
        cost = lot * (bce + bpe)
        net = (lot * (sce + spe) - cost - ch) / cost * 100
        rows.append(dict(trade_date=d, ctx=r["ctx"], exp_choice=r["exp_choice"], exit=r["exit"], spot_0915=so,
                         K=K, K_theirs=r["strike"], expiry=e_mine, expiry_theirs=e, ce_in=ce0, ce_in_t=r["ce_in"],
                         pe_in=pe0, pe_in_t=r["pe_in"], exit_hm=hm_out, exit_hm_t=r["exit_hm"], ce_out=ce1,
                         ce_out_t=r["ce_out"], pe_out=pe1, pe_out_t=r["pe_out"], charges=round(ch, 2),
                         charges_t=r["charges_0.5"], net=net, net_t=r["net_0.5"], maxup=mx, maxup_t=r["maxup_pct"],
                         ok=bool(K == r["strike"] and e_mine == e and math.isclose(net, r["net_0.5"], abs_tol=1e-6)
                                 and math.isclose(mx, r["maxup_pct"], abs_tol=1e-6) and hm_out == r["exit_hm"])))
    H = pd.DataFrame(rows)
    H.to_csv(os.path.join(OUT, "fills_by_hand.csv"), index=False)
    print(H.round(4).T.to_string())
    print("all fills ok:", bool(H.ok.all()))


def part4():
    print("\n== 4. look-ahead / timing ==")
    T = pd.read_csv(os.path.join(RES, "tradeability", "trades.csv"), dtype=str)
    print("trade_date > signal_date on all rows:", bool((T.trade_date > T.signal_date).all()))
    print("exit_date >= trade_date:", bool((T.exit_date >= T.trade_date).all()))
    ih = T[T.exit == "ii_tgt20"]["exit_hm"]
    print("target exits before 09:17:", int((ih < "09:17").sum()), "; distribution of first hits (top):",
          ih[ih != "15:15"].value_counts().head(5).to_dict())
    # spot 09:15 duplicates: would the strike change with the other source?
    chg = []
    for d in sorted(T.trade_date.unique()):
        s = pd.read_parquet(os.path.join(STORE, "spot_1m", "NIFTY50", f"{d[:7]}.parquet"))
        ts = s["timestamp"].dt.tz_convert("Asia/Kolkata")
        x = s[(ts.dt.strftime("%Y-%m-%d") == d) & (ts.dt.strftime("%H:%M") == "09:15")]
        if len(x) > 1:
            ks = sorted(set((np.floor(x["open"] / 50 + 0.5) * 50).tolist()))
            chg.append(dict(date=d, n=len(x), opens=x["open"].tolist(), sources=x["source"].tolist(), strikes=ks))
    C = pd.DataFrame(chg)
    print("trade days with >1 spot 09:15 row:", len(C), "; of these strike ambiguous:",
          int((C["strikes"].apply(len) > 1).sum()) if len(C) else 0)
    if len(C):
        C.to_csv(os.path.join(OUT, "spot_0915_duplicates.csv"), index=False)
        print(C.head(10).to_string(index=False))


def part5():
    print("\n== 5. claim checks ==")
    SG = pd.read_csv(os.path.join(RES, "tradeability", "summary_signals.csv"))
    EF = pd.read_csv(os.path.join(RES, "tradeability", "summary_expiry.csv"))
    pos = SG[SG["mean"] > 0][["exp_choice", "exit", "slip", "group", "n", "mean", "t"]]
    print("positive mean cells in summary_signals (any group):")
    print(pos.round(3).to_string(index=False))
    pe = EF[EF["mean"] > 0][["exp_choice", "exit", "slip", "group", "n", "mean", "t"]]
    print("positive mean cells in summary_expiry:")
    print(pe.round(3).to_string(index=False))
    T = pd.read_csv(os.path.join(RES, "tradeability", "trades.csv"))
    d0 = T[(T.exp_choice == "a") & (T.ctx == "D0") & (T.exit == "i_1515")]
    print(f"D0 same-day 15:15: n {len(d0)}, maxup>=100 {int((d0.maxup_pct >= 100).sum())}, mean maxup "
          f"{d0.maxup_pct.mean():.1f}, median {d0.maxup_pct.median():.1f}, mean net {d0['net_0.5'].mean():.2f}, "
          f"median net {d0['net_0.5'].median():.2f}, mean maxup_net {d0['maxup_net_0.5'].mean():.1f}")
    # among D0 trades that reached +100 %, what was the 15:15 result?
    h = d0[d0.maxup_pct >= 100]
    print(f"  of those reaching +100 %: mean net at 15:15 {h['net_0.5'].mean():.1f}, positive {int((h['net_0.5'] > 0).sum())}")
    # time-of-day of the D0 max
    d0t = T[(T.exp_choice == "a") & (T.ctx == "D0") & (T.exit == "ii_tgt20")]
    print(f"D0 +20 % target: n {len(d0t)}, hit {int((d0t.exit_hm != '15:15').sum())}, win {(d0t['net_0.5'] > 0).mean():.3f},"
          f" mean {d0t['net_0.5'].mean():.2f}, median {d0t['net_0.5'].median():.2f}, worst {d0t['net_0.5'].min():.1f}")
    # premium size on D0 (charges share)
    print(f"D0 same-day premium Rs median {d0.prem_in_rs.median():.0f}, charges median {d0['charges_0.5'].median():.1f}")


if __name__ == "__main__" and len(sys.argv) == 1:
    part1()
    part2()
    part3()
    part4()
    part5()


def part6():
    """VIX-stratified effect (final-period VIX quintiles of t): flagged minus unflagged inside each stratum,
    weighted by flagged count; permutation p within strata (2000 shuffles of flags inside each stratum)."""
    print("\n== 6. effect inside final-period VIX quintiles (check of the 'beyond VIX' claim) ==")
    R = pd.read_csv(os.path.join(RES, "final", "final_results.csv")).set_index("id")
    rng = np.random.default_rng(11)
    out = []
    for cid, (ul, *_rest) in CANDS.items():
        fl = pd.read_csv(os.path.join(RES, "final", f"flags_{ul}.csv")).dropna(subset=[f"{cid}_flag", f"{cid}_target",
                                                                                         "f_vix_close"])
        fl["st"] = pd.qcut(fl["f_vix_close"], 5, labels=False)
        y, f, st = fl[f"{cid}_target"].values, fl[f"{cid}_flag"].values == 1, fl["st"].values

        def eff(fm):
            num, w = 0.0, 0
            for s in range(5):
                m = st == s
                a, b = y[m & fm], y[m & ~fm]
                if len(a) and len(b):
                    num += len(a) * (a.mean() - b.mean())
                    w += len(a)
            return num / w if w else np.nan
        e0 = eff(f)
        null = []
        for _ in range(2000):
            g = f.copy()
            for s in range(5):
                m = np.where(st == s)[0]
                g[m] = rng.permutation(g[m])
            null.append(eff(g))
        null = np.array(null)
        d = np.sign(R.loc[cid, "disc_effect"])
        p = (1 + np.sum(d * null >= d * e0)) / 2001
        out.append(dict(id=cid, label=R.loc[cid, "label"], raw_effect=R.loc[cid, "fin_effect"],
                        resid_diff_logit=R.loc[cid, "resid_diff"], vix_strat_effect=e0, p_perm_one_sided=p,
                        flags_in_top_quintile=int((f & (st == 4)).sum()), n_flag=int(f.sum())))
    V = pd.DataFrame(out)
    V.to_csv(os.path.join(OUT, "vix_stratified.csv"), index=False)
    print(V.round(4).to_string(index=False))


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "part6":
    part6()
