from scanner import fade_timeline as T


def bars(prices):
    """One-minute stock bars from 09:15, open = high = low = close = the given price (simple paths)."""
    out = []
    for i, p in enumerate(prices):
        h, m = divmod(9 * 60 + 15 + i, 60)
        out.append((f"{h:02d}:{m:02d}", p, p, p, p))
    return out


def test_proxy_maps_the_option_range_onto_the_stock_and_inverts_for_puts():
    b = bars([100, 98, 96, 100, 102])                      # stock range 96-102 = 6
    p = T.proxy(b, "PE", o_open=10.0, o_high=13.0, o_low=7.0)   # option range 6: b = -1
    assert [round(x[4], 2) for x in p] == [10.0, 12.0, 14.0, 10.0, 8.0]
    c = T.proxy(b, "CE", o_open=10.0, o_high=13.0, o_low=7.0)
    assert [round(x[4], 2) for x in c] == [10.0, 8.0, 6.0, 10.0, 12.0]
    assert T.proxy(bars([100, 100]), "PE", 10.0, 11.0, 9.0) is None      # the stock did not move
    deep = T.proxy(bars([100, 90, 80]), "PE", o_open=1.0, o_high=1.5, o_low=0.0)   # a put pushed below zero is floored
    assert min(x[3] for x in T.proxy(bars([100, 80, 60]), "CE", 1.0, 2.0, 0.0)) == T.FLOOR and deep is not None


def test_exits_stop_target_trail_and_1520():
    path = [("09:15", 10, 10, 10, 10), ("09:16", 10, 12, 10, 12), ("09:17", 12, 12, 7.5, 8), ("15:20", 9, 9, 9, 9)]
    assert T.run_exit(path, 10.0, T.Exit("x", "", sl=0.80)) == (8.0, "stop", "09:17")
    assert T.run_exit(path, 10.0, T.Exit("x", "", tp=1.15)) == (11.5, "target", "09:16")
    assert T.run_exit(path, 10.0, T.Exit("x", "", trail=0.75)) == (9.0, "trail", "09:17")     # 0.75 x the 12 peak
    assert T.run_exit(path, 10.0, T.Exit("x", "")) == (9, "15:20", "15:20")
    assert T.run_exit(path, 10.0, T.Exit("x", "", sl=0.80, sl_from="09:45"))[1] == "15:20"     # stop not armed yet
    both = [("09:15", 10, 14, 7, 10), ("15:20", 10, 10, 10, 10)]
    assert T.run_exit(both, 10.0, T.Exit("x", "", sl=0.8, tp=1.3))[1] == "stop"              # same minute: stop first


def test_timeline_finds_peak_dip_order_and_first_touches():
    path = [("09:15", 10, 10, 10, 10), ("09:16", 10, 13.5, 10, 13), ("10:30", 13, 13, 7.5, 8), ("15:20", 9, 9, 9, 9)]
    tl = T.timeline(path, 10.0)
    assert (tl["peak_time"], tl["dip_time"], tl["peak_first"]) == ("09:16", "10:30", True)
    assert (tl["touch_p30"], tl["touch_m20"], tl["touch_p50"]) == ("09:16", "10:30", None)
    assert T.minutes_after_open("10:30") == 75 and T.half_hour("10:47") == "10:30"
