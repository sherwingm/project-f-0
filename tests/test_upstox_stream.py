"""server/upstox_stream.py: the protobuf decoder, the quote shape, and the Kotak fallback (DECISIONS.md 2026-10-22)."""
import struct
import time

from server import upstox_stream as U
from server.live import LiveFeed


# ---------------------------------------------------------------- a tiny protobuf encoder for the tests
def _v(n: int) -> bytes:
    out = b""
    while True:
        b, n = n & 0x7F, n >> 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def vi(f, n):
    return _v(f << 3) + _v(n)


def db(f, x):
    return _v(f << 3 | 1) + struct.pack("<d", x)


def ln(f, b):
    return _v(f << 3 | 2) + _v(len(b)) + b


def market_ff(ltp, ltt, cp, depth, open_, atp, vtt, oi):
    ltpc = db(1, ltp) + vi(2, ltt) + vi(3, 50) + db(4, cp)
    level = b"".join(ln(1, vi(1, bq) + db(2, bp) + vi(3, aq) + db(4, ap)) for bp, bq, ap, aq in depth)
    ohlc = ln(1, ln(1, b"1d") + db(2, open_) + db(3, ltp + 1) + db(4, open_ - 1) + db(5, ltp))
    return ln(1, ltpc) + ln(2, level) + ln(4, ohlc) + db(5, atp) + vi(6, vtt) + db(7, oi)


def response(feeds: dict[str, bytes], typ=1) -> bytes:
    body = vi(1, typ)
    for k, mff in feeds.items():
        feed = ln(2, ln(1, mff))                                   # Feed.fullFeed -> FullFeed.marketFF
        body += ln(2, ln(1, k.encode()) + ln(2, feed))
    return body + vi(3, 1761100000000)


LTT = int(time.mktime((2026, 10, 23, 9, 15, 1, 0, 0, -1)) * 1000)


def test_decode_full_feed_into_kotaks_quote_shape():
    msg = response({"NSE_FO|49081": market_ff(18.5, LTT, 17.2, [(18.0, 700, 18.5, 350), (17.9, 1400, 18.6, 700)],
                                               16.0, 18.1, 12_250, 4_550_000)})
    typ, parts = U.decode(msg)
    assert typ == 1 and list(parts) == ["NSE_FO|49081"]
    q = U.to_quote(parts["NSE_FO|49081"], fo=True)
    assert q["last_price"] == 18.5 and q["volume"] == 12_250 and q["open_interest"] == 4_550_000
    assert q["depth"] == {"bid": [(18.0, 700), (17.9, 1400)], "ask": [(18.5, 350), (18.6, 700)]}
    assert q["ohlc"]["open"] == 16.0 and q["ohlc"]["close"] == 17.2 and q["atp"] == 18.1 and q["ltq"] == 50


class FakeLive:
    def __init__(self):
        self.ok, self.state, self.wanted = True, {}, set()

    def want(self, keys):
        self.wanted |= set(keys)

    def get(self, k):
        return self.state.get(k)

    def healthy(self):
        return self.ok


class FakeUpstox:
    _loaded = True
    _eq = {"RELIANCE": {"key": "NSE_EQ|INE002A01018"}}

    def _fo_key(self, p):
        return {"key": "NSE_FO|1", "expiry": "2026-10-27", "lot_size": 500} if p["sym"] == "RELIANCE" else None


class FakeKotak:
    chain_calls_per_poll, _chains = 12, {}

    def __init__(self):
        self.asked = []

    def quote(self, keys):
        self.asked += keys
        return {k: {"last_price": 1.0, "source": "kotak"} for k in keys}

    def quote_many(self, ts):
        self.asked += ts
        return {t: {"last_price": 2.0, "source": "kotak"} for t in ts}

    def _fo_record(self, ts):
        return {"tradingsymbol": ts, "lot_size": 500, "expiry": "2026-10-27"}

    def _sweep(self, syms):
        pass

    def history(self, *a):
        return "kotak history"


def provider():
    live, kotak = FakeLive(), FakeKotak()
    return U.StreamingProvider(kotak, FakeUpstox(), live), live, kotak


def test_streamed_contracts_come_from_the_stream_the_rest_from_kotak():
    p, live, kotak = provider()
    live.state["NSE_EQ|INE002A01018"] = {"ltpc": {"ltp": 1300.5, "cp": 1290.0}}
    out = p.quote(["NSE:RELIANCE", "NSE:UNKNOWN"])
    assert out["NSE:RELIANCE"]["source"] == "upstox_stream" and out["NSE:RELIANCE"]["last_price"] == 1300.5
    assert kotak.asked == ["NSE:UNKNOWN"] and "NSE_EQ|INE002A01018" in live.wanted
    assert p.history("x") == "kotak history"                                   # everything else is Kotak's


def test_options_carry_kotaks_lot_and_expiry_and_a_down_stream_falls_back():
    p, live, kotak = provider()
    live.state["NSE_FO|1"] = {"ltpc": {"ltp": 18.5}, "depth": [(18.0, 500, 18.5, 500)]}
    q = p.quote_one("RELIANCE26OCT1300CE")
    assert q["source"] == "upstox_stream" and q["lot_size"] == 500 and q["depth"]["ask"] == [(18.5, 500)]
    live.ok = False                                                            # no message for 15 s: Kotak
    assert p.quote_one("RELIANCE26OCT1300CE")["source"] == "kotak" and not p.streaming()


def test_the_feed_runs_every_second_only_while_streaming():
    p, live, _ = provider()
    f = LiveFeed(p, {"stocks": []}, 30, {}, fast_seconds=1)
    assert f.interval() == 1
    live.ok = False
    assert f.interval() == 30
