"""Tier-3 RSS: mainstream financial news, used ONLY to tag analyst views (taxonomy step). Never an
event flag, never a model feature. Feeds come from config.RSS_FEEDS; a refused feed is logged and
skipped (Moneycontrol answers 403 to non-browser clients on some networks).
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from .. import config
from ..http import EventHttp, FetchError, read_fixture

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
_TAGS = re.compile(r"<[^>]+>")


def fetch(day: date, http: EventHttp | None = None, fixture: str | None = None,
          feed: str = "et_markets", url: str | None = None, max_age_days: int = 5) -> list[dict]:
    """Items published within `max_age_days` before `day` (RSS has no historical archive)."""
    if fixture:
        text = read_fixture(fixture)
    else:
        try:
            text = (http or EventHttp()).get_text(url or config.RSS_FEEDS[feed])
        except FetchError as exc:
            log.warning("rss %s: %s", feed, exc)
            return []
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        log.warning("rss %s: bad XML (%s)", feed, exc)
        return []
    out = []
    for item in root.iter("item"):
        title = _text(item, "title")
        link = _text(item, "link")
        if not title or not link:
            continue
        pub = _text(item, "pubDate")
        try:
            d = parsedate_to_datetime(pub).astimezone(IST).date() if pub else day
        except (ValueError, TypeError):
            d = day
        if not (day - timedelta(days=max_age_days) <= d <= day):
            continue
        out.append({"source": f"rss:{feed}", "source_id": hashlib.md5(link.encode()).hexdigest()[:16],
                    "symbol": None, "event_date": d.isoformat(), "event_time": None, "category": "news",
                    "subject": title, "text": _TAGS.sub(" ", _text(item, "description") or "")[:500].strip(),
                    "url": link, "extra": {"feed": feed}})
    return out


def fetch_all(day: date, http: EventHttp | None = None) -> list[dict]:
    http = http or EventHttp()
    items = []
    for feed in config.RSS_FEEDS:
        items.extend(fetch(day, http, feed=feed))
    return items


def backfill(start: date, end: date, http: EventHttp | None = None):
    """RSS has no archive: back-fill yields nothing (analyst views are live-only, tier 3)."""
    return iter(())


def _text(el, tag: str) -> str:
    t = el.findtext(tag) or ""
    return re.sub(r"^\s*<!\[CDATA\[(.*)\]\]>\s*$", r"\1", t.strip(), flags=re.S).strip()


def main() -> None:
    ap = argparse.ArgumentParser(description="tier-3 RSS (analyst-view tagging only)")
    ap.add_argument("--day", type=date.fromisoformat, default=date.today())
    ap.add_argument("--feed", default="et_markets", choices=list(config.RSS_FEEDS))
    ap.add_argument("--fixture")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    for i in fetch(a.day, feed=a.feed, fixture=a.fixture):
        print(f"{i['event_date']} {i['subject'][:100]}")


if __name__ == "__main__":
    main()
