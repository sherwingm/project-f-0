"""Read side of the index store, for S3 studies (DECISIONS.md "S3 · index options").

    INDEX_STORE=<checkout of the index-data branch>/data/index
    from index_data.load import options_day, spot_1m, vix_1m, expiries, lot_on

Options follow the merge rule in INDEX_DATA_REPORT.md: one source per contract-day (Kotak wins where it has the day)
and Upstox's volume-0 rows are fillers, never a price. `options_day` drops those fillers; `price_at` reads the last
traded close at or before a minute, refusing it when older than `stale` minutes.
"""
from __future__ import annotations

from datetime import date, datetime, time
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .common import IST, STORE

OPEN, CLOSE = time(9, 15), time(15, 30)


def _store() -> Path:
    return Path(STORE)


def _day(d) -> date:
    return d if isinstance(d, date) and not isinstance(d, datetime) else pd.Timestamp(d).date()


@lru_cache(maxsize=8)
def expiries(underlying: str = "NIFTY") -> tuple[date, ...]:
    """Expiries that have 1-minute option files, oldest first (the directory names)."""
    root = _store() / "options_1m" / underlying
    return tuple(sorted(date.fromisoformat(p.name) for p in root.iterdir() if p.is_dir()))


def trade_days(underlying: str, expiry) -> list[date]:
    root = _store() / "options_1m" / underlying / _day(expiry).isoformat()
    return sorted(date.fromisoformat(p.stem) for p in root.glob("*.parquet"))


def merge_sources(df: pd.DataFrame) -> pd.DataFrame:
    """One source per (strike, option_type): Kotak if it has any row, else Upstox; drop volume-0 Upstox rows."""
    if df.empty:
        return df
    has_kotak = df[df["source"] == "kotak"].groupby(["strike", "option_type"]).size()
    key = pd.MultiIndex.from_frame(df[["strike", "option_type"]])
    kotak_contract = key.isin(has_kotak.index)
    keep = (kotak_contract & (df["source"] == "kotak").to_numpy()) | (~kotak_contract & (df["source"] != "kotak").to_numpy())
    out = df[keep]
    out = out[~((out["source"] == "upstox") & (out["volume"] <= 0))]
    return out.sort_values(["strike", "option_type", "timestamp"]).reset_index(drop=True)


@lru_cache(maxsize=64)
def options_day(underlying: str, expiry, day) -> pd.DataFrame:
    """All strikes of one expiry on one trading day, merged and without filler rows."""
    path = _store() / "options_1m" / underlying / _day(expiry).isoformat() / f"{_day(day).isoformat()}.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["timestamp", "strike", "option_type", "open", "high", "low", "close", "volume",
                                     "oi", "source"])
    df = pd.read_parquet(path)
    df = df[(df["timestamp"].dt.time >= OPEN) & (df["timestamp"].dt.time <= CLOSE)]
    return merge_sources(df)


def price_at(day_frame: pd.DataFrame, strike: float, option_type: str, at: datetime, stale: int = 3) -> float | None:
    """Last traded close of one contract at or before minute `at`; None when none in the last `stale` minutes."""
    rows = day_frame[(day_frame["strike"] == strike) & (day_frame["option_type"] == option_type)
                     & (day_frame["timestamp"] <= at)]
    if rows.empty:
        return None
    last = rows.iloc[-1]
    if (at - last["timestamp"]).total_seconds() > stale * 60:
        return None
    return float(last["close"])


def _monthly(folder: str, start, end) -> pd.DataFrame:
    s, e = pd.Timestamp(_day(start)), pd.Timestamp(_day(end))
    months = pd.period_range(s.to_period("M"), e.to_period("M"), freq="M")
    parts = [pd.read_parquet(p) for m in months
             if (p := _store() / "spot_1m" / folder / f"{m}.parquet").exists()]
    if not parts:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])
    df = pd.concat(parts, ignore_index=True).drop_duplicates("timestamp", keep="last").sort_values("timestamp")
    d = df["timestamp"].dt.date
    t = df["timestamp"].dt.time
    return df[(d >= s.date()) & (d <= e.date()) & (t >= OPEN) & (t <= CLOSE)].reset_index(drop=True)


def spot_1m(start, end, index: str = "NIFTY50") -> pd.DataFrame:
    return _monthly(index, start, end)


def vix_1m(start, end) -> pd.DataFrame:
    """India VIX by the minute. Rows stored at x100 or /100 (left in 2021-10 → 2023-08 by the old download) are rescaled
    to the unit of that day's daily close (vix_daily.parquet): each value is multiplied by whichever of 0.01, 1, 100
    brings it nearest the daily close (fixed 2026-10-23)."""
    v = _monthly("INDIAVIX", start, end)
    if v.empty:
        return v
    ref = _vix_daily()
    day_ref = v["timestamp"].dt.date.map(ref)
    day_ref = day_ref.fillna(v.groupby(v["timestamp"].dt.date)["close"].transform("median"))
    for col in ("open", "high", "low", "close"):
        x = v[col].astype(float)
        best = x.copy()
        err = (np.log(x / day_ref)).abs()
        for f in (0.01, 100.0):
            e = (np.log(x * f / day_ref)).abs()
            best = best.where(e >= err, x * f)
            err = err.where(e >= err, e)
        v[col] = best
    return v


@lru_cache(maxsize=1)
def _vix_daily() -> dict:
    p = _store() / "vix_daily.parquet"
    if not p.exists():
        return {}
    d = pd.read_parquet(p)
    return dict(zip(pd.to_datetime(d["date"]).dt.date, d["close"].astype(float)))


@lru_cache(maxsize=4)
def _lot_table(underlying: str) -> pd.DataFrame:
    """Option (IDO) lot per (trade date, expiry) from the bhavcopy (NewBrdLotQty, known from 2024-07-05)."""
    parts = []
    for p in sorted((_store() / "options_daily" / underlying).glob("*.parquet")):
        df = pd.read_parquet(p, columns=["TradDt", "XpryDt", "FinInstrmTp", "NewBrdLotQty"]).dropna()
        df = df[df["FinInstrmTp"] == "IDO"]
        if not df.empty:
            parts.append(df.drop_duplicates(["TradDt", "XpryDt"]))
    t = pd.concat(parts).drop_duplicates(["TradDt", "XpryDt"], keep="last")
    t["TradDt"] = pd.to_datetime(t["TradDt"]).dt.date
    t["XpryDt"] = pd.to_datetime(t["XpryDt"]).dt.date
    t["NewBrdLotQty"] = t["NewBrdLotQty"].astype(int)
    return t.sort_values(["TradDt", "XpryDt"]).reset_index(drop=True)


def lot_on(day, underlying: str = "NIFTY", expiry=None) -> int:
    """The option lot of the contract traded: (day, expiry) from the bhavcopy. Without an expiry, or when that pair is
    missing, the lot of the nearest expiry on the last known trade date on or before `day`. (Fixed 2026-10-23: it used to
    take the day's first bhavcopy row, the near-month future, so lot-75 weeklies of Jan 2025 ran at 25.)"""
    t = _lot_table(underlying)
    d = _day(day)
    if expiry is not None:
        m = t[(t["TradDt"] == d) & (t["XpryDt"] == _day(expiry))]
        if len(m):
            return int(m["NewBrdLotQty"].iloc[0])
        m = t[(t["TradDt"] <= d) & (t["XpryDt"] == _day(expiry))]
        if len(m):
            return int(m["NewBrdLotQty"].iloc[-1])
    before = t[t["TradDt"] <= d]
    if before.empty:
        raise ValueError(f"no lot size known on or before {day}")
    last = before[before["TradDt"] == before["TradDt"].iloc[-1]]
    return int(last.sort_values("XpryDt")["NewBrdLotQty"].iloc[0])


def at(day, hh: int, mm: int) -> datetime:
    """A tz-aware IST minute on `day`, matching the store's timestamps."""
    return pd.Timestamp(datetime.combine(_day(day), time(hh, mm)), tz=IST).tz_convert("Asia/Kolkata")
