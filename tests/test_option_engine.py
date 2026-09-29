"""The option backtest engine: VWAP / close fills with the 50-contract floor, and the expiry rule."""
from datetime import date

import pandas as pd
import pytest

from scanner import nse_fo
from scanner import option_engine as oe


def test_premium_vwap_from_notional_turnover():
    # GRANULES 600 CE, 2025-01-06: 862 contracts x 1,000, Rs 54,21,91,600 notional -> 628.99 - 600
    assert oe.premium_vwap(542191600.0, 862, 1000, 600.0, 24.25, 33.5) == pytest.approx(28.9926, abs=1e-4)
    # AARTIIND 1000 CE, 2022-01-05 (old file): Rs 7,762.90 lakh, 886 contracts x 850 -> 30.79
    assert oe.premium_vwap(7762.90e5, 886, 850, 1000.0, 26.45, 34.45) == pytest.approx(30.7927, abs=1e-4)
    assert oe.premium_vwap(542191600.0, 862, 1000, 600.0, 30.0, 33.5) is None        # outside low-high
    assert oe.premium_vwap(0.0, 862, 1000, 600.0) is None
    assert oe.premium_vwap(542191600.0, 862, 0, 600.0) is None
    assert oe.premium_vwap(1000.0 * 600 * 10, 10, 1000, 600.0) is None                 # premium 0


def test_entry_fill_vwap_close_fallback_floor_and_sides():
    assert oe.entry_fill(862, 542191600.0, 1000, 600.0, 27.65, 24.25, 33.5) == (29.04, "vwap")
    assert oe.entry_fill(862, 542191600.0, 1000, 600.0, 27.65, 24.25, 33.5, side="SELL") == (28.94, "vwap")
    assert oe.entry_fill(862, 0.0, 1000, 600.0, 27.65) == (27.7, "close")              # no turnover: the close
    assert oe.entry_fill(862, 542191600.0, 0, 600.0, 27.65) == (27.7, "close")         # no lot: the close
    assert oe.entry_fill(50, 50 * 1000 * 610.0, 1000, 600.0, 9.0) == (10.05, "vwap")    # exactly 50: fills
    assert oe.entry_fill(49, 49 * 1000 * 610.0, 1000, 600.0, 9.0) is None               # 49 contracts: no fill
    assert oe.entry_fill(float("nan"), 0.0, 1000, 600.0, 9.0) is None


def test_expiry_rule_current_month_with_10_sessions_else_next():
    cal = [d.date() for d in pd.bdate_range("2026-09-01", "2026-12-31")]
    exp = ["2026-09-29", "2026-10-27", "2026-11-24"]
    assert oe.choose_expiry(exp, cal, date(2026, 9, 14)) == "2026-09-29"    # 11 sessions: 15 Sep .. 29 Sep
    assert oe.choose_expiry(exp, cal, date(2026, 9, 15)) == "2026-09-29"    # exactly 10
    assert oe.choose_expiry(exp, cal, date(2026, 9, 16)) == "2026-10-27"    # 9: the next monthly
    assert oe.choose_expiry(exp, cal, date(2026, 9, 29)) == "2026-10-27"    # expiry day itself: 0 remain
    assert oe.choose_expiry(["2026-09-29"], cal, date(2026, 9, 25)) is None
    weekly = exp + ["2026-10-06", "2026-10-13"]                              # a weekly is never "monthly"
    assert oe.monthly(weekly) == exp
    assert oe.choose_expiry(weekly, cal, date(2026, 9, 25)) == "2026-10-27"


def test_stock_option_prices_both_formats():
    old = pd.DataFrame({"INSTRUMENT": ["OPTSTK", "OPTSTK", "FUTSTK", "OPTIDX"], "SYMBOL": ["ABC", "ABC", "ABC", "NIFTY"],
                        "EXPIRY_DT": ["27-Jan-2022"] * 4, "STRIKE_PR": [1000.0, 1020.0, 0.0, 17000.0],
                        "OPTION_TYP": ["CE", "PE", "XX", "CE"], "OPEN": [30.55, 0.0, 1000.0, 100.0],
                        "HIGH": [34.45, 0.0, 1, 1], "LOW": [26.45, 0.0, 1, 1], "CLOSE": [31.45, 40.0, 1, 1],
                        "CONTRACTS": [886, 0, 5, 5], "VAL_INLAKH": [7762.90, 0.0, 1, 1],
                        "OPEN_INT": [250750, 1700, 999, 50]})
    df = nse_fo.stock_option_prices(old, True)
    assert list(df["TckrSymb"]) == ["ABC", "ABC"] and list(df["NewBrdLotQty"]) == [850, 850]    # gcd(250750, 1700)
    assert df.loc[0, "TtlTrfVal"] == pytest.approx(776290000.0) and df.loc[1, "OpnPric"] == 0
    assert df.loc[0, "XpryDt"] == "2022-01-27"
    new = pd.DataFrame({"FinInstrmTp": ["STO", "STF"], "TckrSymb": ["ABC", "ABC"], "XpryDt": ["2025-01-30"] * 2,
                        "StrkPric": [600.0, None], "OptnTp": ["CE", None], "OpnPric": [24.8, 610.0],
                        "HghPric": [33.5, 1], "LwPric": [24.25, 1], "ClsPric": [27.65, 1], "TtlTradgVol": [862, 1],
                        "TtlTrfVal": [542191600.0, 1], "NewBrdLotQty": [1000, 1000]})
    df = nse_fo.stock_option_prices(new, False)
    assert len(df) == 1 and df.loc[0, "NewBrdLotQty"] == 1000 and df.loc[0, "TtlTradgVol"] == 862


def test_test_window_and_holdout_split():
    assert oe.window() == ("2021-01-01", "2024-12-31")
    assert oe.window(holdout=True, last_session="2026-09-18") == ("2025-01-01", "2026-09-18")
    assert oe.split_of("2024-12-31") == "test" and oe.split_of("2025-01-01") == "holdout"
    assert [p for p, _, _ in oe.TEST_PERIODS] == ["2021-22", "2023-24"]
    s = oe.split_statement(("2021-01-01", "2024-12-31"))
    assert "holdout 2025-01-01 onward" in s and s.endswith("the holdout is untouched.")
