"""Liquidity class of one order against the live book: accept, penalty, lottery or refuse.

    classify(contract, quote, lots, sessions_to_expiry) -> {"class", "reasons", "spread_pct", "visible_qty", "oi", ...}

contract  {"symbol", "instrument": FUT|CE|PE, "tradingsymbol", "lot_size", "side": BUY|SELL, "expiry", "strike"}
quote     {"depth": {"bid": [(price, qty)], "ask": [...]}, "open_interest", "last_price"}  (best level first)

Futures
    accept   spread <= 0.05% of mid and order qty <= 25% of the visible depth on the side it trades against
    penalty  spread 0.05-0.15%, or qty 25-50% of visible depth: the fill adds half a spread
    refuse   spread > 0.15%, qty > 50% of visible depth, or no bid / no ask
Options
    lottery  premium < Rs 2 or sessions to expiry <= 2. Refused unless ALLOW_LOTTERY is true (default false),
             reason "cheap/near-expiry disabled (ALLOW_LOTTERY)". When allowed: not refused for spread or OI;
             fills at best ask + 1 tick (buys) / best bid - 1 tick (sells).
             Still needs the side it trades against (an ask to buy, a bid to sell) and qty <= 100% of that
             side's visible depth.
    accept   spread <= 3% of mid, strike OI >= 50 lots, qty <= 20% of visible depth
    penalty  spread 3-8%, or qty 20-100% of visible depth
    refuse   no bid or no ask, OI < 50 lots, qty > 100% of visible depth, or spread > 8%

Two readings of the spec are fixed here and documented in guide 12: an order inside the spread band but
using more of the book than the accept limit is `penalty` (not accept, not refuse), and an option spread
wider than the penalty band (> 8%) is `refuse`. All thresholds come from server/config.py.
Every refusal is appended to data/refusals.jsonl with the quote it was judged on.
"""
from __future__ import annotations

import json
import math
import threading
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.config import settings

IST = timezone(timedelta(hours=5, minutes=30))
_LOG_LOCK = threading.Lock()


@dataclass(frozen=True)
class Rules:
    fut_accept_spread_pct: float = 0.05
    fut_refuse_spread_pct: float = 0.15
    fut_accept_depth_pct: float = 25
    fut_refuse_depth_pct: float = 50
    opt_accept_spread_pct: float = 3
    opt_refuse_spread_pct: float = 8
    opt_accept_depth_pct: float = 20
    opt_refuse_depth_pct: float = 100
    opt_min_oi_lots: float = 50
    lottery_max_premium: float = 2
    lottery_max_sessions: int = 2
    allow_lottery: bool = False

    @classmethod
    def from_settings(cls, s=settings) -> "Rules":
        return cls(**{f.name: getattr(s, f.name if f.name.startswith(("lottery", "allow")) else "liq_" + f.name)
                      for f in fields(cls)})


def classify(contract: dict, quote: dict | None, lots: int, sessions_to_expiry: int | None,
             rules: Rules | None = None, refusals_path: Path | None = None, stage: str | None = None) -> dict:
    r = rules or Rules.from_settings()
    quote = quote or {}
    depth = quote.get("depth") or {}
    bids, asks = list(depth.get("bid") or []), list(depth.get("ask") or [])
    side = str(contract.get("side") or "BUY").upper()
    lot = int(contract.get("lot_size") or 0)
    qty = lots * lot
    book = asks if side == "BUY" else bids                   # the side this order trades against
    best_bid, best_ask = (bids[0][0] if bids else None), (asks[0][0] if asks else None)
    mid = (best_bid + best_ask) / 2 if best_bid and best_ask else None
    spread_pct = (best_ask - best_bid) / mid * 100 if mid else None
    visible = int(sum(q for _, q in book))
    depth_pct = qty / visible * 100 if visible else math.inf
    oi = quote.get("open_interest")
    oi_lots = oi / lot if oi is not None and lot else None
    fut = str(contract.get("instrument", "")).upper() == "FUT"
    premium = None if fut else (mid or (best_ask if side == "BUY" else best_bid) or best_ask or best_bid or quote.get("last_price"))

    out = {"spread_pct": _r(spread_pct, 3), "visible_qty": visible, "oi": oi, "oi_lots": _r(oi_lots, 1), "qty": qty,
           "depth_pct": None if math.isinf(depth_pct) else _r(depth_pct, 1), "mid": _r(mid, 4),
           "best_bid": best_bid, "best_ask": best_ask, "premium": _r(premium, 4)}
    if fut:
        cls, reasons = _futures(r, best_bid, best_ask, spread_pct, depth_pct, side)
    else:
        cls, reasons, _ = _options(r, best_bid, best_ask, spread_pct, depth_pct, oi_lots, premium, sessions_to_expiry, side)
    out.update({"class": cls, "reasons": reasons})
    if cls == "refuse" and refusals_path is not None:
        log_refusal(refusals_path, contract, quote, lots, out, stage)
    return out


def _futures(r: Rules, bid, ask, spread, depth_pct, side) -> tuple[str, list[str]]:
    if bid is None or ask is None:
        return "refuse", [f"no {'bid' if bid is None else 'ask'} in the book"]
    reasons = [f"spread {spread:.3f}% of mid", f"order is {_pct(depth_pct)} of the visible {'asks' if side == 'BUY' else 'bids'}"]
    if spread > r.fut_refuse_spread_pct:
        return "refuse", reasons + [f"spread above {r.fut_refuse_spread_pct}%"]
    if depth_pct > r.fut_refuse_depth_pct:
        return "refuse", reasons + [f"order uses more than {r.fut_refuse_depth_pct:g}% of the visible depth"]
    if spread <= r.fut_accept_spread_pct and depth_pct <= r.fut_accept_depth_pct:
        return "accept", reasons
    why = []
    if spread > r.fut_accept_spread_pct:
        why.append(f"spread between {r.fut_accept_spread_pct}% and {r.fut_refuse_spread_pct}%")
    if depth_pct > r.fut_accept_depth_pct:
        why.append(f"order is {r.fut_accept_depth_pct:g}-{r.fut_refuse_depth_pct:g}% of the visible depth")
    return "penalty", reasons + why + ["fill adds half a spread"]


def _options(r: Rules, bid, ask, spread, depth_pct, oi_lots, premium, dte, side) -> tuple[str, list[str], bool]:
    cheap = premium is not None and premium < r.lottery_max_premium
    near = dte is not None and dte <= r.lottery_max_sessions
    if cheap or near:
        why = ([f"premium Rs {premium:.2f} < Rs {r.lottery_max_premium:g}"] if cheap else []) + \
              ([f"{dte} session{'s' if dte != 1 else ''} to expiry (<= {r.lottery_max_sessions})"] if near else [])
        if not r.allow_lottery:
            return "refuse", why + ["cheap/near-expiry disabled (ALLOW_LOTTERY)"], False
        need = "ask" if side == "BUY" else "bid"
        if (ask if side == "BUY" else bid) is None:
            return "refuse", why + [f"a lottery fill still needs an {need} to trade against; there is none"], False
        if depth_pct > r.opt_refuse_depth_pct:
            return "refuse", why + [f"order is {_pct(depth_pct)} of the visible depth (> {r.opt_refuse_depth_pct:g}%)"], False
        info = [f"spread {spread:.2f}% of mid" if spread is not None else "one-sided book",
                f"strike OI {oi_lots:.0f} lots" if oi_lots is not None else "strike OI unknown"]
        return "lottery", why + info + [f"fills at best {need} {'+' if side == 'BUY' else '-'} 1 tick regardless of spread"], True
    if bid is None or ask is None:
        return "refuse", [f"no {'bid' if bid is None else 'ask'} in the book"], False
    reasons = [f"spread {spread:.2f}% of mid", f"strike OI {oi_lots:.0f} lots" if oi_lots is not None else "strike OI unknown",
               f"order is {_pct(depth_pct)} of the visible {'asks' if side == 'BUY' else 'bids'}"]
    if oi_lots is None or oi_lots < r.opt_min_oi_lots:
        return "refuse", reasons + [f"strike OI below {r.opt_min_oi_lots:g} lots"], False
    if depth_pct > r.opt_refuse_depth_pct:
        return "refuse", reasons + [f"order is larger than the visible depth"], False
    if spread > r.opt_refuse_spread_pct:
        return "refuse", reasons + [f"spread above {r.opt_refuse_spread_pct:g}%"], False
    if spread <= r.opt_accept_spread_pct and depth_pct <= r.opt_accept_depth_pct:
        return "accept", reasons, False
    why = []
    if spread > r.opt_accept_spread_pct:
        why.append(f"spread between {r.opt_accept_spread_pct:g}% and {r.opt_refuse_spread_pct:g}%")
    if depth_pct > r.opt_accept_depth_pct:
        why.append(f"order is {r.opt_accept_depth_pct:g}-{r.opt_refuse_depth_pct:g}% of the visible depth")
    return "penalty", reasons + why + ["fill adds half a spread"], False


def log_refusal(path: Path, contract: dict, quote: dict, lots: int, result: dict, stage: str | None = None) -> dict:
    rec = {"time": datetime.now(IST).isoformat(timespec="seconds"), "stage": stage,
           "symbol": contract.get("symbol"), "contract": contract.get("tradingsymbol"),
           "instrument": contract.get("instrument"), "expiry": contract.get("expiry"), "strike": contract.get("strike"),
           "side": contract.get("side"), "lots": lots, "qty": result.get("qty"), "reasons": result.get("reasons"),
           "quote": {"depth": _plain_depth(quote.get("depth")), "last_price": quote.get("last_price"),
                     "open_interest": quote.get("open_interest"), "timestamp": quote.get("timestamp")},
           "spread_pct": result.get("spread_pct"), "visible_qty": result.get("visible_qty")}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_LOCK, path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def read_refusals(path: Path, limit: int = 200) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows[::-1][:limit]


def _plain_depth(d) -> dict:
    d = d or {}
    return {"bid": [list(x) for x in d.get("bid") or []], "ask": [list(x) for x in d.get("ask") or []]}


def _pct(v: float) -> str:
    return "unknown (no visible depth)" if math.isinf(v) else f"{v:.0f}%"


def _r(v, nd):
    return None if v is None else round(v, nd)
