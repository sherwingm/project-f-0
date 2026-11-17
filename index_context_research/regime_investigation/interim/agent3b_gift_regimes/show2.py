import pandas as pd, sys
pd.set_option("display.width",250); pd.set_option("display.max_columns",30); pd.set_option("display.max_rows",500)
t=pd.read_csv("gift_tables.csv")
st=sys.argv[1]; sec=sys.argv[2]
x=t[(t.strategy==st)&(t.section==sec)]
x=x[["hypothesis","regime","n","win_rate","mean_net_pct","boot_lo","boot_hi","median_net_pct","total_net_rs","maxup_mean","maxup_ge100","top5pct_share_of_total_rs"]]
print(x[x.n>0].round(1).to_string())
