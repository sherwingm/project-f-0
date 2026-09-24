"""Spec 12 step 6: the event study on hand-checkable series."""
import pandas as pd
import pytest

from scanner.event_study import _car, patterns, print_table, study, summarise

DATES = pd.bdate_range("2026-08-03", periods=20)          # 20 sessions; event at position 10 (2026-08-17)
EVENT_DAY = DATES[10].strftime("%Y-%m-%d")


def series(vals):
    return pd.Series(vals, index=DATES, dtype=float)


def flat_index():
    return series([100.0] * 20)


def ev(**over):
    base = {"symbol": "ABC", "event_date": EVENT_DAY, "type": "order_win", "subtype": None,
            "bucket": "major", "direction": 1, "tier": 1}
    return {**base, **over}


def test_car_windows_by_hand():
    # stock: flat at 100, jumps to 110 on the event day, then to 121 by T+5; index flat
    stock = [100.0] * 10 + [110.0] + [110.0] * 4 + [121.0] * 5
    df = study([ev()], {"ABC": series(stock)}, flat_index())
    r = df.iloc[0]
    assert r["car_pre"] == 0.0                                        # T-5..T-1 unchanged
    assert r["car_day"] == pytest.approx(10.0)                        # 100 -> 110
    assert r["car_post"] == pytest.approx(10.0)                       # 110 -> 121
    assert r["reaction"] == pytest.approx(10.0)


def test_market_adjustment_subtracts_the_index():
    stock = [100.0] * 10 + [105.0] * 10                              # +5% on the day, then flat
    index = [100.0] * 10 + [103.0] * 10                              # market +3% the same day
    df = study([ev()], {"ABC": series(stock)}, series(index))
    assert df.iloc[0]["car_day"] == pytest.approx(2.0)                # 5 - 3
    assert df.iloc[0]["car_post"] == pytest.approx(0.0)


def test_pre_window_catches_the_rumour():
    stock = [100.0] * 5 + [100, 102, 104, 106, 108] + [108.0] * 10   # drifts up before the event
    df = study([ev()], {"ABC": series(stock)}, flat_index())
    assert df.iloc[0]["car_pre"] == pytest.approx(8.0)
    assert df.iloc[0]["car_day"] == pytest.approx(0.0)


def test_edges_and_missing_symbols_stay_as_nulls():
    early = ev(event_date=DATES[2].strftime("%Y-%m-%d"))              # no room for T-5
    late = ev(event_date=DATES[18].strftime("%Y-%m-%d"))              # no room for T+5
    nosym = ev(symbol="XYZ")
    df = study([early, late, nosym], {"ABC": series([100.0] * 20)}, flat_index())
    assert pd.isna(df.iloc[0]["car_pre"]) and not pd.isna(df.iloc[0]["car_day"])   # DataFrame stores None as NaN
    assert pd.isna(df.iloc[1]["car_post"])
    assert pd.isna(df.iloc[2]["car_day"])
    assert len(df) == 3                                               # kept, so counts stay honest
    assert _car([100, 110], [100, 100], 0, 1) == pytest.approx(10.0)


def test_summary_groups_subtypes_buckets_and_results_proxy():
    up = [100.0] * 10 + [104.0] * 10                                  # +4% reaction: beat proxy
    dn = [100.0] * 10 + [97.0] * 10                                   # -3% reaction: miss proxy
    events = [ev(type="results", subtype="outcome", bucket="significant"),
              ev(symbol="DEF", type="results", subtype="outcome", bucket="significant"),
              ev(type="rating", subtype="upgrade", bucket="significant"),
              ev(type="order_win", bucket="major"), ev(type="order_win", bucket="minor")]
    closes = {"ABC": series(up), "DEF": series(dn)}
    df = study(events, closes, flat_index())
    s = summarise(df)
    names = list(s["group"])
    assert "results" in names and "rating / upgrade" in names
    assert "order_win [major]" in names and "order_win [minor]" in names
    beat = s[s["group"].str.startswith("results / beat")].iloc[0]
    miss = s[s["group"].str.startswith("results / miss")].iloc[0]
    assert beat["count"] == 1 and miss["count"] == 1
    assert "proxy" in beat["group"]
    row = s[s["group"] == "results"].iloc[0]
    assert row["count"] == 2 and row["day_mean"] == pytest.approx((4.0 - 3.0) / 2, abs=0.01)
    assert row["day_pos_pct"] == 50.0 and row["post_mean"] == pytest.approx(0.0)
    p = patterns(s)
    assert set(p) == {"results", "rating", "order_win"}
    assert p["results"]["count"] == 2 and p["results"]["day"] == row["day_mean"]
    print_table(s)                                                    # must not raise


def test_post_window_starts_at_the_t_plus_1_close():
    # +10% on T+1 (the reaction day the results proxy is measured on), then flat: post excludes it
    stock = [100.0] * 11 + [110.0] * 9
    r = study([ev()], {"ABC": series(stock)}, flat_index()).iloc[0]
    assert r["car_day"] == 0.0 and r["reaction"] == pytest.approx(10.0)
    assert r["car_post"] == pytest.approx(0.0)
    stock = [100.0] * 11 + [110.0] * 4 + [121.0] * 5                   # T+1 -> T+5: 110 -> 121
    assert study([ev()], {"ABC": series(stock)}, flat_index()).iloc[0]["car_post"] == pytest.approx(10.0)


def test_every_window_has_median_and_t_and_sized_types_always_show_buckets():
    stock = [100.0] * 10 + [104.0] * 10
    df = study([ev(), ev(symbol="DEF")], {"ABC": series(stock), "DEF": series(stock)}, flat_index())
    s = summarise(df)
    assert "order_win [major]" in list(s["group"])                    # one bucket only, still shown
    for w in ("pre", "day", "post"):
        assert {f"{w}_mean", f"{w}_median", f"{w}_pos_pct", f"{w}_t"} <= set(s.columns)
