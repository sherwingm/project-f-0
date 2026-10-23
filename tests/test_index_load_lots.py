from datetime import date

import pandas as pd
import pytest

from index_data import load as L


@pytest.fixture
def store(tmp_path, monkeypatch):
    d = tmp_path / "options_daily" / "NIFTY"
    d.mkdir(parents=True)
    rows = [  # the near-month future comes first in the bhavcopy and carries the old lot
        ("2025-01-02", "2025-01-30", "IDF", 25), ("2025-01-02", "2025-01-02", "IDO", 75),
        ("2025-01-02", "2025-01-30", "IDO", 25), ("2025-01-03", "2025-01-09", "IDO", 75),
        ("2025-01-03", "2025-01-30", "IDO", 25),
    ]
    pd.DataFrame(rows, columns=["TradDt", "XpryDt", "FinInstrmTp", "NewBrdLotQty"]).to_parquet(d / "2025-01.parquet")
    monkeypatch.setattr(L, "STORE", tmp_path)
    L._lot_table.cache_clear()
    yield
    L._lot_table.cache_clear()


def test_lot_is_the_traded_contracts_not_the_futures(store):
    assert L.lot_on(date(2025, 1, 2), "NIFTY", date(2025, 1, 2)) == 75
    assert L.lot_on(date(2025, 1, 2), "NIFTY", date(2025, 1, 30)) == 25


def test_missing_pair_falls_back_to_the_contracts_last_known_lot(store):
    assert L.lot_on(date(2025, 1, 6), "NIFTY", date(2025, 1, 9)) == 75


def test_without_expiry_the_nearest_expiry_on_the_last_trade_date(store):
    assert L.lot_on(date(2025, 1, 4), "NIFTY") == 75
    with pytest.raises(ValueError):
        L.lot_on(date(2024, 12, 1), "NIFTY")


def test_vix_minutes_stored_at_x100_or_div100_are_rescaled(tmp_path, monkeypatch):
    import pandas as pd
    d = tmp_path / "spot_1m" / "INDIAVIX"
    d.mkdir(parents=True)
    ts = pd.date_range("2022-02-24 09:15", periods=4, freq="min", tz="Asia/Kolkata")
    pd.DataFrame({"timestamp": ts, "open": [30.0, 0.31, 3100.0, 31.0], "high": [30.0, 0.31, 3100.0, 31.0],
                  "low": [30.0, 0.31, 3100.0, 31.0], "close": [30.0, 0.31, 3100.0, 31.0]}).to_parquet(d / "2022-02.parquet")
    pd.DataFrame({"date": [pd.Timestamp("2022-02-24")], "close": [30.3]}).to_parquet(tmp_path / "vix_daily.parquet")
    monkeypatch.setattr(L, "STORE", tmp_path)
    L._vix_daily.cache_clear()
    v = L.vix_1m(date(2022, 2, 24), date(2022, 2, 24))
    L._vix_daily.cache_clear()
    assert list(v["close"].round(2)) == [30.0, 31.0, 31.0, 31.0]
