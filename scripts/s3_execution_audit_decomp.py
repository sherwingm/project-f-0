import re, pandas as pd, numpy as np
from datetime import time
R='data/results/'
def sl(t): return 0.01 if (t<time(9,30) or t>=time(15,0)) else 0.005
def tt(s): h,m=map(int,s.split(':')[:2]); return time(h,m)
def plus1(s): h,m=map(int,s.split(':')); m+=1; h+=m//60; return f'{h:02d}:{m%60:02d}'
pods={'P2':(None,'entry'),'P4':('OR 15 min · trail 25 % · stop 25 %','sig'),'E1':('E-1 → E 14:45','14:45'),
 'Q1':('lookback 5 · pct 20 · hold 3','14:45'),'B1':('OR 15 min · volume 2x · stop 25 %','sig'),
 'G1':('gap 0.5 % · confirm 15 min · stop 25 %','09:30'),'B2':('OR 15 min · accept 15 closes · stop 25 %','sig')}
out=[]
for p,(cell,ent) in pods.items():
    d=pd.read_csv(R+f'S3_{p}_trades.csv')
    if 'cost_mult' in d: d=d[d.cost_mult==1]
    if cell: d=d[d.cell==cell]
    if 'traded' in d: d=d[d.traded==True]
    d=d[d.net_pct_premium.notna()&(d.skip.fillna('')=='')]
    if p=='P2': d=d[(d.entry=='14:45')&(d.exit=='15:25')&(d.target.isna())]
    raw=[];slip=[]
    for _,r in d.iterrows():
        te = plus1(r.signal) if ent=='sig' else (r.entry if ent=='entry' else ent)
        si, so = sl(tt(te)), sl(tt(r.exit_at))
        legs=re.findall(r'B\d+(?:CE|PE)@([\d.]+)>([\d.]+)',r.legs)
        fi=sum(float(a) for a,b in legs); fo=sum(float(b) for a,b in legs)
        mi=sum(float(a)/(1+si) for a,b in legs); mo=sum(float(b)/(1-so) for a,b in legs)
        raw.append((mo/mi-1)*100); slip.append(((mo/mi-1)-(fo/fi-1))*100)
    d=d.assign(raw=raw,slip=slip,fee=d.fees_rs/d.premium_rs*100)
    out.append(dict(pod=p,n=len(d),raw_mean=d.raw.mean(),raw_med=d.raw.median(),raw_win=(d.raw>0).mean()*100,
        slip=d.slip.mean(),fees=d.fee.mean(),net=d.net_pct_premium.mean(),net_win=(d.net_pct_premium>0).mean()*100))
print(pd.DataFrame(out).round(2).to_string(index=False))
