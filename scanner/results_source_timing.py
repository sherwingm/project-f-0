"""Which comes first for a market-hours result: NSE, BSE, the news, or the stock's move? (descriptive, recent days)

    python -m scanner.results_source_timing 2026-10-06 2026-10-19

For each F&O results filing first published 09:15-15:15 IST on a weekday in the window:
  - NSE time: the corporate-announcements feed (an_dt, to the second);
  - BSE time: BSE's "Result" announcements feed (DissemDT, to the second), matched by company name;
  - news time: the earliest Google News RSS item that day for "<company> results" (pubDate; a rough guide);
  - the stock: 1-minute candles from the live server. "Moved 1 %" = the first minute, from 30 minutes before the
    earliest filing, whose close is >= 1 % from the close 31 minutes before it. "Volume jump" = the first such minute
    with volume >= 5 x the median of the hour before.
Writes data/results/S1_results_source_timing.md / .csv.
"""
from __future__ import annotations

import re
import sys
import time as _t
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from xml.etree import ElementTree

import pandas as pd
import requests

from .backtest_s1_v2 import md
from .build import ROOT
from .events.http import EventHttp
from .events.sources.nse_announcements import REFERER, URL as NSE_URL

RES = ROOT / "data" / "results"
LIVE = "https://fo-scanner.onrender.com"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
     "Referer": "https://www.bseindia.com/", "Origin": "https://www.bseindia.com", "Accept": "application/json"}
BSE = ("https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno={p}&strCat=Result&strPrevDate={d}"
       "&strScrip=&strSearch=P&strToDate={d}&strType=C&subcategory=-1")
NEWS_WORDS = ("result", "profit", "q2", "earnings", "net income", "revenue")


def norm(name: str) -> str:
    s = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    s = re.sub(r"\b(limited|ltd|the|india|co|company|corporation|corp)\b", " ", s)
    return " ".join(s.split())


def nse_rows(a: date, z: date) -> list[dict]:
    rows = EventHttp().get_json(NSE_URL.format(a=a.strftime("%d-%m-%Y"), b=z.strftime("%d-%m-%Y")), REFERER)
    rows = rows if isinstance(rows, list) else (rows or {}).get("data", [])
    out = []
    for r in rows:
        text = f"{r.get('desc')} {r.get('attchmntText')}".lower()
        if "financial result" not in text:
            continue
        try:
            ts = datetime.strptime(r["an_dt"], "%d-%b-%Y %H:%M:%S")
        except (KeyError, ValueError, TypeError):
            continue
        out.append({"symbol": str(r.get("symbol")).upper(), "company": r.get("sm_name") or "", "nse": ts})
    return out


def bse_rows(d: date) -> list[dict]:
    out, p = [], 1
    while p <= 40:
        j = requests.get(BSE.format(p=p, d=d.strftime("%Y%m%d")), headers=H, timeout=60).json()
        t = (j.get("Table") or []) if isinstance(j, dict) else []
        for r in t:
            ts = r.get("DissemDT") or r.get("NEWS_DT")
            if ts:
                out.append({"company": r.get("SLONGNAME") or "", "bse": datetime.fromisoformat(ts[:19])})
        total = ((j.get("Table1") or [{}])[0].get("ROWCNT") or 0) if isinstance(j, dict) else 0
        if not t or len(out) >= total:
            break
        p += 1
        _t.sleep(0.5)
    return out


def news_time(company: str, day: str) -> datetime | None:
    q = quote(f'"{company}" results')
    try:
        x = requests.get(f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en", timeout=30).text
        items = ElementTree.fromstring(x).findall(".//item")
    except Exception:  # noqa: BLE001
        return None
    best = None
    for it in items:
        title = (it.findtext("title") or "").lower()
        if not any(w in title for w in NEWS_WORDS):
            continue
        try:
            ts = (parsedate_to_datetime(it.findtext("pubDate")) + timedelta(hours=5, minutes=30)).replace(tzinfo=None)
        except Exception:  # noqa: BLE001
            continue
        if ts.strftime("%Y-%m-%d") == day and (best is None or ts < best):
            best = ts
    return best


def candles(sym: str, day: str) -> pd.DataFrame | None:
    try:
        r = requests.get(f"{LIVE}/api/history/{sym}", params={"day": day, "tf": 1}, timeout=150)
        c = r.json().get("candles") or []
    except Exception:  # noqa: BLE001
        return None
    if not c:
        return None
    f = pd.DataFrame(c)
    f["t"] = pd.to_datetime(f["time"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.strftime("%H:%M")
    return f


def hm_add(t: str, k: int) -> str:
    h, m = map(int, t.split(":"))
    x = h * 60 + m + k
    return f"{x // 60:02d}:{x % 60:02d}"


def minutes(t1: str | None, t2: str | None) -> float | None:
    if not t1 or not t2:
        return None
    return (int(t1[:2]) * 60 + int(t1[3:5])) - (int(t2[:2]) * 60 + int(t2[3:5]))


def move_times(f: pd.DataFrame, first: str) -> tuple[str | None, str | None, float | None]:
    s = f.drop_duplicates("t").set_index("t")
    start = hm_add(first, -30)
    base_t = hm_add(start, -1)
    before = s[s.index <= base_t]
    if before.empty:
        return None, None, None
    base = float(before["close"].iloc[-1])
    med = float(s[(s.index > hm_add(start, -60)) & (s.index <= base_t)]["volume"].median() or 0)
    after = s[s.index >= start]
    moved = next((t for t, r in after.iterrows() if abs(r["close"] / base - 1) >= 0.01), None)
    vol = next((t for t, r in after.iterrows() if med > 0 and r["volume"] >= 5 * med), None)
    end = s[s.index <= "15:20"]
    return moved, vol, (round((float(end["close"].iloc[-1]) / base - 1) * 100, 2) if len(end) else None)


def main() -> None:
    a, z = date.fromisoformat(sys.argv[1]), date.fromisoformat(sys.argv[2])
    up = ROOT / "data" / "cache" / "fo_universe.txt"
    fo = {x.split(",")[0].strip() for x in up.read_text().split()} if up.exists() else None
    nse = [r for r in nse_rows(a, z) if "09:15" <= r["nse"].strftime("%H:%M") <= "15:15" and r["nse"].weekday() < 5]
    if fo:
        nse = [r for r in nse if r["symbol"] in fo]
    first = {}
    for r in sorted(nse, key=lambda r: r["nse"]):
        first.setdefault((r["symbol"], r["nse"].date()), r)
    bse: dict[tuple[str, date], datetime] = {}
    for d in sorted({k[1] for k in first}):
        for b in bse_rows(d):
            k = (norm(b["company"]), d)
            bse[k] = min(bse.get(k, b["bse"]), b["bse"])
    rows = []
    for (sym, d), r in first.items():
        b = bse.get((norm(r["company"]), d))
        day = d.isoformat()
        n = news_time(re.sub(r"\s+(Limited|Ltd\.?)$", "", r["company"]), day)
        times = {"NSE": r["nse"], **({"BSE": b} if b else {}), **({"news": n} if n else {})}
        earliest = min(times, key=times.get)
        exch = min(r["nse"], b or r["nse"]).strftime("%H:%M")
        f = candles(sym, day)
        moved = vol = day_move = None
        if f is not None:
            moved, vol, day_move = move_times(f, exch)
        rows.append({"symbol": sym, "day": day, "NSE": r["nse"].strftime("%H:%M:%S"),
                     "BSE": b.strftime("%H:%M:%S") if b else "",
                     "BSE - NSE (min)": round((b - r["nse"]).total_seconds() / 60, 1) if b else None,
                     "news": n.strftime("%H:%M") if n else "", "first source": earliest,
                     "stock moved 1 % at": moved or "", "moved - first filing (min)": minutes(moved, exch),
                     "volume jump at": vol or "", "volume jump - first filing (min)": minutes(vol, exch),
                     "move to 15:20 %": day_move})
        _t.sleep(0.3)
    df = pd.DataFrame(rows).sort_values(["day", "NSE"])
    df.to_csv(RES / "S1_results_source_timing.csv", index=False)
    both = df.dropna(subset=["BSE - NSE (min)"])
    mv, vj = df["moved - first filing (min)"], df["volume jump - first filing (min)"]
    summ = pd.DataFrame([
        {"what": "F&O results first filed in market hours", "value": len(df)},
        {"what": "with a BSE time matched", "value": len(both)},
        {"what": "BSE first", "value": int((both["BSE - NSE (min)"] < 0).sum())},
        {"what": "NSE first", "value": int((both["BSE - NSE (min)"] > 0).sum())},
        {"what": "same minute or less apart (|gap| <= 1 min)", "value": int((both["BSE - NSE (min)"].abs() <= 1).sum())},
        {"what": "median gap, BSE - NSE (min)", "value": both["BSE - NSE (min)"].median()},
        {"what": "news seen before both exchanges", "value": int((df["first source"] == "news").sum())},
        {"what": "stock moved 1 % BEFORE the first exchange filing", "value": int((mv < 0).sum())},
        {"what": "stock moved 1 % within 0-5 min after it", "value": int(mv.between(0, 5).sum())},
        {"what": "stock moved 1 % more than 5 min after it", "value": int((mv > 5).sum())},
        {"what": "stock did not move 1 %", "value": int(mv.isna().sum())},
        {"what": "volume jump BEFORE the first exchange filing", "value": int((vj < 0).sum())},
        {"what": "volume jump within 0-5 min after it", "value": int(vj.between(0, 5).sum())},
    ])
    text = "\n".join([
        f"# Which comes first for a market-hours result: NSE, BSE, the news or the stock? ({a} to {z})\n",
        "Descriptive. NSE and BSE times are the exchanges' own publish times (to the second). News = the earliest "
        "Google News item that day about the company's results; a rough guide, since Google's time is when it "
        "listed the story. 'Moved 1 %' = the first minute (from 30 min before the first filing) whose close is 1 % or "
        "more from the price 31 minutes before. 'Volume jump' = the first minute with 5x the hour's median volume. "
        "Company websites have no time stamps, so they cannot be compared.\n",
        "## Summary\n\n" + md(summ),
        "## Every case\n\n" + md(df),
    ])
    (RES / "S1_results_source_timing.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
