"""Fetch, classify, score and store a day's events — or back-fill years, resumably.

    python -m scanner.events.run --day 2026-09-24
    python -m scanner.events.run --backfill 2023-01-01 2026-09-24     # resumable; progress in
                                                                      # data/cache/events_backfill.json
    python -m scanner.events.run --fixtures                           # one fixture day, no network

Per day: every source's items -> taxonomy -> scoring (market cap on the event's date where eod2 has
it) -> finalisation (unverified ratings resolved from the filing PDF's first page, universe symbols
only; results_maybe linked to a stored results_date; out-of-ban events derived from the previous
list) -> store. Only universe (F&O) symbols are kept: the scan, study and model see nothing else.
Status per source lands in data/cache/events_status.json; the scan shows it as meta.events_status.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..build import ROOT
from ..universe import fetch_fo_lots
from . import config
from .http import EventHttp, FetchError
from .score import (Scorer, finalise_rating, load_shares, pdf_first_page_text, refresh_shares,
                    shares_age_days, value_from_attachment)
from .sources import bse_announcements, nse_announcements, nse_ban, nse_deals, nse_pit, rss
from .store import Store
from .taxonomy import analyst_view, classify, name_index

log = logging.getLogger("events")
OTHER_AGENCIES = re.compile(r"moody'?s|fitch|s&p global|standard & poor'?s|r&i\b|japan credit rating", re.I)
IST = timezone(timedelta(hours=5, minutes=30))
STATUS_PATH = ROOT / "data" / "cache" / "events_status.json"
PROGRESS_PATH = ROOT / "data" / "cache" / "events_backfill.json"
RATING_DROPS_PATH = ROOT / "data" / "cache" / "rating_drops.jsonl"
NAMES_PATH = ROOT / "data" / "cache" / "equity_names.csv"
MAX_ATTACHMENTS_PER_RUN = 40          # PDF page-1 lookups per daily run (backfill chunks budget their own)
RESULTS_GAP_DAYS = 5                  # another results filing for a stock within this many days is the same results

FIXTURES_BY_SOURCE = {"nse_ann": "nse_announcements.json", "nse_block": "nse_block_deals.json",
                      "nse_bulk": "nse_bulk_deals.json", "nse_ban": "nse_ban.csv", "nse_pit": "nse_pit.json",
                      "bse_ann": "bse_announcements.json", "rss:et_markets": "rss_et.xml"}


def load_names(http: EventHttp | None = None, path: Path = NAMES_PATH) -> dict[str, str]:
    """NSE symbol -> company name, cached from EQUITY_L.csv (used only to spot stocks in RSS titles)."""
    if not path.exists():
        try:
            text = (http or EventHttp()).get_text(bse_announcements.NSE_MASTER, "https://www.nseindia.com/")
        except FetchError as exc:
            log.warning("equity names unavailable (%s); analyst views match bare symbols only", exc)
            return {}
        import csv as _csv
        import io as _io
        rows = [{k.strip(): (v or "").strip() for k, v in r.items()} for r in _csv.DictReader(_io.StringIO(text))]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("symbol,name\n" + "".join(f'{r["SYMBOL"]},"{r["NAME OF COMPANY"]}"\n'
                                                  for r in rows if r.get("SERIES") == "EQ"), encoding="utf-8")
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        sym, _, name = line.partition(",")
        out[sym] = name.strip('"')
    return out


class Runner:
    def __init__(self, store: Store | None = None, http: EventHttp | None = None,
                 universe: set[str] | None = None, fixtures: bool = False, eod2_dir: Path | None = None):
        self.store = store or Store()
        self.http = http or EventHttp()
        self.fixtures = fixtures
        self.eod2_dir = eod2_dir or ROOT / "data" / "eod2"
        self.status: dict[str, dict] = json.loads(STATUS_PATH.read_text()) if STATUS_PATH.exists() else {}
        if universe is not None:
            self.universe = universe
        else:
            try:
                self.universe = set(fetch_fo_lots(cache_path=ROOT / "data" / "cache" / "fo_universe.txt"))
            except Exception as exc:  # noqa: BLE001 - no universe file and no network
                log.warning("no F&O universe (%s); keeping every symbol", exc)
                self.universe = set()
        self._frames: dict[str, object] = {}
        self.scorer = Scorer(close_fn=self._close_near)
        self.names = {}

    # ------------------------------------------------------------ eod2 closes for market cap at event time
    def _close_near(self, symbol: str, iso_date: str):
        if symbol not in self._frames:
            try:
                from ..equity import load_symbol
                self._frames[symbol] = load_symbol(symbol, self.eod2_dir)
            except Exception:  # noqa: BLE001
                self._frames[symbol] = None
        f = self._frames[symbol]
        if f is None or f.empty:
            return None
        sub = f[f.index <= iso_date]
        return float(sub["Close"].iloc[-1]) if len(sub) else None

    # ------------------------------------------------------------ one source, one day
    def _fetch(self, name: str, day: date) -> list[dict]:
        fx = FIXTURES_BY_SOURCE.get(name) if self.fixtures else None
        if name == "nse_ann":
            return nse_announcements.fetch(day, self.http, fixture=fx)
        if name == "nse_block":
            return nse_deals.fetch(day, self.http, fixture=fx, kind="block")
        if name == "nse_bulk":
            return nse_deals.fetch(day, self.http, fixture=fx, kind="bulk")
        if name == "nse_ban":
            return nse_ban.fetch(day, self.http, fixture=fx)
        if name == "nse_pit":
            return nse_pit.fetch(day, self.http, fixture=fx)
        if name == "bse_ann":
            return bse_announcements.fetch(day, self.http, fixture=fx)
        if name.startswith("rss:"):
            feed = name.split(":", 1)[1]
            return rss.fetch(day, self.http, fixture=fx, feed=feed)
        raise ValueError(name)

    def sources(self) -> list[str]:
        return ["nse_ann", "bse_ann", "nse_block", "nse_bulk", "nse_ban", "nse_pit"] + \
               [f"rss:{f}" for f in (["et_markets"] if self.fixtures else list(config.RSS_FEEDS))]

    # ------------------------------------------------------------ the day
    def run_day(self, day: date, attachments_budget: int = MAX_ATTACHMENTS_PER_RUN) -> dict:
        if not self.names:
            self.names = name_index({s: n for s, n in load_names(None if self.fixtures else self.http).items()
                                     if not self.universe or s in self.universe})
        counts: dict[str, int] = {}
        events: list[dict] = []
        for src in self.sources():
            try:
                items = self._fetch(src, day)
                self.status[src] = {"last_success": datetime.now(IST).isoformat(timespec="seconds"),
                                    "items": len(items), "error": None}
            except FetchError as exc:
                log.warning("%s: %s", src, exc)
                self.status[src] = {**self.status.get(src, {}), "error": str(exc)[:300]}
                continue
            for item in items:
                e = analyst_view(item, self.names) if src.startswith("rss:") else classify(item)
                if e is None:
                    continue
                if self.universe and e["symbol"] not in self.universe:
                    continue
                events.append(e)
        events.extend(self._ban_out_events(day, [e for e in events if e["type"] == "ban"]))
        written = self._settle(events, attachments_budget)
        for e in written:
            counts[e["type"]] = counts.get(e["type"], 0) + 1
        self._save_status()
        log.info("%s: %d events (%s)", day, len(written), ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none")
        return counts

    def _settle(self, events: list[dict], attachments_budget: int = -1) -> list[dict]:
        """Finalise, score and store one batch. results_maybe is linked against both this batch and the
        store, and is settled after everything else so a same-batch results_date counts."""
        first, maybes = [], []
        for e in events:
            (maybes if e["type"] == "results_maybe" else first).append(e)
        first = self._one_results(first)
        done = []
        for e in first:
            e = self._finalise(e, attachments_budget)
            if e is not None:
                attachments_budget -= _uses_attachment(e)
                done.append(self.scorer.score(e))
        if done:
            self.store.upsert(done)
        dated = {(e["symbol"], e["event_date"]) for e in first if e["type"] == "results_date"}
        linked = []
        for e in maybes:
            if (e["symbol"], e["event_date"]) in dated or any(
                    x["type"] == "results_date" for x in
                    self.store.events_for(e["symbol"], since=e["event_date"], until=e["event_date"])):
                e["type"], e["subtype"] = "results", "outcome"
                linked.append(self.scorer.score(e))
        linked = self._one_results(linked)
        if linked:
            self.store.upsert(linked)
        return done + linked

    def _one_results(self, events: list[dict]) -> list[dict]:
        """Drop a results event when the stock already has results (in this batch or the store) up to
        RESULTS_GAP_DAYS earlier: the board outcome, the results filing and a next-day copy are one event."""
        out, last = [], {}
        for e in sorted(events, key=lambda x: (x["event_date"], x.get("event_time") or "")):
            if e["type"] != "results":
                out.append(e)
                continue
            d = date.fromisoformat(e["event_date"])
            prev = last.get(e["symbol"])
            if prev is None:
                lo = (d - timedelta(days=RESULTS_GAP_DAYS)).isoformat()
                stored = [x["event_date"] for x in self.store.events_for(e["symbol"], since=lo, until=e["event_date"])
                          if x["type"] == "results" and x["id"] != e["id"]]
                prev = max(stored) if stored else None
            if prev is not None and 0 <= (d - date.fromisoformat(prev)).days <= RESULTS_GAP_DAYS:
                continue
            last[e["symbol"]] = e["event_date"]
            out.append(e)
        return out

    def _finalise(self, e: dict, budget_left: int) -> dict | None:
        if e["type"] == "rating" and e.get("subtype") == "unverified":
            text = self._page1(e, budget_left)
            kept = finalise_rating(e, text)
            if kept is None:
                self._log_rating_drop(e, text, budget_left)
            return kept
        if getattr(self, "_pdf_ratings_only", False):
            return e
        if e["type"] in ("order_win", "capacity") and e.get("value_cr") is None:
            from .score import parse_value_cr
            if parse_value_cr(e.get("subject") or "") is None:
                text = self._page1(e, budget_left)
                if text:
                    e["value_cr"] = parse_value_cr(text)
        return e

    def _log_rating_drop(self, e: dict, text: str | None, budget_left: int) -> None:
        """Why a 'Credit Rating' filing did not become a rating event, one JSON line per filing."""
        url = e.get("url") or ""
        if not url.lower().endswith(".pdf"):
            why = "no PDF attachment"
        elif text is None:
            pdf_allowed = budget_left >= 0 or getattr(self, "_pdf_ratings_only", False)
            why = "attachment not read (no --rating-attachments pass / budget spent)" if not pdf_allowed                 else "attachment download or PDF read failed"
        elif not text.strip():
            why = "page 1 has no extractable text (scanned image)"
        else:
            other = OTHER_AGENCIES.search(text)
            why = "page 1 names no SEBI-registered CRA" + (f" (names {other.group(0)})" if other else "")
        rec = {"date": e["event_date"], "symbol": e["symbol"], "reason": why, "subject": (e.get("subject") or "")[:200],
               "url": url}
        RATING_DROPS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with RATING_DROPS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")

    def _page1(self, e: dict, budget_left: int) -> str | None:
        url = e.get("url") or ""
        allow = budget_left >= 0 or (getattr(self, "_pdf_ratings_only", False)
                                     and e["type"] == "rating" and e.get("subtype") == "unverified")
        if self.fixtures or not url.lower().endswith(".pdf") or not allow:
            return None
        try:
            return pdf_first_page_text(self.http.download(url, "https://www.nseindia.com/"))
        except FetchError as exc:
            log.info("attachment %s: %s", url, exc)
            return None

    def _ban_out_events(self, day: date, today_in: list[dict]) -> list[dict]:
        prev = self.store.all_of_type("ban")
        prev_days = sorted({e["event_date"] for e in prev if e["event_date"] < day.isoformat()})
        if not prev_days:
            return []
        last = prev_days[-1]
        now_in = {e["symbol"] for e in today_in}
        out = []
        for e in prev:
            if e["event_date"] == last and e.get("subtype") == "in" and e["symbol"] not in now_in:
                out.append({"id": f"nse_ban:{day.isoformat()}:{e['symbol']}:out", "symbol": e["symbol"],
                            "event_date": day.isoformat(), "event_time": None, "type": "ban", "subtype": "out",
                            "tier": 1, "direction": 0, "value_cr": None, "materiality": None,
                            "bucket": "significant", "source": "nse_ban",
                            "subject": f"{e['symbol']} out of the F&O ban", "url": "", "raw_json": {"in_ban": False}})
        return out

    # ------------------------------------------------------------ back-fill
    def backfill(self, start: date, end: date, rating_attachments: bool = False) -> dict[str, int]:
        """rating_attachments: fetch each unverified rating's filing PDF (first page) so boilerplate
        'informed the Exchange about Credit Rating' subjects resolve; order/capacity PDFs stay off.
        Meant as a second pass over nse_ann (delete its key from events_backfill.json to redo it)."""
        self._pdf_ratings_only = rating_attachments
        progress = json.loads(PROGRESS_PATH.read_text()) if PROGRESS_PATH.exists() else {}
        total: dict[str, int] = {}
        jobs = [("nse_ann", nse_announcements.backfill(start, end, self.http)),
                ("nse_block", nse_deals.backfill(start, end, self.http, kind="block")),
                ("nse_bulk", nse_deals.backfill(start, end, self.http, kind="bulk")),
                ("nse_pit", nse_pit.backfill(start, end, self.http)),
                ("nse_ban", nse_ban.backfill(start, end, self.http))]
        for src, gen in jobs:
            done = set(progress.get(src, []))
            for label, items in gen:
                if label in done:
                    continue
                try:
                    events = []
                    for item in items:
                        e = classify(item)
                        if e is not None and (not self.universe or e["symbol"] in self.universe):
                            events.append(e)
                    if src == "nse_ban":
                        events.extend(self._ban_out_events(date.fromisoformat(label), [x for x in events if x["type"] == "ban"]))
                    written = self._settle(events)             # back-fill never fetches attachments per item
                    for t in (e["type"] for e in written):
                        total[t] = total.get(t, 0) + 1
                except Exception as exc:  # noqa: BLE001 - one bad chunk must not stop a 3-year fill
                    log.warning("backfill %s %s: %s", src, label, exc)
                    continue
                done.add(label)
                progress[src] = sorted(done)
                PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
                PROGRESS_PATH.write_text(json.dumps(progress))
            log.info("backfill %s done: %d chunks", src, len(done))
        self._save_status()
        return total

    def ensure_shares(self, max_age_days: int = 31) -> None:
        age = shares_age_days()
        if age is not None and age <= max_age_days and load_shares():
            return
        if self.fixtures:
            return
        log.info("refreshing shares outstanding for %d symbols (monthly)", len(self.universe))
        refresh_shares(sorted(self.universe), self.http)
        self.scorer.shares = load_shares()

    def _save_status(self) -> None:
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text(json.dumps(self.status, indent=1))


def _uses_attachment(e: dict) -> int:
    return 1 if (e["type"] == "rating" and e.get("subtype") == "unverified") or \
                (e["type"] in ("order_win", "capacity")) else 0


def main() -> None:
    ap = argparse.ArgumentParser(description="fetch, classify and store exchange events")
    ap.add_argument("--day", type=date.fromisoformat)
    ap.add_argument("--backfill", nargs=2, type=date.fromisoformat, metavar=("START", "END"))
    ap.add_argument("--rating-attachments", action="store_true",
                    help="with --backfill: resolve boilerplate rating filings from their PDFs (first page)")
    ap.add_argument("--fixtures", action="store_true", help="one fixture day (2026-09-22), no network")
    ap.add_argument("--no-shares", action="store_true", help="skip the monthly shares-outstanding refresh")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    r = Runner(fixtures=a.fixtures)
    if not a.no_shares and not a.fixtures:
        r.ensure_shares()
    if a.backfill:
        total = r.backfill(*a.backfill, rating_attachments=a.rating_attachments)
    else:
        total = r.run_day(a.day or (date(2026, 9, 22) if a.fixtures else datetime.now(IST).date()))
    print("events by type:", json.dumps(dict(sorted(total.items())), indent=1))
    print("store now holds:", json.dumps(Store().counts_by_type() if r.store is None else r.store.counts_by_type(), indent=1))


if __name__ == "__main__":
    main()
