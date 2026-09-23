"""Join the event store into the scan: per stock, today's tier-1/2 events, the last 10 sessions,
upcoming dates, tier-3 analyst views (labelled, never a flag) and the model-feature flags.

    "events": {
      "today": [...], "last_10": [...],
      "upcoming": [{"type": "results", "date": "2026-09-29", "sessions": 3}],
      "analyst_view": [...],
      "flags": {"results_soon": 3, "order_win": "major", "rating": "upgrade",
                "block_deal": "promoter_buy", "insider": "promoter_buy", "ban": true}
    }

Flags cover the recent window (10 sessions; ban = in-ban as of the scan date) and are what the model
(step 7) is allowed to see, tier 1-2 only. A missing events DB gives every stock an empty block and
meta.events_status = {"available": false}: the static build never fails for want of events.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

BUCKET_RANK = {"ignore": 0, "minor": 1, "significant": 2, "major": 3}
PUBLIC_KEYS = ("type", "subtype", "tier", "direction", "value_cr", "materiality", "bucket",
               "event_date", "event_time", "subject", "url", "source")


def _public(e: dict) -> dict:
    return {k: e.get(k) for k in PUBLIC_KEYS}


def _sessions_between(dates: list[str], a: str, b: str) -> int:
    """Sessions from a to b on the scan's own calendar (the union of chart dates); weekdays beyond it."""
    if a in dates and b in dates:
        return dates.index(b) - dates.index(a)
    da, db = date.fromisoformat(a), date.fromisoformat(b)
    n, d = 0, min(da, db)
    while d < max(da, db):
        d += timedelta(days=1)
        n += d.weekday() < 5
    return n if db >= da else -n


def flags_of(recent: list[dict], upcoming: list[dict], as_of: str) -> dict:
    """The model features: the strongest recent flag per family, tier 1-2 only."""
    flags: dict = {}
    results = [u for u in upcoming if u["type"] in ("results", "results_date")]
    if results:
        flags["results_soon"] = min(u["sessions"] for u in results)
    for fam, types in (("order_win", ("order_win",)), ("capacity", ("capacity",))):
        best = max((e for e in recent if e["type"] in types and e["bucket"] != "ignore"),
                   key=lambda e: BUCKET_RANK.get(e["bucket"], 0), default=None)
        if best:
            flags[fam] = best["bucket"]
    ratings = [e for e in recent if e["type"] == "rating" and e["subtype"] in ("upgrade", "downgrade")]
    if ratings:
        flags["rating"] = sorted(ratings, key=lambda e: e["event_date"])[-1]["subtype"]
    for fam in ("block_deal", "bulk_deal", "insider"):
        cands = [e for e in recent if e["type"] == fam and e["bucket"] not in ("ignore",) and e["subtype"]]
        if cands:
            best = max(cands, key=lambda e: (BUCKET_RANK.get(e["bucket"], 0), e["event_date"]))
            flags[fam] = best["subtype"]
    bans = [e for e in recent if e["type"] == "ban"]
    if bans:
        last = sorted(bans, key=lambda e: e["event_date"])[-1]
        flags["ban"] = last["subtype"] == "in"
    results_today = [e for e in recent if e["type"] == "results" and e["event_date"] == as_of]
    if results_today:
        flags["results_today"] = True
    return flags


def events_for_scan(symbols: list[str], as_of: str, calendar: list[str], db_path: Path | None = None,
                    recent_sessions: int | None = None, analyst_sessions: int | None = None,
                    upcoming_sessions: int | None = None) -> dict[str, dict]:
    """{symbol: the per-stock events block}. Missing DB -> empty blocks."""
    from .events import config as ecfg
    from .events.store import Store
    recent_sessions = recent_sessions or ecfg.EVENTS_RECENT_SESSIONS
    analyst_sessions = analyst_sessions or ecfg.EVENTS_ANALYST_SESSIONS
    upcoming_sessions = upcoming_sessions or ecfg.EVENTS_UPCOMING_SESSIONS
    path = Path(db_path or ecfg.EVENTS_DB)
    empty = {"today": [], "last_10": [], "upcoming": [], "analyst_view": [], "flags": {}}
    if not path.exists():
        return {s: dict(empty) for s in symbols}
    dates = [d for d in calendar if d <= as_of]
    since = dates[-recent_sessions] if len(dates) >= recent_sessions else (dates[0] if dates else as_of)
    a_since = dates[-analyst_sessions] if len(dates) >= analyst_sessions else since
    out = {}
    with Store(path) as store:
        for sym in symbols:
            rows = store.events_for(sym, since=since)
            t12 = [e for e in rows if e["tier"] <= 2 and e["event_date"] <= as_of]
            recent = [_public(e) for e in t12 if e["bucket"] != "ignore"]
            up = [{"type": e["type"].replace("results_date", "results"), "date": e["event_date"],
                   "sessions": _sessions_between(calendar, as_of, e["event_date"]),
                   "subject": e.get("subject") or ""}
                  for e in store.upcoming(sym, upcoming_sessions, today=date.fromisoformat(as_of))
                  if e["tier"] <= 2]
            out[sym] = {"today": [e for e in recent if e["event_date"] == as_of],
                        "last_10": recent,
                        "upcoming": sorted(up, key=lambda u: u["date"]),
                        "analyst_view": [{**_public(e), "label": "analyst view (news, not a filing)"}
                                         for e in rows if e["tier"] == 3 and a_since <= e["event_date"] <= as_of],
                        "flags": flags_of(recent, up, as_of)}
    return out


def events_status(db_path: Path | None = None) -> dict:
    """meta.events_status: whether the DB exists, its counts, and the last fetch per source."""
    from .events import config as ecfg
    from .events.run import STATUS_PATH
    path = Path(db_path or ecfg.EVENTS_DB)
    if not path.exists():
        return {"available": False}
    from .events.store import Store
    with Store(path) as store:
        counts = store.counts_by_type()
    status = json.loads(STATUS_PATH.read_text()) if STATUS_PATH.exists() else {}
    return {"available": True, "counts": counts,
            "sources": {src: {"last_success": s.get("last_success"), "error": s.get("error")}
                        for src, s in status.items()}}
