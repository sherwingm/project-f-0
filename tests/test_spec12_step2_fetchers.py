"""Spec 12 step 2: every fetcher parses its fixture into normalised RawItems; no network in tests."""
from datetime import date

import pytest

from scanner.events.sources import bse_announcements, nse_announcements, nse_ban, nse_deals, nse_pit, rss
from scanner.events.sources import parse_nse_ts

DAY = date(2026, 9, 22)


def test_parse_nse_timestamps():
    assert parse_nse_ts("22-Sep-2026 23:58:18") == ("2026-09-22", "23:58")
    assert parse_nse_ts("22-Sep-2026") == ("2026-09-22", None)
    assert parse_nse_ts(None) == (None, None) and parse_nse_ts("garbage") == (None, None)


def test_nse_announcements_fixture():
    items = nse_announcements.fetch(DAY, fixture="nse_announcements.json")
    assert len(items) >= 30
    one = items[0]
    for k in ("source", "source_id", "symbol", "event_date", "category", "subject", "url", "extra"):
        assert k in one
    assert one["source"] == "nse_ann" and one["event_date"].startswith("2026-09-2")
    assert all(i["symbol"] == i["symbol"].upper() and i["symbol"] for i in items)
    cats = {i["category"] for i in items}
    assert "Credit Rating" in cats and len({i["source_id"] for i in items}) == len(items)


def test_nse_deals_fixture_block_and_bulk():
    block = nse_deals.fetch(DAY, fixture="nse_block_deals.json", kind="block")
    assert block and block[0]["source"] == "nse_block"
    b = block[0]
    assert b["extra"]["side"] in ("BUY", "SELL") and b["extra"]["quantity"] > 0 and b["extra"]["price"] > 0
    assert b["extra"]["client"] and b["event_date"] == "2026-09-22"
    bulk = nse_deals.fetch(DAY, fixture="nse_bulk_deals.json", kind="bulk")
    assert bulk and bulk[0]["source"] == "nse_bulk"
    assert len({i["source_id"] for i in block + bulk}) == len(block) + len(bulk)
    with pytest.raises(ValueError):
        nse_deals.fetch(DAY, kind="nope")


def test_nse_ban_fixture():
    items = nse_ban.fetch(DAY, fixture="nse_ban.csv")
    assert [i["symbol"] for i in items] == ["BANDHANBNK", "INOXWIND", "LICHSGFIN", "MANAPPURAM", "SAIL"]
    assert all(i["event_date"] == "2026-09-22" and i["extra"]["in_ban"] for i in items)


def test_nse_pit_fixture():
    items = nse_pit.fetch(DAY, fixture="nse_pit.json")
    assert len(items) == 2
    buy = next(i for i in items if i["symbol"] == "RELIANCE")
    assert buy["extra"]["person_category"] == "Promoters" and buy["extra"]["side"] == "BUY"
    assert buy["extra"]["quantity"] == 500000 and buy["extra"]["pct_traded"] == 0.07
    assert buy["extra"]["value"] == 625000000.0                    # commas stripped
    sell = next(i for i in items if i["symbol"] == "TCS")
    assert sell["extra"]["side"] == "SELL" and sell["event_date"] == "2026-09-22"


def test_bse_announcements_map_and_drop(tmp_path):
    mapping = bse_announcements.build_map(path=tmp_path / "map.csv",
                                          bse_fixture="bse_master.json", nse_fixture="nse_equity_l.csv")
    assert mapping == {"500325": "RELIANCE", "532540": "TCS"}      # the BSE-only ISIN is unmapped
    assert bse_announcements.load_map(tmp_path / "map.csv") == mapping
    items = bse_announcements.fetch(DAY, fixture="bse_announcements.json", mapping=mapping)
    assert len(items) == 1 and bse_announcements.fetch.last_dropped == 1
    one = items[0]
    assert one["symbol"] == "RELIANCE" and one["source"] == "bse_ann" and one["event_time"] == "18:30"
    assert one["extra"]["subcategory"].startswith("Award of Order") and one["url"].endswith("abc1.pdf")


def test_rss_fixture_dates_and_tier3_shape():
    items = rss.fetch(date(2026, 9, 24), fixture="rss_et.xml", feed="et_markets")
    assert items and all(i["source"] == "rss:et_markets" and i["symbol"] is None for i in items)
    assert all("2026-09" in i["event_date"] for i in items)
    assert rss.fetch(date(2026, 11, 1), fixture="rss_et.xml") == []          # stale items age out
    assert rss.fetch(date(2026, 9, 24), fixture="rss_bs.xml", feed="business_standard")
    assert list(rss.backfill(date(2026, 1, 1), date(2026, 2, 1))) == []      # no RSS archive


def test_backfill_chunking_is_range_based(monkeypatch):
    calls = []
    monkeypatch.setattr(nse_announcements, "fetch", lambda a, http=None, until=None, **k: calls.append((a, until)) or [])
    list(nse_announcements.backfill(date(2026, 1, 1), date(2026, 1, 20), http=object()))
    assert calls == [(date(2026, 1, 1), date(2026, 1, 7)), (date(2026, 1, 8), date(2026, 1, 14)),
                     (date(2026, 1, 15), date(2026, 1, 20))]
