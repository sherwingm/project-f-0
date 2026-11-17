"""Agent 5: consolidated list of every hypothesis test (raw Kruskal-Wallis p) by strategy + Benjamini-Hochberg 10 % per strategy."""
import pandas as pd, numpy as np
R="C:/Users/sherw/project-f-0/index_context_research/regime_investigation/interim/"
rows=[]
S3=pd.read_csv(R+"agent3_regimes/regime_tests.csv")
for _,r in S3[S3.section=="explanatory_all"].iterrows():
    fam="main" if r.hypothesis.startswith("H") else "robustness"
    rows.append(dict(strategy=r.strategy,agent="A3",hypothesis=r.hypothesis,defn="direction/VIX/gap/US (pre-reg H1-H9)" if fam=="main" else "robustness (agent-marked)",raw_p=r.kw_p,family=fam,
        n_cells_ge10=r.n_cells_ge10,note=""))
def gift(fn,tag):
    T=pd.read_csv(R+"agent3b_gift_regimes/"+fn); T=T[(T.section=="explanatory_all")&(T.test=="Kruskal-Wallis")]
    for _,r in T.iterrows():
        fam="robustness" if r.hypothesis.startswith("R") else "main"
        note=""
        if tag=="samecontract" and r.hypothesis=="H12": fam="duplicate"; note="identical Asia labels to the prev_settle run; same p, not counted twice"
        if tag=="samecontract" and r.hypothesis in("R1_gift_prevrow","R2_ivsa_prevrow"): note="in the same-contract run R1/R2 are the prev_settle-column variant"
        rows.append(dict(strategy=r.strategy,agent="A3b",hypothesis=r.hypothesis+("" if tag=="prevsettlecol" else "_samecontract"),defn="GIFT "+("prev_settle column" if tag=="prevsettlecol" else "same-contract open/prev settlement"),
            raw_p=r.p_raw,family=fam,n_cells_ge10=r.n_cells_ge10,note=note))
gift("gift_tests.csv","prevsettlecol"); gift("gift_tests_samecontract.csv","samecontract")
S4=pd.read_csv(R+"agent4_external/external_tests.csv"); S4=S4[S4.analysis=="whole"]
for _,r in S4.iterrows():
    st={"G1F":"G1-F","G1C":"G1-C"}.get(r.strategy,r.strategy)
    fam="main" if r.family=="main" else "robustness"
    rows.append(dict(strategy=st,agent="A4",hypothesis=r.hyp,defn=str(r.description)[:70],raw_p=r.KW_p,family=fam,n_cells_ge10=r.classes_tested,
        note=("agent-marked supplementary" if fam=="robustness" else "")))
T=pd.DataFrame(rows)
# mark overlaps between agents as flagged but counted
T.loc[(T.agent=="A4")&(T.hypothesis=="X01"),"note"]="same hypothesis as A3 H6 (US overnight); counted separately (conservative)"
T.loc[(T.agent=="A4")&(T.hypothesis=="H12"),"note"]="same hypothesis as A3b H12 (Asia gap) but different construction (both markets required); counted separately"
T.loc[(T.agent=="A3b")&(T.hypothesis=="H12"),"note"]="same hypothesis as A4 H12; 3b averages whichever markets are open"
def bh(p,q=.10):
    p=np.asarray(p,float); ok=~np.isnan(p); adj=np.full(len(p),np.nan); pv=p[ok]; o=np.argsort(pv); m=len(pv); a=np.empty(m); prev=1.
    for rank in range(m,0,-1):
        i=o[rank-1]; prev=min(prev,pv[i]*m/rank); a[i]=prev
    adj[ok]=a; return adj
T["BH_q"]=np.nan; T["BH_survive_10pct"]=""
summ=[]
for st,g in T[T.family=="main"].groupby("strategy"):
    q=bh(g.raw_p.values); T.loc[g.index,"BH_q"]=q
    T.loc[g.index,"BH_survive_10pct"]=np.where(np.isnan(q),"untestable",np.where(q<=.10,"YES","no"))
    m=int(g.raw_p.notna().sum()); summ.append(dict(strategy=st,planned=len(g),testable=m,expected_p_lt_05=round(.05*m,2),observed_p_lt_05=int((g.raw_p<.05).sum()),observed_p_lt_10=int((g.raw_p<.10).sum()),
        min_p=g.raw_p.min(),min_q=np.nanmin(q),survivors=int((q<=.10).sum())))
T.loc[T.family!="main","BH_survive_10pct"]="not in family ("+T.family+")"
T=T.sort_values(["strategy","family","raw_p"]); 
T[["strategy","agent","hypothesis","defn","raw_p","BH_q","BH_survive_10pct","family","n_cells_ge10","note"]].rename(columns={"defn":"definition"}).to_csv("consolidated_tests.csv",index=False)
S=pd.DataFrame(summ); S.to_csv("consolidated_summary.csv",index=False); print(S.to_string())
# alternative: dedupe (drop A4 X01 and A3b-samecontract) -> fewer tests
print("\nG1-F lowest raw p (main):"); print(T[(T.strategy=="G1-F")&(T.family=="main")].head(12)[["agent","hypothesis","raw_p","BH_q","note"]].to_string())
print("\nXP lowest:"); print(T[(T.strategy=="XP")&(T.family=="main")].head(5)[["agent","hypothesis","raw_p","BH_q"]].to_string())
print("\nG1-C lowest:"); print(T[(T.strategy=="G1-C")&(T.family=="main")].head(5)[["agent","hypothesis","raw_p","BH_q"]].to_string())
print("\nG1 lowest:"); print(T[(T.strategy=="G1")&(T.family=="main")].head(5)[["agent","hypothesis","raw_p","BH_q"]].to_string())
print("\nrobustness list G1-F:"); print(T[(T.strategy=="G1-F")&(T.family!="main")][["agent","hypothesis","raw_p","family"]].to_string())
# also discovery-only BH sensitivity for G1-F? count of raw p<0.05 in whole sample by agent
print(T[(T.family=="main")].groupby(["strategy","agent"]).raw_p.agg(["count",lambda x:(x<.05).sum()]))
