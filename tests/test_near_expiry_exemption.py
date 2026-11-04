"""NEAR_EXPIRY_STRATEGIES: only the named rule-trade strategy skips ALLOW_LOTTERY (the user, 2026-11-04)."""
from server.config import settings
from server.liquidity import Rules, classify, exempt, rules_for

CE = {"symbol": "RELIANCE", "instrument": "CE", "tradingsymbol": "RELIANCE26SEP1300CE", "lot_size": 500, "side": "SELL",
      "strike": 1300.0, "expiry": "2026-09-29"}
BOOK = {"depth": {"bid": [(1.0, 10_000)], "ask": [(1.1, 10_000)]}, "open_interest": 1, "last_price": 1.05}


def test_default_names_only_near_expiry():
    assert settings.near_expiry_strategies == frozenset({"near_expiry"})
    assert exempt("near_expiry") and not exempt("fade") and not exempt(None) and not exempt("")


def test_only_the_exempt_strategy_gets_the_lottery_rule():
    base = Rules()                                                  # allow_lottery False, as live
    assert classify(CE, BOOK, 1, 1, rules=rules_for(base, "near_expiry"))["class"] == "lottery"
    for other in ("fade", "A", "B", None):
        assert classify(CE, BOOK, 1, 1, rules=rules_for(base, other))["class"] == "refuse"
    assert base.allow_lottery is False                              # the shared rules are not changed


def test_the_list_comes_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "near_expiry_strategies", frozenset({"g2"}))
    assert exempt("g2") and not exempt("near_expiry")
