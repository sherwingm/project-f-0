import math

import numpy as np
import pandas as pd

from scanner import s2b_common as C
from scanner import s2_parents as P
from scanner import s2_weak_results_screen as W


def test_short_return_and_cost():
    assert round(C.short_return(100.0, 98.0), 6) == round(2.0 - 0.1, 6)
    assert math.isnan(C.short_return(float("nan"), 98.0))


def test_strict_lookup_never_uses_the_entry_day_or_after_the_signal_day():
    s = pd.Series([1.0, 2.0, 3.0, 4.0], index=["2025-01-30", "2025-01-31", "2025-02-01", "2025-02-03"])
    assert P.strict_before(s, "2025-02-03", "2025-02-01") == ("2025-02-01", 3.0)      # Saturday budget session
    assert P.strict_before(s, "2025-02-03", "2025-01-31") == ("2025-01-31", 2.0)      # not after the signal day
    assert P.strict_before(s, "2025-01-30", "2025-01-30") is None


def test_known_brent_closes_in_the_cache():
    b = P.load("BZ=F")
    assert round(b["2022-03-08"], 2) == 127.98 and round(b["2022-03-09"], 2) == 111.14


def test_period_ended_and_xbrl_date():
    assert W.period_ended("financial results for the period ended September 30, 2023.") == "2023-09-30"
    assert W.period_ended("for the quarter and nine months ended 31st December 2025") == "2025-12-31"
    assert W.period_ended("for the Financial Year ended March 31 , 2025") == "2025-03-31"
    assert W.period_ended("financial statements for the period ended March 2022, Dividend") == "2022-03-31"
    assert W.period_ended("financial results Q2") is None
    assert W.xbrl_date("https://x/INDAS_51636_209974_23012020041926_WEB.xml") == "2020-01-23"


def test_weak_results_day0_and_pre_move_base():
    cal = ["2025-01-06", "2025-01-07", "2025-01-08"]
    assert W.day0_0900(cal, "2025-01-07", "08:45") == 1                      # before 09:00: the same day
    assert W.day0_0900(cal, "2025-01-07", "09:05") == 2                      # after 09:00: the next session
    assert W.base_k(cal, "2025-01-07", "16:10") == 1                         # after the close: that day's close
    assert W.base_k(cal, "2025-01-07", "13:00") == 0                         # during the session: the day before


def test_report_pass_needs_every_rule():
    rng = np.random.default_rng(3)
    days = pd.bdate_range("2021-01-04", "2026-09-25").strftime("%Y-%m-%d")
    pick = rng.choice(days, 400, replace=False)
    ev = pd.DataFrame({"date": pick, "symbol": [f"S{k % 40}" for k in range(400)],
                       "r": 1.5 + rng.normal(0, 1.0, 400), "step1_overlap": False})
    row = C.report(ev, "r", {"cell": "x"})
    assert row["PASS"] == "PASS" and row["N"] == 400
    weak = ev.assign(r=ev["r"] - 1.4)                                         # mean ~ +0.1 %: fails the mean rule
    assert C.report(weak, "r", {"cell": "y"})["PASS"] == ""


def test_xbrl_date_reads_names_without_the_web_suffix():
    assert W.xbrl_date("https://x/corporate/xbrl/INDAS_97204_918439_14082023051257.xml") == "2023-08-14"
    assert W.xbrl_date("https://x/INTEGRATED_FILING_INDAS_1667963_15052026073307_WEB.xml") == "2026-05-15"
    assert W.xbrl_date(None) is None


def test_date_alignment_check_catches_a_one_day_shift():
    from scanner import s2_parent_screen as S
    rng = np.random.default_rng(5)
    days = pd.bdate_range("2025-01-01", periods=300).strftime("%Y-%m-%d")
    px = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 300))), index=days)
    hourly = pd.Series(px.values, index=[d + " 16:00" for d in days])
    a = S.date_alignment(px, hourly)
    assert S.alignment_ok(a) and a["lag 0"] > 0.99
    shifted = pd.Series(px.values[1:], index=days[:-1])                        # daily bars dated one day early
    assert not S.alignment_ok(S.date_alignment(shifted, hourly))
