"""Risk controls for the paper account, all server-side, checked on every entry at preview, at place and
when a queued order comes due. Exits are never blocked here.

    RISK_PER_TRADE_PCT      0.5  max loss per trade <= 0.5% of capital (Rs 2,500 on Rs 5 lakh). Long option:
                                 premium x qty. Futures and short options: |entry - stop| x qty, stop required.
                                 Lots are capped to fit; the review shows the cap.
    DAILY_LOSS_HALT_PCT     1.0  day P&L (realised + unrealised) <= -1% of capital: no new entries until the
                                 next session (latched for the day even if P&L recovers)
    WEEKLY_LOSS_HALT_PCT    3.0  the same for the week (Monday to Friday)
    DRAWDOWN_REVIEW_PCT     10   drawdown from peak equity >= 10%: "review labels and sizing" banner, not a block
    MARGIN_CAP_PCT          30   margin of open positions + this order <= 30% of capital. Margin: Kotak's
                                 margin_required when a Kotak trade session already exists, else
                                 MARGIN_ESTIMATE_PCT (18) of notional for futures / short options, premium for long options
    MAX_NEW_POSITIONS_PER_DAY    3
    MAX_NEW_POSITIONS_PER_MONTH  20
    BLOCK_EXPIRY_DAY_ENTRIES     true   no new position on its expiry day (the account never holds to expiry)
"""
from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta

from server.config import settings

log = logging.getLogger(__name__)


class RiskGate:
    def __init__(self, s=settings, margin_fn=None):
        self.s = s
        self.margin_fn = margin_fn            # (req, resolved_like, price) -> float | None, Kotak when available

    # ------------------------------------------------------------ limits
    def per_trade_cap(self, capital: float) -> float:
        return round(self.s.risk_per_trade_pct / 100 * capital, 2)

    def state(self, ledger, now: datetime) -> dict:
        """Kill-switch and banner state for the summary; latches a halt once it is hit."""
        cap = ledger.state["capital"]
        halts = ledger.state.setdefault("halts", {})
        today, monday = now.date().isoformat(), (now.date() - timedelta(days=now.weekday())).isoformat()
        day_pnl, week_pnl = ledger.day_pnl(now), ledger.week_pnl(now)
        day_limit = -self.s.daily_loss_halt_pct / 100 * cap
        week_limit = -self.s.weekly_loss_halt_pct / 100 * cap
        if day_pnl <= day_limit and halts.get("day") != today:
            halts["day"] = today
            log.warning("paper kill switch: day P&L Rs %.2f <= Rs %.2f; no new entries until the next session", day_pnl, day_limit)
        if week_pnl <= week_limit and halts.get("week") != monday:
            halts["week"] = monday
            log.warning("paper kill switch: week P&L Rs %.2f <= Rs %.2f; no new entries until next week", week_pnl, week_limit)
        day_halt, week_halt = halts.get("day") == today, halts.get("week") == monday
        eq = ledger.equity()
        peak = max(ledger.state.get("peak_equity", cap), eq)
        dd = (peak - eq) / peak * 100 if peak else 0.0
        reason = None
        if week_halt:
            reason = f"weekly loss halt: week P&L reached {self.s.weekly_loss_halt_pct:g}% of capital; no new entries until next week"
        elif day_halt:
            reason = f"daily loss halt: day P&L reached {self.s.daily_loss_halt_pct:g}% of capital; no new entries until the next session"
        month_start = now.date().replace(day=1)
        return {"kill_switch": {"active": day_halt or week_halt, "reason": reason, "day_halt": day_halt, "week_halt": week_halt,
                                "day_limit": round(day_limit, 2), "week_limit": round(week_limit, 2)},
                "drawdown_review": dd >= self.s.drawdown_review_pct,
                "drawdown_review_message": "Drawdown from peak is {:.1f}%: review labels and sizing.".format(dd)
                if dd >= self.s.drawdown_review_pct else None,
                "limits": {"risk_per_trade": self.per_trade_cap(cap), "risk_per_trade_pct": self.s.risk_per_trade_pct,
                           "margin_cap": round(self.s.margin_cap_pct / 100 * cap, 2), "margin_cap_pct": self.s.margin_cap_pct,
                           "max_new_per_day": self.s.max_new_positions_per_day, "max_new_per_month": self.s.max_new_positions_per_month,
                           "daily_loss_halt_pct": self.s.daily_loss_halt_pct, "weekly_loss_halt_pct": self.s.weekly_loss_halt_pct,
                           "drawdown_review_pct": self.s.drawdown_review_pct},
                "new_positions_today": ledger.new_positions(now.date()),
                "new_positions_month": ledger.new_positions(month_start)}

    # ------------------------------------------------------------ the gate
    def check(self, ledger, review: dict, req, contract: dict, stop: float | None, now: datetime) -> None:
        """Adds readable reasons to review["blocked"] and the numbers behind them to review["risk"]."""
        st = self.state(ledger, now)
        cap = ledger.state["capital"]
        blocked = review["blocked"]
        before = len(blocked)
        risk = {"cap": self.per_trade_cap(cap), "per_lot_max_loss": None, "max_loss": None, "used_pct": None,
                "max_lots": None, "margin": review.get("margin"), "margin_source": "estimate",
                "open_margin": ledger.open_margin(), "margin_cap": st["limits"]["margin_cap"],
                "kill_switch": st["kill_switch"], "day_pnl": ledger.day_pnl(now), "week_pnl": ledger.week_pnl(now),
                "new_positions_today": st["new_positions_today"], "new_positions_month": st["new_positions_month"],
                "drawdown_review": st["drawdown_review"]}
        review["risk"] = risk

        if st["kill_switch"]["active"]:
            blocked.append(st["kill_switch"]["reason"])
        if self.s.block_expiry_day_entries and review.get("sessions_to_expiry") == 0:
            blocked.append("no new positions on expiry day: stock derivatives are physically settled and the paper "
                           "account never holds to expiry")
        if st["new_positions_today"] >= self.s.max_new_positions_per_day:
            blocked.append(f"{st['new_positions_today']} new positions today already (limit {self.s.max_new_positions_per_day})")
        if st["new_positions_month"] >= self.s.max_new_positions_per_month:
            blocked.append(f"{st['new_positions_month']} new positions this month already (limit {self.s.max_new_positions_per_month})")

        f = review.get("fill")
        lot = int(contract["lot_size"])
        opt = contract["instrument"] in ("CE", "PE")
        if opt and req.side == "SELL" and not stop:
            blocked.append("short options need a stop price: without one the loss is not bounded")
        if f:
            px = f["price"]
            if opt and req.side == "BUY":
                per_lot = px * lot
            elif stop:
                per_lot = abs(px - stop) * lot
            else:
                per_lot = None
            if per_lot:
                max_lots = int(math.floor(risk["cap"] / per_lot + 1e-9))
                ml = per_lot * req.lots
                risk.update({"per_lot_max_loss": round(per_lot, 2), "max_loss": round(ml, 2),
                             "used_pct": round(ml / risk["cap"] * 100, 1), "max_lots": max_lots})
                if max_lots < 1:
                    blocked.append(f"one lot risks Rs {per_lot:,.2f}, above the per-trade cap of Rs {risk['cap']:,.2f} "
                                   f"({self.s.risk_per_trade_pct:g}% of capital)")
                elif req.lots > max_lots:
                    blocked.append(f"the per-trade risk cap allows at most {max_lots} lot{'s' if max_lots != 1 else ''} "
                                   f"(Rs {per_lot:,.2f} per lot against Rs {risk['cap']:,.2f})")
            margin = review.get("margin")
            if self.margin_fn is not None:
                try:
                    m = self.margin_fn(req, contract, px)
                    if m is not None:
                        margin, risk["margin_source"] = float(m), "kotak"
                except Exception as exc:  # noqa: BLE001 - fall back to the estimate
                    log.warning("Kotak margin_required failed, using the estimate: %s", exc)
            risk["margin"] = margin
            if margin is not None:
                total = ledger.open_margin() + margin
                risk["margin_after"] = round(total, 2)
                if total > risk["margin_cap"]:
                    blocked.append(f"margin Rs {total:,.2f} with this order would exceed {self.s.margin_cap_pct:g}% of capital "
                                   f"(Rs {risk['margin_cap']:,.2f})")
        for msg in blocked[before:]:
            log.info("paper risk block on %s: %s", contract.get("tradingsymbol"), msg)


def kotak_margin_fn(session):
    """Kotak's margin_required, but only through a trade session that already exists: the paper engine
    never logs in to Kotak's trading side by itself."""
    from server.kotak import KotakBroker

    broker = KotakBroker(session)

    def fn(req, contract, price):
        if not getattr(session, "_trade_ready", False):
            return None
        resolved = broker.resolve(req, contract["lot_size"])
        return broker.margin(req, resolved, price)
    return fn
