"""Data audit of the read-only index store (see reports/lld/audit_calendar.md).

Run from the repo root:
    INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe expiry_research/scripts/audit_data.py
Writes expiry_research/results/audit/*.csv and prints a short summary.
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
OUT = ROOT / "results" / "audit"
OUT.mkdir(parents=True, exist_ok=True)

summary = []          # dataset_summary rows
sessions = {}         # dataset -> set of 'YYYY-MM-DD'


def add_summary(**kw):
    summary.append(kw)


# ---------------------------------------------------------------- bhavcopy
def audit_bhavcopy():
    cov_rows, issue_rows, bhav_all = [], [], {}
    for ul in ["NIFTY", "BANKNIFTY"]:
        files = sorted(glob.glob(str(STORE / f"options_daily/{ul}/*.parquet")))
        parts = []
        for f in files:
            d = pd.read_parquet(f)
            d["file_month"] = Path(f).stem
            parts.append(d)
        d = pd.concat(parts, ignore_index=True)
        bhav_all[ul] = d
        key = ["TradDt", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp"]
        k = d[key].copy()
        k["StrkPric"] = k["StrkPric"].fillna(-1)
        k["OptnTp"] = k["OptnTp"].fillna("FUT")
        n_dup = int(k.duplicated().sum())
        wrong_file = int((d["TradDt"].str[:7] != d["file_month"]).sum())
        px = ["OpnPric", "HghPric", "LwPric", "ClsPric"]
        traded = d["TtlTradgVol"] > 0
        nan_close = d["ClsPric"].isna()
        nonpos_close = d["ClsPric"] <= 0
        nonpos_settle = d["SttlmPric"] <= 0
        zero_ohlc_traded = traded & (d[px] <= 0).any(axis=1)
        bad_ohlc = traded & ((d["HghPric"] < d["LwPric"]) | (d["ClsPric"] > d["HghPric"] + 1e-6)
                             | (d["ClsPric"] < d["LwPric"] - 1e-6) | (d["OpnPric"] > d["HghPric"] + 1e-6)
                             | (d["OpnPric"] < d["LwPric"] - 1e-6))
        undl_nan = d["UndrlygPric"].isna()
        d["month"] = d["TradDt"].str[:7]
        for m, g in d.groupby("month"):
            idx = g.index
            issue_rows.append(dict(underlying=ul, month=m, rows=len(g),
                                   nan_close=int(nan_close[idx].sum()), nonpos_close=int(nonpos_close[idx].sum()),
                                   nonpos_settle=int(nonpos_settle[idx].sum()),
                                   zero_ohlc_on_traded=int(zero_ohlc_traded[idx].sum()),
                                   ohlc_inconsistent_traded=int(bad_ohlc[idx].sum()),
                                   underlying_price_nan=int(undl_nan[idx].sum()),
                                   untraded_rows=int((~traded[idx]).sum())))
            o = g[g["FinInstrmTp"] == "IDO"]
            per_day = o.groupby("TradDt").agg(strikes=("StrkPric", "nunique"), expiries=("XpryDt", "nunique"))
            traded_strikes = o[o["TtlTradgVol"] > 0].groupby("TradDt")["StrkPric"].nunique()
            exp_in_month = g.loc[(g["XpryDt"] == g["TradDt"]) & (g["XpryDt"].str[:7] == m), "XpryDt"].nunique()
            cov_rows.append(dict(underlying=ul, month=m, sessions=g["TradDt"].nunique(), rows=len(g),
                                 fut_rows=int((g["FinInstrmTp"] == "IDF").sum()), opt_rows=len(o),
                                 strikes_per_day_median=float(per_day["strikes"].median()) if len(per_day) else 0,
                                 traded_strikes_per_day_median=float(traded_strikes.median()) if len(traded_strikes) else 0,
                                 distinct_strikes_month=int(o["StrkPric"].nunique()),
                                 option_expiries_listed_per_day_median=float(per_day["expiries"].median()) if len(per_day) else 0,
                                 expiries_settled_in_month=int(exp_in_month)))
        days = set(d["TradDt"].unique())
        sessions[f"bhav_{ul}"] = days
        add_summary(dataset=f"options_daily/{ul}", resolution="daily (bhavcopy)", first=min(days), last=max(days),
                    n_sessions=len(days), n_rows=len(d), n_dup=n_dup, n_nan_price=int(nan_close.sum()),
                    n_nonpos_price=int(nonpos_close.sum()), n_ohlc_bad=int(bad_ohlc.sum()),
                    note=f"rows in wrong month file: {wrong_file}; settle<=0: {int(nonpos_settle.sum())}; "
                         f"traded rows with a zero OHLC: {int(zero_ohlc_traded.sum())}; UndrlygPric NaN rows: {int(undl_nan.sum())}")
    pd.DataFrame(cov_rows).to_csv(OUT / "bhavcopy_monthly_coverage.csv", index=False)
    pd.DataFrame(issue_rows).to_csv(OUT / "price_issues_bhavcopy.csv", index=False)
    return bhav_all


# ---------------------------------------------------------------- daily index files
def audit_daily():
    ic = pd.read_parquet(STORE / "index_close_daily.parquet")
    for name, g in ic.groupby("index"):
        px = g[["open", "high", "low", "close"]]
        bad = (g["high"] < g["low"]) | (g["close"] > g["high"] + 1e-6) | (g["close"] < g["low"] - 1e-6)
        sessions[f"idx_{name}"] = set(g["date"])
        add_summary(dataset=f"index_close_daily/{name}", resolution="daily", first=g["date"].min(), last=g["date"].max(),
                    n_sessions=g["date"].nunique(), n_rows=len(g), n_dup=int(g["date"].duplicated().sum()),
                    n_nan_price=int(px.isna().any(axis=1).sum()), n_nonpos_price=int((px <= 0).any(axis=1).sum()),
                    n_ohlc_bad=int(bad.sum()), note="")
    vd = pd.read_parquet(STORE / "vix_daily.parquet")
    px = vd[["open", "high", "low", "close"]]
    bad = (vd["high"] < vd["low"]) | (vd["close"] > vd["high"] + 1e-6) | (vd["close"] < vd["low"] - 1e-6)
    sessions["vix_daily"] = set(vd["date"])
    add_summary(dataset="vix_daily", resolution="daily", first=vd["date"].min(), last=vd["date"].max(),
                n_sessions=vd["date"].nunique(), n_rows=len(vd), n_dup=int(vd["date"].duplicated().sum()),
                n_nan_price=int(px.isna().any(axis=1).sum()), n_nonpos_price=int((px <= 0).any(axis=1).sum()),
                n_ohlc_bad=int(bad.sum()),
                note=f"close outside 5-100: {int(((vd['close'] < 5) | (vd['close'] > 100)).sum())}")
    return ic, vd


# ---------------------------------------------------------------- spot 1m
def load_spot(ix):
    parts = [pd.read_parquet(f) for f in sorted(glob.glob(str(STORE / f"spot_1m/{ix}/*.parquet")))]
    d = pd.concat(parts, ignore_index=True)
    d["timestamp"] = d["timestamp"].dt.tz_convert("Asia/Kolkata")
    d["date"] = d["timestamp"].dt.strftime("%Y-%m-%d")
    d["hhmm"] = d["timestamp"].dt.strftime("%H:%M")
    return d


def audit_spot(vd):
    bars_rows, vix_rows, spot = [], [], {}
    vref = vd.set_index("date")["close"]
    for ix in ["NIFTY50", "NIFTYBANK", "SENSEX", "INDIAVIX"]:
        d = load_spot(ix)
        n_dup = int(d["timestamp"].duplicated().sum())
        px = d[["open", "high", "low", "close"]]
        bad = (d["high"] < d["low"]) | (d["close"] > d["high"] + 1e-6) | (d["close"] < d["low"] - 1e-6)
        outside = ((d["hhmm"] < "09:15") | (d["hhmm"] > "15:29"))
        if ix == "INDIAVIX":
            ref = d["date"].map(vref)
            # each OHLC field is judged on its own (a bar can hold a good close and a x100 high)
            any_x100 = np.zeros(len(d), bool)
            any_div = np.zeros(len(d), bool)
            for c in ["open", "high", "low", "close"]:
                r = d[c] / ref
                x100, div = (r > 20).to_numpy(), (r < 0.05).to_numpy()
                any_x100 |= x100
                any_div |= div
                d[c + "_fix"] = d[c] * np.where(x100, 0.01, np.where(div, 100.0, 1.0))
            d["vix_x100"] = any_x100
            d["vix_div100"] = any_div
            g = d.groupby("date").agg(n=("close", "size"), n_x100=("vix_x100", "sum"), n_div100=("vix_div100", "sum"),
                                      min_close=("close", "min"), max_close=("close", "max"))
            g["vix_daily_close"] = g.index.map(vref)
            g["no_daily_ref"] = g["vix_daily_close"].isna()
            g = g[(g["n_x100"] > 0) | (g["n_div100"] > 0) | g["no_daily_ref"]]
            g.insert(0, "source", "spot_1m/INDIAVIX")
            vix_rows.append(g.reset_index())
        per = d.groupby("date").agg(n_bars=("timestamp", "size"), n_unique_ts=("timestamp", "nunique"),
                                    first_time=("hhmm", "min"), last_time=("hhmm", "max"))
        per["n_dup_ts"] = per["n_bars"] - per["n_unique_ts"]
        per["short"] = per["n_unique_ts"] < 370
        per["late_start"] = per["first_time"] > "09:15"
        per["early_end"] = per["last_time"] < "15:29"
        per["weekday"] = pd.to_datetime(per.index).day_name()
        per.insert(0, "index", ix)
        bars_rows.append(per.reset_index())
        sessions[f"spot_{ix}"] = set(d["date"])
        src = d["source"].value_counts().to_dict() if "source" in d else {}
        add_summary(dataset=f"spot_1m/{ix}", resolution="1 minute", first=d["date"].min(), last=d["date"].max(),
                    n_sessions=d["date"].nunique(), n_rows=len(d), n_dup=n_dup,
                    n_nan_price=int(px.isna().any(axis=1).sum()), n_nonpos_price=int((px <= 0).any(axis=1).sum()),
                    n_ohlc_bad=int(bad.sum()),
                    note=f"bars outside 09:15-15:29: {int(outside.sum())}; median bars/day {per['n_unique_ts'].median():.0f}; "
                         f"short days (<370 bars): {int(per['short'].sum())}; sources {src}")
        spot[ix] = d
    pd.concat(bars_rows).to_csv(OUT / "spot1m_bars_per_day.csv", index=False)
    return spot, vix_rows


# ---------------------------------------------------------------- reconciliation
def reconcile(ic, vd, spot, vix_rows):
    rows = []
    m = {"NIFTY50": "NIFTY50", "NIFTYBANK": "NIFTYBANK", "INDIAVIX": "INDIAVIX"}
    for ix in m:
        d = spot[ix]
        sfx = "_fix" if ix == "INDIAVIX" else ""
        d = d[(d["hhmm"] >= "09:15") & (d["hhmm"] <= "15:29")].sort_values("timestamp")
        agg = d.groupby("date").agg(o1=("open" + sfx, "first"), h1=("high" + sfx, "max"), l1=("low" + sfx, "min"),
                                    c1=("close" + sfx, "last"), n_bars=("close", "size"))
        off = ic[ic["index"] == ix].set_index("date")[["open", "high", "low", "close"]]
        j = off.join(agg, how="inner")
        for a, b in [("open", "o1"), ("high", "h1"), ("low", "l1"), ("close", "c1")]:
            j[f"pct_{a}"] = (j[b] / j[a] - 1) * 100
        j.insert(0, "index", ix)
        rows.append(j.reset_index())
    rec = pd.concat(rows, ignore_index=True)
    rec.to_csv(OUT / "reconcile_daily_vs_1m.csv", index=False)
    srows = []
    for ix, g in rec.groupby("index"):
        for f in ["open", "high", "low", "close"]:
            a = g[f"pct_{f}"].abs()
            srows.append(dict(pair=f"index_close_daily vs spot_1m ({ix})", field=f, n=int(a.notna().sum()),
                              median_abs_pct=round(a.median(), 4), p99_abs_pct=round(a.quantile(0.99), 4),
                              max_abs_pct=round(a.max(), 4), n_over_0_1pct=int((a > 0.1).sum()),
                              n_over_0_5pct=int((a > 0.5).sum())))
    # vix_daily vs index_close_daily INDIAVIX
    a = vd.set_index("date")[["open", "high", "low", "close"]]
    b = ic[ic["index"] == "INDIAVIX"].set_index("date")[["open", "high", "low", "close"]]
    j = a.join(b, how="inner", lsuffix="_vd", rsuffix="_ic")
    for f in ["open", "high", "low", "close"]:
        p = ((j[f + "_vd"] / j[f + "_ic"] - 1) * 100).abs()
        srows.append(dict(pair="vix_daily vs index_close_daily (INDIAVIX)", field=f, n=int(p.notna().sum()),
                          median_abs_pct=round(p.median(), 4), p99_abs_pct=round(p.quantile(0.99), 4),
                          max_abs_pct=round(p.max(), 4), n_over_0_1pct=int((p > 0.1).sum()),
                          n_over_0_5pct=int((p > 0.5).sum())))
    pd.DataFrame(srows).to_csv(OUT / "reconcile_summary.csv", index=False)
    # vix unit issues also in daily files
    vrows = list(vix_rows)
    for src, s in [("vix_daily", vd.set_index("date")["close"]),
                   ("index_close_daily/INDIAVIX", ic[ic["index"] == "INDIAVIX"].set_index("date")["close"])]:
        bad = s[(s > 100) | (s < 2)]
        if len(bad):
            vrows.append(pd.DataFrame({"source": src, "date": bad.index, "min_close": bad.values, "max_close": bad.values}))
    pd.concat(vrows, ignore_index=True).to_csv(OUT / "vix_unit_issues.csv", index=False)
    return rec


# ---------------------------------------------------------------- options 1m
def audit_options_1m():
    rows, colsets = [], {}
    for ul in ["NIFTY", "SENSEX"]:
        days = set()
        n_rows_total, n_dup_total, n_nan, n_nonpos = 0, 0, 0, 0
        for exp_dir in sorted(glob.glob(str(STORE / f"options_1m/{ul}/*"))):
            exp = Path(exp_dir).name
            files = sorted(glob.glob(exp_dir + "/*.parquet"))
            per_day = []
            for f in files:
                sch = pq.read_schema(f)
                colsets.setdefault(ul, set()).add(tuple(sch.names))
                t = pq.read_table(f, columns=["timestamp", "token", "close", "volume"]).to_pandas()
                # fast IST date / minute from the int64 epoch (no per-row string formatting)
                ns = t["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None).to_numpy().astype("datetime64[ns]").astype("int64")
                ist_min = (ns // 60_000_000_000) + 330
                day0 = (pd.Timestamp(Path(f).stem).value // 60_000_000_000)
                dups = int(t.duplicated(["timestamp", "token"]).sum())
                mins = np.unique(ist_min)
                per_day.append(dict(day=Path(f).stem, rows=len(t), tokens=t["token"].nunique(),
                                    minutes=len(mins), dups=dups, traded_rows=int((t["volume"] > 0).sum()),
                                    ts_date_ok=bool(((ist_min >= day0) & (ist_min < day0 + 1440)).all())))
                n_nan += int(t["close"].isna().sum())
                n_nonpos += int((t["close"] <= 0).sum())
                n_dup_total += dups
                n_rows_total += len(t)
            pdd = pd.DataFrame(per_day)
            days |= set(pdd["day"]) if len(pdd) else set()
            rows.append(dict(underlying=ul, expiry=exp, weekday=pd.Timestamp(exp).day_name(), n_day_files=len(pdd),
                             first_day=pdd["day"].min() if len(pdd) else "", last_day=pdd["day"].max() if len(pdd) else "",
                             last_day_is_expiry=bool(len(pdd) and pdd["day"].max() == exp),
                             rows=int(pdd["rows"].sum()) if len(pdd) else 0,
                             median_tokens_per_day=float(pdd["tokens"].median()) if len(pdd) else 0,
                             median_minutes_per_day=float(pdd["minutes"].median()) if len(pdd) else 0,
                             expiry_day_tokens=int(pdd.loc[pdd["day"] == exp, "tokens"].sum()) if len(pdd) else 0,
                             expiry_day_minutes=int(pdd.loc[pdd["day"] == exp, "minutes"].sum()) if len(pdd) else 0,
                             dup_rows=int(pdd["dups"].sum()) if len(pdd) else 0,
                             files_with_ts_not_on_file_date=int((~pdd["ts_date_ok"]).sum()) if len(pdd) else 0))
        sessions[f"opt1m_{ul}"] = days
        cols = sorted({c for cs in colsets.get(ul, []) for c in cs})
        bidask = [c for c in cols if "bid" in c.lower() or "ask" in c.lower() or "depth" in c.lower()
                  or c.lower() in {"bo", "bh", "bl", "bc", "a"}]
        add_summary(dataset=f"options_1m/{ul}", resolution="1 minute per option", first=min(days), last=max(days),
                    n_sessions=len(days), n_rows=n_rows_total, n_dup=n_dup_total, n_nan_price=n_nan,
                    n_nonpos_price=n_nonpos, n_ohlc_bad=np.nan,
                    note=f"columns: {cols}; bid/ask-like columns: {bidask or 'none'}; distinct schemas: {len(colsets.get(ul, []))}")
    pd.DataFrame(rows).to_csv(OUT / "options_1m_coverage.csv", index=False)


# ---------------------------------------------------------------- extras
def audit_extras():
    for name, pat in [("nifty_1s", "nifty_1s/*.parquet"), ("chain_eod", "chain_eod/*.parquet"),
                      ("instruments", "instruments/*.parquet")]:
        files = sorted(glob.glob(str(STORE / pat)))
        stems = [Path(f).stem for f in files]
        days = [s if "-" in s else f"{s[:4]}-{s[4:6]}-{s[6:]}" for s in stems]
        cols = pq.read_schema(files[0]).names
        n = sum(pq.ParquetFile(f).metadata.num_rows for f in files)
        note = f"columns: {cols}"
        if name == "chain_eod":
            c = pd.concat([pd.read_parquet(f, columns=["bid", "ask", "underlying"]) for f in files])
            note += f"; bid non-null {int(c['bid'].notna().sum())}/{len(c)}, ask non-null {int(c['ask'].notna().sum())}/{len(c)}; underlyings {sorted(c['underlying'].unique())}"
        if name == "nifty_1s":
            c = pd.concat([pd.read_parquet(f, columns=["kind", "bo", "a"]) for f in files])
            note += f"; kinds {c['kind'].value_counts().to_dict()}; bid (bo..bc) non-null share {c['bo'].notna().mean():.3f}; ask (a) non-null share {c['a'].notna().mean():.3f}"
        add_summary(dataset=name, resolution={"nifty_1s": "1 second", "chain_eod": "end-of-day chain snapshot",
                                              "instruments": "daily contract master"}[name],
                    first=min(days), last=max(days), n_sessions=len(days), n_rows=n, n_dup=np.nan,
                    n_nan_price=np.nan, n_nonpos_price=np.nan, n_ohlc_bad=np.nan, note=note)
        sessions[name] = set(days)
    e = pd.read_parquet(STORE / "expiries.parquet")
    add_summary(dataset="expiries.parquet", resolution="listed expiries", first=e["expiry_date"].min(),
                last=e["expiry_date"].max(), n_sessions=np.nan, n_rows=len(e), n_dup=int(e.duplicated(["underlying", "expiry_date"]).sum()),
                n_nan_price=np.nan, n_nonpos_price=np.nan, n_ohlc_bad=np.nan,
                note=f"only current/future listed expiries; underlyings {sorted(e['underlying'].unique())}")


# ---------------------------------------------------------------- session presence
CORE = ["bhav_NIFTY", "bhav_BANKNIFTY", "idx_NIFTY50", "idx_NIFTYBANK", "idx_INDIAVIX", "vix_daily",
        "spot_NIFTY50", "spot_NIFTYBANK", "spot_SENSEX", "spot_INDIAVIX", "opt1m_NIFTY", "opt1m_SENSEX"]


def session_presence():
    union = set()
    for k in CORE:
        union |= {d for d in sessions[k] if d >= "2018-01-01"}
    dates = sorted(union)
    pres = pd.DataFrame({"date": dates})
    pres["weekday"] = pd.to_datetime(pres["date"]).dt.day_name()
    mism = []
    exp_cols = []
    for k in CORE:
        s = sessions[k]
        lo, hi = max(min(s), "2018-01-01"), max(s)
        pres[k] = pres["date"].isin(s).astype(int)
        inspan = (pres["date"] >= lo) & (pres["date"] <= hi)
        pres[k + "_inspan"] = inspan
        exp_cols.append(k + "_inspan")
        for dt in pres.loc[inspan & (pres[k] == 0), "date"]:
            mism.append(dict(date=dt, dataset=k, issue="missing (session present in another dataset)"))
    pres["n_present"] = pres[CORE].sum(axis=1)
    pres["n_expected"] = pres[exp_cols].sum(axis=1)
    pres["weekend"] = pres["weekday"].isin(["Saturday", "Sunday"])
    pres["flag"] = np.where(pres["n_present"] == 1, "only_one_dataset",
                            np.where(pres["n_present"] < pres["n_expected"], "partial", ""))
    pres.loc[pres["weekend"], "flag"] = pres.loc[pres["weekend"], "flag"].radd("weekend;")
    pres.drop(columns=exp_cols).to_csv(OUT / "session_presence.csv", index=False)
    m = pd.DataFrame(mism)
    # attach which other datasets had the day
    if len(m):
        m = m.merge(pres[["date", "weekday", "n_present", "n_expected"]], on="date", how="left")
    m.to_csv(OUT / "session_mismatches.csv", index=False)
    return pres, m


def main():
    audit_bhavcopy()
    ic, vd = audit_daily()
    spot, vix_rows = audit_spot(vd)
    reconcile(ic, vd, spot, vix_rows)
    audit_options_1m()
    audit_extras()
    pres, m = session_presence()
    s = pd.DataFrame(summary)
    s.to_csv(OUT / "dataset_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(s.drop(columns=["note"]).to_string())
    print("\nunion sessions:", len(pres), "weekend sessions:", int(pres["weekend"].sum()))
    if len(m):
        print("\nmissing sessions per dataset:\n", m.groupby("dataset").size().to_string())


if __name__ == "__main__":
    main()
