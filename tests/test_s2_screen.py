"""S2 screen: build-up classes and thresholds, expiry skip, next-open entry with the short sign."""
import math

import numpy as np

from scanner import s2_screen as s2


def test_classes_and_thresholds():
    assert s2.classify(2.5, 6.0, 1.6, 2.0, 5.0) == "long_buildup"
    assert s2.classify(-2.5, 6.0, 1.6, 2.0, 5.0) == "short_buildup"
    assert s2.classify(2.5, -6.0, 1.6, 2.0, 5.0) == "short_covering"
    assert s2.classify(-2.5, -6.0, 1.6, 2.0, 5.0) == "long_unwinding"
    assert s2.classify(2.5, 6.0, 1.4, 2.0, 5.0) is None                 # volume ratio below 1.5
    assert s2.classify(2.5, 6.0, 1.6, 3.0, 5.0) is None                 # price below 3 %
    assert s2.classify(2.5, 6.0, 1.6, 2.0, 10.0) is None                # OI below 10 %
    assert s2.classify(math.nan, 6.0, 1.6, 2.0, 5.0) is None


def test_expiry_and_next_session_are_skipped():
    s = ["2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31"]
    assert s2.skip_days(s, {"2025-01-30"}) == {"2025-01-30", "2025-01-31"}


def test_signed_return_enters_next_open():
    o = np.array([100.0, 101.0, 102.0, 104.0])
    c = np.array([100.0, 102.0, 103.0, 106.0])
    assert round(s2.signed_return(o, c, 0, 3, 1), 4) == round((106 / 101 - 1) * 100 - 0.1, 4)
    assert round(s2.signed_return(o, c, 0, 1, -1), 4) == round(-(102 / 101 - 1) * 100 - 0.1, 4)
    assert math.isnan(s2.signed_return(o, c, 1, 3, 1))                  # runs past the data
