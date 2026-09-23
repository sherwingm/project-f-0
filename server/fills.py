"""Fill engine: what a paper order would really have paid, walked through the live book.

    fill(side, qty, depth, tick=0.05, mode="normal") -> {"price", "levels", "overflow_qty", "slippage_vs_mid", ...}

- Buy walks depth["ask"] from the best level, sell walks depth["bid"]. The price is the VWAP of the
  levels consumed plus one tick adverse for latency, rounded to the tick against the order.
- mode "penalty" adds a further half spread adverse (liquidity class penalty).
- mode "lottery" fills everything at the best level + 1 tick (buys) / - 1 tick (sells), whatever the spread.
- Overflow: quantity beyond the visible depth fills at the worst visible level plus one full quoted spread
  (adverse), and is reported as overflow_qty.

Orders placed while the market is closed are not filled at the close: they wait in
data/paper_queue.jsonl (PaperQueue) and fill at the first poll at or after 09:20 IST of the next session
against that poll's depth (server/paper.py runs the queue). Stop-loss exits fill with this same walk
(bids for a long) at the first poll after the trigger, never at the stop price itself.
"""
from __future__ import annotations

import json
import math
import threading
from pathlib import Path

MODES = ("normal", "penalty", "lottery")


class NoLiquidity(ValueError):
    """The side of the book the order needs is empty."""


def fill(side: str, qty: int, depth: dict | None, tick: float = 0.05, mode: str = "normal") -> dict:
    side = str(side).upper()
    if side not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if qty <= 0:
        raise ValueError("quantity must be positive")
    depth = depth or {}
    bids, asks = list(depth.get("bid") or []), list(depth.get("ask") or [])
    book = asks if side == "BUY" else bids
    if not book:
        raise NoLiquidity(f"no {'asks' if side == 'BUY' else 'bids'} in the book to {'buy' if side == 'BUY' else 'sell'} against")
    sign = 1 if side == "BUY" else -1
    best_bid, best_ask = (bids[0][0] if bids else None), (asks[0][0] if asks else None)
    mid = (best_bid + best_ask) / 2 if best_bid is not None and best_ask is not None else None
    spread = best_ask - best_bid if mid is not None else None
    visible = sum(q for _, q in book)

    levels: list[dict] = []
    if mode == "lottery":
        levels.append({"price": book[0][0], "qty": qty})
        vwap = book[0][0]
        overflow = max(0, qty - visible)
        raw = vwap + sign * tick
    else:
        remaining = qty
        for px, q in book:
            take = min(q, remaining)
            if take > 0:
                levels.append({"price": px, "qty": take})
                remaining -= take
            if remaining == 0:
                break
        overflow = remaining
        if overflow:
            # beyond the visible book: worst visible level plus one full quoted spread, adverse
            gap = spread if spread is not None else max(tick, abs(book[-1][0] - book[0][0]))
            levels.append({"price": round(book[-1][0] + sign * gap, 4), "qty": overflow, "overflow": True})
        vwap = sum(l["price"] * l["qty"] for l in levels) / qty
        raw = vwap + sign * tick                                   # latency: one tick adverse
        if mode == "penalty":
            raw += sign * (spread / 2 if spread is not None else tick)
    price = round_to_tick(raw, tick, up=side == "BUY")
    slip = None if mid is None else round((price - mid) * sign, 4)
    return {"side": side, "qty": qty, "mode": mode, "price": price, "levels": levels, "overflow_qty": overflow,
            "vwap": round(vwap, 4), "mid": None if mid is None else round(mid, 4),
            "spread": None if spread is None else round(spread, 4), "visible_qty": visible,
            "slippage_vs_mid": slip, "slippage_pct": None if not mid or slip is None else round(slip / mid * 100, 3),
            "slippage_value": None if slip is None else round(slip * qty, 2), "tick": tick}


def round_to_tick(price: float, tick: float, up: bool) -> float:
    """Round to the tick against the order: up for buys, down for sells (never below zero)."""
    n = price / tick
    n = math.ceil(n - 1e-9) if up else math.floor(n + 1e-9)
    return round(max(0.0, n * tick), 2)


class PaperQueue:
    """Market-closed paper orders, one JSON object per line in data/paper_queue.jsonl."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock = threading.Lock()

    def add(self, order: dict) -> dict:
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(order) + "\n")
        return order

    def pending(self) -> list[dict]:
        with self.lock:
            return self._read()

    def remove(self, order_ids: set[str]) -> None:
        with self.lock:
            keep = [o for o in self._read() if o.get("order_id") not in order_ids]
            self.path.write_text("".join(json.dumps(o) + "\n" for o in keep), encoding="utf-8")

    def _read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
