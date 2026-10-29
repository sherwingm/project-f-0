"""The registered index pods. Every pod starts OFF (enabled=False). Only the user turns one on, by editing ENABLED
below in its own commit after the pod has passed its research gates; a backtest result never changes it.

A pod gives the runner:
    signal(ctx, now)        -> a reason string when it wants to enter now, else None
    legs(ctx, quotes, now)  -> the legs to buy, from live quotes (strike choice uses bid / ask, never the future)
    exit_due(pos, ctx, now) -> an exit reason, else None
ctx is what the caller knows at `now`: {"vix_closes": [(date, close), ...] up to the last finished session,
"sessions": [date, ...] the trading calendar, "chain": {symbol: {"strike", "opt", "expiry"}}, "lot": int}.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Callable

from server.peak import IST

ENABLED: set[str] = set()          # pods the user has turned on; empty: no index pod trades on paper


@dataclass
class Pod:
    name: str
    underlying: str
    title: str
    page: str
    status: str
    signal: Callable
    legs: Callable
    exit_due: Callable
    meta: dict = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return self.name in ENABLED


# ---- L1 (strategies/S3_L1_vix_rising_long_straddle.md), live form of the daily rule
L1_VIX, L1_LOOKBACK, L1_HOLD, L1_MIN_DTE = 22.0, 5, 5, 10
L1_ENTRY_AT = time(15, 20)           # live stand-in for "the close of d + 1"; the page's backtest uses ClsPric


def l1_signal(ctx: dict, now: datetime) -> str | None:
    """VIX above 22 and rising, measured on the last finished session's close (d), traded on the next session."""
    now = now.astimezone(IST)
    v = [c for d, c in ctx.get("vix_closes", []) if d < now.date()]
    if len(v) <= L1_LOOKBACK or now.time() < L1_ENTRY_AT:
        return None
    last, ref = v[-1], v[-1 - L1_LOOKBACK]
    return f"VIX {last:.2f} > {L1_VIX:g} and above {ref:.2f} five sessions earlier" if last > L1_VIX and last > ref else None


def _mid(q: dict | None) -> float | None:
    d = (q or {}).get("depth") or {}
    b, a = (d.get("bid") or [(None,)])[0][0], (d.get("ask") or [(None,)])[0][0]
    return (a + b) / 2 if a and b else None


def l1_legs(ctx: dict, quotes: dict, now: datetime) -> list[dict]:
    """ATM straddle on the nearest expiry at least 10 days out: the strike with the smallest |CE mid - PE mid|."""
    today = now.astimezone(IST).date()
    exps = sorted({c["expiry"] for c in ctx.get("chain", {}).values() if c["expiry"] >= today + timedelta(days=L1_MIN_DTE)})
    if not exps:
        return []
    e = exps[0]
    by_k: dict[float, dict] = {}
    for sym, c in ctx["chain"].items():
        if c["expiry"] == e:
            by_k.setdefault(c["strike"], {})[c["opt"]] = sym
    best = None
    for k, s in by_k.items():
        if "CE" in s and "PE" in s:
            mc, mp = _mid(quotes.get(s["CE"])), _mid(quotes.get(s["PE"]))
            if mc and mp and (best is None or abs(mc - mp) < best[0]):
                best = (abs(mc - mp), k, s)
    if best is None:
        return []
    _, k, s = best
    lot = ctx.get("lot") or 0
    return [{"symbol": s[o], "underlying": "NIFTY", "expiry": e.isoformat(), "strike": k, "opt": o, "qty": lot}
            for o in ("CE", "PE")]


def l1_exit_due(pos: dict, ctx: dict, now: datetime) -> str | None:
    now = now.astimezone(IST)
    opened = datetime.fromisoformat(pos["opened_at"]).astimezone(IST).date()
    after = [d for d in ctx.get("sessions", []) if d > opened]
    if len(after) < L1_HOLD:
        return None
    target, why = after[L1_HOLD - 1], f"time: {L1_HOLD} sessions"
    exp = min(date.fromisoformat(lg["expiry"]) for lg in pos["legs"])
    before_exp = [d for d in after if d < exp]
    if before_exp and before_exp[-1] < target:
        target, why = before_exp[-1], "time: last session before expiry"
    if now.date() > target or (now.date() == target and now.time() >= L1_ENTRY_AT):
        return why
    return None


PODS: dict[str, Pod] = {
    "L1": Pod("L1", "NIFTY", "Long ATM straddle when India VIX > 22 and rising, ~5 sessions",
              "strategies/S3_L1_vix_rising_long_straddle.md",
              "research: pre-registered 2026-10-29, testing on 2018-2021; not passed, not enabled",
              l1_signal, l1_legs, l1_exit_due),
}
