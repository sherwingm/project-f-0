"""Record-only 1-second candles of NIFTY from the Upstox stream, the same way the stock options are recorded.

The stock options get 1-second candles while the trading loops ask about them (server/upstox_stream.py Candles). For
S3 research (index options; strategies/S3_*) this keeps NIFTY watched the whole session instead:

    the NIFTY 50, Nifty Bank and India VIX indices (last price only: the index feed has no depth or volume);
    the nearest NIFTY future (it has the volume the index lacks);
    NIFTY CE and PE of the EXPIRIES nearest weekly expiries, BAND strikes either side of the at-the-money strike.

Strikes follow the spot during the day; every contract watched once stays watched until the close, so a strike the
market moved away from keeps a full day. Rows go to data/candles_1s_index/<date>.jsonl (same row format as
data/candles_1s); earlier days are gzipped on the first tick of a new day. No orders, no paper trades, no effect on
S1 / S2: it only adds subscriptions (well inside the 2,000-key cap) and writes its own file.
"""
from __future__ import annotations

import gzip
import logging
import shutil
import threading
from datetime import date, datetime, time
from pathlib import Path

from server.upstox_stream import CANDLES_INDEX

log = logging.getLogger(__name__)
INDICES = {"NSE_INDEX|Nifty 50": "NIFTY 50", "NSE_INDEX|Nifty Bank": "NIFTY BANK", "NSE_INDEX|India VIX": "INDIA VIX"}
SPOT_KEY = "NSE_INDEX|Nifty 50"
STEP, BAND, EXPIRIES = 50, 10, 2
EVERY = 20.0                     # seconds between refreshes (a watch lasts WATCH_FOR = 120 s)
OPEN, CLOSE = time(9, 14), time(15, 31)


def option_pairs(nifty: dict[tuple, str], spot: float, today: date) -> dict[str, str]:
    """{instrument key: label} of the nearest future and the CE / PE within BAND strikes of ATM, EXPIRIES expiries."""
    t = today.isoformat()
    exps = sorted({e for e, typ, _ in nifty if typ in ("CE", "PE") and e >= t})[:EXPIRIES]
    futs = sorted(e for e, typ, _ in nifty if typ == "FUT" and e >= t)
    out = {nifty[(futs[0], "FUT", None)]: f"NIFTY FUT {futs[0]}"} if futs else {}
    atm = round(spot / STEP) * STEP
    for e in exps:
        for k in range(atm - BAND * STEP, atm + (BAND + 1) * STEP, STEP):
            for side in ("CE", "PE"):
                ik = nifty.get((e, side, float(k)))
                if ik:
                    out[ik] = f"NIFTY {e} {k} {side}"
    return out


def gzip_old(folder: Path, today: date) -> int:
    """Gzip every <date>.jsonl before today in folder; returns the files done."""
    n = 0
    for f in sorted(folder.glob("*.jsonl")):
        if f.stem >= today.isoformat():
            continue
        with open(f, "rb") as src, gzip.open(f.with_suffix(".jsonl.gz"), "wb") as dst:
            shutil.copyfileobj(src, dst)
        f.unlink()
        n += 1
    return n


class IndexRecorder:
    def __init__(self, stream, upstox, data_dir):
        self.stream, self.upstox, self.folder = stream, upstox, Path(data_dir) / CANDLES_INDEX
        self.day: date | None = None
        self.pairs: dict[str, str] = {}
        self._last = 0.0

    def tick(self, now: datetime) -> None:
        if now.date() != self.day:
            self.day, self.pairs = now.date(), {}
            threading.Thread(target=self._gzip, args=(now.date(),), name="index-gzip", daemon=True).start()
        if now.weekday() >= 5 or not OPEN <= now.time() <= CLOSE or now.timestamp() - self._last < EVERY:
            return
        self._last = now.timestamp()
        new = dict(INDICES)
        spot = ((self.stream.get(SPOT_KEY) or {}).get("ltpc") or {}).get("ltp")
        if spot and self.upstox._loaded:
            new.update(option_pairs(self.upstox._nifty, float(spot), now.date()))
        if len(self.pairs) < len(self.pairs | new):
            log.info("index recorder: %d contracts watched", len(self.pairs | new))
        self.pairs.update(new)
        self.stream.want(list(self.pairs))
        self.stream.watch(self.pairs, group="index")

    def _gzip(self, today: date) -> None:
        try:
            if self.folder.exists():
                n = gzip_old(self.folder, today)
                if n:
                    log.info("index recorder: gzipped %d day file(s)", n)
        except Exception as exc:  # noqa: BLE001 - recording goes on; the file stays as plain jsonl
            log.warning("index recorder gzip: %s", exc)
