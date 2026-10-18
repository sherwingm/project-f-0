"""S2 screen B §4: gap-fill short (strategies/S2_put_screens_B.md). A large gap up specific to the stock, not results
and not market-wide; short from day 0's open. Pass horizon h1; also with a 0.35 % cost (entry-latency haircut)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import s2b_common as C

CELLS = {"G1": (2.0, False), "G2": (3.0, False), "G3": (2.0, True), "G5 (descriptive)": (5.0, False)}
HOLDS = (0, 1, 3)
COOLDOWN = 3


def results_days(m: C.Market, store_events) -> set[tuple[str, int]]:
    """(stock, session index) pairs that are a results day: day 0 of any results filing, and the first session on or
    after a board-meeting `results_date` plus the next one."""
    from .backtest_s1_v2 import day0_index
    out = set()
    for e in store_events:
        s = C.canon(e["symbol"])
        if e["type"] == "results":
            i = day0_index(m.cal, e["event_date"], e.get("event_time"))
            if i is not None:
                out.add((s, i))
        elif e["type"] == "results_date":
            i = int(np.searchsorted(m.cal, e["event_date"]))
            out |= {(s, i), (s, i + 1)}
    return out


def events(m: C.Market, res_days: set) -> pd.DataFrame:
    rows, n = [], len(m.cal)
    syms = [s for s in m.o if s in m.oi.columns]
    O = np.vstack([m.o[s] for s in syms]); Cl = np.vstack([m.c[s] for s in syms])
    H = np.vstack([m.h[s] for s in syms]); L = np.vstack([m.l[s] for s in syms])
    oi = m.oi[syms].to_numpy(dtype=float).T
    for i in range(21, n):
        univ = (oi[:, i - 1] > 0) & (Cl[:, i - 1] > 0) & (O[:, i] > 0)
        if univ.sum() < 20:
            continue
        G = (O[:, i] / Cl[:, i - 1] - 1) * 100
        M = float(np.nanmedian(G[univ]))
        if abs(M) >= 1.0:
            continue
        for k in np.where(univ & (G >= 2.0) & (G < 20.0) & (G - M >= 2.0))[0]:
            s = syms[k]
            if not (L[k, i - 1] <= Cl[k, i - 1] <= H[k, i - 1]) or (s, i) in res_days:
                continue
            ma20 = np.nanmean(Cl[k, i - 20:i]) if np.isfinite(Cl[k, i - 20:i]).all() else np.nan
            rows.append({"symbol": s, "i": i, "date": m.cal[i], "G": G[k], "M": M, "REL": G[k] - M,
                         "stretched": bool(ma20 == ma20 and Cl[k, i - 1] >= 1.05 * ma20)})
    return pd.DataFrame(rows)


def add_returns(m: C.Market, ev: pd.DataFrame) -> pd.DataFrame:
    over: dict[str, set] = {}
    for h in HOLDS:
        ev[f"r{h}"] = [C.short_return(m.o[s][i], m.c[s][i + h]) if i + h < len(m.cal) else np.nan
                       for s, i in zip(ev["symbol"], ev["i"])]
        ev[f"r{h}_035"] = ev[f"r{h}"] - 0.25
        ev.loc[[m.action_near(s, i - 20, i + h) for s, i in zip(ev["symbol"], ev["i"])], [f"r{h}", f"r{h}_035"]] = np.nan
    for s in ev["symbol"].unique():
        over[s] = C.step1_days(m, s, "long_buildup", 2.0, 5.0)
    ev["step1_overlap"] = [any(j in over[s] for j in range(i - 11, i)) for s, i in zip(ev["symbol"], ev["i"])]
    return ev


def cell_events(ev: pd.DataFrame, x: float, stretched: bool) -> pd.DataFrame:
    e = ev[(ev["G"] >= x) & (ev["REL"] >= x) & ((ev["stretched"]) if stretched else True)].sort_values(["symbol", "i"])
    keep, last = [], {}
    for r in e.itertuples():
        if r.symbol in last and r.i - last[r.symbol] < COOLDOWN:
            continue
        last[r.symbol] = r.i
        keep.append(r.Index)
    return e.loc[keep]


def cells(ev: pd.DataFrame) -> list[dict]:
    out = []
    for name, (x, st) in CELLS.items():
        e = cell_events(ev, x, st)
        for h in HOLDS:
            role = "pass test" if (h == 1 and not name.startswith("G5")) else "descriptive"
            row = C.report(e, f"r{h}", {"screen": "§4 gap fill", "cell": name, "h": h, "role": role})
            if role == "pass test":
                hair = C.report(e, f"r{h}_035", {"screen": "§4 gap fill", "cell": name + " (cost 0.35 %)", "h": h,
                                                   "role": "haircut check"})
                if hair["PASS"] != "PASS":
                    row["failed"] = (row["failed"] + ", " if row["failed"] else "") + "0.35 % haircut"
                    row["PASS"] = ""
                out += [row, hair]
            else:
                row["PASS"] = ""
                out.append(row)
    return out
