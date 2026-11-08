"""server/peak.py read_path: one trade's recorded bid / ask rows for the results page's trade chart."""
import json

from server import peak as pk


def write(d, day, rows):
    d.mkdir(exist_ok=True)
    (d / f"{day}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def row(pid, t, bid, phase="held"):
    return {"id": pid, "t": t, "bid": bid, "ask": bid + 0.2, "ltp": bid, "phase": phase, "ts": "X"}


def test_only_this_trade_and_only_its_days_oldest_first(tmp_path):
    d = tmp_path / "observations"
    write(d, "2026-11-05", [row("P-1", "2026-11-05T09:15:01+05:30", 9.0), row("P-2", "2026-11-05T09:15:01+05:30", 4.0)])
    write(d, "2026-11-06", [row("P-1", "2026-11-06T10:00:00+05:30", 11.0, "after_exit"),
                            row("P-1", "2026-11-06T09:20:00+05:30", 10.0)])
    write(d, "2026-11-07", [row("P-1", "2026-11-07T09:15:00+05:30", 99.0)])          # after the trade's last day
    (d / "2026-11-06.jsonl").open("a", encoding="utf-8").write("not json P-1\n")      # a torn line is skipped
    rows = pk.read_path(d, "P-1", "2026-11-05", "2026-11-06")
    assert [r["bid"] for r in rows] == [9.0, 10.0, 11.0]
    assert rows[-1]["phase"] == "after_exit" and set(rows[0]) == {"t", "bid", "ask", "ltp", "phase"}


def test_a_long_record_is_thinned_but_keeps_the_peak_and_the_dip(tmp_path):
    d = tmp_path / "observations"
    bids = [10.0 + (i % 7) * 0.1 for i in range(5000)]
    bids[1234], bids[4321] = 30.0, 1.0
    write(d, "2026-11-06", [row("P-1", f"2026-11-06T09:{i // 600 + 15:02d}:{(i // 10) % 60:02d}.{i % 10}", b) for i, b in enumerate(bids)])
    rows = pk.read_path(d, "P-1", "2026-11-06", "2026-11-06", max_rows=400)
    assert len(rows) <= 400 and max(r["bid"] for r in rows) == 30.0 and min(r["bid"] for r in rows) == 1.0
    assert [r["t"] for r in rows] == sorted(r["t"] for r in rows)


def test_no_records_no_rows(tmp_path):
    assert pk.read_path(tmp_path / "missing", "P-1", "2026-11-05", "2026-11-06") == []


# ---------------------------------------------------------------- day edges (the gap-open column)
def hrow(pid, t, bid, phase="held"):
    return json.dumps({"id": pid, "t": t, "ts": "X", "bid": bid, "bid_qty": 1, "ask": bid + 0.2, "ask_qty": 1, "ltp": bid,
                       "ltt": None, "spot": 1, "src": "s", "via": "s", "phase": phase}, separators=(",", ":")) + "\n"


def test_day_edges_open_is_the_bid_standing_at_0916_and_last_is_the_close(tmp_path):
    d = tmp_path / "observations"
    d.mkdir()
    (d / "2026-11-05.jsonl").write_text(hrow("P-1", "2026-11-05T09:15:30+05:30", 10.0) + hrow("P-1", "2026-11-05T15:29:00+05:30", 12.0)
                                        + hrow("P-1", "2026-11-05T15:40:00+05:30", 99.0)               # after the close: ignored
                                        + hrow("P-2", "2026-11-05T09:30:00+05:30", 5.0), encoding="utf-8")
    (d / "2026-11-06.jsonl").write_text(hrow("P-1", "2026-11-06T09:15:20+05:30", 13.0)                 # stale book before 09:16
                                        + hrow("P-1", "2026-11-06T09:15:58+05:30", 18.0)               # the bid standing at 09:16
                                        + hrow("P-1", "2026-11-06T09:16:30+05:30", 20.0)
                                        + hrow("P-1", "2026-11-06T10:00:00+05:30", 7.0, "after_exit"), encoding="utf-8")
    e = pk.day_edges(d)
    assert e["P-1"] == [["2026-11-05", 10.0, 12.0], ["2026-11-06", 18.0, 20.0]]      # gap = 18 / 12 - 1 = +50 %
    assert e["P-2"] == [["2026-11-05", 5.0, 5.0]]                                    # first bid after 09:16 when none stood before


def test_day_edges_reads_only_new_bytes_and_waits_for_a_half_written_line(tmp_path):
    d = tmp_path / "observations"
    d.mkdir()
    f = d / "2026-11-06.jsonl"
    f.write_text(hrow("P-1", "2026-11-06T09:15:58+05:30", 18.0), encoding="utf-8")
    assert pk.day_edges(d)["P-1"] == [["2026-11-06", 18.0, 18.0]]
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(hrow("P-1", "2026-11-06T11:00:00+05:30", 25.0)[:40])                 # the writer is mid-line
    assert pk.day_edges(d)["P-1"] == [["2026-11-06", 18.0, 18.0]]
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(hrow("P-1", "2026-11-06T11:00:00+05:30", 25.0)[40:])                 # the line completes
    assert pk.day_edges(d)["P-1"] == [["2026-11-06", 18.0, 25.0]]


# ---------------------------------------------------------------- a special session (the Muhurat) inside the day edges
def test_the_muhurat_session_is_the_previous_close_of_the_next_gap(tmp_path):
    m = tmp_path / "muhurat"
    m.mkdir()
    (m / "2026-11-08.json").write_text(json.dumps({"prices": {"X26NOV100CE": {"open": 12.0, "close": 15.0},
                                                              "Y26NOV100CE": {"open": 3.0, "close": 4.0}}}), encoding="utf-8")
    (m / "broken.json").write_text("not json", encoding="utf-8")                           # skipped, never raises
    sp = pk.special_sessions(m)
    assert sp == {"2026-11-08": {"X26NOV100CE": [12.0, 15.0], "Y26NOV100CE": [3.0, 4.0]}}
    edges = {"P-1": [["2026-11-06", 10.0, 11.0], ["2026-11-09", 18.0, 17.0]], "P-3": [["2026-11-06", 7.0, 8.0]]}
    trades = [("P-1", "X26NOV100CE", "2026-11-03", None),                                  # open through it
              ("P-2", "Y26NOV100CE", "2026-11-03", "2026-11-06"),                          # sold on Friday: not held
              ("P-3", "Z26NOV100CE", "2026-11-03", None),                                  # did not trade in it
              ("P-4", "X26NOV100CE", "2026-11-09", None)]                                  # bought after it
    out = pk.add_special_rows(edges, trades, sp)
    assert out["P-1"] == [["2026-11-06", 10.0, 11.0], ["2026-11-08", 12.0, 15.0, "Muhurat"], ["2026-11-09", 18.0, 17.0]]
    assert "P-2" not in out and "P-4" not in out and out["P-3"] == [["2026-11-06", 7.0, 8.0]]
    assert pk.add_special_rows(out, trades, sp)["P-1"] == out["P-1"]                       # idempotent
    # the gaps the page computes: Muhurat open vs Friday's last, then Monday's open vs the Muhurat close
    r = out["P-1"]
    assert round((r[1][1] / r[0][2] - 1) * 100, 1) == 9.1 and round((r[2][1] / r[1][2] - 1) * 100, 1) == 20.0


# ---------------------------------------------------------------- the after-sale path beyond the first hour (T-2)
from datetime import datetime  # noqa: E402

from server.sessions import IST  # noqa: E402

from .test_fade import EXP, setup  # noqa: E402,F401  (pytest fixture)


def tt(h, m, s=0):
    return datetime(2026, 10, 15, h, m, s, tzinfo=IST)


def test_the_after_sale_path_is_recorded_every_two_minutes_and_on_a_new_extreme(setup):  # noqa: F811
    lg, q, ft, _ = setup
    ts = "X26OCT100CE"
    lg.state["closed"] = [{"id": "P-9", "symbol": "X", "instrument": "CE", "expiry": EXP, "strike": 100.0, "tradingsymbol": ts, "lot_size": 100,
                           "rule": {"arms": ["A"]}, "post_exit_until": tt(9, 0).isoformat(),       # the first hour is long over
                           "after": {"until": EXP, "peak": None, "trough": None, "last": None}}]

    def quote(bid):
        q.book[ts] = {"last_price": bid + 0.1, "depth": {"bid": [(bid, 100)], "ask": [(bid + 0.2, 100)]}}

    def rows():
        f = lg.obs.dir / "2026-10-15.jsonl"
        return [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []
    quote(7.0)
    lg._follow_closed(tt(10, 0))
    assert [r["bid"] for r in rows()] == [7.0] and rows()[0]["phase"] == "after_exit" and rows()[0]["id"] == "P-9"
    quote(7.2)                                                       # a new highest bid: recorded at once
    lg._follow_closed(tt(10, 0, 5))
    quote(7.1)                                                       # nothing new, 10 s later: throttled
    lg._follow_closed(tt(10, 0, 15))
    assert [r["bid"] for r in rows()] == [7.0, 7.2]
    quote(7.15)                                                      # 2 minutes after the last row: recorded
    lg._follow_closed(tt(10, 2, 6))
    assert [r["bid"] for r in rows()] == [7.0, 7.2, 7.15]
    lg.state["closed"][0]["post_exit_until"] = tt(11, 0).isoformat()                       # inside the first hour: that is another recorder's
    quote(9.0)
    lg._follow_closed(tt(10, 30))
    assert [r["bid"] for r in rows()][-1] == 7.15
