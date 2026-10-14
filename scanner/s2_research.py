"""S2 · the research numbers the S2 page shows: step 1's screen (the passing cell year by year, and the four
build-up classes beside it) and, once run, step 2's put backtest.

    python -m scanner.s2_research          # -> data/s2/research.json (from data/results/S2_*.csv)
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .build import ROOT
from .s2_screen import table

RES = ROOT / "data" / "results"
OUT = ROOT / "data" / "s2" / "research.json"


def _clean(v):
    if isinstance(v, float) and v != v:
        return None
    return v.item() if hasattr(v, "item") else v


def build(res: Path = RES, out: Path = OUT) -> dict:
    data: dict = {"screen": None, "put": None}
    sig_path = res / "S2_screen_signals.csv"
    if sig_path.exists():
        tab = table(pd.read_csv(sig_path))
        keep = tab[(tab["price_thr"] == 3.0) & (tab["oi_thr"] == 10.0)]
        data["screen"] = {
            "rows": [{k: _clean(v) for k, v in r.items()} for r in keep.to_dict("records")],
            "passed": [{k: _clean(v) for k, v in r.items()} for r in tab[tab["PASS"] == "PASS"].to_dict("records")],
            "cells": len(tab), "note": "Stock-level screen (not a trade): enter at the next open, signed, net of 0.1 %; "
                                       "48 cells tested, 2021-01 → 2026-09."}
    put_path = res / "S2_put_trades.csv"
    if put_path.exists():
        from .backtest_s2_put import VARIANTS, by_year, gate, metrics
        t = pd.read_csv(put_path)
        data["put"] = {"variants": [{"variant": v.name, **{k: _clean(x) for k, x in metrics(t[t["variant"] == v.name]).items()},
                                     "years": {k: _clean(x) for k, x in by_year(t[t["variant"] == v.name]).items()}}
                                    for v in VARIANTS],
                       "gate": [{k: _clean(x) for k, x in r.items()} for r in gate(t[t["variant"] == "h5"])]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data


if __name__ == "__main__":
    d = build()
    print("screen rows", len((d["screen"] or {}).get("rows", [])), "put", bool(d["put"]))
