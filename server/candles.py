"""Chart candles from the live feed's intraday ticks (server/live.py: LiveFeed.history / opt_history).

A tick is (epoch seconds, price, cumulative day volume, average traded price, ...). Candles are tf-minute buckets
aligned to the clock: open / high / low / close from the ticks' prices; volume = the day volume at the bucket's last
tick minus the day volume at the previous bucket's last tick when that bucket is the one just before (else, after
a gap in polling, only the volume seen inside the bucket, so a gap never lands as one giant bar); atp = the
average traded price at the bucket's last tick. Prices are only as fine as the poll (30-45 s): a candle's high
and low are the highest and lowest polled prices, not the exchange's.
"""
from __future__ import annotations


def candles(ticks: list[tuple], tf_minutes: int = 1, price: int = 1, volume: int = 2, atp: int = 3) -> list[dict]:
    """[{time, open, high, low, close, volume, atp}] with `time` the bucket start (epoch seconds, UTC)."""
    step = max(1, int(tf_minutes)) * 60
    out: list[dict] = []
    last_vol: dict[int, float] = {}                # bucket start -> day volume at its last tick
    for t in sorted(ticks, key=lambda x: x[0]):
        px = t[price]
        if px is None:
            continue
        b = int(t[0]) // step * step
        v = t[volume] if volume < len(t) else None
        a = t[atp] if atp < len(t) else None
        if out and out[-1]["time"] == b:
            c = out[-1]
            c["high"], c["low"], c["close"] = max(c["high"], px), min(c["low"], px), px
        else:
            c = {"time": b, "open": px, "high": px, "low": px, "close": px, "volume": None, "atp": None, "_v0": v}
            out.append(c)
        if a is not None:
            c["atp"] = a
        if v is not None:
            if c["_v0"] is None:
                c["_v0"] = v
            last_vol[b] = v
    for i, c in enumerate(out):
        end = last_vol.get(c["time"])
        prev = out[i - 1]["time"] if i else None
        if end is None:
            c["volume"] = None
        elif prev is not None and prev == c["time"] - step and last_vol.get(prev) is not None:
            c["volume"] = max(0.0, end - last_vol[prev])
        else:
            c["volume"] = max(0.0, end - (c["_v0"] or end))
        del c["_v0"]
    return out
