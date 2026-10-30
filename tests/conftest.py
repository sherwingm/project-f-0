"""Every test gets its own index Feather cache, so no test can write into data/cache/index/feather (2026-10-30: a test
store under tmp_path wrote 5 fake lot rows over the real options_daily/NIFTY/2025-01 copy)."""
import pytest


@pytest.fixture(autouse=True)
def _private_index_feather_cache(tmp_path_factory, monkeypatch):
    try:
        from index_data import load as L
    except Exception:           # a test environment without the index modules
        yield
        return
    monkeypatch.setattr(L, "FEATHER_CACHE", tmp_path_factory.mktemp("feather_cache"))
    yield
