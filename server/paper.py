"""Paper account: every paper order is filled against the live book, charged, marked and exited honestly.

Ledger file data/paper_ledger.json (capital, cash, open positions, closed trades, daily equity history).
Order log data/paper_orders.jsonl (one line per order event; the latest line per order id wins).
Queue data/paper_queue.jsonl (orders placed while the market is closed).

Entry
    quote (fresh depth for the contract) -> liquidity class (server/liquidity.py) -> fill (server/fills.py:
    accept = normal walk, penalty = walk + half spread, lottery = best level +/- 1 tick) -> charges
    (server/charges.py) -> risk gate (server/risk.py, when attached) -> position.
    Futures need a stop price. Options may have one.
    Market closed: the order is queued and fills at the first poll at/after 09:20 IST of the next session,
    against that poll's depth, after every check runs again. A LIMIT price is a cap on that fill: an order
    whose fill would be worse is rejected (or cancelled from the queue); the engine never rests orders.
Marks (every live poll)
    long positions at the best bid, short positions at the best ask. A long option with no bid is marked
    at 0 (it cannot be sold); a missing side on anything else keeps the previous mark, flagged stale.
    Unrealised P&L is net of the entry charges and of the charges to exit at the mark.
Exits
    manual   an order on the opposite side of an open position (whole or part of it)
    stop     long: bid <= stop, short: ask >= stop; the exit fills at the book walk on the first poll
             after the trigger, never at the stop price
    forced_t2  on the second-last session before expiry (T-2), at the first poll at/after 09:20: stock
             derivatives are physically settled and this account never holds to expiry. A position opened
             on or after T-2 is closed at the first poll at/after 09:20 of the next session.
    Exits are never refused for spread or OI while the side they need exists (they fill in penalty mode);
    with no bid (for a long) an automatic exit waits for the next poll.
Equity = cash + what every open position would realise if closed at its mark, after exit charges.
Realised P&L of a closed trade = gross move x qty - entry charges - exit charges.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from server import charges as ch
from server import sessions
from server.config import settings
from server.fills import NoLiquidity, PaperQueue, fill
from server.liquidity import BUCKET_NORMAL, Rules, classify

log = logging.getLogger(__name__)
IST = sessions.IST
MODE_FOR_CLASS = {"accept": "normal", "penalty": "penalty", "lottery": "lottery"}


class PaperRejected(ValueError):
    """A paper order that cannot be accepted; the message is shown on the order sheet."""


def contract_of(req, resolved: dict) -> dict:
    return {"symbol": req.symbol, "instrument": req.instrument, "expiry": req.expiry, "strike": req.strike,
            "tradingsymbol": resolved["tradingsymbol"], "lot_size": int(resolved["lot_size"]), "side": req.side}


def is_option(instrument: str) -> bool:
    return str(instrument).upper() in ("CE", "PE")


def max_loss(instrument: str, side: str, qty: int, entry_px: float, stop: float | None) -> float | None:
    """Worst case the trade is sized for: a long option loses at most its premium; anything with a stop
    loses |entry - stop| x qty; a short option or a future without a stop has no defined max loss."""
    if is_option(instrument) and side == "BUY":
        return round(entry_px * qty, 2)
    if stop:
        return round(abs(entry_px - stop) * qty, 2)
    return None


def estimate_margin(instrument: str, side: str, qty: int, px: float, underlying: float | None = None,
                    strike: float | None = None) -> float:
    """MARGIN_ESTIMATE_PCT of notional for futures and short options; the premium for long options."""
    if is_option(instrument) and side == "BUY":
        return round(px * qty, 2)
    notional_px = px if not is_option(instrument) else (underlying or strike or px)
    return round(settings.margin_estimate_pct / 100 * notional_px * qty, 2)


class QuoteSource:
    """Live quotes for one contract: the feed's polled near future when it matches, else the provider's
    quote_one() (options are not in the polling universe). Returns None with no feed."""

    def __init__(self, feed):
        self.feed = feed
        self.last_error: str | None = None

    def get(self, contract: dict, fresh: bool = True) -> dict | None:
        if not self.feed:
            return None
        ts = contract["tradingsymbol"]
        try:
            one = getattr(self.feed.provider, "quote_one", None)
            if contract["instrument"] == "FUT" and not (fresh and one):
                row = self.feed.snapshot()["quotes"].get(contract["symbol"]) or {}
                if row.get("fut_tradingsymbol") == ts and row.get("fut_depth"):
                    return {"depth": row["fut_depth"], "last_price": row.get("fut_ltp"),
                            "open_interest": row.get("fut_oi"), "timestamp": row.get("ts"), "underlying": row.get("ltp")}
            if one:
                q = one(ts)
                row = self.feed.snapshot()["quotes"].get(contract["symbol"]) or {}
                return {**q, "underlying": row.get("ltp")}
        except Exception as exc:  # noqa: BLE001 - a failed quote means "no fill now", never a crash
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.warning("paper quote %s: %s", ts, self.last_error)
        return None

    def spot(self, symbol: str) -> float | None:
        if not self.feed:
            return None
        return (self.feed.snapshot()["quotes"].get(symbol) or {}).get("ltp")


class PaperLedger:
    def __init__(self, data_dir: Path, quotes: QuoteSource | None = None, capital: float | None = None,
                 tick: float | None = None, rules: Rules | None = None, always_open: bool = False):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "paper_ledger.json"
        self.orders_path = self.dir / "paper_orders.jsonl"
        self.refusals_path = self.dir / "refusals.jsonl"
        self.queue = PaperQueue(self.dir / "paper_queue.jsonl")
        self.quotes = quotes or QuoteSource(None)
        self.tick = tick or settings.fill_tick
        self.rules = rules
        self.always_open = always_open
        self.risk = None                     # server.risk.RiskGate, attached by the app
        self.lock = threading.RLock()
        self._seq = 0
        self.state = self._load(capital if capital is not None else settings.paper_capital)

    # ------------------------------------------------------------ persistence
    def _load(self, capital: float) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {"capital": float(capital), "cash": float(capital), "positions": [], "closed": [], "daily": {},
                "peak_equity": float(capital), "created_at": datetime.now(IST).isoformat(timespec="seconds")}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.state, indent=1), encoding="utf-8")
        os.replace(tmp, self.path)

    def _id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{int(time.time() * 1000)}-{self._seq}"

    def _log_order(self, rec: dict) -> None:
        with self.orders_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")

    # ------------------------------------------------------------ clock / market
    def is_open(self, now: datetime) -> bool:
        return self.always_open or sessions.market_open_at(now)

    # ------------------------------------------------------------ evaluation (preview and every place)
    def evaluate(self, req, resolved: dict, stop: float | None = None, now: datetime | None = None,
                 stage: str = "preview") -> dict:
        """Everything the Review screen shows, and the list of reasons the order cannot go through.
        Runs the same way at preview, at place and when a queued order comes due."""
        now = (now or datetime.now(IST)).astimezone(IST)
        contract = contract_of(req, resolved)
        qty = int(resolved["quantity"])
        pos = self._position_for(contract["tradingsymbol"])
        intent = "entry"
        blocked: list[str] = []
        if pos is not None:
            if pos["side"] == req.side:
                blocked.append(f"a {'long' if pos['side'] == 'BUY' else 'short'} {pos['tradingsymbol']} position is already open; "
                               "close it before opening another")
            elif req.lots > pos["lots"]:
                blocked.append(f"the exit is larger than the open position ({pos['lots']} lot{'s' if pos['lots'] != 1 else ''})")
            else:
                intent = "exit"
        dte = sessions.sessions_to_expiry(now, req.expiry)
        review = {"intent": intent, "position_id": pos["id"] if pos and intent == "exit" else None, "contract": contract,
                  "lots": req.lots, "qty": qty, "order_type": req.order_type, "limit_price": req.price, "stop": stop,
                  "sessions_to_expiry": dte, "expiry": req.expiry,
                  "t2_date": sessions.t_minus(req.expiry, 2).isoformat(), "queued": None, "liquidity": None,
                  "fill": None, "bucket": BUCKET_NORMAL, "charges_entry": None, "round_trip_now": None,
                  "margin": None, "max_loss": None, "blocked": blocked, "warnings": []}
        open_now = self.is_open(now)
        # with the market closed the book is stale: book-dependent checks warn now and decide at 09:20
        book_block = blocked if open_now else review["warnings"]
        if not open_now:
            when = sessions.next_fill_time(now)
            review["queued"] = {"fill_after": when.isoformat(),
                                "message": f"Market closed: this order is queued and fills at the first poll at or after "
                                           f"{when.strftime('%H:%M')} IST on {when.strftime('%a %d %b')}, against that "
                                           "poll's depth. Every check runs again then; the estimate below uses the last quote."}
        if intent == "entry" and req.instrument == "FUT" and not stop:
            blocked.append("futures need a stop price (the risk per trade is |entry - stop| x quantity)")

        quote = self.quotes.get(contract)
        review["quote_error"] = None if quote else self.quotes.last_error
        if not quote or not (quote.get("depth") or {}).get("bid") and not (quote.get("depth") or {}).get("ask"):
            if open_now:
                blocked.append("no live depth for this contract: paper orders fill only against the live book "
                               "(set DATA_PROVIDER and check the feed)")
            self._risk(review, req, contract, None, stop, now, stage)
            return review

        liq = classify(contract, quote, req.lots, dte, rules=self.rules,
                       refusals_path=self.refusals_path if intent == "entry" and open_now else None, stage=stage)
        review["liquidity"] = liq
        review["bucket"] = liq["bucket"]
        mode = MODE_FOR_CLASS.get(liq["class"])
        if liq["class"] == "refuse":
            if intent == "entry":
                book_block.append("liquidity: " + "; ".join(liq["reasons"]) +
                                  ("" if open_now else " (on the last quote; checked again when the queued order comes due)"))
                mode = None if open_now else "penalty"
            else:
                mode = "penalty"                      # exits are never refused while the needed side exists
        if mode is not None:
            try:
                f = fill(req.side, qty, quote["depth"], self.tick, mode)
            except NoLiquidity as exc:
                book_block.append(str(exc))
                f = None
            if f:
                review["fill"] = f
                if req.order_type == "LIMIT" and req.price:
                    worse = f["price"] > req.price if req.side == "BUY" else f["price"] < req.price
                    if worse:
                        book_block.append(f"expected fill Rs {f['price']:.2f} is beyond your limit Rs {req.price:.2f}; "
                                          "the paper engine does not rest orders (use Market, or a limit the book reaches)")
                review["charges_entry"] = ch.leg(req.instrument, req.side, qty, f["price"])
                opp = "SELL" if req.side == "BUY" else "BUY"
                try:
                    back = fill(opp, qty, quote["depth"], self.tick, mode if mode != "lottery" else "lottery")
                    rt = ch.round_trip(req.instrument, req.side, qty, f["price"], back["price"])
                    sign = 1 if req.side == "BUY" else -1
                    review["round_trip_now"] = {"exit_price": back["price"], "charges": rt,
                                                "net_pnl": round(sign * (back["price"] - f["price"]) * qty - rt["total"], 2)}
                except NoLiquidity:
                    review["round_trip_now"] = {"exit_price": None, "charges": None, "net_pnl": None,
                                                "note": "no opposite side in the book to exit into right now"}
                if intent == "entry":
                    underlying = quote.get("underlying") or self.quotes.spot(req.symbol)
                    review["margin"] = estimate_margin(req.instrument, req.side, qty, f["price"], underlying, req.strike)
                    review["max_loss"] = max_loss(req.instrument, req.side, qty, f["price"], stop)
                    if stop:
                        bad = (req.side == "BUY" and stop >= f["price"]) or (req.side == "SELL" and stop <= f["price"])
                        if bad:
                            book_block.append(f"the stop Rs {stop:.2f} is on the wrong side of the expected fill Rs {f['price']:.2f}")
        self._risk(review, req, contract, quote, stop, now, stage)
        return review

    def _risk(self, review, req, contract, quote, stop, now, stage) -> None:
        if self.risk is not None and review["intent"] == "entry":
            self.risk.check(self, review, req, contract, stop, now)

    # ------------------------------------------------------------ orders
    def preview(self, req, resolved: dict, stop: float | None = None, now: datetime | None = None) -> dict:
        with self.lock:
            return self.evaluate(req, resolved, stop, now, stage="preview")

    def submit(self, req, resolved: dict, stop: float | None = None, now: datetime | None = None) -> dict:
        now = (now or datetime.now(IST)).astimezone(IST)
        with self.lock:
            self._ensure_day(now)
            review = self.evaluate(req, resolved, stop, now, stage="place")
            base = self._order_record(req, resolved, stop, now, review)
            if review["blocked"]:
                self._log_order({**base, "status": "REJECTED", "reason": "; ".join(review["blocked"])})
                raise PaperRejected("; ".join(review["blocked"]))
            if review["queued"]:
                rec = {**base, "status": "QUEUED", "fill_after": review["queued"]["fill_after"]}
                self.queue.add({**rec, "request": _req_dict(req), "resolved": resolved, "stop": stop})
                self._log_order(rec)
                return rec
            rec = self._execute(req, resolved, stop, review, now, base)
            self._touch_day(now)
            self._save()
            return rec

    def _order_record(self, req, resolved, stop, now, review) -> dict:
        return {"order_id": self._id("PAPER"), "placed_at": now.isoformat(timespec="seconds"), "paper": True,
                **_req_dict(req), **{k: resolved[k] for k in ("tradingsymbol", "quantity", "lot_size") if k in resolved},
                "stop": stop, "intent": review["intent"]}

    def _execute(self, req, resolved, stop, review, now, base) -> dict:
        f = review["fill"]
        liq = review["liquidity"] or {}
        if review["intent"] == "exit":
            pos = self._position_by_id(review["position_id"])
            closed = self._close(pos, int(resolved["quantity"]), f, liq.get("class"), now, "manual")
            rec = {**base, "status": "FILLED", "fill_price": f["price"], "fill": f, "liquidity_class": liq.get("class"),
                   "bucket": pos["bucket"], "position_id": pos["id"], "net_pnl": closed["net_pnl"],
                   "charges": closed["exit_charges"]}
        else:
            pos = self._open(req, resolved, stop, review, f, liq, now)
            rec = {**base, "status": "FILLED", "fill_price": f["price"], "fill": f, "liquidity_class": liq.get("class"),
                   "bucket": pos["bucket"], "position_id": pos["id"], "charges": pos["entry_charges"]}
        self._log_order(rec)
        return rec

    def _open(self, req, resolved, stop, review, f, liq, now) -> dict:
        qty = int(resolved["quantity"])
        entry_ch = review["charges_entry"]
        pos = {"id": self._id("P"), "symbol": req.symbol, "instrument": req.instrument, "expiry": req.expiry,
               "strike": req.strike, "tradingsymbol": resolved["tradingsymbol"], "lot_size": int(resolved["lot_size"]),
               "side": req.side, "lots": req.lots, "qty": qty,
               "entry": {"price": f["price"], "levels": f["levels"], "class": liq.get("class"), "mode": f["mode"],
                         "bucket": liq.get("bucket", BUCKET_NORMAL), "mid": f["mid"], "slippage_vs_mid": f["slippage_vs_mid"],
                         "overflow_qty": f["overflow_qty"]},
               "bucket": liq.get("bucket", BUCKET_NORMAL), "entry_charges": entry_ch, "entry_charges_open": entry_ch["total"],
               "stop": stop, "max_loss_at_entry": review["max_loss"], "margin": review["margin"] or 0.0,
               "opened_at": now.isoformat(timespec="seconds"), "t2_date": review["t2_date"], "stop_triggered_at": None,
               "mark": None}
        value = f["price"] * qty
        if is_option(req.instrument):
            self.state["cash"] += (-value if req.side == "BUY" else value) - entry_ch["total"]
        else:
            self.state["cash"] -= entry_ch["total"]
        self._revalue(pos)
        self.state["positions"].append(pos)
        return pos

    def _close(self, pos: dict, qty: int, f: dict, liq_class: str | None, now: datetime, reason: str) -> dict:
        frac = qty / pos["qty"]
        exit_side = "SELL" if pos["side"] == "BUY" else "BUY"
        sign = 1 if pos["side"] == "BUY" else -1
        exit_ch = ch.leg(pos["instrument"], exit_side, qty, f["price"])
        entry_part = round(pos["entry_charges_open"] * frac, 2)
        gross = round(sign * (f["price"] - pos["entry"]["price"]) * qty, 2)
        net = round(gross - entry_part - exit_ch["total"], 2)
        if is_option(pos["instrument"]):
            value = f["price"] * qty
            self.state["cash"] += (value if pos["side"] == "BUY" else -value) - exit_ch["total"]
        else:
            self.state["cash"] += gross - exit_ch["total"]
        committed = pos["entry"]["price"] * qty if is_option(pos["instrument"]) and pos["side"] == "BUY" else pos["margin"] * frac
        ml = pos.get("max_loss_at_entry")
        closed = {k: pos[k] for k in ("id", "symbol", "instrument", "expiry", "strike", "tradingsymbol", "lot_size", "side",
                                      "bucket", "stop", "opened_at", "t2_date")}
        lots = qty // pos["lot_size"] if pos["lot_size"] else pos["lots"]
        closed.update({"lots": lots, "qty": qty, "entry": pos["entry"], "entry_charges": entry_part,
                       "exit": {"price": f["price"], "levels": f["levels"], "class": liq_class, "mode": f["mode"],
                                "mid": f["mid"], "slippage_vs_mid": f["slippage_vs_mid"], "overflow_qty": f["overflow_qty"]},
                       "exit_charges": exit_ch, "gross_pnl": gross, "charges_total": round(entry_part + exit_ch["total"], 2),
                       "net_pnl": net, "reason": reason, "closed_at": now.isoformat(timespec="seconds"),
                       "capital_committed": round(committed, 2),
                       "return_pct": round(net / committed * 100, 2) if committed else None,
                       "max_loss_at_entry": round(ml * frac, 2) if ml else None,
                       "r_multiple": round(net / (ml * frac), 3) if ml else None})
        self.state["closed"].append(closed)
        day = self._ensure_day(now)
        day["realised"] = round(day.get("realised", 0.0) + net, 2)
        if qty >= pos["qty"]:
            self.state["positions"] = [p for p in self.state["positions"] if p["id"] != pos["id"]]
        else:
            pos["qty"] -= qty
            pos["lots"] -= lots
            pos["entry_charges_open"] = round(pos["entry_charges_open"] - entry_part, 2)
            pos["margin"] = round(pos["margin"] * (1 - frac), 2)
            if pos.get("max_loss_at_entry"):
                pos["max_loss_at_entry"] = round(pos["max_loss_at_entry"] * (1 - frac), 2)
            self._revalue(pos)
        return closed

    # ------------------------------------------------------------ live polls
    def on_poll(self, feed=None, now: datetime | None = None) -> None:
        """Called after every live poll: run due queued orders, execute triggered stops and forced T-2
        exits against this poll's depth, mark everything else and look for new stop triggers."""
        now = (now or datetime.now(IST)).astimezone(IST)
        with self.lock:
            if not self.is_open(now):
                return
            self._ensure_day(now)
            self.process_queue(now)
            for pos in list(self.state["positions"]):
                if now.date() > sessions._d(pos["expiry"]):          # the server missed T-2 and expiry entirely
                    self._close_at_mark(pos, now, "expired_no_quote")
                    continue
                c = {k: pos[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol", "lot_size")}
                quote = self.quotes.get(c, fresh=False)
                reason = "stop" if pos.get("stop_triggered_at") else "forced_t2" if self._forced_due(pos, now) else None
                if reason and quote and self._auto_exit(pos, quote, now, reason):
                    continue
                if quote:
                    self._mark(pos, quote, now)
                    self._check_stop(pos, now)
            self._touch_day(now)
            self._save()

    def process_queue(self, now: datetime) -> list[dict]:
        done, out = set(), []
        for o in self.queue.pending():
            if now < datetime.fromisoformat(o["fill_after"]):
                continue
            from server.broker import OrderRequest
            req = OrderRequest(**o["request"])
            base = {k: v for k, v in o.items() if k not in ("request", "resolved", "status", "fill_after")}
            try:
                review = self.evaluate(req, o["resolved"], o.get("stop"), now, stage="queue")
                if review["intent"] != o.get("intent"):
                    review["blocked"].append(f"it was queued as an {o.get('intent')}, but the position it refers to has changed "
                                             "(opened or closed) while it waited")
                if review["blocked"]:
                    rec = {**base, "status": "CANCELLED", "reason": "at the queued fill: " + "; ".join(review["blocked"]),
                           "filled_at": now.isoformat(timespec="seconds")}
                    self._log_order(rec)
                elif review["queued"]:
                    continue
                else:
                    rec = self._execute(req, o["resolved"], o.get("stop"), review, now,
                                        {**base, "filled_at": now.isoformat(timespec="seconds")})
            except Exception as exc:  # noqa: BLE001
                rec = {**base, "status": "CANCELLED", "reason": f"{type(exc).__name__}: {exc}"}
                self._log_order(rec)
            done.add(o["order_id"])
            out.append(rec)
        if done:
            self.queue.remove(done)
        return out

    def _forced_due(self, pos: dict, now: datetime) -> bool:
        t2 = date.fromisoformat(pos["t2_date"])
        opened = datetime.fromisoformat(pos["opened_at"]).astimezone(IST).date()
        return now.date() >= t2 and now.time() >= sessions.fill_at() and opened < now.date()

    def _auto_exit(self, pos: dict, quote: dict, now: datetime, reason: str) -> bool:
        exit_side = "SELL" if pos["side"] == "BUY" else "BUY"
        c = {**{k: pos[k] for k in ("symbol", "instrument", "expiry", "strike", "tradingsymbol", "lot_size")}, "side": exit_side}
        liq = classify(c, quote, pos["lots"], sessions.sessions_to_expiry(now, pos["expiry"]), rules=self.rules)
        mode = MODE_FOR_CLASS.get(liq["class"], "penalty")
        try:
            f = fill(exit_side, pos["qty"], quote.get("depth"), self.tick, mode)
        except NoLiquidity as exc:
            log.warning("%s exit of %s waits for the next poll: %s", reason, pos["tradingsymbol"], exc)
            return False
        closed = self._close(pos, pos["qty"], f, liq["class"], now, reason)
        self._log_order({"order_id": self._id("PAPER"), "placed_at": now.isoformat(timespec="seconds"), "paper": True,
                         "symbol": pos["symbol"], "instrument": pos["instrument"], "expiry": pos["expiry"], "strike": pos["strike"],
                         "side": exit_side, "lots": closed["lots"], "order_type": "MARKET", "price": None,
                         "tradingsymbol": pos["tradingsymbol"], "quantity": closed["qty"], "lot_size": pos["lot_size"],
                         "intent": "exit", "status": "FILLED", "auto": reason, "fill_price": f["price"], "fill": f,
                         "liquidity_class": liq["class"], "bucket": pos["bucket"], "position_id": pos["id"],
                         "net_pnl": closed["net_pnl"], "charges": closed["exit_charges"]})
        return True

    def _close_at_mark(self, pos: dict, now: datetime, reason: str) -> None:
        px = (pos.get("mark") or {}).get("price")
        px = pos["entry"]["price"] if px is None else px
        f = {"price": px, "levels": [], "mode": "mark", "mid": None, "slippage_vs_mid": None, "overflow_qty": 0}
        self._close(pos, pos["qty"], f, None, now, reason)

    def _mark(self, pos: dict, quote: dict, now: datetime) -> None:
        d = quote.get("depth") or {}
        bid = d["bid"][0][0] if d.get("bid") else None
        ask = d["ask"][0][0] if d.get("ask") else None
        prev = (pos.get("mark") or {}).get("price")
        side_px = bid if pos["side"] == "BUY" else ask
        stale = side_px is None
        if side_px is None:
            side_px = 0.0 if is_option(pos["instrument"]) and pos["side"] == "BUY" else prev
        pos["mark"] = {"price": side_px, "bid": bid, "ask": ask, "ltp": quote.get("last_price"),
                       "at": now.isoformat(timespec="seconds"), "stale": stale}
        self._revalue(pos)

    def _check_stop(self, pos: dict, now: datetime) -> None:
        stop, m = pos.get("stop"), pos.get("mark") or {}
        if not stop or pos.get("stop_triggered_at"):
            return
        hit = (pos["side"] == "BUY" and m.get("bid") is not None and m["bid"] <= stop) or \
              (pos["side"] == "SELL" and m.get("ask") is not None and m["ask"] >= stop)
        if hit:
            pos["stop_triggered_at"] = now.isoformat(timespec="seconds")
            log.info("paper stop triggered on %s at %s (stop %s); exits at the next poll's book", pos["tradingsymbol"],
                     m.get("bid") if pos["side"] == "BUY" else m.get("ask"), stop)

    def _revalue(self, pos: dict) -> None:
        px = (pos.get("mark") or {}).get("price")
        px = pos["entry"]["price"] if px is None else px
        exit_side = "SELL" if pos["side"] == "BUY" else "BUY"
        sign = 1 if pos["side"] == "BUY" else -1
        exit_ch = ch.leg(pos["instrument"], exit_side, pos["qty"], px)["total"]
        gross = sign * (px - pos["entry"]["price"]) * pos["qty"]
        pos["unrealised_gross"] = round(gross, 2)
        pos["exit_charges_est"] = exit_ch
        pos["unrealised"] = round(gross - pos["entry_charges_open"] - exit_ch, 2)
        if is_option(pos["instrument"]):
            pos["liquidation_value"] = round(sign * px * pos["qty"] - exit_ch, 2)
        else:
            pos["liquidation_value"] = round(gross - exit_ch, 2)

    # ------------------------------------------------------------ equity and the day
    def equity(self) -> float:
        return round(self.state["cash"] + sum(p.get("liquidation_value", 0.0) for p in self.state["positions"]), 2)

    def _ensure_day(self, now: datetime) -> dict:
        d = now.astimezone(IST).date().isoformat()
        daily = self.state["daily"]
        if d not in daily:
            prev = daily[max(daily)]["end_equity"] if daily else self.state["capital"]
            daily[d] = {"start_equity": prev, "end_equity": prev, "realised": 0.0}
        return daily[d]

    def _touch_day(self, now: datetime) -> None:
        day = self._ensure_day(now)
        eq = self.equity()
        day["end_equity"] = eq
        self.state["peak_equity"] = round(max(self.state.get("peak_equity", self.state["capital"]), eq), 2)

    def day_pnl(self, now: datetime | None = None) -> float:
        now = (now or datetime.now(IST)).astimezone(IST)
        d = now.date().isoformat()
        daily = self.state["daily"]
        start = daily[d]["start_equity"] if d in daily else (daily[max(daily)]["end_equity"] if daily else self.state["capital"])
        return round(self.equity() - start, 2)

    def week_pnl(self, now: datetime | None = None) -> float:
        now = (now or datetime.now(IST)).astimezone(IST)
        monday = (now.date() - timedelta(days=now.weekday())).isoformat()
        daily = self.state["daily"]
        this_week = sorted(d for d in daily if d >= monday)
        if this_week:
            start = daily[this_week[0]]["start_equity"]
        else:
            start = daily[max(daily)]["end_equity"] if daily else self.state["capital"]
        return round(self.equity() - start, 2)

    def new_positions(self, since: date) -> int:
        """Positions opened on or after `since`, open or closed (a partly closed position counts once)."""
        seen: dict[str, str] = {}
        for p in self.state["positions"] + self.state["closed"]:
            seen.setdefault(p["id"], p["opened_at"])
        return sum(1 for o in seen.values() if datetime.fromisoformat(o).astimezone(IST).date() >= since)

    def open_margin(self) -> float:
        return round(sum(p.get("margin") or 0.0 for p in self.state["positions"]), 2)

    # ------------------------------------------------------------ views
    def summary(self, now: datetime | None = None) -> dict:
        now = (now or datetime.now(IST)).astimezone(IST)
        with self.lock:
            eq, peak = self.equity(), max(self.state.get("peak_equity", self.state["capital"]), self.equity())
            out = {"capital": self.state["capital"], "cash": round(self.state["cash"], 2), "equity": eq,
                   "realised_total": round(sum(c["net_pnl"] for c in self.state["closed"]), 2),
                   "unrealised_total": round(sum(p.get("unrealised", 0.0) for p in self.state["positions"]), 2),
                   "day_pnl": self.day_pnl(now), "week_pnl": self.week_pnl(now), "peak_equity": round(peak, 2),
                   "drawdown_pct": round((peak - eq) / peak * 100, 2) if peak else 0.0,
                   "open_margin": self.open_margin(), "open_positions": len(self.state["positions"]),
                   "closed_trades": len(self.state["closed"]), "queued_orders": len(self.queue.pending()),
                   "market_open": self.is_open(now), "as_of": now.isoformat(timespec="seconds")}
            if self.risk is not None:
                out.update(self.risk.state(self, now))
            return out

    def positions_view(self) -> list[dict]:
        with self.lock:
            return [dict(p) for p in self.state["positions"]]

    def trades_view(self) -> list[dict]:
        with self.lock:
            return [dict(c) for c in self.state["closed"]][::-1]

    def _position_for(self, tradingsymbol: str) -> dict | None:
        return next((p for p in self.state["positions"] if p["tradingsymbol"] == tradingsymbol), None)

    def _position_by_id(self, pid: str) -> dict:
        p = next((p for p in self.state["positions"] if p["id"] == pid), None)
        if p is None:
            raise PaperRejected("that position is no longer open")
        return p


def _req_dict(req) -> dict:
    return {"symbol": req.symbol, "instrument": req.instrument, "expiry": req.expiry, "strike": req.strike,
            "side": req.side, "lots": req.lots, "order_type": req.order_type, "price": req.price}
