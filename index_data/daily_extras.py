"""Nightly top-ups after the index recorder, so every dataset stays current (all on GitHub, no PC needed):

    KOTAK_CONSUMER_KEY=... UPSTOX_ANALYTICS_TOKEN=... INDEX_STORE=... python -m index_data.daily_extras [--weekly]

1. Index spot + India VIX, today's 1-minute candles (Kotak; VIX x100 fix applied) -> spot_1m/<name>/<YYYY-MM>.parquet.
2. Today's NSE daily OHLC of every index option and future (raw F&O bhavcopy) -> options_daily/<underlying>/<YYYY>.parquet.
   NSE may refuse a cloud runner on some nights; the next night's run tries again (restart-safe).
3. Weekly (Fridays, or --weekly): the Upstox expired-contract top-up for the expiries of the last 14 days (NIFTY,
   BANKNIFTY, SENSEX; contracts already on disk are skipped) and the India VIX daily file from yfinance.
Every step is independent: one failing does not stop the others. Result -> status.json "daily_extras".
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import date, timedelta

from .common import SMALL, STORE, Kotak, read_json, session_day, today_ist, write_json

log = logging.getLogger("index_data.daily_extras")


def main() -> None:
    ap = argparse.ArgumentParser(description="nightly top-ups: spot/VIX, daily OHLC, weekly Upstox")
    ap.add_argument("--weekly", action="store_true", help="run the weekly part now")
    ap.add_argument("--day", default=None, help="the session to top up (YYYY-MM-DD); default: session_day()")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    day, t0, out = (date.fromisoformat(a.day) if a.day else session_day()), time.monotonic(), {}
    k = None
    try:
        from .backfill_spot import backfill
        k = Kotak()
        out["spot_vix_1m"] = backfill(k, day, day)
    except Exception as exc:  # noqa: BLE001
        out["spot_vix_1m"] = {"error": str(exc)[:300]}
    try:
        from .bhavcopy_ohlc import run as ohlc
        out["options_daily"] = ohlc(day, day)
    except Exception as exc:  # noqa: BLE001
        out["options_daily"] = {"error": str(exc)[:300]}
    if a.weekly or day.weekday() == 4:
        try:
            from .upstox_expired import run as up
            out["upstox_topup"] = {u: up(u, (day - timedelta(days=14)).isoformat(), 40, False)
                                   for u in ("NIFTY", "BANKNIFTY", "SENSEX")}
        except Exception as exc:  # noqa: BLE001
            out["upstox_topup"] = {"error": str(exc)[:300]}
        try:
            from .backfill_spot import vix_daily
            out["vix_daily"] = vix_daily(k or Kotak())
        except Exception as exc:  # noqa: BLE001
            out["vix_daily"] = {"error": str(exc)[:300]}
    out.update(day=day.isoformat(), runtime_s=round(time.monotonic() - t0))
    st = read_json(SMALL / "status.json", {}) or {}
    write_json(SMALL / "status.json", {**st, "daily_extras": out})
    print(out)


if __name__ == "__main__":
    main()
