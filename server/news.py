"""Recent news headlines for one stock from Google News RSS (free, no key), cached 15 minutes per stock.

    GET /api/news/{symbol}  ->  {"items": [{title, source, url, published (ISO, IST), ts (epoch)}], "query", "fetched_at"}

Headlines only, labelled as news on the page and kept apart from exchange filings (the scan's events); nothing here
feeds a label, the verdict rules or the model.
"""
from __future__ import annotations

import logging
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
FEED = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
TTL_SECONDS = 15 * 60
MAX_ITEMS = 15
SUFFIXES = re.compile(r"\b(limited|ltd\.?|corporation|corp\.?|company|co\.)\s*$", re.I)


def query_for(symbol: str, name: str | None) -> str:
    """'"Reliance Industries" stock' for a known company name, else '"SYMBOL" NSE share'; last 7 days."""
    if name:
        short = SUFFIXES.sub("", name).strip(" .,")
        return f'"{short}" stock when:7d'
    return f'"{symbol}" NSE share when:7d'


def parse(xml_text: str, limit: int = MAX_ITEMS) -> list[dict]:
    items = []
    for it in ET.fromstring(xml_text).iter("item"):
        title = (it.findtext("title") or "").strip()
        src = it.find("source")
        source = (src.text or "").strip() if src is not None else ""
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3]
        try:
            dt = parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(IST)
        except (TypeError, ValueError):
            dt = None
        items.append({"title": title, "source": source, "url": (it.findtext("link") or "").strip(),
                      "published": dt.isoformat(timespec="minutes") if dt else None,
                      "ts": int(dt.timestamp()) if dt else None})
    items.sort(key=lambda x: x["ts"] or 0, reverse=True)
    return items[:limit]


class News:
    def __init__(self, get=None, ttl: int = TTL_SECONDS):
        self._get = get or _http_get
        self.ttl = ttl
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()

    def get(self, symbol: str, name: str | None = None) -> dict:
        with self._lock:
            hit = self._cache.get(symbol)
            if hit and time.time() - hit[0] < self.ttl:
                return hit[1]
        q = query_for(symbol, name)
        try:
            items, error = parse(self._get(FEED.format(q=quote_plus(q)))), None
        except Exception as exc:  # noqa: BLE001 - the page shows the error instead of headlines
            log.warning("news %s: %s", symbol, exc)
            items, error = [], f"{type(exc).__name__}: {exc}"
        out = {"symbol": symbol, "query": q, "items": items, "error": error,
               "fetched_at": datetime.now(IST).strftime("%H:%M")}
        if error is None:
            with self._lock:
                self._cache[symbol] = (time.time(), out)
        return out


def _http_get(url: str) -> str:
    import requests
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (fo-scanner news reader)"})
    r.raise_for_status()
    return r.text
