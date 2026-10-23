"""server/peak.py and its use in the paper ledger: the while-held sellable peak and how much the exit captured."""
import json
from datetime import datetime

import pytest

from server import charges as ch
from server import fade as F
from server import peak as pk
from server.paper import PaperLedger
from server.sessions import IST
from tests.test_fade import CountingQuotes, sig


def t(h, m, s=0):
    return datetime(2026, 10, 15, h, m, s, tzinfo=IST)


def run(bids, entry=10.0, qty=100, exit_price=None, net=None):
    """Feed a bid sequence, then capture() as if sold at exit_price (default: the last bid)."""
    pos = {}
    for i, b in enumerate(bids):
        pk.observe(pos, b, t(9, 16, i), pk.SOURCE_POLL)
    ex = exit_price if exit_price is not None else [b for b in bids if b][-1]
    e_ch = ch.leg("PE", "BUY", qty, entry)["total"]
    if net is None:
        net = (ex - entry) * qty - e_ch - ch.leg("PE", "SELL", qty, ex)["total"]
    return pos, pk.capture(entry, qty, "PE", e_ch, pos.get("held_bid"), ex, net), net


def test_1_rises_then_reverses_before_the_exit():
    pos, c, net = run([10.0, 12.0, 15.0, 13.0, 14.6])
    assert c["peak_bid"] == 15.0 and c["peak_at"] == t(9, 16, 2).isoformat(timespec="seconds")
    assert c["peak_return_pct"] == 50.0 and c["peak_to_exit_pct"] == round((15 - 14.6) / 15 * 100, 2)
    assert 0 < c["capture_pct"] < 100 and c["giveback_rs"] == round(c["peak_net"] - net, 2)


def test_2_peak_on_the_exit_quote():
    _, c, _ = run([10.0, 11.0, 12.5])
    assert c["peak_bid"] == 12.5 and c["peak_to_exit_pct"] == 0.0 and c["capture_pct"] == 100.0


def test_3_a_higher_price_after_the_exit_never_changes_the_held_peak(tmp_path):
    lg, q, ft = ledger(tmp_path)
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(t(9, 16))
    pid = lg.state["positions"][0]["id"]
    lg.close_at(pid, 18.0, t(9, 20), "fade_stop")
    q.set("PE", 1220.0, 40.0, 40.5)
    lg.on_poll(now=t(10, 0))                                                   # the after-sale follow sees 40
    c = lg.state["closed"][-1]
    assert c["held_bid"]["peak"]["price"] == 18.0 and c["peak_capture"]["peak_bid"] == 18.0
    assert c["after"]["peak_bid"]["price"] == 40.0                             # kept apart


def test_4_no_favourable_peak():
    _, c, _ = run([9.0, 8.5, 8.2])
    assert c["peak_return_pct"] == -10.0 and c["mfe_pct"] == -10.0 and c["mae_pct"] == -18.0


def test_5_exit_at_the_fixed_stop_counts_the_exit_quote():
    _, c, _ = run([10.0, 9.0, 8.0])
    assert c["low_bid"] == 8.0 and c["mae_pct"] == -20.0 and c["capture_pct"] is None


def test_6_exit_at_the_trailing_stop():
    _, c, _ = run([10.0, 11.0, 12.0, 11.76])                                    # 0.98 x 12
    assert c["peak_bid"] == 12.0 and c["peak_to_exit_pct"] == 2.0


def test_7_exit_at_the_scheduled_close():
    _, c, _ = run([10.0, 10.4, 10.2])
    assert c["peak_bid"] == 10.4 and c["quotes"] == 3


def test_8_missing_quotes_are_counted_not_used():
    pos, c, _ = run([10.0, None, 0, 11.0])
    assert c["quotes"] == 2 and c["missing_quotes"] == 2 and c["low_bid"] == 10.0


def test_9_a_repeated_timestamp_keeps_the_earliest_equal_peak():
    pos = {}
    pk.observe(pos, 12.0, t(9, 20), pk.SOURCE_POLL)
    pk.observe(pos, 12.0, t(9, 20), pk.SOURCE_FAST)
    pk.observe(pos, 12.0, t(9, 21), pk.SOURCE_POLL)
    assert pos["held_bid"]["peak"]["at"] == t(9, 20).isoformat(timespec="seconds") and pos["held_bid"]["n"] == 3


def test_10_capture_undefined_when_the_peak_never_paid():
    _, c, _ = run([10.0, 10.02, 9.0])                                           # +0.2 % does not cover charges
    assert c["peak_net"] <= 0 and c["capture_pct"] is None and c["capture_note"].startswith("N/A")


def test_11_a_loss_after_a_profitable_peak_is_a_negative_capture():
    _, c, net = run([10.0, 14.0, 7.9])
    assert net < 0 < c["peak_net"] and c["capture_pct"] < 0                    # not clamped to 0


def test_12_the_basis_is_the_live_bid_never_a_candle_or_ltp():
    _, c, _ = run([10.0, 11.0])
    assert "best bid" in c["basis"] and "not LTP" in c["basis"]


def test_13_old_trades_without_the_new_fields_still_load(tmp_path):
    lg, _, _ = ledger(tmp_path)
    lg.state["closed"].append({"id": "OLD", "symbol": "X", "net_pnl": 5.0, "held_peak": {"price": 1, "at": "x"}})
    lg._save()
    again = PaperLedger(tmp_path, CountingQuotes(), capital=500_000, clock=lambda: t(9, 16))
    assert again.state["closed"][-1]["id"] == "OLD" and pk.capture(10, 1, "PE", 0, None, 10, 0) is None


def test_14_post_sale_quotes_never_reach_the_held_peak(tmp_path):
    lg, q, ft = ledger(tmp_path)
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(t(9, 16))
    q.set("PE", 1220.0, 21.0, 21.3)
    lg.on_poll(now=t(9, 30))                                                    # held: 21
    lg.close_at(lg.state["positions"][0]["id"], 19.0, t(9, 40), "fade_trail")
    q.set("PE", 1220.0, 30.0, 30.3)
    lg.on_poll(now=t(11, 0))
    c = lg.state["closed"][-1]
    assert c["peak_capture"]["peak_bid"] == 21.0 and c["held_bid"]["last"]["price"] == 19.0
    assert c["entry_quote"]["ask"] == 18.5 and c["entry_quote"]["spread_pct"] == round(0.5 / 18.25 * 100, 2)
    rows = [json.loads(x) for x in (tmp_path / "observations" / "2026-10-15.jsonl").read_text().splitlines()]
    assert {r["bid"] for r in rows} >= {18.0, 21.0} and all(r["id"] == c["id"] for r in rows)


def ledger(tmp_path):
    q = CountingQuotes()
    lg = PaperLedger(tmp_path, q, capital=500_000, clock=lambda: t(9, 16))
    return lg, q, F.FadeTrader(lg, lambda: sig())


def test_the_1_second_check_feeds_the_held_peak(tmp_path):
    lg, q, ft = ledger(tmp_path)
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(t(9, 16))
    q.set("PE", 1220.0, 19.4, 19.6)                                             # below +10 %: no trail yet
    ft.fast_tick(t(9, 20, 7))
    assert lg.state["positions"][0]["held_bid"]["peak"] == {"price": 19.4, "at": t(9, 20, 7).isoformat(timespec="seconds")}
    assert pk.SOURCE_FAST in lg.state["positions"][0]["held_bid"]["sources"]
