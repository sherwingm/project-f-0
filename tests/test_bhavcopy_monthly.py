"""Daily index-option OHLC in monthly files (index_data/bhavcopy_ohlc.py) and the one-off split of the yearly files."""
import pandas as pd

from index_data import bhavcopy_ohlc as B


def rows(days, close):
    return pd.DataFrame({"TradDt": days, "FinInstrmTp": "IDO", "XpryDt": "2026-10-27", "StrkPric": 25000.0,
                         "OptnTp": "CE", "ClsPric": close})


def test_split_yearly_into_months_and_merge_with_an_existing_month(tmp_path):
    d = tmp_path / "options_daily" / "NIFTY"
    d.mkdir(parents=True)
    rows(["2026-09-29", "2026-09-30", "2026-10-01", "2026-10-16"], 1.0).to_parquet(d / "2026.parquet", index=False)
    rows(["2026-10-19"], 2.0).to_parquet(d / "2026-10.parquet", index=False)        # the nightly job, already monthly
    out = B.split_yearly(tmp_path)
    assert out == {"yearly_files": 1, "monthly_files": 2, "rows": 4}
    assert sorted(f.name for f in d.iterdir()) == ["2026-09.parquet", "2026-10.parquet"]
    oct_ = pd.read_parquet(d / "2026-10.parquet")
    assert list(oct_["TradDt"]) == ["2026-10-01", "2026-10-16", "2026-10-19"]
    assert B.done_days(tmp_path) == {"2026-09-29", "2026-09-30", "2026-10-01", "2026-10-16", "2026-10-19"}
    assert B.split_yearly(tmp_path)["yearly_files"] == 0                                # a re-run does nothing
