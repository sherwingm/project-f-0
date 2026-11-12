"""G1-C · NIFTY upside opening-range breakout, call held overnight (strategies/S3_G1C_call_overnight.md; the user, 2026-11-12:
"Setup for the call option buying"). Paper only: no order is sent. Its own ledger data/g1c_ledger.json, its own section on the /index
page, API /api/index/g1c and its own alerts; G1, G1-F, Near Tighty, XP and S1 are not touched.

The mirror of G1 (server/g1_live.py): the first 1-minute close ABOVE the 09:15-09:29 range (09:30-13:00) buys one lot of the ATM call of the
nearest weekly expiry at the ask of the next minute; a first close below the range is no G1-C trade (G1 takes it as a put). 50 % stop on the
bid, else sold at the next session's close (15:29). No skip filters and no breakout score (both were built for puts only).
"""
from __future__ import annotations

from server.g1_live import G1Trader


class G1CTrader(G1Trader):
    NAME, LEDGER = "G1-C", "g1c_ledger.json"
    EPOCH = "2026-11-12 G1-C live paper"
    PAGE = "strategies/S3_G1C_call_overnight.md"
    OPT = "CE"
    FILTERS = False
    SCORE = False

    def entry_note(self, st: dict) -> str:
        return ""

    def tracks(self, trades: list) -> list:
        return [("G1-C (call mirror)", trades)]
