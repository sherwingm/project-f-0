"""Bhavcopy cache fill: calendar, resume, rate limit, failures; both file formats cached under UDiFF names."""
import io
import zipfile
from datetime import date

import pandas as pd
import pytest

from scanner import nse_fo
from scanner.bhav_cache import cache_path, fill, sessions
from scanner.nse_fo import BhavcopyUnavailable, download_fo_bhavcopy, fo_metrics

OLD = ("INSTRUMENT,SYMBOL,EXPIRY_DT,STRIKE_PR,OPTION_TYP,OPEN,HIGH,LOW,CLOSE,SETTLE_PR,CONTRACTS,VAL_INLAKH,"
       "OPEN_INT,CHG_IN_OI,TIMESTAMP,\n"
       "FUTSTK,ABC,26-Jan-2023,0,XX,100,101,99,100.5,100.5,120,10,110000,10000,02-JAN-2023,\n"
       "OPTSTK,ABC,26-Jan-2023,110,CE,1,1,1,1.25,1.25,40,1,2000,0,02-JAN-2023,\n"
       "OPTSTK,ABC,26-Jan-2023,90,PE,1,1,1,0.75,0.75,30,1,1000,0,02-JAN-2023,\n"
       "FUTIDX,NIFTY,26-Jan-2023,0,XX,1,1,1,18000,18000,1,1,5,0,02-JAN-2023,\n")
UDIFF = ("TradDt,TckrSymb,FinInstrmTp,XpryDt,StrkPric,OptnTp,ClsPric,UndrlygPric,OpnIntrst,ChngInOpnIntrst,"
         "TtlTradgVol,NewBrdLotQty,SctySrs\n"
         "2026-09-18,ABC,STF,2026-09-29,,,100.5,100,110000,10000,120,500,\n"
         "2026-09-18,ABC,STO,2026-09-29,110,CE,1.25,100,2000,0,40,500,\n"
         "2026-09-18,ABC,STO,2026-09-29,90,PE,0.75,100,1000,0,30,500,\n")


def zipped(text, name):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name, text)
    return buf.getvalue()


class Resp:
    def __init__(self, status, content=b""):
        self.status_code, self.content = status, content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


@pytest.mark.parametrize("day,body,name", [(date(2023, 1, 2), OLD, "fo02JAN2023bhav.csv"),
                                           (date(2026, 9, 18), UDIFF, "BhavCopy.csv")])
def test_both_formats_are_cached_under_udiff_names(tmp_path, monkeypatch, day, body, name):
    urls = []
    monkeypatch.setattr(nse_fo.requests, "get", lambda url, headers, timeout: urls.append(url) or Resp(200, zipped(body, name)))
    df = download_fo_bhavcopy(day, cache_dir=tmp_path)
    assert ("DERIVATIVES/2023/JAN/fo02JAN2023bhav" in urls[0]) == (day.year == 2023)
    cached = pd.read_csv(cache_path(tmp_path, day))
    assert {"TckrSymb", "FinInstrmTp", "OpnIntrst", "ChngInOpnIntrst", "OptnTp"} <= set(cached.columns)
    m = fo_metrics(cached).set_index("symbol").loc["ABC"]
    assert m["fut_oi"] == 110000 and m["oi_change_pct"] == pytest.approx(10.0) and m["pcr"] == pytest.approx(0.5)
    assert set(df["FinInstrmTp"]) <= {"STF", "STO", "IDF"}


def test_sessions_use_eod2_dates_then_weekdays():
    idx = [date(2026, 9, 14), date(2026, 9, 15), date(2026, 9, 17)]          # 16th a holiday in eod2
    assert sessions(idx, date(2026, 9, 15), date(2026, 9, 22)) == [
        date(2026, 9, 15), date(2026, 9, 17), date(2026, 9, 18), date(2026, 9, 21), date(2026, 9, 22)]


def test_fill_skips_cached_limits_rate_and_reports_failures(tmp_path):
    days = [date(2026, 9, d) for d in (14, 15, 16, 17)]
    cache_path(tmp_path, days[0]).write_text("x")                          # resume: already there
    t = {"now": 0.0}
    sleeps, fetched = [], []

    def fetch(d):
        fetched.append(d)
        t["now"] += 0.2                                                     # each download takes 0.2 s
        if d.day == 16:
            raise BhavcopyUnavailable("No F&O bhavcopy for 2026-09-16 (404)")
        cache_path(tmp_path, d).write_text("x")

    def sleep(s):
        sleeps.append(round(s, 3))
        t["now"] += s

    r = fill(days, tmp_path, fetch=fetch, sleep=sleep, clock=lambda: t["now"])
    assert fetched == days[1:] and sleeps == [0.8, 0.8]                    # never faster than 1 a second
    assert r["cached"] == 3 and r["downloaded"] == 2 and r["sessions"] == 4
    assert r["failed"] == {"2026-09-16": "No F&O bhavcopy for 2026-09-16 (404)"}
    assert r["first"] == "2026-09-14" and r["last"] == "2026-09-17"
