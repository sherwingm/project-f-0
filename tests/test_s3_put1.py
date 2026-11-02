"""S3 PUT1 day trade (scanner/s3_put1.py)."""
from scanner import s3_put1 as P
from tests.test_s3_b2 import day


def test_put_only_when_the_first_breakout_is_down():
    d = day([100] * 15 + [98] * 20 + [97] * 400)                 # first break below 99 at 09:30, held to 15:15
    t = P.day_trade(d, 15, "PE")
    assert (t["signal"], t["entry"], t["exit"]) == ("09:30", "09:31", "15:15")
    assert abs(t["move_pct"] - (1 - 97 / 98) * 100) < 1e-9          # fall from 98 to 97, positive for a put
    assert P.day_trade(d, 15, "CE") is None
    up = day([100] * 15 + [102] * 5 + [98] * 400)                 # first breakout is upward: no put that day
    assert P.day_trade(up, 15, "PE") is None


def test_failure_exit_for_the_side_report():
    d = day([100] * 15 + [98] * 10 + [100] * 400)
    t = P.day_trade(d, 15, "PE", fail_exit=True)
    assert t["exit"] == "09:41" and t["move_pct"] < 0               # back inside at 09:40, out the minute after
