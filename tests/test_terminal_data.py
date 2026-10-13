"""Data behind the trading-terminal page: Kotak's extra quote fields, the intraday tick buffer and option watch,
candles, news headlines, and quarterly results numbers (XBRL parsing, QoQ / YoY)."""
from datetime import date, datetime

import pytest

from scanner import financials as fin
from server import candles as cd
from server import live as lv
from server.kotak import _parse_quote
from server.news import News, parse, query_for

IST = lv.IST
T0 = int(datetime(2026, 10, 13, 9, 15, tzinfo=IST).timestamp())


# ---------------------------------------------------------------- Kotak quote fields
RAW = {"exchange_token": "2885", "exchange": "nse_cm", "lstup_time": "1791800993", "ltp": "1158.9000",
       "last_traded_quantity": "700", "total_buy": "24217", "total_sell": "0", "last_volume": "11338332",
       "avg_cost": "1162.1700", "open_int": "0", "year_high": "1611.8", "year_low": "0",
       "low_price_range": "1120.0000", "high_price_range": "1189.2000",
       "ohlc": {"open": "1180.3000", "high": "1185.5000", "low": "1153.2000", "close": "1170.3000"},
       "depth": {"buy": [{"price": "1158.8", "quantity": "10"}], "sell": [{"price": "1159.0", "quantity": "5"}]}}


def test_parse_quote_keeps_atp_ohlc_and_book_totals():
    q = _parse_quote(RAW, fo=False)
    assert q["atp"] == 1162.17 and q["ltq"] == 700 and q["buy_qty"] == 24217 and q["sell_qty"] == 0
    assert q["ohlc"] == {"open": 1180.3, "high": 1185.5, "low": 1153.2, "close": 1170.3}
    assert q["wk52_high"] == 1611.8 and q["wk52_low"] is None                      # "0" means no value
    assert q["upper_circuit"] == 1189.2 and q["depth"]["bid"] == [(1158.8, 10)]


def test_parse_quote_fo_has_previous_close_and_oi():
    q = _parse_quote({**RAW, "open_int": "146301000"}, fo=True)
    assert q["open_interest"] == 146301000 and q["ohlc"]["close"] == 1170.3


# ---------------------------------------------------------------- live feed: fields, ticks, option watch
class Provider:
    def __init__(self):
        self.ltp, self.calls = 100.0, []

    def quote(self, keys):
        self.calls.append(list(keys))
        out = {"NSE:ABC": {"last_price": self.ltp, "volume": 1000 + int(self.ltp), "atp": 99.5, "ltq": 5,
                           "ohlc": {"open": 98.0, "high": 101.0, "low": 97.0, "close": 98.0}, "timestamp": "x"},
               "NFO:ABC26OCTFUT": {"last_price": self.ltp + 1, "open_interest": 5000, "volume": 70, "atp": 100.4,
                                   "ohlc": {"close": 99.0}}}
        for k in keys:
            if k.endswith("CE"):
                out[k] = {"last_price": 4.0, "volume": 10, "atp": 4.1, "open_interest": 300}
        return out


def feed():
    scan = {"stocks": [{"symbol": "ABC", "close": 98.0, "fut_oi": 4800, "avg_volume_20d": 10_000, "pcr": 1.0}]}
    return lv.LiveFeed(Provider(), scan, fut_tradingsymbols={"ABC": "ABC26OCTFUT"})


def test_live_row_carries_ohlc_atp_and_future_fields():
    f = feed()
    f.poll_once(datetime(2026, 10, 13, 10, 0, tzinfo=IST))
    r = f.quotes["ABC"]
    assert (r["open"], r["high"], r["low"], r["atp"], r["ltq"]) == (98.0, 101.0, 97.0, 99.5, 5)
    assert r["chg"] == 2.0 and r["chg_pct"] == pytest.approx(2.04)
    assert r["fut_atp"] == 100.4 and r["fut_volume"] == 70 and r["fut_chg_pct"] == pytest.approx(2.02)


def test_ticks_accumulate_and_reset_on_a_new_day():
    f = feed()
    f.poll_once(datetime(2026, 10, 13, 10, 0, tzinfo=IST))
    f.provider.ltp = 101.0
    f.poll_once(datetime(2026, 10, 13, 10, 1, tzinfo=IST))
    assert [t[1] for t in f.ticks("ABC")] == [100.0, 101.0]
    f.poll_once(datetime(2026, 10, 14, 9, 15, tzinfo=IST))
    assert len(f.ticks("ABC")) == 1


def test_watched_options_are_polled_and_recorded():
    f = feed()
    f.watch_options("ABC", ["NFO:ABC26OCT100CE"])
    f.poll_once(datetime(2026, 10, 13, 10, 0, tzinfo=IST))
    assert "NFO:ABC26OCT100CE" in f.provider.calls[-1]
    assert f.option_ticks("NFO:ABC26OCT100CE")[0][1:4] == (4.0, 10, 4.1)


def test_watch_keeps_at_most_three_stocks_and_expires():
    f = feed()
    for i, s in enumerate(("A", "B", "C", "D")):
        f.watch_options(s, [f"NFO:{s}26OCT1CE"], now=1000 + i)
    assert sorted(f.watch) == ["B", "C", "D"]
    assert f.watched_keys(now=1000 + lv.WATCH_MINUTES * 60 + 2) == ["NFO:D26OCT1CE"]


# ---------------------------------------------------------------- candles
def test_candles_bucket_prices_and_difference_volume():
    ticks = [(T0 + 5, 100.0, 1000, 99.0), (T0 + 40, 102.0, 1500, 99.5), (T0 + 65, 101.0, 1800, 99.8),
             (T0 + 110, 103.0, 2600, 100.1)]
    c = cd.candles(ticks, 1)
    assert [(x["open"], x["high"], x["low"], x["close"]) for x in c] == [(100.0, 102.0, 100.0, 102.0),
                                                                          (101.0, 103.0, 101.0, 103.0)]
    assert c[0]["volume"] == 500 and c[1]["volume"] == 1100 and c[1]["atp"] == 100.1
    assert c[0]["time"] == T0 and c[1]["time"] == T0 + 60


def test_candles_after_a_gap_do_not_lump_the_gap_volume():
    c = cd.candles([(T0, 100.0, 1000, None), (T0 + 30, 100.5, 1200, None),
                    (T0 + 3600, 101.0, 90_000, None), (T0 + 3630, 101.5, 90_400, None)], 1)
    assert c[-1]["volume"] == 400


def test_candles_five_minute_and_future_columns():
    ticks = [(T0 + 60 * i, 0, 0, 0, 200.0 + i, 0, 10 * i, 201.0) for i in range(10)]
    c = cd.candles(ticks, 5, 4, 6, 7)
    assert len(c) == 2 and c[0]["close"] == 204.0 and c[1]["volume"] == 50 and c[1]["atp"] == 201.0


# ---------------------------------------------------------------- news
RSS = """<rss><channel>
<item><title>Reliance shares rise on retail growth - Business Standard</title><link>https://x/1</link>
<pubDate>Mon, 12 Oct 2026 09:30:00 GMT</pubDate><source url="https://bs">Business Standard</source></item>
<item><title>Older item - ET</title><link>https://x/2</link><pubDate>Sun, 11 Oct 2026 05:00:00 GMT</pubDate>
<source url="https://et">ET</source></item></channel></rss>"""


def test_news_parse_strips_source_and_sorts_newest_first():
    items = parse(RSS)
    assert items[0]["title"] == "Reliance shares rise on retail growth" and items[0]["source"] == "Business Standard"
    assert items[0]["published"].startswith("2026-10-12T15:00") and items[0]["ts"] > items[1]["ts"]


def test_news_query_and_cache():
    assert query_for("RELIANCE", "Reliance Industries Limited") == '"Reliance Industries" stock when:7d'
    assert query_for("M&M", None) == '"M&M" NSE share when:7d'
    calls = []
    n = News(get=lambda url: calls.append(url) or RSS)
    assert n.get("RELIANCE", "Reliance Industries Limited")["items"] and n.get("RELIANCE")["items"]
    assert len(calls) == 1


def test_news_error_is_reported_not_cached():
    def boom(url):
        raise OSError("offline")
    n = News(get=boom)
    assert n.get("ABC")["error"].startswith("OSError") and n._cache == {}


# ---------------------------------------------------------------- quarterly results
XBRL = """<xbrli:xbrl><in-capmkt:RevenueFromOperations contextRef="OneD" unitRef="INR" decimals="-5">3118500000000</in-capmkt:RevenueFromOperations>
<in-capmkt:RevenueFromOperations contextRef="FourD" unitRef="INR">9000000000000</in-capmkt:RevenueFromOperations>
<in-capmkt:ProfitLossForPeriod contextRef="OneD" unitRef="INR">231960000000.00</in-capmkt:ProfitLossForPeriod>
<in-capmkt:BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations contextRef="OneD" unitRef="INRPerShare">15.48</in-capmkt:BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations>
</xbrli:xbrl>"""
BANK = """<in-capmkt:InterestEarned contextRef="OneD">905753300000</in-capmkt:InterestEarned>
<in-capmkt:ProfitLossForThePeriod contextRef="OneD">192447100000</in-capmkt:ProfitLossForThePeriod>
<in-capmkt:BasicEarningsPerShareAfterExtraordinaryItems contextRef="OneD">12.50</in-capmkt:BasicEarningsPerShareAfterExtraordinaryItems>"""


def test_parse_xbrl_reads_the_quarter_in_crore():
    assert fin.parse_xbrl(XBRL) == {"revenue": 311850.0, "net_profit": 23196.0, "eps": 15.48}
    assert fin.parse_xbrl(BANK) == {"revenue": 90575.33, "net_profit": 19244.71, "eps": 12.5}
    assert fin.parse_xbrl("<x/>") == {"revenue": None, "net_profit": None, "eps": None}


def test_quarter_arithmetic_and_needed_quarters():
    assert fin.quarter_back("2026-06-30") == "2026-03-31" and fin.quarter_back("2026-03-31") == "2025-12-31"
    assert fin.quarter_back("2026-06-30", 4) == "2025-06-30"
    assert fin.needed("2026-06-30") == ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30",
                                        "2025-03-31", "2024-12-31"]


def test_filings_prefer_integrated_and_latest_revision():
    integ = [{"type": "Integrated Filing- Financials", "qe_Date": "30-JUN-2026", "consolidated": "Consolidated",
              "xbrl": "u1", "broadcast_Date": "17-Jul-2026 19:50:03"},
             {"type": "Integrated Filing- Financials", "qe_Date": "30-JUN-2026", "consolidated": "Consolidated",
              "xbrl": "u2", "broadcast_Date": "20-Jul-2026 10:00:00"},
             {"type": "Integrated Filing- Governance", "qe_Date": "30-JUN-2026", "xbrl": "g"}]
    old = [{"toDate": "31-Dec-2024", "consolidated": "Non-Consolidated", "cumulative": "Non-cumulative", "xbrl": "o1"},
           {"toDate": "31-Dec-2024", "consolidated": "Consolidated", "cumulative": "Cumulative", "xbrl": "o2"}]
    assert fin.filings(integ, old) == {("2026-06-30", "consolidated"): "u2", ("2024-12-31", "standalone"): "o1"}


def test_summary_qoq_yoy_and_missing_quarters():
    q = lambda r, p, e: {"revenue": r, "net_profit": p, "eps": e}                      # noqa: E731
    rec = {"basis": "consolidated", "quarters": {"2026-06-30": q(110, 12, 2.0), "2026-03-31": q(100, 10, 1.0),
                                                 "2025-12-31": q(90, -5, -1.0), "2025-06-30": q(88, 8, 1.6)}}
    s = fin.summary(rec)
    assert [r["period"] for r in s["quarters"]] == ["2026-06-30", "2026-03-31", "2025-12-31"]
    top = s["quarters"][0]
    assert top["revenue_qoq"] == 10.0 and top["revenue_yoy"] == 25.0 and top["net_profit_qoq"] == 20.0
    assert s["quarters"][1]["net_profit_qoq"] == "n/m"                     # from a loss: not meaningful
    assert s["quarters"][2]["net_profit_qoq"] is None and fin.pct(-5, 10) == -150.0
    assert s["quarters"][2]["revenue_yoy"] is None and fin.summary({}) is None


# ---------------------------------------------------------------- the intraday endpoint
def test_intraday_endpoint_returns_candles(monkeypatch):
    from fastapi.testclient import TestClient
    from server import app as app_mod
    from server.config import settings
    monkeypatch.setattr(settings, "public_access", True)
    f = feed()
    f.poll_once(datetime(2026, 10, 13, 10, 0, tzinfo=IST))
    monkeypatch.setattr(app_mod.state, "feed", f)
    c = TestClient(app_mod.app)
    r = c.get("/api/intraday/abc?tf=5").json()
    assert r["symbol"] == "ABC" and len(r["candles"]) == 1 and r["candles"][0]["close"] == 100.0
    assert c.get("/api/intraday/abc?leg=fut").json()["candles"][0]["close"] == 101.0
    assert c.get("/api/intraday/abc?tf=2").status_code == 400


class HistProvider(Provider):
    """Provider with a historical API: two 5-minute candles on any weekday."""
    def __init__(self):
        super().__init__()
        self.hist_calls = []

    def history(self, key, tf, day):
        self.hist_calls.append((key, tf, day))
        d = date.fromisoformat(day)
        if d.weekday() >= 5:
            return []
        t0 = int(datetime(d.year, d.month, d.day, 9, 15, tzinfo=IST).timestamp())
        return [{"time": t0 + i * tf * 60, "open": 90.0, "high": 91.0, "low": 89.0, "close": 90.5, "volume": 10.0,
                 "atp": None} for i in range(2)]


def _client(monkeypatch, f):
    from fastapi.testclient import TestClient
    from server import app as app_mod
    from server.config import settings
    monkeypatch.setattr(settings, "public_access", True)
    monkeypatch.setattr(app_mod.state, "feed", f)
    return TestClient(app_mod.app)


def test_intraday_without_ticks_shows_the_last_session_from_history(monkeypatch):
    scan = {"stocks": [{"symbol": "ABC", "close": 98.0, "fut_oi": 4800, "avg_volume_20d": 10_000, "pcr": 1.0}]}
    p = HistProvider()
    c = _client(monkeypatch, lv.LiveFeed(p, scan, fut_tradingsymbols={"ABC": "ABC26OCTFUT"}))
    r = c.get("/api/intraday/abc?tf=5").json()
    assert r["source"] == "history" and len(r["candles"]) == 2 and r["session"] and r["ticks"] == 0
    assert p.hist_calls[0][:2] == ("NSE:ABC", 5)


def test_intraday_late_start_is_filled_from_history(monkeypatch):
    f = lv.LiveFeed(HistProvider(), {"stocks": [{"symbol": "ABC", "close": 98.0}]},
                    fut_tradingsymbols={"ABC": "ABC26OCTFUT"})
    now = datetime.now(IST).replace(hour=11, minute=0, second=0, microsecond=0)
    if now.weekday() >= 5:
        pytest.skip("needs a weekday")
    f.poll_once(now)
    r = _client(monkeypatch, f).get("/api/intraday/abc?tf=5").json()
    assert r["source"] == "history+live" and len(r["candles"]) == 3 and r["candles"][-1]["close"] == 100.0
