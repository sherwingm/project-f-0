"""Step 1: 5-level depth passes from the provider through the live feed."""
import pytest

from server.kotak import KotakSession, _raise_if_error
from server.live import FakeProvider, LiveFeed
from tests.fakes import EXPIRY, kotak_provider

SCAN = {"stocks": [{"symbol": "RELIANCE", "close": 1226.4, "fut_oi": 12_000_000}]}


def test_kotak_depth_reaches_the_feed_snapshot():
    provider, _ = kotak_provider()
    feed = LiveFeed(provider, SCAN, fut_tradingsymbols={"RELIANCE": "RELIANCE26SEPFUT"})
    feed.poll_once()
    q = feed.snapshot()["quotes"]["RELIANCE"]

    assert isinstance(q["fut_depth"]["ask"][0], tuple)
    # best level first on both sides, floats and ints, even when Kotak lists them out of order
    assert q["fut_depth"]["ask"] == [(1248.2, 500), (1248.25, 750), (1248.3, 2000)]
    assert q["fut_depth"]["bid"] == [(1248.0, 1000), (1247.9, 1500)]
    assert q["depth"]["bid"] == [(1243.85, 1733), (1243.8, 900)]          # the empty level is dropped
    assert q["depth"]["ask"][0] == (1243.95, 550)
    assert all(isinstance(p, float) and isinstance(n, int) for p, n in q["depth"]["bid"] + q["fut_depth"]["ask"])
    assert q["fut_tradingsymbol"] == "RELIANCE26SEPFUT"
    assert q["fut_oi"] == 12345678 and q["ltp"] == 1243.9


def test_depth_is_capped_at_five_levels():
    from server.kotak import _depth
    raw = {"buy": [{"price": str(100 - i), "quantity": "10"} for i in range(8)], "sell": []}
    d = _depth(raw)
    assert len(d["bid"]) == 5 and d["bid"][0] == (100.0, 10) and d["ask"] == []


def test_quote_one_resolves_an_option_via_the_scrip_master():
    provider, fake = kotak_provider()
    q = provider.quote_one("RELIANCE26SEP1300CE")
    assert q["depth"] == {"bid": [(4.05, 1500)], "ask": [(4.2, 2000)]}
    assert q["open_interest"] == 2500000 and q["last_price"] == 4.1
    assert q["lot_size"] == 500 and q["expiry"] == EXPIRY
    assert fake.calls[-1] == [{"instrument_token": "40001", "exchange_segment": "nse_fo"}]
    assert provider.quote_one("NFO:RELIANCE26SEPFUT")["depth"]["ask"][0] == (1248.2, 500)


def test_quote_one_unknown_contract_raises():
    provider, _ = kotak_provider()
    with pytest.raises(ValueError):
        provider.quote_one("RELIANCE26SEP9999CE")


def test_fake_provider_emits_synthetic_depth():
    provider = FakeProvider({"RELIANCE": 1226.4}, {"RELIANCE": 12_000_000}, {"RELIANCE": 500})
    feed = LiveFeed(provider, SCAN, fut_tradingsymbols={"RELIANCE": "RELIANCE26SEPFUT"})
    feed.poll_once()
    q = feed.snapshot()["quotes"]["RELIANCE"]
    for d in (q["depth"], q["fut_depth"]):
        assert len(d["bid"]) == 5 and len(d["ask"]) == 5
        assert isinstance(d["ask"][0], tuple)
        assert d["bid"][0][0] < d["ask"][0][0]
        assert [p for p, _ in d["ask"]] == sorted(p for p, _ in d["ask"])
    assert q["fut_depth"]["ask"][0][1] % 500 == 0                      # quantities in whole lots
    opt = provider.quote_one("RELIANCE26SEP1300CE")
    assert opt["depth"]["bid"][0][0] < opt["depth"]["ask"][0][0] and opt["lot_size"] == 500


def test_kotak_error_messages_never_carry_the_key():
    KotakSession("super-secret-consumer-key")
    with pytest.raises(RuntimeError) as exc:
        _raise_if_error({"error": True, "message": "Consumer key 'super-secret-consumer-key' is invalid. "}, "quotes")
    assert "super-secret-consumer-key" not in str(exc.value) and "<redacted>" in str(exc.value)


def test_quote_batches_stay_under_kotaks_limit():
    from server.kotak import QUOTE_BATCH
    provider, fake = kotak_provider()
    toks = [{"instrument_token": str(i), "exchange_segment": "nse_cm"} for i in range(120)]
    fake.book.update({t["instrument_token"]: {"exchange_token": t["instrument_token"], "exchange": "nse_cm"} for t in toks})
    provider.master.eq.update({f"S{i}": {"token": str(i)} for i in range(120)})
    provider.quote([f"NSE:S{i}" for i in range(120)])
    assert QUOTE_BATCH == 49 and fake.calls and max(len(c) for c in fake.calls) <= 49


LIVE_CHAIN = {  # the live option_chain shape (2026-09-28): top-level call/put, short keys, strings
    "common_data": {"mktLot": "500", "multiplier": "1", "expiryDt": "2026-09-29", "unlSymbol": "RELIANCE", "exSeg": "nse_fo"},
    "call": [{"inst": {"neoSymbol": "nse_fo|1", "symbol": "RELIANCE26SEP1200CE", "optType": "CE", "strkPrc": "1200"},
              "quote": {"ltp": "9.5", "pc": "20.1", "vol": "1500"}, "oi": {"cur": "2000000", "prev": "1800000", "chg": "200000"}}],
    "put": [{"inst": {"neoSymbol": "nse_fo|2", "symbol": "RELIANCE26SEP1200PE", "optType": "PE", "strkPrc": "1200"},
             "quote": {"ltp": "6.7", "pc": "3.2", "vol": "900"}, "oi": {"cur": "1500000", "prev": "1600000", "chg": "-100000"}}],
    "future_contracts": [], "spot": {}, "future": {}}


@pytest.mark.parametrize("shape", ["live", "documented"])
def test_option_chain_parses_the_live_and_the_documented_shape(shape):
    provider, fake = kotak_provider()
    if shape == "live":
        resp = LIVE_CHAIN
    else:
        long = lambda leg: {"instrument": leg["inst"], "quote": {"ltp": leg["quote"]["ltp"], "prevClose": leg["quote"]["pc"],
                                                                  "volume": leg["quote"]["vol"]},
                            "openInterest": {"current": leg["oi"]["cur"], "previous": leg["oi"]["prev"], "change": leg["oi"]["chg"]}}
        resp = {"data": {"common_data": LIVE_CHAIN["common_data"], "call": [long(LIVE_CHAIN["call"][0])],
                         "put": [long(LIVE_CHAIN["put"][0])]}}
    fake.option_chain = lambda **kw: resp
    c = provider._fetch_chain("RELIANCE", EXPIRY)
    assert (c["call_oi"], c["put_oi"], c["pcr"], c["lot_size"], c["expiry"]) == (2000000, 1500000, 0.75, 500, "2026-09-29")
    ce = c["strikes"]["RELIANCE26SEP1200CE"]
    assert (ce["last_price"], ce["open_interest"], ce["prev_oi"], ce["oi_change"], ce["volume"], ce["prev_close"]) == \
        (9.5, 2000000, 1800000, 200000, 1500, 20.1)


def test_option_chain_calls_are_spaced(monkeypatch):
    from server import kotak
    provider, fake = kotak_provider()
    fake.option_chain = lambda **kw: LIVE_CHAIN
    t = {"now": 100.0}
    sleeps = []
    monkeypatch.setattr(kotak.time, "monotonic", lambda: t["now"])
    monkeypatch.setattr(kotak.time, "sleep", lambda s: (sleeps.append(round(s, 3)), t.__setitem__("now", t["now"] + s)))
    monkeypatch.setattr(provider.limiter, "wait", lambda: None)
    for _ in range(3):
        provider._fetch_chain("RELIANCE", EXPIRY)
        t["now"] += 0.25                                   # each call takes 0.25 s
    assert sleeps == [0.75, 0.75] and kotak.CHAIN_MIN_INTERVAL == 1.0
