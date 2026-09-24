"""The verdict card's lean and confidence: one fixed, documented rule, computed in code at build
time. Identical whether or not any LLM exists; the optional AI summary renders below it, never in it.

Three votes:
    data    +1 Bullish setup, -1 Bearish setup, else 0
    model   +1 when p_up - p_down > 0.10, -1 when p_down - p_up > 0.10, else 0 (0 with no model),
            times MODEL_WEIGHT. The weight is 0 (env VERDICT_MODEL_WEIGHT): the walk-forward Brier score
            is no better than the base rate's, so the model is shown on the card but does not vote.
            votes.model is the counted vote; votes.model_raw is what it would have been.
    events  the sum over tier-1/2 events of the last 10 sessions of direction x weight
            (minor 0.5, significant 1, major 2); +1 when the sum >= +1, -1 when <= -1, else 0
Lean: bullish when every non-zero counted vote is positive (and at least one is), bearish when every
non-zero counted vote is negative, mixed otherwise (including all-zero).
Confidence:
    high    every counted vote non-zero and the same sign; with the model counted (weight > 0) it must
            also be confident (max(p_up, p_down) >= 0.40 and |p_up - p_down| >= 0.15). With weight 0
            that is data and events agreeing.
    low     two counted votes with opposite signs, or no non-zero counted vote
    medium  everything else
"""
from __future__ import annotations

import os

MODEL_WEIGHT = float(os.getenv("VERDICT_MODEL_WEIGHT", "0"))
MODEL_VOTE_MARGIN = 0.10
MODEL_CONFIDENT_P = 0.40
MODEL_CONFIDENT_MARGIN = 0.15
EVENT_WEIGHTS = {"minor": 0.5, "significant": 1.0, "major": 2.0}


def data_vote(label: str | None) -> int:
    return 1 if label == "Bullish setup" else -1 if label == "Bearish setup" else 0


def model_vote(model: dict | None) -> int:
    if not model:
        return 0
    edge = (model.get("p_up") or 0) - (model.get("p_down") or 0)
    return 1 if edge > MODEL_VOTE_MARGIN else -1 if edge < -MODEL_VOTE_MARGIN else 0


def model_confident(model: dict | None) -> bool:
    if not model:
        return False
    up, down = model.get("p_up") or 0, model.get("p_down") or 0
    return max(up, down) >= MODEL_CONFIDENT_P and abs(up - down) >= MODEL_CONFIDENT_MARGIN


def events_vote(last_10: list[dict] | None) -> tuple[int, float]:
    total = 0.0
    for e in last_10 or []:
        if e.get("tier", 3) > 2:
            continue
        total += (e.get("direction") or 0) * EVENT_WEIGHTS.get(e.get("bucket"), 0.0)
    return (1 if total >= 1 else -1 if total <= -1 else 0), round(total, 2)


def verdict(stock: dict) -> dict:
    """The card block for one scan stock (needs stock['label'], stock.get('model'), stock['events'])."""
    dv = data_vote(stock.get("label"))
    raw_mv = model_vote(stock.get("model"))
    mv = int(raw_mv * MODEL_WEIGHT > 0) - int(raw_mv * MODEL_WEIGHT < 0)
    ev, escore = events_vote((stock.get("events") or {}).get("last_10"))
    votes = [v for v in (dv, mv, ev) if v]
    if votes and all(v > 0 for v in votes):
        lean = "bullish"
    elif votes and all(v < 0 for v in votes):
        lean = "bearish"
    else:
        lean = "mixed"
    counted = (dv, mv, ev) if MODEL_WEIGHT else (dv, ev)
    if not votes or (max(votes) > 0 and min(votes) < 0):
        confidence = "low"
    elif all(counted) and (not MODEL_WEIGHT or model_confident(stock.get("model"))):
        confidence = "high"
    else:
        confidence = "medium"
    rule = ("data, model and events each vote; high needs all three agreeing and a confident model; "
            "low means two disagree or none votes") if MODEL_WEIGHT else            ("data and events vote; the model is shown but its weight is 0 (its out-of-sample Brier does not "
            "beat the base rate); high needs data and events agreeing; low means they disagree or neither votes")
    return {"lean": lean, "confidence": confidence,
            "votes": {"data": dv, "model": mv, "events": ev, "model_raw": raw_mv, "model_weight": MODEL_WEIGHT},
            "events_score": escore, "rule": rule}
