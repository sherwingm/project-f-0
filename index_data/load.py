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
    return _monthly("INDIAVIX", start, end)


@lru_cache(maxsize=1)
def _lots(underlying: str) -> pd.Series:
    parts = []
    for p in sorted((_store() / "options_daily" / underlying).glob("*.parquet")):
        df = pd.read_parquet(p, columns=["TradDt", "NewBrdLotQty"]).dropna()
        if not df.empty:
            parts.append(df.drop_duplicates("TradDt"))
    s = pd.concat(parts).drop_duplicates("TradDt", keep="last")
    s["TradDt"] = pd.to_datetime(s["TradDt"]).dt.date
    return s.set_index("TradDt")["NewBrdLotQty"].astype(int).sort_index()


def lot_on(day, underlying: str = "NIFTY") -> int:
    """Lot size on a trading day from the bhavcopy (known from 2024-07-05); the last known value on or before it."""
    s = _lots(underlying)
    s = s[s.index <= _day(day)]
    if s.empty:
        raise ValueError(f"no lot size known on or before {day}")
    return int(s.iloc[-1])


def at(day, hh: int, mm: int) -> datetime:
    """A tz-aware IST minute on `day`, matching the store's timestamps."""
    return pd.Timestamp(datetime.combine(_day(day), time(hh, mm)), tz=IST).tz_convert("Asia/Kolkata")
