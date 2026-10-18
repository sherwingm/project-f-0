"""§4 Index spot and India VIX 1-minute backfill (Kotak), plus India VIX daily from yfinance with a cross-check.

    KOTAK_CONSUMER_KEY=... INDEX_STORE=... python -m index_data.backfill_spot [--from 2021-10-25]

Nifty 50, Nifty Bank, SENSEX, INDIA VIX, 1-minute, from the oldest date Kotak allows (5 years) to today in < 30-day
windows -> STORE/spot_1m/<name>/<YYYY-MM>.parquet. Rows before 09:15 are dropped. VIX scaling: Kotak's older VIX
minutes come x100 (open 1622.25 for VIX 16.2): rows with open > 200 are divided by 100, counted and dated.
India VIX daily (yfinance ^INDIAVIX, max) -> STORE/vix_daily.parquet, compared with Kotak `D` candles 2022-2026:
mismatches above 1 % are reported. Restart-safe: months already on disk are skipped (except the current one).
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import date, timedelta

import pandas as pd

from .common import SMALL, STORE, Kotak, candles_frame, read_json, today_ist, upsert_parquet, write_json

log = logging.getLogger("index_data.backfill_spot")
SERIES = {"NIFTY50": "nse_cm|Nifty 50", "NIFTYBANK": "nse_cm|Nifty Bank", "SENSEX": "bse_cm|SENSEX",
          "INDIAVIX": "nse_cm|INDIA VIX"}


def fix_vix(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    bad = df["open"] > 200
    info = {"rows_corrected": int(bad.sum())}
    if bad.any():
        info["from"], info["to"] = str(df.loc[bad, "timestamp"].min()), str(df.loc[bad, "timestamp"].max())
        df.loc[bad, ["open", "high", "low", "close"]] = df.loc[bad, ["open", "high", "low", "close"]] / 100.0
    return df, info


def backfill(k: Kotak, start: date, end: date, store=STORE) -> dict:
    out = {}
    for name, neo in SERIES.items():
        t0, rows, vix = time.monotonic(), 0, {"rows_corrected": 0}
        months = pd.period_range(start, end, freq="M")
        for m in months:
            p = store / "spot_1m" / name / f"{m}.parquet"
            if p.exists() and str(m) != end.strftime("%Y-%m"):
                continue
            a = max(m.start_time.date(), start)
            b = min(m.end_time.date(), end)
            f = candles_frame(k.history_range(neo, "1min", a, b))          # a month can exceed one 29-day call
            f = f[f["timestamp"].dt.strftime("%H:%M") >= "09:15"]
            if name == "INDIAVIX" and len(f):
                f, info = fix_vix(f)
                vix["rows_corrected"] += info["rows_corrected"]
                if info.get("from"):
                    vix["from"] = min(vix.get("from", info["from"]), info["from"])
                    vix["to"] = max(vix.get("to", info["to"]), info["to"])
            if len(f):
                f["source"] = "kotak"
                rows += len(f)
                upsert_parquet(p, f, ["timestamp"])
        out[name] = {"rows_added": rows, "runtime_s": round(time.monotonic() - t0), **({"vix_fix": vix} if name == "INDIAVIX" else {})}
        log.info("%s: %s", name, out[name])
    return out


def vix_daily(k: Kotak, store=STORE) -> dict:
    import yfinance as yf
    y = yf.download("^INDIAVIX", period="max", interval="1d", auto_adjust=False, progress=False)
    if isinstance(y.columns, pd.MultiIndex):
        y.columns = y.columns.get_level_values(0)
    y = y.reset_index().rename(columns={"Date": "date"})
    y["date"] = pd.to_datetime(y["date"]).dt.strftime("%Y-%m-%d")
    y = y[["date", "Open", "High", "Low", "Close"]].rename(columns=str.lower)
    store.mkdir(parents=True, exist_ok=True)
    y.to_parquet(store / "vix_daily.parquet", index=False)
    kd = []
    a = date(2022, 1, 1)
    while a <= today_ist():
        b = min(today_ist(), a + timedelta(days=170))
        kd += k.history(SERIES["INDIAVIX"], "D", a.isoformat(), b.isoformat())
        a = b + timedelta(days=1)
    kf = candles_frame(kd)
    kf["date"] = kf["timestamp"].dt.strftime("%Y-%m-%d")
    kf.loc[kf["close"] > 200, "close"] = kf["close"] / 100.0
    m = y.merge(kf[["date", "close"]], on="date", suffixes=("_yf", "_kotak"))
    m["diff_pct"] = (m["close_kotak"] / m["close_yf"] - 1) * 100
    bad = m[m["diff_pct"].abs() > 1]
    return {"yf_rows": len(y), "yf_first": y["date"].min(), "yf_last": y["date"].max(), "compared_days": len(m),
            "mismatch_gt_1pct": len(bad), "worst": bad.reindex(bad["diff_pct"].abs().sort_values(ascending=False).index)
            .head(10)[["date", "close_yf", "close_kotak", "diff_pct"]].round(3).to_dict("records")}


def coverage(store=STORE) -> dict:
    out = {}
    for name in SERIES:
        files = sorted((store / "spot_1m" / name).glob("*.parquet"))
        if files:
            out[name] = {"first_month": files[0].stem, "last_month": files[-1].stem, "months": len(files)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="index spot / VIX 1-minute backfill")
    ap.add_argument("--from", dest="start", default=None, help="default: 5 years back (Kotak's limit)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    end = today_ist() - timedelta(days=1)
    start = date.fromisoformat(a.start) if a.start else end.replace(year=end.year - 5) + timedelta(days=3)
    k, t0 = Kotak(), time.monotonic()
    res = {"window": [start.isoformat(), end.isoformat()], "series": backfill(k, start, end)}
    try:
        res["vix_daily"] = vix_daily(k)
    except Exception as exc:  # noqa: BLE001
        res["vix_daily"] = {"error": str(exc)[:300]}
    res.update(calls=k.calls, runtime_s=round(time.monotonic() - t0), coverage=coverage())
    st = read_json(SMALL / "status.json", {}) or {}
    write_json(SMALL / "status.json", {**st, "spot_backfill": res})
    print(res)


if __name__ == "__main__":
    main()
