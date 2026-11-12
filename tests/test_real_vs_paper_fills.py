"""scanner.real_vs_paper_fills: matching a real execution to the paper fill and the sign of the cost (synthetic data only)."""
import pandas as pd

from scanner.real_vs_paper_fills import compare, paper_fills, summary

LEDGER = {
    "positions": [],
    "closed": [{"tradingsymbol": "TEST26NOV100CE", "opened_at": "2026-11-12T09:15:09+05:30", "closed_at": "2026-11-12T09:40:00+05:30",
                "qty": 100, "entry": {"price": 5.00}, "exit": {"price": 8.00}}],
}


def test_buy_dearer_than_paper_is_positive_cost():
    real = pd.DataFrame([{"date": "2026-11-12", "time": "09:15:12", "tradingsymbol": "TEST26NOV100CE", "side": "BUY", "qty": 100, "price": 5.50}])
    df = compare(paper_fills(LEDGER), real)
    assert df.loc[0, "cost_pct"] == 10.0 and df.loc[0, "lag_s"] == 3.0


def test_sell_lower_than_paper_is_positive_cost():
    real = pd.DataFrame([{"date": "2026-11-12", "time": "09:40:05", "tradingsymbol": "TEST26NOV100CE", "side": "SELL", "qty": 100, "price": 7.60}])
    df = compare(paper_fills(LEDGER), real)
    assert df.loc[0, "cost_pct"] == 5.0


def test_unmatched_symbol_is_reported_not_dropped():
    real = pd.DataFrame([{"date": "2026-11-12", "time": "09:15:12", "tradingsymbol": "OTHER", "side": "BUY", "qty": 1, "price": 1.0}])
    df = compare(paper_fills(LEDGER), real)
    assert df.loc[0, "note"] == "no paper fill that day"
    assert summary(df) == "No executions matched a paper fill."


def test_partial_fill_is_counted():
    real = pd.DataFrame([{"date": "2026-11-12", "time": "09:15:10", "tradingsymbol": "TEST26NOV100CE", "side": "BUY", "qty": 40, "price": 5.00}])
    assert "partial or different size in 1" in summary(compare(paper_fills(LEDGER), real))
