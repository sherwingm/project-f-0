"""Peak study: the exit simulators on synthetic option paths, the peak stats and the result-quality labels."""
from scanner import peak_study as ps

E = 10.0
RISE = [12.0, 16.0, 22.0, 18.0, 13.0, 11.0, 10.5, 10.0, 9.0, 8.0]      # peaks at day 3 then fades
CRASH = [8.0, 4.9, 6.0]


def test_live_rules_stop_decay_and_t1():
    assert ps.simulate(CRASH, E, "live") == (1, 4.85, "stop")
    i, px, why = ps.simulate(RISE, E, "live")
    assert (i + 1, why) == (8, "decay")                              # 5 closes after the day-3 high
    assert ps.simulate([11.0, 12.0], E, "live")[2] == "t1"


def test_targets_trails_fixed_and_combos():
    assert ps.simulate(RISE, E, "target:0.5")[:1] == (1,) and ps.simulate(RISE, E, "target:1.0")[2] == "target"
    assert ps.simulate(RISE, E, "target:2.0")[2] == "decay"          # never reached: the live rules decide
    i, px, why = ps.simulate(RISE, E, "trail:0.3")
    assert (i + 1, why) == (5, "trail") and px == 12.95               # 13 <= 22 * 0.7 = 15.4
    assert ps.simulate(RISE, E, "fixed:3") == (2, 21.95, "fixed")
    assert ps.simulate(CRASH, E, "fixed:3")[2] == "stop"
    assert ps.simulate(RISE, E, "combo:1.0:0.3") == (2, 21.95, "target")
    assert ps.simulate(RISE, E, "combo:2.0:0.3")[2] == "trail"
    i, px, why = ps.simulate(RISE, E, "half:0.5:0.4")
    assert why == "half+trail" and px == round((15.95 + 12.95) / 2, 2)    # half at 16 (day 2), rest at 13 (day 5)


def test_peak_stats_and_labels():
    p = ps.peak_stats(RISE, E)
    assert (p["peak_pct"], p["peak_day"], p["first_day_50"], p["first_day_100"]) == (120.0, 3, 2, 3)
    assert p["dd_after_peak_pct"] == round((8.0 / 22.0 - 1) * 100, 2) and p["next_after_50"] == 60.0
    assert ps.quarter_of("2025-07-18") == "2025-06-30" and ps.quarter_of("2026-01-16") == "2025-12-31"
    assert ps.quarter_of("2025-04-02") == "2025-03-31"
    assert ps.beat_cat(2.5) == "<3%" and ps.beat_cat(4.9) == "3-5%" and ps.beat_cat(5.0) == ">5%"
    fin = {"X": {"basis": "consolidated", "quarters": {"2025-06-30": {"net_profit": -5.0, "revenue": 100.0, "eps": -1},
                                                        "2025-03-31": {"net_profit": 10.0, "revenue": 90.0, "eps": 2},
                                                        "2024-06-30": {"net_profit": 8.0, "revenue": 80.0, "eps": 1.6}}}}
    q = ps.result_quality(fin, "X", "2025-07-20")
    assert q["revenue_qoq"] == 11.1 and q["revenue_yoy"] == 25.0 and q["net_profit_qoq"] == -150.0
    assert q["turned_to_loss"] and q["loss_quarter"] and q["revenue_yoy_cat"] == "up" and q["net_profit_qoq_cat"] == "down"
    assert ps.result_quality(fin, "X", "2025-04-20")["net_profit_qoq"] is None          # the quarter before is unknown
