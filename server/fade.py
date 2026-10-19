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

Positions carry rule.strategy = "fade" and arm "F"; server/rules.py's S1 exits leave them alone. Positions whose signal
date is in CARRY_DATES (empty: the eight trades of 2026-10-16 were closed instead) would follow _carry_exits.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, time
from typing import Callable

from server import sessions
from server.broker import tradingsymbol

log = logging.getLogger("fade")

OPEN_FROM, EOD_AT = time(9, 15), time(15, 20)
RETRY_SECONDS = 120
BAND, MIN_PREMIUM, MAX_SPREAD, TICK, WALK_MAX = (600.0, 8000.0), 2.0, 0.10, 0.05, 15

# Signal dates whose positions follow the carried-trade rule (sell at -20 % of the entry premium, at 25 % below the
# highest close since entry, or at T-1; strategies/S1_v10_results_day_fade_paper.md, addendum 2026-10-17). EMPTY on
# purpose: on 2026-10-17 the user closed the eight trades of 2026-10-16 instead (sold at the first poll of 2026-10-19)
# and kept the same-day exit strict for every fade trade, so no position follows this rule. The code stays, tested.
CARRY_DATES: set[str] = set()
CARRY_STOP, CARRY_TRAIL = 0.80, 0.75

# Shadow track (strategies/S1_v10_np25_shadow_track.md): v10's calls plus its puts with net profit YoY above 25 %. A tag
# on each fade position only: v10 still takes every trade.
NP_SHADOW = 25.0
_NP_RE = re.compile(r"net profit YoY ([+-]?\d+(?:\.\d+)?) %")


def np_yoy_of(rule: dict) -> float | None:
    """The filing's net profit YoY % from the rule (tagged at entry), else from its `why` note (trades before the tag)."""
    v = rule.get("np_yoy")
    if v is not None:
        return float(v)
    m = _NP_RE.search(str(rule.get("why") or ""))
    return float(m.group(1)) if m else None


def in_shadow(side: str, np_yoy: float | None) -> bool | None:
    """True if the trade is in the NP YoY > 25 % shadow track; None when a put's number is unknown."""
    if side == "CE":
        return True
    return None if np_yoy is None else np_yoy > NP_SHADOW


def split(state: dict) -> dict:
    """v10's fade trades split into the shadow track and the puts it leaves out: closed trades, wins, net Rs, mean net %
    of premium, and the open positions' unrealised Rs."""
    groups = {"v10 all fade": lambda s: True, "shadow: calls + puts NP YoY > 25 %": lambda s: s is True,
              "left out: puts NP YoY <= 25 %": lambda s: s is False, "unknown numbers": lambda s: s is None}
    out = {k: {"closed": 0, "wins": 0, "net_rs": 0.0, "mean_net_pct": None, "open": 0, "unrealised_rs": 0.0}
           for k in groups}
    pcts: dict[str, list[float]] = {k: [] for k in groups}
    for kind in ("closed", "positions"):
        for p in state.get(kind) or []:
            r = p.get("rule") or {}
            if r.get("strategy") != "fade":
                continue
            tag = r["shadow_np25"] if "shadow_np25" in r else in_shadow(p.get("instrument"), np_yoy_of(r))
            for k, f in groups.items():
                if not f(tag):
                    continue
                g = out[k]
                if kind == "closed":
                    g["closed"] += 1
                    g["wins"] += int(p.get("net_pnl", 0) > 0)
                    g["net_rs"] += float(p.get("net_pnl", 0.0))
                    if p.get("return_pct") is not None:
                        pcts[k].append(float(p["return_pct"]))
                else:
                    g["open"] += 1
                    g["unrealised_rs"] += float(p.get("unrealised", 0.0) or 0.0)
    for k, g in out.items():
        g["net_rs"], g["unrealised_rs"] = round(g["net_rs"], 2), round(g["unrealised_rs"], 2)
        g["mean_net_pct"] = round(sum(pcts[k]) / len(pcts[k]), 2) if pcts[k] else None
    out["rule"] = "strategies/S1_v10_np25_shadow_track.md (judged after >= 40 left-out puts have closed)"
    return out


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
            return f"premium below Rs 2 (at {k:g}: ask {ask:g})"
        if (ask - float(bid)) > MAX_SPREAD * ask:
            reason = f"spread above 10 % of the ask (at {k:g}: bid {bid}, ask {ask})"
            continue
        cost = ask * lot
        if cost < BAND[0]:
            return f"cheapest liquid lot below Rs 600 (Rs {cost:,.0f} at {k:g})"
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

    def _waiting(self, st: dict, key: str, now: datetime, why: str | None) -> None:
        """Why a signal of today has not filled yet, for the fade list (/api/paper/rules: rules.fade_wait); None clears it.
        Under the ledger lock: a save or /api/paper/rules may be walking the dict on another thread."""
        with self.ledger.lock:
            w = st.setdefault("fade_wait", {})
            for k in [k for k in w if not k.startswith(key.split(":")[0])]:
                del w[k]                                         # an earlier day's reasons
            if why is None:
                w.pop(key, None)
            else:
                w[key] = {"reason": why, "at": now.isoformat(timespec="seconds")}

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
        self._carry_exits(now)
        if now.time() < OPEN_FROM:
            return
        for sig in self.signals(today):
            key = f"{today}:{sig['symbol']}"
            if key in done:
                continue
            if now.time() >= EOD_AT:
                self._refuse(st, sig, today, self._last_why.get(key) or "no affordable two-sided strike 09:15-15:20")
                self._waiting(st, key, now, None)
                continue
            if now.timestamp() - self._tried.get(key, 0) < RETRY_SECONDS:
                continue
            self._tried[key] = now.timestamp()
            spot = self.spot(sig["symbol"]) or sig.get("spot")
            w = walk(sig.get("strikes") or [], spot, sig["side"],
                     lambda k: self.ledger.quotes.get(self._contract(sig, k)))
            if isinstance(w, str):
                self._last_why[key] = w
                self._waiting(st, key, now, w)
                continue
            k, px, lot = w
            rule = {"strategy": "fade", "entry_mode": "fade", "arms": ["F"], "signal_date": today,
                    "filed": sig.get("filed"), "why": sig.get("why"), "spot_at_entry": spot,
                    "np_yoy": sig.get("np_yoy"), "np_qoq": sig.get("np_qoq"), "rev_yoy": sig.get("rev_yoy"),
                    "shadow_np25": in_shadow(sig["side"], sig.get("np_yoy"))}
            pos = self.ledger.open_rule(self._contract(sig, k, lot), px, now, rule)
            done[key] = "bought"
            self._waiting(st, key, now, None)
            self.ledger._save()
            log.info("fade entry: %s at %.2f x %d (%s)", pos["tradingsymbol"], px, lot, sig.get("why"))

    @staticmethod
    def carried(pos: dict) -> bool:
        r = pos.get("rule") or {}
        return r.get("strategy") == "fade" and r.get("signal_date") in CARRY_DATES

    def _carry_exits(self, now: datetime) -> None:
        """Carried trades, once a session at the first poll from 15:20 on the last traded price as the close: sell at
        a close <= 0.80 x entry, at a close <= 0.75 x the highest close since entry, or on T-1; at the best bid."""
        if now.time() < EOD_AT:
            return
        today = now.date().isoformat()
        for pos in list(self.ledger.state["positions"]):
            if not self.carried(pos):
                continue
            c = pos["rule"].setdefault("carry", {"peak": pos["entry"]["price"], "checked": None})
            if c["checked"] == today:
                continue
            ck = {k: pos[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol", "lot_size")}
            q = self.ledger.quotes.get(ck) or {}
            close = q.get("last_price")
            if not close:
                continue                                         # no price this poll: try the next one
            entry = pos["entry"]["price"]
            c["peak"], c["checked"], c["last_close"] = max(c["peak"], close), today, close
            reason = ("carry_stop" if close <= CARRY_STOP * entry else
                      "carry_trail" if close <= CARRY_TRAIL * c["peak"] else
                      "carry_t1" if now.date() >= sessions.t_minus(pos["expiry"], 1) else None)
            if reason:
                bid = ((q.get("depth") or {}).get("bid") or [[None]])[0][0]
                px = bid or max(0.0, round(close - TICK, 2))
                pos["rule"]["spot_at_exit"] = self.spot(pos["symbol"])
                self.ledger.close_at(pos["id"], px, now, reason)
                log.info("fade carry exit %s: %s at %.2f (close %.2f, entry %.2f, peak %.2f)",
                         reason, pos["tradingsymbol"], px, close, entry, c["peak"])
            self.ledger._save()

    def _exits(self, now: datetime) -> None:
        """Sell every fade position from 15:20 on its entry day, or at the first poll of any later day."""
        for pos in list(self.ledger.state["positions"]):
            r = pos.get("rule") or {}
            if r.get("strategy") != "fade" or self.carried(pos):
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
