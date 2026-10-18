"""S2 screen B §5: weak results × pre-move. A weak quarter (net profit YoY < −10 %), short from day 0's open; W1 = the
stock had NOT already fallen into the filing (pre5 >= 0); h3 and h5 must pass jointly."""
from __future__ import annotations

import re
from datetime import date

import numpy as np
import pandas as pd

from . import s2b_common as C

HOLDS = (0, 1, 3, 5)
MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"), 1)}
_PERIOD = re.compile(r"ended\s+(?:on\s+)?([0-9]{1,2})(?:st|nd|rd|th)?[\s,.-]*([A-Za-z]{3,})[\s,.-]*([0-9]{4})"
                     r"|ended\s+(?:on\s+)?([A-Za-z]{3,})\s*([0-9]{1,2})(?:st|nd|rd|th)?\s*,?\s*([0-9]{4})"
                     r"|ended\s+(?:on\s+)?([0-9]{1,2})[-/.]([0-9]{1,2})[-/.]([0-9]{4})"
                     r"|ended\s+(?:on\s+)?([A-Za-z]{3,})[\s,]*([0-9]{4})", re.I)
_XBRL_DATE = re.compile(r"_(\d{2})(\d{2})(\d{4})\d{6}(?:_|\.xml)", re.I)


def period_ended(subject: str) -> str | None:
    """The 'period ended' date of a results filing's subject, ISO, or None."""
    m = _PERIOD.search(str(subject or ""))
    if not m:
        return None
    g = m.groups()
    month = lambda name: next((v for k, v in MONTHS.items() if k.startswith(name.lower()[:3])), 0)   # noqa: E731
    try:
        if g[0]:
            d, mo, y = int(g[0]), month(g[1]), int(g[2])
        elif g[3]:
            mo, d, y = month(g[3]), int(g[4]), int(g[5])
        elif g[6]:
            d, mo, y = int(g[6]), int(g[7]), int(g[8])
        else:                                                     # "ended March 2022": the month's last day
            mo, y = month(g[9]), int(g[10])
            return (pd.Timestamp(y, mo, 1) + pd.offsets.MonthEnd(0)).date().isoformat()
        return date(y, mo, d).isoformat()
    except (ValueError, TypeError):
        return None


def xbrl_date(url: str | None) -> str | None:
    """The date part of an XBRL filename stamp (the clock is 12-hour and ambiguous, so only the date is used)."""
    m = _XBRL_DATE.search(str(url or ""))
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return None


def day0_0900(cal: list[str], d: str, t: str | None) -> int | None:
    """Day 0 = the filing day if filed before 09:00 on a session day, else the next session."""
    i = int(np.searchsorted(cal, d))
    if i < len(cal) and cal[i] == d and t and str(t)[:5] < "09:00":
        return i
    j = int(np.searchsorted(cal, d, side="right"))
    return j if j < len(cal) else None


def base_k(cal: list[str], d: str, t: str | None) -> int:
    """The last session whose close is strictly before the filing."""
    i = int(np.searchsorted(cal, d))
    if i < len(cal) and cal[i] == d and t and str(t)[:5] >= "15:30":
        return i                                                  # after the close on a session day
    return i - 1                                                  # before / during the session, or a non-session day


def events(m: C.Market, store_events, fin: dict) -> tuple[pd.DataFrame, dict]:
    from .peak_study import quarter_back, quarter_of
    first: dict[tuple, tuple] = {}
    for e in store_events:
        if e["type"] != "results":
            continue
        key = (C.canon(e["symbol"]), e["event_date"])
        t = e.get("event_time") or "99:99"
        if key not in first or t < first[key][0]:
            first[key] = (t, e.get("subject"))
    drops = {"period not parsed": 0, "period disagrees": 0, "as-filed rule": 0, "no numbers / base <= 0": 0,
             "not weak": 0, "outside universe or prices": 0}
    rows, seen = [], set()
    for (s, d), (t, subj) in sorted(first.items(), key=lambda kv: (kv[0][1], kv[1][0])):
        t = None if t == "99:99" else t
        i = day0_0900(m.cal, d, t)
        if i is None or i < 6 or (s, i) in seen:
            continue
        q = quarter_of(d)
        per = period_ended(subj)
        if per is None:
            drops["period not parsed"] += 1
            continue
        if per != q:
            drops["period disagrees"] += 1
            continue
        qs = (fin.get(s) or {}).get("quarters") or {}
        cur, ya = qs.get(q) or {}, qs.get(quarter_back(q, 4)) or {}
        stamps = [xbrl_date(x.get("xbrl")) for x in (cur, ya) if x]
        if any(st is None for st in stamps):
            drops["xbrl date unreadable (kept)"] = drops.get("xbrl date unreadable (kept)", 0) + 1
        if any(st and st > (pd.Timestamp(d) + pd.Timedelta(days=1)).date().isoformat() for st in stamps):
            drops["as-filed rule"] += 1
            continue
        np0, np4 = cur.get("net_profit"), ya.get("net_profit")
        if np0 is None or np4 is None or not np4 > 0:
            drops["no numbers / base <= 0"] += 1
            continue
        yoy = (np0 / np4 - 1) * 100
        if not yoy < -10:
            drops["not weak"] += 1
            continue
        if s not in m.c or not m.in_universe(s, i - 1):
            drops["outside universe or prices"] += 1
            continue
        seen.add((s, i))
        k = base_k(m.cal, d, t)
        c = m.c[s]
        pre5 = (c[k] / c[k - 5] - 1) * 100 if c[k] > 0 and c[k - 5] > 0 else np.nan
        pre10 = (c[k] / c[k - 10] - 1) * 100 if k >= 10 and c[k] > 0 and c[k - 10] > 0 else np.nan
        q1 = qs.get(quarter_back(q, 1)) or {}
        qoq = (np0 / q1["net_profit"] - 1) * 100 if q1.get("net_profit") and q1["net_profit"] > 0 else np.nan
        rows.append({"symbol": s, "i": i, "date": m.cal[i], "filed": d, "filed_time": t, "np_yoy": yoy, "np_qoq": qoq,
                     "pre5": pre5, "pre10": pre10})
    return pd.DataFrame(rows), drops


def add_returns(m: C.Market, ev: pd.DataFrame) -> pd.DataFrame:
    for h in HOLDS:
        ev[f"r{h}"] = [C.short_return(m.o[s][i], m.c[s][i + h]) if i + h < len(m.cal) else np.nan
                       for s, i in zip(ev["symbol"], ev["i"])]
        ev.loc[[m.action_near(s, i - 20, i + h) for s, i in zip(ev["symbol"], ev["i"])], f"r{h}"] = np.nan
    over = {s: C.step1_days(m, s, "short_buildup", 3.0, 10.0) for s in ev["symbol"].unique()}
    fil = {(s, i): int(np.searchsorted(m.cal, f)) for s, i, f in zip(ev["symbol"], ev["i"], ev["filed"])}
    ev["step1_overlap"] = [(i in over[s]) or (fil[(s, i)] in over[s]) for s, i in zip(ev["symbol"], ev["i"])]
    return ev


def cells(ev: pd.DataFrame) -> list[dict]:
    from .stats import clustered_diff_t
    out = []
    w1, ctl = ev[ev["pre5"] >= 0], ev[ev["pre5"] < 0]
    for h in HOLDS:
        role = "pass test" if h in (3, 5) else "descriptive"
        row = C.report(w1, f"r{h}", {"screen": "§5 weak results", "cell": "W1 weak, not yet fallen (pre5 >= 0)", "h": h,
                                     "role": role})
        if role != "pass test":
            row["PASS"] = ""
        out.append(row)
    legs = [r for r in out if r["role"] == "pass test"]
    ok = C.joint(legs, "W1")
    for r in legs:
        r["PASS"] = ok
    for h in HOLDS:
        row = C.report(ctl, f"r{h}", {"screen": "§5 weak results", "cell": "control: weak, already fell (pre5 < 0)",
                                      "h": h, "role": "descriptive"})
        a, b = w1.dropna(subset=[f"r{h}"]), ctl.dropna(subset=[f"r{h}"])
        row["W1 minus control t"] = clustered_diff_t(a[f"r{h}"], a["date"], b[f"r{h}"], b["date"]) if len(a) > 1 and len(b) > 1 else None
        row["PASS"] = ""
        out.append(row)
    core = ev[ev["np_qoq"] < 0]
    for lab, e in (("pre10 >= 0", ev[ev["pre10"] >= 0]), ("S1 v9 core (YoY < -10, QoQ < 0), pre5 >= 0", core[core["pre5"] >= 0])):
        for h in (3, 5):
            row = C.report(e, f"r{h}", {"screen": "§5 weak results", "cell": lab, "h": h, "role": "descriptive"})
            row["PASS"] = ""
            out.append(row)
    return out
