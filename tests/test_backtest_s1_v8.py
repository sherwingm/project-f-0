"""S1 v8: beat / miss classification with the raw caps, and which arm takes which signal."""
import math

import pandas as pd

from scanner import backtest_s1_v8 as v8


def test_kind_of_beats_misses_and_caps():
    assert v8.kind_of(2.0, 3.0) == "beat" and v8.kind_of(-2.0, -1.0) == "miss"
    assert v8.kind_of(1.9, 3.0) is None and v8.kind_of(-1.9, -3.0) is None
    assert v8.kind_of(5.0, 10.0) is None and v8.kind_of(-5.0, -10.0) is None        # moves of 10 % or more
    assert v8.kind_of(math.nan, 1.0) is None


def test_arms():
    assert v8.in_arm("S", "miss", True) and v8.in_arm("S", "beat", True) and not v8.in_arm("S", "beat", False)
    assert v8.in_arm("S_miss", "miss", True) and not v8.in_arm("S_miss", "beat", True)
    assert v8.in_arm("A", "beat", False) and not v8.in_arm("A", "miss", True)
    assert v8.in_arm("B", "beat", True) and not v8.in_arm("B", "beat", False) and not v8.in_arm("B", "miss", True)


def test_gate_uses_the_two_halves():
    t = pd.DataFrame({"arm": ["S"] * 4, "entry_date": ["2025-05-01", "2025-06-01", "2026-05-01", "2026-06-01"],
                      "net_pct": [10.0, 20.0, -5.0, -1.0], "excluded": [""] * 4})
    g = {r["test"]: r for r in v8.gate(t, "S")}
    assert g["positive in 2025 (mean %)"]["result"] == "pass" and g["positive in 2026 (mean %)"]["result"] == "fail"
    assert g["OVERALL"]["result"] == "FAIL"
