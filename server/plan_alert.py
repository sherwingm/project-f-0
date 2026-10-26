"""Telegram messages about the NEXT session's plan (the user, 2026-10-26: "I want the next session alert in the telegram").

Pure text builders (the server sends them through server/alerts.py, see server/app.py _phone_tick):

    plan_rows(meta, day)      what the paper account will try to buy on `day`, from the scan's lists, and whether each list
                              is really for that day (the same rules the trader and the page use)
    ready_text(meta, day)     "the list for <day> is ready" (sent once, when it lands)
    morning_text(meta, day)   the plan at 09:08, or a loud warning when the lists are not for today
    late_text(meta, day)      a list that arrived after the open

A list that is not for `day` is never described as the plan: that was the 26 Oct failure (Friday's list shown on Monday).
"""
from __future__ import annotations

from datetime import date, timedelta

from server import sessions
from server.rules import forward_is_current, signals_for


def next_session(after: date) -> date:
    d = after + timedelta(days=1)
    while not sessions.is_session(d):
        d += timedelta(days=1)
    return d


def target_day(today: date, minutes_of_day: int) -> date:
    """The session the next list is for: today before the open (09:15) on a session day, else the next session."""
    if sessions.is_session(today) and minutes_of_day < 9 * 60 + 15:
        return today
    return next_session(today)


def plan_rows(meta: dict, day: date) -> dict:
    fd, fw = (meta or {}).get("fade") or {}, (meta or {}).get("forward") or {}
    fade_ok = fd.get("session") == day.isoformat()
    fw_ok = forward_is_current(fw, day)
    fade = [f"{s['symbol']} {'PUT' if s.get('side') == 'PE' else 'CALL'}" for s in fd.get("signals", [])] if fade_ok else []
    arms = [f"{r['symbol']} CALL (Arm {'/'.join(r.get('arms', []))})" for r in signals_for(fw, day)] if fw_ok else []
    return {"fade_ok": fade_ok, "fw_ok": fw_ok, "fade": fade, "arms": arms, "fade_session": fd.get("session"),
            "fw_last": fw.get("last_session")}


def _lines(r: dict) -> list[str]:
    out = []
    if r["fade_ok"]:
        out.append("Fade (results day): " + (", ".join(r["fade"]) if r["fade"] else "no stock"))
    if r["fw_ok"]:
        out.append("Arm A/B: " + (", ".join(r["arms"]) if r["arms"] else "no stock"))
    return out


def ready_text(meta: dict, day: date) -> str | None:
    r = plan_rows(meta, day)
    if not (r["fade_ok"] or r["fw_ok"]):
        return None
    return "\n".join([f"📋 List for {day:%a %d %b} is ready"] + _lines(r) +
                     ["Bought from 09:15 at the live ask, paper only." if r["fade"] or r["arms"] else "No trade planned."])


def morning_text(meta: dict, day: date) -> tuple[str, bool]:
    """(text, ok): ok is False when a list that should be for today is missing."""
    r = plan_rows(meta, day)
    if r["fade_ok"] and r["fw_ok"]:
        n = len(r["fade"]) + len(r["arms"])
        return "\n".join([f"🌅 Today {day:%a %d %b}: " + (f"{n} trade(s) planned" if n else "no trade planned")] + _lines(r)), True
    miss = []
    if not r["fade_ok"]:
        miss.append(f"fade list is for {r['fade_session'] or 'unknown'}")
    if not r["fw_ok"]:
        miss.append(f"Arm A/B list was made after {r['fw_last'] or 'unknown'}")
    return "\n".join([f"⚠️ No full list for {day:%a %d %b}: " + "; ".join(miss) + ".",
                      "The account trades nothing from a list that is not for today."] + _lines(r)), False


def late_text(meta: dict, day: date) -> str | None:
    r = plan_rows(meta, day)
    if not (r["fade_ok"] and r["fw_ok"]):
        return None
    return "\n".join([f"🕘 The list for {day:%a %d %b} arrived after the open. Entries start now, at the live ask."] + _lines(r))
