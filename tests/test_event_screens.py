"""Event screens: open-entry returns, the result-number tests, the cell summary, QIP issue grouping, dividends."""
import math

import numpy as np
import pandas as pd

from scanner import event_screens as es
from scanner.corp_actions import dividend_amount
from scanner.qip import first_per_issue


def test_open_entry_return():
    o, c = np.array([100.0, 102.0, 104.0]), np.array([101.0, 103.0, 106.0])
    assert round(es.open_entry_return(o, c, 1, 0, 1), 4) == round((103 / 102 - 1) * 100 - 0.1, 4)
    assert round(es.open_entry_return(o, c, 1, 1, -1), 4) == round(-(106 / 102 - 1) * 100 - 0.1, 4)
    assert math.isnan(es.open_entry_return(o, c, 2, 1, 1))


def test_strong_and_weak_numbers():
    assert es.strong({"net_profit_yoy": 30, "net_profit_qoq": 5, "revenue_yoy": 2}, 25)
    assert not es.strong({"net_profit_yoy": 30, "net_profit_qoq": 5, "revenue_yoy": "n/m"}, 25)
    assert not es.strong({"net_profit_yoy": 20, "net_profit_qoq": 5, "revenue_yoy": 2}, 25)
    assert not es.strong({"net_profit_yoy": None, "net_profit_qoq": 5, "revenue_yoy": 2}, 10)
    assert es.weak({"net_profit_yoy": -15, "net_profit_qoq": -1}) and not es.weak({"net_profit_yoy": -15, "net_profit_qoq": 1})


def test_summary_pass_rule_and_direction():
    dates = [f"{y}-06-{d:02d}" for y in range(2021, 2027) for d in range(1, 21)]
    df = pd.DataFrame({"date": dates, "r": [2.0 + (i % 3) * 0.1 for i in range(len(dates))]})
    s = es.summarise(df, {"cell": "x"}, "r", 1.0)
    assert s["n"] == 120 and s["PASS"] == "PASS" and s["years_pos"] == 6
    neg = es.summarise(df.assign(r=-df["r"]), {"cell": "y"}, "r", 0.6, direction_free=True)
    assert neg["side"] == "short" and neg["mean"] > 1.5
    few = es.summarise(df.head(50), {"cell": "z"}, "r", 0.6)
    assert few["PASS"] == ""                                    # N < 100


def test_qip_issue_grouping_and_dividends():
    q = pd.DataFrame({"symbol": ["A", "A", "A"], "date": ["2025-01-02", "2025-01-10", "2025-04-01"],
                      "time": ["10:00", "18:00", "09:00"], "text": ["", "", ""], "url": ["", "", ""]})
    assert list(first_per_issue(q)["date"]) == ["2025-01-02", "2025-04-01"]
    assert dividend_amount("Interim Dividend - Rs 5 Per Share/Special Dividend - Rs 2.50 Per Share") == 7.5
