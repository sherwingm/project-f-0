"""Step 6: per-trade risk cap, daily/weekly halts, drawdown banner, margin cap, intensity limits."""
from types import SimpleNamespace

import pytest

from server.paper import PaperLedger, PaperRejected
from server.risk import RiskGate
from tests.test_step5_paper import CE, FUT, StubQuotes, at, order, resolved

DEFAULTS = dict(risk_per_trade_pct=0.5, daily_loss_halt_pct=1.0, weekly_loss_halt_pct=3.0, drawdown_review_pct=10,
                margin_cap_pct=30, max_new_positions_per_day=3, max_new_positions_per_month=20, block_expiry_day_entries=True)


def make(tmp_path, **over):
    q = StubQuotes()
    ledger = PaperLedger(tmp_path, q, capital=500_000)
    ledger.risk = RiskGate(SimpleNamespace(**{**DEFAULTS, **over}))
    return ledger, q


def test_long_option_lots_are_capped_by_premium_at_risk(tmp_path):
    ledger, q = make(tmp_path)
    q.set(CE, 4.0, 4.1)                                          # fill 4.15 x 500 = Rs 2,075 a lot; cap Rs 2,500
    r = ledger.preview(order(lots=2), resolved(CE, 2), now=at(21))
    assert r["risk"]["cap"] == 2500 and r["risk"]["max_lots"] == 1 and r["risk"]["per_lot_max_loss"] == 2075
    assert any("at most 1 lot" in b for b in r["blocked"])
    ok = ledger.preview(order(), resolved(CE), now=at(21))
    assert not ok["blocked"] and ok["risk"]["used_pct"] == 83.0
    q.set(CE, 10.0, 10.2)                                        # Rs 5,125 a lot
    assert any("one lot risks" in b for b in ledger.preview(order(), resolved(CE), now=at(21))["blocked"])


def test_futures_risk_is_entry_minus_stop(tmp_path):
    ledger, q = make(tmp_path)
    q.set(FUT, 1000.0, 1000.1, oi=10_000_000)                    # fill 1000.15
    wide = ledger.preview(order("FUT"), resolved(FUT), stop=995.0, now=at(21))     # 5.15 x 500 = 2,575
    assert any("one lot risks" in b for b in wide["blocked"])
    tight = ledger.preview(order("FUT"), resolved(FUT), stop=996.0, now=at(21))    # 4.15 x 500 = 2,075
    assert not tight["blocked"] and tight["risk"]["max_loss"] == 2075


def test_short_option_needs_a_stop(tmp_path):
    ledger, q = make(tmp_path)
    q.set(CE, 4.0, 4.1)
    r = ledger.preview(order(side="SELL"), resolved(CE), now=at(21))
    assert any("short options need a stop" in b for b in r["blocked"])


def test_daily_loss_halt_blocks_entries_for_the_rest_of_the_day_but_not_exits(tmp_path):
    ledger, q = make(tmp_path)
    q.set(FUT, 1000.0, 1000.1, oi=10_000_000)
    ledger.submit(order("FUT"), resolved(FUT), stop=996.0, now=at(21))
    q.set(FUT, 980.0, 980.1, oi=10_000_000)                      # gap through the stop: about -Rs 10,300 today
    ledger.on_poll(now=at(21, 11))
    s = ledger.summary(now=at(21, 11))
    assert s["day_pnl"] <= -5000 and s["kill_switch"]["active"] and s["kill_switch"]["day_halt"]
    q.set(CE, 4.0, 4.1)
    with pytest.raises(PaperRejected, match="daily loss halt"):
        ledger.submit(order(), resolved(CE), now=at(21, 11, 5))
    q.set(FUT, 999.0, 999.1, oi=10_000_000)                      # recovers: the halt stays for the day
    ledger.on_poll(now=at(21, 11, 10))
    assert ledger.summary(now=at(21, 11, 10))["kill_switch"]["active"]
    assert not ledger.positions_view()                           # the triggered stop exited at the next poll anyway
    rec = ledger.submit(order(), resolved(CE), now=at(22))       # next session: entries allowed again
    assert rec["status"] == "FILLED"


def test_exits_are_allowed_while_halted(tmp_path):
    ledger, q = make(tmp_path, daily_loss_halt_pct=0.1)          # Rs 500
    q.set(CE, 4.0, 4.1)
    ledger.submit(order(), resolved(CE), now=at(21))
    q.set(CE, 2.5, 2.6)
    ledger.on_poll(now=at(21, 11))
    assert ledger.summary(now=at(21, 11))["kill_switch"]["active"]
    rec = ledger.submit(order(side="SELL"), resolved(CE), now=at(21, 11, 5))
    assert rec["intent"] == "exit" and rec["status"] == "FILLED"


def test_weekly_halt(tmp_path):
    ledger, q = make(tmp_path, daily_loss_halt_pct=50, weekly_loss_halt_pct=0.2)    # Rs 1,000 a week
    q.set(CE, 4.0, 4.1)
    ledger.submit(order(), resolved(CE), now=at(21))
    q.set(CE, 2.0, 2.1)
    ledger.on_poll(now=at(21, 11))
    q.set("RELIANCE26SEP1320CE", 1.0, 1.05)
    with pytest.raises(PaperRejected, match="weekly loss halt"):
        ledger.submit(order(strike=1320.0), resolved("RELIANCE26SEP1320CE"), now=at(22))


def test_drawdown_review_banner_is_not_a_block(tmp_path):
    ledger, q = make(tmp_path, drawdown_review_pct=0.1, daily_loss_halt_pct=50, weekly_loss_halt_pct=50)
    q.set(CE, 4.0, 4.1)
    ledger.submit(order(), resolved(CE), now=at(21))
    q.set(CE, 1.0, 1.1)
    ledger.on_poll(now=at(21, 11))
    s = ledger.summary(now=at(21, 11))
    assert s["drawdown_review"] and "review labels and sizing" in s["drawdown_review_message"]
    q.set("RELIANCE26SEP1320CE", 1.0, 1.05)
    assert ledger.submit(order(strike=1320.0), resolved("RELIANCE26SEP1320CE"), now=at(21, 11, 5))["status"] == "FILLED"


def test_margin_cap_uses_the_estimate_or_kotak(tmp_path):
    ledger, q = make(tmp_path, risk_per_trade_pct=5)             # let sizing pass so margin is what binds
    q.set(FUT, 1000.0, 1000.1, oi=10_000_000)
    two = ledger.preview(order("FUT", lots=2), resolved(FUT, 2), stop=998.0, now=at(21))
    assert two["risk"]["margin"] == pytest.approx(0.18 * 1000.15 * 1000)                   # Rs 1,80,027 > Rs 1,50,000
    assert any("margin" in b and "30%" in b for b in two["blocked"])
    assert not ledger.preview(order("FUT"), resolved(FUT), stop=998.0, now=at(21))["blocked"]
    ledger.risk.margin_fn = lambda req, contract, px: 200_000.0
    k = ledger.preview(order("FUT"), resolved(FUT), stop=998.0, now=at(21))
    assert k["risk"]["margin_source"] == "kotak" and any("margin" in b for b in k["blocked"])


def test_new_position_limits_per_day_and_month(tmp_path):
    ledger, q = make(tmp_path, max_new_positions_per_month=4)
    for k in (1300, 1320, 1340):
        ts = f"RELIANCE26SEP{k}CE"
        q.set(ts, 1.0, 1.05)
        ledger.submit(order(strike=float(k)), resolved(ts), now=at(21))
    q.set("RELIANCE26SEP1360CE", 1.0, 1.05)
    with pytest.raises(PaperRejected, match="new positions today"):
        ledger.submit(order(strike=1360.0), resolved("RELIANCE26SEP1360CE"), now=at(21, 12))
    ledger.submit(order(strike=1360.0), resolved("RELIANCE26SEP1360CE"), now=at(22))       # 4th of the month
    q.set("RELIANCE26SEP1380CE", 1.0, 1.05)
    with pytest.raises(PaperRejected, match="this month"):
        ledger.submit(order(strike=1380.0), resolved("RELIANCE26SEP1380CE"), now=at(23))


def test_no_entries_on_expiry_day(tmp_path):
    ledger, q = make(tmp_path)
    q.set(CE, 1.0, 1.05)
    r = ledger.preview(order(), resolved(CE), now=at(29, 10))
    assert any("expiry day" in b for b in r["blocked"])


def test_summary_carries_kill_switch_and_limits(tmp_path):
    ledger, _ = make(tmp_path)
    s = ledger.summary(now=at(21))
    assert s["kill_switch"] == {"active": False, "reason": None, "day_halt": False, "week_halt": False,
                                "day_limit": -5000.0, "week_limit": -15000.0}
    assert s["limits"]["risk_per_trade"] == 2500 and s["limits"]["margin_cap"] == 150_000
