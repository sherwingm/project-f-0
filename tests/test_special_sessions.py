"""server/sessions.py is_index_session: announced full weekend sessions count for the index programs only."""
from datetime import date

import pytest

from server import sessions as S
from server.config import settings

SAT, SUN, MON = date(2026, 11, 7), date(2026, 11, 8), date(2026, 11, 9)


@pytest.fixture(autouse=True)
def calendar(monkeypatch):
    monkeypatch.setattr(S, "_file_special", lambda: frozenset())
    monkeypatch.setattr(S, "_file_holidays", lambda: frozenset({SUN}))
    monkeypatch.setattr(settings, "nse_holidays", "")
    monkeypatch.setattr(settings, "special_sessions", "")


def test_weekend_is_not_a_session_by_default():
    assert not S.is_index_session(SAT) and not S.is_index_session(SUN) and S.is_index_session(MON)


def test_announced_saturday_counts_for_the_index_programs_only(monkeypatch):
    monkeypatch.setattr(settings, "special_sessions", "2026-11-07")
    assert S.is_index_session(SAT)
    assert not S.is_session(SAT)                               # S1 / S2 timing is unchanged
    assert S.sessions_to_expiry(date(2026, 11, 6), date(2026, 11, 9)) == 1


def test_a_holiday_wins_over_a_special_session(monkeypatch):
    monkeypatch.setattr(settings, "special_sessions", "2026-11-08")   # listed by mistake; it is also a holiday
    assert not S.is_index_session(SUN)


def test_special_sessions_file(monkeypatch):
    monkeypatch.setattr(S, "_file_special", lambda: frozenset({SAT}))
    assert S.is_index_session(SAT) and S.special_sessions() == {SAT}
