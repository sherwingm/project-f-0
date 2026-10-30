"""The 09:16 counterfactual's pre-registered decision and the recorded walk-choice replay (scanner/fade_entry_0916_cf.py)."""
import pandas as pd

from scanner import fade_entry_0916_cf as cf


def pick(**kw):
    p = {"status": "chosen", "side": "PE", "decided_at": "09:16:00.400", "strike": 1200.0, "ask": 10.0, "lot": 500,
         "lots": 1, "id": "w0916:2026-11-02:X", "follow": {"last": "15:20:59.000", "kotak_polls": 0}}
    p.update(kw)
    return {"picks": {"X": p}}


def row(t, bid, phase="walk_0916", id_="w0916:2026-11-02:X"):
    return {"id": id_, "t": f"2026-11-02T{t}+05:30", "bid": bid, "phase": phase}


BOOKED = {"X": {"strike": 1200.0, "net_pnl": -1200.0, "return_pct": -22.0, "reason": "fade_stop"}}


def test_walk_choice_stop_on_its_own_follow_rows_only():
    obs = [row("09:16:00", 10.0), row("09:16:30", 7.5, id_="P1"), row("09:17:00", 8.4), row("09:18:00", 7.9)]
    (m,) = cf.walk_choice("2026-11-02", pick(), obs, BOOKED)
    assert (m["w_reason"], m["w_exit"], m["w_exit_time"]) == ("stop", 7.9, "09:18:00")      # P1's 7.5 is not its row
    assert m["same_strike"] is True and m["w_qty"] == 500 and m["w_rows"] == 3
    assert m["w_net"] < (7.9 - 10.0) * 500 and m["w_diff_pts"] == round(m["w_net_pct"] + 22.0, 2)


def test_walk_choice_1520_at_the_standing_bid_and_unresolved_without_coverage():
    obs = [row("09:16:00", 10.0), row("12:00:00", 10.6), row("15:19:58", 10.4), row("15:20:30", 9.0)]
    (m,) = cf.walk_choice("2026-11-02", pick(), obs, BOOKED)
    assert (m["w_reason"], m["w_exit"], m["w_exit_time"]) == ("eod", 10.4, "15:20:00")      # not the 15:20:30 row
    (m,) = cf.walk_choice("2026-11-02", pick(follow={"last": "14:00:00.000"}), obs, BOOKED)
    assert m["w_exit"] is None and m["w_by"].startswith("unresolved") and "w_net" not in m


def test_walk_choice_trail_and_not_chosen():
    obs = [row("09:16:00", 10.0), row("09:30:00", 11.0), row("09:31:00", 12.0), row("09:32:00", 11.7)]
    (m,) = cf.walk_choice("2026-11-02", pick(), obs, BOOKED)
    assert (m["w_reason"], m["w_exit"]) == ("trail", 11.7)                                   # 11.7 <= 0.98 x 12.0
    (m,) = cf.walk_choice("2026-11-02", {"picks": {"X": {"status": "none by 09:20", "last_why": "spread"}}}, [], BOOKED)
    assert m["w_status"] == "none by 09:20" and "w_reason" not in m and m["net15_pct"] == -22.0


def pairs(diffs, days, stops15=(), stops16=()):
    rows = []
    for i, (d, day) in enumerate(zip(diffs, days)):
        rows.append({"day": day, "symbol": f"S{i}", "status": "available", "net15_pct": -10.0, "net16_pct": -10.0 + d,
                     "net15": -500.0, "net16": -500.0 + d * 50, "x15_reason": "stop" if i in stops15 else "eod",
                     "x16_reason": "stop" if i in stops16 else "eod", "walk_same": "yes", "replay15_net": -500.0,
                     "e15_price": 10.0, "qty": 500})
    return pd.DataFrame(rows)


def test_decision_waits_for_30_then_passes_or_closes():
    days = [f"2026-11-{d:02d}" for d in range(2, 12) for _ in range(3)]                      # 30 pairs on 10 days
    diffs = [8.0 + (i % 4) for i in range(30)]                                               # day sums differ
    _, v = cf.decision(pairs(diffs[:12], days[:12], stops15={0, 1, 2, 3}), pd.DataFrame())
    assert v["verdict"].startswith("NOT A DECISION")
    _, v = cf.decision(pairs(diffs, days, stops15={0, 1, 2, 3}), pd.DataFrame())
    assert v["verdict"].startswith("PASS") and v["criteria"]["P4"] == "pass" and v["criteria"]["C3"] == "too few"
    _, v = cf.decision(pairs(diffs, days), pd.DataFrame())                                   # no stops avoided
    assert v["verdict"].startswith("INCONCLUSIVE") and v["criteria"]["P4"] == "fail"
    _, v = cf.decision(pairs([0.5 * (-1) ** i for i in range(30)], days), pd.DataFrame())
    assert v["verdict"].startswith("CLOSE")


def test_decision_ignores_27_oct_and_earlier():
    d = pd.concat([pairs([50.0] * 6, ["2026-10-27"] * 6), pairs([1.0, -1.0], ["2026-10-28", "2026-10-29"])])
    _, v = cf.decision(d.reset_index(drop=True), pd.DataFrame())
    assert v["n"] == 2 and v["mean_pts"] == 0.0


def test_decision_judges_at_the_fixed_looks_only():
    days = [f"2026-11-{d:02d}" for d in range(2, 22) for _ in range(3)]                      # 60 pairs on 20 days
    good = [8.0 + (i % 4) for i in range(30)]
    _, v = cf.decision(pairs(good + [-30.0] * 30, days, stops15=set(range(8))), pd.DataFrame())
    assert v["look"] == 1 and v["upto"] == "2026-11-11" and v["verdict"].startswith("PASS")   # later days ignored
    mid = [3.0 + (i % 4) for i in range(60)]                                                 # mean 4.5: P1 fails
    _, v = cf.decision(pairs(mid, days, stops15=set(range(8))), pd.DataFrame())
    assert v["look"] == 2 and v["verdict"].startswith("CLOSE: still not a pass")


def test_exit_v12_uses_live_rounded_levels_and_stops_checking_at_1520():
    rows = lambda *tb: [{"t": t, "bid": b, "src": "x"} for t, b in tb]                     # noqa: E731
    x = cf.exit_v12(rows(("09:17:00", 3.30), ("09:18:00", 3.23)), 3.0, {}, None)
    assert (x["reason"], x["price"]) == ("trail", 3.23)                                      # 1.1 x 3.0 = 3.3000000000000003
    assert cf.exit_v12(rows(("09:17:00", 7.36)), 9.2, {}, None)["reason"] == "stop"          # 0.8 x 9.2 = 7.3599999
    assert cf.exit_v12(rows(("15:20:00", 1.0)), 9.2, {}, None)["reason"] is None             # 15:20: the sale, not a stop
