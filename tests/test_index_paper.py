"""index_paper: fills at ask / bid, rejection without quotes, held peak on the combined bid, exit_pending, after-exit
follow-up kept apart, IDs, persistence, pods off by default, the L1 live rule."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import pytest

from index_paper import pods as P
from index_paper.ledger import IndexPaperLedger, IndexPaperRejected, capture
from index_paper.report import build
from index_paper.runner import tick
from server.peak import IST

T0 = datetime(2026, 11, 2, 15, 20, tzinfo=IST)
LEGS = [{"symbol": "NIFTY-CE", "underlying": "NIFTY", "expiry": "2026-11-17", "strike": 25000, "opt": "CE", "qty": 75},
        {"symbol": "NIFTY-PE", "underlying": "NIFTY", "expiry": "2026-11-17", "strike": 25000, "opt": "PE", "qty": 75}]


def q(bid, ask, ltt="2026-11-02 15:19:58"):
    return {"depth": {"bid": [(bid, 300)] if bid else [], "ask": [(ask, 300)] if ask else []}, "last_price": bid,
            "timestamp": ltt, "source": "test"}


def quotes(ce, pe, **kw):
    return {"NIFTY-CE": q(*ce, **kw), "NIFTY-PE": q(*pe, **kw)}


def test_entry_fills_at_ask_and_ids(tmp_path):
    led = IndexPaperLedger(tmp_path)
    p = led.open("L1", LEGS, quotes((99, 100), (79, 80)), T0, reason="test")
    assert p["id"] == "IX-L1-20261102-001"
    assert [lg["entry_px"] for lg in p["legs"]] == [100, 80]
    assert p["debit_rs"] == 180 * 75 and p["entry_fees"] > 0
    p2 = led.open("L1", LEGS, quotes((99, 100), (79, 80)), T0, reason="test")
    assert p2["id"] == "IX-L1-20261102-002"
    assert (tmp_path / "index_paper" / "state.json").exists()


@pytest.mark.parametrize("qs,msg", [
    ({"NIFTY-CE": q(99, 100)}, "no quote"),
    (quotes((99, None), (79, 80)), "no ask"),
    (quotes((99, 100), (79, 80), ltt="2026-10-30 15:29:00"), "before today's open"),
])
def test_entry_rejected_without_live_ask(tmp_path, qs, msg):
    led = IndexPaperLedger(tmp_path)
    with pytest.raises(IndexPaperRejected, match=msg):
        led.open("L1", LEGS, qs, T0)
    assert led.state["open"] == [] and led.state["rejected"][-1]["problems"]


def test_held_peak_uses_combined_bid_and_skips_partial_polls(tmp_path):
    led = IndexPaperLedger(tmp_path)
    p = led.open("L1", LEGS, quotes((99, 100), (79, 80)), T0)
    led.observe(quotes((110, 111), (70, 71)), T0 + timedelta(minutes=1))     # 180 x 75
    led.observe(quotes((150, 151), (None, 60)), T0 + timedelta(minutes=2))   # PE has no bid: missing
    led.observe(quotes((130, 131), (75, 76)), T0 + timedelta(minutes=3))     # 205 x 75: peak
    led.observe(quotes((90, 91), (75, 76)), T0 + timedelta(minutes=4))       # 165 x 75: low
    h = led.state["open"][0]["held"]
    assert h["peak"]["value"] == 205 * 75 and h["peak"]["bids"] == {"NIFTY-CE": 130, "NIFTY-PE": 75}
    assert h["low"]["value"] == 165 * 75 and h["missing"] == 1 and h["n"] == 3
    rows = (tmp_path / "index_paper" / "observations" / "2026-11-02.jsonl").read_text().splitlines()
    assert all(json.loads(r)["id"] == p["id"] and json.loads(r)["phase"] == "held" for r in rows)


def test_exit_at_bid_capture_and_after_exit_kept_apart(tmp_path):
    led = IndexPaperLedger(tmp_path)
    p = led.open("L1", LEGS, quotes((99, 100), (79, 80)), T0)
    led.observe(quotes((130, 131), (75, 76)), T0 + timedelta(minutes=1))
    c = led.close(p["id"], quotes((120, 121), (70, 71)), T0 + timedelta(minutes=2), "time")
    assert [lg["exit_px"] for lg in c["legs"]] == [120, 70]
    assert c["proceeds_rs"] == 190 * 75
    assert c["net_rs"] == pytest.approx(190 * 75 - 180 * 75 - c["entry_fees"] - c["exit_fees"], abs=0.01)
    cap = c["capture"]
    assert cap["peak_value"] == 205 * 75 and cap["peak_return_pct"] == pytest.approx((205 - 180) / 180 * 100, abs=0.01)
    assert 0 < cap["capture_pct"] < 100 and cap["giveback_rs"] > 0
    peak_before = c["held"]["peak"]["value"]
    led.observe_after(quotes((300, 301), (200, 201)), T0 + timedelta(minutes=10))
    c2 = led.state["closed"][0]
    assert c2["held"]["peak"]["value"] == peak_before and c2["net_rs"] == c["net_rs"]
    assert c2["after"]["peak"]["value"] == 500 * 75
    led.observe_after(quotes((400, 401), (300, 301)), T0 + timedelta(minutes=70))   # past the 60-min window
    assert led.state["closed"][0]["after"]["n"] == 1


def test_exit_waits_without_bid(tmp_path):
    led = IndexPaperLedger(tmp_path)
    p = led.open("L1", LEGS, quotes((99, 100), (79, 80)), T0)
    assert led.close(p["id"], quotes((120, 121), (None, 71)), T0 + timedelta(minutes=1), "time") is None
    assert led.state["open"][0]["exit_pending"]["waiting_for"] == "NIFTY-PE"
    assert led.close(p["id"], quotes((120, 121), (70, 71)), T0 + timedelta(minutes=2), "time")["status"] == "closed"


def test_state_survives_reload(tmp_path):
    led = IndexPaperLedger(tmp_path)
    led.open("L1", LEGS, quotes((99, 100), (79, 80)), T0)
    led2 = IndexPaperLedger(tmp_path)
    assert len(led2.state["open"]) == 1
    assert led2.open("L1", LEGS, quotes((99, 100), (79, 80)), T0)["id"].endswith("-002")


def test_pods_off_by_default_and_runner_does_not_enter(tmp_path):
    assert P.ENABLED == set() and not P.PODS["L1"].enabled
    led = IndexPaperLedger(tmp_path)
    ctx = {"vix_closes": [(date(2026, 10, 20) + timedelta(days=i), 20 + i) for i in range(8)]}
    ev = tick(led, P.PODS, ctx, lambda s: {}, T0)
    assert ev == [] and led.state["open"] == []


def test_l1_signal_uses_finished_sessions_only():
    closes = [(date(2026, 10, 26) + timedelta(days=i), v) for i, v in enumerate([18, 19, 20, 21, 21.5, 23])]
    now = datetime(2026, 11, 1, 15, 21, tzinfo=IST)            # last close 31 Oct = 23 > 22 and > 18
    assert P.l1_signal({"vix_closes": closes}, now)
    assert P.l1_signal({"vix_closes": closes}, now.replace(hour=14)) is None   # before the entry time
    today_close = closes + [(date(2026, 11, 1), 10.0)]          # today's own value must not be used
    assert P.l1_signal({"vix_closes": today_close}, now)
    falling = [(d, v) for d, v in closes[:-1]] + [(closes[-1][0], 17.0)]
    assert P.l1_signal({"vix_closes": falling}, now) is None


def test_l1_legs_and_exit():
    chain = {f"{k}{o}": {"strike": k, "opt": o, "expiry": e} for k in (24900, 25000) for o in ("CE", "PE")
             for e in [date(2026, 11, 4), date(2026, 11, 17)]}
    chain = {f"{s}-{c['expiry']}": c for s, c in chain.items()}
    qs = {s: q(100, 102) if (c["strike"] == 25000) else q(150, 152) if c["opt"] == "CE" else q(60, 62)
          for s, c in chain.items()}
    legs = P.l1_legs({"chain": chain, "lot": 75}, qs, T0)
    assert {lg["strike"] for lg in legs} == {25000} and {lg["expiry"] for lg in legs} == {"2026-11-17"}
    sessions = [date(2026, 11, 2) + timedelta(days=i) for i in range(12) if (date(2026, 11, 2) + timedelta(days=i)).weekday() < 5]
    pos = {"opened_at": T0.isoformat(), "legs": legs}
    assert P.l1_exit_due(pos, {"sessions": sessions}, datetime(2026, 11, 9, 15, 25, tzinfo=IST)) == "time: 5 sessions"
    assert P.l1_exit_due(pos, {"sessions": sessions}, datetime(2026, 11, 6, 15, 25, tzinfo=IST)) is None


def test_report(tmp_path):
    led = IndexPaperLedger(tmp_path)
    p = led.open("L1", LEGS, quotes((99, 100), (79, 80)), T0)
    led.observe(quotes((130, 131), (75, 76)), T0 + timedelta(minutes=1))
    led.close(p["id"], quotes((120, 121), (70, 71)), T0 + timedelta(minutes=2), "time")
    r = build(led)
    l1 = r["pods"][0]
    assert l1["pod"] == "L1" and l1["trades"] == 1 and l1["won"] == 1 and l1["enabled"] is False
    assert capture({"held": {}}) is None


def test_api_reads_ledger(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from server import index_api
    monkeypatch.setattr(index_api.settings, "data_dir", tmp_path)
    led = IndexPaperLedger(tmp_path)
    p = led.open("L1", LEGS, quotes((99, 100), (79, 80)), T0)
    app = FastAPI()
    app.include_router(index_api.router)
    c = TestClient(app)
    pos = c.get("/api/index/positions").json()
    assert [x["id"] for x in pos["positions"]] == [p["id"]]
    res = c.get("/api/index/results").json()
    assert res["pods"][0]["pod"] == "L1" and res["pods"][0]["enabled"] is False and res["closed"] == []
