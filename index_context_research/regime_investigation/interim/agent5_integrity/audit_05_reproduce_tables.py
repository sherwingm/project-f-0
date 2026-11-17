"""Agent 5: reproduce key G1-F class tables independently (own labels from raw files; own stats). Read-only."""
import pandas as pd, numpy as np
from scipy import stats
R="C:/Users/sherw/project-f-0/"; RI=R+"index_context_research/regime_investigation/"; I=RI+"interim/"
ctx=pd.read_csv(R+"index_context_research/results/context_dataset.csv",parse_dates=["day"]); g=ctx[ctx.tset=="G1F"].copy()
e=pd.read_csv(R+"data/eod2/nifty 50.csv",parse_dates=["Date"]).set_index("Date").Close.sort_index()
ix=pd.read_csv(RI+"external_data/nse_index_closes.csv",usecols=["date","index_name","close"],parse_dates=["date"])
vx=ix[ix.index_name=="India VIX"].set_index("date").close.sort_index()
ret20=e/e.shift(20)-1
H=slice("2018-01-01","2024-09-30"); edges=ret20.loc[H].quantile([.2,.4,.6,.8]).values
p25,p75=vx.loc[H].quantile([.25,.75])
def prevval(s,T):
    i=s.index.searchsorted(T,side="left")-1; return s.iloc[i]
g["ret20"]=[prevval(ret20,T) for T in g.day]; g["q20"]=np.searchsorted(edges,g.ret20,side="right")+1
g["dir3"]=g.q20.map({1:"bearish",2:"bearish",3:"sideways",4:"bullish",5:"bullish"})
g["vixp"]=[prevval(vx,T) for T in g.day]; g["vixlvl"]=np.where(g.vixp<p25,"low",np.where(g.vixp>p75,"high","normal"))
def tab(df,col,order):
    rows=[]
    for k in order:
        s=df[df[col]==k]
        if len(s)==0: rows.append(dict(cls=k,n=0)); continue
        rows.append(dict(cls=k,n=len(s),win_pct=100*(s.net_pct>0).mean(),wins_rs=int((s.net_rs>0).sum()),mean=s.net_pct.mean(),median=s.net_pct.median(),total_rs=s.net_rs.sum()))
    return pd.DataFrame(rows)
out=[f"my ret20 edges {np.round(edges,5).tolist()}; VIX p25/p75 {p25:.3f}/{p75:.3f}"]
T3=pd.read_csv(I+"agent3_regimes/regime_tables.csv"); T3=T3[(T3.strategy=="G1-F")&(T3.section=="explanatory_all")]
def compare(h,mine,col):
    a=T3[T3.hypothesis==h].copy()
    a["cls"]=a.regime.astype(str)
    for _,r in mine.iterrows():
        m=a[a.cls==(str(int(r.cls)) if isinstance(r.cls,(int,float,np.integer,np.floating)) else str(r.cls))]
        if len(m)==0: continue
        m=m.iloc[0]
        if r.n==0 and m.n==0: continue
        diffs=[]
        if int(m.n)!=int(r.n): diffs.append(f"n {m.n} vs {r.n}")
        else:
            for k1,k2,tol in (("win_rate","win_pct",.01),("mean_net_pct","mean",.01),("median_net_pct","median",.01),("total_net_rs","total_rs",1)):
                if abs(m[k1]-r[k2])>tol: diffs.append(f"{k1} {m[k1]:.2f} vs {r[k2]:.2f}")
        out.append(f"  {h} {r.cls}: agent3 n={int(m.n)} win={m.win_rate:.1f} mean={m.mean_net_pct:.2f} med={m.median_net_pct:.2f} Rs={m.total_net_rs:.0f} | mine n={int(r.n)} win={r.win_pct:.1f} mean={r['mean']:.2f} med={r['median']:.2f} Rs={r.total_rs:.0f} -> "+("MATCH" if not diffs else "DIFF "+"; ".join(diffs)))
out.append("H1 direction (ret20 quintile)"); t=tab(g,"q20",[1,2,3,4,5]); compare("H1",t,"q20"); out.append(t.round(2).to_string())
out.append("H2 VIX level"); t=tab(g,"vixlvl",["low","normal","high"]); compare("H2",t,"vix"); out.append(t.round(2).to_string())
# KW for H1 and H2
def kw(df,col): 
    gs=[x.net_pct.values for _,x in df.groupby(col) if len(x)>=10]; return stats.kruskal(*gs).pvalue
out.append(f"my KW p: H1 dir5 {kw(g,'q20'):.4f}; H2 VIX level {kw(g,'vixlvl'):.4f}")
# GIFT (both definitions) from raw
gf=pd.read_csv(RI+"external_data/gift_bhavcopy_futures.csv"); gf=gf[gf.contract.astype(str).str.match(r"^FUTIDXNIFTY\d{2}-[A-Z]{3}-\d{4}$")].copy()
gf["d"]=pd.to_datetime(gf.trade_date); gf["exp"]=pd.to_datetime(gf.contract.str[11:],format="%d-%b-%Y")
for c in ("open","settlement","prev_settle"): gf[c]=pd.to_numeric(gf[c],errors="coerce")
gf=gf[gf.exp>=gf.d].sort_values(["d","exp"]); nm=gf.groupby("d").first()
days=sorted(gf.d.unique()); prevd={days[i]:days[i-1] for i in range(1,len(days))}
key=gf.set_index(["d","contract"]).settlement
def same(T):
    if T not in nm.index or T not in prevd: return np.nan
    r=nm.loc[T]; s=key.get((prevd[T],r.contract),np.nan); return (r.open/s-1)*100
g["gift_ps"]=[(nm.loc[T].open/nm.loc[T].prev_settle-1)*100 if T in nm.index else np.nan for T in g.day]
g["gift_same"]=[same(T) for T in g.day]
cl=lambda x:np.nan if x!=x else ("gap-up" if x>=.3 else ("gap-down" if x<=-.3 else "flat"))
g["gc_ps"]=g.gift_ps.map(cl); g["gc_same"]=g.gift_same.map(cl)
T3b=pd.read_csv(I+"agent3b_gift_regimes/gift_tables.csv"); T3b=T3b[(T3b.strategy=="G1-F")&(T3b.section=="explanatory_all")&(T3b.hypothesis=="H10")]
T3s=pd.read_csv(I+"agent3b_gift_regimes/gift_tables_samecontract.csv"); T3s=T3s[(T3s.strategy=="G1-F")&(T3s.section=="explanatory_all")&(T3s.hypothesis=="H10")]
for nmx,col,TT in (("prev_settle column (3b primary)","gc_ps",T3b),("same contract (3b addendum)","gc_same",T3s)):
    out.append(f"H10 GIFT class, {nmx}")
    t=tab(g,col,["gap-down","flat","gap-up"]); out.append(t.round(2).to_string())
    for _,r in t.iterrows():
        m=TT[TT.regime==r.cls].iloc[0]
        ok=int(m.n)==int(r.n) and abs(m.mean_net_pct-r["mean"])<.01 and abs(m.total_net_rs-r.total_rs)<1 and abs(m.median_net_pct-r["median"])<.01
        out.append(f"  agent3b {r.cls}: n={int(m.n)} mean={m.mean_net_pct:.2f} Rs={m.total_net_rs:.0f} -> {'MATCH' if ok else 'DIFF'}")
    out.append(f"  my KW p {kw(g,col):.4f}")
print("\n".join(out)); open("audit_05_reproduce_tables.txt","w").write("\n".join(out)+"\n")
g.to_csv("audit_05_g1f_mylabels.csv",index=False)
