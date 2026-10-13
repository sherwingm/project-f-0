"""The option's path, pure helpers (no Excel dependency): used by the trade sheet and the forward test."""
from __future__ import annotations


def pct(x: float | None, ref: float | None) -> float | None:
    return None if x is None or not ref else round((x / ref - 1) * 100, 2)


def span(points: list[tuple[str, float]], entry: float) -> dict:
    """Upside-only peak and downside-only dip of (date, close) points, % of the entry price. A peak that never got
    above entry is 0 with no date; a dip that never got below entry is 0 with no date."""
    if not points:
        return {"peak": None, "peak_date": None, "dip": None, "dip_date": None, "high": None}
    dh, hi = max(points, key=lambda p: p[1])
    dl, lo = min(points, key=lambda p: p[1])
    up, down = pct(hi, entry), pct(lo, entry)
    return {"peak": max(up, 0.0), "peak_date": dh if up > 0 else None,
            "dip": min(down, 0.0), "dip_date": dl if down < 0 else None, "high": hi}
