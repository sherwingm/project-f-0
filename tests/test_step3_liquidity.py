"""Step 3: liquidity classes for futures and options, the lottery bucket, and the refusal log."""
import json

from server.liquidity import BUCKET_CHEAP, BUCKET_NORMAL, Rules, classify, read_refusals

FUT = {"symbol": "RELIANCE", "instrument": "FUT", "tradingsymbol": "RELIANCE26SEPFUT", "lot_size": 500, "side": "BUY"}
CE = {"symbol": "RELIANCE", "instrument": "CE", "tradingsymbol": "RELIANCE26SEP1300CE", "lot_size": 500, "side": "BUY",
      "strike": 1300.0, "expiry": "2026-09-29"}


def book(bid, ask, qty=10_000, oi=None, levels=5, tick=0.05):
    d = {"bid": [(round(bid - i * tick, 2), qty) for i in range(levels)] if bid else [],
         "ask": [(round(ask + i * tick, 2), qty) for i in range(levels)] if ask else []}
    return {"depth": d, "open_interest": oi, "last_price": ask or bid}


# ---- futures
def test_future_tight_and_small_is_accept():
    r = classify(FUT, book(1000.0, 1000.2), lots=1, sessions_to_expiry=10)   # 0.02% spread, 500 of 50,000
    assert r["class"] == "accept" and r["visible_qty"] == 50_000 and r["spread_pct"] == 0.02


def test_future_spread_in_band_is_penalty():
    assert classify(FUT, book(1000.0, 1001.0), 1, 10)["class"] == "penalty"          # 0.1%


def test_future_wide_spread_no_side_or_big_order_is_refused():
    assert classify(FUT, book(1000.0, 1002.0), 1, 10)["class"] == "refuse"           # 0.2%
    assert classify(FUT, book(None, 1000.2), 1, 10)["class"] == "refuse"             # no bid
    thin = book(1000.0, 1000.2, qty=200)                                            # 1,000 visible, order 500 = 50%...
    assert classify(FUT, thin, 1, 10)["class"] == "penalty"                         # ...is not above 50%
    assert classify(FUT, thin, 2, 10)["class"] == "refuse"                          # 1,000 of 1,000 visible


def test_future_between_depth_limits_is_penalty():
    r = classify(FUT, book(1000.0, 1000.2, qty=300), 1, 10)                        # 500 of 1,500 = 33%
    assert r["class"] == "penalty" and any("25-50%" in x for x in r["reasons"])


def test_sell_order_is_judged_against_the_bids():
    b = book(1000.0, 1000.2)
    b["depth"]["bid"] = [(1000.0, 100)]
    assert classify({**FUT, "side": "SELL"}, b, 1, 10)["class"] == "refuse"          # 500 vs 100 visible bids
    assert classify(FUT, b, 1, 10)["class"] == "accept"                             # the asks are deep


# ---- options
def test_option_accept_penalty_and_refuse_by_spread():
    oi = 100 * 500
    assert classify(CE, book(10.0, 10.2, oi=oi), 1, 10)["class"] == "accept"          # 1.98%
    assert classify(CE, book(10.0, 10.5, oi=oi), 1, 10)["class"] == "penalty"         # 4.9%
    r = classify(CE, book(10.0, 11.0, oi=oi), 1, 10)                                 # 9.5%
    assert r["class"] == "refuse" and any("spread above 8" in x for x in r["reasons"])


def test_option_low_oi_one_sided_or_too_big_is_refused():
    assert classify(CE, book(10.0, 10.2, oi=20 * 500), 1, 10)["class"] == "refuse"    # 20 lots of OI
    assert classify(CE, book(None, 10.2, oi=100 * 500), 1, 10)["class"] == "refuse"


def test_option_order_exactly_the_visible_depth_is_penalty_and_above_is_refused():
    b = book(10.0, 10.2, qty=100, oi=100 * 500)                  # 500 visible asks
    assert classify(CE, b, 1, 10)["class"] == "penalty"          # 100% of depth: not above the limit
    b["depth"]["ask"] = b["depth"]["ask"][:4]                   # 400 visible
    assert classify(CE, b, 1, 10)["class"] == "refuse"


def test_cheap_premium_is_lottery_even_with_wide_spread_and_low_oi():
    r = classify(CE, book(0.5, 1.5, oi=5 * 500), 1, 10)
    assert r["class"] == "lottery" and r["bucket"] == BUCKET_CHEAP


def test_near_expiry_is_lottery_regardless_of_premium():
    r = classify(CE, book(40.0, 44.0, oi=1), 1, sessions_to_expiry=2)
    assert r["class"] == "lottery" and r["bucket"] == BUCKET_CHEAP
    assert classify(CE, book(40.0, 44.0, oi=1), 1, sessions_to_expiry=3)["class"] == "refuse"


def test_lottery_still_needs_the_side_it_trades_against():
    assert classify(CE, book(1.0, None, oi=1), 1, 10)["class"] == "refuse"            # buy, no ask
    assert classify({**CE, "side": "SELL"}, book(1.0, None, oi=1), 1, 10)["class"] == "lottery"


def test_normal_bucket_on_ordinary_fills():
    assert classify(CE, book(10.0, 10.2, oi=100 * 500), 1, 10)["bucket"] == BUCKET_NORMAL


def test_refusals_are_logged_with_the_quote(tmp_path):
    path = tmp_path / "refusals.jsonl"
    classify(FUT, book(1000.0, 1000.2), 1, 10, refusals_path=path)          # accept: not logged
    classify(FUT, book(1000.0, 1005.0), 1, 10, refusals_path=path, stage="preview")
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    assert len(rows) == 1
    rec = rows[0]
    assert rec["symbol"] == "RELIANCE" and rec["contract"] == "RELIANCE26SEPFUT" and rec["stage"] == "preview"
    assert rec["reasons"] and rec["quote"]["depth"]["ask"][0] == [1005.0, 10_000] and rec["time"]
    assert read_refusals(path)[0]["contract"] == "RELIANCE26SEPFUT"


def test_thresholds_are_configurable():
    loose = Rules(fut_refuse_spread_pct=1.0, fut_accept_spread_pct=0.5)
    assert classify(FUT, book(1000.0, 1002.0), 1, 10, rules=loose)["class"] == "accept"
