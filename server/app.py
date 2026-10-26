"""The scanner as a small web service.

    uvicorn server.app:app --host 0.0.0.0 --port 8000

Login: GET/POST /login (a page; sets a cookie for a year), GET /logout. Every other route needs that cookie or
HTTP Basic auth (user "user", password APP_PASSWORD):
    GET  /                         the page, with the latest scan and server capabilities embedded
    GET  /api/scan                 scan.json
    GET  /api/live                 latest intraday quotes (empty when the feed is off or market closed)
    GET  /api/chain/{symbol}       nearest-expiry strikes; live premium / % change / volume / OI / ATP / bid-ask when the
                                   feed is on (and ATM +/- 5 strikes are then polled for 30 min for their charts)
    GET  /api/intraday/{symbol}    chart candles from the feed's ticks: ?tf=1|5|15 &leg=stock|fut|CE:<strike>|PE:<strike>
    GET  /api/news/{symbol}        recent news headlines (Google News RSS, cached 15 min)
    GET  /api/commentary/{symbol}  plain-language reading (needs ANTHROPIC_API_KEY)
    GET  /api/verdict/{symbol}     evidence verdict: numbers + web-searched news (needs ANTHROPIC_API_KEY); ?refresh=1 bypasses the day's cache
    POST /api/order/preview        resolve the contract, quantity, margin -> confirmation token
    POST /api/order                place it (paper by default); needs the token from preview
    GET  /api/orders, /api/positions
    GET  /api/paper/summary        paper account: capital, equity, day/week P&L, drawdown, open margin, kill switch
    GET  /api/paper/positions      open paper positions with marks, stops, expiry and T-2 date
    GET  /api/paper/trades         closed paper trades, net of fills and charges
    GET  /api/paper/refusals       orders refused for liquidity, newest first, with the quote they were judged on
    POST /api/rebuild              re-run the EOD build (also runs itself daily at 20:30 IST); with SCAN_URL set,
                                   re-read the scan from there instead (also at 21:00 and 22:00 IST)
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from scanner.build import ROOT, build
from server.broker import OrderRequest, PaperBroker, check_token, make_broker, preview_token, tradingsymbol
from server.candles import candles
from server.liquidity import read_refusals
from server.news import News
from server.paper import PaperLedger, PaperRejected, QuoteSource, trade_stats
from server.risk import RiskGate, kotak_margin_fn
from server.commentary import Commentary
from server.verdict import Verdict
from server.version import deployed
from server import alerts
from server.config import settings
from server.live import FakeProvider, KiteProvider, LiveFeed, market_open

log = logging.getLogger("server")
IST = timezone(timedelta(hours=5, minutes=30))
app = FastAPI(title="F&O scanner", docs_url=None, redoc_url=None, openapi_url=None)   # nothing public without the password
security = HTTPBasic(auto_error=False)


COOKIE = "fo_login"
COOKIE_DAYS = 365


def _cookie_value() -> str:
    """The login cookie: an HMAC of the password, so changing APP_PASSWORD signs every browser out."""
    return hmac.new(settings.app_password.encode(), b"fo-login-v1", hashlib.sha256).hexdigest()


def auth(request: Request, c: HTTPBasicCredentials | None = Depends(security)) -> str:
    """The login page's cookie (browsers, remembered a year) or HTTP Basic (scripts, the watchdog). Pages without
    either go to /login; the API answers 401 without a Basic challenge, so the browser shows no popup."""
    if settings.public_access:                      # PUBLIC_ACCESS=true: no login (paper orders only, see config)
        return "public"
    if not settings.app_password:
        raise HTTPException(503, "APP_PASSWORD is not set on the server")
    if secrets.compare_digest(request.cookies.get(COOKIE, ""), _cookie_value()):
        return "user"
    if c is not None and secrets.compare_digest(c.username, "user") and secrets.compare_digest(c.password, settings.app_password):
        return c.username
    if request.method == "GET" and not request.url.path.startswith("/api/"):
        raise HTTPException(303, headers={"Location": "/login?next=" + quote(request.url.path)})
    raise HTTPException(401, "Unauthorized")


@app.get("/login", response_class=HTMLResponse)
def login_page():
    if settings.public_access:
        return RedirectResponse("/", 303)
    return (ROOT / "templates" / "login.html").read_text(encoding="utf-8")


@app.post("/login")
async def login(request: Request):
    form = parse_qs((await request.body()).decode())
    nxt = (form.get("next") or ["/"])[0]
    nxt = nxt if nxt.startswith("/") and not nxt.startswith("//") else "/"
    if settings.app_password and secrets.compare_digest((form.get("password") or [""])[0], settings.app_password):
        r = RedirectResponse(nxt, 303)
        r.set_cookie(COOKIE, _cookie_value(), max_age=COOKIE_DAYS * 86400, httponly=True, samesite="lax")
        return r
    await asyncio.sleep(1.5)                        # slows guessing; the site is on the open internet (Funnel)
    return RedirectResponse("/login?bad=1&next=" + quote(nxt), 303)


@app.get("/logout")
def logout():
    r = RedirectResponse("/login", 303)
    r.delete_cookie(COOKIE)
    return r


# ---------------------------------------------------------------- state
class State:
    def __init__(self):
        self.scan: dict = {}
        self.stocks: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.feed: LiveFeed | None = None
        self.broker = make_broker(settings)
        self.ledger: PaperLedger | None = None
        self.rules = None                    # server.rules.RuleTrader: the S1 rule trades in the paper account
        self.fade = None                     # server.fade.FadeTrader: S1 v10 results-day fade, paper only
        self.mirror = None                   # server.durable.Mirror when LEDGER_GITHUB_TOKEN is set
        self.compare = None                  # server.provider_compare.ProviderCompare (Kotak live + Upstox token)
        self.commentary = Commentary(settings.anthropic_api_key, settings.commentary_model, settings.data_dir / "cache") if settings.commentary_enabled else None
        self.verdict = Verdict(settings.anthropic_api_key, settings.commentary_model, settings.data_dir / "cache") if settings.commentary_enabled else None
        self.orders_today = Counter()
        self.news = News()
        self.fut_source = None              # provider.futures(symbols) -> {symbol: [near, next, ...]} when it has one
        self.upstox = None                  # server.upstox.UpstoxProvider (instrument keys) when the stream is on
        self.stream = None                  # server.upstox_stream.UpstoxStream
        self.version: dict | None = None    # server.version.deployed(), read once at start-up

    def load_scan(self, path: Path) -> None:
        scan = json.loads(path.read_text())
        with self.lock:
            self.scan = scan
            self.stocks = {s["symbol"]: s for s in scan["stocks"]}
        if self.feed:
            self.feed.reload(scan, self.fut_symbols())

    def fut_symbols(self) -> dict[str, str | list[str]]:
        """Futures per stock for the live feed: every live contract, nearest first, when the provider lists them
        (fut_source); else the nearest-expiry tradingsymbol (Kite naming; the option chain expiry is the same
        monthly cycle as the near futures contract)."""
        if self.fut_source is not None:
            try:
                return self.fut_source(sorted(self.stocks))
            except Exception as exc:  # noqa: BLE001 - fall back to the scan's contract
                log.warning("futures from the provider failed (%s); using the scan's expiry", exc)
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
    state.version = deployed(ROOT)
    log.info("running commit %s (%s)", state.version["commit"], state.version["commit_source"])
    alerts.send(f"🔄 F&O scanner started (commit {state.version['commit']}).", key="startup", every=300)
    if settings.scan_url:
        try:
            _pull_scan()
        except Exception as exc:  # noqa: BLE001 - the copy in the image is the fallback
            log.warning("could not read the scan from SCAN_URL (%s); using the local copy", exc)
    if SCAN_PATH.exists():
        if not state.scan:
            state.load_scan(SCAN_PATH)
    else:
        log.warning("no data/scan.json yet; run `python -m scanner.build` or POST /api/rebuild")
    src = settings.live_source
    if src == "upstox":
        from server.upstox import UpstoxProvider
        provider = UpstoxProvider(settings.upstox_analytics_token, settings.upstox_chain_calls_per_poll)
        state.fut_source = provider.futures
        state.feed = LiveFeed(provider, state.scan or {"stocks": []}, settings.poll_seconds, state.fut_symbols())
        state.feed.start()
        log.info("live feed on (Upstox, read-only): LTP + futures OI every %ss, PCR/strike OI for %d stocks per poll",
                 settings.poll_seconds, settings.upstox_chain_calls_per_poll)
    elif src == "kotak":
        from server.kotak import KotakProvider, shared_session
        provider = KotakProvider(shared_session(settings), settings.kotak_chain_calls_per_poll)
        state.fut_source = provider.futures
        if settings.upstox_analytics_token and settings.upstox_stream:
            # prices pushed by the Upstox WebSocket, Kotak as the automatic fallback (DECISIONS.md 2026-10-22)
            from server.upstox import UpstoxProvider
            from server.upstox_stream import StreamingProvider, UpstoxStream
            state.upstox = UpstoxProvider(settings.upstox_analytics_token, chain_calls_per_poll=0)
            threading.Thread(target=state.upstox.load_instruments, name="upstox-instruments", daemon=True).start()
            state.stream = UpstoxStream(settings.upstox_analytics_token)
            state.stream.start()
            provider = StreamingProvider(provider, state.upstox, state.stream)
        state.feed = LiveFeed(provider, state.scan or {"stocks": []}, settings.poll_seconds, state.fut_symbols(),
                              fast_seconds=settings.live_fast_seconds)
        state.feed.start()
        if state.stream is not None:
            threading.Thread(target=lambda: log.info("upstox stream: %d universe keys subscribed",
                                                     provider.prime(list(state.feed.keys))),
                             name="upstox-prime", daemon=True).start()
        log.info("live feed on (%s): every %ss while the stream is up, else every %ss from Kotak",
                 "Upstox stream + Kotak fallback" if state.stream else "Kotak Neo, consumer key only",
                 settings.live_fast_seconds, settings.poll_seconds)
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
    if state.feed:
        state.feed.snapshot_dir = settings.data_dir / "live_snapshots"
    if not settings.orders_enabled:
        state.broker = None
    elif isinstance(state.broker, PaperBroker):
        _start_mirror()
        state.ledger = PaperLedger(settings.data_dir, QuoteSource(state.feed), always_open=bool(state.feed and state.feed.poll_always),
                                   real_orders=settings.paper_real_orders)
        margin_fn = None
        if settings.kotak_consumer_key and settings.kotak_mobile and settings.kotak_ucc and settings.kotak_totp_secret and settings.kotak_mpin:
            from server.kotak import shared_session
            margin_fn = kotak_margin_fn(shared_session(settings))   # used only while a Kotak trade session exists
        state.ledger.risk = RiskGate(settings, margin_fn)
        state.broker.ledger = state.ledger
        if state.feed:
            from server.rules import RuleTrader
            state.feed.hooks.append(lambda feed: state.ledger.on_poll(feed))
            state.rules = RuleTrader(state.ledger, lambda: ((state.scan or {}).get("meta") or {}).get("forward"),
                                     fade=lambda: ((state.scan or {}).get("meta") or {}).get("fade"))   # the ban list
            state.feed.hooks.append(lambda feed: state.rules.on_poll(datetime.now(IST)))
            from server.fade import FadeTrader                  # S1 v10 results-day fade, paper only
            state.fade = FadeTrader(state.ledger, lambda: ((state.scan or {}).get("meta") or {}).get("fade"))
            state.feed.hooks.append(lambda feed: state.fade.on_poll(datetime.now(IST)))
            if settings.fade_fast_seconds > 0:
                threading.Thread(target=_fade_fast_loop, name="fade-fast-exit", daemon=True).start()
        log.info("paper engine on: capital Rs %s, fills against %s", f"{state.ledger.state['capital']:,.0f}",
                 "the live book" if state.feed else "nothing (no live feed: paper orders cannot fill)")
    if src == "kotak" and state.feed and settings.upstox_analytics_token:
        _start_compare()
    threading.Thread(target=_daily_rebuild_loop, daemon=True).start()


def _fade_fast_loop() -> None:
    """The fade's live exits and waiting entries about every FADE_FAST_SECONDS (default 1 s): one quote call for the open fade contracts
    only (Kotak: well inside 25/s; the shared limiter keeps the whole server under 200/min), then the stop and trail
    checks (server/fade.py fast_tick). Idle outside 09:16-15:20 or with no open fade position."""
    while True:
        try:
            if state.fade is not None:
                now = datetime.now(IST)
                state.ledger.work_orders(now)            # rule orders in flight (strategies/S1_paper_real_order_fills.md)
                state.fade.fast_tick(now)
                state.fade.entry_tick(now)               # 1-second entries from 09:15:00 (DECISIONS.md 2026-10-22)
                state.fade.entry_probe(now)              # record only, 09:14:50-10:00 (S1_v11_entry_probe.md)
                _phone_tick(now)
                if state.stream is not None:
                    state.stream.write_candles(settings.data_dir)   # 1-second candles (server/upstox_stream.py)
        except Exception as exc:  # noqa: BLE001 - the 30 s poll still checks the exits
            log.warning("fade fast exit: %s", exc)
            alerts.send(f"⚠️ Trading loop error: {exc}"[:300], key="fast-loop", every=900)
        time.sleep(settings.fade_fast_seconds)


_PHONE: dict = {"stream": None, "eod": None, "ready": None, "plan": None, "missing": None, "late": None, "checked": 0.0}


def _plan_alerts(now: datetime) -> None:
    """The next session's plan on Telegram (server/plan_alert.py): "list ready" once when it lands, the plan at 09:08, a
    warning at 09:08 when the lists are not for today, and a note if a missing list arrives after the open."""
    if now.timestamp() - _PHONE["checked"] < 30:
        return
    _PHONE["checked"] = now.timestamp()
    from server import plan_alert as pa, sessions
    meta, today, hhmm = (state.scan or {}).get("meta") or {}, now.date(), now.strftime("%H:%M")
    day = pa.target_day(today, now.hour * 60 + now.minute)
    if _PHONE["ready"] != day.isoformat() and (hhmm >= "15:45" or hhmm < "09:15"):
        text = pa.ready_text(meta, day)
        if text:
            _PHONE["ready"] = day.isoformat()
            alerts.send(text, key=f"ready-{day}", every=86400)
    if not sessions.is_session(today):
        return
    if "09:08" <= hhmm < "09:15" and _PHONE["plan"] != today.isoformat():
        _PHONE["plan"] = today.isoformat()
        text, ok = pa.morning_text(meta, today)
        _PHONE["missing"] = None if ok else today.isoformat()
        alerts.send(text, key=f"plan-{today}", every=86400)
    elif "09:15" <= hhmm < "15:00" and _PHONE["missing"] == today.isoformat() and _PHONE["late"] != today.isoformat():
        text = pa.late_text(meta, today)
        if text:
            _PHONE["late"] = today.isoformat()
            alerts.send(text, key=f"late-{today}", every=86400)


def _phone_tick(now: datetime) -> None:
    """Phone alerts the 1-second loop raises (server/alerts.py): the Upstox stream lost or back during market hours,
    and once after 15:31 on a session day, the day's paper result."""
    if not alerts.enabled():
        return
    from server import sessions
    from server.rules import streaming
    if sessions.market_open_at(now):
        s = streaming(state.ledger)
        if _PHONE["stream"] is True and not s:
            alerts.send("⚠️ Upstox price stream lost: prices now come from Kotak (slower). Trading continues.",
                        key="stream-down", every=600)
        elif _PHONE["stream"] is False and s:
            alerts.send("✅ Upstox price stream is back (1-second prices).", key="stream-up", every=600)
        _PHONE["stream"] = s
    _plan_alerts(now)
    today = now.date().isoformat()
    if now.strftime("%H:%M") >= "15:31" and _PHONE["eod"] != today and sessions.is_session(now.date()):
        _PHONE["eod"] = today
        closed = [c for c in state.ledger.state.get("closed", []) if c.get("rule") and c["closed_at"][:10] == today]
        net = sum(c["net_pnl"] for c in closed)
        inst = [c["instant"]["net"] for c in closed if c.get("instant")]
        lines = [f"📊 {today}: {len(closed)} paper trade(s) closed, net ₹{net:,.0f}"
                 + (f" (instant fills would be ₹{sum(inst):,.0f})" if inst else "")]
        lines += [f"• {c['tradingsymbol']} {c.get('reason')}: ₹{c['net_pnl']:,.0f}" for c in closed[:12]]
        still = len(state.ledger.state.get("positions", []))
        if still:
            lines.append(f"{still} position(s) still open.")
        alerts.send("\n".join(lines))


def _start_compare() -> None:
    """The Upstox-vs-Kotak shadow check (server/provider_compare.py): reads only, never changes the live feed."""
    try:
        from server.provider_compare import ProviderCompare, contract_picker
        from server.upstox import UpstoxProvider
        up = state.upstox or UpstoxProvider(settings.upstox_analytics_token, chain_calls_per_poll=0)
        spot = lambda s: (state.feed.snapshot()["quotes"].get(s) or {}).get("ltp")              # noqa: E731
        kotak = getattr(state.feed.provider, "kotak", state.feed.provider)      # Kotak's own quotes, not the stream's
        state.compare = ProviderCompare(settings.data_dir, kotak, up,
                                        contract_picker(state.ledger, state.stocks, state.fut_symbols, spot, up))
        state.compare.start()
        log.info("provider compare on: Upstox vs Kotak every %ss of a session", 300)
    except Exception as exc:  # noqa: BLE001 - the shadow check is optional
        log.warning("provider compare could not start: %s", exc)


def _daily_rebuild_loop() -> None:
    """19:45 IST: fetch the day's exchange events (guide 12 spec); 20:30 IST: rebuild the scan, which
    joins them in. A failed event run never blocks the rebuild."""
    # the nightly Action commits after midnight IST: pull again before the open, for the rule trades' list
    jobs = [((8, 40), _pull_scan), ((9, 5), _pull_scan), ((21, 0), _pull_scan), ((22, 0), _pull_scan)] \
        if settings.scan_url else \
        [((19, 45), _events_run), ((20, 30), _rebuild)]
    while True:
        now = datetime.now(IST)
        when, job = min(((now.replace(hour=h, minute=m, second=0, microsecond=0)
                          + (timedelta(days=1) if now.replace(hour=h, minute=m, second=0, microsecond=0) <= now
                             else timedelta())), fn) for (h, m), fn in jobs)
        time.sleep((when - now).total_seconds())
        if when.weekday() < 5:
            try:
                job()
            except Exception as exc:  # noqa: BLE001
                log.error("scheduled %s failed: %s", job.__name__, exc)


def _events_run() -> None:
    from scanner.events.run import Runner
    r = Runner()
    r.ensure_shares()
    r.run_day(datetime.now(IST).date())
    _maybe_retrain()


def _maybe_retrain(max_age_days: int = 31) -> None:
    """Monthly model retrain from the rebuild hook, in its own thread so the 20:30 build never waits."""
    from scanner.model import MODEL_PATH
    try:
        age_ok = MODEL_PATH.exists() and (time.time() - MODEL_PATH.stat().st_mtime) < max_age_days * 86400
    except OSError:
        age_ok = False
    if age_ok:
        return

    def _job() -> None:
        try:
            from scanner.model import train
            from datetime import date as _date
            train(since=_date.today().replace(year=_date.today().year - 3))
            log.info("model retrained")
        except Exception as exc:  # noqa: BLE001
            log.error("model retrain failed: %s", exc)
    threading.Thread(target=_job, name="model-retrain", daemon=True).start()


def _start_mirror() -> None:
    """Restore the paper account from its durable copy (if any file is missing locally) and keep mirroring it."""
    if not settings.ledger_github_token:
        log.warning("paper account mirror off (no LEDGER_GITHUB_TOKEN): the ledger is lost on every restart")
        return
    from server.durable import GitHubStore, Mirror
    try:
        store = GitHubStore(settings.ledger_github_repo, settings.ledger_github_branch, settings.ledger_github_token)
        store.ensure_branch()
        state.mirror = Mirror(settings.data_dir, store)
        state.mirror.restore(snapshot_days=[datetime.now(IST).strftime("%Y-%m-%d")])
        state.mirror.start()
    except Exception as exc:  # noqa: BLE001 - the server still runs; the summary shows the mirror is off
        log.warning("paper account mirror could not start: %s", exc)
        state.mirror = None


def _pull_scan() -> dict:
    """Read the scan someone else built (SCAN_URL, e.g. the GitHub Action's raw data/scan.json), keep a local copy,
    and load it. Refuses anything that is not a scan, so a bad download never replaces a good scan."""
    import requests
    r = requests.get(settings.scan_url, timeout=60, headers={"Cache-Control": "no-cache"})
    r.raise_for_status()
    scan = r.json()
    if not isinstance(scan, dict) or not scan.get("stocks") or "meta" not in scan:
        raise ValueError("SCAN_URL did not return a scan (no stocks/meta)")
    SCAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCAN_PATH.write_text(json.dumps(scan))
    state.load_scan(SCAN_PATH)
    log.info("scan %s read from SCAN_URL (%d stocks)", scan["meta"].get("as_of"), len(scan["stocks"]))
    return scan["meta"]


def _rebuild() -> dict:
    if settings.scan_url:
        return _pull_scan()
    scan = build(ROOT / "data" / "eod2", settings.data_dir / "cache")
    SCAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCAN_PATH.write_text(json.dumps(scan))
    state.load_scan(SCAN_PATH)
    return scan["meta"]


def _forward_for_page(fw: dict | None) -> dict | None:
    """The forward list plus `for_today`: whether it is the list for the current session (server.rules.forward_is_current),
    so the results page never shows an old list as today's."""
    from server.rules import forward_is_current
    return None if fw is None else {**fw, "for_today": forward_is_current(fw, datetime.now(IST).date())}


# ---------------------------------------------------------------- page & data
@app.get("/tokens.css")
def tokens_css():
    """Shared design tokens for every page (templates/tokens.css). Public: it holds colours only."""
    return Response((ROOT / "templates" / "tokens.css").read_text(encoding="utf-8"), media_type="text/css",
                    headers={"Cache-Control": "no-cache"})


@app.get("/", response_class=HTMLResponse)
def results_page(_: str = Depends(auth)):
    """The home page: paper account and the forward test (templates/results.html), no chart and no scan."""
    html = (ROOT / "templates" / "results.html").read_text(encoding="utf-8")
    meta = (state.scan or {}).get("meta") or {}
    fwd = json.dumps(_forward_for_page(meta.get("forward")), separators=(",", ":")).replace("</", "<\\/")
    fade = json.dumps(meta.get("fade"), separators=(",", ":")).replace("</", "<\\/")
    return (html.replace("/*__FORWARD__*/null", fwd).replace("/*__FADE__*/null", fade)
            .replace("/*__SERVER__*/{}", json.dumps(settings.public())))


@app.get("/s2", response_class=HTMLResponse)
def s2_page(_: str = Depends(auth)):
    """S2's own page (templates/s2.html): the last session's short build-ups and the S2 research."""
    html = (ROOT / "templates" / "s2.html").read_text(encoding="utf-8")
    data = json.dumps(((state.scan or {}).get("meta") or {}).get("s2"), separators=(",", ":")).replace("</", "<\\/")
    return html.replace("/*__S2__*/null", data).replace("/*__SERVER__*/{}", json.dumps(settings.public()))


@app.get("/api/s2")
def api_s2(_: str = Depends(auth)):
    return ((state.scan or {}).get("meta") or {}).get("s2")


@app.get("/api/forward")
def api_forward(_: str = Depends(auth)):
    return _forward_for_page(((state.scan or {}).get("meta") or {}).get("forward"))


@app.get("/api/fade")
def api_fade(_: str = Depends(auth)):
    """S1 v10 fade list for the next results session (scanner/fade_live.py): signals, skipped filings, history."""
    return ((state.scan or {}).get("meta") or {}).get("fade")


@app.get("/terminal", response_class=HTMLResponse)
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
    snap = {"enabled": True, **state.feed.snapshot(), "interval_s": state.feed.interval()}
    if state.stream is not None:
        snap["stream"] = {**state.stream.status(), "served": dict(state.feed.provider.served)}
    return snap


@app.get("/api/live/snapshot")
def api_live_snapshot(date: str | None = None, _: str = Depends(auth)):
    """The 09:30 opening snapshot of live labels for `date` (default today, IST), for the GitHub workflow."""
    import re
    d = date or datetime.now(IST).date().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        raise HTTPException(400, "date must be YYYY-MM-DD")
    path = settings.data_dir / "live_snapshots" / f"{d}.json"
    if not path.exists():
        raise HTTPException(404, f"no opening snapshot for {d}")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/chain/{symbol}")
def api_chain(symbol: str, _: str = Depends(auth)):
    s = state.stocks.get(symbol.upper())
    if not s or not s.get("chain"):
        raise HTTPException(404, "no option chain for this symbol in the current scan")
    chain = json.loads(json.dumps(s["chain"]))
    sym = symbol.upper()
    if state.feed and (state.feed.poll_always or market_open()):
        key = {(row["strike"], t): "NFO:" + tradingsymbol(sym, t, chain["expiry"], row["strike"])
               for row in chain["strikes"] for t in ("CE", "PE")}
        try:
            q = state.feed.provider.quote(list(key.values()))
            for row in chain["strikes"]:
                for t in ("CE", "PE"):
                    row.update(_live_leg(q.get(key[(row["strike"], t)]), t.lower(), row))
            chain["live_at"] = datetime.now(IST).strftime("%H:%M:%S")
        except Exception as exc:  # noqa: BLE001
            chain["live_error"] = str(exc)
        strikes = sorted(row["strike"] for row in chain["strikes"])
        atm = chain.get("atm") if chain.get("atm") in strikes else (strikes[len(strikes) // 2] if strikes else None)
        if atm is not None:                           # the options around the money get polled for their charts
            i = strikes.index(atm)
            state.feed.watch_options(sym, [key[(k, t)] for k in strikes[max(0, i - 5): i + 6] for t in ("CE", "PE")])
    return chain


def _live_leg(q: dict | None, t: str, row: dict) -> dict:
    """One option's live fields for the chain table: price, % change vs its previous close, volume, OI, OI change
    vs the scan's close, average traded price, best bid / ask."""
    if not q:
        return {}
    ltp, prev = q.get("last_price"), (q.get("ohlc") or {}).get("close") or q.get("prev_close") or row.get(f"{t}_close")
    oi, oi_eod = q.get("open_interest"), row.get(f"{t}_oi")
    depth = q.get("depth") or {}
    return {f"{t}_live_ltp": ltp, f"{t}_live_oi": oi, f"{t}_live_vol": q.get("volume"), f"{t}_live_atp": q.get("atp"),
            f"{t}_live_chg_pct": round((ltp / prev - 1) * 100, 2) if ltp and prev else None,
            f"{t}_live_oi_chg": oi - oi_eod if oi is not None and oi_eod is not None else None,
            f"{t}_bid": (depth.get("bid") or [(None,)])[0][0], f"{t}_ask": (depth.get("ask") or [(None,)])[0][0]}


HISTORY_LOOKBACK = 6                              # calendar days searched for the last session with candles


def _history(key: str, tf: int, today_only: bool = False) -> tuple[str | None, list[dict], str | None]:
    """The most recent session's candles of `key` from the provider's historical API (KotakProvider.history):
    (session, candles, error). Today first, then back over weekdays."""
    hist = getattr(state.feed.provider, "history", None) if state.feed else None
    if hist is None:
        return None, [], None
    d = datetime.now(IST).date()
    for _ in range(1 if today_only else HISTORY_LOOKBACK):
        if d.weekday() < 5:
            try:
                bars = hist(key, tf, d.isoformat())
            except Exception as exc:  # noqa: BLE001 - the chart then says why, the page keeps working
                log.warning("history %s %s: %s", key, d, exc)
                return None, [], str(exc)[:160]
            if bars:
                return d.isoformat(), bars, None
        d -= timedelta(days=1)
    return None, [], None


@app.get("/api/intraday/{symbol}")
def api_intraday(symbol: str, tf: int = 1, leg: str = "stock", _: str = Depends(auth)):
    """Candles from the live feed's ticks since the server's first poll today (see server/candles.py). With no
    ticks (market closed, a restart, Render asleep) the last session's candles come from the broker's historical
    API; when the server started polling late today, history fills the morning before the first tick."""
    sym = symbol.upper()
    if tf not in (1, 3, 5, 15, 30):
        raise HTTPException(400, "tf must be 1, 3, 5, 15 or 30 (minutes)")
    if not state.feed:
        return {"symbol": sym, "leg": leg, "tf": tf, "candles": [], "since": None, "note": "live feed is off"}
    if leg == "stock":
        ticks, cols, key, hkey = state.feed.ticks(sym), (1, 2, 3), None, "NSE:" + sym
    elif leg == "fut":
        ticks, cols, key, hkey = state.feed.ticks(sym), (4, 6, 7), None, None
    else:
        typ, _sep, strike = leg.upper().partition(":")
        s = state.stocks.get(sym)
        exp = ((s or {}).get("chain") or {}).get("expiry")
        if typ not in ("CE", "PE") or not exp:
            raise HTTPException(400, "leg must be stock, CE:<strike> or PE:<strike> of a stock with an option chain")
        try:
            key = "NFO:" + tradingsymbol(sym, typ, exp, float(strike))
        except ValueError:
            raise HTTPException(400, "bad strike")
        hkey = key
        if market_open():                              # keep polling the option while its chart is open
            w = state.feed.watch.get(sym)
            state.feed.watch_options(sym, list(dict.fromkeys(((w[1] if w and w[0] > time.time() else []) + [key]))))
        ticks, cols = state.feed.option_ticks(key), (1, 2, 3)
    bars = candles(ticks, tf, *cols)
    source, session, err = "live", None, None
    if hkey and not bars:
        session, bars, err = _history(hkey, tf)
        source = "history" if bars else "none"
    elif hkey and bars and datetime.fromtimestamp(bars[0]["time"], IST).strftime("%H:%M") > "09:16":
        day, hb, err = _history(hkey, tf, today_only=True)
        if day == datetime.now(IST).date().isoformat() and hb:
            bars = [b for b in hb if b["time"] < bars[0]["time"]] + bars
            source = "history+live"
    return {"symbol": sym, "leg": leg, "tf": tf, "key": key, "candles": bars, "source": source, "session": session,
            "history_error": err,
            "since": datetime.fromtimestamp(ticks[0][0], IST).strftime("%H:%M") if ticks else None,
            "ticks": len(ticks), "market_open": market_open()}


@app.get("/api/history/{symbol}")
def api_history(symbol: str, day: str, tf: int = 1, _: str = Depends(auth)):
    """Research (the S1 v10 stop-loss study): a STOCK's tf-minute candles on a past day from the broker's historical
    API, through this server's own key, so the key never leaves the server. Stocks only; refused while the market
    is open, so it never competes with the live polls (Kotak's calls are also spaced HISTORY_MIN_INTERVAL apart)."""
    sym = symbol.upper()
    try:
        d = datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "day must be YYYY-MM-DD")
    if d >= datetime.now(IST).date():
        raise HTTPException(400, "past days only")
    if tf not in (1, 3, 5, 15, 30):
        raise HTTPException(400, "tf must be 1, 3, 5, 15 or 30 (minutes)")
    if market_open():
        raise HTTPException(503, "not during market hours (09:15-15:30 IST): the live feed comes first")
    hist = getattr(state.feed.provider, "history", None) if state.feed else None
    if hist is None:
        raise HTTPException(404, "no broker history on this server")
    try:
        bars = hist("NSE:" + sym, tf, d.isoformat())
    except Exception as exc:  # noqa: BLE001 - say why, do not crash
        return {"symbol": sym, "day": d.isoformat(), "tf": tf, "candles": [], "error": str(exc)[:200]}
    return {"symbol": sym, "day": d.isoformat(), "tf": tf, "candles": bars, "error": None}


@app.get("/api/news/{symbol}")
def api_news(symbol: str, _: str = Depends(auth)):
    sym = symbol.upper()
    s = state.stocks.get(sym)
    if not s:
        raise HTTPException(404, f"{sym} is not in the scan")
    return state.news.get(sym, s.get("name"))


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
    stop: float | None = None
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
    if req.instrument == "FUT":                      # DECISIONS.md: long options only (CE / PE buys), no futures
        raise HTTPException(400, "options only: futures orders are off (buy a call or a put)")
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
    if state.ledger is not None:                     # paper: the full review against the live book
        review = state.ledger.preview(req, resolved, body.stop)
        px = (review.get("fill") or {}).get("price") or req.price or ref or 0
        ok = not review["blocked"]
        if not ok:
            log.info("paper preview blocked %s: %s", resolved["tradingsymbol"], "; ".join(review["blocked"]))
        return {**resolved, "paper": True, "reference_price": ref, "notional": round(px * resolved["quantity"], 2),
                "estimated_margin": review.get("margin"), "orders_today": sum(state.orders_today.values()),
                "max_orders_per_day": settings.max_orders_per_day, "review": review,
                "token": preview_token(payload) if ok else None}
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
    if state.ledger is not None:
        try:
            rec = state.ledger.submit(req, resolved, body.stop)
            if getattr(state, "mirror", None) is not None:
                try:
                    state.mirror.flush(force=True)       # an order is never left only on the wiped disk
                except Exception as exc:  # noqa: BLE001
                    log.warning("paper account mirror: %s", exc)
        except PaperRejected as exc:                 # risk, liquidity or sizing block: readable, logged
            log.info("paper order blocked %s: %s", resolved["tradingsymbol"], exc)
            raise HTTPException(400, str(exc))
    else:
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


def _ledger() -> PaperLedger:
    if state.ledger is None:
        raise HTTPException(404, "paper trading is off (set ORDERS=true with PAPER=true)")
    return state.ledger


@app.get("/api/paper/summary")
def api_paper_summary(_: str = Depends(auth)):
    import os
    from server.fade import CARRY_DATES, fd2, shadow_entries, split, t100, trail_shadow, v10_shadow, v12_compare
    m = getattr(state, "mirror", None)
    lg = _ledger()
    # which code is running: read at start-up from a deploy setting or the checkout's .git (server/version.py)
    ver = state.version or deployed(ROOT)
    return {**lg.summary(), "persistence": m.status if m is not None else {"enabled": False},
            "version": {**ver, "fade_carry_dates": sorted(CARRY_DATES)},
            "fade_split": split(getattr(lg, "state", {})),            # strategies/S1_v10_np25_shadow_track.md
            "fade_t100": t100(getattr(lg, "state", {})),              # strategies/S1_v10_t100_shadow_track.md
            "fade_v10_shadow": v10_shadow(getattr(lg, "state", {})),  # strategies/S1_v11_fade_stop20.md
            "fade_subfloor": shadow_entries(getattr(lg, "state", {})),  # strategies/S1_v10_subfloor_entry.md
            "fade_fd2": fd2(getattr(lg, "state", {})),                 # strategies/S1_v11_fd2_shadow_track.md
            "fade_trail": trail_shadow(getattr(lg, "state", {})),      # strategies/S1_v11_trail_shadow_track.md
            "fade_v12": v12_compare(getattr(lg, "state", {}))}         # strategies/S1_v12_fade_trail2.md


@app.get("/api/paper/positions")
def api_paper_positions(_: str = Depends(auth)):
    return _ledger().positions_view()


@app.get("/api/paper/trades")
def api_paper_trades(_: str = Depends(auth)):
    trades = _ledger().trades_view()
    return {"trades": trades, "stats": trade_stats(trades)}


@app.post("/api/paper/close/{pid}")
def api_paper_close(pid: str, _: str = Depends(auth)):
    """Close one paper position now at the best bid (the results page's Close)."""
    try:
        return _ledger().close_now(pid)
    except PaperRejected as exc:
        raise HTTPException(409, str(exc))


@app.get("/api/paper/rules")
def api_paper_rules(_: str = Depends(auth)):
    """The rule trader's day (entries made or refused per stock and entry time) and the archived earlier account."""
    lg = _ledger()
    with lg.lock:                    # a copy: the feed thread edits rules (open_wait, fade_wait) while this is encoded
        st = lg.state
        arch = [{**{k: a.get(k) for k in ("epoch", "archived_at", "created_at")},
                 "open": len(a.get("positions", [])), "closed": len(a.get("closed", []))} for a in st.get("archive", [])]
        rules = json.loads(json.dumps(st.get("rules") or {}))
        return {"epoch": st.get("epoch"), "started": st.get("created_at"), "rules": rules, "archive": arch}


@app.get("/api/data/compare")
def api_data_compare(day: str | None = None, _: str = Depends(auth)):
    """The Upstox-vs-Kotak shadow check for a day (default today): per-round summaries, day totals, largest gaps."""
    c = state.compare
    if c is None:
        return {"enabled": False, "why": "runs only while Kotak is the live source and UPSTOX_ANALYTICS_TOKEN is set"}
    d = day or datetime.now(IST).date().isoformat()
    return {"enabled": True, "status": c.status, **(c.load(d) or {"date": d, "rounds": []})}


@app.get("/api/paper/refusals")
def api_paper_refusals(_: str = Depends(auth)):
    rows = read_refusals(_ledger().refusals_path, limit=100_000)
    return {"count": len(rows), "refusals": rows[:200]}


@app.post("/api/rebuild")
def api_rebuild(_: str = Depends(auth)):
    try:
        return _rebuild()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"rebuild failed: {exc}")


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=exc.headers)


# ---------------------------------------------------------------- index options (INDEX_DATA_PLAN.md §8)
# Read-only page and data in their own modules; registered here without changing any existing route.
from server import index_api, index_pages  # noqa: E402

app.include_router(index_api.router, dependencies=[Depends(auth)])
app.include_router(index_pages.router, dependencies=[Depends(auth)])
