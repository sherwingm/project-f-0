"""NSE session calendar for the paper engine: weekdays, minus any dates listed in NSE_HOLIDAYS.

    sessions_to_expiry(today, expiry)  sessions after `today` up to and including expiry day
                                       (expiry day itself = 0, the day before = 1, T-2 = 2)
    t_minus(expiry, n)                 the session n sessions before expiry (T-2 = t_minus(expiry, 2))
    next_fill_time(now)                first 09:20 IST (PAPER_QUEUE_FILL_AT) at or after `now` on a session day
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from server.config import settings

IST = timezone(timedelta(hours=5, minutes=30))


def _d(x) -> date:
    if isinstance(x, datetime):
        return x.astimezone(IST).date() if x.tzinfo else x.date()
    if isinstance(x, date):
        return x
    return datetime.strptime(str(x)[:10], "%Y-%m-%d").date()


def holidays() -> set[date]:
    return {_d(s.strip()) for s in settings.nse_holidays.split(",") if s.strip()}


def is_session(d, hol: set[date] | None = None) -> bool:
    d = _d(d)
    return d.weekday() < 5 and d not in (holidays() if hol is None else hol)


def sessions_to_expiry(today, expiry, hol: set[date] | None = None) -> int:
    t, e = _d(today), _d(expiry)
    hol = holidays() if hol is None else hol
    n, d = 0, t + timedelta(days=1)
    while d <= e:
        n += is_session(d, hol)
        d += timedelta(days=1)
    return n


def t_minus(expiry, n: int, hol: set[date] | None = None) -> date:
    """The session `n` sessions before expiry (the expiry session itself is T-0)."""
    hol = holidays() if hol is None else hol
    d = _d(expiry)
    while not is_session(d, hol):
        d -= timedelta(days=1)
    while n > 0:
        d -= timedelta(days=1)
        if is_session(d, hol):
            n -= 1
    return d


def fill_at() -> time:
    h, m = settings.paper_queue_fill_at.split(":")
    return time(int(h), int(m))


def next_fill_time(now: datetime | None = None) -> datetime:
    """When a queued (market-closed) order becomes fillable: the first session's 09:20 IST at or after now."""
    now = (now or datetime.now(IST)).astimezone(IST)
    hol, at = holidays(), fill_at()
    d = now.date()
    if not (is_session(d, hol) and now.time() <= at):
        d += timedelta(days=1)
        while not is_session(d, hol):
            d += timedelta(days=1)
    return datetime.combine(d, at, tzinfo=IST)
