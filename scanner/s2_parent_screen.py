"""S2 screen B §1: parent indicators. After a large adverse overnight move in a stock's parent (INFY ADR for IT, Brent
for oil producers / users, copper for copper stocks, iron ore for steel at k=5), does the stock keep falling from the
next open? Judged on shock dates (the equal-weight mean of a date's children), P1 (k=1) and P2 (k=5), h3 and h5 jointly."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import s2_parents as P
from . import s2b_common as C

GROUPS = {   # name: (parent ticker, link, children, measures)
    "IT (INFY ADR)": ("INFY", 1, ("INFY", "TCS", "WIPRO", "HCLTECH", "TECHM", "LTM", "COFORGE", "MPHASIS", "PERSISTENT",
                                  "BSOFT"), (1, 5)),
    "Oil producers (Brent)": ("BZ=F", 1, ("ONGC", "OIL"), (1, 5)),
    "Oil users (Brent up)": ("BZ=F", -1, ("BPCL", "HINDPETRO", "IOC", "ASIANPAINT", "BERGEPAINT", "INDIGO", "APOLLOTYRE",
                                          "MRF", "BALKRISIND"), (1, 5)),
    "Copper": ("HG=F", 1, ("HINDCOPPER", "VEDL", "HINDZINC"), (1, 5)),
    "Iron ore (TIO=F)": ("TIO=F", 1, ("TATASTEEL", "JSWSTEEL", "JINDALSTEL", "SAIL", "NMDC", "JSL"), (5,)),
    "Aluminium (side report)": ("ALI=F", 1, ("HINDALCO", "NATIONALUM"), (1, 5)),
}
SIDE_ONLY = {"Aluminium (side report)"}
ROLL_GUARD = {"BZ=F", "TIO=F"}
HOLDS = (1, 3, 5)
Z = -1.5
COOLDOWN = 5


# ---------------------------------------------------------------- parent series
def guarded_returns(ticker: str, guard: bool = True) -> pd.Series:
    """Daily log returns on the parent's own bars; the roll guard sets the first trading day of each month to 0 for
    BZ=F and TIO=F; TIO=F zero returns are missing."""
    s = P.load(ticker)
    r = np.log(s).diff()
    if guard and ticker in ROLL_GUARD:
        months = pd.Series(s.index.str[:7], index=s.index)
        first = months != months.shift(1)
        r[first] = 0.0
    if ticker == "TIO=F":
        r[r == 0] = np.nan
    return r


def settlement_check() -> dict:
    """Date alignment of the daily bars against the 1h bars (ET date): the share of days whose daily Close is within
    0.5 % of a 1h close on the same ET date. The run aborts below 95 %."""
    out = {}
    for t in P.HOURLY:
        d, hr = P.load(t), P.load(t, hourly=True)
        by_day = pd.Series(hr.values, index=hr.index.str[:10]).groupby(level=0)
        ok = n = 0
        for day, g in by_day:
            if day not in d.index:
                continue
            n += 1
            ok += int((abs(g - d[day]) / d[day]).min() <= 0.005)
        out[t] = round(ok / n * 100, 1) if n else None
    return out


# ---------------------------------------------------------------- measures on the NSE calendar
def aligned(series: pd.Series, cal: list[str], lag: int = 0) -> np.ndarray:
    """The value of the last bar dated on or before each session (lag 1: before the previous session)."""
    idx = np.searchsorted(series.index.to_numpy(), np.array(cal), side="right") - 1 - 0
    vals = series.to_numpy()
    out = np.where(idx >= 0, vals[np.clip(idx, 0, None)], np.nan)
    if lag:
        out = np.concatenate([[np.nan] * lag, out[:-lag]])
    return out


def exact(series: pd.Series, cal: list[str]) -> np.ndarray:
    """The value of the bar dated exactly on each session, NaN otherwise (never forward-filled)."""
    return series.reindex(cal).to_numpy(dtype=float)


def z_k1_commodity(m: C.Market, ticker: str, link: int, child: str) -> np.ndarray:
    rp = exact(guarded_returns(ticker), m.cal)
    c = m.c[child]
    rc = np.concatenate([[np.nan], np.log(c[1:] / c[:-1])])
    z = np.full(len(m.cal), np.nan)
    for d in range(61, len(m.cal)):
        if not np.isfinite(rp[d]) or not np.isfinite(rc[d]):
            continue
        a, b = rp[d - 60:d], rc[d - 60:d]
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() < 40 or np.var(b[ok]) == 0:
            continue
        beta = np.cov(a[ok], b[ok], ddof=0)[0, 1] / np.var(b[ok])
        e_hist = a[ok] - beta * b[ok]
        sd = np.std(e_hist, ddof=1)
        if sd > 0:
            z[d] = link * (rp[d] - beta * rc[d]) / sd
    return z


def z_k1_it(m: C.Market, ex_dates: set[str]) -> np.ndarray:
    adr, fx = P.load("INFY"), P.load("USDINR=X")
    a = exact(adr, m.cal)
    f = aligned(fx, m.cal)
    nse = m.c.get("INFY")
    g = np.log(a) + np.log(f) - np.log(nse)
    ex = {m.pos[d] for d in ex_dates if d in m.pos}
    for j in ex:
        g[max(0, j - 1):j + 2] = np.nan                                 # within one session of an INFY ex-date
    out = np.full(len(m.cal), np.nan)
    gd = g - pd.Series(g).rolling(20, min_periods=15).median().shift(1).to_numpy()
    for d in range(61, len(m.cal)):
        if not np.isfinite(gd[d]):
            continue
        hist = gd[d - 60:d]
        hist = hist[np.isfinite(hist)]
        if len(hist) >= 40 and np.std(hist, ddof=1) > 0:
            out[d] = gd[d] / np.std(hist, ddof=1)
    return out


def z_k5(m: C.Market, ticker: str, link: int) -> np.ndarray:
    if ticker == "INFY":
        lvl = np.log(aligned(P.load("INFY"), m.cal)) + np.log(aligned(P.load("USDINR=X"), m.cal))
    else:
        r = guarded_returns(ticker).fillna(0).cumsum()
        lvl = aligned(r, m.cal, lag=1 if ticker == "TIO=F" else 0)
    one = np.concatenate([[np.nan], np.diff(lvl)])
    z = np.full(len(m.cal), np.nan)
    for d in range(70, len(m.cal)):
        hist = one[d - 64:d - 4]                                          # 60 sessions ending d−5
        hist = hist[np.isfinite(hist)]
        if len(hist) < 40 or not np.isfinite(lvl[d]) or not np.isfinite(lvl[d - 5]):
            continue
        sd = np.std(hist, ddof=1)
        if sd > 0:
            z[d] = link * (lvl[d] - lvl[d - 5]) / (sd * math.sqrt(5))
    return z


def infy_ex_dates() -> set[str]:
    f = C.CACHE / "corp_actions.csv"
    if not f.exists():
        return set()
    ca = pd.read_csv(f, dtype=str)
    sym = "symbol" if "symbol" in ca.columns else ca.columns[0]
    dc = next((c for c in ("ex_date", "exDate", "date") if c in ca.columns), None)
    return set(ca.loc[ca[sym].str.upper() == "INFY", dc].str[:10]) if dc else set()


# ---------------------------------------------------------------- events
def events(m: C.Market, z_thr: float = Z) -> pd.DataFrame:
    ex = infy_ex_dates()
    zit1 = z_k1_it(m, ex) if "INFY" in m.c else None
    rows = []
    for g, (tk, link, kids, ks) in GROUPS.items():
        for k in ks:
            zk5 = z_k5(m, tk, link) if k == 5 else None
            for s in kids:
                s = C.canon(s)
                if s not in m.c:
                    continue
                z = (zit1 if tk == "INFY" else z_k1_commodity(m, tk, link, s)) if k == 1 else zk5
                if z is None:
                    continue
                last = -99
                for d in np.where(z <= z_thr)[0]:
                    if d - last < COOLDOWN or d + 1 >= len(m.cal) or not m.in_universe(s, d):
                        continue
                    last = d
                    rows.append({"group": g, "k": k, "symbol": s, "i": int(d), "date": m.cal[d], "z": float(z[d])})
    return pd.DataFrame(rows)


def add_returns(m: C.Market, ev: pd.DataFrame) -> pd.DataFrame:
    for h in HOLDS:
        ev[f"r{h}"] = [C.short_return(m.o[s][i + 1], m.c[s][i + h]) if i + h < len(m.cal) else np.nan
                       for s, i in zip(ev["symbol"], ev["i"])]
        ev.loc[[m.action_near(s, i - 20, i + h) for s, i in zip(ev["symbol"], ev["i"])], f"r{h}"] = np.nan
    over = {s: C.step1_days(m, s, "short_buildup", 3.0, 10.0) for s in ev["symbol"].unique()}
    ev["step1_overlap"] = [any(j in over[s] for j in range(i - 10, i + 1)) for s, i in zip(ev["symbol"], ev["i"])]
    return ev


def date_means(e: pd.DataFrame, col: str) -> pd.DataFrame:
    x = e.dropna(subset=[col])
    g = x.groupby("date").agg(r=(col, "mean"), symbol=("group", lambda v: v.value_counts().index[0]))
    return g.reset_index()


def date_cell(e: pd.DataFrame, col: str, cell: dict, pass_rules: bool) -> dict:
    dm = date_means(e, col)
    row = C.report(dm, "r", {**cell, "events": int(e[col].notna().sum())}, overlap_col=None, min_g=100, unit="shock date")
    if not pass_rules:
        row["PASS"] = ""
        return row
    fails = [row["failed"]] if row["failed"] else []
    if any((row.get(f"{y} n") or 0) < 15 for y in C.YEARS):
        fails.append(">= 15 shock dates every year")
    big = e.dropna(subset=[col])["symbol"].value_counts().index[0] if e[col].notna().any() else None
    if big:
        d2 = date_means(e[e["symbol"] != big], col)
        row["largest stock"], row["t without the largest stock"] = big, C.min_t(d2["r"], d2["date"])
    d3 = date_means(e[~e["step1_overlap"]], col)
    row["mean not a step-1 signal"], row["t not a step-1 signal"] = round(d3["r"].mean(), 3), C.min_t(d3["r"], d3["date"])
    if (row["t without the largest stock"] or 0) < 2 or (row["t not a step-1 signal"] or 0) < 2 or row["mean not a step-1 signal"] < 0.6:
        fails.append("robust (stock / step-1)")
    for g in e["group"].unique():
        d4 = date_means(e[e["group"] != g], col)
        t4 = C.min_t(d4["r"], d4["date"])
        row[f"without {g}: mean / t"] = f"{d4['r'].mean():.2f} / {t4}"
        if not (d4["r"].mean() > 0 and (t4 or 0) >= 2):
            fails.append(f"without {g}")
    row["failed"] = ", ".join(f for f in fails if f)
    row["PASS"] = "" if row["failed"] else "PASS"
    return row


def cells(m: C.Market) -> tuple[list[dict], dict]:
    chk = settlement_check()
    if any(v is None or v < 95 for v in chk.values()):
        raise SystemExit(f"§1 aborted: the daily / 1h date check failed {chk}")
    ev = add_returns(m, events(m))
    ev2 = add_returns(m, events(m, -2.0))
    out = []
    main = ev[~ev["group"].isin(SIDE_ONLY)]
    for k, name in ((1, "P1 k=1"), (5, "P2 k=5")):
        e = main[main["k"] == k]
        legs = []
        for h in HOLDS:
            primary = h in (3, 5)
            row = date_cell(e, f"r{h}", {"screen": "§1 parent indicator", "cell": f"{name}, z <= -1.5", "h": h,
                                         "role": "pass test" if primary else "descriptive"}, primary)
            out.append(row)
            if primary:
                legs.append(row)
        ok = C.joint(legs, name)
        for r in legs:
            r["PASS"] = ok
        e2 = ev2[(ev2["k"] == k) & ~ev2["group"].isin(SIDE_ONLY)]
        for h in (3, 5):
            out.append(date_cell(e2, f"r{h}", {"screen": "§1 parent indicator", "cell": f"{name}, z <= -2.0", "h": h,
                                                "role": "descriptive"}, False))
        for g in ev["group"].unique():
            eg = ev[(ev["k"] == k) & (ev["group"] == g)]
            if len(eg):
                out.append(date_cell(eg, "r5", {"screen": "§1 parent indicator", "cell": f"{name}: {g}", "h": 5,
                                                 "role": "descriptive"}, False))
    return out, {"date check (% of days within 0.5 %)": chk, "events k=1": int((ev["k"] == 1).sum()),
                 "events k=5": int((ev["k"] == 5).sum())}
