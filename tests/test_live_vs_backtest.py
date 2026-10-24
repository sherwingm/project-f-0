"""scanner/fade_live_vs_backtest.py: live fills against the backtest's candle prices, from the day's own records."""
import pytest

from scanner import fade_live_vs_backtest as LB
from server.fade import PROBE_COLS


def probe():
    row = lambda t, ltp, ltt, op: [t, "HCLTECH", "PE", 1200.0, ltp + 0.2, 100, ltp - 0.2, 100, ltp, ltt, 0, op,   # noqa: E731
                                   ltp, 1225.0]
    return {"cols": PROBE_COLS, "rows": [row("09:15:01", 18.4, "09:15:00", 18.0), row("09:15:59", 18.6, "09:15:58", 18.0),
                                         row("09:16:01", 18.9, "09:16:00", 18.0)]}


def trade(reason, **rule):
    return {"id": "T1", "symbol": "HCLTECH", "instrument": "PE", "strike": 1200.0, "qty": 350, "reason": reason,
            "opened_at": "2026-10-26T09:15:02+05:30", "closed_at": "2026-10-26T15:20:01+05:30",
            "entry": {"price": 18.7}, "exit": {"price": 20.0}, "net_pnl": 400.0, "instant": {"net": 450.0},
            "rule": {"strategy": "fade", "spot_at_entry": 1225.0, **rule}}


def test_entry_b_is_the_first_trade_from_09_16():
    assert LB.entry_b(probe(), "HCLTECH", "PE", 1200.0) == (18.9, 18.0)
    assert LB.entry_b(probe(), "HCLTECH", "CE", 1200.0) == (None, None)


def test_stop_trail_and_eod_exits():
    s = LB.compare(trade("fade_stop", stop={"level": 14.96}), probe(), [])
    assert s["bt_entry_B"] == 18.95 and s["bt_entry_A"] == 18.05 and s["bt_exit"] == 14.91
    assert s["entry_gap_rs"] == pytest.approx((18.95 - 18.7) * 350)
    t = LB.compare(trade("fade_trail", trail={"level": 21.0}), probe(), [])
    assert t["bt_exit"] == 20.95 and t["exit_gap_rs"] == pytest.approx((20.0 - 20.95) * 350)
    rows = [{"id": "T1", "t": "2026-10-26T15:19:40+05:30", "ltp": 20.3}, {"id": "T1", "t": "2026-10-26T15:20:05+05:30", "ltp": 19.0}]
    e = LB.compare(trade("fade_eod"), probe(), rows)
    assert e["bt_exit"] == 20.25 and e["gap_rs"] == pytest.approx(400.0 - e["bt_net"])


def test_missing_data_stays_missing():
    m = LB.compare(trade("fade_eod"), {}, [])
    assert m["bt_entry_B"] is None and m["bt_net"] is None and m["gap_rs"] is None
