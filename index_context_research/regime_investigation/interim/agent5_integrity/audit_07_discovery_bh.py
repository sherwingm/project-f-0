"""Agent 5: BH 10 % on the discovery-section p-values (predictive logic) and probability of the observed number of nominal hits."""
import pandas as pd, numpy as np
from scipy import stats
R="C:/Users/sherw/project-f-0/index_context_research/regime_investigation/interim/"
def collect(sec3,sec4):
    rows=[]
    S3=pd.read_csv(R+"agent3_regimes/regime_tests.csv"); S3=S3[(S3.section==sec3)&S3.hypothesis.str.startswith("H")]
    for _,r in S3.iterrows(): rows.append((r.strategy,"A3",r.hypothesis,r.kw_p))
    for fn,tag in (("gift_tests.csv",""),("gift_tests_samecontract.csv","_sc")):
        T=pd.read_csv(R+"agent3b_gift_regimes/"+fn); T=T[(T.section==sec3)&(T.test=="Kruskal-Wallis")&~T.hypothesis.str.startswith("R")]
        for _,r in T.iterrows():
            if tag=="_sc" and r.hypothesis=="H12": continue
            rows.append((r.strategy,"A3b",r.hypothesis+tag,r.p_raw))
    S4=pd.read_csv(R+"agent4_external/external_tests.csv"); S4=S4[(S4.analysis==sec4)&(S4.family=="main")]
    for _,r in S4.iterrows(): rows.append(({"G1F":"G1-F","G1C":"G1-C"}.get(r.strategy,r.strategy),"A4",r.hyp,r.KW_p))
    return pd.DataFrame(rows,columns=["strategy","agent","hyp","p"])
def bh(p,q=.10):
    p=np.asarray(p,float); ok=~np.isnan(p); adj=np.full(len(p),np.nan); pv=p[ok]; o=np.argsort(pv); m=len(pv); a=np.empty(m); prev=1.
    for rank in range(m,0,-1):
        i=o[rank-1]; prev=min(prev,pv[i]*m/rank); a[i]=prev
    adj[ok]=a; return adj
out=[]
for lab,s3,s4 in (("whole sample","explanatory_all","whole"),("discovery","discovery_to_2025-09-30","discovery"),("second half","second_half","second_half")):
    T=collect(s3,s4)
    for st,g in T.groupby("strategy"):
        q=bh(g.p.values); m=int(g.p.notna().sum()); k=int((g.p<.05).sum())
        pb=1-stats.binom.cdf(k-1,m,.05) if k>0 else 1.0
        best=g.loc[g.p.idxmin()]
        out.append(f"{lab:13s} {st:5s} tests {m:2d}  p<.05 observed {k} (expected {0.05*m:.1f}; P(>=obs by chance, independence) {pb:.3f})  min p {g.p.min():.5f} ({best.agent} {best.hyp})  BH survivors: "+
          (", ".join(f"{a} {h} (q={qq:.3f})" for a,h,qq in zip(g.agent,g.hyp,q) if qq<=.10) or "none"))
print("\n".join(out)); open("audit_07_discovery_bh.txt","w").write("\n".join(out)+"\n")
