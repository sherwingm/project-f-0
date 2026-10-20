"""S1 v10 results-day fade in the live paper account (paper only, 1 lot each; strategies/S1_v10_results_day_fade_paper.md).

The scan carries scanner/fade_live.py's list as meta.fade: for one session (`session`), the stocks whose results
day it is, with the side to buy (a put on strong numbers, a call on weak ones), the expiry and its strikes. On that
session this module:

    entry  any poll from 09:15 to 15:20, retried every 30 seconds per stock (every poll; 2 minutes until 2026-10-20) until it fills: from the strike nearest
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
import math
import re
from datetime import datetime, time
from typing import Callable

from server import sessions
from server.broker import tradingsymbol
from server.rules import lot_of, never_fits

log = logging.getLogger("fade")

OPEN_FROM, EOD_AT = time(9, 15), time(15, 20)
RETRY_SECONDS = 30                                       # DECISIONS.md, 2026-10-20 (was 120)
RETRY_SLACK = 5                                          # a poll landing a few seconds early still counts
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
# Shadow exit (strategies/S1_v10_t100_shadow_track.md): a sell at 2 x entry, filled when a poll sees the best bid at or
# above it, else the real 15:20 sale. A tag on each fade position only: the real exit is unchanged.
T100 = 2.0
# Shadow stop (strategies/S1_v10_s20_shadow_track.md): sold at the best bid of the first poll with the bid at or below
# 0.80 x entry, else the real 15:20 sale. A tag only: the real exit is unchanged.
S20, S20_FROM = 0.80, time(9, 16)                 # S1 v11 (strategies/S1_v11_fade_stop20.md): active from 09:16:00
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


def walk_path(strikes: list[float], spot: float | None, side: str) -> list[float]:
    """The strikes walk() may visit, nearest the money first, away from it (priced in one quote call)."""
    ks = sorted(set(float(k) for k in strikes))
    if not ks or not spot:
        return []
    put = side == "PE"
    k0 = min(ks, key=lambda k: (abs(k - spot), -k if put else k))
    i = ks.index(k0)
    return (ks[: i + 1][::-1] if put else ks[i:])[:WALK_MAX]


def t100_target(entry: float) -> float:
    return round(math.ceil(round(entry * T100 / TICK, 6)) * TICK, 2)


def t100(state: dict) -> dict:
    """Tagged closed fade trades under the real 15:20 exit and under the +100 % shadow exit: N, wins, mean net % of
    premium, total net Rs, targets hit; open tagged positions with their target hit so far."""
    from server import charges as ch
    real, shadow, hits, untagged = [], [], 0, 0
    for p in state.get("closed") or []:
        r = p.get("rule") or {}
        if r.get("strategy") != "fade":
            continue
        sh = r.get("shadow_t100")
        if not sh:
            untagged += 1
            continue
        cost = p["entry"]["price"] * p["qty"]
        net = float(p.get("net_pnl", 0.0))
        if sh.get("hit_at"):
            hits += 1
            snet = round((sh["target"] - p["entry"]["price"]) * p["qty"] - float(p.get("entry_charges", 0.0))
                         - ch.leg(p["instrument"], "SELL", p["qty"], sh["target"])["total"], 2)
        else:
            snet = net
        real.append((net, net / cost * 100 if cost else 0.0))
        shadow.append((snet, snet / cost * 100 if cost else 0.0))

    def agg(xs):
        return {"closed": len(xs), "wins": sum(1 for n, _ in xs if n > 0), "net_rs": round(sum(n for n, _ in xs), 2),
                "mean_net_pct": round(sum(q for _, q in xs) / len(xs), 2) if xs else None}
    open_ = [p for p in state.get("positions") or [] if ((p.get("rule") or {}).get("shadow_t100"))]
    return {"real_1520": agg(real), "shadow_t100": {**agg(shadow), "targets_hit": hits},
            "open_tagged": len(open_), "open_hit": sum(1 for p in open_ if p["rule"]["shadow_t100"].get("hit_at")),
            "untagged_closed": untagged,
            "rule": "strategies/S1_v10_t100_shadow_track.md (judged after >= 30 tagged trades have closed)"}


def shadow_entries(state: dict) -> dict:
    """The sub-Rs 2 shadow entries (strategies/S1_v10_subfloor_entry.md): closed judged entries (not flagged
    real_bought) with N, wins, mean net % of lot value, total net Rs and date-clustered t; open ones; the latest rows."""
    rows = list(((state.get("rules") or {}).get("fade_shadow_entries")) or [])
    judged = [r for r in rows if r.get("net") is not None and not r.get("real_bought")]
    pcts = [r["net_pct"] for r in judged]
    t = None
    if len(judged) > 1:
        from scanner.stats import clustered_t
        t = clustered_t(pcts, [r["date"] for r in judged])
    return {"closed": len(judged), "wins": sum(1 for r in judged if r["net"] > 0),
            "net_rs": round(sum(r["net"] for r in judged), 2),
            "mean_net_pct": round(sum(pcts) / len(pcts), 2) if pcts else None, "t": t,
            "open": sum(1 for r in rows if r.get("net") is None),
            "real_bought": sum(1 for r in rows if r.get("real_bought")),
            "rows": rows[-60:][::-1],
            "rule": "strategies/S1_v10_subfloor_entry.md (judged at 30 closed shadow entries)"}


def s20(state: dict) -> dict:
    """Tagged closed fade trades under the real 15:20 exit and under the -20 % shadow stop (filled at the bid that
    fired it): N, wins, mean net % of premium, total net Rs, stops fired and how many of those ended better at 15:20."""
    from server import charges as ch
    real, shadow, fired, cut_early, untagged = [], [], 0, 0, 0
    for p in state.get("closed") or []:
        r = p.get("rule") or {}
        if r.get("strategy") != "fade":
            continue
        sh = r.get("shadow_s20")
        if not sh:
            untagged += 1
            continue
        cost = p["entry"]["price"] * p["qty"]
        net = float(p.get("net_pnl", 0.0))
        if sh.get("hit_at") and sh.get("fill") is not None:
            fired += 1
            snet = round((sh["fill"] - p["entry"]["price"]) * p["qty"] - float(p.get("entry_charges", 0.0))
                         - ch.leg(p["instrument"], "SELL", p["qty"], sh["fill"])["total"], 2)
            cut_early += int(net > snet)
        else:
            snet = net
        real.append((net, net / cost * 100 if cost else 0.0))
        shadow.append((snet, snet / cost * 100 if cost else 0.0))

    def agg(xs):
        return {"closed": len(xs), "wins": sum(1 for n, _ in xs if n > 0), "net_rs": round(sum(n for n, _ in xs), 2),
                "mean_net_pct": round(sum(q for _, q in xs) / len(xs), 2) if xs else None}
    open_ = [p for p in state.get("positions") or [] if ((p.get("rule") or {}).get("shadow_s20"))]
    return {"real_1520": agg(real), "shadow_s20": {**agg(shadow), "stops_fired": fired, "better_at_1520": cut_early},
            "open_tagged": len(open_), "open_fired": sum(1 for p in open_ if p["rule"]["shadow_s20"].get("hit_at")),
            "untagged_closed": untagged,
            "rule": "strategies/S1_v10_s20_shadow_track.md (judged after >= 30 tagged trades have closed)"}


def walk(strikes: list[float], spot: float, side: str, quote: Callable[[float], dict | None],
         floor: float = MIN_PREMIUM):
    """From the strike nearest `spot` (a tie: the lower for calls, the higher for puts), away from the money, the first
    strike with a two-sided live quote, spread <= 10 % of the ask, ask >= Rs 2 and ask x lot within Rs 600-8,000.
    Returns (strike, ask, lot) or the reason there is none."""
    path = walk_path(strikes, spot, side)
    if not path:
        return "no strikes"
    reason = "no strike with a two-sided quote and a lot in Rs 600-8,000"
    for k in path:
        q = quote(k) or {}
        depth = q.get("depth") or {}
        bid, ask, lot = (depth.get("bid") or [[None]])[0][0], (depth.get("ask") or [[None]])[0][0], q.get("lot_size") or 0
        if not bid or not ask or not lot:
            continue
        ask = float(ask)
        if ask < floor:
            return f"premium below Rs {floor:g} (at {k:g}: ask {ask:g})"
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

    def _book(self, sig: dict, strikes: list[float]) -> dict[float, dict | None]:
        """{strike: live quote} for the strikes walk() may visit, in one quote call (QuoteSource.get_many)."""
        cs = {k: self._contract(sig, k) for k in strikes}
        many = getattr(self.ledger.quotes, "get_many", None)
        if many:
            got = many(list(cs.values()))
            return {k: got.get(c["tradingsymbol"]) for k, c in cs.items()}
        return {k: self.ledger.quotes.get(c) for k, c in cs.items()}

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
        self._track_t100(now)
        self._track_shadow_entries(now)
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
            if now.timestamp() - self._tried.get(key, 0) < RETRY_SECONDS - RETRY_SLACK:
                continue
            self._tried[key] = now.timestamp()
            spot = self.spot(sig["symbol"]) or sig.get("spot")
            book = self._book(sig, walk_path(sig.get("strikes") or [], spot, sig["side"]))
            why = never_fits(lot_of(book), BAND, MIN_PREMIUM)
            if why:                                              # no strike can ever fit: say so now, not at 15:20
                self._refuse(st, sig, today, why)
                self._waiting(st, key, now, None)
                self._shadow_entry(st, sig, key, now, spot, book.get, why)   # the Rs 2 floor's doing, too
                continue
            w = walk(sig.get("strikes") or [], spot, sig["side"], book.get)
            if isinstance(w, str):
                self._last_why[key] = w
                self._waiting(st, key, now, w)
                if w.startswith(f"premium below Rs {MIN_PREMIUM:g} "):
                    self._shadow_entry(st, sig, key, now, spot, book.get, w)
                continue
            k, px, lot = w
            rule = {"strategy": "fade", "entry_mode": "fade", "arms": ["F"], "signal_date": today,
                    "filed": sig.get("filed"), "why": sig.get("why"), "spot_at_entry": spot,
                    "np_yoy": sig.get("np_yoy"), "np_qoq": sig.get("np_qoq"), "rev_yoy": sig.get("rev_yoy"),
                    "shadow_np25": in_shadow(sig["side"], sig.get("np_yoy")),
                    "shadow_t100": {"target": t100_target(px), "hit_at": None, "max_bid": None},
                    "shadow_s20": {"stop": round(px * S20, 4), "hit_at": None, "fill": None, "min_bid": None}}
            pos = self.ledger.open_rule(self._contract(sig, k, lot), px, now, rule)
            done[key] = "bought"
            self._waiting(st, key, now, None)
            for r in st.get("fade_shadow_entries") or []:
                if r["key"] == key:
                    r["real_bought"] = True                      # its ask rose to Rs 2: not a refused trade after all
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

    def _shadow_entry(self, st: dict, sig: dict, key: str, now: datetime, spot: float, look, why: str) -> None:
        """A premium-floor refusal: the same walk on the same quotes with the floor at one tick. A strike found there
        (two-sided, spread <= 10 %, lot in Rs 600-8,000) is the shadow entry at its ask; none found, no entry."""
        rows = st.setdefault("fade_shadow_entries", [])
        if any(r["key"] == key for r in rows):
            return
        w = walk(sig.get("strikes") or [], spot, sig["side"], look, floor=TICK)
        if isinstance(w, str):
            log.info("fade shadow entry %s: none (%s)", key, w)
            return
        k, ask, lot = w
        c = self._contract(sig, k, lot)
        bid = (((look(k) or {}).get("depth") or {}).get("bid") or [[None]])[0][0]
        rows.append({"key": key, "date": now.date().isoformat(), "symbol": sig["symbol"], "side": sig["side"],
                     "expiry": sig["expiry"], "strike": k, "tradingsymbol": c["tradingsymbol"], "lot_size": lot,
                     "entry": ask, "bid_at_entry": bid, "lot_cost": round(ask * lot, 2),
                     "opened_at": now.isoformat(timespec="seconds"), "refused": why, "why": sig.get("why"),
                     "np_yoy": sig.get("np_yoy"), "spot_at_entry": spot, "last_bid": bid, "max_bid": bid,
                     "exit": None, "closed_at": None, "late": False, "charges": None, "net": None, "net_pct": None,
                     "real_bought": False})
        del rows[:-200]
        self.ledger._save()
        log.info("fade shadow entry: %s at %.2f x %d (refused: %s)", c["tradingsymbol"], ask, lot, why)

    def _track_shadow_entries(self, now: datetime) -> None:
        """Each poll: the best bid and the highest bid seen; from 15:20 on the entry day (or the first poll of a later
        day) the shadow sale at the best bid, else the last price - 1 tick, netted with real charges on both orders."""
        from server import charges as ch
        for r in (self.ledger.state.get("rules") or {}).get("fade_shadow_entries") or []:
            if r.get("exit") is not None:
                continue
            c = {"symbol": r["symbol"], "instrument": r["side"], "expiry": r["expiry"], "strike": r["strike"],
                 "tradingsymbol": r["tradingsymbol"], "lot_size": r["lot_size"]}
            q = self.ledger.quotes.get(c) or {}
            bid = ((q.get("depth") or {}).get("bid") or [[None]])[0][0]
            if bid:
                r["last_bid"], r["max_bid"] = bid, max(float(bid), r.get("max_bid") or 0.0)
            opened = datetime.fromisoformat(r["opened_at"]).date()
            if not (now.date() > opened or now.time() >= EOD_AT):
                continue
            px = bid or (max(0.0, round(q["last_price"] - TICK, 2)) if q.get("last_price") else None)
            if not px:
                continue                                         # no quote this poll: try the next one
            lot, cost = r["lot_size"], r["entry"] * r["lot_size"]
            charges = ch.leg(r["side"], "BUY", lot, r["entry"])["total"] + ch.leg(r["side"], "SELL", lot, px)["total"]
            net = round((px - r["entry"]) * lot - charges, 2)
            r.update(exit=px, closed_at=now.isoformat(timespec="seconds"), late=now.date() > opened,
                     charges=round(charges, 2), net=net, net_pct=round(net / cost * 100, 2) if cost else None)
            self.ledger._save()
            log.info("fade shadow entry exit: %s at %.2f, net %.2f", r["tradingsymbol"], px, net)

    def _track_t100(self, now: datetime) -> None:
        """The shadow exits on the entry day before 15:20, one bid read a poll for both: +100 % (the first poll whose
        best bid >= the target) and the -20 % stop (the first poll whose best bid <= the stop, filled at that bid)."""
        if not (OPEN_FROM <= now.time() < EOD_AT):
            return
        for pos in self.ledger.state["positions"]:
            r = pos.get("rule") or {}
            t1, s2 = r.get("shadow_t100"), r.get("shadow_s20")
            if not [x for x in (t1, s2) if x and not x.get("hit_at")]:
                continue
            if datetime.fromisoformat(pos["opened_at"]).date() != now.date():
                continue
            c = {k: pos[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol", "lot_size")}
            bid = (((self.ledger.quotes.get(c) or {}).get("depth") or {}).get("bid") or [[None]])[0][0]
            if not bid:
                continue
            if t1 and not t1.get("hit_at"):
                t1["max_bid"] = max(float(bid), t1.get("max_bid") or 0.0)
                if bid >= t1["target"]:
                    t1["hit_at"] = now.isoformat(timespec="seconds")
                    log.info("fade shadow t100 hit: %s bid %.2f >= %.2f", pos["tradingsymbol"], bid, t1["target"])
                    self.ledger._save()
            if s2 and not s2.get("hit_at") and now.time() >= S20_FROM:
                s2["min_bid"] = min(float(bid), s2["min_bid"]) if s2.get("min_bid") is not None else float(bid)
                if bid <= s2["stop"]:
                    s2["hit_at"], s2["fill"] = now.isoformat(timespec="seconds"), float(bid)
                    log.info("fade shadow s20 fired: %s bid %.2f <= %.2f", pos["tradingsymbol"], bid, s2["stop"])
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
