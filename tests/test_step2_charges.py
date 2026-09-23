"""Step 2: charges table, including the two acceptance numbers from the spec."""
import pytest

from server import charges


def test_acceptance_future_round_trip_is_about_330():
    rt = charges.round_trip("FUT", "BUY", 500, 1000.0, 1000.0)
    assert rt["total"] == pytest.approx(330, abs=1)
    # the breakdown behind it: value Rs 5,00,000 per leg
    assert rt["brokerage"] == 40.0                  # min(0.03% x 5,00,000 = 150, 20) per order
    assert rt["stt"] == 250.0                       # 0.05% on the sell leg only
    assert rt["exchange"] == 18.3                   # 1.83 per lakh x 5 lakh x 2 legs
    assert rt["sebi"] == 1.0                        # 10 per crore x 2 legs
    assert rt["stamp"] == 10.0                      # 0.002% on the buy leg only
    assert rt["gst"] == pytest.approx(0.18 * (40 + 18.3 + 1.0), abs=0.02)


def test_acceptance_option_round_trip_is_about_83():
    rt = charges.round_trip("CE", "BUY", 500, 30.0, 30.0)
    assert rt["total"] == pytest.approx(83, abs=1)
    assert rt["brokerage"] == 40.0                  # Rs 20 flat per order
    assert rt["stt"] == 22.5                        # 0.15% of the Rs 15,000 sell premium
    assert rt["stamp"] == 0.45                      # 0.003% of the buy premium
    assert rt["exchange"] == pytest.approx(2 * 35.53 * 0.15, abs=0.02)


def test_stt_is_sell_side_only_and_stamp_buy_side_only():
    buy, sell = charges.leg("FUT", "BUY", 500, 1000), charges.leg("FUT", "SELL", 500, 1000)
    assert buy["stt"] == 0 and sell["stt"] == 250.0
    assert buy["stamp"] == 10.0 and sell["stamp"] == 0


def test_future_brokerage_is_percentage_below_the_cap():
    small = charges.leg("FUT", "BUY", 10, 500)       # value 5,000 -> 0.03% = 1.50
    assert small["brokerage"] == 1.5


def test_components_add_up_to_total():
    lg = charges.leg("PE", "SELL", 1250, 3.35)
    assert lg["total"] == pytest.approx(sum(lg[k] for k in charges.COMPONENTS), abs=0.001)


def test_exercise_stt_on_intrinsic_value():
    ex = charges.exercise(500, 12.0)                  # 0.15% x 6,000
    assert ex["stt"] == 9.0
    assert charges.exercise(500, -3.0)["stt"] == 0     # out of the money: nothing to exercise
    h = charges.held_to_expiry("CE", 500, 1.5, 12.0)
    assert h["total"] == pytest.approx(charges.leg("CE", "BUY", 500, 1.5)["total"] + 9.0, abs=0.001)


def test_charges_json_overrides_a_rate_and_rejects_unknown_names():
    before = charges.OPT_BROKERAGE
    try:
        charges.configure('{"OPT_BROKERAGE": 0}')
        assert charges.leg("CE", "BUY", 500, 30)["brokerage"] == 0
        with pytest.raises(ValueError):
            charges.configure({"NOT_A_RATE": 1})
    finally:
        charges.configure({"OPT_BROKERAGE": before})
    assert charges.rates()["effective"] == "2026-04-01"


def test_bad_side_is_rejected():
    with pytest.raises(ValueError):
        charges.leg("FUT", "HOLD", 1, 1)
