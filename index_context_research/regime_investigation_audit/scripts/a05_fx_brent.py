import pandas as pd, numpy as np
E='external_data/yahoo/'
F=pd.read_csv('interim/agent4_external/external_features.csv')
g=F[F.strategy=='G1F'] if 'G1F' in set(F.strategy) else F[F.strategy=='G1-F']
print('G1-F rows',len(g), set(F.strategy))
uh=pd.read_csv(E+'USDINR_60m.csv'); uh['ts']=pd.to_datetime(uh.timestamp_utc)
uh['d']=uh.ts.dt.normalize(); uh['h']=uh.ts.dt.hour
print('hours present',sorted(uh.h.unique()), 'range',uh.ts.min(),uh.ts.max())
o=uh[uh.h==3].groupby('d').open.first(); c=uh[uh.h==9].groupby('d').close.last()
ch=((c/o-1)*100).dropna()
g=g.copy(); g['mine']=[ch.get(pd.Timestamp(p),np.nan) for p in g.prev_session]
d=(g.mine-g.usd_chg).abs()
print('usd: have',g.usd_chg.notna().sum(),'mine',g.mine.notna().sum(),'max diff',d.max())
print('missing usd trades',g.usd_chg.isna().sum(),'date range of missing',g[g.usd_chg.isna()].date.min(),g[g.usd_chg.isna()].date.max())
# class
cls=lambda x: np.where(np.isnan(x),'',np.where(x>0.2,'up',np.where(x<-0.2,'down','flat')))
print('class agree',(cls(g.mine.values)==g.usd_class.fillna('').values).mean())
print('usd |chg| quantiles',g.mine.abs().describe().round(3).to_dict())
# brent
b=pd.read_csv(E+'BRENT_1d.csv'); print(b.columns.tolist()[:8]); 
tc=[x for x in b.columns if 'time' in x or 'date' in x][0]
b['d']=pd.to_datetime(b[tc]).dt.normalize(); b=b.set_index('d').close.dropna()
bad=0;mx=0;la=0
for _,r in g.iterrows():
    if pd.isna(r.brent_date) or r.brent_date=='': continue
    bd=pd.Timestamp(r.brent_date)
    if bd>=pd.Timestamp(r.date): la+=1
    i=b.index.get_indexer([bd])[0]
    if i<=0: bad+=1; continue
    m=(b.iloc[i]/b.iloc[i-1]-1)*100; mx=max(mx,abs(m-r.brent_chg))
print('brent lookahead rows',la,'unmatched',bad,'max diff chg',round(mx,6))
dd=b.pct_change().abs()*100; print('brent daily moves >8% :',int((dd>8).sum()),' negative prices',int((b<=0).sum()), 'dates', list(dd[dd>8].index.date[:5]))
print('suspect trades G1-F',int(g.brent_suspect.sum()))
