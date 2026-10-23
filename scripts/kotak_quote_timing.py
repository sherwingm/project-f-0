"""Read-only: how long Kotak quote calls take from this server (task 3 of the 24 Oct measurement work).

    set -a; . ./.env; set +a; .venv/bin/python scripts/kotak_quote_timing.py

Times 5 single-contract calls (quote_one, what the post-exit record used per closed trade) and 5 batched calls of 5
contracts (quote_many). Places nothing, changes nothing.
"""
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.config import settings  # noqa: E402
from server.kotak import KotakProvider, shared_session  # noqa: E402

p = KotakProvider(shared_session(settings), chain_calls_per_poll=0)
p.master.load()
fut = p.futures(["RELIANCE", "HDFCBANK", "INFY", "TCS", "SBIN"])
ts = [v[0] for v in fut.values()][:5]
one, many = [], []
for t in ts:
    a = time.perf_counter(); p.quote_one(t); one.append(time.perf_counter() - a)
for _ in range(5):
    a = time.perf_counter(); p.quote_many(ts); many.append(time.perf_counter() - a)
print(f"quote_one  x5: median {statistics.median(one) * 1000:.0f} ms, max {max(one) * 1000:.0f} ms")
print(f"quote_many(5) x5: median {statistics.median(many) * 1000:.0f} ms, max {max(many) * 1000:.0f} ms")
