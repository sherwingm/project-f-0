"""Read-only: each live fade trade against the price the v12 backtest would have booked for it.

    python -m scanner.fade_live_vs_backtest [DATA_DIR] [YYYY-MM-DD]     (default: data, every day with closed fade trades)

The backtest (scanner/fade_stop_trail.py, strategies/S1_fade_realistic_entry.md) prices on 1-minute LAST-TRADE candles:
  entry B   the 09:16 candle's open + 1 tick (entry A, the older one: the day's open + 1 tick)
  stop      the -20 % level - 1 tick (a candle low touching it)
  trail     the trail level (0.98 x the peak) - 1 tick
  15:20     the 15:19 candle's close - 1 tick
Live prices them on the BOOK: the real-order fill (buy at the ask, sell at the bid). Per trade this prints the live
real-order net, the live instant net, the backtest-style net, and the gap split into entry and exit, in Rs and in % of
the premium. Backtest-style prices come from the day's own records:
  entry B   the first last-trade at or after 09:16:00 in the entry probe (data/entry_probe/<date>.json)
  entry A   the probe's day open
  exit      the rule's trigger level from the trade (stop level, trail level); for 15:20 the last traded price before
            15:20 in the bid/ask record (data/observations/<date>.jsonl)
These are approximations of a candle (a candle's open is the first trade of the minute; the probe stores a row only
when the book changes), labelled as such. Missing data is reported as missing, never filled in.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from server import charges as ch
from server import order_sim as om


def _hms(v) -> str | None:
    s = str(v or "")
    return s[-8:] if len(s) >= 8 else None


def entry_b(probe: dict, sym: str, side: str, strike: float) -> tuple[float | None, float | None]:
    """(first last-trade price at/after 09:16:00, the day's open) for one contract from the entry probe."""
    cols = probe.get("cols") or []
    ix = {c: i for i, c in enumerate(cols)}
    rows = [r for r in probe.get("rows") or [] if r[ix["symbol"]] == sym and r[ix["side"]] == side
            and float(r[ix["strike"]]) == float(strike)]
    b = next((r[ix["ltp"]] for r in rows if (_hms(r[ix["ltt"]]) or "") >= "09:16:00" and r[ix["ltp"]]), None)
    op = next((r[ix["open"]] for r in rows if r[ix["open"]]), None)
    return b, op


def last_ltp_before(rows: list[dict], tid: str, cut: str = "15:20:00") -> float | None:
    mine = [r for r in rows if r["id"] == tid and r.get("ltp") and r["t"][11:19] < cut]
    return mine[-1]["ltp"] if mine else None


def compare(c: dict, probe: dict, rows: list[dict]) -> dict:
    r = c.get("rule") or {}
    q, inst = c["qty"], c["instrument"]
    tick = om.tick_for(r.get("spot_at_entry"))

    def net(buy, sell):
        if buy is None or sell is None:
            return None
        return round((sell - buy) * q - ch.leg(inst, "BUY", q, buy)["total"] - ch.leg(inst, "SELL", q, sell)["total"], 2)

    b, op = entry_b(probe, c["symbol"], inst, c["strike"])
    eb = round(b + tick, 2) if b else None
    ea = round(op + tick, 2) if op else None
    reason = c.get("reason")
    if reason == "fade_stop":
        xb = round((r.get("stop") or {}).get("level", 0) - tick, 2) or None
    elif reason == "fade_trail":
        lv = (r.get("trail") or {}).get("level")
        xb = round(lv - tick, 2) if lv else None
    elif reason in ("fade_eod", "fade_late"):
        lp = last_ltp_before(rows, c["id"])
        xb = round(max(tick, lp - tick), 2) if lp else None
    else:
        xb = None
    prem = c["entry"]["price"] * q
    bt = net(eb, xb)
    out = {"stock": c["symbol"], "contract": f"{inst} {c['strike']:g}", "reason": reason,
           "opened": c["opened_at"][11:19], "closed": c["closed_at"][11:19],
           "live_entry": c["entry"]["price"], "bt_entry_B": eb, "bt_entry_A": ea,
           "live_exit": c["exit"]["price"], "bt_exit": xb,
           "live_net": c["net_pnl"], "instant_net": (c.get("instant") or {}).get("net"), "bt_net": bt,
           "gap_rs": None if bt is None else round(c["net_pnl"] - bt, 2),
           "entry_gap_rs": None if eb is None else round((eb - c["entry"]["price"]) * q, 2),
           "exit_gap_rs": None if xb is None else round((c["exit"]["price"] - xb) * q, 2)}
    out["gap_pct"] = None if out["gap_rs"] is None or not prem else round(out["gap_rs"] / prem * 100, 2)
    out["live_pct"] = round(c["net_pnl"] / prem * 100, 2) if prem else None
    out["bt_pct"] = None if bt is None or not prem else round(bt / prem * 100, 2)
    return out


def main() -> None:
    data = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    only = sys.argv[2] if len(sys.argv) > 2 else None
    led = json.loads((data / "paper_ledger.json").read_text(encoding="utf-8"))
    trades = [c for c in led.get("closed", []) if (c.get("rule") or {}).get("strategy") == "fade"
              and (only is None or c["opened_at"][:10] == only)]
    if not trades:
        print("no closed fade trades" + (f" on {only}" if only else ""))
        return
    out = []
    for c in trades:
        day = c["opened_at"][:10]
        pf, of = data / "entry_probe" / f"{day}.json", data / "observations" / f"{day}.jsonl"
        probe = json.loads(pf.read_text()) if pf.exists() else {}
        rows = [json.loads(x) for x in of.read_text(encoding="utf-8").splitlines() if x.strip()] if of.exists() else []
        out.append(compare(c, probe, rows))
    f = lambda v: "missing" if v is None else f"{v:,.2f}" if isinstance(v, float) else str(v)   # noqa: E731
    keys = ["stock", "contract", "reason", "opened", "live_entry", "bt_entry_B", "bt_entry_A", "live_exit", "bt_exit",
            "live_net", "instant_net", "bt_net", "gap_rs", "entry_gap_rs", "exit_gap_rs", "live_pct", "bt_pct", "gap_pct"]
    print(" | ".join(keys))
    for o in out:
        print(" | ".join(f(o[k]) for k in keys))
    ok = [o for o in out if o["bt_net"] is not None]
    if ok:
        print(f"\n{len(ok)} of {len(out)} trades priced both ways: live real-order net Rs {sum(o['live_net'] for o in ok):,.2f}, "
              f"backtest-style net Rs {sum(o['bt_net'] for o in ok):,.2f}, gap Rs {sum(o['gap_rs'] for o in ok):,.2f} "
              f"(entry {sum(o['entry_gap_rs'] or 0 for o in ok):,.2f}, exit {sum(o['exit_gap_rs'] or 0 for o in ok):,.2f}); "
              f"mean gap {sum(o['gap_pct'] for o in ok) / len(ok):.2f} % of premium a trade (the backtest's v12 mean: +3.25 %)")
    print("Backtest-style prices are last-trade approximations of 1-minute candles (see the module doc).")


if __name__ == "__main__":
    main()
