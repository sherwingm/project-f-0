"""Leak-free daily panels (see reports/lld/panel.md).

Run from the repo root:
    INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe expiry_research/scripts/build_panel.py
Writes expiry_research/data/panel_{NIFTY,BANKNIFTY,SENSEX}.parquet (discovery + validation only),
data/sealed/panel_<UL>_final.parquet (final period, coordinator only), data/panel_dictionary.csv,
results/panel_summary.csv, results/panel_reconcile.csv, results/panel_gaps.csv, data/sealed/panel_gaps_final.csv.
Research code reads panels through scripts/panel_io.py, never the sealed files.

Importable: load_raw_all() -> raws, build_all(raws) -> {ul: panel}. The leakage test cuts the raws and rebuilds.
"""
import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import warnings

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
STORE = Path(os.environ.get("INDEX_STORE", "../fo-index-data/data/index"))
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RES = ROOT / "results"

ULS = ["NIFTY", "BANKNIFTY", "SENSEX"]
IDX = {"NIFTY": "NIFTY50", "BANKNIFTY": "NIFTYBANK", "SENSEX": "SENSEX"}
# Data-error days from reports/DATA_AUDIT.md (minute bars wrong or incomplete), per minute series; not market
# information. 2022-03-07: NIFTY50 / NIFTYBANK hold a bad high (+2.5 % one-bar spike); SENSEX that day is clean.
BAD_MINUTE_DAYS = {"NIFTY50": {"2021-11-04", "2021-11-10", "2022-03-07"},
                   "NIFTYBANK": {"2021-11-04", "2021-11-10", "2022-03-07"},
                   "SENSEX": {"2021-11-04", "2021-11-10"},
                   "INDIAVIX": {"2021-11-04", "2021-11-10"}}
VIX_MIN_CLEAN_FROM = "2023-08-23"      # VIX minute values before this have x100 / 100 unit errors (audit)
SENSEX_FIRST = "2021-10-20"
SPLITS = [("discovery", "2018-01-01", "2022-12-31"), ("validation", "2023-01-01", "2024-06-30"),
          ("final", "2024-07-01", "2099-12-31")]
FINAL_START = "2024-07-01"
SEALED = DATA / "sealed"
FLAT_GAP = 0.1                         # percent
BIG = 1.0                              # percent
M_1514 = 359                           # minutes after 09:15 of the 15:14 bar
M_1529 = 374
BHAV_COLS = ["TradDt", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "SttlmPric", "OpnIntrst",
             "ChngInOpnIntrst", "TtlTradgVol"]


# ======================================================================== loading (raw, untouched)
def load_minutes(ix):
    frames = [pq.read_table(f, columns=["timestamp", "open", "high", "low", "close"]).to_pandas()
              for f in sorted(glob.glob(str(STORE / f"spot_1m/{ix}/*.parquet")))]
    d = pd.concat(frames, ignore_index=True)
    ts = d["timestamp"].dt.tz_convert("Asia/Kolkata")
    d["date"] = ts.dt.strftime("%Y-%m-%d")
    d["mins"] = (ts.dt.hour * 60 + ts.dt.minute - 555).astype(int)
    d = d[(d["mins"] >= 0) & (d["mins"] <= M_1529)]
    d = d.sort_values(["date", "mins"]).drop_duplicates(["date", "mins"], keep="first")
    return d[["date", "mins", "open", "high", "low", "close"]].reset_index(drop=True)


def load_bhav(ul):
    frames = [pq.read_table(f, columns=BHAV_COLS).to_pandas()
              for f in sorted(glob.glob(str(STORE / f"options_daily/{ul}/*.parquet")))]
    b = pd.concat(frames, ignore_index=True)
    b = b[b["FinInstrmTp"].isin(["IDF", "IDO"])]
    return b.reset_index(drop=True)


def load_raw_all():
    icd = pd.read_parquet(STORE / "index_close_daily.parquet")
    vixd = pd.read_parquet(STORE / "vix_daily.parquet", columns=["date", "close"])
    sess = {ul: pd.read_csv(DATA / f"sessions_{ul}.csv", dtype={"date": str}) for ul in ULS}
    special = set(pd.read_csv(DATA / "special_sessions.csv", dtype={"date": str})["date"])
    cal = pd.read_csv(DATA / "expiry_calendar.csv", dtype={"expiry_date": str})
    raws = {"vixd": vixd, "icd_vix": icd[icd["index"] == "INDIAVIX"][["date", "close"]].reset_index(drop=True),
            "vixmin": load_minutes("INDIAVIX"), "special": special, "cal": cal}
    for ul in ULS:
        raws[ul] = {"min": load_minutes(IDX[ul]),
                    "icd": icd[icd["index"] == IDX[ul]][["date", "open", "high", "low", "close"]].reset_index(drop=True),
                    "bhav": load_bhav(ul) if ul != "SENSEX" else None,
                    "sess": sess[ul]}
    raws["nse_sess"] = sess["NIFTY"]
    return raws


# ======================================================================== daily OHLC + session outcomes
def minute_daily(m, bad=frozenset()):
    g = m.groupby("date", sort=True)
    d = pd.DataFrame({"n_bars": g.size(), "first_min": g["mins"].min(), "last_min": g["mins"].max(),
                      "m_open": g["open"].first(), "m_high": g["high"].max(), "m_low": g["low"].min(),
                      "m_close": g["close"].last()})
    d["m_ok"] = ((d["n_bars"] >= 370) & (d["first_min"] == 0) & (d["last_min"] == M_1529)
                 & ~d.index.isin(bad))
    return d


def asof_close(m, cutoff):
    """Close of the last bar at or before `cutoff` minutes after 09:15, per date (within the day only)."""
    return m[m["mins"] <= cutoff].groupby("date")["close"].last()


def minute_outcomes(m, prev_close):
    """Path outcomes of each minute day (ret15/30/60, last hour, rv, high/low minute, gap fill minute)."""
    g = m.groupby("date", sort=True)
    o = pd.DataFrame(index=g.size().index)
    op = g["open"].first()
    for k, cut in [("ret15", 14), ("ret30", 29), ("ret60", 59)]:
        o[k] = (asof_close(m, cut) / op - 1) * 100
    o["last_hour"] = (g["close"].last() / asof_close(m, 314) - 1) * 100
    lr = np.log(m["close"] / m.groupby("date")["close"].shift(1))
    first = m["mins"].eq(g["mins"].transform("min"))
    lr = lr.where(~first, np.log(m["close"] / m["open"]))
    o["rv"] = np.sqrt((lr ** 2).groupby(m["date"]).sum()) * 100
    o["high_min"] = m.loc[g["high"].idxmax(), ["date", "mins"]].set_index("date")["mins"]
    o["low_min"] = m.loc[g["low"].idxmin(), ["date", "mins"]].set_index("date")["mins"]
    pc = m["date"].map(prev_close)
    up = op.reindex(m["date"]).to_numpy() > pc.to_numpy()
    dn = op.reindex(m["date"]).to_numpy() < pc.to_numpy()
    hit = (up & (m["low"].to_numpy() <= pc.to_numpy())) | (dn & (m["high"].to_numpy() >= pc.to_numpy()))
    o["gap_fill_min"] = m.loc[hit, ["date", "mins"]].groupby("date")["mins"].min()
    return o


def session_outcomes(px, mo):
    """One value per session s relative to s-1 (px holds px_open..px_close per panel row, in row order)."""
    pc = px["px_close"].shift(1)
    o = pd.DataFrame(index=px.index)
    o["gap_pct"] = (px["px_open"] / pc - 1) * 100
    o["gap_sign"] = np.sign(o["gap_pct"])
    o["gap_dir"] = pd.Series(np.where(o["gap_pct"].abs() < FLAT_GAP, "flat",
                                      np.where(o["gap_pct"] > 0, "up", "down")), index=px.index).where(o["gap_pct"].notna())
    o["oc"] = (px["px_close"] / px["px_open"] - 1) * 100
    o["cc"] = (px["px_close"] / pc - 1) * 100
    o["high_vs_prevclose"] = (px["px_high"] / pc - 1) * 100
    o["low_vs_prevclose"] = (px["px_low"] / pc - 1) * 100
    o["range_pct"] = (px["px_high"] - px["px_low"]) / pc * 100
    o["max_exc"] = np.fmax(o["high_vs_prevclose"], -o["low_vs_prevclose"]).where(pc.notna() & px["px_high"].notna())
    o["big_move_cc"] = (o["cc"].abs() >= BIG).astype("boolean").mask(o["cc"].isna())
    o["big_move_exc"] = (o["max_exc"] >= BIG).astype("boolean").mask(o["max_exc"].isna())
    filled = np.where(o["gap_pct"] > 0, px["px_low"] <= pc, px["px_high"] >= pc)
    o["gap_filled"] = pd.Series(filled, index=px.index).astype("boolean").mask(o["gap_pct"].isna() | (o["gap_pct"] == 0)
                                                                               | px["px_low"].isna())
    ok = px["m_ok"].fillna(False).astype(bool).to_numpy()
    for c in ["ret15", "ret30", "ret60", "last_hour", "rv", "high_min", "low_min", "gap_fill_min"]:
        v = mo[c].reindex(px["date"]).to_numpy(dtype=float)
        o[c] = np.where(ok, v, np.nan)
    o.loc[o["gap_filled"].fillna(False).eq(False).to_numpy(), "gap_fill_min"] = np.nan
    return o


# ======================================================================== options / futures
def chain_stats(g, spot):
    ce = g[g["OptnTp"] == "CE"]
    pe = g[g["OptnTp"] == "PE"]
    K = np.union1d(ce["StrkPric"].to_numpy(), pe["StrkPric"].to_numpy())
    n = len(K)

    def arr(df, c, fill):
        a = np.full(n, fill, float)
        a[np.searchsorted(K, df["StrkPric"].to_numpy())] = df[c].to_numpy(float)
        return a
    ceoi, peoi = arr(ce, "OpnIntrst", 0.0), arr(pe, "OpnIntrst", 0.0)
    cev, pev = arr(ce, "TtlTradgVol", 0.0), arr(pe, "TtlTradgVol", 0.0)
    ces, pes = arr(ce, "SttlmPric", np.nan), arr(pe, "SttlmPric", np.nan)
    r = {"n_strikes": n, "n_strikes_oi": int(((ceoi + peoi) > 0).sum()),
         "ce_oi": ceoi.sum(), "pe_oi": peoi.sum(),
         "ce_oi_chg": ce["ChngInOpnIntrst"].sum(), "pe_oi_chg": pe["ChngInOpnIntrst"].sum(),
         "ce_vol": cev.sum(), "pe_vol": pev.sum()}
    r["pcr_oi"] = r["pe_oi"] / r["ce_oi"] if r["ce_oi"] > 0 else np.nan
    r["pcr_vol"] = r["pe_vol"] / r["ce_vol"] if r["ce_vol"] > 0 else np.nan
    tot = ceoi + peoi
    if tot.sum() > 0:
        diff = K[:, None] - K[None, :]                     # candidate x strike
        pain = (np.maximum(diff, 0) * ceoi[None, :] + np.maximum(-diff, 0) * peoi[None, :]).sum(1)
        r["maxpain"] = K[int(np.argmin(pain))]
        r["top3_oi_share"] = np.sort(tot)[-3:].sum() / tot.sum()
    else:
        r["maxpain"] = np.nan
        r["top3_oi_share"] = np.nan
    r["callwall"] = r["putwall"] = r["atm_strike"] = r["straddle"] = r["atm_ce_vol"] = r["atm_pe_vol"] = np.nan
    if np.isfinite(spot):
        a = (K > spot) & (ceoi > 0)
        if a.any():
            r["callwall"] = K[a][int(np.argmax(ceoi[a]))]          # ties -> nearest (lowest) strike above
        b = (K < spot) & (peoi > 0)
        if b.any():
            kb, pb = K[b][::-1], peoi[b][::-1]
            r["putwall"] = kb[int(np.argmax(pb))]                  # ties -> nearest (highest) strike below
        v = (ces > 0) & (pes > 0)
        if v.any():
            i = np.flatnonzero(v)[int(np.argmin(np.abs(K[v] - spot)))]
            r["atm_strike"], r["straddle"] = K[i], ces[i] + pes[i]
            r["atm_ce_vol"], r["atm_pe_vol"] = cev[i], pev[i]
    return r


def option_tables(bhav, spot):
    """Per (TradDt, XpryDt) chain stats for the first 2 expiries and first 2 monthlies listed after TradDt."""
    opt = bhav[(bhav["FinInstrmTp"] == "IDO") & (bhav["XpryDt"] > bhav["TradDt"])]
    opt = opt.drop_duplicates(["TradDt", "XpryDt", "StrkPric", "OptnTp"], keep="first")
    fut = bhav[(bhav["FinInstrmTp"] == "IDF") & (bhav["XpryDt"] > bhav["TradDt"])]
    pairs = opt[["TradDt", "XpryDt"]].drop_duplicates().sort_values(["TradDt", "XpryDt"])
    fpairs = fut[["TradDt", "XpryDt"]].drop_duplicates()
    mon = pairs.merge(fpairs, on=["TradDt", "XpryDt"])
    first2 = pairs.groupby("TradDt").head(2)
    mon2 = mon.groupby("TradDt").head(2)
    need = pd.concat([first2, mon2]).drop_duplicates()
    sub = opt.merge(need, on=["TradDt", "XpryDt"])
    rows = []
    for (d, e), g in sub.groupby(["TradDt", "XpryDt"], sort=True):
        r = chain_stats(g, float(spot.get(d, np.nan)))
        r["TradDt"], r["XpryDt"] = d, e
        rows.append(r)
    st = pd.DataFrame(rows)
    if len(st):
        sp = st["TradDt"].map(spot)
        st["straddle_pct"] = st["straddle"] / sp * 100
    near = pairs.groupby("TradDt")["XpryDt"].min()
    monthly = mon.groupby("TradDt")["XpryDt"].min()
    return st, near, monthly


def futures_table(bhav):
    f = bhav[bhav["FinInstrmTp"] == "IDF"]
    allf = f[f["XpryDt"] >= f["TradDt"]].groupby("TradDt").agg(futall_oi=("OpnIntrst", "sum"),
                                                              futall_oi_chg=("ChngInOpnIntrst", "sum"))
    fr = f[f["XpryDt"] > f["TradDt"]].sort_values(["TradDt", "XpryDt"]).groupby("TradDt").head(1).set_index("TradDt")
    out = pd.DataFrame({"fut_expiry": fr["XpryDt"], "fut_close": fr["ClsPric"], "fut_settle": fr["SttlmPric"],
                        "fut_oi": fr["OpnIntrst"], "fut_oi_chg": fr["ChngInOpnIntrst"], "fut_vol": fr["TtlTradgVol"]})
    return out.join(allf, how="outer")


# ======================================================================== VIX
def vix_series(raws):
    """Combined VIX close by date (vix_daily, then index_close_daily, then the clean minute 15:29 close)."""
    special = raws["special"]
    sess = set(raws["nse_sess"]["date"])
    v = raws["vixd"].dropna(subset=["close"]).set_index("date")["close"]
    s = pd.DataFrame({"vix": v, "vix_src": "vix_daily"})
    ic = raws["icd_vix"].dropna(subset=["close"]).set_index("date")["close"]
    ic = ic[~ic.index.isin(s.index)]
    s = pd.concat([s, pd.DataFrame({"vix": ic, "vix_src": "index_close_daily"})])
    vm = raws["vixmin"]
    md = minute_daily(vm, BAD_MINUTE_DAYS["INDIAVIX"])
    mc = md.loc[md["m_ok"] & (md.index >= VIX_MIN_CLEAN_FROM), "m_close"]
    mc = mc[~mc.index.isin(s.index)]
    s = pd.concat([s, pd.DataFrame({"vix": mc, "vix_src": "spot_1m"})]).sort_index()
    first_sess = min(sess) if sess else "2018-01-01"
    keep = ~s.index.isin(special) & ((s.index < first_sess) | s.index.isin(sess))
    s = s[keep]
    x = s["vix"].to_numpy()
    pct = np.full(len(x), np.nan)
    for i in range(len(x)):
        w = x[max(0, i - 252):i]
        if len(w) >= 200:
            pct[i] = (w <= x[i]).mean() * 100
    s["vix_pctile_1y"] = pct
    return s


# ======================================================================== panel
def session_rows(ul, raws):
    s = raws["nse_sess"]
    s = s[~s["is_special_session"].astype(bool)][["date"]].copy()
    if ul == "SENSEX":
        s = s[s["date"] >= SENSEX_FIRST]
    s = s.sort_values("date").reset_index(drop=True)
    special = sorted(raws["special"])
    nxt = s["date"].shift(-1)
    s["cal_special_between"] = [any(a < x < b for x in special) if isinstance(b, str) else pd.NA
                                for a, b in zip(s["date"], nxt)]
    s["cal_special_between"] = s["cal_special_between"].astype("boolean")
    return s


def base_panel(ul, raws, vix):
    r = raws[ul]
    P = session_rows(ul, raws)
    P.insert(1, "underlying", ul)
    md = minute_daily(r["min"], BAD_MINUTE_DAYS[IDX[ul]])
    icd = r["icd"].set_index("date")
    j = md.reindex(P["date"])
    ic = icd.reindex(P["date"])
    ok = j["m_ok"].eq(True).to_numpy()
    has_ic = ic["close"].notna().to_numpy()
    short = (~ok) & (~has_ic) & (j["n_bars"].fillna(0).to_numpy() >= 300)
    src = np.where(ok, "spot_1m", np.where(has_ic, "index_close_daily", np.where(short, "spot_1m_short", "none")))
    P["src"] = src
    P["m_ok"] = ok
    for c in ["open", "high", "low", "close"]:
        mv, iv = j["m_" + c].to_numpy(), ic[c].to_numpy()
        P["px_" + c] = np.where(src == "spot_1m", mv, np.where(src == "index_close_daily", iv,
                                                                np.where(src == "spot_1m_short", mv, np.nan)))
    P["px_close_official"] = ic["close"].to_numpy()
    P["n_bars"] = j["n_bars"].to_numpy()
    prev_close = pd.Series(P["px_close"].shift(1).to_numpy(), index=P["date"])
    mo = minute_outcomes(r["min"], prev_close)
    so = session_outcomes(P, mo)
    nxt = so.shift(-1)
    for c in so.columns:
        P["o_" + c] = so[c]
    for c in so.columns:
        P["y_" + c] = nxt[c]
    P["y_src"] = pd.Series(src).shift(-1).to_numpy()
    P["y_date"] = P["date"].shift(-1)

    # ---------- f_ price features (TCLOSE)
    o, h, l, c = P["px_open"], P["px_high"], P["px_low"], P["px_close"]
    rng = (h - l).where(h > l)
    P["f_body_frac"] = (c - o).abs() / rng
    P["f_upper_wick_frac"] = (h - np.fmax(o, c)) / rng
    P["f_lower_wick_frac"] = (np.fmin(o, c) - l) / rng
    P["f_close_pos"] = (c - l) / rng
    P["f_streak_close"] = streak(np.sign(P["o_cc"]))
    P["f_streak_gap"] = streak(np.sign(P["o_gap_pct"]))
    for k in [1, 3, 5, 10, 20]:
        P[f"f_mom{k}"] = (c / c.shift(k) - 1) * 100
    for k in [20, 55]:
        P[f"f_dist_high{k}"] = (c / h.rolling(k, min_periods=k).max() - 1) * 100
        P[f"f_dist_low{k}"] = (c / l.rolling(k, min_periods=k).min() - 1) * 100
    lr = np.log(c / c.shift(1))
    for k in [10, 20]:
        P[f"f_hv{k}"] = lr.rolling(k, min_periods=k).std() * np.sqrt(252) * 100
    pc = c.shift(1)
    tr = np.fmax(h - l, np.fmax((h - pc).abs(), (l - pc).abs())).where(h.notna() & pc.notna())
    P["f_atr14_pct"] = tr.rolling(14, min_periods=14).mean() / c * 100

    # ---------- VIX
    vj = vix.reindex(P["date"])
    P["f_vix_close"] = vj["vix"].to_numpy()
    P["f_vix_src"] = vj["vix_src"].to_numpy()
    P["f_vix_chg1"] = (P["f_vix_close"] / P["f_vix_close"].shift(1) - 1) * 100
    P["f_vix_chg5"] = (P["f_vix_close"] / P["f_vix_close"].shift(5) - 1) * 100
    P["f_vix_pctile_1y"] = vj["vix_pctile_1y"].to_numpy()

    # ---------- f1515 (T1515): minute bars of t up to 15:14 + earlier rows only
    m = r["min"]
    m14 = m[m["mins"] <= M_1514]
    g = m14.groupby("date")
    q = pd.DataFrame({"n": g.size(), "first": g["mins"].min(), "o": g["open"].first(), "h": g["high"].max(),
                      "l": g["low"].min(), "c": g["close"].last()})
    lr14 = np.log(m14["close"] / m14.groupby("date")["close"].shift(1))
    firstbar = m14["mins"].eq(g["mins"].transform("min"))
    lr14 = lr14.where(~firstbar, np.log(m14["close"] / m14["open"]))
    q["rv"] = np.sqrt((lr14 ** 2).groupby(m14["date"]).sum()) * 100
    q["ok"] = (q["n"] >= 355) & (q["first"] == 0) & ~q.index.isin(BAD_MINUTE_DAYS[IDX[ul]])
    q = q.reindex(P["date"])
    qok = q["ok"].eq(True).to_numpy()
    pcv = pc.to_numpy()
    P["f1515_ret_to_1514"] = np.where(qok, (q["c"].to_numpy() / pcv - 1) * 100, np.nan)
    P["f1515_ret_open_to_1514"] = np.where(qok, (q["c"] / q["o"] - 1).to_numpy() * 100, np.nan)
    qr = (q["h"] - q["l"]).where(q["h"] > q["l"])
    P["f1515_pos_in_range"] = np.where(qok, ((q["c"] - q["l"]) / qr).to_numpy(), np.nan)
    P["f1515_range_pct"] = np.where(qok, (q["h"] - q["l"]).to_numpy() / pcv * 100, np.nan)
    P["f1515_rv"] = np.where(qok, q["rv"].to_numpy(), np.nan)
    vm = raws["vixmin"]
    v14 = vm[vm["mins"] <= M_1514].groupby("date").agg(n=("mins", "size"), c=("close", "last"))
    v14 = v14[(v14["n"] >= 355) & ~v14.index.isin(BAD_MINUTE_DAYS["INDIAVIX"])].reindex(P["date"])
    vprev = P["f_vix_close"].shift(1).to_numpy()
    raw14 = v14["c"].to_numpy()
    ratio = raw14 / vprev
    fixed = np.where(ratio > 20, raw14 / 100, np.where(ratio < 0.05, raw14 * 100, raw14))
    P["f1515_vix_1514"] = fixed
    P["f1515_vix_chg"] = (fixed / vprev - 1) * 100

    # ---------- bhavcopy
    if r["bhav"] is not None:
        add_bhav_features(P, r["bhav"])

    # ---------- calendar
    add_calendar(P, ul, raws)
    P["split"] = split_of(P["date"])
    P["split_edge"] = (pd.Series(split_of(P["y_date"].fillna("")), index=P.index) != P["split"]) & P["y_date"].notna()
    return P


def streak(sign):
    out = np.full(len(sign), np.nan)
    run = 0.0
    for i, s in enumerate(np.asarray(sign, float)):
        if not np.isfinite(s):
            run = np.nan
            out[i] = np.nan
            continue
        if s == 0:
            run = 0.0
        elif np.isfinite(run) and np.sign(run) == s:
            run += s
        else:
            run = s
        out[i] = run
    return out


def split_of(dates):
    d = pd.Series(dates).astype(str)
    out = pd.Series("", index=d.index, dtype=object)
    for name, lo, hi in SPLITS:
        out[(d >= lo) & (d <= hi)] = name
    out[d == ""] = None
    return out.to_numpy()


OPT_KEYS = ["n_strikes", "n_strikes_oi", "ce_oi", "pe_oi", "ce_oi_chg", "pe_oi_chg", "ce_vol", "pe_vol", "pcr_oi",
            "pcr_vol", "maxpain", "top3_oi_share", "callwall", "putwall", "atm_strike", "straddle_pct", "atm_ce_vol",
            "atm_pe_vol"]


def add_bhav_features(P, bhav):
    dates = P["date"]
    close = pd.Series(P["px_close"].to_numpy(), index=dates)
    fu = futures_table(bhav).reindex(dates)
    P["f_fut_expiry"] = fu["fut_expiry"].to_numpy()
    P["f_fut_dte"] = (pd.to_datetime(fu["fut_expiry"]) - pd.to_datetime(dates.to_numpy())).dt.days.to_numpy()
    P["f_fut_close"] = fu["fut_close"].to_numpy()
    P["f_fut_settle"] = fu["fut_settle"].to_numpy()
    P["f_fut_basis_pct"] = (P["f_fut_close"] / P["px_close"] - 1) * 100
    for k in ["fut_oi", "fut_oi_chg", "fut_vol", "futall_oi", "futall_oi_chg"]:
        P["f_" + k] = fu[k].to_numpy(dtype=float)
    for k in ["fut_oi", "fut_vol", "futall_oi"]:
        x = P["f_" + k]
        P[f"f_{k}_r20"] = x / x.shift(1).rolling(20, min_periods=15).mean()
    st, near, monthly = option_tables(bhav, close.dropna())
    sti = st.set_index(["TradDt", "XpryDt"]) if len(st) else None
    prev_date = dates.shift(1)
    for tag, sel in [("near", near), ("mon", monthly)]:
        e = sel.reindex(dates)
        P[f"f_opt_{tag}_expiry"] = e.to_numpy()
        P[f"f_opt_{tag}_dte"] = (pd.to_datetime(e) - pd.to_datetime(dates.to_numpy())).dt.days.to_numpy()
        idx = pd.MultiIndex.from_arrays([dates.to_numpy(), e.fillna("").to_numpy()])
        rows = sti.reindex(idx)
        for k in OPT_KEYS:
            P[f"f_opt_{tag}_{k}"] = rows[k].to_numpy(dtype=float)
        sp = P["px_close"].to_numpy()
        for k in ["maxpain", "callwall", "putwall"]:
            P[f"f_opt_{tag}_{k}_dist_pct"] = (P[f"f_opt_{tag}_{k}"].to_numpy() / sp - 1) * 100
        pidx = pd.MultiIndex.from_arrays([prev_date.fillna("").to_numpy(), e.fillna("").to_numpy()])
        prev_str = sti["straddle_pct"].reindex(pidx).to_numpy()
        P[f"f_opt_{tag}_straddle_chg1"] = P[f"f_opt_{tag}_straddle_pct"].to_numpy() - prev_str
    P["f_opt_near_is_monthly"] = (P["f_opt_near_expiry"] == P["f_opt_mon_expiry"]).astype("boolean").mask(
        P["f_opt_near_expiry"].isna())


def add_calendar(P, ul, raws):
    s = raws[ul]["sess"].set_index("date")
    cal = raws["cal"]
    quarterly = set(cal[(cal["underlying"] == ul) & cal["is_quarterly"].astype(bool)]["expiry_date"])
    j = s.reindex(P["date"])
    avail = j["weekday"].notna().to_numpy()

    def b(col):
        return pd.Series(j[col].to_numpy(), index=P.index).map({True: True, False: False, "True": True,
                                                                "False": False}).astype("boolean")
    t = pd.DataFrame(index=P.index)
    t["is_expiry"] = b("is_expiry_any")
    kind = np.where(b("is_expiry_monthly").fillna(False), "monthly",
                    np.where(b("is_expiry_weekly").fillna(False), "weekly", "none"))
    t["kind"] = pd.Series(kind, index=P.index).where(avail)
    t["is_quarterly"] = pd.Series(P["date"].isin(quarterly).to_numpy() & (kind == "monthly"),
                                  index=P.index).astype("boolean").mask(~avail)
    t["sessions_to_expiry"] = j["sessions_to_next_expiry"].to_numpy()
    t["sessions_to_weekly"] = j["sessions_to_next_weekly"].to_numpy()
    t["sessions_to_monthly"] = j["sessions_to_next_monthly"].to_numpy()
    t["sessions_since_expiry"] = j["sessions_since_last_expiry"].to_numpy()
    t["days_to_expiry"] = j["cal_days_to_next_expiry"].to_numpy()
    t["upcoming_kind"] = j["next_expiry_kind"].to_numpy()
    t["gap"] = b("calendar_gap")
    t["dow"] = pd.to_datetime(P["date"]).dt.day_name().to_numpy()
    nxt = t.shift(-1)
    # tags of t+1 are used at t: blank any whose expiry was not yet known on t (known_from > t)
    today = pd.Series(P["date"].to_numpy(), index=P.index)
    t1 = today.shift(-1)
    t1_expiry = pd.Series(j["next_expiry"].to_numpy(), index=P.index).shift(-1)
    for kcol, cols in [("next_expiry_known_from", ["sessions_to_expiry", "days_to_expiry", "upcoming_kind"]),
                       ("next_weekly_known_from", ["sessions_to_weekly"]),
                       ("next_monthly_known_from", ["sessions_to_monthly"])]:
        kf = pd.Series(j[kcol].to_numpy(), index=P.index).shift(-1)
        late = kf.notna() & (kf.astype(str) > today)
        for c in cols:
            nxt.loc[late.to_numpy(), c] = None
        if kcol == "next_expiry_known_from":
            # "t+1 is an expiry" is unknown at t only if t+1's own expiry was not yet known on t
            late_day = (late & (t1_expiry == t1)).to_numpy()
            for c in ["is_expiry", "kind", "is_quarterly"]:
                nxt.loc[late_day, c] = None
    for c in t.columns:
        P["cal_" + c] = t[c]
    for c in t.columns:
        P["cal_next_" + c] = nxt[c]
    P["cal_next_date"] = P["date"].shift(-1)
    P["cal_days_to_next_session"] = (pd.to_datetime(P["cal_next_date"]) - pd.to_datetime(P["date"])).dt.days


def add_cross(panels):
    a, b = panels["NIFTY"], panels["BANKNIFTY"]
    ca = pd.Series(a["px_close"].to_numpy(), index=a["date"])
    cb = pd.Series(b["px_close"].to_numpy(), index=b["date"])
    # returns on each panel's own session sequence, then matched on the same date
    ra1, rb1 = ca / ca.shift(1) - 1, cb / cb.shift(1) - 1
    ra5, rb5 = ca / ca.shift(5) - 1, cb / cb.shift(5) - 1
    rel1 = (rb1 - ra1.reindex(rb1.index)) * 100
    rel5 = (rb5 - ra5.reindex(rb5.index)) * 100
    for P in (a, b):
        P["f_rel_bn_nifty_ret1"] = rel1.reindex(P["date"]).to_numpy()
        P["f_rel_bn_nifty_ret5"] = rel5.reindex(P["date"]).to_numpy()


def build_all(raws, uls=ULS):
    vix = vix_series(raws)
    panels = {ul: base_panel(ul, raws, vix) for ul in uls}
    if "NIFTY" in panels and "BANKNIFTY" in panels:
        add_cross(panels)
    for ul, P in panels.items():
        panels[ul] = order_columns(P)
    return panels


def order_columns(P):
    head = ["date", "underlying", "split", "split_edge", "src", "m_ok", "n_bars", "px_open", "px_high", "px_low",
            "px_close", "px_close_official"]
    rest = [c for c in P.columns if c not in head]
    key = {"f": 0, "f1515": 1, "o": 2, "cal": 3, "y": 4}
    rest.sort(key=lambda c: (key.get("f1515" if c.startswith("f1515_") else c.split("_")[0], 5),))
    return P[head + rest].copy()


# ======================================================================== dictionary
AVAIL = {"f_": "TCLOSE(t)", "f1515_": "T1515(t)", "o_": "OUTCOME(t)", "y_": "NEXT(t+1)", "cal_": "TCLOSE(t)"}


def availability(col):
    for p in ["f1515_", "f_", "o_", "y_", "cal_"]:
        if col.startswith(p):
            return AVAIL[p]
    return "TCLOSE(t)"


OUT_DEFS = {
    "gap_pct": ("open/close(prev session)-1, %", "gap"),
    "gap_sign": ("sign of gap_pct (+1 / -1 / 0), raw", "gap"),
    "gap_dir": ("up / down / flat (|gap| < 0.1 %)", "gap"),
    "oc": ("close/open-1, %", "session_return"),
    "cc": ("close/close(prev session)-1, %", "session_return"),
    "high_vs_prevclose": ("high/close(prev session)-1, %", "session_return"),
    "low_vs_prevclose": ("low/close(prev session)-1, %", "session_return"),
    "range_pct": ("(high-low)/close(prev session), %", "session_return"),
    "max_exc": ("max(high/prev close-1, 1-low/prev close), %", "session_return"),
    "big_move_cc": ("|cc| >= 1 %", "big_move"),
    "big_move_exc": ("max_exc >= 1 %", "big_move"),
    "gap_filled": ("session traded back to the previous close (gap up: low <= prev close; gap down: high >= prev close); blank if gap is 0", "gap_fill"),
    "gap_fill_min": ("minutes after 09:15 of the first bar that reached the previous close (minute days only; blank if not filled)", "gap_fill"),
    "ret15": ("close of the 09:29 bar (last bar at or before) / 09:15 open - 1, % (minute days only)", "minute_path"),
    "ret30": ("close of the 09:44 bar / 09:15 open - 1, % (minute days only)", "minute_path"),
    "ret60": ("close of the 10:14 bar / 09:15 open - 1, % (minute days only)", "minute_path"),
    "last_hour": ("close 15:29 / close as of 14:29 - 1, % (minute days only)", "minute_path"),
    "rv": ("sqrt(sum of squared 1-minute log returns, first bar open->close), % (minute days only)", "minute_path"),
    "high_min": ("minutes after 09:15 of the first bar making the session high (minute days only)", "minute_path"),
    "low_min": ("minutes after 09:15 of the first bar making the session low (minute days only)", "minute_path"),
}
CAL_DEFS = {
    "is_expiry": "an expiry (weekly or monthly) of this underlying settles on the session",
    "kind": "monthly / weekly / none",
    "is_quarterly": "monthly expiry in Mar/Jun/Sep/Dec",
    "sessions_to_expiry": "full sessions until the next expiry known (listed) on that day (0 on expiry day)",
    "sessions_to_weekly": "full sessions until the next weekly expiry known (listed) on that day; blank before the first weekly is listed",
    "sessions_to_monthly": "full sessions until the next monthly expiry known (listed) on that day",
    "sessions_since_expiry": "full sessions since the previous expiry",
    "days_to_expiry": "calendar days to the next expiry known (listed) on that day",
    "upcoming_kind": "kind of the next expiry (known on that day) on or after the session (weekly / monthly)",
    "gap": "calendar_gap: a stored expiry is missing around this session, so counts are blank",
    "dow": "weekday name",
}
OPT_DEFS = {
    "expiry": "XpryDt as listed in the bhavcopy of t", "dte": "calendar days from t to that expiry",
    "n_strikes": "strikes with a CE or PE row", "n_strikes_oi": "strikes with CE+PE OI > 0",
    "ce_oi": "total CE open interest", "pe_oi": "total PE open interest", "ce_oi_chg": "total CE OI change",
    "pe_oi_chg": "total PE OI change", "ce_vol": "total CE volume", "pe_vol": "total PE volume",
    "pcr_oi": "PE OI / CE OI", "pcr_vol": "PE volume / CE volume",
    "maxpain": "strike minimising total intrinsic payout to option holders at expiry (from OI)",
    "maxpain_dist_pct": "maxpain / px_close - 1, %",
    "top3_oi_share": "share of CE+PE OI in the 3 strikes with most CE+PE OI",
    "callwall": "strike above px_close with the most CE OI", "callwall_dist_pct": "callwall / px_close - 1, %",
    "putwall": "strike below px_close with the most PE OI", "putwall_dist_pct": "putwall / px_close - 1, %",
    "atm_strike": "strike nearest px_close among strikes with CE and PE settle > 0",
    "straddle_pct": "ATM CE settle + PE settle as % of px_close (implied move to expiry)",
    "straddle_chg1": "straddle_pct minus the same expiry's straddle_pct on the previous session (pct points)",
    "atm_ce_vol": "volume of the ATM CE", "atm_pe_vol": "volume of the ATM PE",
}
F_DEFS = {
    "f_body_frac": ("candle", "|close-open|/(high-low) of t"),
    "f_upper_wick_frac": ("candle", "(high-max(open,close))/(high-low) of t"),
    "f_lower_wick_frac": ("candle", "(min(open,close)-low)/(high-low) of t"),
    "f_close_pos": ("candle", "(close-low)/(high-low) of t"),
    "f_streak_close": ("streak", "consecutive up (+n) / down (-n) closes ending at t; unchanged close resets to 0"),
    "f_streak_gap": ("streak", "consecutive gap-up (+n) / gap-down (-n) sessions ending at t; zero gap resets"),
    "f_atr14_pct": ("volatility", "mean true range of the last 14 sessions / close(t), %"),
    "f_vix_close": ("vix", "India VIX close of t (see f_vix_src)"),
    "f_vix_src": ("vix", "source of f_vix_close: vix_daily / index_close_daily / spot_1m (clean 15:29 minute close)"),
    "f_vix_chg1": ("vix", "VIX close / previous session's - 1, %"),
    "f_vix_chg5": ("vix", "VIX close / 5 sessions ago - 1, %"),
    "f_vix_pctile_1y": ("vix", "percent of the previous 252 VIX closes <= today's close (needs 200)"),
    "f_fut_expiry": ("futures", "expiry of the front future (smallest XpryDt > t)"),
    "f_fut_dte": ("futures", "calendar days to the front future's expiry"),
    "f_fut_close": ("futures", "front future ClsPric (last traded)"),
    "f_fut_settle": ("futures", "front future SttlmPric"),
    "f_fut_basis_pct": ("futures", "front future close / px_close - 1, %"),
    "f_fut_oi": ("futures", "front future open interest"),
    "f_fut_oi_chg": ("futures", "front future OI change"),
    "f_fut_vol": ("futures", "front future volume"),
    "f_futall_oi": ("futures", "OI summed over all futures with XpryDt >= t"),
    "f_futall_oi_chg": ("futures", "OI change summed over all futures with XpryDt >= t"),
    "f_fut_oi_r20": ("futures", "f_fut_oi / mean of the previous 20 sessions (t-20..t-1, needs 15)"),
    "f_fut_vol_r20": ("futures", "f_fut_vol / mean of the previous 20 sessions"),
    "f_futall_oi_r20": ("futures", "f_futall_oi / mean of the previous 20 sessions"),
    "f_opt_near_is_monthly": ("options_near", "the near expiry is also the next monthly"),
    "f_rel_bn_nifty_ret1": ("cross", "BANKNIFTY 1-session return minus NIFTY 1-session return, same date, pct points"),
    "f_rel_bn_nifty_ret5": ("cross", "BANKNIFTY 5-session return minus NIFTY 5-session return, same date, pct points"),
    "f1515_ret_to_1514": ("intraday_1515", "close of the 15:14 bar / px_close(t-1) - 1, %"),
    "f1515_ret_open_to_1514": ("intraday_1515", "close of the 15:14 bar / 09:15 open - 1, %"),
    "f1515_pos_in_range": ("intraday_1515", "(close15:14 - low)/(high - low) over bars 09:15..15:14"),
    "f1515_range_pct": ("intraday_1515", "(high-low) over bars 09:15..15:14 / px_close(t-1), %"),
    "f1515_rv": ("intraday_1515", "realized vol of 1-minute log returns 09:15..15:14, %"),
    "f1515_vix_1514": ("intraday_1515", "India VIX minute close of 15:14, unit-fixed vs the previous VIX close"),
    "f1515_vix_chg": ("intraday_1515", "f1515_vix_1514 / previous session's VIX close - 1, %"),
}
ID_DEFS = {
    "date": ("id", "session date t (IST)"), "underlying": ("id", "NIFTY / BANKNIFTY / SENSEX"),
    "split": ("id", "discovery / validation by the date of t (PREREGISTRATION); final rows are sealed in data/sealed/"),
    "split_edge": ("id", "t+1 falls in a later split than t (the label belongs to the next period)"),
    "src": ("price", "source of px_*: spot_1m / index_close_daily / spot_1m_short / none"),
    "m_ok": ("price", "minute day is complete (>= 370 bars, 09:15..15:29, not on the audit bad-day list)"),
    "n_bars": ("price", "minute bars 09:15..15:29 stored for t"),
    "px_open": ("price", "open of t (09:15 bar open, or official)"), "px_high": ("price", "high of t"),
    "px_low": ("price", "low of t"), "px_close": ("price", "close of t (15:29 bar close, or official)"),
    "px_close_official": ("price", "official close from index_close_daily (to 2025-09) for reference"),
}


def dictionary(cols):
    rows = []
    for c in cols:
        if c in ID_DEFS:
            g, d = ID_DEFS[c]
        elif c in F_DEFS:
            g, d = F_DEFS[c]
        elif c.startswith("f_mom"):
            k = c[5:]
            g, d = "momentum", f"close(t)/close(t-{k})-1, %"
        elif c.startswith("f_dist_high") or c.startswith("f_dist_low"):
            k = c.split("high")[-1] if "high" in c else c.split("low")[-1]
            hl = "highest high" if "high" in c else "lowest low"
            g, d = "range_distance", f"close(t) / {hl} of the {k} sessions ending at t - 1, %"
        elif c.startswith("f_hv"):
            g, d = "volatility", f"std of daily log returns over the last {c[4:]} sessions x sqrt(252), %"
        elif c.startswith("f_opt_"):
            tag, key = c[6:].split("_", 1)
            g = "options_near" if tag == "near" else "options_monthly"
            which = ("nearest option expiry listed after t (on or after t+1)" if tag == "near"
                     else "nearest monthly (option expiry with a listed future) after t")
            d = f"{OPT_DEFS[key]}; expiry = {which}; bhavcopy of t"
        elif c.startswith("o_") or c.startswith("y_"):
            key = c[2:]
            if key == "src":
                g, d = "label", "source of t+1 prices (as src)"
            elif key == "date":
                g, d = "label", "date of t+1"
            else:
                dd, gg = OUT_DEFS[key]
                who = "session t" if c.startswith("o_") else "session t+1 (prev close = close of t)"
                g, d = ("outcome_" if c.startswith("o_") else "label_") + gg, f"{dd}; of {who}"
        elif c.startswith("cal_next_"):
            key = c[9:]
            g, d = "calendar_next", ("date of t+1" if key == "date" else f"{CAL_DEFS[key]}; of t+1, blank if it needs an expiry not yet listed on t")
        elif c == "cal_days_to_next_session":
            g, d = "calendar_next", "calendar days from t to t+1"
        elif c == "cal_special_between":
            g, d = "calendar_next", "a special (Muhurat) session lies between t and t+1; its move is inside y_gap"
        elif c.startswith("cal_"):
            g, d = "calendar", f"{CAL_DEFS[c[4:]]}; of t"
        else:
            raise KeyError(c)
        rows.append({"column": c, "group": g, "definition": d, "availability": availability(c)})
    out = pd.DataFrame(rows)
    out.loc[out["column"].isin(["y_src", "y_date"]), "availability"] = "NEXT(t+1)"
    return out


# ======================================================================== reports
def reconcile(raws):
    rows, glab = [], []
    for ul in ["NIFTY", "BANKNIFTY"]:
        md = minute_daily(raws[ul]["min"], BAD_MINUTE_DAYS[IDX[ul]])
        md = md[md["m_ok"] & (md.index < FINAL_START)]           # final period sealed: not used here
        ic = raws[ul]["icd"].set_index("date")
        ic = ic[ic.index < FINAL_START]
        j = md.join(ic, how="inner")
        for f in ["open", "high", "low", "close"]:
            p = (j["m_" + f] / j[f] - 1).abs() * 100
            rows.append({"underlying": ul, "field": f, "n_days": len(p), "median_abs_pct": p.median(),
                         "p99_abs_pct": p.quantile(0.99), "max_abs_pct": p.max(), "n_over_0_1pct": int((p > 0.1).sum()),
                         "n_over_0_5pct": int((p > 0.5).sum())})
        # gap label computed with minute prices vs official prices on consecutive days both present
        j = j.sort_index()
        gm = (j["m_open"] / j["m_close"].shift(1) - 1) * 100
        go = (j["open"] / j["close"].shift(1) - 1) * 100
        ok = gm.notna() & go.notna()
        dirm = np.where(gm.abs() < FLAT_GAP, "flat", np.where(gm > 0, "up", "down"))[ok]
        diro = np.where(go.abs() < FLAT_GAP, "flat", np.where(go > 0, "up", "down"))[ok]
        rows.append({"underlying": ul, "field": "gap_pct (minute vs official)", "n_days": int(ok.sum()),
                     "median_abs_pct": (gm - go)[ok].abs().median(), "p99_abs_pct": (gm - go)[ok].abs().quantile(0.99),
                     "max_abs_pct": (gm - go)[ok].abs().max(), "n_over_0_1pct": int(((gm - go)[ok].abs() > 0.1).sum()),
                     "n_over_0_5pct": int(((gm - go)[ok].abs() > 0.5).sum()),
                     "gap_dir_agree_share": float((dirm == diro).mean())})
    return pd.DataFrame(rows)


def gaps_report(panels):
    rows = []
    for ul, P in panels.items():
        for _, r in P.iterrows():
            iss = []
            if r["src"] == "none":
                iss.append("no price data")
            elif r["src"] != "spot_1m" and r["date"] >= SENSEX_FIRST:
                iss.append(f"minute day not usable (bars={r['n_bars']}); src={r['src']}")
            if pd.isna(r["f_vix_close"]):
                iss.append("no VIX close")
            if ul != "SENSEX":
                if pd.isna(r.get("f_fut_close")):
                    iss.append("no futures in bhavcopy")
                if pd.isna(r.get("f_opt_near_ce_oi")):
                    iss.append("no near-expiry options in bhavcopy")
                elif pd.isna(r.get("f_opt_near_straddle_pct")):
                    iss.append("no ATM straddle (settle missing)")
            if iss:
                rows.append({"underlying": ul, "date": r["date"], "issues": "; ".join(iss)})
    return pd.DataFrame(rows)


def summary(panels, finals):
    """NaN shares for the open splits only; the sealed final split gets its row count and span, nothing else."""
    rows = []
    for ul, P in panels.items():
        for sp in ["discovery", "validation", "open"]:
            Q = P if sp == "open" else P[P["split"] == sp]
            r = {"panel": ul, "split": sp, "rows": len(Q), "first": Q["date"].min(), "last": Q["date"].max(),
                 "n_split_edge": int(Q["split_edge"].sum())}
            for c in P.columns:
                r["nan_" + c] = round(float(Q[c].isna().mean()), 4) if len(Q) else np.nan
            rows.append(r)
        F = finals[ul]
        F = F[F["split"] == "final"]
        rows.append({"panel": ul, "split": "final (sealed)", "rows": len(F), "first": F["date"].min(),
                     "last": F["date"].max()})
    return pd.DataFrame(rows)


def seal(P):
    """Split a full panel into the open part (discovery + validation) and the sealed final part.

    Open: rows with t < FINAL_START; on a row whose t+1 is a final session every y_ value except y_date is blanked.
    Sealed: the final rows plus the unblanked edge row(s), for the coordinator only.
    """
    open_ = P[P["date"] < FINAL_START].copy()
    edge = open_["y_date"].fillna("") >= FINAL_START
    sealed = pd.concat([P[edge.reindex(P.index, fill_value=False)], P[P["date"] >= FINAL_START]])
    ycols = [c for c in P.columns if c.startswith("y_") and c != "y_date"]
    for c in ycols:
        open_.loc[edge, c] = None
    return open_.reset_index(drop=True), sealed.reset_index(drop=True)


def main():
    RES.mkdir(exist_ok=True)
    print("loading raw data ...")
    raws = load_raw_all()
    for ul in ["NIFTY", "BANKNIFTY"]:
        b = raws[ul]["bhav"]
        nd = b.duplicated(["TradDt", "XpryDt", "StrkPric", "OptnTp", "FinInstrmTp"]).sum()
        print(f"{ul}: bhavcopy rows {len(b):,}, duplicate keys {nd}")
    print("building panels ...")
    panels = build_all(raws)
    cols = []
    for P in panels.values():
        cols += [c for c in P.columns if c not in cols]
    dic = dictionary(cols)
    dic.to_csv(DATA / "panel_dictionary.csv", index=False)
    SEALED.mkdir(exist_ok=True)
    opens, finals = {}, {}
    for ul, P in panels.items():
        O, F = seal(P)
        opens[ul], finals[ul] = O, F
        O.to_parquet(DATA / f"panel_{ul}.parquet", index=False)
        F.to_parquet(SEALED / f"panel_{ul}_final.parquet", index=False)
        print(f"{ul}: open {len(O)} rows x {O.shape[1]} cols, {O['date'].min()} .. {O['date'].max()}; "
              f"sealed {len(F)} rows ({int((F['split'] == 'final').sum())} final + "
              f"{int((F['split'] != 'final').sum())} edge row)")
        print("  open rows per split:", O["split"].value_counts().reindex(["discovery", "validation"]).to_dict())
        print("  open src:", O["src"].value_counts().to_dict())
        print("  open split_edge rows:", O.loc[O["split_edge"], "date"].tolist())
    summary(opens, finals).to_csv(RES / "panel_summary.csv", index=False)
    rc = reconcile(raws)
    rc.to_csv(RES / "panel_reconcile.csv", index=False)
    print(rc.to_string(index=False))
    gp = gaps_report(opens)
    gp.to_csv(RES / "panel_gaps.csv", index=False)
    print(f"gap report rows (open splits): {len(gp)}")
    print(gp.groupby("underlying").size().to_dict() if len(gp) else {})
    # final-period input gaps for the coordinator: src / n_bars / f_ columns only, written next to the sealed files
    gf = gaps_report({ul: F[F["split"] == "final"] for ul, F in finals.items()})
    gf.to_csv(SEALED / "panel_gaps_final.csv", index=False)


if __name__ == "__main__":
    main()
