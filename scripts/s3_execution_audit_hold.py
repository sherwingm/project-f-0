import re, pandas as pd
from datetime import date
from index_data import load as L
R='data/results/'
def plus1(s): h,m=map(int,s.split(':')); m+=1; h+=m//60; return h, m%60
res=[]
for p,cell in [('P4','OR 15 min · trail 25 % · stop 25 %'),('B1','OR 15 min · volume 2x · stop 25 %'),('B2','OR 15 min · accept 15 closes · stop 25 %')]:
    d=pd.read_csv(R+f'S3_{p}_trades.csv'); d=d[(d.cost_mult==1)&(d.cell==cell)]
    if 'traded' in d: d=d[d.traded==True]
    d=d[d.skip.fillna('')=='']
    for _,r in d.iterrows():
        day=date.fromisoformat(r.day); exp=date.fromisoformat(r.expiry)
        m=re.match(r'B(\d+)(CE|PE)@([\d.]+)>([\d.]+)',r.legs); k,opt=float(m[1]),m[2]
        ch=L.options_day('NIFTY',exp,day); h,mi=plus1(r.signal)
        pin=L.price_at(ch,k,opt,L.at(day,h,mi),stale=3); p1515=L.price_at(ch,k,opt,L.at(day,15,15),stale=30)
        fi=float(m[3]); fo=float(m[4])
        res.append(dict(pod=p,dte=(exp-day).days,side=opt,booked_raw=(fo/0.995/ (fi/1.005)-1)*100 if r.exit_at<'15:00' else (fo/0.99/(fi/1.005)-1)*100,
                        hold_raw=(p1515/pin-1)*100 if p1515 else None))
x=pd.DataFrame(res)
g=x.groupby('pod')[['booked_raw','hold_raw']].agg(['mean','median']); print(g.round(2))
x['dteb']=pd.cut(x.dte,[0,2,4,6,8],labels=['1-2','3-4','5-6','7-8'])
print(x.groupby(['pod','dteb'])[['booked_raw','hold_raw']].mean().round(2).unstack(0))
print(x.groupby(['pod','side'])[['booked_raw','hold_raw']].mean().round(2))
x.to_csv('data/results/S3_execution_audit_hold.csv',index=False)
