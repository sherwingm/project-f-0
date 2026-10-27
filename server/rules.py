"""S1 rule trades in the live paper account (paper only, 1 lot each, outside the manual-order limits).

The nightly forward test (scanner/forward_s1.py, in the scan as meta.forward) lists each session's results beats
as "buy next session", per arm. On that next session this module buys each of them twice, as two separate
positions, so the two entry times can be compared:

    open   any poll from 09:15 to 15:20 (retried every 30 seconds, i.e. every poll; every 2 minutes until 2026-10-20): over the strikes that traded >= 50 contracts
           on day 0, from the one nearest the live stock price upward, the first whose live best ask x lot is
           Rs 600-8,000, bought at that ask (until 2026-10-14 this used one strike fixed overnight, which a gap-up
           could price out: HCLTECH's 1330 CE cost Rs 14,440 at the 14 Oct open)
    close  the first poll from 15:20: the walk again on today's live volume and average traded price (ATP),
           bought at ATP + 1 tick (the live version of the backtest's "day's VWAP + 1 tick")

A stock in the F&O ban list that session is refused by both entries ("in the F&O ban today"), as the backtest and
the forward test skip it. The list comes from the fade signal file (meta.fade.ban, written by scanner/fade_live.py
nightly and before the open for its `session`); a file for another session blocks nothing.

Exits, checked once a session at the first poll from 15:20 with the last traded price as the close: 50 % stop,
5 sessions without a new closing high, T-1 (the session before expiry); the sale fills at the best bid. Each
position carries the arms whose signal it is (A, B or both), so the results page scores each arm on its own.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Callable

from scanner import backtest_s1_v7 as v7
from server import peak as pk, sessions
from server.broker import tradingsymbol

log = logging.getLogger("rules")

OPEN_FROM, EOD_AT = time(9, 15), time(15, 20)
RETRY_SECONDS = 30                             # the open-window walk is retried every poll (DECISIONS.md, 2026-10-20)
RETRY_SLACK = 5                                # a poll landing a few seconds early still counts


def streaming(ledger) -> bool:
    """The live prices come from the Upstox stream: retry at every poll (DECISIONS.md, 2026-10-22)."""
    f = getattr(getattr(ledger, "quotes", None), "streaming", None)
    return bool(f and f())
BAND, CONTRACTS, MIN_PREMIUM = v7.NORMAL_BAND, v7.NORMAL_CONTRACTS, 2.0
TICK = 0.01                                    # NSE stock-option tick since 2025-11-03 (Rs 0.05 before)
WALK_MAX = 15                                  # strikes tried upward from the at-the-money one at 15:20
BAN_WHY = "in the F&O ban today"


def forward_is_current(fw: dict | None, today: date) -> bool:
    """True when `today` is the session the forward list was made for (the first session after its last_session). A
    session in between, a missed nightly build, makes it stale; the page asks this too (meta.forward.for_today)."""
    if not fw or not fw.get("last_session"):
        return False
    last = date.fromisoformat(fw["last_session"])
    if last >= today:
        return False
    d = last + timedelta(days=1)
    while d < today:
        if sessions.is_session(d):
            return False                       # the list is for a session already gone
        d += timedelta(days=1)
    return True


def signals_for(fw: dict | None, today: date) -> list[dict]:
    """The forward test's "buy next session" list, when today is that next session: one row per stock with the
    arms that hold it. A stale list (a session passed since it was made) gives nothing."""
    if not forward_is_current(fw, today):
        return []
    rows: dict[str, dict] = {}
    for arm, st in (fw.get("arms") or {}).items():
        for p in st.get("pending", []):
            r = rows.setdefault(p["symbol"], {**p, "arms": []})
            r["arms"] = sorted(set(r["arms"]) | {arm})
    return list(rows.values())


def banned_today(fade: dict | None, today: date) -> set[str]:
    """The F&O ban list for today from the fade signal file (scanner/fade_live.py writes the ban list of its
    `session`); empty when the file is for another session or has no list."""
    if not fade or fade.get("session") != today.isoformat():
        return set()
    return set(fade.get("ban") or [])


def path_up(strikes: list[float], spot: float | None) -> list[float]:
    """The strikes a call walk may visit: from the one nearest spot (a tie: the lower) upward, at most WALK_MAX.
    The entries price them all in one quote call."""
    ks = sorted(set(float(k) for k in strikes))
    if not ks or not spot:
        return []
    k0 = min(ks, key=lambda k: (abs(k - spot), k))
    return ks[ks.index(k0):][:WALK_MAX]


def never_fits(lot: int, band: tuple[float, float] = BAND, floor: float = MIN_PREMIUM) -> str | None:
    """The lot-size range check (the user's idea, 2026-10-19): one lot must cost band[0]-band[1] and the premium must
    be >= floor, so a share's premium must lie in [max(floor, band[0] / lot), band[1] / lot]. When that range is
    empty no strike can ever fit (IRFC: lot 5,425 -> at most Rs 1.47, below Rs 2), so the entry is refused at once
    instead of being retried all day. The reason, else None."""
    if not lot:
        return None
    hi = band[1] / lot
    if hi < max(floor, band[0] / lot):
        return (f"never fits: 1 lot is {lot:,} shares, so Rs {band[1]:,.0f} allows at most Rs {hi:.2f} a share, "
                f"below the Rs {floor:g} floor")
    return None


def lot_of(book: dict) -> int:
    """The lot size from a priced strike set (every strike of one stock and expiry has the same lot)."""
    return next((int(q["lot_size"]) for q in book.values() if q and q.get("lot_size")), 0)


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
            return f"premium below Rs 2 (at {k:g}: ATP {atp:g})"
        if px * lot < BAND[0]:
            return f"cheapest liquid lot below Rs 600 (Rs {px * lot:,.0f} at {k:g})"
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
            return f"premium below Rs 2 (at {k:g}: ask {px:g})"
        if px * lot < BAND[0]:
            return f"cheapest liquid lot below Rs 600 (Rs {px * lot:,.0f} at {k:g})"
        if px * lot > BAND[1]:
            reason = f"the cheapest liquid lot costs more than Rs 8,000 at the live ask (Rs {px * lot:,.0f} at {k:g})"
            continue
        return k, px, lot
    return reason


class RuleTrader:
    def __init__(self, ledger, forward: Callable[[], dict | None], spot: Callable[[str], float | None] | None = None,
                 fade: Callable[[], dict | None] | None = None):
        self.ledger, self.forward = ledger, forward
        self.fade = fade or (lambda: None)           # the fade signal file: today's F&O ban list
        self.spot = spot or ledger.quotes.spot
        self._tried: dict[str, float] = {}           # open-window walk: last try per (day, stock), epoch seconds
        self._last_why: dict[str, str] = {}

    def _state(self) -> dict:
        return self.ledger.state.setdefault("rules", {"open": {}, "close": {}, "exits_checked": None, "refused": []})

    def _book(self, sig: dict, strikes: list[float]) -> dict[float, dict | None]:
        """{strike: live quote} for the calls a walk may visit, in one quote call (QuoteSource.get_many)."""
        cs = {k: {"symbol": sig["symbol"], "instrument": "CE", "expiry": sig["expiry"], "strike": k,
                  "tradingsymbol": tradingsymbol(sig["symbol"], "CE", sig["expiry"], k), "lot_size": 0} for k in strikes}
        many = getattr(self.ledger.quotes, "get_many", None)
        if many:
            got = many(list(cs.values()))
            return {k: got.get(c["tradingsymbol"]) for k, c in cs.items()}
        return {k: self.ledger.quotes.get(c) for k, c in cs.items()}

    def _waiting(self, st: dict, key: str, now: datetime, arms: list[str], why: str | None) -> None:
        """Why today's open entry has not filled yet, for the results page (/api/paper/rules: rules.open_wait);
        None clears it. Under the ledger lock: a save or /api/paper/rules may be walking the dict on another thread."""
        with self.ledger.lock:
            w = st.setdefault("open_wait", {})
            for k in [k for k in w if not k.startswith(key.split(":")[0])]:
                del w[k]                                         # an earlier day's reasons
            if why is None:
                w.pop(key, None)
            else:
                w[key] = {"reason": why, "at": now.isoformat(timespec="seconds"), "arms": arms}

    def _refuse(self, st: dict, sig: dict, mode: str, today: str, why: str) -> None:
        with self.ledger.lock:
            st[mode][f"{today}:{sig['symbol']}"] = "refused"
            st["refused"] = (st.get("refused") or [])[-99:] + [{"date": today, "symbol": sig["symbol"], "mode": mode,
                                                                "arms": sig["arms"], "reason": why}]
        log.info("rule %s entry %s %s refused: %s", mode, today, sig["symbol"], why)

    def _buy(self, st: dict, key: str, sig: dict, mode: str, strike: float, price: float, lot: int, now: datetime,
             quote: dict | None = None, old_price: float | None = None) -> None:
        """Order the call decided at `price`; st[mode][key] is "ordered" until the ledger fills it ("bought") or cancels
        it (open: the walk tries again; close: refused). strategies/S1_paper_real_order_fills.md."""
        contract = {"symbol": sig["symbol"], "instrument": "CE", "expiry": sig["expiry"], "strike": strike,
                    "tradingsymbol": tradingsymbol(sig["symbol"], "CE", sig["expiry"], strike), "lot_size": lot}
        rule = {"entry_mode": mode, "arms": sig["arms"], "signal_date": sig["signal_date"], "beat": sig.get("beat"),
                "move": sig.get("move")}
        today = now.date().isoformat()

        def filled(pos: dict, at: datetime) -> None:
            st[mode][key] = "bought"
            if mode == "open":
                self._waiting(st, key, at, sig["arms"], None)
            self.ledger._save()
            log.info("rule %s entry: %s at %.2f x %d (arms %s)", mode, pos["tradingsymbol"], pos["entry"]["price"], lot,
                     ",".join(sig["arms"]))

        def cancelled(why: str, at: datetime) -> None:
            if mode == "close":
                self._refuse(st, sig, "close", today, f"buy order not filled ({why})")
                return
            st[mode].pop(key, None)                              # the open walk tries again next poll
            self._last_why[key] = f"buy order not filled ({why})"
            self._waiting(st, key, at, sig["arms"], self._last_why[key])

        st[mode][key] = "ordered"
        cutoff = datetime.combine(now.date(), EOD_AT, now.tzinfo) if mode == "open" else None
        self.ledger.buy_rule(contract, price, now, rule, quote=quote, on_fill=filled, on_cancel=cancelled,
                             cutoff=cutoff, old_price=old_price)

    def on_poll(self, now: datetime) -> None:
        if not self.ledger.is_open(now):
            return
        today = now.date().isoformat()
        st = self._state()
        sigs = signals_for(self.forward(), now.date())
        banned = banned_today(self.fade(), now.date()) if sigs else set()
        if OPEN_FROM <= now.time():
            for sig in sigs:
                key = f"{today}:{sig['symbol']}"
                if key in st["open"]:
                    continue
                if sig["symbol"] in banned:
                    self._refuse(st, sig, "open", today, BAN_WHY)
                    self._waiting(st, key, now, sig["arms"], None)
                    continue
                if now.time() >= EOD_AT:                         # the saved reason survives a restart
                    self._refuse(st, sig, "open", today, self._last_why.get(key) or
                                 ((st.get("open_wait") or {}).get(key) or {}).get("reason") or
                                 "no affordable liquid strike between 09:15 and 15:20")
                    self._waiting(st, key, now, sig["arms"], None)
                    continue
                every = 0 if streaming(self.ledger) else RETRY_SECONDS - RETRY_SLACK    # streaming: every poll (1 s)
                if every and now.timestamp() - self._tried.get(key, 0) < every:
                    continue
                self._tried[key] = now.timestamp()
                spot = self.spot(sig["symbol"]) or sig.get("spot")
                strikes = sig.get("liquid_strikes") or ([sig["open_strike"]] if sig.get("open_strike") else [])
                book = self._book(sig, path_up(strikes, spot))
                if any(book.values()) and all(pk.not_traded_today(q, now) for q in book.values() if q):
                    self._last_why[key] = w = "waiting for the first trade today (every quote is yesterday's)"
                    self._waiting(st, key, now, sig["arms"], w)  # no price of today yet: no buy and no refusal
                    continue
                why = never_fits(lot_of(book) or sig.get("open_lot") or 0)
                if why:                                          # no strike can ever fit: say so now, not at 15:20
                    self._refuse(st, sig, "open", today, why)
                    self._waiting(st, key, now, sig["arms"], None)
                    continue
                w = walk_ask(strikes, spot, book.get)
                if isinstance(w, str):
                    self._last_why[key] = w
                    self._waiting(st, key, now, sig["arms"], w)
                    continue                                     # try again next poll, until 15:20
                k, px, lot = w
                if pk.not_traded_today(book.get(k), now):       # yesterday's book: wait for today's first trade
                    self._last_why[key] = w = f"waiting for the first trade today at {k:g} (the quote is yesterday's)"
                    self._waiting(st, key, now, sig["arms"], w)
                    continue
                with self.ledger.lock:                           # saved now: a restart must not buy it again
                    self._buy(st, key, sig, "open", k, px, lot, now, quote=book.get(k))
                    self.ledger._save()
        if now.time() >= EOD_AT and st.get("exits_checked") != today:
            for sig in sigs:
                key = f"{today}:{sig['symbol']}"
                if key in st["close"]:
                    continue
                if sig["symbol"] in banned:
                    self._refuse(st, sig, "close", today, BAN_WHY)
                    continue
                spot = self.spot(sig["symbol"]) or sig.get("spot")
                book = self._book(sig, path_up(sig.get("strikes") or [], spot))
                w = never_fits(lot_of(book)) or walk_live(sig.get("strikes") or [], spot, book.get)
                if isinstance(w, str):
                    self._refuse(st, sig, "close", today, w)
                    continue
                k, px, lot, _ = w
                if pk.not_traded_today(book.get(k), now):
                    self._refuse(st, sig, "close", today, f"no trade today at {k:g} (the quote is yesterday's)")
                    continue
                ask = (((book.get(k) or {}).get("depth") or {}).get("ask") or [[None]])[0][0]
                if self.ledger.real_orders:                      # the real 15:20 book, not the day's ATP (2026-10-26)
                    if not ask:
                        self._refuse(st, sig, "close", today, f"no ask at 15:20 (at {k:g})")
                        continue
                    self._buy(st, key, sig, "close", k, float(ask), lot, now, quote=book.get(k), old_price=px)
                else:
                    self._buy(st, key, sig, "close", k, px, lot, now, quote=book.get(k))
            self.check_exits(now)
            with self.ledger.lock:
                st["exits_checked"] = today
                self.ledger._save()

    def check_exits(self, now: datetime) -> None:
        """Each rule position's close (the last traded price at 15:20) through the rules: stop, decay, T-1."""
        today = now.date().isoformat()
        for pos in list(self.ledger.state["positions"]):
            r = pos.get("rule")
            if not r or r.get("strategy") == "fade" or r.get("checked") == today:    # fade: server/fade.py exits
                continue
            if pos.get("exiting"):
                continue                                         # its sell order is working
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
                                                          "2_t_minus_1": "rule_t1"}[reason], price_is_bid=bool(bid))
                log.info("rule exit %s: %s at %.2f", reason, pos["tradingsymbol"], px)
