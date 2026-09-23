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
