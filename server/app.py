"""The scanner as a small web service.

    uvicorn server.app:app --host 0.0.0.0 --port 8000

Routes (all behind HTTP Basic auth, user "user", password APP_PASSWORD):
    GET  /                         the page, with the latest scan and server capabilities embedded
    GET  /api/scan                 scan.json
    GET  /api/live                 latest intraday quotes (empty when the feed is off or market closed)
    GET  /api/chain/{symbol}       nearest-expiry strikes; live premiums/OI when the feed is on
    GET  /api/commentary/{symbol}  plain-language reading (needs ANTHROPIC_API_KEY)
    GET  /api/verdict/{symbol}     evidence verdict: numbers + web-searched news (needs ANTHROPIC_API_KEY); ?refresh=1 bypasses the day's cache
    POST /api/order/preview        resolve the contract, quantity, margin -> confirmation token
    POST /api/order                place it (paper by default); needs the token from preview
    GET  /api/orders, /api/positions
    POST /api/rebuild              re-run the EOD build (also runs itself daily at 20:30 IST)
"""
from __future__ import annotations

import json
import logging
import secrets
import threading
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from scanner.build import ROOT, build
from server.broker import OrderRequest, check_token, make_broker, preview_token, tradingsymbol
from server.commentary import Commentary
from server.verdict import Verdict
from server.config import settings
from server.live import FakeProvider, KiteProvider, LiveFeed, market_open

log = logging.getLogger("server")
IST = timezone(timedelta(hours=5, minutes=30))
app = FastAPI(title="F&O scanner", docs_url=None, redoc_url=None)
security = HTTPBasic()


def auth(c: HTTPBasicCredentials = Depends(security)) -> str:
    if not settings.app_password:
        raise HTTPException(503, "APP_PASSWORD is not set on the server")
    if not (secrets.compare_digest(c.username, "user") and secrets.compare_digest(c.password, settings.app_password)):
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Basic"})
    return c.username


# ---------------------------------------------------------------- state
class State:
    def __init__(self):
        self.scan: dict = {}
        self.stocks: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.feed: LiveFeed | None = None
        self.broker = make_broker(settings)
        self.commentary = Commentary(settings.anthropic_api_key, settings.commentary_model, settings.data_dir / "cache") if settings.commentary_enabled else None
        self.verdict = Verdict(settings.anthropic_api_key, settings.commentary_model, settings.data_dir / "cache") if settings.commentary_enabled else None
        self.orders_today = Counter()

    def load_scan(self, path: Path) -> None:
        scan = json.loads(path.read_text())
        with self.lock:
            self.scan = scan
            self.stocks = {s["symbol"]: s for s in scan["stocks"]}
        if self.feed:
            self.feed.reload(scan, self.fut_symbols())

    def fut_symbols(self) -> dict[str, str]:
        """Nearest-expiry futures tradingsymbol per stock (Kite naming; the option chain expiry is
        the same monthly cycle as the near futures contract)."""
        out = {}
        for sym, s in self.stocks.items():
            exp = (s.get("chain") or {}).get("expiry")
            if exp:
                out[sym] = tradingsymbol(sym, "FUT", exp, None)
        return out


state = State()
SCAN_PATH = ROOT / "data" / "scan.json"


@app.on_event("startup")
def startup() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if SCAN_PATH.exists():
        state.load_scan(SCAN_PATH)
    else:
        log.warning("no data/scan.json yet; run `python -m scanner.build` or POST /api/rebuild")
    src = settings.live_source
    if src == "upstox":
        from server.upstox import UpstoxProvider
        provider = UpstoxProvider(settings.upstox_analytics_token, settings.upstox_chain_calls_per_poll)
        state.feed = LiveFeed(provider, state.scan or {"stocks": []}, settings.poll_seconds, state.fut_symbols())
        state.feed.start()
        log.info("live feed on (Upstox, read-only): LTP + futures OI every %ss, PCR/strike OI for %d stocks per poll",
                 settings.poll_seconds, settings.upstox_chain_calls_per_poll)
    elif src == "kotak":
        from server.kotak import KotakProvider, shared_session
        provider = KotakProvider(shared_session(settings), settings.kotak_chain_calls_per_poll)
        state.feed = LiveFeed(provider, state.scan or {"stocks": []}, settings.poll_seconds, state.fut_symbols())
        state.feed.start()
        log.info("live feed on (Kotak Neo, consumer key only): LTP + futures OI every %ss, PCR/strike OI for %d stocks per poll",
                 settings.poll_seconds, settings.kotak_chain_calls_per_poll)
    elif src == "kite":
        provider = KiteProvider(settings.kite_api_key, settings.kite_access_token)
        state.feed = LiveFeed(provider, state.scan or {"stocks": []}, settings.poll_seconds, state.fut_symbols())
        state.feed.start()
        log.info("live feed on (Kite), polling every %ss during market hours", settings.poll_seconds)
    elif src == "groww":
        from server.groww import GrowwProvider, shared_session
        provider = GrowwProvider(shared_session(settings), settings.groww_oi_calls_per_poll)
        state.feed = LiveFeed(provider, state.scan or {"stocks": []}, settings.poll_seconds, state.fut_symbols())
        state.feed.start()
        log.info("live feed on (Groww): LTP every %ss, futures OI refreshed %d contracts per poll",
                 settings.poll_seconds, settings.groww_oi_calls_per_poll)
    elif src == "fake":  # local demo without a broker: random-walk quotes
        closes = {s: v["close"] for s, v in state.stocks.items()}
        fo = {s: v.get("fut_oi") for s, v in state.stocks.items()}
        lots = {s: v.get("lot_size") for s, v in state.stocks.items()}
        state.feed = LiveFeed(FakeProvider(closes, fo, lots), state.scan, settings.poll_seconds, state.fut_symbols(), poll_always=True)
        state.feed.start()
    if not settings.orders_enabled:
        state.broker = None
    threading.Thread(target=_daily_rebuild_loop, daemon=True).start()


def _daily_rebuild_loop() -> None:
    while True:
        now = datetime.now(IST)
        target = now.replace(hour=20, minute=30, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        time.sleep((target - now).total_seconds())
        if target.weekday() < 5:
            try:
                _rebuild()
            except Exception as exc:  # noqa: BLE001
                log.error("scheduled rebuild failed: %s", exc)


def _rebuild() -> dict:
    scan = build(ROOT / "data" / "eod2", settings.data_dir / "cache")
    SCAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCAN_PATH.write_text(json.dumps(scan))
    state.load_scan(SCAN_PATH)
    return scan["meta"]


# ---------------------------------------------------------------- page & data
@app.get("/", response_class=HTMLResponse)
def index(_: str = Depends(auth)):
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    scan = state.scan or {"meta": {"as_of": "—", "as_of_label": "no scan yet", "generated_at_ist": "", "universe_size": 0,
                                   "fo_available": False, "fo_status": "no scan built yet", "disclaimer": ""},
                          "summary": {"bullish": 0, "bearish": 0, "neutral": 0, "unclassified": 0}, "stocks": []}
    payload = json.dumps(scan, separators=(",", ":")).replace("</", "<\\/")
    server = json.dumps(settings.public())
    return html.replace("/*__SCAN_DATA__*/", payload).replace("/*__SERVER__*/{}", server)


@app.get("/api/scan")
def api_scan(_: str = Depends(auth)):
    return state.scan


@app.get("/api/live")
def api_live(_: str = Depends(auth)):
    if not state.feed:
        return {"enabled": False, "market_open": market_open(), "quotes": {}}
    return {"enabled": True, **state.feed.snapshot()}


@app.get("/api/chain/{symbol}")
def api_chain(symbol: str, _: str = Depends(auth)):
    s = state.stocks.get(symbol.upper())
    if not s or not s.get("chain"):
        raise HTTPException(404, "no option chain for this symbol in the current scan")
    chain = json.loads(json.dumps(s["chain"]))
    if state.feed and (state.feed.poll_always or market_open()):
        keys = []
        for row in chain["strikes"]:
            for t in ("CE", "PE"):
                keys.append("NFO:" + tradingsymbol(symbol.upper(), t, chain["expiry"], row["strike"]))
        try:
            q = state.feed.provider.quote(keys)
            for row in chain["strikes"]:
                for t in ("CE", "PE"):
                    k = "NFO:" + tradingsymbol(symbol.upper(), t, chain["expiry"], row["strike"])
                    if k in q:
                        row[f"{t.lower()}_live_ltp"] = q[k].get("last_price")
                        row[f"{t.lower()}_live_oi"] = q[k].get("open_interest")
            chain["live_at"] = datetime.now(IST).strftime("%H:%M:%S")
        except Exception as exc:  # noqa: BLE001
            chain["live_error"] = str(exc)
    return chain


@app.get("/api/commentary/{symbol}")
def api_commentary(symbol: str, _: str = Depends(auth)):
    if not state.commentary:
        raise HTTPException(404, "commentary is off (set ANTHROPIC_API_KEY)")
    s = state.stocks.get(symbol.upper())
    if not s:
        raise HTTPException(404, "unknown symbol")
    return state.commentary.get(s, state.scan["meta"]["as_of"], state.scan["meta"].get("thresholds", {}))


@app.get("/api/verdict/{symbol}")
def api_verdict(symbol: str, refresh: int = 0, _: str = Depends(auth)):
    if not state.verdict:
        raise HTTPException(404, "verdict is off (set ANTHROPIC_API_KEY)")
    s = state.stocks.get(symbol.upper())
    if not s:
        raise HTTPException(404, f"{symbol} is not in the scan")
    live = state.feed.snapshot()["quotes"].get(s["symbol"]) if state.feed else None
    return state.verdict.get(s, state.scan["meta"]["as_of"], state.scan["meta"].get("thresholds", {}), live, refresh=bool(refresh))


# ---------------------------------------------------------------- orders
class OrderBody(BaseModel):
    symbol: str
    instrument: str
    expiry: str
    strike: float | None = None
    side: str
    lots: int
    order_type: str = "LIMIT"
    price: float | None = None
    token: str | None = None


def _ref_price(sym: str, instrument: str, strike: float | None) -> float | None:
    s = state.stocks.get(sym)
    if not s:
        return None
    live = state.feed.snapshot()["quotes"].get(sym) if state.feed else None
    if instrument == "FUT":
        return (live or {}).get("fut_ltp") or (live or {}).get("ltp") or s["close"]
    for row in (s.get("chain") or {}).get("strikes", []):
        if row["strike"] == strike:
            return row["ce_close"] if instrument == "CE" else row["pe_close"]
    return None


def _prepare(body: OrderBody) -> tuple[OrderRequest, dict, float | None]:
    if not state.broker:
        raise HTTPException(503, "orders are off: no broker configured and PAPER=false")
    sym = body.symbol.upper()
    s = state.stocks.get(sym)
    if not s:
        raise HTTPException(400, f"{sym} is not in the current F&O scan")
    req = OrderRequest(sym, body.instrument.upper(), body.expiry, body.strike, body.side.upper(), body.lots, body.order_type.upper(), body.price)
    try:
        req.validate(s.get("lot_size"), settings.max_lots_per_order)
        resolved = state.broker.resolve(req, s["lot_size"])
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return req, resolved, _ref_price(sym, req.instrument, req.strike)


@app.post("/api/order/preview")
def api_order_preview(body: OrderBody, _: str = Depends(auth)):
    req, resolved, ref = _prepare(body)
    payload = body.model_dump(exclude={"token"})
    margin = state.broker.margin(req, resolved, ref)
    notional = (req.price or ref or 0) * resolved["quantity"]
    return {**resolved, "paper": state.broker.paper, "reference_price": ref, "notional": round(notional, 2),
            "estimated_margin": margin, "orders_today": sum(state.orders_today.values()),
            "max_orders_per_day": settings.max_orders_per_day, "token": preview_token(payload)}


@app.post("/api/order")
def api_order(body: OrderBody, _: str = Depends(auth)):
    if not body.token:
        raise HTTPException(400, "preview the order first")
    try:
        check_token(body.token, body.model_dump(exclude={"token"}))
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    today = datetime.now(IST).strftime("%Y-%m-%d")
    if state.orders_today[today] >= settings.max_orders_per_day:
        raise HTTPException(429, f"daily cap of {settings.max_orders_per_day} orders reached")
    req, resolved, ref = _prepare(body)
    try:
        rec = state.broker.place(req, resolved, ref)
    except Exception as exc:  # noqa: BLE001 - broker rejections come back as a readable error
        raise HTTPException(502, f"broker rejected the order: {exc}")
    state.orders_today[today] += 1
    log.info("order %s: %s", rec["order_id"], {k: rec[k] for k in ("tradingsymbol", "side", "quantity", "order_type", "price", "paper")})
    return rec


@app.get("/api/orders")
def api_orders(_: str = Depends(auth)):
    return state.broker.orders() if state.broker else []


@app.get("/api/positions")
def api_positions(_: str = Depends(auth)):
    return state.broker.positions() if state.broker else []


@app.post("/api/rebuild")
def api_rebuild(_: str = Depends(auth)):
    try:
        return _rebuild()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"rebuild failed: {exc}")


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=exc.headers)
