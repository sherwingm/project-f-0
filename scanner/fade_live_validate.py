"""Read-only validation of the first measured paper trades: do the stored records hold together?

    python -m scanner.fade_live_validate [path/to/paper_ledger.json] [path/to/observations_dir]

Default source: the public paper-state branch (ledger, and the bid/ask record of finished days). For every closed trade
carrying the measurement fields it prints PASS / FAIL / WAIT per check:
  entry   contract fields, IST times, entry quote (bid, ask, spread recomputed), last-trade time, age and stale flag
  held    peak / low present, inside the held window, equal to the max / min of the record's held bids
  exit    exit price and reason; a bid-priced exit is the held window's last bid
  after   post-exit rows exist, start after the exit, stop by the 60-minute cutoff, never earlier than the sale
  capture net at the peak re-derived with the same charges; capture N/A exactly when the peak never paid
  backup  the day's record is on GitHub (WAIT until the day is over)
Changes nothing. Trades without the fields are listed as "not measured", never reconstructed.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from server import charges as ch
from server.peak import POST_EXIT_MINUTES

from .fade_live_checkpoint import load_ledger, load_obs


def check_trade(c: dict, rows: list[dict], backed_up: bool | None) -> list[tuple[str, str, str]]:
    out = []

    def add(area, ok, msg):
        out.append((area, "PASS" if ok is True else "WAIT" if ok is None else "FAIL", msg))

    eq, pc, hb = c.get("entry_quote") or {}, c.get("peak_capture") or {}, c.get("held_bid") or {}
    opened, closed = datetime.fromisoformat(c["opened_at"]), datetime.fromisoformat(c["closed_at"])
    add("entry", all(c.get(k) for k in ("symbol", "instrument", "expiry", "tradingsymbol")) and c.get("strike") is not None,
        f"{c['tradingsymbol']} {c['instrument']} {c['strike']} exp {c['expiry']}")
    add("entry", c["opened_at"].endswith("+05:30") and c["closed_at"].endswith("+05:30"), "times in IST (+05:30)")
    if eq.get("bid") and eq.get("ask"):
        mid = (eq["bid"] + eq["ask"]) / 2
        add("entry", abs(round((eq["ask"] - eq["bid"]) / mid * 100, 2) - (eq.get("spread_pct") or -1)) < 0.011,
            f"bid {eq['bid']} ask {eq['ask']} spread {eq.get('spread_pct')} %")
    else:
        add("entry", False, f"entry bid/ask missing ({eq.get('bid')} / {eq.get('ask')})")
    add("entry", "ltt" in eq and "stale_ltt" in eq,
        f"last trade {eq.get('ltt')} · age {eq.get('ltt_age_s')} s · stale {eq.get('stale_ltt')} ({eq.get('stale_ltt_reason')})")
    add("entry", c["entry"]["price"] == eq.get("ask") or eq.get("ask") is None,
        f"fill {c['entry']['price']} vs entry ask {eq.get('ask')}")
    held = [r for r in rows if r["id"] == c["id"] and r.get("phase", "held") == "held" and r.get("bid")
            and r.get("via") != "entry quote"]
    if hb.get("peak"):
        pk_at = datetime.fromisoformat(hb["peak"]["at"])
        add("held", opened <= pk_at <= closed, f"peak bid {hb['peak']['price']} at {hb['peak']['at'][11:19]}, "
                                                f"low {hb['low']['price']} at {hb['low']['at'][11:19]}")
        if held:
            add("held", max(r["bid"] for r in held) <= hb["peak"]["price"] + 1e-9 and
                min(r["bid"] for r in held) >= hb["low"]["price"] - 1e-9,
                f"record's held bids {min(r['bid'] for r in held)}-{max(r['bid'] for r in held)} inside peak/low "
                f"({len(held)} rows; longest gap {hb.get('max_gap_s')} s)")
        else:
            add("held", None, "the day's record is not on GitHub yet")
        add("held", "estimated" in (pc.get("basis") or ""), f"peak labelled an estimate; bid size at peak "
                                                             f"{pc.get('peak_bid_qty')} (lot fits: {pc.get('lot_fits_at_peak')})")
    else:
        add("held", False, "no held bid peak")
    add("exit", c.get("reason") is not None, f"exit {c['exit']['price']} at {c['closed_at'][11:19]} ({c.get('reason')})")
    if c.get("reason") in ("fade_stop", "fade_trail") and hb.get("last"):
        add("exit", abs(hb["last"]["price"] - c["exit"]["price"]) < 1e-9, "the exit bid is the held window's last bid")
    after = sorted((r for r in rows if r["id"] == c["id"] and r.get("phase") == "after_exit"), key=lambda r: r["t"])
    until = closed + timedelta(minutes=POST_EXIT_MINUTES)
    if after:
        ts = [datetime.fromisoformat(r["t"]) for r in after]
        add("after", ts[0] >= closed and ts[-1] <= until + timedelta(seconds=1),
            f"{len(after)} post-exit rows {after[0]['t'][11:19]}-{after[-1]['t'][11:19]} (cutoff {until.strftime('%H:%M:%S')})")
        gaps = [(b - a).total_seconds() for a, b in zip(ts, ts[1:])]
        add("after", True, f"longest post-exit gap {max(gaps) if gaps else 0:.0f} s; sources {sorted({r.get('src') for r in after})}")
    else:
        add("after", None if rows == [] else False, "no post-exit rows (record not on GitHub yet, or none written)")
    if pc:
        e, q = c["entry"]["price"], c["qty"]
        peak_net = round((pc["peak_bid"] - e) * q - c["entry_charges"] - ch.leg(c["instrument"], "SELL", q, pc["peak_bid"])["total"], 2)
        add("capture", abs(peak_net - pc["peak_net"]) < 0.02, f"net at peak {pc['peak_net']} (re-derived {peak_net}); "
                                                              f"realised {c['net_pnl']}; left {pc['giveback_rs']}")
        add("capture", (pc["capture_pct"] is None) == (pc["peak_net"] <= 0), f"captured {pc['capture_pct']} %"
                                                                               f"{' (' + pc['capture_note'] + ')' if pc.get('capture_note') else ''}")
    add("backup", backed_up, "the day's bid/ask record is on GitHub" if backed_up else
        "WAIT: backed up once the day is over" if backed_up is None else "the day's record is missing on GitHub")
    return out


def main() -> None:
    led = load_ledger(sys.argv[1] if len(sys.argv) > 1 else None)
    local = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    cache: dict = {}
    measured = [c for c in led.get("closed", []) if c.get("peak_capture") or c.get("entry_quote")]
    print(f"{len(measured)} measured closed trade(s); {len(led.get('closed', [])) - len(measured)} older trades not measured")
    today = datetime.now().date().isoformat()
    for c in measured:
        day = c["opened_at"][:10]
        if local:
            f = local / f"{day}.jsonl"
            rows = [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []
        else:
            rows = load_obs(day, cache)
        backed = True if rows else (None if day >= today else False)
        print(f"\n== {c['symbol']} {c['instrument']} {c['strike']} · {c['opened_at'][:19]} -> {c['closed_at'][11:19]}")
        for area, st, msg in check_trade(c, rows, backed):
            print(f"  {st:4} {area:7} {msg}")


if __name__ == "__main__":
    main()
