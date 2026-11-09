"""NT · Near Tighty live paper trading (strategies/NT_near_tighty.md; the user, 2026-11-04: "keep this as a seperate
rule , i will name it as a near tighty dont mix with the nifty index , i will be a seperate part form it").

Its own part of the project: own ledger data/nt_ledger.json, own sections on the /index page (2026-11-10: the user wanted no separate page), API /api/index/nt, own
alerts. Paper only: nothing is ordered, and neither the S1 paper account nor G1's ledger is touched.

Rules: G1's (server/g1_live.py: downside first breakout of the 09:15-09:29 range, ATM put of the nearest weekly
expiry at the ask, 50 % stop on the bid, else sold at the next session's 09:16 bid) plus one condition: trade only
when that expiry is 1-3 sessions after the signal day (server.sessions.sessions_to_expiry). G1-F's filters do not
apply. On a 1-3-session day G1 takes the same put in its own ledger.
"""
from __future__ import annotations

from datetime import date, datetime

from server import sessions
from server.g1_live import VIX_KEY, G1Trader, _ltp

NEAR = (1, 3)                                              # sessions to expiry, both included


class NearTightyTrader(G1Trader):
    NAME, LEDGER = "Near Tighty", "nt_ledger.json"
    EPOCH = "2026-11-05 Near Tighty live paper"
    PAGE = "strategies/NT_near_tighty.md"
    SCORE = False             # the G1 breakout score is not applied to Near Tighty
    HOLD_TO_CLOSE = False     # Near Tighty keeps G1's original exit (next 09:16); the 2026-11-06 change is G1 / G1-F only

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
        v["index"] = self.INDEX
        return v


class NearTightySensexTrader(NearTightyTrader):
    """Near Tighty on SENSEX (strategies/NT_near_tighty.md, "SENSEX track", added 2026-11-08): the same rule on the BSE
    SENSEX weekly puts (step 100). Own ledger data/nt_sensex_ledger.json, own alerts; NIFTY's Near Tighty, G1 and G1-F are
    not touched. Prices from the same Upstox stream (BSE_INDEX|SENSEX, BSE_FO put contracts from GET /v2/option/contract);
    the lot is read from the contract list (20 in the history run). Paper only."""
    NAME, LEDGER = "Near Tighty SENSEX", "nt_sensex_ledger.json"
    EPOCH = "2026-11-08 Near Tighty SENSEX live paper"
    INDEX, SPOT, SPOT_LABEL, STEP, KEYS = "SENSEX", "BSE_INDEX|SENSEX", "SENSEX", 100, "_sensex"
    BAND, EXPIRIES = 6, 2               # puts subscribed: this many strikes either side of ATM, this many expiries

    def __init__(self, stream, upstox, data_dir, lot: int = 20):
        super().__init__(stream, upstox, data_dir, lot=lot)

    def subscribe(self, now: datetime) -> None:
        self.upstox.ensure_sensex(now.date())
        keys = [self.SPOT, VIX_KEY]
        contracts = self._nifty_keys()                              # the SENSEX contract map (KEYS = "_sensex")
        spot = _ltp(self.stream.get(self.SPOT))
        if spot and contracts:
            today = now.date().isoformat()
            exps = sorted({e for e, typ, _ in contracts if typ == "PE" and e > today})[:self.EXPIRIES]
            atm = round(spot / self.STEP) * self.STEP
            for e in exps:
                for k in range(atm - self.BAND * self.STEP, atm + (self.BAND + 1) * self.STEP, self.STEP):
                    key = contracts.get((e, "PE", float(k)))
                    if key:
                        keys.append(key)
            lot = (getattr(self.upstox, "_sensex_lot", None) or {}).get(exps[0]) if exps else None
            if lot:
                self.lot = int(lot)                                 # the lot of the nearest expiry, read at entry
        self.stream.want(keys)

    def tracks(self, trades: list) -> list:
        return [("Near Tighty SENSEX", trades)]

    def entry_skip(self, day: date, expiry: str) -> str:
        why = super().entry_skip(day, expiry)
        return why.replace("downside breakout, but", "SENSEX downside breakout, but") if why else ""
