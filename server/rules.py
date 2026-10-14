"""S1 rule trades in the live paper account (paper only, 1 lot each, outside the manual-order limits).

The nightly forward test (scanner/forward_s1.py, in the scan as meta.forward) lists each session's results beats
as "buy next session", per arm. On that next session this module buys each of them twice, as two separate
positions, so the two entry times can be compared:

    open   any poll from 09:15 to 15:20 (retried every 2 minutes): over the strikes that traded >= 50 contracts
           on day 0, from the one nearest the live stock price upward, the first whose live best ask x lot is
           Rs 600-8,000, bought at that ask (until 2026-10-14 this used one strike fixed overnight, which a gap-up
           could price out: HCLTECH's 1330 CE cost Rs 14,440 at the 14 Oct open)
    close  the first poll from 15:20: the walk again on today's live volume and average traded price (ATP),
           bought at ATP + 1 tick (the live version of the backtest's "day's VWAP + 1 tick")

Exits, checked once a session at the first poll from 15:20 with the last traded price as the close: 50 % stop,
5 sessions without a new closing high, T-1 (the session before expiry); the sale fills at the best bid. Each
position carries the arms whose signal it is (A, B or both), so the results page scores each arm on its own.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Callable

from scanner import backtest_s1_v7 as v7
from server import sessions
from server.broker import tradingsymbol

log = logging.getLogger("rules")

OPEN_FROM, EOD_AT = time(9, 15), time(15, 20)
RETRY_SECONDS = 120                            # the open-window walk is retried at most every 2 minutes per stock
BAND, CONTRACTS, MIN_PREMIUM, TICK = v7.NORMAL_BAND, v7.NORMAL_CONTRACTS, 2.0, 0.05
WALK_MAX = 15                                  # strikes tried upward from the at-the-money one at 15:20


def signals_for(fw: dict | None, today: date) -> list[dict]:
    """The forward test's "buy next session" list, when today is that next session: one row per stock with the
    arms that hold it. A stale list (a session passed since it was made) gives nothing."""
    if not fw or not fw.get("last_session"):
        return []
    last = date.fromisoformat(fw["last_session"])
    if last >= today:
        return []
    d = last + timedelta(days=1)
    while d < today:
        if sessions.is_session(d):
            return []                          # the list is for a session already gone
        d += timedelta(days=1)
    rows: dict[str, dict] = {}
    for arm, st in (fw.get("arms") or {}).items():
        for p in st.get("pending", []):
            r = rows.setdefault(p["symbol"], {**p, "arms": []})
            r["arms"] = sorted(set(r["arms"]) | {arm})
    return list(rows.values())


def walk_live(strikes: list[float], spot: float, quote: Callable[[float], dict | None]):
    """The rules' walk on live quotes: from the strike nearest spot (a tie: the lower) upward, the first call that
    traded >= 50 contracts today with ATP >= Rs 2 and one lot at ATP + 1 tick within Rs 600-8,000.
    Returns (strike, price, lot, quote) or the reason there is none."""
    ks = sorted(set(float(k) for k in strikes))
    if not ks or not spot:
        return "no strikes"
    k0 = min(ks, key=lambda k: (abs(k - spot), k))
    for k in ks[ks.index(k0):][:WALK_MAX]:
        q = quote(k)
        if not q:
            continue
        lot, atp, vol = q.get("lot_size") or 0, q.get("atp"), q.get("volume") or 0
        if not lot or not atp or vol / lot < CONTRACTS:
            continue
        px = round(atp + TICK, 2)
        if px < MIN_PREMIUM:
            return "premium below Rs 2"
        if px * lot < BAND[0]:
            return "cheapest liquid lot below Rs 600"
        if px * lot > BAND[1]:
            continue
        return k, px, lot, q
    return "no strike with >= 50 contracts today and a lot in Rs 600-8,000"


def walk_ask(strikes: list[float], spot: float, quote: Callable[[float], dict | None]):
    """The open-window walk (2026-10-14: entries are no longer tied to one strike picked overnight): over the
    strikes that traded >= 50 contracts on day 0, from the one nearest the LIVE stock price (a tie: the lower)
    upward, the first whose live best ask x lot is within Rs 600-8,000. Returns (strike, ask, lot) or the reason."""
    ks = sorted(set(float(k) for k in strikes))
    if not ks or not spot:
        return "no liquid strikes on the results day"
    k0 = min(ks, key=lambda k: (abs(k - spot), k))
    reason = "no liquid strike with a lot in Rs 600-8,000 at the live ask"
    for k in ks[ks.index(k0):][:WALK_MAX]:
        q = quote(k)
        ask = ((q or {}).get("depth") or {}).get("ask") or []
        lot = (q or {}).get("lot_size") or 0
        if not ask or not lot:
            continue
        px = float(ask[0][0])
        if px < MIN_PREMIUM:
            return "premium below Rs 2"
        if px * lot < BAND[0]:
            return "cheapest liquid lot below Rs 600"
        if px * lot > BAND[1]:
            reason = f"the cheapest liquid lot costs more than Rs 8,000 at the live ask (Rs {px * lot:,.0f} at {k:g})"
            continue
        return k, px, lot
    return reason


class RuleTrader:
    def __init__(self, ledger, forward: Callable[[], dict | None], spot: Callable[[str], float | None] | None = None):
        self.ledger, self.forward = ledger, forward
        self.spot = spot or ledger.quotes.spot
        self._tried: dict[str, float] = {}           # open-window walk: last try per (day, stock), epoch seconds
        self._last_why: dict[str, str] = {}

    def _state(self) -> dict:
        return self.ledger.state.setdefault("rules", {"open": {}, "close": {}, "exits_checked": None, "refused": []})

    def _quote(self, sym: str, expiry: str, strike: float) -> dict | None:
        c = {"symbol": sym, "instrument": "CE", "expiry": expiry, "strike": strike,
             "tradingsymbol": tradingsymbol(sym, "CE", expiry, strike), "lot_size": 0}
        return self.ledger.quotes.get(c)

    def _refuse(self, st: dict, sig: dict, mode: str, today: str, why: str) -> None:
        st[mode][f"{today}:{sig['symbol']}"] = "refused"
        st["refused"] = (st.get("refused") or [])[-99:] + [{"date": today, "symbol": sig["symbol"], "mode": mode,
                                                            "arms": sig["arms"], "reason": why}]
        log.info("rule %s entry %s %s refused: %s", mode, today, sig["symbol"], why)

    def _buy(self, sig: dict, mode: str, strike: float, price: float, lot: int, now: datetime) -> None:
        contract = {"symbol": sig["symbol"], "instrument": "CE", "expiry": sig["expiry"], "strike": strike,
                    "tradingsymbol": tradingsymbol(sig["symbol"], "CE", sig["expiry"], strike), "lot_size": lot}
        rule = {"entry_mode": mode, "arms": sig["arms"], "signal_date": sig["signal_date"], "beat": sig.get("beat"),
                "move": sig.get("move")}
        pos = self.ledger.open_rule(contract, price, now, rule)
        log.info("rule %s entry: %s at %.2f x %d (arms %s)", mode, pos["tradingsymbol"], price, lot, ",".join(sig["arms"]))

    def on_poll(self, now: datetime) -> None:
        if not self.ledger.is_open(now):
            return
        today = now.date().isoformat()
        st = self._state()
        sigs = signals_for(self.forward(), now.date())
        if OPEN_FROM <= now.time():
            for sig in sigs:
                key = f"{today}:{sig['symbol']}"
                if key in st["open"]:
                    continue
                if now.time() >= EOD_AT:
                    self._refuse(st, sig, "open", today, self._last_why.get(key) or
                                 "no affordable liquid strike between 09:15 and 15:20")
                    continue
                if now.timestamp() - self._tried.get(key, 0) < RETRY_SECONDS:
                    continue
                self._tried[key] = now.timestamp()
                spot = self.spot(sig["symbol"]) or sig.get("spot")
                strikes = sig.get("liquid_strikes") or ([sig["open_strike"]] if sig.get("open_strike") else [])
                w = walk_ask(strikes, spot, lambda k: self._quote(sig["symbol"], sig["expiry"], k))
                if isinstance(w, str):
                    self._last_why[key] = w
                    continue                                     # try again in 2 minutes, until 15:20
                k, px, lot = w
                self._buy(sig, "open", k, px, lot, now)
                st["open"][key] = "bought"
        if now.time() >= EOD_AT and st.get("exits_checked") != today:
            for sig in sigs:
                key = f"{today}:{sig['symbol']}"
                if key in st["close"]:
                    continue
                spot = self.spot(sig["symbol"]) or sig.get("spot")
                w = walk_live(sig.get("strikes") or [], spot, lambda k: self._quote(sig["symbol"], sig["expiry"], k))
                if isinstance(w, str):
                    self._refuse(st, sig, "close", today, w)
                    continue
                k, px, lot, _ = w
                self._buy(sig, "close", k, px, lot, now)
                st["close"][key] = "bought"
            self.check_exits(now)
            st["exits_checked"] = today
            self.ledger._save()

    def check_exits(self, now: datetime) -> None:
        """Each rule position's close (the last traded price at 15:20) through the rules: stop, decay, T-1."""
        today = now.date().isoformat()
        for pos in list(self.ledger.state["positions"]):
            r = pos.get("rule")
            if not r or r.get("checked") == today:
                continue
            q = self.ledger.quotes.get({k: pos[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol",
                                                            "lot_size")}) or {}
            close = q.get("last_price")
            if not close:
                continue
            left = sessions.sessions_to_expiry(now.date(), pos["expiry"])
            r["best"], r["stall"], reason = v7.exit_step(close, pos["entry"]["price"], r["best"], r["stall"], left)
            r["checked"], r["last_close"] = today, close
            if reason:
                bid = ((q.get("depth") or {}).get("bid") or [[None]])[0][0]
                px = bid or max(0.0, round(close - TICK, 2))
                self.ledger.close_at(pos["id"], px, now, {"0_stop": "rule_stop", "1_decay": "rule_decay",
                                                          "2_t_minus_1": "rule_t1"}[reason])
                log.info("rule exit %s: %s at %.2f", reason, pos["tradingsymbol"], px)
