"""Step 7: what the Review and Orders screens are fed, and that the page shows it."""
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server import app as app_mod
from server import paper as paper_mod
from server.broker import PaperBroker
from server.config import settings
from server.paper import PaperLedger
from server.risk import RiskGate
from server.sessions import IST
from tests.test_step5_paper import CE, CLOCK, EXP, StubQuotes

AUTH = ("user", "pw")
BODY = {"symbol": "RELIANCE", "instrument": "CE", "expiry": EXP, "strike": 1300, "side": "BUY", "lots": 1, "order_type": "MARKET"}
TEMPLATE = (Path(__file__).resolve().parent.parent / "templates" / "index.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def allow_lottery(monkeypatch):
    """These tests cover the engine with the cheap / near-expiry fill rule switched on (ALLOW_LOTTERY=true)."""
    from server.config import settings
    monkeypatch.setattr(settings, "allow_lottery", True)


@pytest.fixture
def client(tmp_path, monkeypatch):
    q = StubQuotes()
    ledger = PaperLedger(tmp_path, q, capital=500_000, always_open=True, clock=CLOCK)
    ledger.risk = RiskGate(settings)
    monkeypatch.setattr(settings, "app_password", "pw")
    monkeypatch.setattr(app_mod.state, "ledger", ledger)
    monkeypatch.setattr(app_mod.state, "broker", PaperBroker(tmp_path, ledger))
    monkeypatch.setattr(app_mod.state, "stocks", {"RELIANCE": {"symbol": "RELIANCE", "close": 1250.0, "lot_size": 500,
                                                               "chain": {"expiry": EXP, "strikes": []}}})
    return TestClient(app_mod.app), ledger, q


def test_review_carries_everything_the_sheet_shows(client):
    c, _, q = client
    q.set(CE, 1.0, 1.1, oi=5000)                                 # cheap: lottery fill rule
    r = c.post("/api/order/preview", json=BODY, auth=AUTH).json()["review"]
    assert r["liquidity"]["class"] == "lottery" and r["liquidity"]["reasons"] and "bucket" not in r
    assert r["fill"]["price"] == 1.15 and r["fill"]["slippage_vs_mid"] is not None and r["fill"]["levels"]
    assert r["charges_entry"]["total"] > 0 and r["round_trip_now"]["charges"]["total"] > r["charges_entry"]["total"]
    assert r["risk"]["margin"] == pytest.approx(575.0) and r["risk"]["cap"] == 30000     # 6 % of Rs 5 lakh
    assert r["risk"]["kill_switch"]["active"] is False and "day_pnl" in r["risk"]


def test_exit_review_shows_what_the_exit_realises(client):
    c, _, q = client
    q.set(CE, 4.0, 4.1)
    pv = c.post("/api/order/preview", json=BODY, auth=AUTH).json()
    c.post("/api/order", json={**BODY, "token": pv["token"]}, auth=AUTH)
    q.set(CE, 5.0, 5.1)
    r = c.post("/api/order/preview", json={**BODY, "side": "SELL"}, auth=AUTH).json()["review"]
    assert r["intent"] == "exit" and r["exit_estimate"]["net_pnl"] > 0 and r["round_trip_now"] is None
    assert r.get("risk") is None                                  # limits do not apply to exits


def test_market_closed_review_says_when_it_fills_and_place_queues(client, monkeypatch):
    c, ledger, q = client
    ledger.always_open = False
    monkeypatch.setattr(paper_mod.sessions, "market_open_at", lambda now=None: False)
    q.set(CE, 4.0, 4.1)
    pv = c.post("/api/order/preview", json=BODY, auth=AUTH).json()
    queued = pv["review"]["queued"]
    assert "Market closed" in queued["message"] and "09:20" in queued["message"] and queued["fill_after"]
    rec = c.post("/api/order", json={**BODY, "token": pv["token"]}, auth=AUTH).json()
    assert rec["status"] == "QUEUED" and rec["fill_after"] == queued["fill_after"]
    assert c.get("/api/paper/summary", auth=AUTH).json()["queued_orders"] == 1


def test_refusals_endpoint_counts_and_lists_reasons(client):
    c, ledger, q = client
    ledger.clock = lambda: datetime(2026, 9, 10, 10, 0, tzinfo=IST)   # 13 sessions to the 29 Sep expiry: not lottery
    q.set(CE, 10.0, 11.0)                                        # 9.5% spread: refused
    pv = c.post("/api/order/preview", json=BODY, auth=AUTH).json()
    assert pv["review"]["sessions_to_expiry"] == 13
    assert pv["token"] is None and any("liquidity" in b for b in pv["review"]["blocked"])
    rf = c.get("/api/paper/refusals", auth=AUTH).json()
    assert rf["count"] == 1 and rf["refusals"][0]["contract"] == CE and "spread above 8%" in rf["refusals"][0]["reasons"]


def test_positions_expose_mtm_stop_expiry_and_t2(client):
    c, ledger, q = client
    q.set(CE, 4.0, 4.1)
    pv = c.post("/api/order/preview", json=BODY, auth=AUTH).json()
    c.post("/api/order", json={**BODY, "token": pv["token"]}, auth=AUTH)
    p = c.get("/api/paper/positions", auth=AUTH).json()[0]
    for k in ("unrealised", "stop", "expiry", "t2_date", "mark", "entry", "lots"):
        assert k in p
    assert p["t2_date"] == "2026-09-25"


@pytest.mark.parametrize("text", [
    "Slippage vs mid", "Depth level used", "Charges, this order",
    "Round trip if closed at once", "Margin", "per-trade cap", "Day P&L", "Kill switch", "MTM, net of charges",
    "T-2", "Refusals:", "Show the reasons", "Closed trades", "/api/paper/summary", "/api/paper/refusals", "paperbar"])
def test_template_has_the_review_and_orders_screen_pieces(text):
    assert text in TEMPLATE
