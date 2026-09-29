"""Results coverage table: counts by year of the day-0 abnormal move."""
import math

import pandas as pd

from scanner import results_coverage as rc


def test_coverage_counts_by_year():
    t = pd.DataFrame({"event_date": ["2021-05-01", "2021-06-01", "2021-07-01", "2022-01-10"],
                      "benchmark": ["sector", "nifty500", "sector", None],
                      "abnormal_pct": [-2.0, 2.5, 0.3, math.nan]})
    c = rc.coverage(t).set_index("year")
    assert c.loc["2021"].tolist() == [3, 3, 2, 1, 1, 1]
    assert c.loc["2022"].tolist() == [1, 0, 0, 0, 0, 0]
