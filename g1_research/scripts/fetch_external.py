"""Fetch the public data for g1_research/EXTERNAL_PREREG.md: NSE participant-wise OI (one file per session) and GDELT news tone.
Read-only public sources, polite pacing. Output: g1_research/data/external/. Re-runnable (skips files already saved)."""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "external")
UA = {"User-Agent": "Mozilla/5.0"}


def get(url, tries=3, wait=2.0):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(wait * (i + 1))
        except Exception:  # noqa: BLE001
            time.sleep(wait * (i + 1))
    return b""


def participants():
    d0, d1 = date(2021, 9, 1), date(2026, 11, 6)
    os.makedirs(os.path.join(OUT, "participant_oi"), exist_ok=True)
    got = miss = 0
    d = d0
    while d <= d1:
        if d.weekday() < 5:
            f = os.path.join(OUT, "participant_oi", f"{d.isoformat()}.csv")
            if not os.path.exists(f):
                b = get(f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{d:%d%m%Y}.csv")
                if b:
                    open(f, "wb").write(b)
                    got += 1
                else:
                    miss += 1
                time.sleep(0.25)
        d += timedelta(days=1)
    print("participant files saved this run:", got, "| not available (holiday / error):", miss, flush=True)


def gdelt():
    os.makedirs(os.path.join(OUT, "gdelt"), exist_ok=True)
    q = "(Nifty OR Sensex OR \"Indian stocks\")".replace(" ", "%20").replace('"', "%22")
    for mode in ("timelinetone", "timelinevolraw"):
        for yr in range(2021, 2027):
            f = os.path.join(OUT, "gdelt", f"{mode}_{yr}.json")
            if os.path.exists(f):
                continue
            s, e = f"{yr}0101000000", f"{yr}1231235959" if yr < 2026 else "20261107000000"
            if yr == 2021:
                s = "20210901000000"
            url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={q}&mode={mode}&format=json&startdatetime={s}&enddatetime={e}"
            b = get(url, tries=4, wait=6)
            if b and b.strip().startswith(b"{"):
                open(f, "wb").write(b)
                print("gdelt", mode, yr, len(b), flush=True)
            else:
                print("gdelt FAILED", mode, yr, (b or b"")[:120], flush=True)
            time.sleep(7)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "gdelt"):
        gdelt()
    if which in ("all", "participants"):
        participants()
