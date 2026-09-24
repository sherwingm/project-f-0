"""Event data quality: insider dates, results detection and dedupe, the deals row cap, rating drop reasons.
Every case is taken from a real NSE row seen while checking the back-fill."""
import json
from datetime import date

import pytest

from scanner.events import run as run_mod
from scanner.events.sources import nse_deals, nse_pit
from scanner.events.store import Store
from scanner.events.taxonomy import classify


class Http:
    """get_json answers from a function of the URL; records every URL asked."""
    def __init__(self, answer):
        self.answer, self.urls = answer, []

    def get_json(self, url, referer):
        self.urls.append(url)
        return self.answer(url)


# ---------------------------------------------------------------- a) insider dates
def pit_row(**over):
    r = {"symbol": "DMART", "acqName": "Hitesh Bachubhai Shah", "personCategory": "-", "secAcq": "800",
         "secVal": "3,20,000", "tdpTransactionType": "Sell", "befAcqSharesPer": "0.01", "afterAcqSharesPer": "0.00",
         "date": "23-Jan-2025 18:21", "intimDt": "23-Jan-1925"}
    r.update(over)
    return r


def test_insider_date_is_the_broadcast_time_not_the_typed_intimation():
    rows = [pit_row(), pit_row(symbol="SOLARINDS", date="11-Mar-2026 15:17", intimDt="10-Nov-2026"),
            pit_row(symbol="X", date=None, intimDt="23-Jan-1925")]                  # nothing plausible: dropped
    items = nse_pit.fetch(date(2025, 1, 20), Http(lambda u: {"data": rows}), until=date(2025, 2, 18))
    assert [(i["symbol"], i["event_date"], i["event_time"]) for i in items] == [
        ("DMART", "2025-01-23", "18:21"), ("SOLARINDS", "2026-03-11", "15:17")]
    assert items[0]["extra"]["pct_before"] == 0.01 and items[0]["extra"]["intimated"] == "23-Jan-1925"


# ---------------------------------------------------------------- b) results
def ann(category, subject, symbol="NTPC", day="2025-01-25", sid="1"):
    return {"source": "nse_ann", "source_id": sid, "symbol": symbol, "event_date": day, "event_time": "18:00",
            "category": category, "subject": subject, "text": subject, "url": "", "extra": {}}


@pytest.mark.parametrize("category,subject,expected", [
    ("Financial Result Updates", "NTPC Limited has submitted to the Exchange, the financial results for the period "
                                 "ended December 31, 2024.", "results"),
    ("Outcome of Board Meeting", "JSW Steel Limited has submitted to the Exchange, the financial results for the "
                                 "period ended Jun 30, 2025.", "results"),
    ("Outcome of Board Meeting", "Indus Towers Limited has informed the Exchange regarding Outcome of the Board "
                                 "Meeting pertaining to Financial Results for the third quarter", "results"),
    ("Clarification - Financial Results", "The Exchange had sought clarification from NTPC Limited for the quarter "
                                          "ended 30-Jun-2023 with respect to Regulation 33", None),
    ("Integrated Filing- Financial", "Integrated filing - Financial results for quarter ended 31st Dec 2024", None),
    ("Press Release", "a press release titled \"Unaudited Financial Results\"", None),
    ("Board Meeting Intimation", "Board meeting to be held on 30 January 2025 to consider financial results", "results_date"),
])
def test_results_categories(category, subject, expected):
    e = classify(ann(category, subject))
    assert (e or {}).get("type") == expected


def test_one_results_event_per_stock_across_filings_and_nearby_days(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod, "STATUS_PATH", tmp_path / "s.json")
    monkeypatch.setattr(run_mod, "RATING_DROPS_PATH", tmp_path / "drops.jsonl")
    store = Store(tmp_path / "events.sqlite")
    r = run_mod.Runner(store=store, universe={"NTPC", "DLF"}, fixtures=True)
    events = [classify(ann("Outcome of Board Meeting", "submitted to the Exchange, the financial results", sid="a")),
              classify(ann("Financial Result Updates", "the financial results for the period", sid="b")),
              classify(ann("Financial Result Updates", "the financial results", day="2025-01-27", sid="c")),
              classify(ann("Financial Result Updates", "the financial results", symbol="DLF", sid="d"))]
    r._settle(events)
    r._settle([classify(ann("Financial Result Updates", "the financial results", day="2025-01-28", sid="e"))])
    r._settle([classify(ann("Financial Result Updates", "the financial results", day="2025-04-25", sid="f"))])
    got = sorted((e["symbol"], e["event_date"]) for e in store.all_of_type("results"))
    assert got == [("DLF", "2025-01-25"), ("NTPC", "2025-01-25"), ("NTPC", "2025-04-25")]


# ---------------------------------------------------------------- c) deals row cap
def test_deals_split_any_answer_at_the_row_cap(monkeypatch):
    per_day = {date(2025, 3, d): n for d, n in ((3, 30), (4, 40), (5, 45), (6, 0), (7, 70))}

    def answer(url):
        a, b = (date(int(x[6:10]), int(x[3:5]), int(x[:2])) for x in (url.split("from=")[1][:10], url.split("to=")[1][:10]))
        rows = [{"BD_DT_DATE": d.strftime("%d-%b-%Y").upper(), "BD_SYMBOL": "ABC", "BD_CLIENT_NAME": f"C{i}",
                 "BD_BUY_SELL": "BUY", "BD_QTY_TRD": 100 + i, "BD_TP_WATP": 10} for d, n in per_day.items() if a <= d <= b
                for i in range(n)]
        return {"data": rows[:nse_deals.ROW_CAP]}                           # the endpoint's silent cap

    http = Http(answer)
    items = nse_deals.fetch(date(2025, 3, 3), http, kind="bulk", until=date(2025, 3, 7))
    assert len(items) == 30 + 40 + 45 + 70                                  # everything, the 70-row day included
    assert len(http.urls) > 1
    assert nse_deals.BACKFILL_CHUNK_DAYS == {"block": 30, "bulk": 1}


# ---------------------------------------------------------------- d) rating drop reasons
def test_rating_drops_are_logged_with_a_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod, "STATUS_PATH", tmp_path / "s.json")
    monkeypatch.setattr(run_mod, "RATING_DROPS_PATH", tmp_path / "drops.jsonl")
    r = run_mod.Runner(store=Store(tmp_path / "events.sqlite"), universe={"SBIN"}, fixtures=True)
    base = classify(ann("Credit Rating", "State Bank Of India has informed the Exchange about Credit Rating", symbol="SBIN"))
    assert base["subtype"] == "unverified"
    cases = [({**base, "url": ""}, None, -1),
             ({**base, "url": "x.pdf"}, None, -1),
             ({**base, "url": "x.pdf"}, "", 5),
             ({**base, "url": "x.pdf"}, "Moody's Investors Service has upgraded the Bank's rating", 5),
             ({**base, "url": "x.pdf"}, "CRISIL has reaffirmed its rating on the bonds", 5)]
    kept = []
    for e, text, budget in cases:
        monkeypatch.setattr(r, "_page1", lambda e, b, text=text: text)
        kept.append(r._finalise(dict(e, raw_json={}), budget))
    reasons = [json.loads(l)["reason"] for l in (tmp_path / "drops.jsonl").read_text().splitlines()]
    assert reasons == ["no PDF attachment", "attachment not read (no --rating-attachments pass / budget spent)",
                       "page 1 has no extractable text (scanned image)",
                       "page 1 names no SEBI-registered CRA (names Moody's)"]
    assert kept[-1]["subtype"] == "reaffirm" and kept[:4] == [None] * 4


# ---------------------------------------------------------------- board meetings -> results_date
def test_board_meetings_become_dated_results_meetings():
    from scanner.events.sources import nse_board_meetings as bm
    items = bm.fetch(date(2026, 9, 22), fixture="nse_board_meetings.json")
    by = {i["symbol"]: i for i in items}
    assert len(items) == 3 and by["HDFCBANK"]["subject"].startswith("Revised")     # the later intimation wins
    events = {i["symbol"]: classify(i) for i in items}
    hd = events["HDFCBANK"]
    assert (hd["type"], hd["subtype"], hd["event_date"], hd["id"]) == ("results_date", "scheduled", "2026-10-18",
                                                                        "nse_bm:HDFCBANK:2026-10-18")
    assert events["INFY"]["type"] == "results_date" and events["INFY"]["event_date"] == "2026-10-15"
    assert events["ITC"] is None                                                      # fund raising: not results


# ---------------------------------------------------------------- order-win values and shares
@pytest.mark.parametrize("text,largest,first", [
    ("bagged orders worth Rs. 1,234.5 crore", 1234.5, 1234.5),
    ("an order of ₹ 500 Cr. taking the order book to Rs 20,000 crore", 20000.0, 500.0),
    ("Rs.500/- crores", 500.0, 500.0),
    ("INR 2,500 million", 250.0, 250.0),
    ("orders worth 1,200 crore from NTPC", 1200.0, 1200.0),
    ("Rs 50 lakh", 0.5, 0.5),
    ("USD 100 million", None, None),
])
def test_value_parsing(text, largest, first):
    from scanner.events.score import parse_value_cr
    assert parse_value_cr(text) == largest and parse_value_cr(text, first=True) == first


def test_shares_from_the_market_cap_file():
    import io
    import zipfile
    from scanner.events.score import shares_from_mcap_file
    csv_text = ("Trade Date,Symbol,Series,Security Name,Category,Last Trade Date,Face Value(Rs.),Issue Size,"
                "Close Price/Paid up value(Rs.),Market Cap(Rs.)              \n"
                "24 SEP 2026,RELIANCE,EQ,RELIANCE IND ,Listed ,24 SEP 2026, 10.00,   13532538722, 1219.20, 1.6e13 \n"
                "24 SEP 2026,SOMEBOND,N1,BOND ,Listed ,24 SEP 2026, 1000.00,   500, 1000, 5e5 \n")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mcap24092026.csv", csv_text)

    class R:
        def __init__(self, code, content=b""):
            self.status_code, self.content = code, content

    urls = []
    got = shares_from_mcap_file(date(2026, 9, 26), get=lambda u: urls.append(u) or (R(200, buf.getvalue()) if "PR240926" in u else R(404)))
    assert got == {"RELIANCE": 13532538722.0} and urls[-1].endswith("PR240926.zip") and len(urls) == 2


def test_backfill_reads_order_values_from_page_one_only_when_asked(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod, "STATUS_PATH", tmp_path / "s.json")
    r = run_mod.Runner(store=Store(tmp_path / "events.sqlite"), universe={"LT"}, fixtures=False)
    e = classify(ann("Updates", "Larsen & Toubro has informed the Exchange about an order win", symbol="LT"))
    e["url"] = "https://nsearchives.nseindia.com/corporate/LT_order.pdf"
    assert e["type"] == "order_win" and e["value_cr"] is None
    monkeypatch.setattr(run_mod, "pdf_first_page_text", lambda b: "an order of Rs 2,500 crore; order book Rs 5,00,000 crore")
    monkeypatch.setattr(r.http, "download", lambda url, ref: b"%PDF")
    assert r._finalise(dict(e), -1)["value_cr"] is None                    # plain back-fill: no PDFs
    r._pdf_orders = True
    assert r._finalise(dict(e), -1)["value_cr"] == 2500.0                  # first value on page 1, not the book
