"""Shared pieces of the index data layer: paths, the Kotak client, rate-limited history calls, Parquet writes.

Large Parquet goes under STORE (env INDEX_STORE; in the Actions a checkout of the `index-data` branch). Small JSON
(status, coverage, next expiries) goes under SMALL = data/index on `main`.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STORE = Path(os.getenv("INDEX_STORE") or ROOT / "data" / "index")
SMALL = ROOT / "data" / "index"
IST = timezone(timedelta(hours=5, minutes=30))
HISTORY_MIN_INTERVAL = 1.5                 # seconds between Kotak historical_data calls (server/kotak.py:255)
MAX_DAYS_PER_CALL = 29                     # Kotak: 1-min / 5-min ranges must be under 30 days (DATA_ACCESS_AUDIT.md)
OLDEST_YEARS = 5                           # Kotak: "fromDate cannot be older than 5 years"

log = logging.getLogger("index_data")


def today_ist() -> date:
    return datetime.now(IST).date()


class Kotak:
    """The Kotak Neo client with the consumer key only (data calls need no login), and spaced history calls."""

    def __init__(self, consumer_key: str | None = None):
        from server.kotak import KotakSession
        key = consumer_key or os.getenv("KOTAK_CONSUMER_KEY", "")
        if not key:
            raise SystemExit("KOTAK_CONSUMER_KEY is not set (GitHub secret / Render environment)")
        self.session = KotakSession(key)
        self.calls = 0
        self._last = 0.0
        self._lock = threading.Lock()

    def client(self):
        return self.session.client()

    def history(self, neosymbol: str, interval: str, start: str, end: str, retries: int = 3) -> list[list]:
        """Raw candles [[iso time, open, high, low, close, volume], ...] for one call (start..end inclusive)."""
        from server.kotak import redact
        for attempt in range(retries):
            with self._lock:
                wait = HISTORY_MIN_INTERVAL - (time.monotonic() - self._last)
                if wait > 0:
                    time.sleep(wait)
                try:
                    resp = self.client().historical_data(neosymbol=neosymbol, interval=interval,
                                                         from_date=start, to_date=end)
                except Exception as exc:  # noqa: BLE001 - dropped connections: retry with a pause
                    resp = {"error": f"connection: {exc}"}
                finally:
                    self._last = time.monotonic()
                    self.calls += 1
            data = resp.get("data") if isinstance(resp, dict) else None
            if isinstance(data, dict) and isinstance(data.get("candles"), list):
                return data["candles"]
            msg = redact(str(resp))[:300]
            if "Rate limit" in msg or "429" in msg or msg.startswith("{'error': 'connection"):
                time.sleep(5 * (attempt + 1))
                continue
            if "Invalid neosymbol" in msg or "older than" in msg or "exceeds maximum" in msg:
                raise ValueError(msg)
            if attempt == retries - 1:
                raise RuntimeError(msg)
            time.sleep(2 * (attempt + 1))
        return []

    def history_range(self, neosymbol: str, interval: str, start: date, end: date) -> list[list]:
        """Candles over any range, in windows of MAX_DAYS_PER_CALL days, oldest allowed first."""
        oldest = today_ist().replace(year=today_ist().year - OLDEST_YEARS) + timedelta(days=2)
        start = max(start, oldest)
        out, a = [], start
        while a <= end:
            b = min(end, a + timedelta(days=MAX_DAYS_PER_CALL - 1))
            out += self.history(neosymbol, interval, a.isoformat(), b.isoformat())
            a = b + timedelta(days=1)
        return out


def candles_frame(rows: list[list]) -> pd.DataFrame:
    """Kotak / Upstox candle rows -> timestamp (IST, tz-aware), open, high, low, close, volume, oi (oi when present)."""
    cols = ["timestamp", "open", "high", "low", "close", "volume", "oi"]
    if not rows:                                   # typed, so .dt works on an empty frame
        return pd.DataFrame({"timestamp": pd.Series([], dtype="datetime64[ns, Asia/Kolkata]"),
                             **{c: pd.Series([], dtype="float64") for c in cols[1:]}})
    df = pd.DataFrame([list(r) + [None] * (7 - len(r)) for r in rows], columns=cols)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("Asia/Kolkata")
    for c in cols[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)


def upsert_parquet(path: Path, df: pd.DataFrame, keys: list[str]) -> int:
    """Append df to the Parquet file at path, deduplicated on keys (the new rows win). Returns the file's rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old = pd.read_parquet(path)
        df = pd.concat([old, df], ignore_index=True)
    df = df.drop_duplicates(keys, keep="last").sort_values(keys).reset_index(drop=True)
    df.to_parquet(path, index=False)
    return len(df)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
