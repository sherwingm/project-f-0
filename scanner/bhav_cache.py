"""Fill the F&O bhavcopy cache (data/cache/fo_bhavcopy_YYYYMMDD.csv) for a date range. Resumable.

    python -m scanner.bhav_cache --since 2023-01-01            # up to today
    python -m scanner.bhav_cache --since 2023-01-01 --until 2024-12-31

Sessions are eod2's NIFTY 50 dates (so exchange holidays are never requested) plus the weekdays after
eod2's last date. A session already in the cache is skipped, so an interrupted run picks up where it
stopped. Downloads go through scanner.nse_fo.download_fo_bhavcopy, which reads the pre-2024-07-05 files in
NSE's old format and the later ones in UDiFF and caches both under the UDiFF column names. At most one
request a second. Dates that fail are listed at the end and in data/cache/bhav_cache_status.json, and are
tried again on the next run.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from .backtest_cheap_options import _read_index
from .build import ROOT
from .nse_fo import BhavcopyUnavailable, download_fo_bhavcopy

log = logging.getLogger("bhav_cache")
STATUS_FILE = "bhav_cache_status.json"


def cache_path(cache_dir: Path, day: date) -> Path:
    return cache_dir / f"fo_bhavcopy_{day:%Y%m%d}.csv"


def sessions(index_dates: list[date], since: date, until: date) -> list[date]:
    """eod2's sessions in [since, until], then every weekday after eod2's last date up to `until`."""
    out = [d for d in index_dates if since <= d <= until]
    x = max(index_dates[-1] + timedelta(days=1), since) if index_dates else since
    while x <= until:
        if x.weekday() < 5:
            out.append(x)
        x += timedelta(days=1)
    return out


def fill(days: list[date], cache_dir: Path, fetch: Callable[[date], object] | None = None,
         min_interval: float = 1.0, sleep: Callable[[float], None] = time.sleep,
         clock: Callable[[], float] = time.monotonic) -> dict:
    """Download every day not yet cached, one request per `min_interval` seconds at most."""
    fetch = fetch or (lambda d: download_fo_bhavcopy(d, cache_dir=cache_dir))
    todo = [d for d in days if not cache_path(cache_dir, d).exists()]
    done, failed, last = [], {}, None
    for n, d in enumerate(todo, 1):
        if last is not None:
            wait = min_interval - (clock() - last)
            if wait > 0:
                sleep(wait)
        last = clock()
        try:
            fetch(d)
            done.append(d)
        except BhavcopyUnavailable as exc:
            failed[d.isoformat()] = str(exc)
        except Exception as exc:  # noqa: BLE001  (network errors, a changed layout: report, carry on)
            failed[d.isoformat()] = f"{type(exc).__name__}: {exc}"
        if n % 25 == 0:
            log.info("%s: %d of %d downloaded, %d failed", d, len(done), len(todo), len(failed))
    cached = [d for d in days if cache_path(cache_dir, d).exists()]
    return {"sessions": len(days), "cached": len(cached), "downloaded": len(done), "failed": failed,
            "first": cached[0].isoformat() if cached else None, "last": cached[-1].isoformat() if cached else None}


def main() -> None:
    ap = argparse.ArgumentParser(description="fill the F&O bhavcopy cache for a date range (resumable, 1 request/s)")
    ap.add_argument("--since", type=date.fromisoformat, default=date(2023, 1, 1))
    ap.add_argument("--until", type=date.fromisoformat, default=None, help="default: yesterday")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    until = a.until or date.today() - timedelta(days=1)
    idx = [t.date() for t in _read_index(a.eod2_dir).index]
    days = sessions(idx, a.since, until)
    a.cache_dir.mkdir(parents=True, exist_ok=True)
    log.info("%d sessions %s to %s; %d already cached", len(days), a.since, until,
             sum(cache_path(a.cache_dir, d).exists() for d in days))
    r = fill(days, a.cache_dir)
    r.update({"since": a.since.isoformat(), "until": until.isoformat(), "run_at": datetime.now().isoformat(timespec="seconds")})
    (a.cache_dir / STATUS_FILE).write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(f"{r['cached']} of {r['sessions']} sessions cached ({r['first']} to {r['last']}); "
          f"{r['downloaded']} downloaded this run; {len(r['failed'])} failed")
    for d, why in sorted(r["failed"].items()):
        print(f"  {d}: {why}")


if __name__ == "__main__":
    main()
