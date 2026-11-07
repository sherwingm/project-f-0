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
