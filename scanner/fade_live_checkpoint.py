"""S1 fade · live peak-capture checkpoint: the closed fade trades measured on LIVE best bids (server/peak.py).

    python -m scanner.fade_live_checkpoint [path/to/paper_ledger.json]

Default source: the paper-state branch (raw.githubusercontent.com; the repo is public). Uses only trades closed
after the measurement deploy (they carry `peak_capture`). Early moves come from the bid/ask record
data/observations/<date>.jsonl on the same branch (finished days only). v12 stays the control; this is a
diagnostic, not a test: the target is 30 trades (strategies/S1_fade_entry_quality_audit.md). Writes
data/results/S1_fade_live_checkpoint.md and .xlsx.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

import pandas as pd
import requests

from .build import ROOT
from .fade_entry_quality import md_table

RES = ROOT / "data" / "results"
RAW = "https://raw.githubusercontent.com/sherwingm/project-f-0/paper-state/data/"
TARGET = 30


def load_ledger(path: str | None) -> dict:
    if path:
        return json.loads(open(path, encoding="utf-8").read())
    r = requests.get(RAW + "paper_ledger.json", timeout=30)
    r.raise_for_status()
    return r.json()


def load_obs(day: str, cache: dict) -> list[dict]:
    if day not in cache:
        r = requests.get(RAW + f"observations/{day}.jsonl", timeout=30)
        cache[day] = [json.loads(x) for x in r.text.splitlines() if x.strip()] if r.ok else []
    return cache[day]


def early(rows: list[dict], tid: str, opened: str, entry: float, spot0: float | None) -> dict:
    """Bid and stock moves 1, 3 and 5 minutes after the entry, from the observation record (live bids)."""
    t0 = datetime.fromisoformat(opened)
    mine = [r for r in rows if r["id"] == tid and r.get("bid") and r.get("phase", "held") != "after_exit"]
    out = {}
    for m in (1, 3, 5):
        w = [r for r in mine if 0 < (datetime.fromisoformat(r["t"]) - t0).total_seconds() <= m * 60]
        out[f"bid max up {m} min %"] = round((max(r["bid"] for r in w) / entry - 1) * 100, 1) if w else None
        out[f"bid max dip {m} min %"] = round((min(r["bid"] for r in w) / entry - 1) * 100, 1) if w else None
        sp = [r["spot"] for r in w if r.get("spot")]
        out[f"stock move {m} min %"] = round((sp[-1] / spot0 - 1) * 100, 2) if sp and spot0 else None
    return out


def rows(ledger: dict, obs_cache: dict) -> pd.DataFrame:
    out = []
    for c in ledger.get("closed", []):
        r, pc = c.get("rule") or {}, c.get("peak_capture")
        if r.get("strategy") != "fade" or not pc:
            continue
        e, eq = c["entry"]["price"], c.get("entry_quote") or {}
        day = c["opened_at"][:10]
        row = {"day": day, "symbol": c["symbol"], "side": c["instrument"], "strike": c["strike"], "expiry": c["expiry"],
               "qty": c["qty"], "entry": e, "exit": c["exit"]["price"], "why": c.get("reason"),
               "opened": c["opened_at"][11:19], "closed": c["closed_at"][11:19], "net Rs": c["net_pnl"],
               "net %": c.get("return_pct"), "peak bid": pc["peak_bid"], "peak at": pc["peak_at"][11:19],
               "MFE % (bid)": pc["peak_return_pct"], "MAE % (bid)": pc["mae_pct"],
               "net at peak Rs (est.)": pc["peak_net"], "left Rs (est.)": pc["giveback_rs"],
               "captured %": pc["capture_pct"], "peak to exit %": pc["peak_to_exit_pct"],
               "bid size at peak": pc.get("peak_bid_qty"), "lot fitted at peak": pc.get("lot_fits_at_peak"),
               "longest gap s": pc.get("max_gap_s"), "quotes": pc.get("quotes"),
               "entry bid": eq.get("bid"), "entry ask": eq.get("ask"), "entry spread %": eq.get("spread_pct"),
               "spread vs 2 % gap": round(eq["spread_pct"] / 2, 2) if eq.get("spread_pct") is not None else None,
               "stock at entry": r.get("spot_at_entry"), "stock at exit": r.get("spot_at_exit"),
               "sub2": bool(r.get("sub2"))}
        row.update(early(load_obs(day, obs_cache), c["id"], c["opened_at"], e, r.get("spot_at_entry")))
        out.append(row)
    return pd.DataFrame(out)


def summary(d: pd.DataFrame) -> pd.DataFrame:
    if d.empty:
        return pd.DataFrame([{"closed trades measured": 0, "target": TARGET}])
    return pd.DataFrame([{
        "closed trades measured": len(d), "target": TARGET, "wins": int((d["net Rs"] > 0).sum()),
        "win %": round((d["net Rs"] > 0).mean() * 100, 1), "mean net %": round(d["net %"].mean(), 2),
        "median net %": round(d["net %"].median(), 2), "total net Rs": round(d["net Rs"].sum()),
        "mean MFE % (bid)": round(d["MFE % (bid)"].mean(), 1), "mean MAE % (bid)": round(d["MAE % (bid)"].mean(), 1),
        "total net at peak Rs (est.)": round(d["net at peak Rs (est.)"].clip(lower=0).sum()),
        "total left Rs (est.)": round(d["left Rs (est.)"].sum()),
        "median captured %": d["captured %"].median(), "median peak to exit %": d["peak to exit %"].median(),
        "median entry spread %": d["entry spread %"].median(),
        "lot fitted at peak": f"{int((d['lot fitted at peak'] == True).sum())} of {int(d['lot fitted at peak'].notna().sum())}"}])  # noqa: E712


def main() -> None:
    d = rows(load_ledger(sys.argv[1] if len(sys.argv) > 1 else None), {})
    s = summary(d)
    n = len(d)
    head = (f"# S1 fade · live peak-capture checkpoint ({n} of {TARGET} trades)\n\n"
            "Live best bids (server/peak.py), trades closed after the measurement deploy (23 Oct 2026). v12 is the "
            "control; nothing changes from this report. Net at peak is an ESTIMATE: it assumes the whole lot sells at "
            "the highest observed bid (see 'lot fitted at peak'). A diagnostic, not statistical proof.\n")
    body = md_table(s) if n else "No measured trade yet: keep collecting."
    (RES / "S1_fade_live_checkpoint.md").write_text(head + "\n" + body + "\n" +
                                                     ("\n" + md_table(d) if n else ""), encoding="utf-8")
    with pd.ExcelWriter(RES / "S1_fade_live_checkpoint.xlsx") as x:
        s.to_excel(x, sheet_name="Summary", index=False)
        if n:
            d.to_excel(x, sheet_name="Trades", index=False)
    from .fade_entry_quality_fmt import tidy
    tidy(RES / "S1_fade_live_checkpoint.xlsx")
    print(f"{n} of {TARGET} measured trades")


if __name__ == "__main__":
    main()
