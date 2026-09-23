"""Transaction charges for NSE stock futures and options, one table.

Rates effective CHARGES_EFFECTIVE (2026-04-01). Every rate is a module constant; set CHARGES_JSON in
the environment to override any of them without a code change, e.g.
    CHARGES_JSON='{"OPT_NSE_PER_LAKH": 35.03, "FUT_STT_SELL_PCT": 0.05}'
Unknown names are rejected at start-up rather than silently ignored.

| Component                         | Futures                   | Options                        |
|-----------------------------------|---------------------------|--------------------------------|
| Brokerage per order               | min(0.03% x value, Rs 20) | Rs 20                          |
| STT (sell side only)              | 0.05% x contract value    | 0.15% x premium                |
| NSE transaction charge (each side)| Rs 1.83 per lakh of value | Rs 35.53 per lakh of premium   |
| SEBI fee (each side)              | Rs 10 per crore           | Rs 10 per crore of premium     |
| Stamp duty (buy side only)        | 0.002% x value            | 0.003% x premium               |
| GST                               | 18% x (brokerage + NSE charge + SEBI)                      |
| STT on exercise (long ITM option held to expiry) | -          | 0.15% x intrinsic value        |

"value" is quantity x price: the contract value for futures, the premium for options. Every
component is rounded to the paisa and `total` is the sum of the rounded components, so a
contract-note style breakdown always adds up.
"""
from __future__ import annotations

import json

from server.config import settings

CHARGES_EFFECTIVE = "2026-04-01"

FUT_BROKERAGE_PCT = 0.03        # % of contract value, capped at BROKERAGE_CAP
BROKERAGE_CAP = 20.0            # Rs per order
OPT_BROKERAGE = 20.0            # Rs per order, flat
FUT_STT_SELL_PCT = 0.05         # % of contract value, sell side only
OPT_STT_SELL_PCT = 0.15         # % of premium, sell side only
OPT_STT_EXERCISE_PCT = 0.15     # % of intrinsic value when a long ITM option is exercised at expiry
FUT_NSE_PER_LAKH = 1.83         # Rs per Rs 1,00,000 of contract value, each side
OPT_NSE_PER_LAKH = 35.53        # Rs per Rs 1,00,000 of premium, each side
SEBI_PER_CRORE = 10.0           # Rs per Rs 1,00,00,000, each side
FUT_STAMP_BUY_PCT = 0.002       # % of contract value, buy side only
OPT_STAMP_BUY_PCT = 0.003       # % of premium, buy side only
GST_PCT = 18.0                  # % of (brokerage + NSE transaction charge + SEBI fee)

RATE_NAMES = ("FUT_BROKERAGE_PCT", "BROKERAGE_CAP", "OPT_BROKERAGE", "FUT_STT_SELL_PCT", "OPT_STT_SELL_PCT",
              "OPT_STT_EXERCISE_PCT", "FUT_NSE_PER_LAKH", "OPT_NSE_PER_LAKH", "SEBI_PER_CRORE",
              "FUT_STAMP_BUY_PCT", "OPT_STAMP_BUY_PCT", "GST_PCT")
COMPONENTS = ("brokerage", "stt", "exchange", "sebi", "stamp", "gst")


def configure(overrides: str | dict | None) -> dict:
    """Apply CHARGES_JSON-style overrides (JSON text or a dict) to the module rates; returns rates()."""
    if not overrides:
        return rates()
    data = json.loads(overrides) if isinstance(overrides, str) else dict(overrides)
    unknown = sorted(set(data) - set(RATE_NAMES))
    if unknown:
        raise ValueError(f"CHARGES_JSON: unknown rate name(s) {unknown}; valid: {list(RATE_NAMES)}")
    for name, value in data.items():
        globals()[name] = float(value)
    return rates()


def rates() -> dict:
    return {"effective": CHARGES_EFFECTIVE, **{n: globals()[n] for n in RATE_NAMES}}


def is_future(instrument: str) -> bool:
    return str(instrument).upper() in ("FUT", "FUTSTK", "STF")


def leg(instrument: str, side: str, qty: int, px: float) -> dict:
    """Charges on one order: `instrument` FUT or CE/PE, `side` BUY or SELL, `qty` units, `px` per unit."""
    side = str(side).upper()
    if side not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")
    if qty < 0 or px < 0:
        raise ValueError("quantity and price must not be negative")
    fut = is_future(instrument)
    value = qty * px
    brokerage = min(FUT_BROKERAGE_PCT / 100 * value, BROKERAGE_CAP) if fut else OPT_BROKERAGE
    stt = ((FUT_STT_SELL_PCT if fut else OPT_STT_SELL_PCT) / 100 * value) if side == "SELL" else 0.0
    exchange = (FUT_NSE_PER_LAKH if fut else OPT_NSE_PER_LAKH) * value / 1e5
    sebi = SEBI_PER_CRORE * value / 1e7
    stamp = ((FUT_STAMP_BUY_PCT if fut else OPT_STAMP_BUY_PCT) / 100 * value) if side == "BUY" else 0.0
    gst = GST_PCT / 100 * (brokerage + exchange + sebi)
    parts = {k: round(v, 2) for k, v in zip(COMPONENTS, (brokerage, stt, exchange, sebi, stamp, gst))}
    return {"instrument": "FUT" if fut else str(instrument).upper(), "side": side, "qty": qty, "price": px,
            "value": round(value, 2), **parts, "total": round(sum(parts.values()), 2)}


def round_trip(instrument: str, side_entry: str, qty: int, entry_px: float, exit_px: float) -> dict:
    """Entry leg on `side_entry`, exit leg on the opposite side, and the summed components."""
    exit_side = "SELL" if str(side_entry).upper() == "BUY" else "BUY"
    entry = leg(instrument, side_entry, qty, entry_px)
    exit_ = leg(instrument, exit_side, qty, exit_px)
    summed = {k: round(entry[k] + exit_[k], 2) for k in COMPONENTS}
    return {"entry": entry, "exit": exit_, **summed, "total": round(entry["total"] + exit_["total"], 2)}


def exercise(qty: int, intrinsic: float) -> dict:
    """STT when a long ITM option is held to expiry and exercised: 0.15% of the intrinsic value."""
    stt = round(OPT_STT_EXERCISE_PCT / 100 * qty * max(0.0, intrinsic), 2)
    return {"value": round(qty * max(0.0, intrinsic), 2), "stt": stt, "total": stt}


def held_to_expiry(instrument: str, qty: int, entry_px: float, intrinsic: float) -> dict:
    """Long option bought at `entry_px` and left to expire: buy-leg charges plus exercise STT if ITM."""
    entry = leg(instrument, "BUY", qty, entry_px)
    ex = exercise(qty, intrinsic)
    return {"entry": entry, "exercise": ex, "total": round(entry["total"] + ex["total"], 2)}


configure(settings.charges_json)
