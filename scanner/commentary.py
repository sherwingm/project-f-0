"""Plain-English read-out of the finished scan, written by Claude at build time.

The model only ever sees the aggregated numbers the page already shows, and is instructed to
describe them, not to recommend. The output is checked for instruction-like trading language
and dropped (with a log line) if any slips through, so the page never carries a trade call.
Requires ANTHROPIC_API_KEY; enabled with `python -m scanner.build --commentary`.
"""
from __future__ import annotations

import logging
import os
import re

log = logging.getLogger(__name__)

MODEL = os.getenv("COMMENTARY_MODEL", "claude-sonnet-5")

SYSTEM = (
    "You write a short factual read-out of an end-of-day NSE F&O data scan for a reader who will "
    "interpret the data themselves. Describe what the numbers show: how the labels are distributed, "
    "which stocks stand out on volume ratio, futures OI change and PCR, and any clustering you can see "
    "from the figures given. Plain sentences, no headings, no bullet points, no markdown, at most "
    "three short paragraphs. Strictly descriptive: do not recommend, advise, predict, or suggest any "
    "trade, direction, strike, entry, exit, target or stop; do not use 'buy', 'sell', 'long', 'short', "
    "'should', 'consider', 'opportunity', 'watch for' or similar. When you mention a label, say it "
    "is a conventional reading of the pattern, not a forecast. Always give the numbers behind any "
    "stock you name."
)

# Anything that reads like an instruction to trade is rejected wholesale.
FORBIDDEN = re.compile(
    r"\b(buy|sell|go long|go short|short it|should|consider|opportunit|entry|exit|target|stop[- ]loss|"
    r"recommend|advis|bet on|accumulate|book profit)\w*",
    re.IGNORECASE,
)


def _digest(scan: dict, top: int = 8) -> str:
    """Compact text table of the scan for the prompt: summary + the most extreme rows per metric."""
    m, s, rows = scan["meta"], scan["summary"], scan["stocks"]
    lines = [f"Session: {m['as_of_label']}. Universe: {m['universe_size']} F&O stocks, {m['stocks_with_data']} with data.",
             f"Labels: {s['bullish']} Bullish setup, {s['bearish']} Bearish setup, {s['neutral']} Neutral, "
             f"{s['unclassified']} Unclassified.",
             "Label rules: price up/down + volume above its 20-day average + futures OI rising; PCR <0.7 read as "
             "bullish sentiment, >1.3 bearish, secondary only.",
             "Columns: symbol | label | price % | volume ratio | futures OI % | PCR"]

    def fmt(r):
        v = lambda x, f: "n/a" if x is None else f.format(x)  # noqa: E731
        return (f"{r['symbol']} | {r['label']} | {v(r['price_change_pct'], '{:+.2f}%')} | "
                f"{v(r['volume_ratio'], '{:.2f}x')} | {v(r['oi_change_pct'], '{:+.2f}%')} | {v(r['pcr'], '{:.2f}')}")

    def top_by(key, rev=True):
        have = [r for r in rows if r.get(key) is not None]
        return sorted(have, key=lambda r: r[key], reverse=rev)[:top]

    for title, key, rev in [("Largest price gains", "price_change_pct", True),
                            ("Largest price falls", "price_change_pct", False),
                            ("Highest volume ratio", "volume_ratio", True),
                            ("Largest futures OI increase", "oi_change_pct", True),
                            ("Largest futures OI decrease", "oi_change_pct", False),
                            ("Highest PCR", "pcr", True), ("Lowest PCR", "pcr", False)]:
        picked = top_by(key, rev)
        if picked:
            lines.append(f"\n{title}:")
            lines.extend(fmt(r) for r in picked)
    for label in ("Bullish setup", "Bearish setup"):
        picked = [r for r in rows if r["label"] == label][:top]
        if picked:
            lines.append(f"\nSome {label} rows:")
            lines.extend(fmt(r) for r in picked)
    return "\n".join(lines)


def generate_commentary(scan: dict) -> str | None:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        log.warning("commentary skipped: ANTHROPIC_API_KEY not set")
        return None
    try:
        import anthropic  # imported lazily so the rest of the build never needs it
    except ImportError:
        log.warning("commentary skipped: pip install anthropic")
        return None
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(model=MODEL, max_tokens=700, system=SYSTEM,
                                     messages=[{"role": "user", "content": _digest(scan)}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    except Exception as exc:  # noqa: BLE001
        log.error("commentary failed: %s", exc)
        return None
    hit = FORBIDDEN.search(text)
    if hit:
        log.error("commentary dropped: contains trading-instruction language (%r)", hit.group(0))
        return None
    return text
