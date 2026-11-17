"""Agent 5: Agent 4 sp_ret vs context us_prev_ret; which one is the right previous US session? Read-only."""
import pandas as pd, numpy as np
RI="C:/Users/sherw/project-f-0/index_context_research/regime_investigation"
F=pd.read_csv(RI+"/interim/agent4_external/external_features.csv",parse_dates=["date"])
c=F.dropna(subset=["sp_ret","check_us_prev_ret_ctx"]).copy()
c["diff"]=(c.sp_ret-c.check_us_prev_ret_ctx).abs()
print("n",len(c),"diff>0.01:",(c['diff']>0.01).sum(),">0.1:",(c['diff']>0.1).sum(),">0.5:",(c['diff']>0.5).sum(),"max",c['diff'].max())
print(c[c['diff']>0.1][["strategy","date","sp_date","sp_ret","check_us_prev_ret_ctx"]].head(20))
# G1F
g=c[c.strategy=="G1F"]; print("G1F",len(g),(g['diff']>0.01).sum())
# independent: S&P from yahoo, previous bar strictly before T
y=pd.read_csv(RI+"/external_data/yahoo/GSPC_1d.csv"); y["d"]=pd.to_datetime(y.timestamp_utc).dt.normalize(); y=y.set_index("d").close
r=y.pct_change()*100
def prev(T):
    i=y.index.searchsorted(T,side="left")-1; return y.index[i], r.iloc[i]
for strat in ["G1F"]:
    g=F[F.strategy==strat].copy()
    g[["my_d","my_r"]]=[prev(T) for T in g.date]
    print("indep vs agent4 sp_ret max diff", (g.my_r-g.sp_ret).abs().max(), "date mismatch",(g.my_d.dt.date.astype(str)!=g.sp_date.astype(str)).sum())
# ctx alignment test: does ctx value equal return of bar dated T-?
ctx=pd.read_csv("C:/Users/sherw/project-f-0/index_context_research/results/context_dataset.csv",parse_dates=["day"])
ctx=ctx[ctx.tset=="G1F"]
import itertools
for lag in [0,1]:
    # return of the bar k positions before the first bar >= T
    vals=[]
    for T in ctx.day:
        i=y.index.searchsorted(T,side="left")-1-lag
        vals.append(r.iloc[i])
    v=np.array(vals); m=ctx.us_prev_ret.notna()
    print("lag",lag,"ctx matches",(abs(v[m]-ctx.us_prev_ret[m])<0.01).sum(),"of",m.sum())
