import pandas as pd, sys
pd.set_option('display.width',250,'display.max_columns',30,'display.max_rows',500)
R=pd.read_csv('regime_tables.csv')
c=['strategy','hypothesis','regime','n','win_rate','mean_net_pct','boot_lo','boot_hi','median_net_pct','total_net_rs','maxup_mean','maxup_ge100','top5pct_share_of_total_rs']
sec=sys.argv[1]; hy=sys.argv[2].split(','); st=sys.argv[3].split(',')
x=R[(R.section==sec)&R.hypothesis.isin(hy)&R.strategy.isin(st)&(R.n>0)]
print(x[c].round(1).to_string(index=False))
