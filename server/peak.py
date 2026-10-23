"""The sellable peak while a paper trade is held, and how much of it the exit captured (strategies/S1_fade_peak_capture.md).

Measured on the BEST BID, the price a sell could have filled at, never on the last traded price, a candle high or
the stock's price. Conventions:
    - the window runs from the first quote after the entry through the quote that triggered the exit (included);
    - quotes after the exit never touch it (the after-sale follow is kept separately, in closed["after"]);
    - a quote without a bid counts as missing and is skipped;
    - of equal bids the earliest keeps the timestamp (a later equal quote does not move the peak);
    - "peak" means the highest OBSERVED bid: the market may have been higher between two quotes.

capture(): peak_return_pct = (peak_bid - entry) / entry x 100 (MFE, can be negative: never above entry);
MAE_pct = (low_bid - entry) / entry x 100; peak_net = the net P&L had it sold at peak_bid, with the trade's own entry
charges and charges.leg for the sell; giveback_rs = peak_net - realised net; capture_pct = net / peak_net x 100 only
when peak_net > 0 (else None with a reason), never clamped; peak_to_exit_pct = (peak_bid - exit) / peak_bid x 100.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from server import charges as ch

SOURCE_POLL = "live best bid (feed poll)"
SOURCE_FAST = "live best bid (1-s exit check)"
SOURCE_EXIT = "live best bid (exit quote)"
OBS_DIR = "observations"                 # data/observations/<date>.jsonl, one row per bid/ask change of an open trade


def observe(pos: dict, bid: float | None, now: datetime, source: str) -> None:
    """One quote's best bid into pos["held_bid"] (see the module doc). Missing bids are counted, not used."""
    hb = pos.setdefault("held_bid", {"first": None, "peak": None, "low": None, "last": None, "n": 0, "missing": 0,
                                     "sources": []})
    if bid is None or not bid > 0:
        hb["missing"] += 1
        return
    at = now.isoformat(timespec="seconds")
    pt = {"price": float(bid), "at": at}
    if hb["first"] is None:
        hb["first"] = pt
    if hb["peak"] is None or bid > hb["peak"]["price"]:
        hb["peak"] = pt
    if hb["low"] is None or bid < hb["low"]["price"]:
        hb["low"] = pt
    hb["last"] = pt
    hb["n"] += 1
    if source not in hb["sources"]:
        hb["sources"].append(source)


def capture(entry: float, qty: int, instrument: str, entry_charges: float, held_bid: dict | None,
            exit_price: float, net_pnl: float) -> dict | None:
    """The peak-capture numbers of one closed long option (see the module doc); None without any observed bid."""
    hb = held_bid or {}
    if not hb.get("peak") or not entry:
        return None
    peak, low = hb["peak"]["price"], hb["low"]["price"]
    peak_net = round((peak - entry) * qty - entry_charges - ch.leg(instrument, "SELL", qty, peak)["total"], 2)
    out = {"basis": "live best bid, observed at each quote (not LTP, not a candle high)",
           "peak_bid": peak, "peak_at": hb["peak"]["at"], "low_bid": low, "low_at": hb["low"]["at"],
           "peak_return_pct": round((peak - entry) / entry * 100, 2), "mae_pct": round((low - entry) / entry * 100, 2),
           "peak_gross": round((peak - entry) * qty, 2), "peak_net": peak_net,
           "giveback_rs": round(peak_net - net_pnl, 2),
           "peak_to_exit_pct": round((peak - exit_price) / peak * 100, 2) if peak else None,
           "quotes": hb.get("n", 0), "missing_quotes": hb.get("missing", 0)}
    if peak_net > 0:
        out["capture_pct"], out["capture_note"] = round(net_pnl / peak_net * 100, 1), None
    else:
        out["capture_pct"] = None
        out["capture_note"] = "N/A: selling at the peak bid would not have made a net profit"
    out["mfe_pct"] = out["peak_return_pct"]
    return out


class ObsLog:
    """Append-only bid/ask record of open paper trades: one JSON row per change, per day file. Rows: trade id,
    time, contract, best bid / ask and sizes, the stock price, the source."""

    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir) / OBS_DIR
        self._last: dict[str, tuple] = {}

    def add(self, pos: dict, quote: dict, now: datetime, source: str) -> None:
        d = quote.get("depth") or {}
        b = (d.get("bid") or [(None, None)])[0]
        a = (d.get("ask") or [(None, None)])[0]
        key = (b[0], b[1], a[0], a[1])
        if self._last.get(pos["id"]) == key:
            return
        self._last[pos["id"]] = key
        row = {"id": pos["id"], "t": now.isoformat(timespec="seconds"), "ts": pos["tradingsymbol"], "bid": b[0],
               "bid_qty": b[1], "ask": a[0], "ask_qty": a[1], "ltp": quote.get("last_price"),
               "spot": quote.get("underlying"), "src": quote.get("source") or source}
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / f"{now.date().isoformat()}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")


def entry_quote(quote: dict | None, now: datetime) -> dict | None:
    """The quote a rule trade was bought on: bid, ask, sizes, relative spread, last price and the stock's price."""
    if not quote:
        return None
    d = quote.get("depth") or {}
    b = (d.get("bid") or [(None, None)])[0]
    a = (d.get("ask") or [(None, None)])[0]
    mid = (a[0] + b[0]) / 2 if a[0] and b[0] else None
    return {"bid": b[0], "bid_qty": b[1], "ask": a[0], "ask_qty": a[1], "ltp": quote.get("last_price"),
            "spread_pct": round((a[0] - b[0]) / mid * 100, 2) if mid else None, "spot": quote.get("underlying"),
            "volume": quote.get("volume"), "oi": quote.get("open_interest"), "source": quote.get("source") or "kotak",
            "at": now.isoformat(timespec="seconds")}
