"""Spec 12 step 8: the fixed verdict rule and the card's presence in the page."""
from pathlib import Path

import pytest

from scanner import verdict_rules
from scanner.verdict_rules import data_vote, events_vote, model_confident, model_vote, verdict

TEMPLATE = (Path(__file__).resolve().parent.parent / "templates" / "index.html").read_text(encoding="utf-8")


def ev(direction, bucket="significant", tier=1):
    return {"direction": direction, "bucket": bucket, "tier": tier}


def stock(label="Bullish setup", model=None, last_10=()):
    return {"label": label, "model": model, "events": {"last_10": list(last_10)}}


def test_individual_votes():
    assert data_vote("Bullish setup") == 1 and data_vote("Bearish setup") == -1
    assert data_vote("Neutral") == 0 and data_vote(None) == 0
    assert model_vote({"p_up": 0.45, "p_down": 0.20}) == 1
    assert model_vote({"p_up": 0.30, "p_down": 0.42}) == -1
    assert model_vote({"p_up": 0.35, "p_down": 0.30}) == 0 and model_vote(None) == 0
    assert model_confident({"p_up": 0.45, "p_down": 0.20})
    assert not model_confident({"p_up": 0.38, "p_down": 0.20})       # p below 0.40
    assert not model_confident({"p_up": 0.45, "p_down": 0.35})       # margin below 0.15
    assert events_vote([ev(1), ev(1, "minor")]) == (1, 1.5)          # 1 + 0.5
    assert events_vote([ev(-1, "major")]) == (-1, -2.0)
    assert events_vote([ev(1, "minor")]) == (0, 0.5)                 # below the +-1 bar
    assert events_vote([ev(1, tier=3)]) == (0, 0.0)                  # tier 3 never votes
    assert events_vote(None) == (0, 0.0)


@pytest.fixture
def model_counts(monkeypatch):
    """The rule as it reads when the model is given a vote (VERDICT_MODEL_WEIGHT=1)."""
    monkeypatch.setattr(verdict_rules, "MODEL_WEIGHT", 1.0)


def test_model_does_not_vote_by_default_but_its_raw_vote_is_kept():
    assert verdict_rules.MODEL_WEIGHT == 0
    v = verdict(stock("Neutral", model={"p_up": 0.55, "p_down": 0.10}, last_10=[]))
    assert v["votes"]["model"] == 0 and v["votes"]["model_raw"] == 1 and v["votes"]["model_weight"] == 0
    assert v["lean"] == "mixed" and v["confidence"] == "low"                   # nothing counted votes
    against = verdict(stock("Bullish setup", model={"p_up": 0.1, "p_down": 0.5}, last_10=[ev(1)]))
    assert against["lean"] == "bullish" and against["confidence"] == "high"   # data + events agree; model ignored
    assert "weight is 0" in against["rule"]


def test_high_needs_all_three_agreeing_and_a_confident_model(model_counts):
    v = verdict(stock(model={"p_up": 0.45, "p_down": 0.20}, last_10=[ev(1)]))
    assert v["lean"] == "bullish" and v["confidence"] == "high"
    # same votes, hesitant model: medium
    v2 = verdict(stock(model={"p_up": 0.36, "p_down": 0.22}, last_10=[ev(1)]))
    assert v2["lean"] == "bullish" and v2["confidence"] == "medium"


def test_two_disagreeing_votes_mean_low_and_mixed(model_counts):
    v = verdict(stock("Bullish setup", model={"p_up": 0.2, "p_down": 0.45}, last_10=[]))
    assert v["lean"] == "mixed" and v["confidence"] == "low"
    bear = verdict(stock("Bearish setup", model={"p_up": 0.1, "p_down": 0.5}, last_10=[ev(-1)]))
    assert bear["lean"] == "bearish" and bear["confidence"] == "high"


def test_partial_votes_are_medium_not_high(model_counts):
    v = verdict(stock("Neutral", model={"p_up": 0.55, "p_down": 0.10}, last_10=[]))
    assert v["lean"] == "bullish" and v["confidence"] == "medium"    # one vote only
    none = verdict(stock("Neutral", model=None, last_10=[]))
    assert none["lean"] == "mixed" and none["confidence"] == "low"
    assert {k: none["votes"][k] for k in ("data", "model", "events")} == {"data": 0, "model": 0, "events": 0}


def test_verdict_is_model_free_safe(model_counts):
    v = verdict(stock("Bullish setup", model=None, last_10=[ev(1), ev(1)]))
    assert v["lean"] == "bullish" and v["confidence"] == "medium"    # two votes, no model: never high


@pytest.mark.parametrize("piece", [
    "Verdict (computed by fixed rules, not advice)", "verdictCard(s)", "p(up)", "out-of-sample Brier",
    "vs base rate", "vote weight",
    "no analyst views (tier-3 news)", "pattern over ", "event_patterns", "votes — data"])
def test_card_is_in_the_template(piece):
    assert piece in TEMPLATE


def test_ai_summary_renders_below_the_card():
    assert TEMPLATE.index("${verdictCard(s)}") < TEMPLATE.index('data-verdict="${s.symbol}"')
