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
    assert lg.state["positions"][0]["held_bid"]["peak"] == {"price": 19.4, "at": t(9, 20, 7).isoformat(timespec="seconds"),
                                                            "qty": 5000}
    assert pk.SOURCE_FAST in lg.state["positions"][0]["held_bid"]["sources"]


# ---------------------------------------------------------------- audit fixes (23 Oct)
def test_an_exit_priced_from_the_last_trade_is_not_a_bid_observation(tmp_path):
    lg, q, ft = ledger(tmp_path)
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(t(9, 16))
    pos = lg.state["positions"][0]
    lg.close_at(pos["id"], 25.0, t(15, 20), "fade_eod", price_is_bid=False)    # ltp - tick, no bid then
    c = lg.state["closed"][-1]
    assert c["peak_capture"] is None or c["peak_capture"]["peak_bid"] != 25.0
    assert pk.SOURCE_EXIT not in ((c["held_bid"] or {}).get("sources") or [])


def test_bid_size_at_the_peak_says_whether_the_lot_fitted():
    pos = {}
    pk.observe(pos, 10.0, t(9, 16), pk.SOURCE_POLL, qty=5000)
    pk.observe(pos, 12.0, t(9, 17), pk.SOURCE_POLL, qty=100)                   # peak, but only 100 bid
    c = pk.capture(10.0, 350, "PE", 20.0, pos["held_bid"], 11.0, 300.0)
    assert c["peak_bid_qty"] == 100 and c["lot_fits_at_peak"] is False and "estimated" in c["basis"]
    pk.observe(pos, 13.0, t(9, 18), pk.SOURCE_POLL)                             # size unknown
    assert pk.capture(10.0, 350, "PE", 20.0, pos["held_bid"], 11.0, 300.0)["lot_fits_at_peak"] is None


def test_the_longest_gap_between_observations_is_kept():
    pos = {}
    for s in (0, 1, 2, 47):
        pk.observe(pos, 10.0 + s / 100, t(9, 16, s), pk.SOURCE_POLL)
    assert pos["held_bid"]["max_gap_s"] == 45.0


def test_the_closed_record_is_a_copy_later_quotes_cannot_reach(tmp_path):
    lg, q, ft = ledger(tmp_path)
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(t(9, 16))
    pos = lg.state["positions"][0]
    lg.close_at(pos["id"], 18.0, t(9, 20), "fade_stop")
    pk.observe(pos, 99.0, t(9, 21), pk.SOURCE_POLL)                            # the old dict, touched after the exit
    assert lg.state["closed"][-1]["held_bid"]["peak"]["price"] == 18.0


def test_the_live_checkpoint_reads_measured_trades_and_their_first_minutes(tmp_path, monkeypatch):
    from scanner import fade_live_checkpoint as K
    lg, q, ft = ledger(tmp_path)
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(t(9, 16))
    q.set("PE", 1220.0, 20.5, 20.8)
    lg.on_poll(now=t(9, 16, 40))
    lg.close_at(lg.state["positions"][0]["id"], 20.1, t(9, 17, 30), "fade_trail")
    obs = [json.loads(x) for x in (tmp_path / "observations" / "2026-10-15.jsonl").read_text().splitlines()]
    d = K.rows(lg.state, {"2026-10-15": obs})
    assert len(d) == 1 and d["peak bid"].iat[0] == 20.5 and d["entry spread %"].iat[0] is not None
    assert d["bid max up 1 min %"].iat[0] == round((20.5 / 18.5 - 1) * 100, 1)
    s = K.summary(d)
    assert s["closed trades measured"].iat[0] == 1 and s["target"].iat[0] == 30


# ---------------------------------------------------------------- post-exit series and entry freshness (24 Oct)
def test_the_entry_quote_keeps_its_last_trade_time(tmp_path):
    lg, q, ft = ledger(tmp_path)
    q.set("PE", 1220.0, 18.0, 18.5)
    q.book["HCLTECH26OCT1220PE"]["timestamp"] = "2026-10-15 09:16:30"
    ft.on_poll(t(9, 17))
    assert lg.state["positions"][0]["entry_quote"]["ltt"] == "2026-10-15 09:16:30"


def test_the_fade_waits_for_the_first_trade_today_instead_of_buying_yesterdays_book(tmp_path):
    lg, q, ft = ledger(tmp_path)                                    # 27 Oct 2026: bought at 09:15:01 at yesterday's ask
    q.set("PE", 1220.0, 18.0, 18.5)
    q.book["HCLTECH26OCT1220PE"]["timestamp"] = "2026-10-14 15:29:59"
    ft.on_poll(t(9, 16))
    assert lg.state["positions"] == [] and not lg.state["rules"]["refused"]
    assert "first trade today" in lg.state["rules"]["fade_wait"]["2026-10-15:HCLTECH"]["reason"]
    q.set("PE", 1220.0, 9.0, 9.2)                                    # the first real trade, at half the old price
    q.book["HCLTECH26OCT1220PE"]["timestamp"] = "2026-10-15 09:16:02"
    ft.on_poll(t(9, 18))
    pos = lg.state["positions"][0]
    assert pos["entry"]["price"] == 9.2 and pos["entry_quote"]["stale_ltt"] is False


def test_the_post_exit_series_runs_60_minutes_apart_from_the_held_peak(tmp_path):
    lg, q, ft = ledger(tmp_path)
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(t(9, 16))
    lg.close_at(lg.state["positions"][0]["id"], 18.0, t(9, 20), "fade_stop")
    c = lg.state["closed"][-1]
    assert c["post_exit_until"] == t(10, 20).isoformat(timespec="seconds")
    lg._post_exit_series(t(9, 20, 10))                                          # Kotak only: the first record
    q.set("PE", 1220.0, 25.0, 25.3)
    lg._post_exit_series(t(9, 20, 20))                                          # 10 s later: throttled (30 s)
    lg._post_exit_series(t(9, 20, 45))                                          # 35 s later: recorded
    lg._post_exit_series(t(10, 21))                                             # past 60 minutes: nothing
    rows = [json.loads(x) for x in (tmp_path / "observations" / "2026-10-15.jsonl").read_text().splitlines()]
    after = [r for r in rows if r["phase"] == "after_exit"]
    assert [r["bid"] for r in after] == [18.0, 25.0] and all(r["id"] == c["id"] for r in after)
    assert c["held_bid"]["peak"]["price"] == 18.0 and c["peak_capture"]["peak_bid"] == 18.0   # untouched by 25.0


def test_the_post_exit_series_records_every_poll_while_streaming(tmp_path):
    lg, q, ft = ledger(tmp_path)
    q.streaming = lambda: True
    q.set("PE", 1220.0, 18.0, 18.5)
    ft.on_poll(t(9, 16))
    lg.close_at(lg.state["positions"][0]["id"], 18.0, t(9, 20), "fade_stop")
    for s, b in ((1, 18.1), (2, 18.2), (3, 18.3)):
        q.set("PE", 1220.0, b, b + 0.3)
        lg._post_exit_series(t(9, 21, s))
    rows = [json.loads(x) for x in (tmp_path / "observations" / "2026-10-15.jsonl").read_text().splitlines()]
    assert [r["bid"] for r in rows if r["phase"] == "after_exit"] == [18.1, 18.2, 18.3]


# ---------------------------------------------------------------- last-trade age (task 1) and the running commit (task 2)
@pytest.mark.parametrize("ltt, now, stale, reason", [
    ("2026-10-15 09:15:58", t(9, 16), False, None),                                   # fresh: 2 s old
    ("2026-10-14 15:39:53", t(9, 15), True, "last trade before today's 09:15 open"),  # ADANIENSOL's case
    ("2026-10-15 09:20:00", t(9, 30), True, "last trade more than 5 min old"),
    (None, t(9, 16), None, "no last-trade time in the quote"),
    ("not a time", t(9, 16), None, "unreadable last-trade time 'not a time'"),
    ("2026-10-15 10:00:00", t(9, 16), None, "last-trade time is after the entry (clock mismatch)"),
])
def test_last_trade_age_and_the_stale_flag(ltt, now, stale, reason):
    a = pk.ltt_age(ltt, now)
    assert a["stale_ltt"] is stale and a["stale_ltt_reason"] == reason
    if ltt == "2026-10-14 15:39:53":
        assert a["ltt_age_s"] == 63307.0                                               # 17 h 35 min 7 s


def test_an_old_trade_from_today_is_flagged_but_still_bought_at_its_price(tmp_path):
    lg, q, ft = ledger(tmp_path)                                    # only yesterday's book waits (27 Oct 2026)
    q.set("PE", 1220.0, 18.0, 18.5)
    q.book["HCLTECH26OCT1220PE"]["timestamp"] = "2026-10-15 09:15:10"
    ft.on_poll(t(11, 0))
    p = lg.state["positions"][0]
    assert p["entry"]["price"] == 18.5 and p["entry_quote"]["stale_ltt"] is True             # a warning, not a refusal


def test_the_running_commit_comes_from_git_or_is_none(tmp_path, monkeypatch):
    from server.version import deployed
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    assert deployed(tmp_path) == {"commit": None, "commit_source": None}                  # no checkout
    g = tmp_path / ".git"
    (g / "refs" / "heads").mkdir(parents=True)
    (g / "HEAD").write_text("ref: refs/heads/main\n")
    (g / "refs" / "heads" / "main").write_text("8bac3c5a1234567890abcdef\n")
    assert deployed(tmp_path) == {"commit": "8bac3c5a", "commit_source": "git"}
    (g / "refs" / "heads" / "main").unlink()
    (g / "packed-refs").write_text("# pack\n0123456789abcdef refs/heads/main\n")
    assert deployed(tmp_path)["commit"] == "01234567"                                    # after git gc
    monkeypatch.setenv("GIT_COMMIT", "feedbeef99")
    assert deployed(tmp_path) == {"commit": "feedbeef", "commit_source": "env"}


# ---------------------------------------------------------------- task 3: the post-exit record never holds the ledger lock
def test_post_exit_quotes_are_fetched_outside_the_ledger_lock_in_one_call(tmp_path):
    import threading
    import time as _t
    lg, q, ft = ledger(tmp_path)
    for k in (1180.0, 1200.0, 1220.0):
        q.set("PE", k, 18.0, 18.5)
    ft.on_poll(t(9, 16))
    lg.close_at(lg.state["positions"][0]["id"], 18.0, t(9, 20), "fade_stop")
    for k in (1180.0, 1200.0):                                    # two more sales close together
        c = {**lg.state["closed"][-1]}
        c.update(id=f"X{int(k)}", strike=k, tradingsymbol=f"HCLTECH26OCT{int(k)}PE")
        lg.state["closed"].append(c)
    calls, inside = [], threading.Event()
    real = q.get_many

    def slow(cs):                                                 # a slow broker: 0.3 s per call
        calls.append(len(cs))
        inside.set()
        _t.sleep(0.3)
        return real(cs)
    q.get_many = slow
    th = threading.Thread(target=lg._post_exit_series, args=(t(9, 21),))
    th.start()
    assert inside.wait(2)
    a = _t.perf_counter()
    got = lg.lock.acquire(timeout=0.1)                            # a trading check needs the lock meanwhile
    waited = _t.perf_counter() - a
    if got:
        lg.lock.release()
    th.join()
    assert got and waited < 0.1                                   # not blocked by the slow call
    assert calls == [3]                                           # three trades, one batched call


# ---------------------------------------------------------------- task 5: the live-trade validator on a simulated day
def test_the_validator_passes_a_consistent_trade_and_catches_a_tampered_one(tmp_path):
    from scanner.fade_live_validate import check_trade
    lg, q, ft = ledger(tmp_path)
    q.set("PE", 1220.0, 18.0, 18.5)
    q.book["HCLTECH26OCT1220PE"]["timestamp"] = "2026-10-15 09:15:58"
    ft.on_poll(t(9, 16))
    q.set("PE", 1220.0, 21.0, 21.3)
    lg.on_poll(now=t(9, 18))
    lg.close_at(lg.state["positions"][0]["id"], 20.5, t(9, 20), "fade_trail")
    q.set("PE", 1220.0, 22.0, 22.3)
    lg._post_exit_series(t(9, 21))
    rows = [json.loads(x) for x in (tmp_path / "observations" / "2026-10-15.jsonl").read_text().splitlines()]
    c = lg.state["closed"][-1]
    res = check_trade(c, rows, True)
    assert [r for r in res if r[1] == "FAIL"] == [], res
    bad = json.loads(json.dumps(c))
    bad["peak_capture"]["peak_net"] += 500                                    # tampered: no longer re-derivable
    assert any(r[0] == "capture" and r[1] == "FAIL" for r in check_trade(bad, rows, True))
