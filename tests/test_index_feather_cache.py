"""index_data.load.read_store: a Feather copy of a store Parquet that returns the same frame and follows Parquet changes."""
import os
import time

import pandas as pd

from index_data import load as L


def _setup(tmp_path, monkeypatch):
    store = tmp_path / "store"
    (store / "options_daily" / "NIFTY").mkdir(parents=True)
    monkeypatch.setattr(L, "STORE", str(store))
    monkeypatch.setattr(L, "FEATHER_CACHE", tmp_path / "cache")
    return store


def test_same_frame_and_cache_built(tmp_path, monkeypatch):
    store = _setup(tmp_path, monkeypatch)
    p = store / "options_daily" / "NIFTY" / "2024-01.parquet"
    df = pd.DataFrame({"TradDt": pd.to_datetime(["2024-01-01", "2024-01-02"]), "StrkPric": [21000.0, 21050.0],
                       "OptnTp": ["CE", "PE"], "ClsPric": [101.5, 99.0]})
    df.to_parquet(p)
    first = L.read_store(p)
    assert len(list((tmp_path / "cache").rglob("2024-01.feather"))) == 1
    second = L.read_store(p, columns=["TradDt", "ClsPric"])
    pd.testing.assert_frame_equal(first, pd.read_parquet(p))
    pd.testing.assert_frame_equal(second, pd.read_parquet(p, columns=["TradDt", "ClsPric"]))


def test_rebuilt_when_parquet_changes(tmp_path, monkeypatch):
    store = _setup(tmp_path, monkeypatch)
    p = store / "vix_daily.parquet"
    pd.DataFrame({"close": [14.0]}).to_parquet(p)
    assert L.read_store(p)["close"].tolist() == [14.0]
    pd.DataFrame({"close": [14.0, 23.5]}).to_parquet(p)
    later = time.time() + 5
    os.utime(p, (later, later))
    assert L.read_store(p)["close"].tolist() == [14.0, 23.5]


def test_non_default_index_not_cached(tmp_path, monkeypatch):
    store = _setup(tmp_path, monkeypatch)
    p = store / "x.parquet"
    pd.DataFrame({"a": [1, 2]}, index=[5, 9]).to_parquet(p)
    out = L.read_store(p)
    assert list(out.index) == [5, 9]
    assert not list((tmp_path / "cache").rglob("x.feather"))


def test_another_store_with_the_same_relative_path_never_shares_a_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "FEATHER_CACHE", tmp_path / "cache")
    real, fake = tmp_path / "real", tmp_path / "fake"
    for root, n in ((real, 3), (fake, 1)):
        (root / "options_daily" / "NIFTY").mkdir(parents=True)
        pd.DataFrame({"x": list(range(n))}).to_parquet(root / "options_daily" / "NIFTY" / "2025-01.parquet")
    monkeypatch.setattr(L, "STORE", str(real))
    assert len(L.read_store(real / "options_daily" / "NIFTY" / "2025-01.parquet")) == 3
    monkeypatch.setattr(L, "STORE", str(fake))                  # a test store, read later and newer
    assert len(L.read_store(fake / "options_daily" / "NIFTY" / "2025-01.parquet")) == 1
    monkeypatch.setattr(L, "STORE", str(real))
    assert len(L.read_store(real / "options_daily" / "NIFTY" / "2025-01.parquet")) == 3


def test_copy_rebuilt_when_size_changes_with_the_same_mtime(tmp_path, monkeypatch):
    store = _setup(tmp_path, monkeypatch)
    p = store / "vix_daily.parquet"
    pd.DataFrame({"close": [14.0]}).to_parquet(p)
    ns = p.stat().st_mtime_ns
    assert L.read_store(p)["close"].tolist() == [14.0]
    pd.DataFrame({"close": [14.0, 23.5, 19.0]}).to_parquet(p)
    os.utime(p, ns=(ns, ns))
    assert L.read_store(p)["close"].tolist() == [14.0, 23.5, 19.0]
