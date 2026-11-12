"""Real fills against the paper account's fills (numbers only). Places NO orders.

    python -m scanner.real_vs_paper_fills <paper_ledger.json> <real_fills.csv>

real_fills.csv (one row per real execution, typed in or exported from the broker's tradebook):

    date,time,tradingsymbol,side,qty,price
    2026-11-12,09:15:12,KALYANKJIL26NOV760CE,BUY,1350,5.90

Each real BUY is matched to the paper position of the same tradingsymbol opened that day, each real SELL to the paper position of that symbol closed that
day. Reported per execution: the real price against the paper price (% of the paper price; for a BUY a positive figure = the real fill was dearer, for a
SELL a positive figure = the real fill was lower), the seconds between the two fills, and the real quantity against the paper quantity. Then the means.
The 'cost' sign is the same for both sides: positive = real was worse than paper.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def _t(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "")[:19])


def paper_fills(ledger: dict) -> pd.DataFrame:
    rows = []
    for p in ledger.get("positions", []) + ledger.get("closed", []):
        e = p.get("entry") or {}
        rows.append({"tradingsymbol": p["tradingsymbol"], "side": "BUY", "at": _t(p["opened_at"]), "price": e.get("price"), "qty": p.get("qty")})
        x = p.get("exit") or {}
        if p.get("closed_at") and x.get("price") is not None:
            rows.append({"tradingsymbol": p["tradingsymbol"], "side": "SELL", "at": _t(p["closed_at"]), "price": x["price"], "qty": p.get("qty")})
    return pd.DataFrame(rows)


def compare(paper: pd.DataFrame, real: pd.DataFrame) -> pd.DataFrame:
    real = real.copy()
    real["at"] = pd.to_datetime(real["date"].astype(str) + " " + real["time"].astype(str))
    out = []
    for r in real.itertuples():
        side = str(r.side).upper()
        cand = paper[(paper.tradingsymbol == r.tradingsymbol) & (paper.side == side) & (paper["at"].dt.date == r.at.date())]
        if cand.empty:
            out.append({"tradingsymbol": r.tradingsymbol, "side": side, "real_price": r.price, "paper_price": None, "note": "no paper fill that day"})
            continue
        c = cand.iloc[(cand["at"] - r.at).abs().argmin()]
        diff = (float(r.price) / float(c["price"]) - 1) * 100
        out.append({"tradingsymbol": r.tradingsymbol, "side": side, "real_at": r.at.time(), "paper_at": c["at"].time(),
                    "lag_s": round((r.at - c["at"]).total_seconds(), 1), "real_price": float(r.price), "paper_price": float(c["price"]),
                    "cost_pct": round(diff if side == "BUY" else -diff, 2), "real_qty": int(r.qty), "paper_qty": int(c["qty"]), "note": ""})
    return pd.DataFrame(out)


def summary(df: pd.DataFrame) -> str:
    ok = df[df.get("cost_pct").notna()] if "cost_pct" in df else df.iloc[0:0]
    if ok.empty:
        return "No executions matched a paper fill."
    lines = [f"{len(ok)} matched executions of {len(df)}."]
    for side in ("BUY", "SELL"):
        s = ok[ok.side == side]
        if len(s):
            lines.append(f"{side}: {len(s)} fills, real worse than paper by {s.cost_pct.mean():+.2f} % on average (median {s.cost_pct.median():+.2f} %), "
                         f"real fill {s.lag_s.mean():+.1f} s after the paper fill on average, partial or different size in {int((s.real_qty != s.paper_qty).sum())}.")
    return "\n".join(lines)


def main() -> None:
    ledger = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    real = pd.read_csv(sys.argv[2])
    df = compare(paper_fills(ledger), real)
    print(df.to_string(index=False))
    print()
    print(summary(df))


if __name__ == "__main__":
    main()
