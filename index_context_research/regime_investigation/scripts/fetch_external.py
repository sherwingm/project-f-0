"""Download the extra public data approved by the user on 17 Nov 2026 for the regime investigation. Resumable; polite; curl-based (urllib times out on nseix.com).
Modes (run one per process):
  gift     NSE IX GIFT futures bhavcopy (open / high / low / close / previous settlement), weekdays 2023-07-03 -> today  -> external_data/gift_bhavcopy_futures.csv
  indices  NSE daily closes of ALL NSE indices (sector indices, VIX ...), weekdays 2018-01-01 -> today                  -> external_data/nse_index_closes.csv
  breadth  NSE full equity bhavcopy, breadth aggregates per day (advances, declines, turnover shares, delivery %), 2021-10-01 -> today -> external_data/nse_breadth_daily.csv
  yahoo    Yahoo chart API: Asian and US indices, US VIX, dollar index, US yields, crude, gold, USD/INR (daily 2018 -> today), ES / NQ futures hourly (2 years) -> external_data/yahoo/*.csv
Each mode writes progress to external_data/progress_<mode>.txt so a restart skips finished days. Raw downloads are not kept (only the compact outputs). Public files; no personal data sent."""
import csv
import io
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "external_data")
UA = "Mozilla/5.0"   # a longer custom user-agent made the NSE / NSE IX servers stall; the plain one works
TODAY = date.today()


def curl(url, timeout=90, headers=()):
    for k in range(3):
        try:
            cmd = ["curl", "-s", "-m", str(timeout), "-A", UA, "-w", "\n%{http_code}"]
            for h in headers:
                cmd += ["-H", h]
            r = subprocess.run(cmd + [url], capture_output=True, timeout=timeout + 30)
            body, _, code = r.stdout.decode("utf-8", "replace").rpartition("\n")
            if code == "404":
                return None
            if code == "200":
                return body
        except Exception:
            pass
        time.sleep(2 * (k + 1))
    return "ERROR"


def weekdays(a, b):
    d = a
    while d <= b:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def run_days(mode, days, worker, outfile, header):
    os.makedirs(OUT, exist_ok=True)
    prog = os.path.join(OUT, f"progress_{mode}.txt")
    done = set(open(prog).read().split()) if os.path.exists(prog) else set()
    todo = [d for d in days if d.isoformat() not in done]
    print(mode, "days to fetch:", len(todo), flush=True)
    new = not os.path.exists(outfile)
    fo = open(outfile, "a", encoding="utf-8", newline="")
    w = csv.writer(fo)
    if new:
        w.writerow(header)
    fp = open(prog, "a")
    n = errs = 0
    with ThreadPoolExecutor(3) as ex:
        for d, rows in zip(todo, ex.map(worker, todo)):
            if rows == "ERROR":
                errs += 1
                print("ERROR", d, flush=True)
                continue
            for r in rows or []:
                w.writerow(r)
            fp.write(d.isoformat() + "\n")
            fo.flush()
            fp.flush()
            n += 1
            if n % 100 == 0:
                print("done", n, d, "errors", errs, flush=True)
    print("finished", mode, n, "days, errors", errs, flush=True)


def gift_worker(d):
    t = curl(f"https://www.nseix.com/api/content/daily_report/G_T_Bhavcopy_FO_{d.strftime('%d%m%y')}.CSV")
    if t is None or t == "ERROR":
        return t
    rows = []
    for line in t.splitlines()[1:]:
        if line.startswith("FUTIDX"):
            p = line.split(",")
            if len(p) >= 12:
                rows.append([d.isoformat()] + p[:12])
        time.sleep(0)
    time.sleep(0.2)
    return rows


def indices_worker(d):
    t = curl(f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{d.strftime('%d%m%Y')}.csv", 60)
    if t is None or t == "ERROR":
        return t
    rows = list(csv.reader(t.splitlines()))[1:]
    time.sleep(0.15)
    return [[d.isoformat()] + r[:13] for r in rows if len(r) >= 6]


def breadth_worker(d):
    t = curl(f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{d.strftime('%d%m%Y')}.csv", 90)
    if t is None or t == "ERROR":
        return t
    adv = dec = unch = 0
    tov_adv = tov_dec = tov_all = 0.0
    deliv = []
    n = 0
    for p in csv.reader(t.splitlines()):
        if len(p) < 15 or p[0].strip() == "SYMBOL" or p[1].strip() != "EQ":
            continue
        try:
            prev, close, tov = float(p[3]), float(p[8]), float(p[11])
        except ValueError:
            continue
        n += 1
        tov_all += tov
        if close > prev:
            adv += 1
            tov_adv += tov
        elif close < prev:
            dec += 1
            tov_dec += tov
        else:
            unch += 1
        try:
            deliv.append(float(p[14]))
        except ValueError:
            pass
    if n == 0:
        return []
    time.sleep(0.2)
    return [[d.isoformat(), n, adv, dec, unch, round(tov_adv / tov_all, 4) if tov_all else "", round(tov_dec / tov_all, 4) if tov_all else "", round(tov_all, 1),
             round(sum(deliv) / len(deliv), 2) if deliv else ""]]


YAHOO_DAILY = {"N225": "^N225", "HSI": "^HSI", "SSEC": "000001.SS", "KOSPI": "^KS11", "TWII": "^TWII", "ASX200": "^AXJO", "IXIC": "^IXIC", "GSPC": "^GSPC", "VIX_US": "^VIX",
               "US10Y": "^TNX", "DXY": "DX-Y.NYB", "WTI": "CL=F", "BRENT": "BZ=F", "GOLD": "GC=F", "USDINR": "USDINR=X", "NSEI": "^NSEI", "ES_F": "ES=F", "NQ_F": "NQ=F"}
YAHOO_HOURLY = {"ES_F": "ES=F", "NQ_F": "NQ=F", "USDINR": "USDINR=X"}


def yahoo():
    os.makedirs(os.path.join(OUT, "yahoo"), exist_ok=True)
    p1, p2 = int(datetime(2018, 1, 1, tzinfo=timezone.utc).timestamp()), int(datetime.now(timezone.utc).timestamp())
    for name, sym in YAHOO_DAILY.items():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym.replace('^', '%5E')}?period1={p1}&period2={p2}&interval=1d&events=history"
        t = curl(url, 90)
        save_yahoo(name, t, "1d")
        time.sleep(1.5)
    for name, sym in YAHOO_HOURLY.items():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym.replace('^', '%5E')}?range=2y&interval=60m"
        t = curl(url, 90)
        save_yahoo(name, t, "60m")
        time.sleep(1.5)


def save_yahoo(name, t, interval):
    if not t or t == "ERROR":
        print("yahoo", name, interval, "FAILED", flush=True)
        return
    try:
        j = json.loads(t)["chart"]["result"][0]
        ts = j["timestamp"]
        q = j["indicators"]["quote"][0]
        off = j["meta"].get("gmtoffset", 0)
        path = os.path.join(OUT, "yahoo", f"{name}_{interval}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["timestamp_utc", "local_offset_s", "open", "high", "low", "close", "volume"])
            for i, s in enumerate(ts):
                w.writerow([datetime.fromtimestamp(s, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), off, q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i]])
        print("yahoo", name, interval, len(ts), "rows", flush=True)
    except Exception as e:
        print("yahoo", name, interval, "PARSE FAIL", str(e)[:80], flush=True)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "gift":
        run_days("gift", list(weekdays(date(2023, 7, 3), TODAY)), gift_worker, os.path.join(OUT, "gift_bhavcopy_futures.csv"),
                 ["trade_date", "contract", "prev_settle", "open", "high", "low", "close", "settlement", "net_change", "oi", "traded_qty", "trades", "traded_value"])
    elif mode == "indices":
        run_days("indices", list(weekdays(date(2018, 1, 1), TODAY)), indices_worker, os.path.join(OUT, "nse_index_closes.csv"),
                 ["date", "index_name", "index_date", "open", "high", "low", "close", "points_change", "change_pct", "volume", "turnover_cr", "pe", "pb", "div_yield"])
    elif mode == "breadth":
        run_days("breadth", list(weekdays(date(2021, 10, 1), TODAY)), breadth_worker, os.path.join(OUT, "nse_breadth_daily.csv"),
                 ["date", "n_eq", "advances", "declines", "unchanged", "adv_turnover_share", "dec_turnover_share", "turnover_lacs", "avg_delivery_pct"])
    elif mode == "yahoo":
        yahoo()
