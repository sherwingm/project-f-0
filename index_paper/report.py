"""Per-pod research numbers from the index paper ledger, for /api/index/results and the page.

    python -m index_paper.report [--data-dir data]     # -> <data_dir>/index_paper/report.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, median

from .ledger import IndexPaperLedger
from .pods import PODS


def _t(x: list[float]) -> float | None:
    if len(x) < 3:
        return None
    m, sd = mean(x), math.sqrt(sum((v - mean(x)) ** 2 for v in x) / (len(x) - 1))
    return round(m / (sd / math.sqrt(len(x))), 2) if sd > 0 else None


def pod_stats(closed: list[dict]) -> dict:
    pct = [p["net_pct"] for p in closed if p.get("net_pct") is not None]
    rs = [p["net_rs"] for p in closed]
    caps = [p["capture"] for p in closed if p.get("capture")]
    out = {"trades": len(closed), "won": sum(r > 0 for r in rs), "mean_pct": round(mean(pct), 2) if pct else None,
           "median_pct": round(median(pct), 2) if pct else None, "t": _t(pct), "total_rs": round(sum(rs), 2)}
    if caps:
        out["median_peak_return_pct"] = round(median(c["peak_return_pct"] for c in caps), 2)
        out["median_mae_pct"] = round(median(c["mae_pct"] for c in caps), 2)
        cp = [c["capture_pct"] for c in caps if c.get("capture_pct") is not None]
        out["median_capture_pct"] = round(median(cp), 1) if cp else None
    return out


def build(ledger: IndexPaperLedger) -> dict:
    pods = []
    for name, pod in PODS.items():
        closed = [p for p in ledger.state["closed"] if p["pod"] == name]
        pods.append({"pod": name, "title": pod.title, "page": pod.page, "status": pod.status,
                     "enabled": pod.enabled, "open": sum(p["pod"] == name for p in ledger.state["open"]),
                     **pod_stats(closed)})
    return {"pods": pods, "open": ledger.state["open"], "closed": ledger.state["closed"][-50:],
            "rejected": ledger.state["rejected"][-20:]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    a = ap.parse_args()
    led = IndexPaperLedger(Path(a.data_dir))
    rep = build(led)
    out = led.dir / "report.json"
    led.dir.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
