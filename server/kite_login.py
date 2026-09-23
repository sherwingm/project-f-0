"""Daily Kite Connect login: prints the login URL, exchanges the request_token for the day's
access_token and writes it to .env (KITE_ACCESS_TOKEN=...). Kite tokens expire every morning.

    KITE_API_KEY=... KITE_API_SECRET=... python -m server.kite_login
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def main() -> None:
    from kiteconnect import KiteConnect
    key, secret = os.getenv("KITE_API_KEY"), os.getenv("KITE_API_SECRET")
    if not (key and secret):
        sys.exit("set KITE_API_KEY and KITE_API_SECRET")
    kite = KiteConnect(api_key=key)
    print("1. Open and log in:", kite.login_url())
    print("2. After the redirect, copy the request_token from the URL.")
    request_token = input("request_token: ").strip()
    data = kite.generate_session(request_token, api_secret=secret)
    token = data["access_token"]
    env = Path(".env")
    text = env.read_text() if env.exists() else ""
    if re.search(r"^KITE_ACCESS_TOKEN=", text, re.M):
        text = re.sub(r"^KITE_ACCESS_TOKEN=.*$", f"KITE_ACCESS_TOKEN={token}", text, flags=re.M)
    else:
        text += f"\nKITE_ACCESS_TOKEN={token}\n"
    env.write_text(text)
    print("access token written to .env; restart the server (or export it) to use it")


if __name__ == "__main__":
    main()
