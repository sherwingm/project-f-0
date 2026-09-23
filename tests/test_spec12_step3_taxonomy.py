"""Spec 12 step 3: taxonomy rules, value parsing, materiality buckets."""
import pytest

from scanner.events.score import Scorer, bucket_of, parse_value_cr
from scanner.events.taxonomy import analyst_view, classify, meeting_date, name_index


def item(**over):
    base = {"source": "nse_ann", "source_id": "1", "symbol": "ABC", "event_date": "2026-09-22",
            "event_time": "18:00", "category": "Updates", "subject": "", "text": "", "url": "", "extra": {}}
    return {**base, **over}


# ---------------------------------------------------------------- classification per type
def test_results_date_moves_to_the_meeting_day():
    e = classify(item(category="Board Meeting Intimation",
                      subject="Board meeting scheduled to be held on September 30, 2026 to consider unaudited financial results"))
    assert e["type"] == "results_date" and e["event_date"] == "2026-09-30" and e["direction"] == 0
    assert meeting_date("meeting on 30-09-2026 to approve results") == "2026-09-30"


def test_results_and_order_and_capacity():
    assert classify(item(category="Financial Results", subject="Unaudited financial results for the quarter"))["type"] == "results"
    e = classify(item(subject="Bagged an order worth Rs 800 crore from NTPC"))
    assert e["type"] == "order_win" and e["direction"] == 1
    assert classify(item(category="Press Release", subject="Received letter of award (LoA)"))["type"] == "order_win"
    assert classify(item(subject="Commissioning of new plant at Dahej"))["type"] == "capacity"
    assert classify(item(category="Acquisition", subject="Acquisition of 100% stake in XYZ Ltd"))["type"] == "capacity"
    # "orders passed" by a regulator is not an order win
    assert classify(item(category="Action(s) taken or orders passed", subject="Orders passed by SEBI")) is None


def test_rating_requires_a_registered_cra():
    up = classify(item(category="Credit Rating", subject="CRISIL upgrades the long-term rating to AA"))
    assert up["type"] == "rating" and up["direction"] == 1 and up["subtype"] == "upgrade"
    down = classify(item(category="Credit Rating", subject="ICRA places the rating on negative watch"))
    assert down["direction"] == -1 and down["subtype"] == "downgrade"
    same = classify(item(category="Credit Rating", subject="CARE reaffirms the rating at A1+"))
    assert same["direction"] == 0 and same["subtype"] == "reaffirm"
    assert classify(item(category="Credit Rating", subject="Joe's Rating Shop upgrades us to AAA+")) is None


def test_deals_insider_and_ban_rules():
    deal = classify(item(source="nse_block", category="block deal",
                         extra={"client": "HDFC MUTUAL FUND", "side": "BUY", "quantity": 1_000_000, "price": 300.0}))
    assert deal["type"] == "block_deal" and deal["direction"] == 1 and deal["subtype"] == "fund_buy"
    ins = classify(item(source="nse_pit", extra={"person_category": "Promoters", "side": "BUY", "quantity": 10}))
    assert ins["type"] == "insider" and ins["direction"] == 1 and ins["subtype"] == "promoter_buy"
    pledge = classify(item(source="nse_pit", extra={"person_category": "Promoters", "side": "PLEDGE"}))
    assert pledge is None
    ban_in = classify(item(source="nse_ban", extra={"in_ban": True}))
    assert ban_in["type"] == "ban" and ban_in["direction"] == -1 and ban_in["subtype"] == "in"
    ban_out = classify(item(source="nse_ban", extra={"in_ban": False}))
    assert ban_out["direction"] == 0 and ban_out["subtype"] == "out"


def test_rss_only_becomes_analyst_view_and_never_classify():
    names = name_index({"RELIANCE": "Reliance Industries Limited"})
    it = item(source="rss:et_markets", subject="Jefferies raises target price on Reliance Industries to Rs 1,600")
    assert classify(it) is None
    av = analyst_view(it, names)
    assert av["type"] == "analyst_view" and av["tier"] == 3 and av["symbol"] == "RELIANCE" and av["direction"] == 1
    assert analyst_view(item(source="rss:et_markets", subject="Reliance shares rise 3%"), names) is None       # no broker
    assert analyst_view(item(source="rss:et_markets", subject="Jefferies initiates coverage on Unknown Co"), names) is None
    down = analyst_view(item(source="rss:et_markets", subject="Morgan Stanley downgrades Reliance to underweight"), names)
    assert down["direction"] == -1


# ---------------------------------------------------------------- value parsing and buckets
def test_value_parsing_units():
    assert parse_value_cr("orders worth ₹1,234.5 crore received") == 1234.5
    assert parse_value_cr("an order of Rs. 500 lakhs") == 5.0
    assert parse_value_cr("capex of INR 2 billion planned") == 200.0
    assert parse_value_cr("worth Rs 750 mn") == 75.0
    assert parse_value_cr("orders of Rs 5 crore and Rs 800 crore") == 800.0        # the largest wins
    assert parse_value_cr("no numbers here") is None


def test_bucket_bounds():
    assert bucket_of(0.5, (1, 5, 20)) == "ignore" and bucket_of(1.0, (1, 5, 20)) == "minor"
    assert bucket_of(5.0, (1, 5, 20)) == "significant" and bucket_of(25.0, (1, 5, 20)) == "major"
    assert bucket_of(None, (1, 5, 20)) == "minor"


def test_spec_acceptance_buckets():
    sc = Scorer(closes={"BIG": 500.0, "SMALL": 400.0}, shares={"BIG": 1_000_000_000, "SMALL": 100_000_000})
    # BIG: mcap 50,000 cr; a Rs 5 crore order is noise
    small_order = classify(item(symbol="BIG", subject="Received an order worth Rs 5 crore"))
    assert sc.score(small_order)["bucket"] == "ignore" and small_order["value_cr"] == 5.0
    # SMALL: mcap 4,000 cr; a Rs 800 crore order is 20% of it
    big_order = classify(item(symbol="SMALL", subject="Bagged an order worth Rs 800 crore"))
    scored = sc.score(big_order)
    assert scored["bucket"] == "major" and scored["materiality"] == 20.0


def test_deal_and_insider_materiality():
    sc = Scorer(closes={"ABC": 300.0}, shares={"ABC": 100_000_000})
    deal = classify(item(source="nse_block", symbol="ABC",
                         extra={"client": "SBI LIFE INSURANCE", "side": "SELL", "quantity": 3_000_000, "price": 300.0}))
    scored = sc.score(deal)
    assert scored["materiality"] == 3.0 and scored["bucket"] == "significant" and scored["value_cr"] == 90.0
    ins = classify(item(source="nse_pit", symbol="ABC",
                        extra={"person_category": "Director", "side": "SELL", "quantity": 50_000, "pct_traded": 0.05}))
    assert sc.score(ins)["bucket"] == "ignore"
    big = classify(item(source="nse_pit", symbol="ABC",
                        extra={"person_category": "Promoters", "side": "BUY", "quantity": 2_000_000, "pct_traded": 2.0}))
    assert sc.score(big)["bucket"] == "significant"


def test_events_without_a_size_are_always_significant():
    sc = Scorer()
    for cat, subj, typ in (("Credit Rating", "CRISIL reaffirms", "rating"),
                           ("Financial Results", "Unaudited financial results", "results")):
        e = classify(item(category=cat, subject=subj))
        assert e["type"] == typ and sc.score(e)["bucket"] == "significant"
    ban = classify(item(source="nse_ban", extra={"in_ban": True}))
    assert sc.score(ban)["bucket"] == "significant"


def test_order_with_no_value_is_minor_not_ignored():
    sc = Scorer(closes={"ABC": 300.0}, shares={"ABC": 100_000_000})
    e = classify(item(symbol="ABC", subject="Received a large export order from Europe"))
    assert sc.score(e)["bucket"] == "minor" and e["value_cr"] is None
