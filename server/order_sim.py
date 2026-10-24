"""Real-order fills for paper rule trades (strategies/S1_paper_real_order_fills.md). Pure functions, no state.

    protection(price) -> Rs        Kotak Neo's market-order protection for options, as an amount at that price
    tick_for(spot) -> Rs           NSE stock-option tick: Rs 0.01 below a Rs 250 stock, else Rs 0.05
    buy_limit / sell_limit         a marketable limit off the best ask / bid, rounded against the order
    rejected(limit, ltp) -> why    no last price, or outside NSE's limit price protection band; None when fine
    match(side, qty, limit, depth) the whole order against the levels within the limit, or None
    sweep(qty, depth)              a sell taking the whole visible bid side (overflow: lowest bid minus one spread)
"""
from __future__ import annotations

import math

BUY_WAIT_S = 60.0          # an unfilled buy is cancelled after this long
SELL_SWEEP_S = 10.0        # an unfilled sell takes the whole visible bid side from this long on
STEP_S = 0.9               # an order is checked at most once a second, never on the quote it was placed on
TICK_SPLIT = 250.0         # stock price below which the option tick is Rs 0.01

# Kotak Neo: market orders on options become limits this far from the last price (support page, read 2026-10-24)
BANDS = ((1.0, None), (5.0, 0.10), (10.0, 0.05), (100.0, 0.03), (500.0, 0.02), (math.inf, 0.01))


def protection(price: float) -> float:
    for top, pct in BANDS:
        if price < top:
            return 0.10 if pct is None else price * pct
    return price * 0.01


def tick_for(spot: float | None) -> float:
    return 0.01 if spot and spot < TICK_SPLIT else 0.05


def _round(x: float, tick: float, up: bool) -> float:
    n = x / tick
    n = math.ceil(n - 1e-9) if up else math.floor(n + 1e-9)
    return round(max(tick, n * tick), 2)


def buy_limit(ask: float, tick: float) -> float:
    return _round(ask + protection(ask), tick, up=True)


def sell_limit(bid: float, tick: float) -> float:
    return _round(bid - protection(bid), tick, up=False)


def rejected(limit: float, ltp: float | None) -> str | None:
    """What the exchange (or Kotak) would refuse the order for, else None."""
    if not ltp:
        return "rejected: no last traded price (Kotak refuses an option order without one)"
    band = 20.0 if ltp <= 50 else ltp * 0.40
    if abs(limit - ltp) > band:
        return f"rejected: limit {limit:g} outside NSE price protection ({ltp:g} +/- {band:g})"
    return None


def best(depth: dict | None, side: str) -> tuple[float | None, int | None]:
    lv = (depth or {}).get("ask" if side == "BUY" else "bid") or []
    return (lv[0][0], lv[0][1]) if lv else (None, None)


def match(side: str, qty: int, limit: float, depth: dict | None) -> dict | None:
    """The whole order against the book's levels within the limit (asks <= limit for a buy, bids >= limit for a
    sell), best first. None when they do not hold it all."""
    book = (depth or {}).get("ask" if side == "BUY" else "bid") or []
    levels, left = [], qty
    for px, q in book:
        if (px > limit + 1e-9) if side == "BUY" else (px < limit - 1e-9):
            break
        take = min(int(q or 0), left)
        if take > 0:
            levels.append({"price": px, "qty": take})
            left -= take
        if left == 0:
            return {"price": round(sum(l["price"] * l["qty"] for l in levels) / qty, 4), "levels": levels}
    return None


def sweep(qty: int, depth: dict | None) -> dict | None:
    """A sell taking every visible bid, best first; what is left fills at the lowest bid minus one quoted spread."""
    bids, asks = (depth or {}).get("bid") or [], (depth or {}).get("ask") or []
    if not bids:
        return None
    levels, left = [], qty
    for px, q in bids:
        take = min(int(q or 0), left)
        if take > 0:
            levels.append({"price": px, "qty": take})
            left -= take
        if left == 0:
            break
    if left:
        gap = (asks[0][0] - bids[0][0]) if asks else max(0.05, bids[0][0] - bids[-1][0])
        levels.append({"price": round(max(0.01, bids[-1][0] - gap), 2), "qty": left, "overflow": True})
    return {"price": round(sum(l["price"] * l["qty"] for l in levels) / qty, 4), "levels": levels}
