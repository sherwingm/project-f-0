"""Optional Upstox OAuth login (fallback). The free Analytics Token already reaches the expired-instruments API
(DATA_ACCESS_AUDIT.md), so this is only needed if that ever changes.

    UPSTOX_API_KEY=... UPSTOX_API_SECRET=... UPSTOX_REDIRECT_URI=... python -m index_data.upstox_login

1. Prints the login URL; open it, log in, and copy the `code` from the address you are sent back to.
2. Paste the code; the access token (valid until the next morning, about 03:30 IST) is saved to
   data/index/.upstox_token (git-ignored). Run it yourself: the secrets are typed by you, never stored in the repo.
"""
from __future__ import annotations

import os
import sys
from urllib.parse import urlencode

import requests

from .common import SMALL

AUTH = "https://api.upstox.com/v2/login/authorization/dialog"
TOKEN = "https://api.upstox.com/v2/login/authorization/token"


def main() -> None:
    key, secret, redirect = (os.getenv(v, "") for v in ("UPSTOX_API_KEY", "UPSTOX_API_SECRET", "UPSTOX_REDIRECT_URI"))
    if not (key and secret and redirect):
        raise SystemExit("set UPSTOX_API_KEY, UPSTOX_API_SECRET and UPSTOX_REDIRECT_URI (your Upstox app's settings)")
    print("Open this, log in, then copy the `code=` value from the page you land on:\n")
    print(AUTH + "?" + urlencode({"response_type": "code", "client_id": key, "redirect_uri": redirect}))
    code = input("\ncode: ").strip()
    r = requests.post(TOKEN, headers={"Accept": "application/json"}, timeout=30,
                      data={"code": code, "client_id": key, "client_secret": secret, "redirect_uri": redirect,
                            "grant_type": "authorization_code"})
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    tok = body.get("access_token")
    if not tok:
        sys.exit(f"login failed (HTTP {r.status_code}): {body.get('errors') or r.text[:200]}")
    SMALL.mkdir(parents=True, exist_ok=True)
    (SMALL / ".upstox_token").write_text(tok, encoding="utf-8")
    print("saved to data/index/.upstox_token (valid until about 03:30 IST tomorrow)")


if __name__ == "__main__":
    main()
