"""Live prices pushed by the Upstox v3 market data feed (WebSocket), with Kotak as the automatic fallback.

The server is always on (AWS), so instead of polling every 30 s it keeps one WebSocket open to Upstox
(`full` mode: last price, 5-level depth, ATP, volume, OI, day OHLC) for every contract it asks about. Read-only:
the Analytics Token cannot place orders. DECISIONS.md, 2026-10-22 (the user's decision).

    UpstoxStream        the connection: authorize -> wss -> subscribe in `full` mode -> decode each FeedResponse;
                        reconnects by itself; keeps the latest state per instrument key (at most MAX_KEYS).
    StreamingProvider   the provider the live feed and the paper engine use: quote / quote_one / quote_many answer
                        from the stream when it is healthy (a message within STALE_SECONDS) and the contract has
                        streamed at least once; anything else (and everything while the stream is down) goes to
                        Kotak, as before. Every other call (history, chains, futures, scrip master) is Kotak's.
                        The live PCR still comes from Kotak's option-chain sweep, CHAIN_STOCKS stocks every
                        CHAIN_EVERY seconds.

The decoder below reads the protobuf wire format directly for the fields of MarketDataFeedV3.proto that we use
(upstox/upstox-python, upstox_client/feeder/proto), so no generated code or extra package is needed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import struct
import threading
import time
from datetime import datetime, timedelta, timezone

import requests

from server.upstox import KEY_RE, UpstoxProvider

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
AUTHORIZE = "https://api.upstox.com/v3/feed/market-data-feed/authorize"
MAX_KEYS = 1900                 # `full` mode allows 2,000 keys per connection
SUB_CHUNK = 500                 # keys per subscribe message
STALE_SECONDS = 15.0            # no message for this long during market hours: the stream counts as down
CHAIN_EVERY, CHAIN_STOCKS = 10.0, 4     # Kotak option-chain sweep for the live PCR (same budget as 12 per 30 s)


# ---------------------------------------------------------------- protobuf wire format
def _varint(b: bytes, i: int) -> tuple[int, int]:
    n = shift = 0
    while True:
        c = b[i]
        i += 1
        n |= (c & 0x7F) << shift
        if not c & 0x80:
            return n, i
        shift += 7


def fields(b: bytes) -> dict[int, list]:
    """{field number: [values]}: varints as int, 64-bit as 8 raw bytes, length-delimited as bytes."""
    out: dict[int, list] = {}
    i, n = 0, len(b)
    while i < n:
        key, i = _varint(b, i)
        f, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _varint(b, i)
        elif wt == 1:
            v, i = b[i:i + 8], i + 8
        elif wt == 2:
            ln, i = _varint(b, i)
            v, i = b[i:i + ln], i + ln
        elif wt == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f"protobuf wire type {wt}")
        out.setdefault(f, []).append(v)
    return out


def _d(fs: dict, f: int) -> float | None:
    v = fs.get(f)
    return struct.unpack("<d", v[-1])[0] if v else None


def _i(fs: dict, f: int) -> int | None:
    v = fs.get(f)
    if not v:
        return None
    n = v[-1]
    return n - (1 << 64) if n >= 1 << 63 else n


def _ltpc(b: bytes) -> dict:
    fs = fields(b)
    return {"ltp": _d(fs, 1), "ltt": _i(fs, 2), "ltq": _i(fs, 3), "cp": _d(fs, 4)}


def _day_ohlc(b: bytes) -> dict | None:
    for o in fields(b).get(1, []):
        fs = fields(o)
        if (fs.get(1) or [b""])[-1] == b"1d":
            return {"open": _d(fs, 2), "high": _d(fs, 3), "low": _d(fs, 4)}
    return None


def decode(msg: bytes) -> tuple[int, dict[str, dict]]:
    """FeedResponse -> (type, {instrument key: the parts present in this message}). type 0 = initial snapshot,
    1 = live, 2 = market info. Parts: ltpc, depth [(bidP, bidQ, askP, askQ)], ohlc, atp, vtt, oi, tbq, tsq."""
    top = fields(msg)
    typ = _i(top, 1) or 0
    out: dict[str, dict] = {}
    for entry in top.get(2, []):
        e = fields(entry)
        key = e.get(1, [b""])[-1].decode()
        feed = fields(e.get(2, [b""])[-1])
        part: dict = {}
        if 1 in feed:                                           # ltpc mode
            part["ltpc"] = _ltpc(feed[1][-1])
        if 2 in feed:                                           # full mode
            ff = fields(feed[2][-1])
            if 1 in ff:                                         # marketFF
                m = fields(ff[1][-1])
                if 1 in m:
                    part["ltpc"] = _ltpc(m[1][-1])
                if 2 in m:
                    part["depth"] = [(_d(q, 2), _i(q, 1), _d(q, 4), _i(q, 3))
                                     for q in (fields(x) for x in fields(m[2][-1]).get(1, []))]
                if 4 in m:
                    part["ohlc"] = _day_ohlc(m[4][-1])
                for f, name in ((5, "atp"), (7, "oi"), (9, "tbq"), (10, "tsq")):
                    if f in m:
                        part[name] = _d(m, f)
                if 6 in m:
                    part["vtt"] = _i(m, 6)
            elif 2 in ff:                                       # indexFF
                m = fields(ff[2][-1])
                if 1 in m:
                    part["ltpc"] = _ltpc(m[1][-1])
                if 2 in m:
                    part["ohlc"] = _day_ohlc(m[2][-1])
        out[key] = part
    return typ, out


def to_quote(s: dict, fo: bool) -> dict:
    """The merged stream state of one instrument in server/kotak.py's _parse_quote shape."""
    lt = s.get("ltpc") or {}
    ltt = lt.get("ltt")
    d = {"last_price": lt.get("ltp") or None, "volume": s.get("vtt"), "ltq": lt.get("ltq"),
         "timestamp": datetime.fromtimestamp(ltt / 1000, tz=IST).strftime("%Y-%m-%d %H:%M:%S") if ltt else None,
         "depth": {"bid": sorted([(p, q) for p, q, _, _ in s.get("depth") or [] if p and q], key=lambda x: -x[0]),
                   "ask": sorted([(p, q) for _, _, p, q in s.get("depth") or [] if p and q], key=lambda x: x[0])},
         "atp": s.get("atp") or None,
         "buy_qty": int(s["tbq"]) if s.get("tbq") is not None else None,
         "sell_qty": int(s["tsq"]) if s.get("tsq") is not None else None,
         "source": "upstox_stream"}
    o = s.get("ohlc") or {}
    ohlc = {"open": o.get("open") or None, "high": o.get("high") or None, "low": o.get("low") or None,
            "close": lt.get("cp") or None}
    if any(ohlc.values()):
        d["ohlc"] = ohlc
    if fo:
        d["open_interest"] = int(s["oi"]) if s.get("oi") is not None else None
    return d


# ---------------------------------------------------------------- the connection
class UpstoxStream:
    def __init__(self, token: str, max_keys: int = MAX_KEYS):
        self.token, self.max_keys = token, max_keys
        self.lock = threading.Lock()
        self.state: dict[str, dict] = {}            # instrument key -> merged parts
        self.subs: set[str] = set()
        self._pending: set[str] = set()
        self.connected = False
        self.last_msg = 0.0
        self.error: str | None = None
        self.connects = 0
        self.dropped = 0                            # keys refused for the MAX_KEYS cap
        self._stop = threading.Event()

    # -------------------------------------------------- used by the provider (any thread)
    def want(self, keys) -> None:
        with self.lock:
            new = [k for k in keys if k and k not in self.subs]
            room = self.max_keys - len(self.subs)
            if len(new) > room:
                self.dropped += len(new) - max(room, 0)
                new = new[:max(room, 0)]
            self.subs.update(new)
            self._pending.update(new)

    def get(self, key: str) -> dict | None:
        with self.lock:
            s = self.state.get(key)
            return dict(s) if s else None

    def healthy(self, now: float | None = None) -> bool:
        return self.connected and (now or time.time()) - self.last_msg < STALE_SECONDS

    def status(self) -> dict:
        with self.lock:
            return {"connected": self.connected, "healthy": self.healthy(), "keys": len(self.subs),
                    "streamed": len(self.state), "dropped": self.dropped, "connects": self.connects,
                    "last_message_age_s": round(time.time() - self.last_msg, 1) if self.last_msg else None,
                    "error": self.error}

    # -------------------------------------------------- the loop (its own thread)
    def start(self) -> None:
        threading.Thread(target=lambda: asyncio.run(self._main()), name="upstox-stream", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    async def _main(self) -> None:
        backoff = 2.0
        while not self._stop.is_set():
            try:
                await self._run()
                backoff = 2.0
            except Exception as exc:  # noqa: BLE001 - reconnect; the provider falls back to Kotak meanwhile
                self.error = f"{type(exc).__name__}: {exc}"[:300]
                log.warning("upstox stream: %s; reconnecting in %.0fs", self.error, backoff)
            self.connected = False
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)

    def _authorize(self) -> str:
        r = requests.get(AUTHORIZE, headers={"Accept": "application/json", "Authorization": f"Bearer {self.token}"},
                         timeout=15)
        url = ((r.json() or {}).get("data") or {}).get("authorized_redirect_uri") if r.ok else None
        if not url:
            raise RuntimeError(f"authorize failed: HTTP {r.status_code}")
        return url

    async def _send_sub(self, ws, keys: list[str]) -> None:
        for i in range(0, len(keys), SUB_CHUNK):
            msg = {"guid": f"s{time.time_ns()}", "method": "sub",
                   "data": {"mode": "full", "instrumentKeys": keys[i:i + SUB_CHUNK]}}
            await ws.send(json.dumps(msg).encode())         # binary frame, as Upstox requires

    async def _run(self) -> None:
        import websockets
        url = await asyncio.get_running_loop().run_in_executor(None, self._authorize)
        async with websockets.connect(url, max_size=2 ** 24, ping_interval=20, ping_timeout=20) as ws:
            with self.lock:
                keys, self._pending = sorted(self.subs), set()
            self.connected, self.error, self.last_msg = True, None, time.time()
            self.connects += 1
            log.info("upstox stream connected (%d keys)", len(keys))
            await self._send_sub(ws, keys)
            while not self._stop.is_set():
                with self.lock:
                    new, self._pending = sorted(self._pending), set()
                if new:
                    await self._send_sub(ws, new)
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                if isinstance(msg, str):
                    continue
                self.last_msg = time.time()
                try:
                    _, parts = decode(msg)
                except Exception as exc:  # noqa: BLE001 - one bad frame must not drop the connection
                    log.warning("upstox stream: undecodable frame (%s)", exc)
                    continue
                if parts:
                    with self.lock:
                        for k, p in parts.items():
                            self.state.setdefault(k, {}).update({n: v for n, v in p.items() if v is not None})


# ---------------------------------------------------------------- the provider
class StreamingProvider:
    """Kotak's provider with prices from the Upstox stream when it is up (see the module doc)."""

    def __init__(self, kotak, upstox: UpstoxProvider, live: UpstoxStream):
        self.kotak, self.upstox, self.live = kotak, upstox, live
        self._last_sweep = 0.0
        self.served = {"stream": 0, "kotak": 0}

    def __getattr__(self, name):                          # history, futures, chains, master, limiter ...
        if name in ("kotak", "upstox", "live"):
            raise AttributeError(name)
        return getattr(self.kotak, name)

    def streaming(self) -> bool:
        return self.live.healthy()

    def prime(self, keys: list[str], wait_s: float = 300.0) -> int:
        """Subscribe the polling universe as soon as the instrument master is in (server/app.py, at start-up), so
        the first poll of the day already reads the stream. Returns the keys subscribed."""
        end = time.time() + wait_s
        while not self.upstox._loaded and time.time() < end:
            time.sleep(1)
        ik = [self._ikey(k)[0] for k in keys]
        self.live.want(i for i in ik if i)
        return sum(1 for i in ik if i)

    def _ikey(self, key: str) -> tuple[str | None, bool]:
        """Our key (NSE:SYM, NFO:<tradingsymbol> or a bare tradingsymbol) -> (Upstox instrument key, is F&O)."""
        if not self.upstox._loaded:                       # loading in the background (server/app.py): Kotak meanwhile
            return None, key.startswith("NFO:") or ":" not in key
        if key.startswith("NSE:"):
            e = self.upstox._eq.get(key[4:])
            return (e["key"], False) if e else (None, False)
        m = KEY_RE.match(key.split(":", 1)[-1])
        fo = self.upstox._fo_key(m.groupdict()) if m else None
        return (fo["key"], True) if fo else (None, True)

    def _from_stream(self, keys: list[str]) -> tuple[dict[str, dict], list[str]]:
        ik = {k: self._ikey(k) for k in keys}
        self.live.want(i for i, _ in ik.values() if i)
        if not self.live.healthy():
            return {}, list(keys)
        out, missing = {}, []
        for k, (i, fo) in ik.items():
            s = self.live.get(i) if i else None
            if s and (s.get("ltpc") or {}).get("ltp"):
                out[k] = to_quote(s, fo)
            else:
                missing.append(k)
        return out, missing

    def quote(self, keys: list[str]) -> dict[str, dict]:
        out, missing = self._from_stream(keys)
        self.served["stream"] += len(out)
        self.served["kotak"] += len(missing)
        if missing:
            out.update(self.kotak.quote(missing))
        futs = sorted({KEY_RE.match(k[4:]).group("sym") for k in keys
                       if k.startswith("NFO:") and k.endswith("FUT") and KEY_RE.match(k[4:])})
        if out and futs and time.time() - self._last_sweep >= CHAIN_EVERY:
            self._last_sweep = time.time()
            n, cur = self.kotak.chain_calls_per_poll, self.kotak.chain_calls_per_poll
            try:
                self.kotak.chain_calls_per_poll = min(CHAIN_STOCKS, cur) if cur else 0
                self.kotak._sweep(futs)
            finally:
                self.kotak.chain_calls_per_poll = n
        for sym in futs:
            c = self.kotak._chains.get(sym)
            if c and "PCR:" + sym not in out:
                out["PCR:" + sym] = {"pcr": c["pcr"], "call_oi": c["call_oi"], "put_oi": c["put_oi"], "pcr_ts": c["ts"]}
        return out

    def quote_many(self, tradingsymbols: list[str]) -> dict[str, dict]:
        out, missing = self._from_stream(list(tradingsymbols))
        for t in list(out):                               # lot size, expiry, tradingsymbol from Kotak's scrip master
            rec = self.kotak._fo_record(t.split(":", 1)[-1])
            if rec is None:
                missing.append(t)
                del out[t]
                continue
            out[t].update({"tradingsymbol": rec["tradingsymbol"], "lot_size": rec["lot_size"], "expiry": rec["expiry"]})
        self.served["stream"] += len(out)
        self.served["kotak"] += len(missing)
        if missing:
            out.update(self.kotak.quote_many(missing))
        return out

    def quote_one(self, tradingsymbol: str) -> dict:
        got = self.quote_many([tradingsymbol])
        if tradingsymbol in got:
            return got[tradingsymbol]
        return self.kotak.quote_one(tradingsymbol)
