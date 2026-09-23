"""Every threshold and knob of the event feed, with env overrides. Defaults are the spec's.

Buckets are (ignore-below, minor-below, significant-below) as percentages; at or above the last bound the
bucket is `major`. Bounds are inclusive at the lower edge of the named bucket (1% of market cap is `minor`).
"""
from __future__ import annotations

import os
from pathlib import Path

from ..build import ROOT


def _floats(name: str, default: str) -> tuple[float, float, float]:
    v = tuple(float(x) for x in os.getenv(name, default).split(","))
    if len(v) != 3 or list(v) != sorted(v):
        raise ValueError(f"{name} must be three ascending numbers, got {v}")
    return v  # type: ignore[return-value]


EVENTS_DB = Path(os.getenv("EVENTS_DB", ROOT / "data" / "events.sqlite"))
EVENTS_RATE_SECONDS = float(os.getenv("EVENTS_RATE_SECONDS", "1.0"))     # never below 1 request/second apart
EVENTS_TIMEOUT = int(os.getenv("EVENTS_TIMEOUT", "30"))
EVENTS_BACKOFF_START = float(os.getenv("EVENTS_BACKOFF_START", "2"))     # seconds, doubled per 429/403, 5 tries
EVENTS_BACKOFF_TRIES = int(os.getenv("EVENTS_BACKOFF_TRIES", "5"))

# ₹-value buckets, % of market cap (orders and capacity/capex announcements)
ORDER_BUCKETS_PCT = _floats("EVENT_ORDER_BUCKETS_PCT", "1,5,20")
# block/bulk deals, % of free float (fallback: of shares outstanding)
DEAL_BUCKETS_PCT = _floats("EVENT_DEAL_BUCKETS_PCT", "0.5,2,5")
# insider (PIT/SAST), % of holding traded
INSIDER_BUCKETS_PCT = _floats("EVENT_INSIDER_BUCKETS_PCT", "0.1,1,3")

# windows used by the scan join (sessions)
EVENTS_RECENT_SESSIONS = int(os.getenv("EVENTS_RECENT_SESSIONS", "10"))
EVENTS_ANALYST_SESSIONS = int(os.getenv("EVENTS_ANALYST_SESSIONS", "5"))
EVENTS_UPCOMING_SESSIONS = int(os.getenv("EVENTS_UPCOMING_SESSIONS", "10"))

# registered credit rating agencies (SEBI): a "rating" event must name one, or it is discarded
REGISTERED_CRAS = tuple(s.strip() for s in os.getenv(
    "EVENT_REGISTERED_CRAS",
    "CRISIL,ICRA,CARE,India Ratings,Acuite,Acuité,Brickwork,Infomerics").split(","))

# tier-3 RSS feeds: analyst-view tagging only, never an event flag
RSS_FEEDS = {
    "et_markets": os.getenv("EVENT_RSS_ET", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    "moneycontrol": os.getenv("EVENT_RSS_MC", "https://www.moneycontrol.com/rss/marketreports.xml"),
    "business_standard": os.getenv("EVENT_RSS_BS", "https://www.business-standard.com/rss/markets-106.rss"),
}

FIXTURES = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"
