"""index_data.fill_spot_upstox.repair_month on small synthetic months."""
import pandas as pd

from index_data.fill_spot_upstox import COLS, repair_month


def _day(day: str, n: int, start: str = "09:15", px: float = 100.0, source: str = "kotak") -> pd.DataFrame:
    ts = pd.date_range(f"{day} {start}", periods=n, freq="min", tz="Asia/Kolkata")
    f = pd.DataFrame({"timestamp": ts, "open": px, "high": px + 1, "low": px - 1, "close": px, "volume": 0,
                      "oi": float("nan"), "source": source})
    return f[COLS]


def test_first_bar_replaced_missing_minutes_added_rest_kept():
    old = _day("2025-03-03", 376)                                     # 09:15-15:30
    old = old.drop(index=[100, 101]).reset_index(drop=True)          # two minutes missing
    up = _day("2025-03-03", 375, px=100.0, source="upstox")          # 09:15-15:29
    up.loc[0, ["open", "high", "low"]] = [99.0, 103.0, 98.0]
    up.loc[50, "close"] = 555.0                                       # a later Upstox minute never overwrites the store
    new, info = repair_month(old, up)
    assert info["bar_0915_replaced"] == 1 and info["bar_0915_changed"] == 1 and info["minutes_added"] == 2
    first = new.iloc[0]
    assert (first["open"], first["high"], first["low"], first["source"]) == (99.0, 103.0, 98.0, "upstox")
    assert len(new) == 376 and new["timestamp"].is_unique
    assert new.loc[new["timestamp"] == up.loc[50, "timestamp"], "close"].iloc[0] == 100.0
    assert new["timestamp"].dt.strftime("%H:%M").iloc[-1] == "15:30"           # the stored 15:30 bar stays


def test_short_special_session_dropped_and_missing_regular_session_added():
    filler = _day("2025-10-21", 376)
    filler[["high", "low"]] = 100.0                                   # 21st: flat filler at the previous close
    old = pd.concat([_day("2025-10-20", 376), filler], ignore_index=True)
    up = pd.concat([_day("2025-10-20", 375, source="upstox"), _day("2025-10-21", 60, "13:45", source="upstox"),
                    _day("2025-10-23", 375, source="upstox")], ignore_index=True)
    new, info = repair_month(old, up)
    days = sorted(set(new["timestamp"].dt.date.astype(str)))
    assert days == ["2025-10-20", "2025-10-23"]
    assert info["days_added"] == ["2025-10-23"] and len(info["days_dropped"]) == 1


def test_day_without_upstox_kept():
    old = _day("2021-12-01", 376)
    new, info = repair_month(old, pd.DataFrame(columns=COLS))
    assert len(new) == 376 and info["days_kept_no_upstox"] == ["2021-12-01"]


def test_flat_filler_without_upstox_dropped():
    old = pd.concat([_day("2025-08-22", 376, px=101.0), _day("2025-08-23", 1)], ignore_index=True)
    old.loc[old.index[-1], ["high", "low"]] = [100.0, 100.0]                  # the one Saturday bar is flat
    up = _day("2025-08-22", 375, source="upstox")
    new, info = repair_month(old, up)
    assert sorted(set(new["timestamp"].dt.date.astype(str))) == ["2025-08-22"] and len(info["days_dropped"]) == 1


def test_partial_upstox_day_never_removes_real_minutes():
    old = _day("2026-10-28", 376)                                    # real (not flat) stored minutes
    up = _day("2026-10-28", 120, source="upstox")                    # a partial Upstox day
    new, info = repair_month(old, up)
    assert len(new) == 376 and not info["days_dropped"] and new["source"].eq("kotak").all()
