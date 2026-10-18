"""S2 screen B §3: sector rotation. A stock still stretched above its 20-session average and far ahead of its falling
cyclical sector; short from d+1's open (R1 h1, R2 h3)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import s2b_common as C

CYCLICAL = ("nifty metal", "nifty auto", "nifty realty", "nifty oil & gas", "nifty energy", "nifty psu bank")
INFRA = ("nifty infrastructure",)
HOLDS = (1, 3, 5)
COOLDOWN = 5


def loo_returns(m: C.Market, members: list[str]) -> dict[str, np.ndarray]:
    """Each member's leave-one-out sector daily return: equal weight of the other members with OI > 0 on d−1 and d,
    >= 3 peers, no fill across gaps, demerger ex-dates set to NaN."""
    rets = {}
    for s in members:
        c = pd.Series(m.c[s])
        r = c.pct_change(fill_method=None).to_numpy()
        for d in m.actions.get(s, ()):
            if d in m.pos:
                r[m.pos[d]] = np.nan
        oi = m.oi[s].to_numpy(dtype=float) if s in m.oi.columns else np.full(len(m.cal), np.nan)
        ok = (oi > 0) & (np.roll(oi, 1) > 0)
        ok[0] = False
        rets[s] = np.where(ok, r, np.nan)
    R = np.vstack([rets[s] for s in members]) if members else np.zeros((0, len(m.cal)))
    tot, cnt = np.nansum(R, axis=0), np.isfinite(R).sum(axis=0)
    out = {}
    for k, s in enumerate(members):
        own = np.isfinite(R[k])
        c_ = cnt - own
        out[s] = np.where(c_ >= 3, (tot - np.where(own, R[k], 0)) / np.maximum(c_, 1), np.nan)
    return out


def comp(r: np.ndarray, a: int, b: int) -> float:
    """Compounded return over sessions a+1 .. b (in %), NaN if any is missing."""
    x = r[a + 1:b + 1]
    return (np.prod(1 + x) - 1) * 100 if len(x) and np.isfinite(x).all() else np.nan


def events(m: C.Market, sectors=CYCLICAL, w: float = -2.0, rel: float = 8.0) -> pd.DataFrame:
    from .sectors import load_map
    smap = {C.canon(k): v for k, v in load_map().items()}
    rows = []
    for sec in sectors:
        members = [s for s, v in smap.items() if v == sec and s in m.c]
        loo = loo_returns(m, members)
        for s in members:
            c, L = m.c[s], loo[s]
            for d in range(21, len(m.cal) - 1):
                if not m.in_universe(s, d) or not np.isfinite(c[d - 19:d + 1]).all() or not c[d - 10] > 0:
                    continue
                sec5 = comp(L, d - 5, d)
                if not sec5 <= w:
                    continue
                dist20 = (c[d] / np.mean(c[d - 19:d + 1]) - 1) * 100
                rel10 = (c[d] / c[d - 10] - 1) * 100 - comp(L, d - 10, d)
                if dist20 >= 5 and rel10 >= rel:
                    rows.append({"sector": sec, "symbol": s, "i": d, "date": m.cal[d], "SEC5": sec5, "DIST20": dist20,
                                 "REL10": rel10})
    ev = pd.DataFrame(rows)
    if ev.empty:
        return ev
    ev = ev.sort_values(["date", "sector", "REL10"], ascending=[True, True, False])
    ev = ev.groupby(["date", "sector"]).head(2)                     # at most the 2 highest REL10 per sector per day
    keep, last = [], {}
    for r in ev.sort_values(["symbol", "i"]).itertuples():
        if r.symbol in last and r.i - last[r.symbol] < COOLDOWN:
            continue
        last[r.symbol] = r.i
        keep.append(r.Index)
    return ev.loc[keep]


def add_returns(m: C.Market, ev: pd.DataFrame) -> pd.DataFrame:
    if ev.empty:
        return ev
    for h in HOLDS:
        ev[f"r{h}"] = [C.short_return(m.o[s][i + 1], m.c[s][i + h]) if i + h < len(m.cal) else np.nan
                       for s, i in zip(ev["symbol"], ev["i"])]
        ev.loc[[m.action_near(s, i - 20, i + h) for s, i in zip(ev["symbol"], ev["i"])], f"r{h}"] = np.nan
    over = {s: C.step1_days(m, s, "long_buildup", 2.0, 5.0) for s in ev["symbol"].unique()}
    ev["step1_overlap"] = [any(j in over[s] for j in range(i - 10, i + 1)) for s, i in zip(ev["symbol"], ev["i"])]
    return ev


def cells(m: C.Market) -> tuple[list[dict], dict]:
    out, counts = [], {}
    variants = {"R (W -2 %, R +8 %)": (CYCLICAL, -2.0, 8.0), "W -2 %, R +10 %": (CYCLICAL, -2.0, 10.0),
                "W -3 %, R +8 %": (CYCLICAL, -3.0, 8.0), "infrastructure, W -2 %, R +8 %": (INFRA, -2.0, 8.0)}
    for name, (secs, w, rel) in variants.items():
        ev = add_returns(m, events(m, secs, w, rel))
        counts[name] = len(ev)
        for h in HOLDS:
            primary = name.startswith("R (") and h in (1, 3)
            cell = ("R1 " if h == 1 else "R2 ") + name if primary else name
            row = C.report(ev, f"r{h}", {"screen": "§3 sector rotation", "cell": cell, "h": h,
                                         "role": "pass test" if primary else "descriptive"})
            if primary and len(ev):
                no_ad = ev[ev["symbol"] != "ADANIENT"].dropna(subset=[f"r{h}"])
                row["t without ADANIENT"] = C.min_t(no_ad[f"r{h}"], no_ad["date"])
                if (row["t without ADANIENT"] or 0) < 2 and row["PASS"]:
                    row["PASS"], row["failed"] = "", "without ADANIENT"
            if not primary:
                row["PASS"] = ""
            out.append(row)
    return out, counts
