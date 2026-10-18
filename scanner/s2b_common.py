"""S2 screen B: the common rules every screen uses (strategies/S2_put_screens_B.md, "Common rules" and "Pass").

Calendar, universe, prices on the session calendar, corporate-action drops, the short return, the S2 step-1 classes
for the overlap rule, and the per-cell report with the pass test and its robustness checks.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .build import ROOT

START, END = "2021-01-01", "2026-09-25"
COST = 0.1
YEARS = tuple(str(y) for y in range(2021, 2027))
PERIODS = (("2021-22", "2021", "2022"), ("2023-24", "2023", "2024"), ("2025-26", "2025", "2026"))
SPECIAL = {"2021-11-04", "2022-10-24", "2023-11-12", "2024-11-01", "2025-10-21",          # Muhurat
           "2024-01-20", "2025-02-01", "2026-02-01"}                                    # weekend budget sessions
EXTRA_ALIASES = {"TATAMOTORS": "TMPV", "MOTHERSUMI": "MOTHERSON", "LTIM": "LTM"}
NO_EOD2 = {"HDFC", "MINDTREE", "LTI", "CADILAHC", "SRTRANSFIN", "AMARAJABAT", "GUJGASLTD", "IDFC"}
KNOWN_DEMERGERS = {("VEDL", "2026-04-30"), ("TMPV", "2025-10-14"), ("SIEMENS", "2025-04-07"),
                   ("MOTHERSON", "2022-01-14"), ("NMDC", "2022-10-27"), ("RELIANCE", "2023-07-20"),
                   ("GMRAIRPORT", "2022-01-11")}
CACHE, EOD2 = ROOT / "data" / "cache", ROOT / "data" / "eod2"


def canon(sym: str) -> str:
    """The eod2 / panel-joined name of a ticker (renames through EOD2_ALIASES and the spec's extra ones)."""
    from .equity import EOD2_ALIASES
    s = str(sym).strip().upper()
    return EXTRA_ALIASES.get(s, EOD2_ALIASES.get(s, s))


def calendar(eod2: Path = EOD2) -> list[str]:
    """NSE sessions from eod2's NIFTY 500 file in the window, without Muhurat and weekend budget sessions."""
    f = pd.read_csv(eod2 / "nifty 500.csv", usecols=["Date", "Close"], parse_dates=["Date"])
    days = f[f["Close"] > 0]["Date"].dt.strftime("%Y-%m-%d")
    return sorted(d for d in set(days) if START <= d <= END and d not in SPECIAL)


def short_return(o_entry: float, c_exit: float, cost: float = COST) -> float:
    """−(Close[exit] ÷ Open[entry] − 1) × 100 − cost; NaN when a price is missing."""
    if not (o_entry > 0 and c_exit > 0):
        return math.nan
    return -(c_exit / o_entry - 1) * 100 - cost


@dataclass
class Market:
    """Stock OHLCV on the session calendar (NaN where a stock has no EQ row), the F&O universe and the
    corporate-action dates."""
    cal: list[str]
    o: dict[str, np.ndarray] = field(default_factory=dict)
    h: dict[str, np.ndarray] = field(default_factory=dict)
    l: dict[str, np.ndarray] = field(default_factory=dict)
    c: dict[str, np.ndarray] = field(default_factory=dict)
    v: dict[str, np.ndarray] = field(default_factory=dict)
    oi: pd.DataFrame | None = None                    # session x canonical symbol, combined stock-futures OI
    expiries: set = field(default_factory=set)
    actions: dict[str, set] = field(default_factory=dict)
    dropped_no_eod2: set = field(default_factory=set)

    @property
    def pos(self) -> dict[str, int]:
        if not hasattr(self, "_pos"):
            self._pos = {d: i for i, d in enumerate(self.cal)}
        return self._pos

    def in_universe(self, sym: str, i: int) -> bool:
        """Stock futures OI > 0 on session i (the last F&O bhavcopy before the entry is the caller's choice of i)."""
        if self.oi is None or i < 0 or sym not in self.oi.columns:
            return False
        v = self.oi.iat[i, self.oi.columns.get_loc(sym)]
        return bool(v == v and v > 0)

    def action_near(self, sym: str, i_from: int, i_to: int) -> bool:
        a = self.actions.get(sym)
        if not a:
            return False
        lo, hi = self.cal[max(0, i_from)], self.cal[min(len(self.cal) - 1, i_to)]
        return any(lo <= d <= hi for d in a)


def load_market(symbols=None, eod2: Path = EOD2, cache: Path = CACHE) -> Market:
    """The calendar, the OI panel (2021-01-01 .. 2026-09-25, from the cached F&O bhavcopies), every panel stock's
    prices aligned to the calendar, and the corporate-action list."""
    from .equity import load_symbol
    from .s2_screen import oi_panel
    cal = calendar(eod2)
    panel, expiries = oi_panel(cache, START, END)
    panel.columns = [canon(s) for s in panel.columns]
    panel = panel.T.groupby(level=0).sum(min_count=1).T                          # renamed tickers joined
    panel = panel.reindex(cal)
    m = Market(cal=cal, oi=panel, expiries={str(e)[:10] for e in expiries})
    for s in sorted(set(symbols or panel.columns)):
        s = canon(s)
        if s in NO_EOD2:
            m.dropped_no_eod2.add(s)
            continue
        try:
            f = load_symbol(s, eod2)
        except Exception:  # noqa: BLE001 - renamed / delisted names without an eod2 file are counted
            m.dropped_no_eod2.add(s)
            continue
        f.index = f.index.strftime("%Y-%m-%d")
        f = f[~f.index.duplicated(keep="last")].reindex(cal)
        for k, store in (("Open", m.o), ("High", m.h), ("Low", m.l), ("Close", m.c), ("Volume", m.v)):
            store[s] = f[k].to_numpy(dtype=float)
    m.actions = corporate_actions(m, cache)
    return m


def corporate_actions(m: Market, cache: Path = CACHE) -> dict[str, set]:
    """Demerger dates per stock: corp_actions.csv rows of kind `other` whose subject names a demerger, the spec's known
    list, and any EQ one-day close move <= −30 % or >= +50 % with no listed action."""
    out: dict[str, set] = {}
    f = cache / "corp_actions.csv"
    if f.exists():
        ca = pd.read_csv(f, dtype=str)
        kind = ca.get("kind", pd.Series("", index=ca.index)).fillna("")
        subj = ca.get("subject", pd.Series("", index=ca.index)).fillna("")
        sym_col = "symbol" if "symbol" in ca.columns else ca.columns[0]
        date_col = next((c for c in ("ex_date", "exDate", "date") if c in ca.columns), None)
        if date_col:
            for r in ca[(kind == "other") & subj.str.contains("demerger", case=False)].itertuples():
                out.setdefault(canon(getattr(r, sym_col)), set()).add(str(getattr(r, date_col))[:10])
    for s, d in KNOWN_DEMERGERS:
        out.setdefault(s, set()).add(d)
    for s, c in m.c.items():
        r = pd.Series(c).pct_change(fill_method=None).to_numpy()
        for i in np.where((r <= -0.30) | (r >= 0.50))[0]:
            out.setdefault(s, set()).add(m.cal[i])
    return out


# ---------------------------------------------------------------- S2 step-1 classes (for the overlap rule)
def step1_days(m: Market, sym: str, cls: str, p_thr: float, oi_thr: float) -> set[int]:
    """Session indices where `sym` was in S2 step-1 class `cls` at these thresholds (no cooldown: the overlap rule
    removes an event if any such day falls in d−10 … d)."""
    from .s2_screen import VOL_RATIO, VOL_WINDOW, classify, skip_days
    if sym not in m.c or m.oi is None or sym not in m.oi.columns:
        return set()
    if not hasattr(m, "_skip"):
        m._skip = skip_days(m.cal, m.expiries)
    c, v = m.c[sym], m.v[sym]
    oi = m.oi[sym].to_numpy(dtype=float)
    avg = pd.Series(v).rolling(VOL_WINDOW).mean().shift(1).to_numpy()
    out = set()
    for i in range(1, len(c)):
        if m.cal[i] in m._skip or not (c[i - 1] > 0 and c[i] > 0 and oi[i - 1] > 0 and oi[i] > 0 and avg[i] > 0):
            continue
        k = classify((c[i] / c[i - 1] - 1) * 100, (oi[i] / oi[i - 1] - 1) * 100, v[i] / avg[i], p_thr, oi_thr)
        if k == cls and v[i] / avg[i] >= VOL_RATIO:
            out.add(i)
    return out


# ---------------------------------------------------------------- the per-cell report and the pass test
def iso_week(d: str) -> str:
    y, w, _ = date.fromisoformat(d).isocalendar()
    return f"{y}-W{w:02d}"


def _t(v: pd.Series, dates: pd.Series) -> float | None:
    from .stats import clustered_t
    return clustered_t(v.to_numpy(), dates.to_numpy()) if len(v) > 1 else None


def min_t(v: pd.Series, dates: pd.Series) -> float | None:
    """The smaller of the date-clustered and the ISO-week-clustered t."""
    a, b = _t(v, dates), _t(v, dates.map(iso_week))
    return None if a is None or b is None else min(a, b)


def report(ev: pd.DataFrame, col: str, cell: dict, years=YEARS, need_years: int = 5,
           must_years=("2025", "2026"), min_n: int = 100, min_g: int = 60, min_mean: float = 0.6,
           overlap_col: str | None = "step1_overlap", unit: str = "event") -> dict:
    """One cell's report (spec "Reported per cell") and the common pass test (rules 1-5). `ev` needs columns
    `date` (signal day), `symbol`, `col` (the short return), and `overlap_col` (True = an S2 step-1 signal on the same
    stock in d−10 … d). For a date-level cell pass the date means with `symbol` = the group."""
    x = ev.dropna(subset=[col])
    r, dts = x[col].astype(float), x["date"].astype(str)
    out = {**cell, "unit": unit, "N": len(x), "G": int(dts.nunique()), "weeks": int(dts.map(iso_week).nunique()) if len(x) else 0,
           "mean": round(r.mean(), 3) if len(x) else None, "median": round(r.median(), 3) if len(x) else None,
           "hit %": round((r > 0).mean() * 100, 1) if len(x) else None}
    t_d, t = _t(r, dts), min_t(r, dts)
    out.update({"t date": t_d, "t (min of date / week)": t})
    pos = 0
    for y in years:
        ry = r[dts.str[:4] == y]
        out[f"{y} n"], out[f"{y} mean"] = len(ry), round(ry.mean(), 3) if len(ry) else None
        pos += int(len(ry) > 0 and ry.mean() > 0)
    for name, a, b in PERIODS:
        rp = r[(dts.str[:4] >= a) & (dts.str[:4] <= b)]
        out[f"{name} mean"] = round(rp.mean(), 3) if len(rp) else None
    se = abs(out["mean"] / t) if t not in (None, 0) and out["mean"] else None
    out["mean needed for t=3"] = round(3 * se, 3) if se else None
    out["years positive"] = pos
    # robustness
    rob = {}
    if len(x) > 6:
        contrib = x.assign(_r=r).groupby("date")["_r"].sum().abs().sort_values(ascending=False)
        y5 = x[~x["date"].isin(contrib.index[:5])]
        rob["t without the 5 biggest dates"] = min_t(y5[col].astype(float), y5["date"].astype(str))
        big = x["symbol"].value_counts().index[0]
        ys = x[x["symbol"] != big]
        rob["largest stock"], rob["t without the largest stock"] = big, min_t(ys[col].astype(float), ys["date"].astype(str))
        if overlap_col and overlap_col in x.columns:
            yn = x[~x[overlap_col].astype(bool)]
            rob["N not a step-1 signal"] = len(yn)
            rob["mean not a step-1 signal"] = round(yn[col].mean(), 3) if len(yn) else None
            rob["t not a step-1 signal"] = min_t(yn[col].astype(float), yn["date"].astype(str)) if len(yn) > 1 else None
    out.update(rob)
    checks = {
        "N and dates": len(x) >= min_n and out["G"] >= min_g,
        "t >= 3": (t or 0) >= 3,
        f"mean >= {min_mean}": (out["mean"] or -1) >= min_mean,
        "years": pos >= need_years and all((out.get(f"{y} mean") or -1) > 0 for y in must_years),
        "robust": (rob.get("t without the 5 biggest dates") or 0) >= 2 and (rob.get("t without the largest stock") or 0) >= 2
                  and (not overlap_col or ((rob.get("t not a step-1 signal") or 0) >= 2
                                           and (rob.get("mean not a step-1 signal") or -1) >= min_mean)),
    }
    out["failed"] = ", ".join(k for k, ok in checks.items() if not ok)
    out["PASS"] = "PASS" if all(checks.values()) else ""
    return out


def joint(rows: list[dict], label: str) -> str:
    """A cell that must pass at several horizons jointly (§1, §5, §6)."""
    return "PASS" if rows and all(r["PASS"] == "PASS" for r in rows) else ""
