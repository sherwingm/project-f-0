"""S2 screen B §6 (addendum 2026-10-18): order-book hype, a proxy for the user's RVNL idea. Order-win announcements
while the stock has already run up (O1) or keeps announcing orders (O2); short from day 0's open; h3 and h5 jointly."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import s2b_common as C

HOLDS = (0, 1, 3, 5)
COOLDOWN = 5
YEARS = ("2022", "2023", "2024", "2025", "2026")
TOP = ("NBCC", "LT", "RVNL", "BEL", "HAL", "BHEL", "SUZLON")


def events(m: C.Market, store_events) -> pd.DataFrame:
    from .backtest_s1_v2 import day0_index
    wins = []
    for e in store_events:
        if e["type"] != "order_win" or (e.get("bucket") or "") == "ignore":
            continue
        i = day0_index(m.cal, e["event_date"], e.get("event_time"))
        if i is not None:
            wins.append({"symbol": C.canon(e["symbol"]), "i": i, "filed": e["event_date"],
                         "materiality": e.get("materiality"), "value_cr": e.get("value_cr")})
    w = pd.DataFrame(wins).sort_values(["symbol", "i"])
    rows = []
    for s, g in w.groupby("symbol"):
        if s not in m.c:
            continue
        c, idx = m.c[s], g["i"].to_numpy()
        for r in g.itertuples():
            i = r.i
            if i < 22 or not m.in_universe(s, i - 1):
                continue
            last20 = c[i - 20:i]
            dist20 = (c[i - 1] / np.mean(last20) - 1) * 100 if np.isfinite(last20).all() else np.nan
            run20 = (c[i - 1] / c[i - 21] - 1) * 100 if c[i - 21] > 0 and c[i - 1] > 0 else np.nan
            n60 = int(((idx > i - 60) & (idx <= i)).sum())
            rows.append({"symbol": s, "i": i, "date": m.cal[i], "filed": r.filed, "DIST20": dist20, "RUN20": run20,
                         "N60": n60, "materiality": r.materiality})
    return pd.DataFrame(rows)


def add_returns(m: C.Market, ev: pd.DataFrame) -> pd.DataFrame:
    for h in HOLDS:
        ev[f"r{h}"] = [C.short_return(m.o[s][i], m.c[s][i + h]) if i + h < len(m.cal) else np.nan
                       for s, i in zip(ev["symbol"], ev["i"])]
        ev.loc[[m.action_near(s, i - 20, i + h) for s, i in zip(ev["symbol"], ev["i"])], f"r{h}"] = np.nan
    over = {s: C.step1_days(m, s, "long_buildup", 2.0, 5.0) for s in ev["symbol"].unique()}
    ev["step1_overlap"] = [any(j in over[s] for j in range(i - 10, i + 1)) for s, i in zip(ev["symbol"], ev["i"])]
    return ev


def cooldown(e: pd.DataFrame) -> pd.DataFrame:
    keep, last = [], {}
    for r in e.sort_values(["symbol", "i"]).itertuples():
        if r.symbol in last and r.i - last[r.symbol] < COOLDOWN:
            continue
        last[r.symbol] = r.i
        keep.append(r.Index)
    return e.loc[keep]


CELL_RULES = {
    "O1 order hype (DIST20 >= 5 %, RUN20 >= 10 %)": lambda e: (e["DIST20"] >= 5) & (e["RUN20"] >= 10),
    "O2 order pile-up (N60 >= 3, DIST20 >= 5 %)": lambda e: (e["N60"] >= 3) & (e["DIST20"] >= 5),
    "every order win (descriptive)": lambda e: e["DIST20"] == e["DIST20"],
    "order value >= 5 % of revenue (descriptive)": lambda e: pd.to_numeric(e["materiality"], errors="coerce") >= 5,
}


def cells(ev: pd.DataFrame) -> list[dict]:
    out = []
    for name, rule in CELL_RULES.items():
        e = cooldown(ev[rule(ev)])
        for h in HOLDS:
            # gate 4 (2026-10-18): O1 50 and O2 36 events, below N 100 -> descriptive only, dropped before any return
            role = "descriptive (below N 100 at the recount)" if name.startswith("O") and h in (3, 5) else "descriptive"
            row = C.report(e, f"r{h}", {"screen": "§6 order-book hype", "cell": name, "h": h, "role": role},
                           years=YEARS, need_years=4)
            if role != "pass test":
                row["PASS"] = ""
            out.append(row)
    for name in ("O1", "O2"):                                       # h3 and h5 must pass jointly
        legs = [r for r in out if r["cell"].startswith(name) and r["role"] == "pass test"]
        ok = C.joint(legs, name)
        for r in legs:
            r["PASS"] = ok
            if not ok and not r["failed"]:
                r["failed"] = "the other horizon failed"
    allw = cooldown(ev)
    for s in TOP:
        e = allw[allw["symbol"] == s]
        row = C.report(e, "r5", {"screen": "§6 order-book hype", "cell": f"every order win: {s}", "h": 5,
                                 "role": "descriptive"}, years=YEARS, need_years=4, min_n=1, min_g=1)
        row["PASS"] = ""
        out.append(row)
    return out
