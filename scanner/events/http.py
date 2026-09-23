"""One HTTP door for every event fetcher: browser-like headers, NSE cookie warmup, a shared
1-request-per-second limiter across all sources, and exponential backoff on 429/403/5xx.

NSE refuses datacenter IPs and bare clients; from a home connection it answers once the session
carries the cookies its home page sets (the home page itself may answer 403 and still set them).
"""
from __future__ import annotations

import json
import logging
import threading
import time

import requests

from . import config

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

_pace_lock = threading.Lock()
_last_request = 0.0


def _pace() -> None:
    """At most one request per EVENTS_RATE_SECONDS, across every fetcher and thread."""
    global _last_request
    with _pace_lock:
        wait = config.EVENTS_RATE_SECONDS - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()


class FetchError(RuntimeError):
    """A source that could not be fetched after retries; the run logs it and continues."""


class EventHttp:
    def __init__(self, timeout: int | None = None):
        self.s = requests.Session()
        self.s.headers.update(HEADERS)
        self.timeout = timeout or config.EVENTS_TIMEOUT
        self._warmed = False

    def warmup(self, force: bool = False) -> None:
        if self._warmed and not force:
            return
        _pace()
        try:
            r = self.s.get("https://www.nseindia.com", timeout=self.timeout)
            log.debug("nseindia.com warmup: HTTP %s, %d cookies", r.status_code, len(self.s.cookies))
        except requests.RequestException as exc:
            log.warning("warmup failed (%s); continuing without cookies", exc)
        self._warmed = True

    def get(self, url: str, referer: str | None = None, warm: bool = True) -> requests.Response:
        if warm and "nseindia.com" in url:
            self.warmup()
        headers = {"Referer": referer} if referer else {}
        backoff = config.EVENTS_BACKOFF_START
        last = "no attempt made"
        for attempt in range(config.EVENTS_BACKOFF_TRIES):
            _pace()
            try:
                r = self.s.get(url, headers=headers, timeout=self.timeout)
                if r.status_code == 200:
                    return r
                last = f"HTTP {r.status_code}"
                if r.status_code not in (403, 429, 500, 502, 503, 504):
                    break
                if r.status_code == 403 and "nseindia.com" in url:
                    self.warmup(force=True)                    # cookies expired mid-run
            except requests.RequestException as exc:
                last = f"{type(exc).__name__}: {exc}"
            log.debug("retry %d for %s (%s); backing off %.0fs", attempt + 1, url, last, backoff)
            time.sleep(backoff)
            backoff *= 2
        raise FetchError(f"{url}: {last}")

    def get_json(self, url: str, referer: str | None = None):
        r = self.get(url, referer)
        try:
            return r.json()
        except json.JSONDecodeError as exc:
            raise FetchError(f"{url}: not JSON ({r.text[:120]!r})") from exc

    def get_text(self, url: str, referer: str | None = None) -> str:
        return self.get(url, referer).text

    def download(self, url: str, referer: str | None = None, max_bytes: int = 5_000_000) -> bytes:
        r = self.get(url, referer)
        return r.content[:max_bytes]


def read_fixture(name: str) -> str:
    return (config.FIXTURES / name).read_text(encoding="utf-8")
