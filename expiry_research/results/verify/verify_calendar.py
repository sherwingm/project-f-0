import sys, os, glob
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd, numpy as np
S = os.environ.get("INDEX_STORE", "../fo-index-data/data/index")
cal = pd.read_csv("expiry_research/data/expiry_calendar.csv", dtype=str)
CH = [  # underlying, expiry to verify, regime day it replaces (None if unshifted), why chosen
 ("NIFTY", "2019-02-14", None, "first NIFTY weekly"),
 ("NIFTY", "2023-03-29", "2023-03-30", "holiday shift (Ram Navami), quarterly"),
 ("BANKNIFTY", "2023-06-28", "2023-06-29", "late holiday shift (Bakri Id)"),
 ("BANKNIFTY", "2023-09-06", None, "first BANKNIFTY Wednesday weekly"),
 ("BANKNIFTY", "2024-03-27", None, "first BANKNIFTY last-Wednesday monthly"),
 ("BANKNIFTY", "2024-11-13", None, "last BANKNIFTY weekly"),
 ("BANKNIFTY", "2025-01-30", None, "BANKNIFTY monthly back to Thursday"),
 ("NIFTY", "2025-08-28", None, "last NIFTY Thursday monthly"),
 ("NIFTY", "2025-09-02", None, "first NIFTY Tuesday weekly"),
 ("NIFTY", "2025-09-30", None, "first NIFTY Tuesday monthly (quarterly)"),
 ("NIFTY", "2025-10-20", "2025-10-21", "Muhurat shift"),
 ("NIFTY", "2026-03-30", "2026-03-31", "holiday shift (31-Mar-2026)"),
]
cache = {}
def months(u):
    if u not in cache:
        cache[u] = pd.concat([pd.read_parquet(f, columns=["TradDt","FinInstrmTp","XpryDt","OpnIntrst","TtlTradgVol"]) for f in sorted(glob.glob(f"{S}/options_daily/{u}/*.parquet"))])
        cache[u]["TradDt"] = cache[u].TradDt.astype(str); cache[u]["XpryDt"] = cache[u].XpryDt.astype(str)
    return cache[u]
out = []
for u, e, reg, why in CH:
    b = months(u); days = set(b.TradDt)
    x = b[b.XpryDt == e]
    last = x.TradDt.max() if len(x) else None
    first = x.TradDt.min() if len(x) else None
    fut = (x.FinInstrmTp == "IDF").any()
    vol_exp = x[x.TradDt == e].TtlTradgVol.sum()
    # what other expiries trade in the same week: next expiry after e
    nxt = sorted(set(b[(b.TradDt == e)].XpryDt) - {e})[:1]
    reg_session = (reg in days) if reg else None
    ghost = b[b.XpryDt == reg] if reg else pd.DataFrame()
    c = cal[(cal.underlying == u) & (cal.expiry_date == e)]
    cr = c.iloc[0].to_dict() if len(c) else {}
    out.append(dict(underlying=u, expiry=e, why=why, weekday=pd.Timestamp(e).day_name(),
        bhav_first_traded=first, bhav_last_traded=last, last_eq_expiry=(last == e), futures_listed=fut,
        opt_vol_on_expiry=vol_exp, regime_day=reg, regime_day_is_session=reg_session,
        ghost_rows=len(ghost), ghost_last_traded=(ghost.TradDt.max() if len(ghost) else None),
        cal_present=len(c) == 1, cal_kind=cr.get("kind"), cal_shifted=cr.get("shifted"),
        cal_last_traded=cr.get("last_traded"), cal_has_futures=cr.get("has_futures"),
        cal_quarterly=cr.get("is_quarterly"), cal_relabelled_from=cr.get("relabelled_from")))
r = pd.DataFrame(out); r.to_csv("expiry_research/results/verify/calendar_checks.csv", index=False)
print(r.T.to_string())
# also: around regime changes, list all expiries the bhavcopy shows trading to expiry, vs calendar
for u, a, z in [("BANKNIFTY","2023-08-20","2023-09-20"),("NIFTY","2025-08-15","2025-10-25"),("BANKNIFTY","2024-10-25","2025-02-05")]:
    b = months(u); ex = sorted(set(b[(b.TradDt == b.XpryDt) & (b.TradDt >= a) & (b.TradDt <= z)].TradDt))
    ce = sorted(cal[(cal.underlying == u) & (cal.expiry_date >= a) & (cal.expiry_date <= z)].expiry_date)
    print(u, a, z, "bhav:", ex); print("   cal:", ce, "SAME" if ex == ce else "DIFF")
