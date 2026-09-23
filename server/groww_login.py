"""One-off check of the Groww TOTP login: generates an access token and prints its first characters.

    GROWW_TOTP_TOKEN=... GROWW_TOTP_SECRET=... python -m server.groww_login

The server does this itself at start-up (and again if a call fails with an auth error), so this
is only for confirming the key pair works before you turn on BROKER=groww.
"""
from __future__ import annotations

import os
import sys

from server.groww import groww_access_token


def main() -> None:
    token, secret = os.getenv("GROWW_TOTP_TOKEN"), os.getenv("GROWW_TOTP_SECRET")
    if not (token and secret):
        sys.exit("set GROWW_TOTP_TOKEN and GROWW_TOTP_SECRET (Groww Cloud API Keys page -> Generate TOTP token)")
    access = groww_access_token(token, secret, None)
    print("access token OK:", access[:12] + "…", f"({len(access)} chars)")


if __name__ == "__main__":
    main()
