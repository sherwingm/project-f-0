"""G1 breakout score 0-7: RECORD ONLY (g1_research/SCORE_PREREG.md, result SCORE_RESULT.md; the user, 2026-11-07).
It stamps every G1 signal with a score and changes no rule (no filter, no size). On 259 history signals it did not rank max up,
so it is judged again at 30 live signals, max up first, by band. Thresholds are the discovery medians, frozen here (the same
numbers as g1_research/results/score_thresholds.csv; tests/test_g1_score.py checks they match)."""
from __future__ import annotations

import csv
import logging
from datetime import date
from pathlib import Path
from urllib.parse import quote

log = logging.getLogger("g1")
REPO = Path(__file__).resolve().parent.parent
HISTORY_CSV = REPO / "g1_research" / "results" / "g1_score_history.csv"
# item: (label, rule, threshold)   rule ">=" / "<=" / "<"
ITEMS = [("depth", ">=", 0.019224335783798348), ("time", "<=", 5.0), ("width", "<=", 0.3357714264292959),
         ("gap", "<=", 0.10883476101269934), ("vix", "<", 17.0), ("prev5", "<=", -0.0890731582419757),
         ("ema20", "<=", -0.13960602645583514)]


def features(lo: float, close: float, minute, width: float, gap: float | None, vix: float | None,
             closes: list[float] | None) -> dict:
    """The 7 inputs at the signal. `closes` = NIFTY daily closes before today, oldest first (None = unknown)."""
    f = {"depth": (lo - close) / lo * 100, "time": (minute.hour - 9) * 60 + minute.minute - 30, "width": width,
         "gap": gap, "vix": vix, "prev5": None, "ema20": None}
    if closes and len(closes) >= 6:
        f["prev5"] = (closes[-1] / closes[-6] - 1) * 100
        e = closes[0]
        for c in closes[1:]:
            e = e + (2 / 21) * (c - e)
        f["ema20"] = (closes[-1] / e - 1) * 100
    return f


def points(f: dict) -> tuple[int, list[str], list[str]]:
    """(score, items that scored, items with no input: scored 0)."""
    got, missing = [], []
    for lab, rule, th in ITEMS:
        x = f.get(lab)
        if x is None:
            missing.append(lab)
        elif (x >= th) if rule == ">=" else (x < th) if rule == "<" else (x <= th):
            got.append(lab)
    return len(got), got, missing


SHORT = {"depth": "Deep break", "time": "Early", "width": "Narrow range", "gap": "Gap down", "vix": "VIX<17", "prev5": "Falling 5d", "ema20": "Below EMA20"}
LABEL = {"depth": "Breakout depth", "time": "Early break", "width": "Narrow range", "gap": "Day-1 gap down", "vix": "Calm VIX",
         "prev5": "Falling 5 days", "ema20": "Below EMA20"}
RULE = {"depth": "closes at least {th:.3f} % below the range low", "time": "breaks within {th:.0f} minutes of 09:30",
        "width": "range width at most {th:.2f} %", "gap": "day-1 gap at most {th:+.2f} %", "vix": "India VIX under {th:.0f}",
        "prev5": "previous 5-day return at most {th:+.2f} %", "ema20": "previous close at most {th:+.2f} % from its EMA20"}


def meta() -> list[dict]:
    """What each point means, for the website's score board."""
    return [{"key": k, "label": LABEL[k], "short": SHORT[k], "rule": RULE[k].format(th=th)} for k, _, th in ITEMS]


def bands(trades: list) -> list[dict]:
    """Max up first, then the booked result, by score band (closed trades that carry a score)."""
    out = []
    for b in ("high 5-7", "mid 3-4", "low 0-2"):
        sel = [t for t in trades if t.get("score_band") == b]
        mu = sorted(t["max_up_pct"] for t in sel if t.get("max_up_pct") is not None)
        net = [t["net_pct"] for t in sel if t.get("net_pct") is not None]
        out.append({"band": b, "n": len(sel), "up100": (sum(v >= 100 for v in mu) / len(mu)) if mu else None,
                    "mean": sum(mu) / len(mu) if mu else None, "median": (mu[len(mu) // 2] if len(mu) % 2 else (mu[len(mu) // 2 - 1] + mu[len(mu) // 2]) / 2) if mu else None,
                    "booked": sum(net) / len(net) if net else None})
    return out


def history_scores() -> list[int]:
    try:
        with open(HISTORY_CSV, encoding="utf-8") as fh:
            return [int(float(r["score"])) for r in csv.DictReader(fh)]
    except (OSError, KeyError, ValueError) as exc:
        log.warning("g1 score: history file unavailable (%s): percentile uses live signals only", exc)
        return []


def band(score: int) -> str:
    return "low 0-2" if score <= 2 else "mid 3-4" if score <= 4 else "high 5-7"


def percentile(score: int, pool: list[int]) -> float | None:
    """Share of earlier signals with a lower score (ties count half)."""
    if not pool:
        return None
    return round((sum(s < score for s in pool) + 0.5 * sum(s == score for s in pool)) / len(pool) * 100, 1)


def stamp(f: dict, live_before: list[int]) -> dict:
    """The record kept on the day and on the trade. Pool = history + live signals before this one (it accumulates)."""
    score, got, missing = points(f)
    pool = history_scores() + list(live_before)
    avg = (sum(pool) + score) / (len(pool) + 1) / 7 * 100
    return {"score": score, "score_pct": round(score / 7 * 100, 1), "score_band": band(score), "score_items": got,
            "score_missing": missing, "score_pctile": percentile(score, pool), "score_avg_pct": round(avg, 1),
            "score_inputs": {k: (None if v is None else round(v, 4)) for k, v in f.items()}}


def daily_closes(upstox, day: date, n_days: int = 130) -> list[float] | None:
    """NIFTY 50 daily closes before `day`, oldest first, from Upstox's v3 historical API (read-only). None on any failure."""
    try:
        from server.upstox import BASE_V3
        k = quote("NSE_INDEX|Nifty 50", safe="")
        start = date.fromordinal(day.toordinal() - n_days).isoformat()
        end = date.fromordinal(day.toordinal() - 1).isoformat()
        data = upstox._get(f"/historical-candle/{k}/days/1/{end}/{start}", {}, base=BASE_V3) or {}
        rows = sorted((str(r[0])[:10], float(r[4])) for r in data.get("candles") or [] if len(r) >= 5)
        rows = [(d, c) for d, c in rows if d < day.isoformat()]
        return [c for _, c in rows] if len(rows) >= 25 else None
    except Exception as exc:  # noqa: BLE001 - the score is a record; it must never stop a trade
        log.warning("g1 score: daily closes unavailable (%s)", exc)
        return None


def line(s: dict) -> str:
    """One phone-sized line for the alert."""
    p = "" if s.get("score_pctile") is None else f", percentile {s['score_pctile']:.0f}"
    m = f" ({len(s['score_missing'])} input missing)" if s["score_missing"] else ""
    return f"score {s['score']}/7 = {s['score_pct']:.0f} % ({s['score_band']}{p}), running avg {s['score_avg_pct']:.0f} %{m}"
