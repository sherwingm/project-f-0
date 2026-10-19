"""Upstox as a live source (server/upstox.py): full quotes with depth, quote_one / quote_many, futures, history,
and the Upstox-vs-Kotak shadow check (server/provider_compare.py). No network: _get is replaced."""
import json
from datetime import datetime

from server import provider_compare as PC
from server.durable import Mirror
from server.upstox import UpstoxProvider, _parse_full

EXP_MS = int(datetime(2026, 10, 27, 15, 30).timestamp() * 1000)
ROWS = [
    {"segment": "NSE_EQ", "instrument_type": "EQ", "trading_symbol": "HCLTECH", "instrument_key": "NSE_EQ|INE860A01027"},
    {"segment": "NSE_FO", "instrument_type": "FUT", "underlying_symbol": "HCLTECH", "expiry": EXP_MS,
     "instrument_key": "NSE_FO|111", "lot_size": 350},
    {"segment": "NSE_FO", "instrument_type": "FUT", "underlying_symbol": "HCLTECH",
     "expiry": int(datetime(2026, 11, 24, 15, 30).timestamp() * 1000), "instrument_key": "NSE_FO|112", "lot_size": 350},
    {"segment": "NSE_FO", "instrument_type": "CE", "underlying_symbol": "HCLTECH", "expiry": EXP_MS,
     "strike_price": 1350.0, "instrument_key": "NSE_FO|201", "lot_size": 350},
    {"segment": "NSE_FO", "instrument_type": "PE", "underlying_symbol": "HCLTECH", "expiry": EXP_MS,
     "strike_price": 1350.0, "instrument_key": "NSE_FO|202", "lot_size": 350},
]


def full(key, ltp, bid, ask, oi=None, vol=7000):
    return {"instrument_token": key, "last_price": ltp, "volume": vol, "average_price": ltp - 0.2, "oi": oi,
            "net_change": 1.5, "last_trade_time": "1792390000000", "total_buy_quantity": 9000, "total_sell_quantity": 8000,
            "lower_circuit_limit": 0.05, "upper_circuit_limit": 99.0, "ohlc": {"open": ltp - 1, "high": ltp + 2, "low": ltp - 3, "close": ltp},
            "depth": {"buy": [{"price": bid - 0.05, "quantity": 700, "orders": 2}, {"price": bid, "quantity": 350, "orders": 1},
                              {"price": 0, "quantity": 0, "orders": 0}],
                      "sell": [{"price": ask, "quantity": 1050, "orders": 3}, {"price": ask + 0.1, "quantity": 350, "orders": 1}]}}


class Fake(UpstoxProvider):
    def __init__(self):
        super().__init__("token-not-used", chain_calls_per_poll=0)
        self._ingest_instruments(ROWS)
        self.calls = []
        self.book = {"NSE_FO|201": full("NSE_FO|201", 18.35, 18.3, 18.4, oi=350000),
                     "NSE_FO|202": full("NSE_FO|202", 22.0, 21.9, 22.1, oi=280000),
                     "NSE_FO|111": full("NSE_FO|111", 1331.0, 1330.9, 1331.2, oi=9_000_000),
                     "NSE_EQ|INE860A01027": full("NSE_EQ|INE860A01027", 1326.0, 1325.9, 1326.1)}

    def _get(self, path, params, base=None):
        self.calls.append((base, path, dict(params)))
        if path == "/market-quote/quotes":
            keys = params["instrument_key"].split(",")
            return {f"x:{k}": self.book[k] for k in keys if k in self.book}
        if "historical-candle" in path:
            return {"candles": [["2026-10-16T09:16:00+05:30", 10, 11, 9.5, 10.5, 3500, 1],
                                ["2026-10-16T09:15:00+05:30", 9, 10.2, 8.9, 10, 7000, 1]]}
        raise AssertionError(path)


def test_full_quote_has_depth_atp_and_previous_close():
    q = _parse_full(full("NSE_FO|201", 18.35, 18.3, 18.4, oi=350000), fo=True)
    assert q["depth"] == {"bid": [(18.3, 350), (18.25, 700)], "ask": [(18.4, 1050), (18.5, 350)]}   # best first, empty dropped
    assert round(q["atp"], 2) == 18.15 and q["open_interest"] == 350000 and q["volume"] == 7000
    assert q["ohlc"]["close"] == 16.85 and q["timestamp"].startswith("2026-")


def test_quote_many_is_one_call_with_lot_and_expiry():
    p = Fake()
    got = p.quote_many(["HCLTECH26OCT1350CE", "NFO:HCLTECH26OCT1350PE", "HCLTECH26OCT9999CE"])
    assert len(p.calls) == 1 and set(p.calls[0][2]["instrument_key"].split(",")) == {"NSE_FO|201", "NSE_FO|202"}
    ce = got["HCLTECH26OCT1350CE"]
    assert ce["lot_size"] == 350 and ce["expiry"] == "2026-10-27" and ce["tradingsymbol"] == "HCLTECH26OCT1350CE"
    assert ce["depth"]["ask"][0] == (18.4, 1050) and "NFO:HCLTECH26OCT1350PE" in got and "HCLTECH26OCT9999CE" not in got
    assert p.quote_one("HCLTECH26OCT1350CE")["last_price"] == 18.35


def test_feed_quote_gives_kotak_shape_for_equity_future_and_option():
    p = Fake()
    out = p.quote(["NSE:HCLTECH", "NFO:HCLTECH26OCTFUT", "NFO:HCLTECH26OCT1350CE"])
    assert out["NSE:HCLTECH"]["depth"]["bid"][0] == (1325.9, 350) and "open_interest" not in out["NSE:HCLTECH"]
    assert out["NFO:HCLTECH26OCTFUT"]["open_interest"] == 9_000_000
    assert out["NFO:HCLTECH26OCT1350CE"]["depth"]["ask"][0] == (18.4, 1050)


def test_futures_lists_live_contracts_nearest_first():
    assert Fake().futures(["HCLTECH", "XYZ"], today="2026-10-19") == {"HCLTECH": ["HCLTECH26OCTFUT", "HCLTECH26NOVFUT"]}


def test_history_past_day_uses_v3_range_and_sorts_oldest_first():
    p = Fake()
    c = p.history("NFO:HCLTECH26OCT1350CE", 1, "2026-10-16")
    base, path, _ = p.calls[-1]
    assert base.endswith("/v3") and path == "/historical-candle/NSE_FO%7C201/minutes/1/2026-10-16/2026-10-16"
    assert [x["open"] for x in c] == [9.0, 10.0] and c[0]["volume"] == 7000.0 and c[0]["atp"] is None
    p.history("NFO:HCLTECH26OCT1350CE", 1, "2026-10-16")
    assert len(p.calls) == 1                                              # a past day is cached
    assert p.history("NSE:NOPE", 1, "2026-10-16") == []


# ---------------------------------------------------------------- the shadow check
class Side:
    def __init__(self, book):
        self.book = book

    def quote_many(self, names):
        return {n: self.book[n] for n in names if n in self.book}


def q(ltp, bid, ask, vol, oi, ts):
    return {"last_price": ltp, "depth": {"bid": [(bid, 100)], "ask": [(ask, 200)]}, "volume": vol,
            "open_interest": oi, "atp": ltp, "timestamp": ts}


def test_compare_round_and_day_file(tmp_path):
    k = Side({"A": q(10.0, 9.95, 10.05, 1000, 50, "2026-10-19 10:00:00"), "B": q(20.0, 19.9, 20.1, 500, 70, "2026-10-19 10:00:00"),
              "C": q(5.0, 4.9, 5.1, 10, 1, "2026-10-19 10:00:00")})
    u = Side({"A": q(10.05, 9.95, 10.05, 1000, 50, "2026-10-19 10:00:01"), "B": q(20.0, 19.9, 20.15, 1000, 70, "2026-10-19 10:00:02")})
    c = PC.ProviderCompare(tmp_path, k, u, lambda i: ["A", "B", "C"])
    doc = c.run_once(datetime(2026, 10, 19, 10, 0, 5))
    r = doc["rounds"][0]
    assert r["on_both"] == 2 and r["missing_upstox"] == ["C"] and r["same_best_bid_pct"] == 100.0 and r["same_best_ask_pct"] == 50.0
    assert r["ltp_gap_pct_max"] == 0.5 and r["volume_ratio_median"] == 1.5 and r["oi_same_pct"] == 100.0
    assert r["upstox_minus_kotak_quote_time_s_median"] == 1.5 and doc["top_gaps"][0]["contract"] == "A"
    c.run_once(datetime(2026, 10, 19, 10, 5, 5))
    saved = json.loads((tmp_path / "provider_compare" / "2026-10-19.json").read_text())
    assert saved["day"]["rounds"] == 2 and saved["day"]["contract_quotes"] == 4


def test_the_mirror_carries_the_compare_files(tmp_path):
    (tmp_path / "provider_compare").mkdir()
    (tmp_path / "provider_compare" / "2026-10-19.json").write_text("{}")
    assert "provider_compare/2026-10-19.json" in Mirror(tmp_path, store=None)._names()


def test_instrument_rows_are_streamed_across_chunk_edges():
    import io
    from server.upstox import _stream_rows
    text = json.dumps(ROWS + [{"segment": "NSE_COM", "x": "]}[,"}])
    for size in (1, 7, 64, 10_000):                                 # rows split at every possible point
        assert list(_stream_rows(io.StringIO(text), chunk=size)) == ROWS + [{"segment": "NSE_COM", "x": "]}[,"}]
    assert list(_stream_rows(io.StringIO("[]"))) == [] and list(_stream_rows(io.StringIO(""))) == []
