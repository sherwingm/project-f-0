"""Broker layer: one interface, a paper implementation (default) and Kite Connect (Zerodha).

Contracts are always NFO stock futures/options from the scan universe, product NRML, validity DAY.
Every order goes through preview() then place(): the page shows the preview (exact contract,
quantity = lots × lot size, paper/live) and the person confirms before place() is called.

Kite naming convention for NFO tradingsymbols:
    futures            {NAME}{YY}{MON}FUT                RELIANCE26SEPFUT
    monthly options    {NAME}{YY}{MON}{STRIKE}{CE|PE}    RELIANCE26SEP1300CE
The authoritative source is Kite's instrument dump, which KiteBroker loads; PaperBroker derives
the name from the convention so it works with no account at all.

Regulatory note: SEBI's algo framework requires API order placement to come from a static IP
whitelisted with the broker; run the order-enabled server from such a machine, not a free cloud host.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


@dataclass
class OrderRequest:
    symbol: str                # underlying, e.g. RELIANCE
    instrument: str            # FUT | CE | PE
    expiry: str                # YYYY-MM-DD
    strike: float | None
    side: str                  # BUY | SELL
    lots: int
    order_type: str            # MARKET | LIMIT
    price: float | None        # required for LIMIT

    def validate(self, lot_size: int | None, max_lots: int) -> None:
        if self.instrument not in ("FUT", "CE", "PE"):
            raise ValueError("instrument must be FUT, CE or PE")
        if self.instrument != "FUT" and not self.strike:
            raise ValueError("options need a strike")
        if self.side not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")
        if self.order_type not in ("MARKET", "LIMIT"):
            raise ValueError("order_type must be MARKET or LIMIT")
        if self.order_type == "LIMIT" and not (self.price and self.price > 0):
            raise ValueError("LIMIT orders need a positive price")
        if not (1 <= self.lots <= max_lots):
            raise ValueError(f"lots must be between 1 and {max_lots}")
        if not lot_size:
            raise ValueError(f"lot size unknown for {self.symbol}; rebuild the scan from a network NSE accepts")
        datetime.strptime(self.expiry, "%Y-%m-%d")


def tradingsymbol(symbol: str, instrument: str, expiry: str, strike: float | None) -> str:
    d = datetime.strptime(expiry, "%Y-%m-%d")
    base = f"{symbol}{d.strftime('%y')}{MONTHS[d.month - 1]}"
    if instrument == "FUT":
        return base + "FUT"
    s = int(strike) if float(strike).is_integer() else strike
    return f"{base}{s}{instrument}"


# ---------------------------------------------------------------- preview tokens
_SECRET = os.getenv("ORDER_TOKEN_SECRET") or hashlib.sha256(os.urandom(32)).hexdigest()
TOKEN_TTL = 90  # seconds between preview and place


def preview_token(payload: dict) -> str:
    ts = int(time.time())
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    sig = hmac.new(_SECRET.encode(), f"{ts}.{body}".encode(), "sha256").hexdigest()[:24]
    return f"{ts}.{sig}"


def check_token(token: str, payload: dict) -> None:
    try:
        ts_s, sig = token.split(".")
        ts = int(ts_s)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid confirmation token") from exc
    if time.time() - ts > TOKEN_TTL:
        raise ValueError("confirmation expired; preview the order again")
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    good = hmac.new(_SECRET.encode(), f"{ts}.{body}".encode(), "sha256").hexdigest()[:24]
    if not hmac.compare_digest(sig, good):
        raise ValueError("order changed since preview; preview it again")


# ---------------------------------------------------------------- brokers
class Broker:
    name = "none"
    paper = True

    def resolve(self, req: OrderRequest, lot_size: int) -> dict:
        """Return {'tradingsymbol','quantity','lot_size','exchange'} for the request."""
        return {"tradingsymbol": tradingsymbol(req.symbol, req.instrument, req.expiry, req.strike),
                "quantity": req.lots * lot_size, "lot_size": lot_size, "exchange": "NFO"}

    def margin(self, req: OrderRequest, resolved: dict, ref_price: float | None) -> float | None:
        return None

    def place(self, req: OrderRequest, resolved: dict, ref_price: float | None) -> dict:
        raise NotImplementedError

    def orders(self) -> list[dict]:
        raise NotImplementedError

    def positions(self) -> list[dict]:
        raise NotImplementedError


class PaperBroker(Broker):
    """Paper orders go through the paper ledger (server/paper.py): filled against the live book with
    the liquidity class and fill engine, charged, marked every poll and exited by hand, by stop or at
    T-2. Order events are logged to data/paper_orders.jsonl. Nothing here can reach a broker."""
    name = "paper"
    paper = True

    def __init__(self, data_dir: Path, ledger=None):
        self.path = data_dir / "paper_orders.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger = ledger

    def place(self, req: OrderRequest, resolved: dict, ref_price: float | None, stop: float | None = None) -> dict:
        if self.ledger is None:
            raise RuntimeError("the paper ledger is not running")
        return self.ledger.submit(req, resolved, stop)

    def orders(self) -> list[dict]:
        if not self.path.exists():
            return []
        latest: dict[str, dict] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                latest[o.get("order_id")] = o            # the latest event per order wins (queued -> filled)
        return sorted(latest.values(), key=lambda o: o.get("filled_at") or o.get("placed_at") or "", reverse=True)

    def positions(self) -> list[dict]:
        if self.ledger is None:
            return []
        return [{"tradingsymbol": p["tradingsymbol"], "symbol": p["symbol"],
                 "quantity": p["qty"] if p["side"] == "BUY" else -p["qty"], "avg_price": p["entry"]["price"],
                 "pnl": p.get("unrealised"), "last_price": (p.get("mark") or {}).get("price")}
                for p in self.ledger.positions_view()]


class KiteBroker(Broker):
    """Kite Connect. Needs KITE_API_KEY and a KITE_ACCESS_TOKEN generated for the day
    (python -m server.kite_login prints the login URL and exchanges the request_token)."""
    name = "kite"
    paper = False

    def __init__(self, api_key: str, access_token: str):
        from kiteconnect import KiteConnect  # imported lazily so paper mode needs no SDK
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
        self._instruments: dict[tuple, dict] | None = None

    def instruments(self) -> dict[tuple, dict]:
        if self._instruments is None:
            m = {}
            for i in self.kite.instruments("NFO"):
                exp = i["expiry"].strftime("%Y-%m-%d") if isinstance(i["expiry"], (date, datetime)) else str(i["expiry"])
                typ = "FUT" if i["instrument_type"] == "FUT" else i["instrument_type"]
                m[(i["name"], typ, exp, float(i["strike"]) if typ != "FUT" else None)] = i
            self._instruments = m
        return self._instruments

    def resolve(self, req: OrderRequest, lot_size: int) -> dict:
        i = self.instruments().get((req.symbol, req.instrument, req.expiry, req.strike if req.instrument != "FUT" else None))
        if not i:
            raise ValueError(f"no NFO contract for {req.symbol} {req.instrument} {req.expiry} {req.strike or ''}")
        return {"tradingsymbol": i["tradingsymbol"], "quantity": req.lots * int(i["lot_size"]),
                "lot_size": int(i["lot_size"]), "exchange": "NFO", "instrument_token": i["instrument_token"]}

    def margin(self, req: OrderRequest, resolved: dict, ref_price: float | None) -> float | None:
        try:
            r = self.kite.order_margins([{
                "exchange": "NFO", "tradingsymbol": resolved["tradingsymbol"], "transaction_type": req.side,
                "variety": "regular", "product": "NRML", "order_type": req.order_type,
                "quantity": resolved["quantity"], "price": req.price or 0, "trigger_price": 0}])
            return float(r[0]["total"]) if r else None
        except Exception as exc:  # noqa: BLE001
            log.warning("margin check failed: %s", exc)
            return None

    def place(self, req: OrderRequest, resolved: dict, ref_price: float | None) -> dict:
        k = self.kite
        order_id = k.place_order(variety=k.VARIETY_REGULAR, exchange=k.EXCHANGE_NFO, tradingsymbol=resolved["tradingsymbol"],
                                 transaction_type=req.side, quantity=resolved["quantity"], product=k.PRODUCT_NRML,
                                 order_type=req.order_type, price=req.price if req.order_type == "LIMIT" else None,
                                 validity=k.VALIDITY_DAY)
        return {"order_id": order_id, "placed_at": datetime.now(IST).isoformat(timespec="seconds"), "status": "SENT",
                "paper": False, **asdict(req), **resolved}

    def orders(self) -> list[dict]:
        return [{"order_id": o["order_id"], "placed_at": str(o.get("order_timestamp")), "status": o["status"], "paper": False,
                 "tradingsymbol": o["tradingsymbol"], "side": o["transaction_type"], "quantity": o["quantity"],
                 "order_type": o["order_type"], "price": o["price"], "fill_price": o.get("average_price"),
                 "status_message": o.get("status_message")} for o in self.kite.orders()][::-1]

    def positions(self) -> list[dict]:
        return [{"tradingsymbol": p["tradingsymbol"], "quantity": p["quantity"], "avg_price": p["average_price"],
                 "pnl": p.get("pnl"), "last_price": p.get("last_price")} for p in self.kite.positions()["net"] if p["quantity"]]


def make_broker(settings) -> Broker | None:
    if settings.paper or settings.broker not in ("kite", "groww", "kotak"):
        return PaperBroker(settings.data_dir)
    if settings.kite_ready:
        return KiteBroker(settings.kite_api_key, settings.kite_access_token)
    if settings.groww_ready:
        from server.groww import GrowwBroker, shared_session
        return GrowwBroker(shared_session(settings))
    if settings.kotak_ready:
        from server.kotak import KotakBroker, shared_session
        return KotakBroker(shared_session(settings))
    return None
