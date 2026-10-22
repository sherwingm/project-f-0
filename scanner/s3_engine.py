"""S3 step 3: intraday multi-leg backtest engine for index options (DECISIONS.md "S3 · index options").

One trade a day: legs placed at an entry minute around the at-the-money strike, marked every minute on the last traded
close, closed at a combined stop, a target or a time exit. Fills: the minute's last traded close, worse by slippage
(0.5 % of premium; 1 % for legs >= 2 strikes from the money and for fills 09:15-09:30 or 15:00-15:30). Charges per
order from `server/charges.py`. Every long leg is squared off intraday, so no exercise STT.

    from scanner.s3_engine import Leg, Spec, simulate, run_day
    fly = Spec("iron_fly", [Leg("SELL", "CE", 0), Leg("SELL", "PE", 0), Leg("BUY", "CE", 4), Leg("BUY", "PE", -4)],
               entry=(9, 20), exit=(14, 45), stop=0.25)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time

import pandas as pd

from index_data import load as L
from index_data.instruments import STRIKE_STEP
from server import charges

SLIP, SLIP_WIDE = 0.005, 0.01
WIDE_STEPS = 2
ENTRY_STALE, MARK_STALE = 3, 30          # minutes: an entry price must be fresh; a mark may carry forward


@dataclass(frozen=True)
class Leg:
    side: str            # BUY or SELL
    opt: str             # CE or PE
    offset: int          # strikes from the money, + above, − below


@dataclass(frozen=True)
class Spec:
    name: str
    legs: list = field(default_factory=list)
    entry: tuple = (9, 20)
    exit: tuple = (14, 45)
    stop: float | None = None        # credit: close when the cost to close >= credit x (1 + stop); debit: value <= debit x (1 − stop)
    target: float | None = None      # credit: cost to close <= credit x (1 − target); debit: value >= debit x (1 + target)
    lots: int = 1
    cost_mult: float = 1.0           # 2.0 = the gate's stress at twice the costs (charges and slippage)


def _slip(offset: int, t: time, cost_mult: float) -> float:
    wide = abs(offset) >= WIDE_STEPS or t < time(9, 30) or t >= time(15, 0)
    return (SLIP_WIDE if wide else SLIP) * cost_mult


def _fill(px: float, side: str, offset: int, t: time, cost_mult: float) -> float:
    s = _slip(offset, t, cost_mult)
    return px * (1 + s) if side == "BUY" else px * (1 - s)


def _rev(side: str) -> str:
    return "SELL" if side == "BUY" else "BUY"


def simulate(chain: pd.DataFrame, spot_entry: float, day: date, spec: Spec, lot: int, underlying: str = "NIFTY") -> dict:
    """One trade on one day's merged chain (index_data.load.options_day). Returns a trade row, or a row with `skip`."""
    step = STRIKE_STEP[underlying]
    atm = round(spot_entry / step) * step
    t_in, t_out = L.at(day, *spec.entry), L.at(day, *spec.exit)
    base = {"day": day, "pod": spec.name, "spot": spot_entry, "atm": atm}
    legs = []
    for lg in spec.legs:
        k = atm + lg.offset * step
        px = L.price_at(chain, k, lg.opt, t_in, stale=ENTRY_STALE)
        if px is None or px <= 0:
            return {**base, "skip": f"no price {k:.0f} {lg.opt} at {t_in:%H:%M}"}
        legs.append((lg, k, px))
    qty = lot * spec.lots
    sign = {"SELL": 1, "BUY": -1}
    fills_in = [_fill(px, lg.side, lg.offset, t_in.time(), spec.cost_mult) for lg, _, px in legs]
    net = sum(sign[lg.side] * f for (lg, _, _), f in zip(legs, fills_in))       # > 0: credit, < 0: debit
    credit = net > 0
    prem = abs(net)

    # minute marks: last traded close per leg, carried forward up to MARK_STALE minutes
    window = chain[(chain["timestamp"] > t_in) & (chain["timestamp"] <= t_out)]
    minutes = sorted(window["timestamp"].unique())
    last = [px for _, _, px in legs]
    seen = [t_in] * len(legs)
    per_leg = {(k, lg.opt): g.set_index("timestamp")["close"] for lg, k, _ in legs
               for g in [chain[(chain["strike"] == k) & (chain["option_type"] == lg.opt)]]}
    exit_t, reason, worst = t_out, "time", 0.0
    for m in minutes:
        for i, (lg, k, _) in enumerate(legs):
            s = per_leg[(k, lg.opt)]
            if m in s.index:
                last[i], seen[i] = float(s[m]), m
        if any((m - x).total_seconds() > MARK_STALE * 60 for x in seen):
            continue
        val = sum(sign[lg.side] * p for (lg, _, _), p in zip(legs, last))       # value to close, same sign as net
        pnl_pt = net - val                                                       # per unit, before exit costs (credit or debit)
        worst = min(worst, pnl_pt / prem)
        if spec.stop is not None and pnl_pt <= -spec.stop * prem:
            exit_t, reason = m, "stop"
            break
        if spec.target is not None and pnl_pt >= spec.target * prem:
            exit_t, reason = m, "target"
            break
    if reason == "time":   # the exit minute's own marks (or the last fresh ones before it)
        for i, (lg, k, _) in enumerate(legs):
            p = L.price_at(chain, k, lg.opt, t_out, stale=MARK_STALE)
            if p is not None:
                last[i] = p
    fills_out = [_fill(p, _rev(lg.side), lg.offset, pd.Timestamp(exit_t).time(), spec.cost_mult)
                 for (lg, _, _), p in zip(legs, last)]
    gross_pt = sum(sign[lg.side] * (fi - fo) for (lg, _, _), fi, fo in zip(legs, fills_in, fills_out))
    fees = sum(charges.leg(lg.opt, lg.side, qty, fi)["total"] + charges.leg(lg.opt, _rev(lg.side), qty, fo)["total"]
               for (lg, _, _), fi, fo in zip(legs, fills_in, fills_out)) * spec.cost_mult
    pnl = gross_pt * qty - fees
    widths = [abs(lg.offset) for lg in spec.legs if lg.side == "BUY"]
    defined = credit and any(lg.side == "BUY" for lg in spec.legs)
    margin = ((max(widths) * step - prem) * qty if defined and widths else
              0.12 * spot_entry * qty * sum(1 for lg in spec.legs if lg.side == "SELL") / 2 if credit else prem * qty)
    return {**base, "skip": "", "kind": "credit" if credit else "debit", "lot": lot, "qty": qty,
            "premium": round(prem, 2), "premium_rs": round(prem * qty, 2), "exit_at": pd.Timestamp(exit_t).strftime("%H:%M"),
            "reason": reason, "gross_rs": round(gross_pt * qty, 2), "fees_rs": round(fees, 2), "net_rs": round(pnl, 2),
            "net_pct_premium": round(pnl / (prem * qty) * 100, 2), "margin_rs": round(margin, 2),
            "net_pct_margin": round(pnl / margin * 100, 3) if margin > 0 else None,
            "worst_pct": round(worst * 100, 1),
            "legs": ";".join(f"{lg.side[0]}{k:.0f}{lg.opt}@{fi:.2f}>{fo:.2f}" for (lg, k, _), fi, fo in zip(legs, fills_in, fills_out))}


def run_day(spec: Spec, day: date, expiry: date, underlying: str = "NIFTY", index: str = "NIFTY50") -> dict:
    """Load the day's chain and spot from the index store and simulate."""
    sp = L.spot_1m(day, day, index)
    sp = sp[sp["timestamp"] <= L.at(day, *spec.entry)]
    if sp.empty or (L.at(day, *spec.entry) - sp["timestamp"].iloc[-1]).total_seconds() > 180:
        return {"day": day, "pod": spec.name, "skip": "no spot at entry"}
    return simulate(L.options_day(underlying, expiry, day), float(sp["close"].iloc[-1]), day, spec, L.lot_on(day, underlying),
                    underlying)
