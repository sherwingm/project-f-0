"""Fetch GIFT Nifty (NSE International Exchange) daily files and keep the INDEX FUTURES rows only.
Source: https://www.nseix.com/api/content/daily_report/G_T_DSP_INDEX_DDMMYYYY.csv  (daily settlement prices)
        https://www.nseix.com/api/content/daily_report/G_COMBINED_OI_DDMMYYYY.csv  (combined OI)
Public files linked from the nseix.com home page. Every weekday 2023-07-03 -> today is requested once (404 = no file: holiday / not published).
Resumable: days already in data/gift/progress.txt are skipped. Outputs (git-ignored): data/gift/gift_dsp_futures.csv, gift_oi_futures.csv.
Limits: the settlement price is the day's settlement, NOT the pre-open level; no intraday history exists on the site (the chart holds only the current session)."""
import csv
import os
import sys
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "data", "gift")
BASE = "https://www.nseix.com/api/content/daily_report/"


def get(name):
    """curl is used because Python's urllib times out against this site while curl works."""
    for k in range(3):
        try:
            r = subprocess.run(["curl", "-s", "-m", "90", "-A", "Mozilla/5.0", "-w", "\n%{http_code}", BASE + name], capture_output=True, timeout=120)
            body, _, code = r.stdout.decode("utf-8", "replace").rpartition("\n")
            if code == "404":
                return None
            if code == "200":
                return body
        except Exception:
            pass
        time.sleep(2 * (k + 1))
    return "ERROR"


def one(d):
    s = d.strftime("%d%m%Y")
    res = {"day": d}
    t = get(f"G_T_DSP_INDEX_{s}.csv")
    res["dsp"] = None if t is None else ("ERROR" if t == "ERROR" else [l for l in t.splitlines() if l.startswith(("DATE", "")) and ",FUTIDX," in l])
    t = get(f"G_COMBINED_OI_{s}.csv")
    res["oi"] = None if t is None else ("ERROR" if t == "ERROR" else [l for l in t.splitlines()[:1] + [l for l in t.splitlines() if l.startswith("FUTIDX,")]])
    time.sleep(0.2)
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    prog = os.path.join(OUT, "progress.txt")
    done = set(open(prog).read().split()) if os.path.exists(prog) else set()
    days, d = [], date(2023, 7, 3)
    while d <= date.today():
        if d.weekday() < 5 and d.isoformat() not in done:
            days.append(d)
        d += timedelta(days=1)
    print("days to fetch:", len(days), flush=True)
    fd = open(os.path.join(OUT, "gift_dsp_futures.csv"), "a", encoding="utf-8")
    fo = open(os.path.join(OUT, "gift_oi_futures.csv"), "a", encoding="utf-8")
    fp = open(prog, "a")
    n = 0
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(one, days):
            if r["dsp"] == "ERROR" or r["oi"] == "ERROR":
                print("ERROR", r["day"], flush=True)
                continue
            if r["dsp"]:
                fd.write("\n".join(r["dsp"]) + "\n")
            if r["oi"]:
                # first element is the header line of the OI file (date,total..): keep it as a marker row
                fo.write(f"#DAY,{r['day'].isoformat()},{r['oi'][0]}\n" + "\n".join(r["oi"][1:]) + "\n")
            fp.write(r["day"].isoformat() + "\n")
            fd.flush(); fo.flush(); fp.flush()
            n += 1
            if n % 50 == 0:
                print("done", n, r["day"], flush=True)
    print("finished", n, "days", flush=True)


if __name__ == "__main__":
    main()
