"""Second independent pass over the G1 / G1-F scenarios that v2 did not cover through the original engine: C7, E3, E4.
(S5, S6 and C8 need a stop rule the engine does not have; they remain verified only by the audit's own simulator, which equals the engine on the baseline.)

Does NOT import stress_audit/. Uses the ORIGINAL engine with in-process patches. Offline. Seed 20261113 (no randomness used).
    python -m stress_audit_review.v2b_g1_more_scenarios
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("INDEX_STORE", str(Path(__file__).resolve().parents[2] / "fo-index-data" / "data" / "index"))

import numpy as np
import pandas as pd

from index_data import load as L
from scanner import s3_engine as E

from . import v2_g1_independent as V

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "stress_audit" / "results"
OUT = ROOT / "stress_audit_review" / "results"


def main() -> None:
    T = V.collect()
    rp = pd.read_csv(ROOT / "g1_research" / "results" / "g1_live_replay_trades.csv")
    g1f_days = set(rp.loc[rp["g1f"] == 1, "day"].astype(str))
    pubs = pd.read_csv(AUD / "scenario_results_g1.csv")
    rows = []

    def cmp(track, sid, mine_n, mine_rs, note=""):
        p = pubs[(pubs.strategy == track) & (pubs.scenario == sid)].iloc[0]
        ok = int(p.n) == mine_n and abs(float(p.net_rs) - mine_rs) <= 1.5
        rows.append({"item": f"{track} {sid}: trade count and net Rs vs audit (ORIGINAL engine with patches)", "audit_value": f"{int(p.n)} / {p.net_rs:,.0f}",
                     "independent_value": f"{mine_n} / {mine_rs:,.0f}", "status": "Verified" if ok else "NOT REPRODUCED", "note": note})

    base = {t["day0"]: V.eng(t) for t in T}
    # ---- C7: +1 % slippage per side on the top decile of |NIFTY| days (decile over trade rows, as implemented by the audit)
    nf = pd.read_csv(ROOT / "data" / "eod2" / "nifty 50.csv")
    nf.columns = [c.lower() for c in nf.columns]
    nf["date"] = pd.to_datetime(nf["date"]).dt.strftime("%Y-%m-%d")
    nf = nf.sort_values("date").reset_index(drop=True)
    nf["ret"] = nf["close"].pct_change() * 100
    ar = nf.set_index("date")["ret"].abs()
    cut = np.nanquantile([ar.get(t["day0"], np.nan) for t in T], 0.9)
    c7 = {}
    for t in T:
        flagged = ar.get(t["day0"], np.nan) >= cut
        if flagged:
            with V.Patch(slip=E.SLIP + 0.01, slip_wide=E.SLIP_WIDE + 0.01):
                r = V.eng(t)
        else:
            r = base[t["day0"]]
        if not r.get("skip"):
            c7[t["day0"]] = r["net_rs"]
    c7 = pd.Series(c7)
    cmp("G1", "C7", len(c7), float(c7.sum()), f"cut {cut:.3f} % of |NIFTY return|")
    cmp("G1-F", "C7", int(c7.index.isin(g1f_days).sum()), float(c7[c7.index.isin(g1f_days)].sum()))
    # ---- E3: entry at the entry minute's HIGH (patch L.price_at for the entry call only)
    orig = L.price_at

    def price_high(frame, strike, opt, at, stale=3):
        if stale == E.ENTRY_STALE:
            r = frame[(frame["strike"] == strike) & (frame["option_type"] == opt) & (frame["timestamp"] == at)]
            if len(r):
                return float(r["high"].iloc[-1])
        return orig(frame, strike, opt, at, stale=stale)

    L.price_at = price_high
    try:
        e3 = {}
        for t in T:
            r = V.eng(t)
            if not r.get("skip"):
                e3[t["day0"]] = r["net_rs"]
        e3 = pd.Series(e3)
    finally:
        L.price_at = orig
    cmp("G1", "E3", len(e3), float(e3.sum()), "entry at the entry minute's high")
    cmp("G1-F", "E3", int(e3.index.isin(g1f_days).sum()), float(e3[e3.index.isin(g1f_days)].sum()))
    # ---- E4: skip trades whose entry-minute range exceeds 10 % of its open
    keep = {}
    for t in T:
        r = base[t["day0"]]
        if r.get("skip"):
            continue
        atm = round(t["spot"] / 50) * 50
        t_in = L.at(t["day"], t["h"], t["m"])
        c = t["full"][(t["full"]["option_type"] == "PE") & (t["full"]["strike"] == atm) & (t["full"]["timestamp"] == t_in)]
        wide = len(c) and (c["high"].iloc[-1] - c["low"].iloc[-1]) / c["open"].iloc[-1] > 0.10
        if not wide:
            keep[t["day0"]] = r["net_rs"]
    keep = pd.Series(keep)
    cmp("G1", "E4", len(keep), float(keep.sum()))
    cmp("G1-F", "E4", int(keep.index.isin(g1f_days).sum()), float(keep[keep.index.isin(g1f_days)].sum()))
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "v2b_g1_more_scenarios.csv", index=False)
    print(d.to_string(max_colwidth=90))


if __name__ == "__main__":
    main()
