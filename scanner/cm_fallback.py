"""Scan freshness: when eod2_data lags NSE, fill the missing sessions from NSE's own files.

eod2_data (a third-party mirror) sometimes stops updating for days (it stopped at 2026-09-25). The build then
rolls nothing forward: the scan date, its prices and its option chains stay on the old session. This module
downloads NSE's cash-market bhavcopy (UDiFF, the same archive host as the F&O file) for every weekday after
eod2's last session, and appends those sessions to the price frames **in memory only** (the eod2 files are never
touched, so eod2's adjusted history takes over again once it catches up). NIFTY 50 closes come from NSE's
daily index-close file. Every filled day is logged and listed in the scan's meta (`price_fallback_days`).

Caveat: eod2 is adjusted for corporate actions and the bhavcopy is not; a split inside the gap shows as a jump
until eod2 catches up.
"""
from __future__ import annotations

import io
import logging
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from .nse_fo import NSE_HEADERS

log = logging.getLogger("cm_fallback")
CM_URL = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{ymd}_F_0000.csv.zip"
INDEX_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{dmy}.csv"
IST = timezone(timedelta(hours=5, minutes=30))
MAX_GAP_DAYS = 15                                    # never try to fill more than this many calendar days


def download_cm(day: date, cache_dir: Path | None = None, get=None) -> pd.DataFrame | None:
    """EQ-series rows of the cash-market bhavcopy for `day`: symbol, Open, High, Low, Close, Volume;
    None when NSE has no file (holiday, not yet published)."""
    f = cache_dir / f"cm_bhavcopy_{day:%Y%m%d}.csv" if cache_dir else None
    if f and f.exists():
        return pd.read_csv(f)
    get = get or (lambda url: requests.get(url, headers=NSE_HEADERS, timeout=60))
    r = get(CM_URL.format(ymd=day.strftime("%Y%m%d")))
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        raw = pd.read_csv(zf.open(name))
    raw = raw[raw["SctySrs"].astype(str).str.strip() == "EQ"]
    df = pd.DataFrame({"symbol": raw["TckrSymb"].astype(str).str.strip(), "Open": raw["OpnPric"],
                       "High": raw["HghPric"], "Low": raw["LwPric"], "Close": raw["ClsPric"],
                       "Volume": raw["TtlTradgVol"]}).reset_index(drop=True)
    if f:
        f.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(f, index=False)
    return df


def download_index_close(day: date, name: str = "nifty 50", get=None) -> float | None:
    get = get or (lambda url: requests.get(url, headers=NSE_HEADERS, timeout=60))
    r = get(INDEX_URL.format(dmy=day.strftime("%d%m%Y")))
    if r.status_code == 404:
        return None
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = [str(c).strip() for c in df.columns]
    row = df[df["Index Name"].astype(str).str.strip().str.lower() == name.lower()]
    return float(row["Closing Index Value"].iloc[0]) if len(row) else None


def missing_days(last: date, today: date | None = None) -> list[date]:
    """Weekdays after eod2's last session up to today (IST), at most MAX_GAP_DAYS calendar days."""
    today = today or datetime.now(IST).date()
    out, d = [], last + timedelta(days=1)
    while d <= today and (d - last).days <= MAX_GAP_DAYS:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def fill(frames: dict[str, pd.DataFrame], cache_dir: Path | None = None, today: date | None = None,
         download=download_cm) -> list[str]:
    """Append the sessions eod2 lacks to every frame (in place) from NSE's bhavcopy; returns the filled days."""
    if not frames:
        return []
    last = pd.Series({s: f.index[-1] for s, f in frames.items() if len(f)}).mode().iloc[0].date()
    filled = []
    for d in missing_days(last, today):
        try:
            cm = download(d, cache_dir)
        except Exception as exc:  # noqa: BLE001 - a failed day is skipped, never fatal
            log.warning("cash-market bhavcopy %s unavailable (%s)", d, exc)
            continue
        if cm is None or cm.empty:
            continue                                   # holiday or not published yet
        by = cm.set_index("symbol")
        ts = pd.Timestamp(d)
        n = 0
        for sym, f in frames.items():
            if sym in by.index and (not len(f) or f.index[-1] < ts):
                r = by.loc[sym]
                frames[sym] = pd.concat([f, pd.DataFrame([{c: float(r[c]) for c in ("Open", "High", "Low", "Close", "Volume")}],
                                                         index=pd.DatetimeIndex([ts], name=f.index.name))])
                n += 1
        filled.append(d.isoformat())
        log.warning("price fallback: %s filled from NSE's cash-market bhavcopy for %d stocks (eod2 ends %s)", d, n, last)
    return filled


def fill_index(closes: pd.Series, days: list[str], get_close=download_index_close) -> pd.Series:
    """Append NIFTY 50 closes for the filled days that the index series lacks."""
    for d in days:
        ts = pd.Timestamp(d)
        if len(closes) and closes.index[-1] >= ts:
            continue
        try:
            c = get_close(date.fromisoformat(d))
        except Exception as exc:  # noqa: BLE001
            log.warning("index close %s unavailable (%s)", d, exc)
            continue
        if c:
            closes = pd.concat([closes, pd.Series([c], index=pd.DatetimeIndex([ts]))])
            log.warning("price fallback: NIFTY 50 close for %s from NSE's index file", d)
    return closes
