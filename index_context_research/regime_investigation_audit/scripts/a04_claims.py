import pandas as pd, numpy as np
from scipy import stats
L=pd.read_csv('../regime_investigation/interim/agent3_regimes/regime_labels.csv')
def w(a,b):
    return stats.ttest_ind(a,b,equal_var=False).pvalue
for s in ['G1-C']:
    d=L[L.strategy==s]
    for nm,sub in [('all',d),('disc',d[d.period=='discovery']),('second',d[d.period!='discovery'])]:
        a=sub[sub.dir3=='bearish'].net_pct; b=sub[sub.dir3=='bullish'].net_pct
        print(s,nm,len(a),len(b),round(b.mean()-a.mean(),1),'welch p',round(w(a,b),4))
print(L.strategy.value_counts().to_dict(), L.period.value_counts().to_dict())
x=L[L.strategy=='XP']
for nm,sub in [('disc',x[x.period=='discovery']),('second',x[x.period!='discovery'])]:
    g=sub.groupby('vix_dir').net_pct.agg(['count','mean']).round(1)
    print('XP',nm,g.to_dict('index'), 'KW p',round(stats.kruskal(*[v.net_pct for _,v in sub.groupby('vix_dir')]).pvalue,5))
f=L[L.strategy=='G1-F']; sec=f[f.period!='discovery']
print('G1-F second dir3 KW', stats.kruskal(*[v.net_pct for _,v in sec.groupby('dir3')]).pvalue, sec.dir3.value_counts().to_dict())
# discovery count of tests <0.05 check claimed 0/31
t=pd.read_csv('../regime_investigation/interim/agent5_integrity/consolidated_tests.csv'); print(t.columns.tolist()); 
