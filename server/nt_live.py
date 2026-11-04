"""NT · Near Tighty live paper trading (strategies/NT_near_tighty.md; the user, 2026-11-04: "keep this as a seperate
rule , i will name it as a near tighty dont mix with the nifty index , i will be a seperate part form it").

Its own part of the project: own ledger data/nt_ledger.json, own page /near-tighty, own API /api/near-tighty, own
alerts. Paper only: nothing is ordered, and neither the S1 paper account nor G1's ledger is touched.

Rules: G1's (server/g1_live.py: downside first breakout of the 09:15-09:29 range, ATM put of the nearest weekly
expiry at the ask, 50 % stop on the bid, else sold at the next session's 09:16 bid) plus one condition: trade only
when that expiry is 1-3 sessions after the signal day (server.sessions.sessions_to_expiry). G1-F's filters do not
apply. On a 1-3-session day G1 takes the same put in its own ledger.
"""
from __future__ import annotations

from datetime import date

from server import sessions
from server.g1_live import G1Trader

NEAR = (1, 3)                                              # sessions to expiry, both included


class NearTightyTrader(G1Trader):
    NAME, LEDGER = "Near Tighty", "nt_ledger.json"
    EPOCH = "2026-11-05 Near Tighty live paper"
    PAGE = "strategies/NT_near_tighty.md"

    def entry_skip(self, day: date, expiry: str) -> str:
        n = sessions.sessions_to_expiry(day, date.fromisoformat(expiry))
        if n is None or not NEAR[0] <= n <= NEAR[1]:
            return (f"downside breakout, but the {expiry} expiry is {n} sessions away: Near Tighty trades only "
                    f"{NEAR[0]}-{NEAR[1]} sessions to expiry")
        return ""

    def entry_note(self, st: dict) -> str:
        return ""

    def tracks(self, trades: list) -> list:
        return [("Near Tighty", trades)]

    def view(self) -> dict:
        v = super().view()
        v["near"] = list(NEAR)
        return v
