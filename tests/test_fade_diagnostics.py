import math

import pandas as pd

from scanner import fade_diagnostics as D

IDX = """Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change
Nifty 50,23-01-2025,23205.35,23270.80,23090.65,23205.35,49.95
Nifty Bank,23-01-2025,48589.00,48828.40,48339.00,48589.00,-135.55
"""


def test_index_file_parse_and_missing_name():
    k = D.parse_index_file(IDX)
    assert k == {"open": 23205.35, "high": 23270.8, "low": 23090.65, "close": 23205.35}
    assert D.parse_index_file(IDX, "nifty it") is None


def test_loser_classes_and_buckets():
    assert D.loser_class(5.0, -40) == "never up" and D.loser_class(45.0, -10) == "round trip"
    assert D.loser_class(20.0, -5) == "other" and D.loser_class(1.0, 3) == "winner"
    cuts, labs = [-5, 5], ["fell", "flat", "rose"]
    assert [D.bucket(x, cuts, labs) for x in (-6, -5, 0, 5, 5.1)] == ["fell", "fell", "flat", "flat", "rose"]
    assert D.bucket(math.nan, cuts, labs) is None


def test_reversal_sign():
    assert D.reversal(6.0, -1.5) == 1.5          # ran up, fell on day 0: moved opposite
    assert D.reversal(-6.0, -1.5) == -1.5        # fell, kept falling: same direction
    assert math.isnan(D.reversal(0.0, 1.0))


def test_stock_features_use_only_days_before_day0():
    days = pd.bdate_range("2025-01-01", periods=80).strftime("%Y-%m-%d").tolist()
    close = [100.0 + k for k in range(80)]
    df = pd.DataFrame({"Open": close, "High": [c + 1 for c in close], "Low": [c - 1 for c in close], "Close": close,
                       "Volume": [1000.0] * 79 + [5000.0]}, index=days)
    i = 70
    df.loc[days[i], ["Open", "Close"]] = [160.0, 150.0]          # day 0 itself must not change the pre-runs
    f = D.stock_features(df, days, i)
    assert round(f["pre5"], 4) == round((169 / 164 - 1) * 100, 4)
    assert round(f["pre20"], 4) == round((169 / 149 - 1) * 100, 4)
    assert round(f["gap"], 4) == round((160 / 169 - 1) * 100, 4) and round(f["oc"], 4) == round((150 / 160 - 1) * 100, 4)
    assert f["vol_ratio"] == 1.0                                 # day -1's volume vs the 20 before it
    assert round(f["pre_entry"], 4) == round(f["gap"], 4) and round(f["full"], 4) == round(f["cc"], 4)


def test_in_session_filer_ends_the_pre_run_at_day_minus_2():
    days = pd.bdate_range("2025-01-01", periods=80).strftime("%Y-%m-%d").tolist()
    i = 70
    assert D.filing_slot(days, i, days[i], "08:30") == ("pre-open day 0", i - 1)
    assert D.filing_slot(days, i, days[i - 1], "13:05") == ("in session day -1", i - 2)
    assert D.filing_slot(days, i, days[i - 1], "16:40") == ("after close day -1", i - 1)
    assert D.filing_slot(days, i, "2025-04-05", "11:00")[0] == "non-session day / earlier"
    close = [100.0 + k for k in range(80)]
    df = pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close, "Volume": [1.0] * 80}, index=days)
    f = D.stock_features(df, days, i, base=i - 2)
    assert round(f["pre5"], 4) == round((168 / 163 - 1) * 100, 4)
    assert round(f["pre_entry"], 4) == round((170 / 168 - 1) * 100, 4)   # day 0's open vs the close before the filing


def test_one_day_jump_blanks_only_the_windows_it_falls_in():
    days = pd.bdate_range("2025-01-01", periods=80).strftime("%Y-%m-%d").tolist()
    close = [100.0] * 40 + [150.0] * 40                                   # a 50 % jump on days[40]
    df = pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close, "Volume": [1.0] * 80}, index=days)
    f = D.stock_features(df, days, 70)
    assert f["pre5"] == 0.0 and f["pre20"] == 0.0 and math.isnan(f["pre60"]) and math.isnan(f["pos52"])
    assert f["ca_blank"] == "pre60,pos52"


def test_beta_and_pooled_t():
    days = pd.bdate_range("2024-01-01", periods=300).strftime("%Y-%m-%d").tolist()
    rng = __import__("numpy").random.default_rng(1)
    m = pd.Series(1000 * (1 + rng.normal(0, 0.01, 300)).cumprod(), index=days)
    s = pd.Series(100 * (1 + 1.5 * (m / m.shift(1) - 1).fillna(0)).cumprod(), index=days)
    assert abs(D.beta(s, m, days, 299) - 1.5) < 1e-6
    assert D.pooled_t(2.0, 2.0) == round(4 / math.sqrt(2), 3) and D.pooled_t(None, 1.0) is None
    assert 0 < D.chance_consistent(100) < 10
