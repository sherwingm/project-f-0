"""Agent 5 audit 1: Yahoo timestamp handling. Read-only."""
import pandas as pd, numpy as np, glob, os
EX="C:/Users/sherw/project-f-0/index_context_research/regime_investigation/external_data/yahoo"
out=[]
for f in sorted(glob.glob(EX+"/*_1d.csv")):
    n=os.path.basename(f)[:-7]
    d=pd.read_csv(f); ts=pd.to_datetime(d.timestamp_utc)
    utc=ts.dt.normalize(); loc=(ts+pd.to_timedelta(d.local_offset_s,unit='s')).dt.normalize(); fx=(ts+pd.Timedelta(hours=1)).dt.normalize()
    out.append(f"{n}: rows {len(d)}, distinct local_offset_s {d.local_offset_s.nunique()} {sorted(d.local_offset_s.unique())[:3]}, stamp hours UTC {sorted(ts.dt.hour.unique())}, "
               f"local-date != UTC-date rows {(loc!=utc).sum()}, +1h-date != UTC-date {(fx!=utc).sum()}")
print("\n".join(out)); open("audit_01_yahoo_dates.txt","w").write("\n".join(out)+"\n")
