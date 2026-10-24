#!/usr/bin/env python3
"""Market-hours watchdog for the always-on VM (guides/17-always-on-host.md). Stdlib only; run by systemd every
minute (fo-scanner-watchdog.timer).

On an NSE session day between 09:17 and 15:29 IST it reads the server's /api/live. When the request fails, or the
live feed's last update (updated_at, HH:MM:SS IST) is older than STALE_SECONDS, it restarts fo-scanner.service, at
most once per COOLDOWN_SECONDS. Every check is one line on stdout (journalctl -u fo-scanner-watchdog).

Why: on 2026-10-21 the Render free server stopped polling 09:26-09:44 and 12:02-13:08; BAJFINANCE's -20 % stop then
sold at -40 % (ten minutes late). A stalled poller on the VM is restarted within about 3 minutes instead.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
APP = Path(__file__).resolve().parents[2]                  # the repo checkout (~/fo_scanner)
ENV, HOLIDAYS = APP / ".env", APP / "data" / "nse_holidays.json"
STATE = Path("/var/lib/fo-scanner-watchdog/last_restart")
URL = "http://127.0.0.1:8000/api/live"
STALE_SECONDS, COOLDOWN_SECONDS, START, END = 180, 600, "09:17", "15:29"


def env() -> dict[str, str]:
    out = {}
    for line in ENV.read_text().splitlines() if ENV.exists() else []:
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def session_day(now: datetime, extra: str) -> bool:
    if now.weekday() >= 5:
        return False
    days = set(x.strip() for x in extra.split(",") if x.strip())
    try:
        days |= set(json.loads(HOLIDAYS.read_text()).get("holidays") or [])
    except (OSError, ValueError):
        pass
    return now.date().isoformat() not in days


def stale(now: datetime, e: dict[str, str]) -> str | None:
    """None when the feed is fresh, else why it is not."""
    req = urllib.request.Request(URL)
    if e.get("PUBLIC_ACCESS", "false").lower() not in ("1", "true", "yes", "on"):
        tok = base64.b64encode(f"user:{e.get('APP_PASSWORD', '')}".encode()).decode()
        req.add_header("Authorization", "Basic " + tok)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
    except Exception as exc:  # noqa: BLE001 - any failure is a stall
        return f"request failed: {exc}"
    if not d.get("enabled", True):
        return None                                           # live feed switched off on purpose (DATA_PROVIDER=none)
    u = d.get("updated_at")
    if not u:
        return "no live update yet today"
    h, m, s = (int(x) for x in u.split(":"))
    age = (now - now.replace(hour=h, minute=m, second=s, microsecond=0)).total_seconds()
    return f"last live update {u} ({age:.0f} s ago)" if age > STALE_SECONDS else None


def main() -> int:
    now = datetime.now(IST)
    e = env()
    if not session_day(now, e.get("NSE_HOLIDAYS", "")) or not (START <= now.strftime("%H:%M") <= END):
        return 0
    why = stale(now, e)
    if why is None:
        print(f"{now:%H:%M:%S} ok")
        return 0
    last = float(STATE.read_text()) if STATE.exists() else 0.0
    if time.time() - last < COOLDOWN_SECONDS:
        print(f"{now:%H:%M:%S} STALE ({why}); restarted {time.time() - last:.0f} s ago, waiting")
        return 0
    print(f"{now:%H:%M:%S} STALE ({why}): restarting fo-scanner")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(str(time.time()))
    phone(e, f"⚠️ F&O scanner stalled at {now:%H:%M} ({why}). The watchdog is restarting it now.")
    return subprocess.call(["systemctl", "restart", "fo-scanner"])


def phone(e: dict[str, str], text: str) -> None:
    """A Telegram alert (server/alerts.py), when TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set; never fails."""
    tok, chat = e.get("TELEGRAM_BOT_TOKEN", ""), e.get("TELEGRAM_CHAT_ID", "")
    if not (tok and chat):
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=10).close()
    except Exception as exc:  # noqa: BLE001
        print(f"telegram alert not sent: {type(exc).__name__}")


if __name__ == "__main__":
    sys.exit(main())
