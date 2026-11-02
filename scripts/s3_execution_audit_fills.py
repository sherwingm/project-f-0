import re, pandas as pd
from datetime import date, time
from index_data import load as L
from scanner.s3_engine import _slip
R='data/results/'
def plus1(s): h,m=map(int,s.split(':')); m+=1; h+=m//60; return h, m%60
res=[]
for p,cell in [('P4','OR 15 min · trail 25 % · stop 25 %'),('B1','OR 15 min · volume 2x · stop 25 %'),('B2','OR 15 min · accept 15 closes · stop 25 %')]:
    d=pd.read_csv(R+f'S3_{p}_trades.csv'); d=d[(d.cost_mult==1)&(d.cell==cell)]
    if 'traded' in d: d=d[d.traded==True]
    d=d[d.skip.fillna('')=='']
    for _,r in d.iterrows():
        day=date.fromisoformat(r.day); exp=date.fromisoformat(r.expiry)
        m=re.match(r'B(\d+)(CE|PE)@([\d.]+)>([\d.]+)',r.legs); k,opt,fi,fo=float(m[1]),m[2],float(m[3]),float(m[4])
        ch=L.options_day('NIFTY',exp,day)
        h,mi=plus1(r.signal); tin=L.at(day,h,mi)
        pin=L.price_at(ch,k,opt,tin,stale=3)
        eh,em=map(int,r.exit_at.split(':')); tout=L.at(day,eh,em)
        pout=L.price_at(ch,k,opt,tout,stale=30)
        si=_slip(0,tin.time(),1); so=_slip(0,tout.time(),1)
        # strike sanity: spot at signal vs strike
        dte=(exp-day).days
        res.append(dict(pod=p,day=r.day,ok_in=abs(pin*(1+si)-fi)<0.02 if pin else False,ok_out=abs(pout*(1-so)-fo)<0.02 if pout else False,
                        dte=dte,lot=r.lot,qty=r.qty))
x=pd.DataFrame(res)
print(x.groupby('pod')[['ok_in','ok_out']].mean().round(3))
print(x[~(x.ok_in&x.ok_out)].head(10))
print(x.groupby('pod').dte.describe())
print(x.groupby(['pod','dte']).size().unstack(fill_value=0))
