"""RawItem -> typed event. All detection rules live in one editable table (RULES); direction and
subtype come from small named functions next to it. Anything no rule matches is dropped.

Tiers: 1 exchange filing / exchange data file, 2 registered agency press release (a rating that names
a registered CRA keeps tier 1 when filed on the exchange, 2 from an agency feed), 3 RSS news, which can
only ever become `analyst_view` — never an event flag, never a model feature.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable

from . import config

# ---------------------------------------------------------------- direction / subtype helpers
UPGRADE = re.compile(r"upgrad|revis\w+ (?:the )?(?:rating )?upward|outlook .*(?:revised|changed).*positive", re.I)
DOWNGRADE = re.compile(r"downgrad|revis\w+ (?:the )?(?:rating )?downward|negative watch|watch negative|"
                       r"outlook .*(?:revised|changed).*negative|rating watch with negative", re.I)
REAFFIRM = re.compile(r"reaffirm|re-affirm|reiterat|retain|maintain|assigned|unchanged", re.I)
RESULTS_WORDS = re.compile(r"financial results|results for the|unaudited|audited results|quarterly results|results of the", re.I)
FUND_WORDS = re.compile(r"mutual fund|\bmf\b|fund\b|insurance|\bfpi\b|\bfii\b|pension|investment|capital|asset management|amc\b", re.I)
PROMOTER_WORDS = re.compile(r"promoter", re.I)
DIRECTOR_WORDS = re.compile(r"director|kmp|key managerial", re.I)
BROKERS = re.compile(r"jefferies|morgan stanley|goldman|ubs\b|citi\b|citigroup|clsa|nomura|macquarie|hsbc|"
                     r"jp ?morgan|bofa|bank of america|bernstein|motilal oswal|kotak institutional|icici securities|"
                     r"axis capital|emkay|nuvama|prabhudas|hdfc securities|anand rathi|elara|investec|jm financial", re.I)
ANALYST_WORDS = re.compile(r"upgrade|downgrade|target price|initiat\w+ coverage|overweight|underweight|"
                           r"\bbuy\b rating|\bsell\b rating|price target", re.I)
_CRA = re.compile("|".join(re.escape(c) for c in config.REGISTERED_CRAS), re.I)

# "board meeting ... on September 30, 2026" / "30 September 2026" / "30-09-2026" / "30.09.2026"
_MEET_DATE = re.compile(r"(?:on|held on|scheduled (?:to be held )?on)\s+[^.,;]{0,20}?"
                        r"((?:\d{1,2}[./-]\d{1,2}[./-]\d{4})|(?:\d{1,2}(?:st|nd|rd|th)?[ -][A-Za-z]+[ ,-]+\d{4})"
                        r"|(?:[A-Za-z]+ \d{1,2},? \d{4}))", re.I)


def meeting_date(text: str) -> str | None:
    m = _MEET_DATE.search(text or "")
    if not m:
        return None
    s = re.sub(r"(\d)(st|nd|rd|th)", r"\1", m.group(1)).replace(",", " ")
    s = re.sub(r"[ -]+", " ", s).strip()
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y", "%d %m %Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def rating_direction(text: str) -> tuple[int, str] | None:
    """Direction and subtype from text that names a registered CRA; None when no CRA is named."""
    if not _CRA.search(text or ""):
        return None
    if DOWNGRADE.search(text):
        return -1, "downgrade"
    if UPGRADE.search(text):
        return 1, "upgrade"
    if REAFFIRM.search(text):
        return 0, "reaffirm"
    return 0, "other"


def _rating(item) -> tuple[int, str]:
    """NSE's list-level subject is often boilerplate ('... about Credit Rating') with the agency named
    only in the attachment. A subject that names a registered CRA resolves here; anything else becomes
    an `unverified` candidate that score.finalise_rating() must resolve from the attachment's first
    page — and drops when no registered CRA appears there either."""
    resolved = rating_direction(f"{item.get('subject', '')} {item.get('text', '')}")
    if resolved is None:
        item.setdefault("extra", {})["needs_text"] = True
        return 0, "unverified"
    return resolved


def _deal(item) -> tuple[int, str]:
    side = str(item["extra"].get("side", "")).upper()
    client = item["extra"].get("client") or ""
    who = "promoter" if PROMOTER_WORDS.search(client) else "fund" if FUND_WORDS.search(client) else "other"
    return (1 if side == "BUY" else -1 if side == "SELL" else 0), f"{who}_{side.lower() or 'na'}"


def _insider(item) -> tuple[int, str] | None:
    side = str(item["extra"].get("side", "")).upper()
    cat = str(item["extra"].get("person_category", ""))
    if "BUY" not in side and "SELL" not in side and "ACQUI" not in side and "DISPOS" not in side:
        return None                                   # pledges and the like: not a directional trade
    buy = "BUY" in side or "ACQUI" in side
    who = "promoter" if PROMOTER_WORDS.search(cat) else "director" if DIRECTOR_WORDS.search(cat) else "employee"
    return (1 if buy else -1), f"{who}_{'buy' if buy else 'sell'}"


@dataclass(frozen=True)
class Rule:
    type: str
    sources: tuple[str, ...]                          # prefixes; () = filings (nse_ann / bse_ann)
    category: re.Pattern | None
    subject: re.Pattern | None
    resolve: Callable | None = None                  # item -> (direction, subtype) | None(discard) | (0, None)
    tier: int = 1


FILINGS = ("nse_ann", "bse_ann")
RULES: tuple[Rule, ...] = (
    Rule("rating", FILINGS, re.compile(r"credit rating", re.I), None, lambda i: _rating(i)),
    Rule("results_date", FILINGS, re.compile(r"board meeting", re.I), RESULTS_WORDS, lambda i: (0, "scheduled")),
    Rule("results", FILINGS, re.compile(r"financial results", re.I), None, lambda i: (0, None)),
    # boilerplate "Outcome of Board Meeting held on <date>" resolves to results only when the results
    # words appear, or (in the runner) when the store holds a results_date for that symbol and day
    Rule("results", FILINGS, re.compile(r"outcome of board meeting", re.I), RESULTS_WORDS, lambda i: (0, None)),
    Rule("results_maybe", FILINGS, re.compile(r"outcome of board meeting", re.I), None, lambda i: (0, "unlinked")),
    Rule("order_win", FILINGS, re.compile(r"updates|press release|general|company update|award", re.I),
         re.compile(r"\border(?!s? passed)\w*\b|contract|letter of award|\bLoA\b|bagged|awarded|work order", re.I),
         lambda i: (1, None)),
    Rule("capacity", FILINGS, re.compile(r"updates|press release|general|acquisition|company update", re.I),
         re.compile(r"capacity|expansion|commissioning|greenfield|brownfield|capex|new plant|new unit|"
                    r"acquisition|acquir\w+", re.I), lambda i: (1, None)),
    Rule("block_deal", ("nse_block",), None, None, _deal),
    Rule("bulk_deal", ("nse_bulk",), None, None, _deal),
    Rule("insider", ("nse_pit",), None, None, _insider),
    Rule("ban", ("nse_ban",), None, None, lambda i: (-1, "in") if i["extra"].get("in_ban") else (0, "out")),
)


def classify(item: dict) -> dict | None:
    """The typed event for a RawItem, or None when no rule matches (dropped). RSS never enters here;
    it goes through analyst_view() only."""
    src = item.get("source", "")
    if src.startswith("rss:"):
        return None
    for rule in RULES:
        if not any(src.startswith(s) for s in rule.sources):
            continue
        if rule.category is not None and not rule.category.search(item.get("category") or ""):
            continue
        subj = f"{item.get('subject', '')} {item.get('category', '')}"
        if rule.subject is not None and not rule.subject.search(subj):
            continue
        resolved = rule.resolve(item) if rule.resolve else (0, None)
        if resolved is None:
            return None
        direction, subtype = resolved
        event_date = item["event_date"]
        if rule.type == "results_date":               # the event the market cares about is the meeting day
            md = meeting_date(f"{item.get('subject', '')} {item.get('text', '')}")
            if md and md > item["event_date"]:
                event_date = md
        return {"id": f"{src}:{item['source_id']}", "symbol": item["symbol"], "event_date": event_date,
                "event_time": item.get("event_time"), "type": rule.type, "subtype": subtype, "tier": rule.tier,
                "direction": direction, "value_cr": None, "materiality": None, "bucket": "minor",
                "source": src, "subject": (item.get("subject") or "")[:500], "url": item.get("url") or "",
                "raw_json": item.get("extra") or {}}
    return None


def analyst_view(item: dict, names_to_symbol: dict[str, str]) -> dict | None:
    """Tier-3 RSS item -> analyst_view event, only when it names a broker, an analyst action and a known
    stock. names_to_symbol maps UPPERCASED name fragments and symbols to NSE symbols."""
    if not item.get("source", "").startswith("rss:"):
        return None
    text = f"{item.get('subject', '')} {item.get('text', '')}"
    if not (BROKERS.search(text) and ANALYST_WORDS.search(text)):
        return None
    up = " " + re.sub(r"[^A-Z0-9&]+", " ", text.upper()) + " "
    sym = next((s for name, s in names_to_symbol.items() if f" {name} " in up), None)
    if not sym:
        return None
    direction = -1 if re.search(r"downgrade|underweight|\bsell\b|reduce", text, re.I) else 1
    subtype = "downgrade" if direction < 0 else "upgrade"
    return {"id": f"{item['source']}:{item['source_id']}", "symbol": sym, "event_date": item["event_date"],
            "event_time": None, "type": "analyst_view", "subtype": subtype, "tier": 3, "direction": direction,
            "value_cr": None, "materiality": None, "bucket": "minor", "source": item["source"],
            "subject": (item.get("subject") or "")[:500], "url": item.get("url") or "",
            "raw_json": {"feed": item.get("extra", {}).get("feed")}}


def name_index(symbol_names: dict[str, str]) -> dict[str, str]:
    """{'RELIANCE INDUSTRIES': 'RELIANCE', 'RELIANCE': 'RELIANCE', ...}: uppercase fragments worth
    matching in a headline, longest first so a longer company name wins over a bare symbol."""
    out: dict[str, str] = {}
    for sym, name in symbol_names.items():
        clean = re.sub(r"\b(LIMITED|LTD\.?|INDIA)\b", " ", str(name or "").upper())
        clean = re.sub(r"[^A-Z0-9&]+", " ", clean).strip()
        if len(clean) >= 5:
            out[clean] = sym
        out[sym.upper()] = sym
    return dict(sorted(out.items(), key=lambda kv: -len(kv[0])))
