"""S1 v10 results-day fade in the live paper account (paper only, 1 lot each; strategies/S1_v10_results_day_fade_paper.md).

The scan carries scanner/fade_live.py's list as meta.fade: for one session (`session`), the stocks whose results
day it is, with the side to buy (a put on strong numbers, a call on weak ones), the expiry and its strikes. On that
session this module:

    entry  any poll from 09:15 to 15:20, retried every 2 minutes per stock until it fills: from the strike nearest
           the live stock price, walking away from the money (down for puts, up for calls), the first strike with a
           live bid and ask, a spread <= 10 % of the ask, ask >= Rs 2 and one lot at the ask within Rs 600-8,000;
           bought at the ask. Nothing by 15:20 -> refused with the reason.
    exit   the first poll from 15:20 the same day, at the best bid (else the last price - 1 tick). A position still
           open on a later day (the server was down at 15:20) is sold at the first poll of that day.

Positions carry rule.strategy = "fade" and arm "F"; server/rules.py's S1 exits leave them alone.
"""
from __future__ import annotations

import logging
from datetime import datetime, time
from typing import Callable

from server.broker import tradingsymbol

log = logging.getLogger("fade")

OPEN_FROM, EOD_AT = time(9, 15), time(15, 20)
RETRY_SECONDS = 120
BAND, MIN_PREMIUM, MAX_SPREAD, TICK, WALK_MAX = (600.0, 8000.0), 2.0, 0.10, 0.05, 15


def walk(strikes: list[float], spot: float, side: str, quote: Callable[[float], dict | None]):
    """From the strike nearest `spot` (a tie: the lower for calls, the higher for puts), away from the money, the first
    strike with a two-sided live quote, spread <= 10 % of the ask, ask >= Rs 2 and ask x lot within Rs 600-8,000.
    Returns (strike, ask, lot) or the reason there is none."""
    ks = sorted(set(float(k) for k in strikes))
    if not ks or not spot:
        return "no strikes"
    put = side == "PE"
    k0 = min(ks, key=lambda k: (abs(k - spot), -k if put else k))
    i = ks.index(k0)
    path = (ks[: i + 1][::-1] if put else ks[i:])[:WALK_MAX]
    reason = "no strike with a two-sided quote and a lot in Rs 600-8,000"
    for k in path:
        q = quote(k) or {}
        depth = q.get("depth") or {}
        bid, ask, lot = (depth.get("bid") or [[None]])[0][0], (depth.get("ask") or [[None]])[0][0], q.get("lot_size") or 0
        if not bid or not ask or not lot:
            continue
        ask = float(ask)
        if ask < MIN_PREMIUM:
            return "premium below Rs 2"
        if (ask - float(bid)) > MAX_SPREAD * ask:
            reason = f"spread above 10 % of the ask (at {k:g}: bid {bid}, ask {ask})"
            continue
        cost = ask * lot
        if cost < BAND[0]:
            return "cheapest liquid lot below Rs 600"
        if cost > BAND[1]:
            reason = f"the nearest liquid lot costs more than Rs 8,000 (Rs {cost:,.0f} at {k:g})"
            continue
        return k, ask, lot
    return reason


class FadeTrader:
    def __init__(self, ledger, fade: Callable[[], dict | None], spot: Callable[[str], float | None] | None = None):
        self.ledger, self.fade = ledger, fade
        self.spot = spot or ledger.quotes.spot
        self._tried: dict[str, float] = {}
        self._last_why: dict[str, str] = {}

    def _state(self) -> dict:
        st = self.ledger.state.setdefault("rules", {"open": {}, "close": {}, "exits_checked": None, "refused": []})
        st.setdefault("refused", [])
        return st

    def _contract(self, sig: dict, strike: float, lot: int = 0) -> dict:
        return {"symbol": sig["symbol"], "instrument": sig["side"], "expiry": sig["expiry"], "strike": strike,
                "tradingsymbol": tradingsymbol(sig["symbol"], sig["side"], sig["expiry"], strike), "lot_size": lot}

    def _refuse(self, st: dict, sig: dict, today: str, why: str) -> None:
        st.setdefault("fade", {})[f"{today}:{sig['symbol']}"] = "refused"
        st["refused"] = st["refused"][-99:] + [{"date": today, "symbol": sig["symbol"], "mode": "fade",
                                                "arms": ["F"], "reason": why}]
        log.info("fade entry %s %s refused: %s", today, sig["symbol"], why)

    def signals(self, today: str) -> list[dict]:
        f = self.fade() or {}
        return list(f.get("signals") or []) if f.get("session") == today else []

    def on_poll(self, now: datetime) -> None:
        if not self.ledger.is_open(now):
            return
        today = now.date().isoformat()
        st = self._state()
        done = st.setdefault("fade", {})
        self._exits(now)
        if now.time() < OPEN_FROM:
            return
        for sig in self.signals(today):
            key = f"{today}:{sig['symbol']}"
            if key in done:
                continue
            if now.time() >= EOD_AT:
                self._refuse(st, sig, today, self._last_why.get(key) or "no affordable two-sided strike 09:15-15:20")
                continue
            if now.timestamp() - self._tried.get(key, 0) < RETRY_SECONDS:
                continue
            self._tried[key] = now.timestamp()
            spot = self.spot(sig["symbol"]) or sig.get("spot")
            w = walk(sig.get("strikes") or [], spot, sig["side"],
                     lambda k: self.ledger.quotes.get(self._contract(sig, k)))
            if isinstance(w, str):
                self._last_why[key] = w
                continue
            k, px, lot = w
            rule = {"strategy": "fade", "entry_mode": "fade", "arms": ["F"], "signal_date": today,
                    "filed": sig.get("filed"), "why": sig.get("why"), "spot_at_entry": spot}
            pos = self.ledger.open_rule(self._contract(sig, k, lot), px, now, rule)
            done[key] = "bought"
            self.ledger._save()
            log.info("fade entry: %s at %.2f x %d (%s)", pos["tradingsymbol"], px, lot, sig.get("why"))

    def _exits(self, now: datetime) -> None:
        """Sell every fade position from 15:20 on its entry day, or at the first poll of any later day."""
        for pos in list(self.ledger.state["positions"]):
            r = pos.get("rule") or {}
            if r.get("strategy") != "fade":
                continue
            opened = datetime.fromisoformat(pos["opened_at"]).date()
            if not (now.date() > opened or now.time() >= EOD_AT):
                continue
            c = {k: pos[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol", "lot_size")}
            q = self.ledger.quotes.get(c) or {}
            bid = ((q.get("depth") or {}).get("bid") or [[None]])[0][0]
            px = bid or (max(0.0, round(q["last_price"] - TICK, 2)) if q.get("last_price") else None)
            if not px:
                continue                                         # no quote this poll: try the next one
            r["spot_at_exit"] = self.spot(pos["symbol"])
            self.ledger.close_at(pos["id"], px, now, "fade_eod" if now.date() == opened else "fade_late")
            log.info("fade exit: %s at %.2f", pos["tradingsymbol"], px)
