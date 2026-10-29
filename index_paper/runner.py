"""One tick of the index paper system: observe open positions -> exits -> after-exit follow-up -> new entries.

    events = tick(ledger, pods, ctx, quote_fn, now)

quote_fn(symbols: set[str]) -> {symbol: quote} with the S1 quote shape (depth.bid / depth.ask, last_price, timestamp,
underlying, source). Not wired into the live server: connecting a broker quote source and a scheduler is a separate
deploy step that needs the user's go-ahead.
"""
from __future__ import annotations

from datetime import datetime

from .ledger import IndexPaperLedger, IndexPaperRejected
from .pods import Pod


def tick(ledger: IndexPaperLedger, pods: dict[str, Pod], ctx: dict, quote_fn, now: datetime) -> list[dict]:
    events: list[dict] = []
    need = ledger.symbols_needed(now)
    quotes = quote_fn(need) if need else {}
    ledger.observe(quotes, now)
    for pos in list(ledger.state["open"]):
        pod = pods.get(pos["pod"])
        reason = (pos.get("exit_pending") or {}).get("reason") or (pod.exit_due(pos, ctx, now) if pod else None)
        if reason:
            done = ledger.close(pos["id"], quotes, now, reason)
            events.append({"event": "exit" if done else "exit_pending", "id": pos["id"], "reason": reason})
    ledger.observe_after(quotes, now)
    held_pods = {p["pod"] for p in ledger.state["open"]}
    for name, pod in pods.items():
        if not pod.enabled or name in held_pods:
            continue
        why = pod.signal(ctx, now)
        if not why:
            continue
        chain_q = quote_fn(set(ctx.get("chain", {})))
        legs = pod.legs(ctx, chain_q, now)
        try:
            pos = ledger.open(name, legs, chain_q, now, reason=why, exit_plan={"rule": pod.page})
            events.append({"event": "entry", "id": pos["id"], "reason": why})
        except IndexPaperRejected as exc:
            events.append({"event": "rejected", "pod": name, "reason": str(exc)})
    return events
