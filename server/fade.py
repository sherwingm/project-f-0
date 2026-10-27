"""S1 v12 results-day fade in the live paper account (paper only, 1 lot each): v10's entry
(strategies/S1_v10_results_day_fade_paper.md) with v12's exit (strategies/S1_v12_fade_trail2.md, live from 2026-10-22):
v11's -20 % stop (strategies/S1_v11_fade_stop20.md, 2026-10-21) plus a 2 % trailing stop.

The scan carries scanner/fade_live.py's list as meta.fade: for one session (`session`), the stocks whose results
day it is, with the side to buy (a put on strong numbers, a call on weak ones), the expiry and its strikes. On that
session this module:

    entry  from 09:15:00 to 15:20, retried every second per stock by entry_tick() (from 2026-10-23; every 30 s poll before,
           2 minutes until 2026-10-20; one quote call a second for every waiting signal) until it fills: from the strike nearest
           the live stock price, walking away from the money (down for puts, up for calls), the first strike with a
           live bid and ask, a spread <= 10 % of the ask, ask >= Rs 2 and one lot at the ask within Rs 600-8,000;
           bought at the ask. Nothing by 15:20 -> refused with the reason.
    exit   v12: from 09:16 on the entry day, on the best bid: the first bid <= 0.80 x entry sells ("fade_stop"); the
           first bid >= 1.10 x entry switches a trail on, and once on the first bid <= 0.98 x the highest bid since sells
           ("fade_trail"); else the first poll from 15:20 the same day, at the best bid (else the last price - 1 tick).
           (v11, 2026-10-21 only, had the stop without the trail.)
    speed  the stop and both trails are checked by fast_tick() about every second (FADE_FAST_SECONDS, server/app.py) on
           one quote call for the open fade contracts only; the 30 s poll checks them too.
    shadow v11's exit (rule.shadow_v11): the same as the real one unless the trail sold; then the stop or the 15:20 bid,
           tracked after the sale.
           A position still open on a later day (the server was down at 15:20) is sold at the first poll of that day.
    shadow v10's exit (held to 15:20) on every fade trade, rule.shadow_v10: for a stopped trade, the contract's bid at
           the first poll from 15:20 that day; else the same as the real result.
    trail  rule.shadow_trail (strategies/S1_v11_trail_shadow_track.md): the -20 % stop plus a trailing stop that starts at
           a bid >= 1.10 x entry and sells at a bid <= 0.95 x the highest bid since then; else the same as the real result.

Positions carry rule.strategy = "fade" and arm "F"; server/rules.py's S1 exits leave them alone. Positions whose signal
date is in CARRY_DATES (empty: the eight trades of 2026-10-16 were closed instead) would follow _carry_exits.
"""
from __future__ import annotations

import json
import logging
import math
import re
import threading
from datetime import datetime, time
from typing import Callable

from server import peak as pk, sessions
from server.broker import tradingsymbol
from server.rules import lot_of, never_fits, streaming

log = logging.getLogger("fade")

OPEN_FROM, EOD_AT = time(9, 15), time(15, 20)
RETRY_SECONDS = 30                                       # the 30 s poll's own retry (DECISIONS.md, 2026-10-20; was 120)
# entry_tick() retries every second from 09:15:00 on one quote call (DECISIONS.md, 2026-10-22, the user's decision)
RETRY_SLACK = 5                                          # a poll landing a few seconds early still counts
BAND, MIN_PREMIUM, MAX_SPREAD, WALK_MAX = (600.0, 8000.0), 2.0, 0.10, 15
# the entry probe (record only, strategies/S1_v11_entry_probe.md)
PROBE_FROM, PROBE_FAST_TO, PROBE_TO = time(9, 14, 50), time(9, 20), time(10, 0)
PROBE_SLOW, PROBE_SAVE, PROBE_STRIKES = 10, 60, 8
PROBE_COLS = ["t", "symbol", "side", "strike", "ask", "ask_qty", "bid", "bid_qty", "ltp", "ltt", "volume", "open",
              "atp", "underlying"]
TICK = 0.01                                              # NSE stock-option tick since 2025-11-03 (Rs 0.05 before)
SHADOW_FLOOR = 0.05                                      # the sub-Rs 2 shadow walk's floor, as pre-registered

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
# S1 v11's stop (strategies/S1_v11_fade_stop20.md; live from 2026-10-21): from 09:16:00 on the entry day, sold at the
# best bid of the first poll with the bid at or below 0.80 x entry. The v10 exit is tracked as rule.shadow_v10.
S20, S20_FROM = 0.80, time(9, 16)
# Shadow tag "trail" (strategies/S1_v11_trail_shadow_track.md): on the entry day from 09:16, the first bid >= 1.10 x entry
# switches a trailing stop on; once on, the first bid <= 0.95 x the highest bid since then sells (shadow only).
TRAIL_START, TRAIL_GAP = 1.10, 0.05
# S1 v12's trail (strategies/S1_v12_fade_trail2.md; live from 2026-10-22): on at a bid >= 1.10 x entry, sells at a bid
# <= 0.98 x the highest bid since.
V12_START, V12_GAP = 1.10, 0.02
# S1 v12 below-Rs 2 rule (strategies/S1_v12_sub2_listing.md; live from 2026-10-23): a fade signal refused only by the
# Rs 2 floor is bought anyway when its first liquid strike's listing-day price was Rs 2-7, with as many lots as cost
# <= Rs 8,000; exit v12.
SUB2_LISTING, SUB2_CAP = (2.0, 7.0), 8000.0
LIVE_VERSIONS = ("v11", "v12")                           # the fade's live era (from 2026-10-21)
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


def fd2(state: dict) -> dict:
    """Shadow tag fd2 (strategies/S1_v11_fd2_shadow_track.md): v11 fade puts whose market-hours filing day already fell
    >= 2 % (tagged) against the other market-hours puts and all other puts, on the real results; judged at 20."""
    groups = {"tagged": [], "market_hours_other": [], "unmeasured": [], "other_puts": []}
    unknown = untagged = 0
    for p in state.get("closed") or []:
        r = p.get("rule") or {}
        if r.get("strategy") != "fade" or r.get("version") not in LIVE_VERSIONS or p.get("instrument") != "PE":
            continue
        fd = r.get("shadow_fd2")
        if fd is None:
            untagged += 1
            continue
        cost = p["entry"]["price"] * p["qty"]
        net = float(p.get("net_pnl", 0.0))
        x = (net, net / cost * 100 if cost else 0.0)
        if fd.get("market_hours") and fd.get("tagged") is None:
            unknown += 1
            groups["unmeasured"].append(x)                          # not measured: kept out of both comparisons
        elif fd.get("tagged"):
            groups["tagged"].append(x)
        elif fd.get("market_hours"):
            groups["market_hours_other"].append(x)
        else:
            groups["other_puts"].append(x)

    def agg(xs):
        return {"closed": len(xs), "wins": sum(1 for n, _ in xs if n > 0), "net_rs": round(sum(n for n, _ in xs), 2),
                "mean_net_pct": round(sum(q for _, q in xs) / len(xs), 2) if xs else None}
    open_ = [p for p in state.get("positions") or [] if ((p.get("rule") or {}).get("shadow_fd2") or {}).get("tagged")]
    return {**{k: agg(v) for k, v in groups.items()}, "open_tagged": len(open_), "unknown": unknown,
            "untagged_closed": untagged, "review_at": 20,
            "rule": "strategies/S1_v11_fd2_shadow_track.md (judged at 20 closed tagged puts)"}


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


def v10_shadow(state: dict) -> dict:
    """S1 v11 live vs the v10 exit as a shadow (strategies/S1_v11_fade_stop20.md): closed fade trades tagged
    rule.shadow_v10. Real = v11 (the -20 % stop at the bid, else 15:20); shadow = v10 (held to 15:20: for a stopped
    trade the bid at the first poll from 15:20 that day, else the real result). N, wins, mean net %, total net Rs."""
    real, shadow, stops, held_better, pending, untagged, days = [], [], 0, 0, 0, 0, []
    for p in state.get("closed") or []:
        r = p.get("rule") or {}
        if r.get("strategy") != "fade":
            continue
        sh = r.get("shadow_v10")
        if not sh:
            untagged += 1
            continue
        if sh.get("status") == "pending":
            pending += 1
            continue
        cost = p["entry"]["price"] * p["qty"]
        net = float(p.get("net_pnl", 0.0))
        snet = float(sh["net"]) if sh.get("status") == "done" else net
        if p.get("reason") == "fade_stop":
            stops += 1
            held_better += int(snet > net)
        real.append((net, net / cost * 100 if cost else 0.0))
        shadow.append((snet, snet / cost * 100 if cost else 0.0))
        days.append(str(p.get("closed_at", ""))[:10])

    def agg(xs):
        return {"closed": len(xs), "wins": sum(1 for n, _ in xs if n > 0), "net_rs": round(sum(n for n, _ in xs), 2),
                "mean_net_pct": round(sum(q for _, q in xs) / len(xs), 2) if xs else None}
    t = None
    if len(real) > 1:
        from scanner.stats import clustered_t
        t = clustered_t([s_[1] - r_[1] for r_, s_ in zip(real, shadow)], days)       # v10 minus v11, per trade
    return {"real_v11": agg(real), "shadow_v10": agg(shadow), "stops": stops, "stopped_but_v10_better": held_better,
            "t_v10_minus_v11": t, "pending": pending, "untagged_closed": untagged,
            "rule": "strategies/S1_v11_fade_stop20.md (reviewed at 30 closed fade trades)"}


def v12_compare(state: dict) -> dict:
    """S1 v12 live (strategies/S1_v12_fade_trail2.md) vs its shadows on the same closed v12 trades: v11 (the stop alone)
    and v10 (held to 15:20). N, wins, mean net %, total net Rs, t of (v12 - shadow); reviewed at 30."""
    rows = []
    for p in state.get("closed") or []:
        r = p.get("rule") or {}
        if r.get("strategy") != "fade" or r.get("version") != "v12":
            continue
        net = float(p.get("net_pnl", 0.0))
        sh = {}
        for k in ("shadow_v11", "shadow_v10"):
            x = r.get(k) or {}
            sh[k] = float(x["net"]) if x.get("status") == "done" else net if x.get("status") == "same" else None
        if None in sh.values():
            continue                                             # a shadow still waiting for its price
        cost = p["entry"]["price"] * p["qty"]
        rows.append((str(p.get("closed_at", ""))[:10], net, sh["shadow_v11"], sh["shadow_v10"], cost, p.get("reason")))

    def agg(i):
        xs = [(r_[i], r_[i] / r_[4] * 100 if r_[4] else 0.0) for r_ in rows]
        return {"closed": len(xs), "wins": sum(1 for n, _ in xs if n > 0), "net_rs": round(sum(n for n, _ in xs), 2),
                "mean_net_pct": round(sum(q for _, q in xs) / len(xs), 2) if xs else None}

    def t_of(i):
        if len(rows) < 2:
            return None
        from scanner.stats import clustered_t
        return clustered_t([(r_[1] - r_[i]) / r_[4] * 100 if r_[4] else 0.0 for r_ in rows], [r_[0] for r_ in rows])
    pending = sum(1 for p in state.get("closed") or [] if (p.get("rule") or {}).get("version") == "v12") - len(rows)
    return {"real_v12": agg(1), "shadow_v11": agg(2), "shadow_v10": agg(3), "t_v12_minus_v11": t_of(2),
            "t_v12_minus_v10": t_of(3), "trail_exits": sum(1 for r_ in rows if r_[5] == "fade_trail"),
            "stops": sum(1 for r_ in rows if r_[5] == "fade_stop"), "pending": pending, "review_at": 30,
            "open_active": sum(1 for p in state.get("positions") or []
                               if ((p.get("rule") or {}).get("trail") or {}).get("status") == "active"),
            "rule": "strategies/S1_v12_fade_trail2.md (reviewed at 30 closed v12 trades)"}


def trail_shadow(state: dict) -> dict:
    """Shadow tag "trail" (strategies/S1_v11_trail_shadow_track.md): closed fade trades tagged rule.shadow_trail, real
    v11 vs the -20 % stop + trailing stop (start +10 %, gap 5 %): N, wins, mean net %, total net Rs, t of the
    difference; judged at 30."""
    real, shadow, days, exits, untagged = [], [], [], 0, 0
    for p in state.get("closed") or []:
        r = p.get("rule") or {}
        if r.get("strategy") != "fade":
            continue
        sh = r.get("shadow_trail")
        if not sh:
            untagged += 1
            continue
        if sh.get("status") not in ("done", "same"):
            continue
        cost = p["entry"]["price"] * p["qty"]
        net = float(p.get("net_pnl", 0.0))
        snet = float(sh["net"]) if sh["status"] == "done" else net
        exits += int(sh["status"] == "done")
        real.append((net, net / cost * 100 if cost else 0.0))
        shadow.append((snet, snet / cost * 100 if cost else 0.0))
        days.append(str(p.get("closed_at", ""))[:10])

    def agg(xs):
        return {"closed": len(xs), "wins": sum(1 for n, _ in xs if n > 0), "net_rs": round(sum(n for n, _ in xs), 2),
                "mean_net_pct": round(sum(q for _, q in xs) / len(xs), 2) if xs else None}
    t = None
    if len(real) > 1:
        from scanner.stats import clustered_t
        t = clustered_t([s_[1] - r_[1] for r_, s_ in zip(real, shadow)], days)       # trail minus v11, per trade
    open_ = [p for p in state.get("positions") or [] if (p.get("rule") or {}).get("shadow_trail")]
    return {"real_v11": agg(real), "shadow_trail": agg(shadow), "trail_exits": exits, "t_trail_minus_v11": t,
            "open_tagged": len(open_),
            "open_active": sum(1 for p in open_ if p["rule"]["shadow_trail"].get("status") == "active"),
            "open_done": sum(1 for p in open_ if p["rule"]["shadow_trail"].get("status") == "done"),
            "untagged_closed": untagged, "review_at": 30,
            "rule": "strategies/S1_v11_trail_shadow_track.md (judged at 30 closed tagged trades)"}


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


def sub2_pick(strikes: list[float], spot: float, side: str, quote: Callable[[float], dict | None], listing: dict):
    """The below-Rs 2 rule's contract: the first strike on the walk with a two-sided quote and a spread <= 10 % of the
    ask; bought if its listing-day price is Rs 2-7, with as many lots as cost <= Rs 8,000 (at least one must fit).
    Returns (strike, ask, lot, lots, listing price) or the reason there is none."""
    for k in walk_path(strikes, spot, side):
        q = quote(k) or {}
        depth = q.get("depth") or {}
        bid, ask, lot = (depth.get("bid") or [[None]])[0][0], (depth.get("ask") or [[None]])[0][0], q.get("lot_size") or 0
        if not bid or not ask or not lot or (float(ask) - float(bid)) > MAX_SPREAD * float(ask):
            continue
        ask = float(ask)
        lots = int(SUB2_CAP // (ask * lot))
        if lots < 1:
            return f"below-Rs 2 rule: 1 lot at {k:g} costs more than Rs 8,000"
        lc = (listing or {}).get(f"{k:g}")
        if lc is None:
            return f"below-Rs 2 rule: no listing price for {k:g}"
        if not SUB2_LISTING[0] <= lc < SUB2_LISTING[1]:
            return f"below-Rs 2 rule: listing price Rs {lc:g} at {k:g} is outside Rs 2-7"
        return k, ask, lot, lots, lc
    return "below-Rs 2 rule: no two-sided strike"


class FadeTrader:
    def __init__(self, ledger, fade: Callable[[], dict | None], spot: Callable[[str], float | None] | None = None):
        self.ledger, self.fade = ledger, fade
        self.spot = spot or ledger.quotes.spot
        self._tried: dict[str, float] = {}
        self._last_why: dict[str, str] = {}
        self._lock = threading.RLock()                   # on_poll (feed thread) and fast_tick (fast-exit thread)
        self._cache: dict[str, dict | None] | None = None  # fast_tick's quotes, by tradingsymbol
        self._book_cache: dict[str, dict | None] | None = None   # entry_tick's quotes for the entry walks
        self._tick_quotes: tuple[float, dict] = (0.0, {})  # entry_tick's last call, reused by entry_probe that second
        self._probe: dict = {}                           # entry_probe's day: signals and changed quotes
        self._probe_seen: dict[str, tuple] = {}
        self._probe_last = self._probe_saved = 0.0

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
        if self._book_cache is not None:
            return {k: self._book_cache.get(c["tradingsymbol"]) for k, c in cs.items()}
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

    def _quote(self, c: dict) -> dict | None:
        """The contract's quote: fast_tick's one-call cache while it runs (no extra broker calls), else a live quote."""
        if self._cache is not None:
            return self._cache.get(c["tradingsymbol"])
        return self.ledger.quotes.get(c)

    def fast_tick(self, now: datetime) -> int:
        """About every second (server/app.py): one quote call for today's open fade contracts, then the live exit checks
        on those bids (v11/v12's stop, v12's trail, the 5 % trail and +100 % shadows). Returns the contracts quoted."""
        if not self.ledger.is_open(now) or not (S20_FROM <= now.time() < EOD_AT):
            return 0
        with self.ledger.lock, self._lock:
            cs = {}
            for pos in self.ledger.state["positions"]:
                r = pos.get("rule") or {}
                if r.get("strategy") != "fade" or self.carried(pos):
                    continue
                if datetime.fromisoformat(pos["opened_at"]).date() != now.date():
                    continue
                cs[pos["tradingsymbol"]] = {k: pos[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol",
                                                                "lot_size")}
            if not cs:
                return 0
            many = getattr(self.ledger.quotes, "get_many", None)
            self._cache = many(list(cs.values())) if many else {k: self.ledger.quotes.get(c) for k, c in cs.items()}
            from server.peak import SOURCE_FAST
            for pos in self.ledger.state["positions"]:            # each second's bid into the while-held peak
                if pos["tradingsymbol"] in cs:
                    self.ledger.observe(pos, self._cache.get(pos["tradingsymbol"]), now, SOURCE_FAST)
            try:
                self._track_trail(now)
                self._track_v12(now)
                self._track_t100(now)
            finally:
                self._cache = None
            return len(cs)

    def entry_probe(self, now: datetime) -> int:
        """Record only (strategies/S1_v11_entry_probe.md): the live book of today's fade signals' strikes, every second
        09:14:50-09:20 and every PROBE_SLOW s to 10:00, so the day can show which entry would have paid v11's backtest
        price (the 09:15:00 opening print). One quote call; trades nothing. Saved to data/entry_probe/<date>.json
        (mirrored to paper-state) each minute. Returns the contracts quoted."""
        t = now.time()
        if not sessions.is_session(now.date()) or not (PROBE_FROM <= t < PROBE_TO):
            if self._probe.get("rows") and now.timestamp() - self._probe_saved > 0:
                self._probe_save(now, force=True)
            return 0
        if t >= PROBE_FAST_TO and now.timestamp() - self._probe_last < PROBE_SLOW - 0.5:
            return 0
        today = now.date().isoformat()
        sigs = self.signals(today)
        if not sigs:
            return 0
        if self._probe.get("date") != today:
            self._probe = {"date": today, "rule": "strategies/S1_v11_entry_probe.md", "signals": [],
                           "cols": PROBE_COLS, "rows": []}
            self._probe_seen, self._probe_saved = {}, 0.0
        cs, meta = {}, {}
        for sig in sigs:
            spot = self.spot(sig["symbol"]) or sig.get("spot")
            for k in walk_path(sig.get("strikes") or [], spot, sig["side"])[:PROBE_STRIKES]:
                c = self._contract(sig, k)
                cs[c["tradingsymbol"]], meta[c["tradingsymbol"]] = c, (sig["symbol"], sig["side"], k)
            if not any(s["symbol"] == sig["symbol"] for s in self._probe["signals"]):
                self._probe["signals"].append({k: sig.get(k) for k in ("symbol", "side", "expiry", "why", "np_yoy",
                                                                        "spot", "strikes", "listing")})
        if not cs:
            return 0
        at, have = self._tick_quotes
        got = {k: have[k] for k in cs if k in have} if abs(now.timestamp() - at) < 0.9 else {}
        rest = [c for k, c in cs.items() if k not in got]       # entry_tick's call this second covers waiting signals
        if rest:
            many = getattr(self.ledger.quotes, "get_many", None)
            got.update(many(rest) if many else {c["tradingsymbol"]: self.ledger.quotes.get(c) for c in rest})
        self._probe_last = now.timestamp()
        stamp = now.strftime("%H:%M:%S.%f")[:-3]
        for ts, q in got.items():
            if not q:
                continue
            d = q.get("depth") or {}
            bid, ask = (d.get("bid") or [(None, None)])[0], (d.get("ask") or [(None, None)])[0]
            ltt = q.get("timestamp")
            ltt = ltt.strftime("%H:%M:%S") if hasattr(ltt, "strftime") else ltt
            vals = (ask[0], ask[1], bid[0], bid[1], q.get("last_price"), ltt, q.get("volume"),
                    (q.get("ohlc") or {}).get("open"), q.get("atp"), q.get("underlying"))
            if self._probe_seen.get(ts) == vals:                  # unchanged since the last second: not stored again
                continue
            self._probe_seen[ts] = vals
            sym, side, k = meta[ts]
            self._probe["rows"].append([stamp, sym, side, k, *vals])
        self._probe_save(now)
        return len(cs)

    def _probe_save(self, now: datetime, force: bool = False) -> None:
        if not force and now.timestamp() - self._probe_saved < PROBE_SAVE:
            return
        p = self.ledger.dir / "entry_probe" / f"{self._probe['date']}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self._probe, separators=(",", ":"), default=str))
        self._probe_saved = now.timestamp() if not force else float("inf")

    def on_poll(self, now: datetime) -> None:
        with self.ledger.lock, self._lock:
            self._on_poll(now)

    def _on_poll(self, now: datetime) -> None:
        if not self.ledger.is_open(now):
            return
        self._track_trail(now)
        self._track_v12(now)
        self._track_after_trail(now)
        self._track_t100(now)
        self._track_v10_shadow(now)
        self._track_shadow_entries(now)
        self._exits(now)
        self._carry_exits(now)
        if now.time() < OPEN_FROM:
            return
        self._entries(now, every=0 if streaming(self.ledger) else RETRY_SECONDS - RETRY_SLACK)

    def entry_tick(self, now: datetime) -> int:
        """About every second (server/app.py) from 09:15:00 to 15:20: one quote call for every waiting signal's strikes,
        then the same entry walk as the poll. Returns the contracts quoted (0: nothing waiting or outside the hours)."""
        if not self.ledger.is_open(now) or not (OPEN_FROM <= now.time() < EOD_AT):
            return 0
        with self.ledger.lock, self._lock:
            today = now.date().isoformat()
            done = self._state().setdefault("fade", {})
            cs = {}
            for sig in self.signals(today):
                if f"{today}:{sig['symbol']}" in done:
                    continue
                spot = self.spot(sig["symbol"]) or sig.get("spot")
                for k in walk_path(sig.get("strikes") or [], spot, sig["side"]):
                    c = self._contract(sig, k)
                    cs[c["tradingsymbol"]] = c
            if not cs:
                return 0
            many = getattr(self.ledger.quotes, "get_many", None)
            self._book_cache = many(list(cs.values())) if many else {k: self.ledger.quotes.get(c) for k, c in cs.items()}
            self._tick_quotes = (now.timestamp(), self._book_cache)
            try:
                self._entries(now, every=0)
            finally:
                self._book_cache = None
            return len(cs)

    def _entries(self, now: datetime, every: float = RETRY_SECONDS - RETRY_SLACK) -> None:
        """Walk each of today's waiting signals (at most once per `every` seconds each); refuse what is left at 15:20."""
        today = now.date().isoformat()
        st = self._state()
        done = st.setdefault("fade", {})
        for sig in self.signals(today):
            key = f"{today}:{sig['symbol']}"
            if key in done:
                continue
            if now.time() >= EOD_AT:
                self._refuse(st, sig, today, self._last_why.get(key) or "no affordable two-sided strike 09:15-15:20")
                self._waiting(st, key, now, None)
                continue
            if every and now.timestamp() - self._tried.get(key, 0) < every:
                continue
            self._tried[key] = now.timestamp()
            spot = self.spot(sig["symbol"]) or sig.get("spot")
            book = self._book(sig, walk_path(sig.get("strikes") or [], spot, sig["side"]))
            if any(book.values()) and all(pk.not_traded_today(q, now) for q in book.values() if q):
                self._last_why[key] = w = "waiting for the first trade today (every quote is yesterday's)"
                self._waiting(st, key, now, w)                   # no price of today yet: no buy and no refusal
                continue
            why = never_fits(lot_of(book), BAND, MIN_PREMIUM)
            if why and self._sub2(st, sig, key, today, now, spot, book):
                continue
            if why:                                              # no strike can ever fit: say so now, not at 15:20
                self._refuse(st, sig, today, why)
                self._waiting(st, key, now, None)
                self._shadow_entry(st, sig, key, now, spot, book.get, why)   # the Rs 2 floor's doing, too
                continue
            w = walk(sig.get("strikes") or [], spot, sig["side"], book.get)
            if isinstance(w, str) and w.startswith(f"premium below Rs {MIN_PREMIUM:g} ") and                     self._sub2(st, sig, key, today, now, spot, book):
                continue
            if isinstance(w, str):
                self._last_why[key] = w
                self._waiting(st, key, now, w)
                if w.startswith(f"premium below Rs {MIN_PREMIUM:g} "):
                    self._shadow_entry(st, sig, key, now, spot, book.get, w)
                continue
            k, px, lot = w
            if pk.not_traded_today(book.get(k), now):           # yesterday's book: wait for today's first trade
                self._last_why[key] = w = f"waiting for the first trade today at {k:g} (the quote is yesterday's)"
                self._waiting(st, key, now, w)
                continue
            self._buy(st, sig, key, today, now, spot, k, px, lot, quote=book.get(k))

    def _sub2(self, st, sig, key, today, now, spot, book) -> bool:
        """The below-Rs 2 rule: buy now if sub2_pick finds a contract; the reason is kept when it does not."""
        p = sub2_pick(sig.get("strikes") or [], spot, sig["side"], book.get, sig.get("listing") or {})
        if isinstance(p, str):
            st.setdefault("fade_sub2_why", {})[key] = p
            return False
        k, px, lot, lots, lc = p
        if pk.not_traded_today(book.get(k), now):               # yesterday's book: wait (True = handled for now)
            self._last_why[key] = w = f"waiting for the first trade today at {k:g} (the quote is yesterday's)"
            self._waiting(st, key, now, w)
            return True
        self._buy(st, sig, key, today, now, spot, k, px, lot, lots=lots,
                  sub2={"listing_close": lc, "lots": lots, "rule": "strategies/S1_v12_sub2_listing.md"}, quote=book.get(k))
        return True

    def _buy(self, st, sig, key, today, now, spot, k, px, lot, lots: int = 1, sub2: dict | None = None,
             quote: dict | None = None) -> None:
        """Order the contract decided at the ask `px`: the ledger fills it as a real order (or at once with instant
        fills); the stop, trail and +100 % levels come from the fill price. Until it fills the signal shows "ordered"."""
        done = st.setdefault("fade", {})

        def rule(fill: float) -> dict:
            r = {"strategy": "fade", "version": "v12", "entry_mode": "fade", "arms": ["F"], "signal_date": today,
                 "filed": sig.get("filed"), "why": sig.get("why"), "spot_at_entry": spot,
                 "np_yoy": sig.get("np_yoy"), "np_qoq": sig.get("np_qoq"), "rev_yoy": sig.get("rev_yoy"),
                 "shadow_np25": in_shadow(sig["side"], sig.get("np_yoy")),
                 "shadow_t100": {"target": t100_target(fill), "hit_at": None, "max_bid": None},
                 "stop": {"level": round(fill * S20, 4), "from": S20_FROM.strftime("%H:%M"), "min_bid": None},
                 "trail": {"status": "open", "start": round(fill * V12_START, 4), "gap": V12_GAP, "peak": None},
                 "shadow_v10": {"status": "open"},
                 "shadow_v11": {"status": "open"},
                 "shadow_trail": {"status": "open", "start": round(fill * TRAIL_START, 4), "peak": None},
                 "shadow_fd2": sig.get("filing_day") if sig["side"] == "PE" else None}
            if sub2:
                r["sub2"] = sub2
            return r

        def filled(pos: dict, at: datetime) -> None:
            with self._lock:
                done[key] = "bought" if not sub2 else "bought (below Rs 2, listing Rs 2-7)"
                self._waiting(st, key, at, None)
                for r in st.get("fade_shadow_entries") or []:
                    if r["key"] == key:
                        r["real_bought"] = True              # its ask rose to Rs 2: not a refused trade after all
                self.ledger._save()
            log.info("fade entry: %s at %.2f x %d (%s)", pos["tradingsymbol"], pos["entry"]["price"], lot, sig.get("why"))

        def cancelled(why: str, at: datetime) -> None:
            with self._lock:
                done.pop(key, None)                          # the walk tries again, as for any unfilled entry
                self._last_why[key] = f"buy order not filled ({why})"
                self._waiting(st, key, at, self._last_why[key])

        done[key] = "ordered"
        self._waiting(st, key, now, f"buy order working at {px:g} (limit order, strategies/S1_paper_real_order_fills.md)")
        self.ledger.buy_rule(self._contract(sig, k, lot), px, now, rule, lots=lots, quote=quote, on_fill=filled,
                             on_cancel=cancelled, cutoff=datetime.combine(now.date(), EOD_AT, now.tzinfo), spot=spot)

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
            if pos.get("exiting"):
                continue                                         # its sell order is working
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
                self.ledger.close_at(pos["id"], px, now, reason, price_is_bid=bool(bid))
                log.info("fade carry exit %s: %s at %.2f (close %.2f, entry %.2f, peak %.2f)",
                         reason, pos["tradingsymbol"], px, close, entry, c["peak"])
            self.ledger._save()

    def _shadow_entry(self, st: dict, sig: dict, key: str, now: datetime, spot: float, look, why: str) -> None:
        """A premium-floor refusal: the same walk on the same quotes with the floor at one tick. A strike found there
        (two-sided, spread <= 10 %, lot in Rs 600-8,000) is the shadow entry at its ask; none found, no entry."""
        rows = st.setdefault("fade_shadow_entries", [])
        if any(r["key"] == key for r in rows):
            return
        w = walk(sig.get("strikes") or [], spot, sig["side"], look, floor=SHADOW_FLOOR)
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
        """On the entry day before 15:20, one bid read a poll for both: the +100 % shadow exit (the first poll whose best
        bid >= the target) and v11's real stop (from 09:16, the first poll whose best bid <= the stop: sold at it)."""
        if not (OPEN_FROM <= now.time() < EOD_AT):
            return
        stopped = []
        for pos in self.ledger.state["positions"]:
            if pos.get("exiting"):
                continue                                         # its sell order is working
            r = pos.get("rule") or {}
            t1, stop = r.get("shadow_t100"), r.get("stop")
            if not ((t1 and not t1.get("hit_at")) or (stop and r.get("strategy") == "fade" and not self.carried(pos))):
                continue
            if datetime.fromisoformat(pos["opened_at"]).date() != now.date():
                continue
            c = {k: pos[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol", "lot_size")}
            bid = (((self._quote(c) or {}).get("depth") or {}).get("bid") or [[None]])[0][0]
            if not bid:
                continue
            if t1 and not t1.get("hit_at"):
                t1["max_bid"] = max(float(bid), t1.get("max_bid") or 0.0)
                if bid >= t1["target"]:
                    t1["hit_at"] = now.isoformat(timespec="seconds")
                    log.info("fade shadow t100 hit: %s bid %.2f >= %.2f", pos["tradingsymbol"], bid, t1["target"])
                    self.ledger._save()
            if stop and r.get("strategy") == "fade" and not self.carried(pos) and now.time() >= S20_FROM:
                stop["min_bid"] = min(float(bid), stop["min_bid"]) if stop.get("min_bid") is not None else float(bid)
                if bid <= stop["level"]:
                    stopped.append((pos, float(bid)))
        for pos, bid in stopped:                                 # v11's real exit: the -20 % stop at the bid
            r = pos["rule"]
            r["spot_at_exit"] = self.spot(pos["symbol"])
            if "shadow_v10" in r:
                r["shadow_v10"] = {"status": "pending", "stopped_at": now.isoformat(timespec="seconds")}
            if (r.get("shadow_trail") or {}).get("status") in ("open", "active"):
                r["shadow_trail"]["status"] = "same"             # stopped before the trail sold: the same result
            if (r.get("shadow_v11") or {}).get("status") == "open":
                r["shadow_v11"] = {"status": "same"}             # v12 stopped: v11 stops on the same bid
            self.ledger.close_at(pos["id"], bid, now, "fade_stop")
            log.info("fade stop: %s at %.2f (stop %.2f)", pos["tradingsymbol"], bid, r["stop"]["level"])

    def _track_trail(self, now: datetime) -> None:
        """Shadow tag "trail" on the entry day from 09:16 to before 15:20, on the best bid: start at a bid >= the start
        level, then sell (shadow) at the first bid <= 0.95 x the highest bid since the start, netted with real charges."""
        from server import charges as ch
        if not (S20_FROM <= now.time() < EOD_AT):
            return
        for pos in self.ledger.state["positions"]:
            if pos.get("exiting"):
                continue                                         # its sell order is working
            r = pos.get("rule") or {}
            sh = r.get("shadow_trail")
            if r.get("strategy") != "fade" or not sh or sh.get("status") not in ("open", "active"):
                continue
            if datetime.fromisoformat(pos["opened_at"]).date() != now.date():
                continue
            c = {k: pos[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol", "lot_size")}
            bid = (((self._quote(c) or {}).get("depth") or {}).get("bid") or [[None]])[0][0]
            if not bid:
                continue
            bid = float(bid)
            if sh["status"] == "open":
                if bid >= sh["start"]:
                    sh.update(status="active", peak=bid, started_at=now.isoformat(timespec="seconds"))
                    self.ledger._save()
                continue
            if bid <= round(sh["peak"] * (1 - TRAIL_GAP), 4):
                net = round((bid - pos["entry"]["price"]) * pos["qty"] - float(pos.get("entry_charges_open", 0.0))
                            - ch.leg(pos["instrument"], "SELL", pos["qty"], bid)["total"], 2)
                sh.update(status="done", fill=bid, net=net, at=now.isoformat(timespec="seconds"))
                log.info("fade trail shadow: %s at %.2f (peak %.2f), net %.2f", pos["tradingsymbol"], bid, sh["peak"], net)
            else:
                sh["peak"] = max(sh["peak"], bid)
            self.ledger._save()

    def _track_v12(self, now: datetime) -> None:
        """S1 v12's trail, the live exit (strategies/S1_v12_fade_trail2.md): on the entry day from 09:16 to before 15:20,
        on the best bid: on at a bid >= the start; once on, the first bid <= (1 - gap) x the highest bid since sells.
        v11 (stop only) and v10 (15:20) then follow the same contract as shadows (_track_after_trail, _track_v10_shadow)."""
        if not (S20_FROM <= now.time() < EOD_AT):
            return
        sold = []
        for pos in self.ledger.state["positions"]:
            if pos.get("exiting"):
                continue                                         # its sell order is working
            r = pos.get("rule") or {}
            tr = r.get("trail")
            if r.get("strategy") != "fade" or not tr or tr.get("status") not in ("open", "active"):
                continue
            if datetime.fromisoformat(pos["opened_at"]).date() != now.date():
                continue
            c = {k: pos[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol", "lot_size")}
            bid = (((self._quote(c) or {}).get("depth") or {}).get("bid") or [[None]])[0][0]
            if not bid:
                continue
            bid = float(bid)
            if tr["status"] == "open":
                if bid >= tr["start"]:
                    tr.update(status="active", peak=bid, started_at=now.isoformat(timespec="seconds"))
                    self.ledger._save()
                continue
            if bid <= round(tr["peak"] * (1 - tr["gap"]), 4):
                tr.update(status="sold", at=now.isoformat(timespec="seconds"), level=round(tr["peak"] * (1 - tr["gap"]), 4))
                sold.append((pos, bid))
            elif bid > tr["peak"]:
                tr["peak"] = bid
                self.ledger._save()
        for pos, bid in sold:
            r = pos["rule"]
            r["spot_at_exit"] = self.spot(pos["symbol"])
            if "shadow_v10" in r:
                r["shadow_v10"] = {"status": "pending", "stopped_at": now.isoformat(timespec="seconds")}
            if "shadow_v11" in r:
                r["shadow_v11"] = {"status": "tracking", "since": now.isoformat(timespec="seconds")}
            self.ledger.close_at(pos["id"], bid, now, "fade_trail")
            log.info("fade v12 trail exit: %s at %.2f (peak %.2f)", pos["tradingsymbol"], bid, r["trail"]["peak"])

    def _track_after_trail(self, now: datetime) -> None:
        """After a v12 trail sale, on the same contract's best bid: v11's shadow (the -20 % stop before 15:20, else the
        first bid from 15:20; a later day's first poll if missed, flagged late) and the 5 % trail shadow (its trail before
        15:20, else the same 15:20 bid), each netted with real charges on both orders."""
        from server import charges as ch
        for p in self.ledger.state.get("closed") or []:
            r = p.get("rule") or {}
            if r.get("strategy") != "fade" or p.get("reason") != "fade_trail":
                continue
            v11, t5 = r.get("shadow_v11") or {}, r.get("shadow_trail") or {}
            live11, live5 = v11.get("status") == "tracking", t5.get("status") in ("open", "active")
            if not (live11 or live5):
                continue
            day = datetime.fromisoformat(p["closed_at"]).date()
            c = {k: p[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol", "lot_size")}
            q = self.ledger.quotes.get(c) or {}
            bid = ((q.get("depth") or {}).get("bid") or [[None]])[0][0]
            eod = now.date() > day or now.time() >= EOD_AT
            px = bid or ((max(0.0, round(q["last_price"] - TICK, 2)) if q.get("last_price") else None) if eod else None)
            if not px:
                continue
            px = float(px)

            def net(x: float) -> float:
                return round((x - p["entry"]["price"]) * p["qty"] - float(p.get("entry_charges", 0.0))
                             - ch.leg(p["instrument"], "SELL", p["qty"], x)["total"], 2)
            stamp = dict(at=now.isoformat(timespec="seconds"), late=now.date() > day)
            if live11 and (eod or px <= r["stop"]["level"]):
                v11.update(status="done", fill=px, net=net(px), why="15:20" if eod and px > r["stop"]["level"] else "stop", **stamp)
            if live5:
                if eod:
                    t5.update(status="done", fill=px, net=net(px), **stamp)
                elif t5["status"] == "active" and px <= round(t5["peak"] * (1 - TRAIL_GAP), 4):
                    t5.update(status="done", fill=px, net=net(px), **stamp)
                elif t5["status"] == "active":
                    t5["peak"] = max(t5["peak"], px)
            self.ledger._save()

    def _track_v10_shadow(self, now: datetime) -> None:
        """v10's exit for the trades v11 stopped: the contract's best bid (else the last price - 1 tick) at the first
        poll from 15:20 on the day it was stopped (a later day's first poll if that one was missed, flagged late),
        netted with real charges on both orders."""
        from server import charges as ch
        for p in self.ledger.state.get("closed") or []:
            r = p.get("rule") or {}
            sh = r.get("shadow_v10")
            if r.get("strategy") != "fade" or not sh or sh.get("status") != "pending":
                continue
            day = datetime.fromisoformat(p["closed_at"]).date()
            if now.date() == day and now.time() < EOD_AT:
                continue
            c = {k: p[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol", "lot_size")}
            q = self.ledger.quotes.get(c) or {}
            bid = ((q.get("depth") or {}).get("bid") or [[None]])[0][0]
            px = bid or (max(0.0, round(q["last_price"] - TICK, 2)) if q.get("last_price") else None)
            if not px:
                continue                                         # no quote this poll: try the next one
            net = round((px - p["entry"]["price"]) * p["qty"] - float(p.get("entry_charges", 0.0))
                        - ch.leg(p["instrument"], "SELL", p["qty"], px)["total"], 2)
            sh.update(status="done", fill=px, net=net, at=now.isoformat(timespec="seconds"), late=now.date() > day)
            self.ledger._save()
            log.info("fade v10 shadow: %s at %.2f, net %.2f (real %.2f)", p["tradingsymbol"], px, net, p["net_pnl"])

    def _exits(self, now: datetime) -> None:
        """Sell every fade position from 15:20 on its entry day, or at the first poll of any later day."""
        for pos in list(self.ledger.state["positions"]):
            if pos.get("exiting"):
                continue                                         # its sell order is working
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
            if "shadow_v10" in r:
                r["shadow_v10"] = {"status": "same"}             # not stopped: v10 and v11 sold together
            if (r.get("shadow_trail") or {}).get("status") in ("open", "active"):
                r["shadow_trail"]["status"] = "same"             # the trail never sold: the same 15:20 result
            if (r.get("shadow_v11") or {}).get("status") == "open":
                r["shadow_v11"] = {"status": "same"}             # sold at 15:20: v11 sells there too
            self.ledger.close_at(pos["id"], px, now, "fade_eod" if now.date() == opened else "fade_late",
                                 price_is_bid=bool(bid))
            log.info("fade exit: %s at %.2f", pos["tradingsymbol"], px)
