"""Date-versioned STT (server/charges.py STT_HISTORY, added 2026-11-13): history trades are charged the STT of their own day; live and every
caller that does not pass a date keep the current table exactly as before."""
from datetime import date

import pytest

from index_data import load as L
from scanner.s3_engine import Leg, Spec, simulate
from server import charges


def test_without_a_date_nothing_changes_and_the_current_rates_apply():
    assert charges.stt_rates() == (0.05, 0.15, 0.15)
    a = charges.leg("PE", "SELL", 65, 100.0)
    assert a == charges.leg("PE", "SELL", 65, 100.0, on=None)
    assert a["stt"] == pytest.approx(0.0015 * 65 * 100.0, abs=0.01)


def test_from_the_budget_2026_date_the_current_table_applies():
    assert charges.leg("PE", "SELL", 65, 100.0, on=date(2026, 4, 1)) == charges.leg("PE", "SELL", 65, 100.0)
    assert charges.leg("PE", "SELL", 65, 100.0, on=date(2026, 11, 9)) == charges.leg("PE", "SELL", 65, 100.0)


def test_the_day_before_the_budget_2026_hike_options_sale_stt_is_0_10_percent():
    d = charges.leg("PE", "SELL", 65, 100.0, on=date(2026, 3, 31))
    assert d["stt"] == pytest.approx(0.0010 * 65 * 100.0, abs=0.01)
    assert d["total"] < charges.leg("PE", "SELL", 65, 100.0)["total"]
    assert charges.stt_rates(date(2026, 3, 31)) == (0.02, 0.10, 0.125)


def test_before_october_2024_the_older_rates_apply():
    assert charges.stt_rates(date(2024, 9, 30)) == (0.0125, 0.0625, 0.125)
    assert charges.stt_rates(date(2024, 10, 1)) == (0.02, 0.10, 0.125)
    assert charges.leg("CE", "SELL", 75, 100.0, on=date(2024, 9, 30))["stt"] == pytest.approx(0.000625 * 75 * 100.0, abs=0.01)


def test_buy_legs_and_the_other_components_do_not_depend_on_the_date():
    for on in (date(2024, 5, 1), date(2025, 6, 6), date(2026, 3, 31)):
        a, b = charges.leg("PE", "BUY", 65, 100.0, on=on), charges.leg("PE", "BUY", 65, 100.0)
        assert a == b                                    # stt is sell-side only: a buy leg is identical on every date
        s, t = charges.leg("PE", "SELL", 65, 100.0, on=on), charges.leg("PE", "SELL", 65, 100.0)
        assert all(s[k] == t[k] for k in ("brokerage", "exchange", "sebi", "stamp", "gst"))


def test_futures_stt_follows_the_history_too():
    assert charges.leg("FUT", "SELL", 500, 1000.0, on=date(2025, 1, 9))["stt"] == pytest.approx(0.0002 * 500 * 1000.0, abs=0.01)
    assert charges.leg("FUT", "SELL", 500, 1000.0)["stt"] == pytest.approx(0.0005 * 500 * 1000.0, abs=0.01)


def test_exercise_stt_follows_the_history():
    assert charges.exercise(75, 100.0, on=date(2025, 1, 9))["stt"] == pytest.approx(0.00125 * 7500, abs=0.01)
    assert charges.exercise(75, 100.0)["stt"] == pytest.approx(0.0015 * 7500, abs=0.01)


def test_an_override_through_configure_wins_on_every_date(monkeypatch):
    monkeypatch.setattr(charges, "OPT_STT_SELL_PCT", charges.OPT_STT_SELL_PCT)       # registered so the test restores it
    monkeypatch.setattr(charges, "_OVERRIDDEN", set())
    charges.configure({"OPT_STT_SELL_PCT": 0.2})
    assert charges.stt_rates(date(2025, 1, 9))[1] == 0.2 and charges.stt_rates()[1] == 0.2
    assert charges.stt_rates(date(2025, 1, 9))[0] == 0.02                             # the others still follow the history


def test_the_engine_charges_the_stt_of_each_leg_s_own_day():
    day = date(2025, 1, 9)
    rows = [dict(timestamp=L.at(day, *map(int, t.split(":"))), strike=24000.0, option_type="PE", open=c, high=c, low=c, close=c,
                 volume=10, oi=100, source="upstox") for t, c in (("09:41", 100.0), ("15:15", 150.0))]
    import pandas as pd
    chain = pd.DataFrame(rows)
    r = simulate(chain, 24000.0, day, Spec("p", [Leg("BUY", "PE", 0)], entry=(9, 41), exit=(15, 15)), lot=75)
    import re
    fi, fo = (float(x) for x in re.search(r"@([\d.]+)>([\d.]+)", r["legs"]).groups())
    expected = charges.leg("PE", "BUY", 75, fi, on=day)["total"] + charges.leg("PE", "SELL", 75, fo, on=day)["total"]
    old_style = charges.leg("PE", "BUY", 75, fi)["total"] + charges.leg("PE", "SELL", 75, fo)["total"]
    assert r["fees_rs"] == pytest.approx(expected, abs=0.1)
    assert r["fees_rs"] < old_style - 3                  # the 2025 STT (0.10 %) is lower than the 2026 table's (0.15 %) on a Rs 11,000 sale
