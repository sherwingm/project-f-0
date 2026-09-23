"""Descriptive labels from price, volume, OI and PCR. Numbers in, label + reasons out.

These are the conventional readings of the patterns, not predictions:
    price up   + volume above 20d avg + futures OI rising  -> "Bullish setup"  (often read as long buildup)
    price down + volume above 20d avg + futures OI rising  -> "Bearish setup"  (often read as short buildup)
    PCR < 0.7 is generally read as bullish sentiment, PCR > 1.3 as bearish; it is secondary:
    it can only knock a primary pattern back to Neutral when it contradicts it, never create a label.
    Anything else -> "Neutral". Missing OI/PCR -> "Unclassified" (never guessed).
"""
from __future__ import annotations

PCR_LOW = 0.7
PCR_HIGH = 1.3
VOL_ABOVE = 1.0     # volume_ratio > 1.0 means above its own 20-day average

BULLISH, BEARISH, NEUTRAL, UNCLASSIFIED = "Bullish setup", "Bearish setup", "Neutral", "Unclassified"


def classify(row: dict) -> dict:
    """Return {'label', 'reasons'} for one stock row (see scanner.build for the row schema)."""
    pc, vr, oi, pcr = row.get("price_change_pct"), row.get("volume_ratio"), row.get("oi_change_pct"), row.get("pcr")
    reasons: list[str] = []

    if pc is None or vr is None:
        return {"label": UNCLASSIFIED, "reasons": ["Price or volume data missing for this session"]}
    if oi is None:
        return {"label": UNCLASSIFIED,
                "reasons": [f"Price {pc:+.2f}%", f"Volume {vr:.2f}× its 20-day average",
                            "Futures OI change not available in this build, so no setup label is assigned"]}

    price_up, price_down = pc > 0, pc < 0
    vol_above = vr > VOL_ABOVE
    oi_rising = oi > 0

    reasons.append(f"Price {'up' if price_up else 'down' if price_down else 'flat'} {pc:+.2f}%")
    reasons.append(f"Volume {vr:.2f}× its 20-day average ({'above' if vol_above else 'not above'} average)")
    reasons.append(f"Futures OI {'rising' if oi_rising else 'falling' if oi < 0 else 'unchanged'} {oi:+.2f}%")

    primary = None
    if price_up and vol_above and oi_rising:
        primary = BULLISH
        reasons.append("Price up + volume above average + OI rising: commonly read as fresh long buildup")
    elif price_down and vol_above and oi_rising:
        primary = BEARISH
        reasons.append("Price down + volume above average + OI rising: commonly read as fresh short buildup")

    if pcr is None:
        reasons.append("PCR not available (no options OI)")
        pcr_read = None
    elif pcr < PCR_LOW:
        pcr_read = "bullish"
        reasons.append(f"PCR {pcr:.2f} (< {PCR_LOW}): generally read as bullish options sentiment")
    elif pcr > PCR_HIGH:
        pcr_read = "bearish"
        reasons.append(f"PCR {pcr:.2f} (> {PCR_HIGH}): generally read as bearish options sentiment")
    else:
        pcr_read = "balanced"
        reasons.append(f"PCR {pcr:.2f} (between {PCR_LOW} and {PCR_HIGH}): balanced options sentiment")

    if primary == BULLISH and pcr_read == "bearish":
        reasons.append("Options sentiment contradicts the price/OI pattern, so the label stays Neutral")
        return {"label": NEUTRAL, "reasons": reasons}
    if primary == BEARISH and pcr_read == "bullish":
        reasons.append("Options sentiment contradicts the price/OI pattern, so the label stays Neutral")
        return {"label": NEUTRAL, "reasons": reasons}
    if primary is None:
        reasons.append("No clear buildup pattern (needs price move + above-average volume + rising OI)")
        return {"label": NEUTRAL, "reasons": reasons}
    return {"label": primary, "reasons": reasons}
