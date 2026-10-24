"""Phone alerts through a Telegram bot (the user, 2026-10-24: "Yes, Telegram bot").

    send(text, key=None, every=900)   queue one message; a repeated key is sent at most once per `every` seconds

Off (nothing sent, nothing logged) unless TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are both set in the server's .env.
Sending runs on its own thread with a 10 s timeout: an alert can never hold up a trading check, and a failed send
is one warning line in the log, never an error. Messages carry prices and P&L only, never a credential.

Setup (once): create a bot with @BotFather, put TELEGRAM_BOT_TOKEN=<token> in ~/fo_scanner/.env, send the bot any
message from your phone, then
    python3 -m server.alerts --chat-id     prints the chat id(s) that wrote to the bot (put it in TELEGRAM_CHAT_ID)
    python3 -m server.alerts --test        sends a test message
"""
from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)
API = "https://api.telegram.org/bot{token}/{method}"

_q: queue.Queue = queue.Queue(maxsize=200)
_last: dict[str, float] = {}
_lock = threading.Lock()
_worker: threading.Thread | None = None


def _cfg() -> tuple[str, str]:
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip(), os.getenv("TELEGRAM_CHAT_ID", "").strip()


def enabled() -> bool:
    tok, chat = _cfg()
    return bool(tok and chat)


def _post(text: str) -> bool:
    tok, chat = _cfg()
    data = urllib.parse.urlencode({"chat_id": chat, "text": text[:4000], "disable_web_page_preview": "true"}).encode()
    try:
        with urllib.request.urlopen(API.format(token=tok, method="sendMessage"), data=data, timeout=10) as r:
            return bool(json.load(r).get("ok"))
    except Exception as exc:  # noqa: BLE001 - an alert must never break anything
        log.warning("telegram alert not sent: %s", type(exc).__name__)
        return False


def _run() -> None:
    while True:
        text = _q.get()
        _post(text)
        time.sleep(1.1)                                   # Telegram: about one message a second per chat


def send(text: str, key: str | None = None, every: float = 900.0) -> bool:
    """Queue `text` for the phone. With `key`, the same key goes out at most once per `every` seconds."""
    global _worker
    if not enabled():
        return False
    with _lock:
        now = time.monotonic()
        if key is not None:
            if now - _last.get(key, -1e18) < every:
                return False
            _last[key] = now
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_run, name="telegram-alerts", daemon=True)
            _worker.start()
    try:
        _q.put_nowait(text)
    except queue.Full:
        return False
    return True


def _load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8").read().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main(argv: list[str]) -> int:
    _load_env()
    tok, chat = _cfg()
    if not tok:
        print("TELEGRAM_BOT_TOKEN is not set in .env")
        return 1
    if "--chat-id" in argv:
        with urllib.request.urlopen(API.format(token=tok, method="getUpdates"), timeout=15) as r:
            ups = json.load(r).get("result") or []
        ids = sorted({str((u.get("message") or {}).get("chat", {}).get("id")) for u in ups if u.get("message")})
        print("\n".join(ids) if ids else "no messages yet: send the bot any message from your phone, then run again")
        return 0
    if "--test" in argv:
        if not chat:
            print("TELEGRAM_CHAT_ID is not set in .env")
            return 1
        print("sent" if _post("F&O scanner: test alert. Alerts are working.") else "not sent (see the warning)")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
