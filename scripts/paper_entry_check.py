"""Read-only check: was each paper entry price inside the contract's traded range in its entry minute?
(strategies/S1_fade_decline_recovery.md, addendum). Run on the server, outside market hours:

    set -a; . ./.env; set +a; .venv/bin/python scripts/paper_entry_check.py

Reads data/paper_ledger.json, asks Kotak's history for each contract's 1-minute candles on its entry day, prints one
line per position. Changes nothing. A fill inside the range is not proof the ask was there.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.config import settings  # noqa: E402
from server.kotak import KotakProvider, shared_session  # noqa: E402

L = json.loads(Path("data/paper_ledger.json").read_text())
prov = KotakProvider(shared_session(settings), chain_calls_per_poll=0)
print(f"{'symbol':11} {'contract':22} {'entry at':19} {'fill':>7} {'min':>5} {'low':>7} {'high':>7} {'open':>7} verdict")
for p in L["positions"] + L["closed"]:
    t = datetime.fromisoformat(p["opened_at"])
    fill = p["entry"]["price"]
    try:
        bars = prov.history("NFO:" + p["tradingsymbol"], 1, t.date().isoformat())
    except Exception as exc:  # noqa: BLE001
        print(f"{p['symbol']:11} {p['tradingsymbol']:22} {p['opened_at'][:19]} {fill:7.2f} unresolved ({type(exc).__name__})")
        continue
    m = [b for b in bars if datetime.fromtimestamp(b["time"], t.tzinfo).strftime("%H:%M") == t.strftime("%H:%M")]
    if not m:
        print(f"{p['symbol']:11} {p['tradingsymbol']:22} {p['opened_at'][:19]} {fill:7.2f} unresolved (no candle)")
        continue
    b = m[0]
    v = "consistent" if b["low"] - 1e-9 <= fill <= b["high"] + 1e-9 else "OUTSIDE range"
    print(f"{p['symbol']:11} {p['tradingsymbol']:22} {p['opened_at'][:19]} {fill:7.2f} {t.strftime('%H:%M'):>5} "
          f"{b['low']:7.2f} {b['high']:7.2f} {b['open']:7.2f} {v}")
