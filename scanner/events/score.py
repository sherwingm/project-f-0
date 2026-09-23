"""Value, materiality and bucket for a classified event, from official data only.

Value parsing: ₹/Rs/INR + number + unit, normalised to ₹ crore; the largest value in the text wins
(an order announcement usually headlines the aggregate). Market cap = eod2 close × shares outstanding
(NSE quote-equity issuedSize, cached in data/cache/shares_outstanding.csv, refreshed monthly).

Buckets (config, env-overridable):
    orders/capex   value ÷ market cap          < 1% ignore · 1–5% minor · 5–20% significant · > 20% major
    deals          quantity ÷ shares out       < 0.5% ignore · 0.5–2% · 2–5% · > 5%   (free float is not
                   published free of charge; shares outstanding is the documented fallback and is used)
    insider        % of company traded         < 0.1% ignore · 0.1–1% · 1–3% · > 3%
    rating / results / results_date / ban      always significant (event, not size)
"""
from __future__ import annotations

import csv
import io
import logging
import re
from datetime import date, datetime
from pathlib import Path

from ..build import ROOT
from . import config
from .http import EventHttp, FetchError

log = logging.getLogger(__name__)

VALUE_RE = re.compile(r"(?:₹|\bRs\.?|\bINR)\s*([\d,]+(?:\.\d+)?)\s*(crores?|cr\b|lakhs?|mn\b|million|bn\b|billion)", re.I)
UNITS_TO_CR = {"crore": 1.0, "crores": 1.0, "cr": 1.0, "lakh": 0.01, "lakhs": 0.01,
               "mn": 0.1, "million": 0.1, "bn": 100.0, "billion": 100.0}
SHARES_PATH = ROOT / "data" / "cache" / "shares_outstanding.csv"
QUOTE_URL = "https://www.nseindia.com/api/quote-equity?symbol={sym}"
ALWAYS_SIGNIFICANT = ("rating", "results", "results_date", "ban")


def finalise_rating(event: dict, page1_text: str | None) -> dict | None:
    """A rating whose subject already named a registered CRA passes through. An `unverified` candidate
    is resolved from the attachment's first page: kept (with direction and subtype) when a registered
    CRA is named there, dropped otherwise — including when there is no attachment text at all."""
    from .taxonomy import rating_direction
    if event.get("type") != "rating":
        return event
    if event.get("subtype") != "unverified":
        return event
    resolved = rating_direction(page1_text or "")
    if resolved is None:
        return None
    event["direction"], event["subtype"] = resolved
    (event.get("raw_json") or {}).pop("needs_text", None)
    return event


def parse_value_cr(text: str) -> float | None:
    best = None
    for num, unit in VALUE_RE.findall(text or ""):
        try:
            v = float(num.replace(",", "")) * UNITS_TO_CR[unit.lower().rstrip(".")]
        except (ValueError, KeyError):
            continue
        best = v if best is None else max(best, v)
    return best


def bucket_of(pct: float | None, bounds: tuple[float, float, float]) -> str:
    if pct is None:
        return "minor"                               # a real event whose size is unknown: never silently ignored
    lo, mid, hi = bounds
    return "ignore" if pct < lo else "minor" if pct < mid else "significant" if pct < hi else "major"


# ---------------------------------------------------------------- shares outstanding
def load_shares(path: Path = SHARES_PATH) -> dict[str, float]:
    if not path.exists():
        return {}
    out = {}
    for r in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))):
        try:
            out[r["symbol"]] = float(r["shares"])
        except (KeyError, ValueError):
            continue
    return out


def shares_age_days(path: Path = SHARES_PATH) -> int | None:
    if not path.exists():
        return None
    try:
        line = path.read_text(encoding="utf-8").splitlines()[1]
        return (date.today() - date.fromisoformat(line.split(",")[2][:10])).days
    except (IndexError, ValueError):
        return None


def refresh_shares(symbols: list[str], http: EventHttp | None = None, path: Path = SHARES_PATH) -> dict[str, float]:
    """issuedSize per symbol from NSE's quote API (one request each, paced); keeps old rows on failure."""
    http = http or EventHttp()
    out = load_shares(path)
    today = date.today().isoformat()
    try:                                             # Akamai refuses this endpoint on some networks: one probe
        http.get(QUOTE_URL.format(sym="RELIANCE"), "https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE",
                 tries=1)
    except FetchError as exc:
        log.warning("quote-equity is refused on this network (%s); keeping the %d cached shares rows "
                    "and bucketing sized events as 'minor'", exc, len(out))
        return out
    for i, sym in enumerate(symbols):
        try:
            q = http.get_json(QUOTE_URL.format(sym=sym.replace("&", "%26")),
                              "https://www.nseindia.com/get-quotes/equity?symbol=" + sym)
            issued = float(((q.get("securityInfo") or {}).get("issuedSize")) or 0)
            if issued > 0:
                out[sym] = issued
        except (FetchError, TypeError, ValueError) as exc:
            log.warning("shares outstanding %s: %s", sym, exc)
        if (i + 1) % 50 == 0:
            log.info("shares outstanding: %d/%d", i + 1, len(symbols))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("symbol,shares,as_of\n" + "".join(f"{s},{int(v)},{today}\n" for s, v in sorted(out.items())),
                    encoding="utf-8")
    return out


# ---------------------------------------------------------------- scoring
class Scorer:
    def __init__(self, closes: dict[str, float] | None = None, shares: dict[str, float] | None = None,
                 close_fn=None):
        self.closes = closes or {}                    # eod2 close per symbol (₹)
        self.shares = shares if shares is not None else load_shares()
        self.close_fn = close_fn                      # (symbol, iso_date) -> close near that date, for back-fills

    def market_cap_cr(self, symbol: str, on_date: str | None = None) -> float | None:
        c = self.close_fn(symbol, on_date) if (self.close_fn and on_date) else None
        c = c if c else self.closes.get(symbol)
        n = self.shares.get(symbol)
        return c * n / 1e7 if c and n else None

    def score(self, event: dict) -> dict:
        """Fill value_cr, materiality and bucket in place (and return the event)."""
        t, sym = event["type"], event["symbol"]
        raw = event.get("raw_json") or {}
        if t in ALWAYS_SIGNIFICANT:
            event["bucket"] = "significant"
            return event
        if t in ("order_win", "capacity"):
            if event.get("value_cr") is None:
                event["value_cr"] = parse_value_cr(event.get("subject") or "")
            mcap = self.market_cap_cr(sym, event.get("event_date"))
            pct = event["value_cr"] / mcap * 100 if event.get("value_cr") and mcap else None
            event["materiality"] = round(pct, 4) if pct is not None else None
            event["bucket"] = bucket_of(pct, config.ORDER_BUCKETS_PCT)
        elif t in ("block_deal", "bulk_deal"):
            qty, n = raw.get("quantity"), self.shares.get(sym)
            pct = qty / n * 100 if qty and n else None
            event["materiality"] = round(pct, 4) if pct is not None else None
            event["value_cr"] = round(qty * raw["price"] / 1e7, 2) if qty and raw.get("price") else None
            event["bucket"] = bucket_of(pct, config.DEAL_BUCKETS_PCT)
        elif t == "insider":
            qty, n = raw.get("quantity"), self.shares.get(sym)
            pct = raw.get("pct_traded")
            if pct is None and qty and n:
                pct = qty / n * 100
            event["materiality"] = round(pct, 4) if pct is not None else None
            event["value_cr"] = round(raw["value"] / 1e7, 2) if raw.get("value") else None
            event["bucket"] = bucket_of(pct, config.INSIDER_BUCKETS_PCT)
        elif t == "analyst_view":
            event["bucket"] = "minor"
        return event


# ---------------------------------------------------------------- attachment PDFs (page 1 only)
def pdf_first_page_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        log.warning("pypdf is not installed; PDF value extraction skipped")
        return ""
    try:
        reader = PdfReader(io.BytesIO(data))
        return reader.pages[0].extract_text() or "" if reader.pages else ""
    except Exception as exc:  # noqa: BLE001 - a broken PDF never breaks the run
        log.warning("PDF text extraction failed: %s", exc)
        return ""


def value_from_attachment(event: dict, http: EventHttp) -> None:
    """Only when the subject had no ₹ value and the type needs one: fetch the filing PDF, read page 1."""
    if event["type"] not in ("order_win", "capacity") or event.get("value_cr") is not None:
        return
    url = event.get("url") or ""
    if not url.lower().endswith(".pdf"):
        return
    try:
        text = pdf_first_page_text(http.download(url, "https://www.nseindia.com/"))
    except FetchError as exc:
        log.info("attachment %s: %s", url, exc)
        return
    event["value_cr"] = parse_value_cr(text)
