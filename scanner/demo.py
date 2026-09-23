"""Write a DEMO scan with synthetic OI, PCR and option chains on top of the real price/volume
data, for testing the UI and the order flow without NSE access. The page shows a demo notice.

    python -m scanner.demo   # writes data/scan_demo.json (and data/scan.json with --install)
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

from .build import ROOT
from .classify import classify
from .strikes import option_chains


def make_demo(scan: dict, seed: int = 7) -> dict:
    rng = random.Random(seed)
    rows = []
    as_of = scan["meta"]["as_of"]
    for s in scan["stocks"]:
        oi = rng.randint(200_000, 9_000_000); chg = round(rng.uniform(-12, 15), 2)
        s.update(fut_oi=oi, fut_oi_prev=int(oi / (1 + chg / 100)), oi_change_pct=chg)
        s["call_oi"] = rng.randint(50_000, 3_000_000); s["put_oi"] = int(s["call_oi"] * rng.uniform(0.3, 1.8))
        s["pcr"] = round(s["put_oi"] / s["call_oi"], 2)
        s.update(classify(s))
        step = max(0.5, round(s["close"] * 0.025 / 5) * 5) if s["close"] > 100 else 1
        base = round(s["close"] / step) * step
        for k in range(-12, 13):
            strike = base + k * step
            ce = int(rng.uniform(500, 4000) * (1 + max(0, k) * 0.6)); pe = int(rng.uniform(500, 4000) * (1 + max(0, -k) * 0.6))
            rows.append([as_of, s["symbol"], "STO", "2026-09-30", strike, "CE", round(max(0.5, s["close"] - strike + rng.uniform(1, 8)), 2), s["close"], ce, rng.randint(-300, 600), rng.randint(0, 900)])
            rows.append([as_of, s["symbol"], "STO", "2026-09-30", strike, "PE", round(max(0.5, strike - s["close"] + rng.uniform(1, 8)), 2), s["close"], pe, rng.randint(-300, 600), rng.randint(0, 900)])
    bhav = pd.DataFrame(rows, columns=["TradDt", "TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "UndrlygPric", "OpnIntrst", "ChngInOpnIntrst", "TtlTradgVol"])
    chains, _problems = option_chains(bhav, {s["symbol"]: s["close"] for s in scan["stocks"]})
    for s in scan["stocks"]:
        s["chain"] = chains.get(s["symbol"])
    c = Counter(s["label"] for s in scan["stocks"])
    scan["summary"] = {"bullish": c["Bullish setup"], "bearish": c["Bearish setup"], "neutral": c["Neutral"], "unclassified": c["Unclassified"]}
    scan["meta"].update(fo_status="DEMO: synthetic OI, PCR and strikes", fo_available=True, chains_available=True, demo=True)
    return scan


if __name__ == "__main__":
    scan = make_demo(json.loads((ROOT / "data" / "scan.json").read_text()))
    out = ROOT / "data" / ("scan.json" if "--install" in sys.argv else "scan_demo.json")
    out.write_text(json.dumps(scan))
    print("wrote", out, scan["summary"])
