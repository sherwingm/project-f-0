"""S2 screen B §2: market backdrop filter on the S2 step-1 cell (short build-up 3 % / 10 %, h5). Does a risk-off state
(F1 Brent up over 5 bars, F2 S&P 500 down overnight, F3 NIFTY 50 below its 50-session average) make it work better?"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import s2_parents as P
from . import s2b_common as C

HOLDS = (3, 5)
HOLM = (2.13, 1.96, 1.65)
PERMS = 1000


def base_events(m: C.Market) -> pd.DataFrame:
    """The step-1 short build-up signals (3 % / 10 %, volume >= 1.5x, expiry day and the session after skipped,
    5-session cooldown) with their h3 / h5 short returns from d+1's open."""
    rows = []
    for s in m.c:
        last = -99
        for i in sorted(C.step1_days(m, s, "short_buildup", 3.0, 10.0)):
            if i - last < 5 or i + 5 >= len(m.cal):
                continue
            last = i
            r = {h: C.short_return(m.o[s][i + 1], m.c[s][i + h]) for h in HOLDS}
            if m.action_near(s, i - 20, i + 5):
                r = {h: math.nan for h in HOLDS}
            rows.append({"symbol": s, "i": i, "date": m.cal[i], "entry": m.cal[i + 1], **{f"r{h}": r[h] for h in HOLDS}})
    return pd.DataFrame(rows)


def states(m: C.Market, ev: pd.DataFrame) -> pd.DataFrame:
    bz, sp = P.load("BZ=F"), P.load("^GSPC")
    nf = pd.read_csv(C.EOD2 / "nifty 50.csv", parse_dates=["Date"])
    nf = nf.set_index(nf["Date"].dt.strftime("%Y-%m-%d"))["Close"]
    nf = nf[~nf.index.duplicated(keep="last")].sort_index()
    sma = nf.rolling(50).mean()
    sp_sma = sp.rolling(50).mean()

    def last_bar(series, entry, d, back=0):
        s = series[(series.index < entry) & (series.index <= d)]
        if len(s) <= back:
            return None, None
        return s.index[-1], s.iloc[-1 - back]

    out = {"F1 BRENT_UP5": [], "F2 US_OVERNIGHT_DOWN": [], "F3 NIFTY_DOWNTREND": [], "F4 SPX_DOWNTREND": []}
    for d, e in zip(ev["date"], ev["entry"]):
        when, now = last_bar(bz, e, d)
        _, five = last_bar(bz, e, d, 5)
        out["F1 BRENT_UP5"].append(None if when is None or when < d or not five else bool(now / five - 1 > 0))
        when, now = last_bar(sp, e, d)
        _, prev = last_bar(sp, e, d, 1)
        out["F2 US_OVERNIGHT_DOWN"].append(None if when is None or when < d or not prev else bool(now < prev))
        out["F3 NIFTY_DOWNTREND"].append(bool(nf.get(d) < sma.get(d)) if d in nf.index and sma.get(d) == sma.get(d) else None)
        w = sp_sma[sp_sma.index <= d]
        out["F4 SPX_DOWNTREND"].append(bool(sp[sp.index <= d].iloc[-1] < w.iloc[-1]) if len(w) and w.iloc[-1] == w.iloc[-1] else None)
    st = pd.DataFrame(out, index=ev.index)
    st["F5 F1 AND F3"] = [None if a is None or b is None else (a and b) for a, b in zip(st["F1 BRENT_UP5"], st["F3 NIFTY_DOWNTREND"])]
    return st


def on_off(ev: pd.DataFrame, state: pd.Series, h: int = 5) -> dict:
    from .stats import clustered_diff_t
    ok = state.notna()
    on, off = ev[ok & (state == True)].dropna(subset=[f"r{h}"]), ev[ok & (state == False)].dropna(subset=[f"r{h}"])  # noqa: E712
    t = clustered_diff_t(on[f"r{h}"], on["date"], off[f"r{h}"], off["date"]) if len(on) > 1 and len(off) > 1 else None
    per = {}
    for name, a, b in C.PERIODS:
        x = on[(on["date"].str[:4] >= a) & (on["date"].str[:4] <= b)][f"r{h}"].mean()
        y = off[(off["date"].str[:4] >= a) & (off["date"].str[:4] <= b)][f"r{h}"].mean()
        per[name] = x - y if x == x and y == y else np.nan
    return {"on": on, "off": off, "diff": on[f"r{h}"].mean() - off[f"r{h}"].mean(), "diff_t": t, "per": per,
            "na": int((~ok).sum())}


def family_pass(ev: pd.DataFrame, st: pd.DataFrame, filters=("F1 BRENT_UP5", "F2 US_OVERNIGHT_DOWN", "F3 NIFTY_DOWNTREND"),
                quick: bool = False) -> dict:
    """Rules 1-3 for F1-F3 at h5: the on-state passes the common bar, on − off clears Holm, positive in each period."""
    res = {}
    for f in filters:
        oo = on_off(ev, st[f])
        lvl = C.report(oo["on"].assign(step1_overlap=False), "r5", {}, overlap_col=None) if not quick else None
        res[f] = {"oo": oo, "level_pass": (lvl["PASS"] == "PASS") if lvl else _quick_level(oo["on"]),
                  "periods_pos": all((v or -1) > 0 for v in oo["per"].values()), "level": lvl}
    ranked = sorted(filters, key=lambda f: -(res[f]["oo"]["diff_t"] or -99))
    alive = True
    for k, f in enumerate(ranked):
        holm = alive and (res[f]["oo"]["diff_t"] or -99) >= HOLM[k]
        alive = holm
        res[f]["holm"] = holm
        res[f]["pass"] = bool(res[f]["level_pass"] and holm and res[f]["periods_pos"])
    return res


def _quick_level(on: pd.DataFrame) -> bool:
    """The common bar's main parts, fast (for the permutation null): N, dates, t >= 3, mean >= 0.6, years."""
    r, d = on["r5"], on["date"]
    if len(on) < 100 or d.nunique() < 60 or r.mean() < 0.6:
        return False
    t = C.min_t(r, d)
    years = [r[d.str[:4] == y].mean() for y in C.YEARS]
    return (t or 0) >= 3 and sum(1 for y in years if y == y and y > 0) >= 5 and all((y or -1) > 0 for y in years[-2:])


def permutation_p(ev: pd.DataFrame, st: pd.DataFrame, seed: int = 7) -> float:
    """Shift each filter's date-level state series circularly along the calendar (keeps its persistence), rerun rules
    1-3; the share of shifts in which any of F1-F3 passes."""
    rng = np.random.default_rng(seed)
    dates = sorted(ev["date"].unique())
    hits = 0
    for _ in range(PERMS):
        sh = st.copy()
        for f in ("F1 BRENT_UP5", "F2 US_OVERNIGHT_DOWN", "F3 NIFTY_DOWNTREND"):
            by_date = st[f].groupby(ev["date"]).first().reindex(dates)
            k = int(rng.integers(1, len(dates)))
            moved = pd.Series(np.roll(by_date.to_numpy(dtype=object), k), index=dates)
            sh[f] = ev["date"].map(moved)
        r = family_pass(ev, sh, quick=True)
        hits += any(v["pass"] for v in r.values())
    return hits / PERMS


def cells(m: C.Market) -> tuple[list[dict], dict]:
    ev = base_events(m)
    st = states(m, ev)
    out = []
    for h in HOLDS:
        row = C.report(ev.assign(step1_overlap=False), f"r{h}", {"screen": "§2 market backdrop", "cell": "F0 base (step-1 short build-up)",
                                                                 "h": h, "role": "descriptive"}, overlap_col=None)
        row["PASS"] = ""
        out.append(row)
    fam = family_pass(ev, st)
    p = permutation_p(ev, st) if any(v["pass"] for v in fam.values()) else None
    for f in st.columns:
        for h in HOLDS:
            oo = on_off(ev, st[f], h)
            primary = f in fam and h == 5
            row = C.report(oo["on"].assign(step1_overlap=False), f"r{h}",
                           {"screen": "§2 market backdrop", "cell": f + " (on)", "h": h,
                            "role": "pass test" if primary else "descriptive"}, overlap_col=None)
            row.update({"off mean": round(oo["off"][f"r{h}"].mean(), 3) if len(oo["off"]) else None, "on - off": round(oo["diff"], 3),
                        "on - off t": oo["diff_t"], "NA events": oo["na"],
                        **{f"on - off {k}": round(v, 3) if v == v else None for k, v in oo["per"].items()}})
            if primary:
                ok = fam[f]["pass"] and (p is not None and p < 0.05)
                why = [w for w, c in (("level", fam[f]["level_pass"]), ("Holm", fam[f]["holm"]),
                                      ("periods", fam[f]["periods_pos"])) if not c]
                if fam[f]["pass"] and not ok:
                    why.append(f"permutation p {p}")
                row["failed"], row["PASS"] = ", ".join(why) or row["failed"], "PASS" if ok else ""
                row["permutation p"] = p
            else:
                row["PASS"] = ""
            out.append(row)
    return out, {"base events": len(ev), "permutation p": p}
