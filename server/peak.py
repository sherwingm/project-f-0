"""The sellable peak while a paper trade is held, and how much of it the exit captured (strategies/S1_fade_peak_capture.md).

Measured on the BEST BID, the price a sell could have filled at, never on the last traded price, a candle high or
the stock's price. Conventions:
    - the window runs from the first quote after the entry through the quote that triggered the exit (included);
    - quotes after the exit never touch it (the after-sale follow is kept separately, in closed["after"]);
    - a quote without a bid counts as missing and is skipped;
    - of equal bids the earliest keeps the timestamp (a later equal quote does not move the peak);
    - "peak" means the highest OBSERVED bid: the market may have been higher between two quotes;
    - the bid size at the peak is kept (peak_bid_qty); lot_fits_at_peak says whether the whole lot could have sold
      there at that one level (None when the size is unknown), so peak_net is an ESTIMATED opportunity, not a fill;
    - an exit priced from the last trade (no bid at that moment) is not an observation of the bid and is left out;
    - max_gap_s is the longest time between two observations: a peak inside a long gap was not seen.

capture(): peak_return_pct = (peak_bid - entry) / entry x 100 (MFE, can be negative: never above entry);
MAE_pct = (low_bid - entry) / entry x 100; peak_net = the net P&L had it sold at peak_bid, with the trade's own entry
charges and charges.leg for the sell; giveback_rs = peak_net - realised net; capture_pct = net / peak_net x 100 only
when peak_net > 0 (else None with a reason), never clamped; peak_to_exit_pct = (peak_bid - exit) / peak_bid x 100.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from server import charges as ch

SOURCE_POLL = "live best bid (feed poll)"
SOURCE_FAST = "live best bid (1-s exit check)"
SOURCE_EXIT = "live best bid (exit quote)"
OBS_DIR = "observations"                 # data/observations/<date>.jsonl, one row per bid/ask change of an open trade
IST = timezone(timedelta(hours=5, minutes=30))
# The entry quote's LAST-TRADE age (not the book's freshness: a quote with an old last trade can still carry a live
# bid / ask, and providers send no quote time). stale_ltt = True when the last trade was before that day's 09:15 open
# (a previous session, like ADANIENSOL on 23 Oct 2026), or more than LTT_STALE_S before the entry. A warning only:
# it never rejects or changes a trade.
LTT_STALE_S = 300
SESSION_OPEN = time(9, 15)
POST_EXIT_MINUTES = 60                   # after a sale the contract's bid/ask is still recorded this long (phase after_exit)
POST_EXIT_SLOW_S = 30                    # ... at most this often while prices come from Kotak (rate limits), not the stream


def observe(pos: dict, bid: float | None, now: datetime, source: str, qty: int | None = None) -> None:
    """One quote's best bid (and its size) into pos["held_bid"] (see the module doc). Missing bids are counted."""
    hb = pos.setdefault("held_bid", {"first": None, "peak": None, "low": None, "last": None, "n": 0, "missing": 0,
                                     "sources": []})
    if bid is None or not bid > 0:
        hb["missing"] += 1
        return
    at = now.isoformat(timespec="seconds")
    if hb["last"] is not None:
        gap = (now - datetime.fromisoformat(hb["last"]["at"])).total_seconds()
        hb["max_gap_s"] = max(hb.get("max_gap_s") or 0.0, round(gap, 1))
    pt = {"price": float(bid), "at": at, "qty": qty}
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
    pq = hb["peak"].get("qty")
    out = {"basis": "highest observed live best bid (not LTP, not a candle high); peak_net is an estimated "
                    "opportunity that assumes the whole lot sells at that bid",
           "peak_bid": peak, "peak_at": hb["peak"]["at"], "peak_bid_qty": pq,
           "lot_fits_at_peak": None if pq is None else bool(pq >= qty), "max_gap_s": hb.get("max_gap_s"), "low_bid": low, "low_at": hb["low"]["at"],
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
        self._lock = threading.Lock()                    # the feed poll, the 1-s check and the post-exit record write

    def add(self, pos: dict, quote: dict, now: datetime, source: str, phase: str = "held") -> None:
        """phase "held" while the trade is open; "after_exit" for the hypothetical follow-up after the sale (never
        part of the held peak or of any P&L)."""
        d = quote.get("depth") or {}
        b = (d.get("bid") or [(None, None)])[0]
        a = (d.get("ask") or [(None, None)])[0]
        key = (b[0], b[1], a[0], a[1])
        lk = f"{pos['id']}:{phase}"
        with self._lock:
            if self._last.get(lk) == key:
                return
            self._last[lk] = key
            self._write(pos, quote, now, source, phase, b, a)

    def _write(self, pos, quote, now, source, phase, b, a) -> None:
        row = {"id": pos["id"], "t": now.isoformat(timespec="seconds"), "ts": pos["tradingsymbol"], "bid": b[0],
               "bid_qty": b[1], "ask": a[0], "ask_qty": a[1], "ltp": quote.get("last_price"),
               "ltt": quote.get("timestamp"), "spot": quote.get("underlying"), "src": quote.get("source") or source,
               "via": source, "phase": phase}
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / f"{now.date().isoformat()}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")


def ltt_age(ltt, now: datetime) -> dict:
    """{"ltt_age_s", "stale_ltt", "stale_ltt_reason"} for a last-trade time (str "YYYY-MM-DD HH:MM:SS" IST, ISO, or
    datetime). Missing or unreadable -> age None, stale_ltt None, with the reason."""
    if ltt in (None, ""):
        return {"ltt_age_s": None, "stale_ltt": None, "stale_ltt_reason": "no last-trade time in the quote"}
    try:
        t = ltt if isinstance(ltt, datetime) else datetime.fromisoformat(str(ltt).strip().replace(" ", "T"))
    except ValueError:
        return {"ltt_age_s": None, "stale_ltt": None, "stale_ltt_reason": f"unreadable last-trade time {str(ltt)[:30]!r}"}
    t = t.replace(tzinfo=IST) if t.tzinfo is None else t
    n = now.replace(tzinfo=IST) if now.tzinfo is None else now
    age = round((n - t).total_seconds(), 1)
    open_ = datetime.combine(n.astimezone(IST).date(), SESSION_OPEN, IST)
    if age < -5:
        return {"ltt_age_s": age, "stale_ltt": None, "stale_ltt_reason": "last-trade time is after the entry (clock mismatch)"}
    if t < open_:
        return {"ltt_age_s": age, "stale_ltt": True, "stale_ltt_reason": "last trade before today's 09:15 open"}
    if age > LTT_STALE_S:
        return {"ltt_age_s": age, "stale_ltt": True, "stale_ltt_reason": f"last trade more than {LTT_STALE_S // 60} min old"}
    return {"ltt_age_s": age, "stale_ltt": False, "stale_ltt_reason": None}


def not_traded_today(quote: dict | None, now: datetime) -> bool:
    """True when the quote's last trade is from before today's 09:15 open: its bid / ask are left over from an earlier
    session, not a price anyone can trade at now (27 Oct 2026: five fade puts bought at 09:15:01 at yesterday's ask,
    up to twice the first real price). A quote without a last-trade time is not held back (Kotak sends none)."""
    return bool(quote) and ltt_age(quote.get("timestamp"), now)["stale_ltt_reason"] == "last trade before today's 09:15 open"


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
            "ltt": quote.get("timestamp"), "at": now.isoformat(timespec="seconds"),   # ltt: the quote's last trade
            **ltt_age(quote.get("timestamp"), now)}
