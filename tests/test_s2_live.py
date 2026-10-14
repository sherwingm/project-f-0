"""S2 page data: the last session's short build-ups and the /s2 route."""
import numpy as np
import pandas as pd

from scanner import s2_live


def bars(closes, vols):
    idx = [f"2026-09-{d:02d}" for d in range(1, len(closes) + 1)]
    return pd.DataFrame({"Close": closes, "Volume": vols}, index=idx)


def test_find_signals_reads_the_cell():
    n = 25
    base = [100.0] * (n - 1)
    px = {"DROP": bars(base + [96.0], [1000] * (n - 1) + [2000]),          # -4 %, 2x volume
          "THIN": bars(base + [96.0], [1000] * (n - 1) + [1200]),          # volume only 1.2x
          "SMALL": bars(base + [98.5], [1000] * (n - 1) + [2000])}         # only -1.5 %
    d = f"2026-09-{n:02d}"
    oi_prev = pd.Series({"DROP": 1000.0, "THIN": 1000.0, "SMALL": 1000.0})
    oi_d = pd.Series({"DROP": 1150.0, "THIN": 1150.0, "SMALL": 1150.0})
    out = s2_live.find_signals(oi_d, oi_prev, px, d)
    assert [s["symbol"] for s in out] == ["DROP"] and out[0]["oi_pct"] == 15.0 and out[0]["price_pct"] == -4.0
    oi_small = pd.Series({"DROP": 1050.0, "THIN": 1150.0, "SMALL": 1150.0})   # OI +5 % only
    assert s2_live.find_signals(oi_small, oi_prev, px, d) == []


def test_combined_oi_sums_expiries():
    b = pd.DataFrame({"FinInstrmTp": ["STF", "STF", "STO"], "TckrSymb": ["X", "X", "X"],
                      "XpryDt": ["2026-10-27", "2026-11-24", "2026-10-27"], "OpnIntrst": [100, 50, 999]})
    oi, exp = s2_live.combined_oi(b)
    assert oi["X"] == 150 and exp == {"2026-10-27", "2026-11-24"}


def test_s2_route_renders(monkeypatch):
    from fastapi.testclient import TestClient
    from server import app as app_mod
    from server.config import settings
    monkeypatch.setattr(settings, "public_access", True)
    monkeypatch.setattr(app_mod.state, "scan", {"meta": {"s2": {"signals": {"session": "2026-10-13", "signals": []}}}})
    c = TestClient(app_mod.app)
    r = c.get("/s2")
    assert r.status_code == 200 and "Short build-up" in r.text and '"session":"2026-10-13"' in r.text
    assert c.get("/api/s2").json()["signals"]["session"] == "2026-10-13"
