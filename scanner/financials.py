"""Quarterly results numbers per F&O stock (revenue, net profit, EPS) from NSE's XBRL filings, for the page's
Results tab: the last 3 quarters with QoQ and YoY change.

    python -m scanner.financials                      # stocks with a results filing in the last 5 days, or never fetched
    python -m scanner.financials --all                # every F&O stock (first fill: ~210 stocks, ~30 min at 1 req/s)
    python -m scanner.financials --symbols RELIANCE HDFCBANK

Sources (checked 2026-10-13):
- quarters from Mar 2025 on: NSE "Integrated Filing - Financials"
  (www.nseindia.com/api/integrated-filing-results?index=equities&symbol=X), one XBRL file per quarter and basis;
- earlier quarters (needed for YoY): www.nseindia.com/api/corporates-financial-results?...&period=Quarterly.
Both XBRL kinds tag the quarter's own figures with the context "OneD". Values are rupees; stored in Rs crore.
Consolidated figures when the latest quarter has them, else standalone, the same basis for every quarter of a stock.
Writes data/financials.json (committed by the nightly workflow); scanner/build.py embeds the result per stock.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from .build import ROOT
from .events.http import EventHttp, FetchError

log = logging.getLogger("financials")
PATH = ROOT / "data" / "financials.json"
INTEGRATED = "https://www.nseindia.com/api/integrated-filing-results?index=equities&symbol={sym}"
OLD = "https://www.nseindia.com/api/corporates-financial-results?index=equities&symbol={sym}&period=Quarterly"
REFERER = "https://www.nseindia.com/companies-listing/corporate-integrated-filing"
CRORE = 1e7
# first tag present wins (companies, then banks); all read in the quarter's own context "OneD"
TAGS = {
    "revenue": ("RevenueFromOperations", "InterestEarned", "Income"),
    "net_profit": ("ProfitLossForPeriod", "ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates",
                   "ProfitLossForThePeriod"),
    "eps": ("BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
            "BasicEarningsLossPerShareFromContinuingOperations", "BasicEarningsPerShareAfterExtraordinaryItems",
            "BasicEarningsPerShareBeforeExtraordinaryItems"),
}
SHOW = 3                                   # quarters on the page


# ---------------------------------------------------------------- parsing (pure)
def parse_xbrl(text: str) -> dict:
    """{"revenue": Rs crore, "net_profit": Rs crore, "eps": Rs} for the quarter (context OneD); None when absent."""
    out = {}
    for field, tags in TAGS.items():
        val = None
        for t in tags:
            m = re.search(r"<[A-Za-z0-9_-]+:" + t + r'\b[^>]*contextRef="OneD"[^>]*>\s*([-0-9.Ee+]+)\s*<', text)
            if m:
                val = float(m.group(1))
                break
        out[field] = None if val is None else (round(val, 2) if field == "eps" else round(val / CRORE, 2))
    return out


def _iso(d: str) -> str:
    return datetime.strptime(d.strip().title(), "%d-%b-%Y").date().isoformat()


def filings(integrated: list[dict], old: list[dict]) -> dict[tuple[str, str], str]:
    """{(quarter end ISO, "consolidated" | "standalone"): xbrl url}, the newest filing of each; integrated wins."""
    out: dict[tuple[str, str], tuple[str, str]] = {}
    for r in old or []:
        if r.get("cumulative") != "Non-cumulative" or not r.get("xbrl") or not r.get("toDate"):
            continue
        basis = "consolidated" if r.get("consolidated") == "Consolidated" else "standalone"
        k, when = (_iso(r["toDate"]), basis), r.get("broadCastDate") or ""
        if k not in out or when > out[k][1]:
            out[k] = (r["xbrl"], when)
    seen: dict[tuple[str, str], str] = {}
    for r in integrated or []:
        if "Financ" not in (r.get("type") or "") or not r.get("xbrl") or not r.get("qe_Date"):
            continue
        basis = "consolidated" if (r.get("consolidated") or "").lower().startswith("consol") else "standalone"
        k, when = (_iso(r["qe_Date"]), basis), _sortable(r.get("broadcast_Date"))
        if k not in seen or when > seen[k]:
            seen[k] = when
            out[k] = (r["xbrl"], when)
    return {k: v[0] for k, v in out.items()}


def _sortable(s: str | None) -> str:
    try:
        return datetime.strptime(s or "", "%d-%b-%Y %H:%M:%S").isoformat()
    except ValueError:
        return ""


def quarter_back(q: str, n: int = 1) -> str:
    """The quarter end n quarters before q (ISO)."""
    d = date.fromisoformat(q)
    m = d.month - 3 * n
    y = d.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    nxt = date(y + (m // 12), m % 12 + 1, 1)
    return (nxt - timedelta(days=1)).isoformat()


def needed(latest: str) -> list[str]:
    """The quarters the page needs: the last SHOW, the one before them (QoQ) and each one's year-ago quarter."""
    show = [quarter_back(latest, i) for i in range(SHOW)]
    return sorted(set(show + [quarter_back(latest, SHOW)] + [quarter_back(q, 4) for q in show]), reverse=True)


def pct(a, b) -> float | str | None:
    """% change from b to a; None when either is missing; "n/m" (not meaningful) when the base is zero or a loss."""
    if a is None or b is None:
        return None
    if b <= 0:
        return "n/m"
    return round((a - b) / b * 100, 1)


def summary(rec: dict) -> dict | None:
    """The page block: {basis, quarters: [{period, revenue, net_profit, eps, *_qoq, *_yoy}] newest first}."""
    qs = rec.get("quarters") or {}
    if not qs:
        return None
    latest = max(qs)
    rows = []
    for i in range(SHOW):
        q = quarter_back(latest, i)
        cur = qs.get(q)
        if not cur:
            continue
        prev, ya = qs.get(quarter_back(q, 1)) or {}, qs.get(quarter_back(q, 4)) or {}
        row = {"period": q, "filed": cur.get("filed")}
        for f in TAGS:
            row[f] = cur.get(f)
            row[f + "_qoq"] = pct(cur.get(f), prev.get(f))
            row[f + "_yoy"] = pct(cur.get(f), ya.get(f))
        rows.append(row)
    return {"basis": rec.get("basis"), "quarters": rows, "updated": rec.get("updated")}


# ---------------------------------------------------------------- fetching
class Fetcher:
    def __init__(self, http: EventHttp | None = None):
        self.http = http or EventHttp()

    def stock(self, sym: str, have: dict | None = None) -> dict | None:
        """The stored record for `sym`, refreshed: new quarters fetched, known ones kept."""
        have = have or {}
        integ = self.http.get_json(INTEGRATED.format(sym=_q(sym)), REFERER)
        integ = integ.get("data", []) if isinstance(integ, dict) else (integ or [])
        files = filings(integ, [])
        if not files:
            return None
        latest = max(q for q, _ in files)
        basis = "consolidated" if (latest, "consolidated") in files else "standalone"
        want = needed(latest)
        if any((q, basis) not in files for q in want):         # year-ago quarters before Mar 2025
            try:
                old = self.http.get_json(OLD.format(sym=_q(sym)), REFERER)
                files = filings(integ, old if isinstance(old, list) else [])
            except FetchError as exc:
                log.warning("%s: older results list unavailable (%s)", sym, exc)
        quarters = dict(have.get("quarters") or {}) if have.get("basis") == basis else {}
        for q in want:
            url = files.get((q, basis))
            if not url or (q in quarters and quarters[q].get("xbrl") == url):
                continue
            try:
                quarters[q] = {**parse_xbrl(self.http.get_text(url, REFERER)), "xbrl": url, "filed": None}
            except FetchError as exc:
                log.warning("%s %s: %s", sym, q, exc)
        quarters = {q: v for q, v in quarters.items() if q in want}
        return {"basis": basis, "quarters": quarters, "updated": date.today().isoformat()}


def _q(sym: str) -> str:
    from urllib.parse import quote
    return quote(sym, safe="")


def load(path: Path = PATH) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def due(universe: list[str], store: dict, recent_results: set[str]) -> list[str]:
    """Stocks to refresh tonight: never fetched, or with a results filing in the last few days."""
    return [s for s in universe if s not in store or s in recent_results]


def recent_results(days: int = 5) -> set[str]:
    try:
        from .events.store import Store
        since = (date.today() - timedelta(days=days)).isoformat()
        with Store() as st:
            return {e["symbol"] for e in st.all_of_type("results") if e["event_date"] >= since}
    except Exception as exc:  # noqa: BLE001 - no event store: refresh only the never-fetched
        log.warning("event store unavailable (%s)", exc)
        return set()


def main() -> None:
    ap = argparse.ArgumentParser(description="Quarterly results numbers from NSE XBRL filings -> data/financials.json")
    ap.add_argument("--all", action="store_true", help="refresh every F&O stock")
    ap.add_argument("--symbols", nargs="*", help="refresh only these")
    ap.add_argument("--limit", type=int, default=None, help="at most this many stocks this run (the rest next run)")
    ap.add_argument("--out", type=Path, default=PATH)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from .universe import fetch_fo_lots
    store = load(a.out)
    universe = sorted(fetch_fo_lots(cache_path=ROOT / "data" / "cache" / "fo_universe.txt"))
    todo = [s.upper() for s in a.symbols] if a.symbols else (universe if a.all else due(universe, store, recent_results()))
    if a.limit is not None:
        todo = sorted(todo, key=lambda s: s in store)[: a.limit]          # never-fetched first
    f, done, failed = Fetcher(), 0, []
    log.info("%d stocks to refresh", len(todo))
    for i, sym in enumerate(todo, 1):
        try:
            rec = f.stock(sym, store.get(sym))
            if rec:
                store[sym] = rec
                done += 1
            else:
                failed.append(sym)
        except FetchError as exc:
            log.warning("%s: %s", sym, exc)
            failed.append(sym)
        if i % 10 == 0 or i == len(todo):                     # resumable: progress is saved as it goes
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(store, indent=0, sort_keys=True), encoding="utf-8")
            log.info("%d / %d (%d failed)", i, len(todo), len(failed))
    print(f"financials: {done} refreshed, {len(failed)} without data{': ' + ' '.join(failed[:30]) if failed else ''}")


if __name__ == "__main__":
    main()
