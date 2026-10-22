from datetime import date

import pandas as pd
import pytest

from index_data import load as L
from scanner.s3_engine import Leg, Spec, simulate

DAY = date(2025, 1, 9)


def chain(prices):
    """prices: {(strike, 'CE'|'PE'): {'HH:MM': close}} -> a merged-chain frame."""
    rows = [dict(timestamp=L.at(DAY, *map(int, t.split(":"))), strike=float(k), option_type=o, open=c, high=c, low=c,
                 close=c, volume=10, oi=100, source="upstox")
            for (k, o), path in prices.items() for t, c in path.items()]
    return pd.DataFrame(rows).sort_values(["strike", "option_type", "timestamp"]).reset_index(drop=True)


STRADDLE = Spec("short_straddle", [Leg("SELL", "CE", 0), Leg("SELL", "PE", 0)], entry=(9, 20), exit=(14, 45), stop=0.25)


def test_time_exit_hand_worked():
    c = chain({(24000, "CE"): {"09:20": 100, "12:00": 80, "14:45": 60},
               (24000, "PE"): {"09:20": 100, "12:00": 90, "14:45": 50}})
    r = simulate(c, 24010.0, DAY, STRADDLE, lot=75)
    assert r["skip"] == "" and r["reason"] == "time" and r["exit_at"] == "14:45"
    # entry before 09:30: 1 % slippage -> sold at 99 + 99; exit 0.5 % -> bought at 60.30 + 50.25
    assert r["premium"] == pytest.approx(198.0)
    assert r["gross_rs"] == pytest.approx((198 - 110.55) * 75, abs=0.01)
    assert r["net_rs"] == pytest.approx(r["gross_rs"] - r["fees_rs"], abs=0.01)
    assert r["fees_rs"] > 80                      # 4 orders x Rs 20 plus STT and exchange charges


def test_combined_stop_fires_on_the_first_minute_past_it():
    c = chain({(24000, "CE"): {"09:20": 100, "09:40": 120, "10:00": 200, "14:45": 10},
               (24000, "PE"): {"09:20": 100, "09:40": 90, "10:00": 80, "14:45": 10}})
    r = simulate(c, 24000.0, DAY, STRADDLE, lot=75)
    # 09:40: cost 210 vs credit 198 (-6 %, held); 10:00: cost 280 (-41 %) -> stop
    assert r["reason"] == "stop" and r["exit_at"] == "10:00"
    assert r["gross_rs"] == pytest.approx((198 - (201 + 80.4)) * 75, abs=0.01)
    assert r["worst_pct"] == pytest.approx(-41.4, abs=0.1)


def test_missing_entry_price_skips_the_day():
    c = chain({(24000, "CE"): {"09:20": 100}, (24050, "PE"): {"09:20": 100}})
    r = simulate(c, 24000.0, DAY, STRADDLE, lot=75)
    assert r["skip"].startswith("no price 24000 PE")


def test_stale_entry_price_is_refused():
    c = chain({(24000, "CE"): {"09:20": 100}, (24000, "PE"): {"09:15": 100, "14:45": 50}})
    assert simulate(c, 24000.0, DAY, STRADDLE, lot=75)["skip"].startswith("no price 24000 PE")


def test_long_straddle_target():
    spec = Spec("gamma", [Leg("BUY", "CE", 0), Leg("BUY", "PE", 0)], entry=(14, 45), exit=(15, 25), target=0.5)
    c = chain({(24000, "CE"): {"14:45": 20, "15:05": 40, "15:25": 5},
               (24000, "PE"): {"14:45": 20, "15:05": 25, "15:25": 30}})
    r = simulate(c, 24000.0, DAY, spec, lot=75)
    assert r["kind"] == "debit" and r["reason"] == "target" and r["exit_at"] == "15:05"
    # bought at 20.10 x 2; at 15:05 value 65 = +61.7 % >= 50 %; sold 15:05 (after 15:00: 1 %) at 39.60 + 24.75
    assert r["gross_rs"] == pytest.approx((39.6 + 24.75 - 40.2) * 75, abs=0.01)


def test_double_costs_cost_more():
    c = chain({(24000, "CE"): {"09:20": 100, "14:45": 60}, (24000, "PE"): {"09:20": 100, "14:45": 50}})
    one = simulate(c, 24000.0, DAY, STRADDLE, lot=75)
    two = simulate(c, 24000.0, DAY, Spec(**{**STRADDLE.__dict__, "cost_mult": 2.0}), lot=75)
    assert two["net_rs"] < one["net_rs"] and two["fees_rs"] == pytest.approx(2 * one["fees_rs"], rel=0.02)


def test_iron_fly_margin_is_its_max_loss():
    fly = Spec("fly", [Leg("SELL", "CE", 0), Leg("SELL", "PE", 0), Leg("BUY", "CE", 4), Leg("BUY", "PE", -4)])
    c = chain({(24000, "CE"): {"09:20": 100, "14:45": 60}, (24000, "PE"): {"09:20": 100, "14:45": 60},
               (24200, "CE"): {"09:20": 20, "14:45": 8}, (23800, "PE"): {"09:20": 20, "14:45": 8}})
    r = simulate(c, 24000.0, DAY, fly, lot=75)
    # credit 99 + 99 − 20.2 − 20.2 = 157.6; wings 200 points wide -> max loss (200 − 157.6) x 75
    assert r["premium"] == pytest.approx(157.6)
    assert r["margin_rs"] == pytest.approx((200 - 157.6) * 75, abs=0.01)
