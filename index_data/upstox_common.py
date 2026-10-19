"""Upstox client shared by the backfill and the reconciliation: token, rate limits, 429 backoff, the Plus-plan stop.

Token, first found wins: env UPSTOX_ANALYTICS_TOKEN (the free 1-year read-only token; it reaches the expired-instruments
API, see DATA_ACCESS_AUDIT.md), env UPSTOX_ACCESS_TOKEN, data/index/.upstox_token (written by upstox_login.py).
Limits (Upstox docs, read 2026-10-19): 50/s, 500/min, 2,000 per 30 minutes per user; the sustained rate is set from
the 30-minute cap. The live server shares the token, so a job takes 1,800 / 30 min (400 / min) outside market hours and
1,000 / 30 min (250 / min) from 09:00 to 15:45 IST on weekdays, leaving the server its share during a session.
"""
from __future__ import annotations

import os
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from datetime import time as dtime
from urllib.parse import quote

import requests

from .common import SMALL

BASE = "https://api.upstox.com"
UNDERLYING_KEY = {"NIFTY": "NSE_INDEX|Nifty 50", "BANKNIFTY": "NSE_INDEX|Nifty Bank", "SENSEX": "BSE_INDEX|SENSEX"}
PER_30MIN, PER_MIN = 1000, 250                    # during market hours
NIGHT_30MIN, NIGHT_MIN = 1800, 400                # outside them (documented: 2,000 / 500)
IST = timezone(timedelta(hours=5, minutes=30))


def caps(now: datetime | None = None) -> tuple[int, int]:
    """(per 30 min, per min) for a job right now: the market-hours caps 09:00-15:45 IST on weekdays, else the night caps."""
    now = now or datetime.now(IST)
    market = now.weekday() < 5 and dtime(9, 0) <= now.time() <= dtime(15, 45)
    return (PER_30MIN, PER_MIN) if market else (NIGHT_30MIN, NIGHT_MIN)


class PlusPlanRequired(RuntimeError):
    """UDAPI1149: the expired-instruments API needs Upstox Plus on this account."""


def token() -> str:
    for v in (os.getenv("UPSTOX_ANALYTICS_TOKEN"), os.getenv("UPSTOX_ACCESS_TOKEN")):
        if v:
            return v
    f = SMALL / ".upstox_token"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    raise SystemExit("no Upstox token: set UPSTOX_ANALYTICS_TOKEN (GitHub secret) or run python -m index_data.upstox_login")


class Upstox:
    def __init__(self):
        self.tok = token()
        self.h = {"Accept": "application/json", "Authorization": f"Bearer {self.tok}"}
        self.calls = 0
        self._win30: deque = deque()
        self._win60: deque = deque()

    def _pace(self) -> None:
        now = time.monotonic()
        c30, c60 = caps()
        for w, span, cap in ((self._win30, 1800, c30 - 20), (self._win60, 60, c60 - 10)):
            while w and now - w[0] > span:
                w.popleft()
            if len(w) >= cap:
                time.sleep(span - (now - w[0]) + 0.5)
                now = time.monotonic()
        time.sleep(0.05)

    # 429 waits: another job or the live server on the same token can use up the shared 30-minute cap, so a 429 is
    # waited out (about 35 minutes in all, longer than one 30-minute window) instead of ending a five-hour run
    RATE_WAITS = (30, 60, 120, 300, 600, 600, 600)

    def get(self, path: str, params: dict | None = None, retries: int = 5) -> dict:
        attempt = limited = 0
        while attempt < retries:
            self._pace()
            r = requests.get(BASE + path, headers=self.h, params=params, timeout=60)
            now = time.monotonic()
            self._win30.append(now)
            self._win60.append(now)
            self.calls += 1
            if r.status_code == 429:
                if limited >= len(self.RATE_WAITS):
                    break
                time.sleep(self.RATE_WAITS[limited])
                limited += 1
                continue
            attempt += 1
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            errs = body.get("errors") or [] if isinstance(body, dict) else []
            codes = {e.get("errorCode") or e.get("error_code") for e in errs if isinstance(e, dict)}
            if "UDAPI1149" in codes:
                raise PlusPlanRequired(str(errs)[:300])
            if r.status_code >= 500 and attempt < retries:
                time.sleep(3 * attempt)
                continue
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code} {path}: {str(errs or r.text)[:300]}".replace(self.tok, "***"))
            return body
        raise RuntimeError(f"{path}: still rate-limited after {limited} waits (~{sum(self.RATE_WAITS) // 60} min) or {retries} server errors")

    @staticmethod
    def q(key: str) -> str:
        return quote(key, safe="")
