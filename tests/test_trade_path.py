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
