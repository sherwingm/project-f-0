"""Upstox client shared by the backfill and the reconciliation: token, rate limits, 429 backoff, the Plus-plan stop.

Token, first found wins: env UPSTOX_ANALYTICS_TOKEN (the free 1-year read-only token; it reaches the expired-instruments
API, see DATA_ACCESS_AUDIT.md), env UPSTOX_ACCESS_TOKEN, data/index/.upstox_token (written by upstox_login.py).
Limits (Upstox docs): 25/s, 250/min, 1,000 per 30 minutes; the sustained rate is set from the 30-minute cap.
"""
from __future__ import annotations

import os
import time
from collections import deque
from urllib.parse import quote

import requests

from .common import SMALL

BASE = "https://api.upstox.com"
UNDERLYING_KEY = {"NIFTY": "NSE_INDEX|Nifty 50", "BANKNIFTY": "NSE_INDEX|Nifty Bank", "SENSEX": "BSE_INDEX|SENSEX"}
PER_30MIN, PER_MIN = 1000, 250


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
        for w, span, cap in ((self._win30, 1800, PER_30MIN - 20), (self._win60, 60, PER_MIN - 10)):
            while w and now - w[0] > span:
                w.popleft()
            if len(w) >= cap:
                time.sleep(span - (now - w[0]) + 0.5)
                now = time.monotonic()
        time.sleep(0.05)

    def get(self, path: str, params: dict | None = None, retries: int = 5) -> dict:
        for attempt in range(retries):
            self._pace()
            r = requests.get(BASE + path, headers=self.h, params=params, timeout=60)
            now = time.monotonic()
            self._win30.append(now)
            self._win60.append(now)
            self.calls += 1
            if r.status_code == 429:
                time.sleep(min(60, 5 * 2 ** attempt))
                continue
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            errs = body.get("errors") or [] if isinstance(body, dict) else []
            codes = {e.get("errorCode") or e.get("error_code") for e in errs if isinstance(e, dict)}
            if "UDAPI1149" in codes:
                raise PlusPlanRequired(str(errs)[:300])
            if r.status_code >= 500 and attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code} {path}: {str(errs or r.text)[:300]}".replace(self.tok, "***"))
            return body
        raise RuntimeError(f"{path}: still rate-limited after {retries} tries")

    @staticmethod
    def q(key: str) -> str:
        return quote(key, safe="")
