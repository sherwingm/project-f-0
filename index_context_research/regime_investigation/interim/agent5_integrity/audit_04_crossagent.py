"""Agent 5: cross-agent class agreement for G1-F and A2 vix_prev_close deviation. Read-only."""
import pandas as pd, numpy as np, json
R="C:/Users/sherw/project-f-0/index_context_research/"; I=R+"regime_investigation/interim/"
A3=pd.read_csv(I+"agent3_regimes/regime_labels.csv",parse_dates=["date"]); A3=A3[A3.strategy=="G1-F"].set_index("date")
A2=pd.read_csv(I+"agent2_anatomy/anatomy_dataset.csv",parse_dates=["day"]).set_index("day")
GL=pd.read_csv(I+"agent3b_gift_regimes/gift_labels.csv",parse_dates=["date"]); GL=GL[GL.strategy=="G1-F"].set_index("date")
GS=pd.read_csv(I+"agent3b_gift_regimes/gift_labels_samecontract.csv",parse_dates=["date"]); GS=GS[GS.strategy=="G1-F"].set_index("date")
A4=pd.read_csv(I+"agent4_external/external_features.csv",parse_dates=["date"]); A4=A4[A4.strategy=="G1F"].set_index("date")
out=[]
def agree(name,a,b):
    m=a.notna()&b.notna(); out.append(f"{name}: both defined {m.sum()}/154, same class {(a[m].astype(str)==b[m].astype(str)).sum()}, different {(a[m].astype(str)!=b[m].astype(str)).sum()}")
agree("ret20 quintile A2 vs A3",A2.ret20_class.astype(float),A3.q20.astype(float))
agree("VIX level A2(vix_signal) vs A3(prev close)",A2.vix_level_class,A3.vix_level)
agree("gap class A2 vs A3",A2.gap_class.str.replace("_","-"),A3.gap_cls)
agree("VIX dir A2 vs A3",A2.vix_dir_class,A3.vix_dir)
agree("US class A3(ctx) vs A4",A3.us_cls,A4.us_class)
agree("Asia class 3b vs A4",GL.asia_cls,A4.asia_class)
agree("GIFT class prev_settle-col vs same-contract (3b)",GL.gift_cls,GS.gift_cls)
agree("IvsA class prev_settle-col vs same-contract (3b)",GL.ivsa_cls,GS.ivsa_cls)
out.append(f"A3 boundaries ret20 edges {json.load(open(I+'agent3_regimes/boundaries.json'))['ret20_quintile_edges']}; vix p25/p75 {json.load(open(I+'agent3_regimes/boundaries.json'))['vix_p25']:.2f}/{json.load(open(I+'agent3_regimes/boundaries.json'))['vix_p75']:.2f}")
out.append(open(I+"agent2_anatomy/class_boundaries.csv").read())
# NSE VIX vs A2 vix_prev_close
ix=pd.read_csv(R+"regime_investigation/external_data/nse_index_closes.csv",usecols=["date","index_name","close"],parse_dates=["date"])
v=ix[ix.index_name=="India VIX"].set_index("date").close
d=[]
for T in A2.index:
    p=A3.loc[T,"prev_session"]; d.append(A2.loc[T,"vix_prev_close"]-v.get(pd.Timestamp(p),np.nan))
d=pd.Series(d).dropna(); out.append(f"A2 vix_prev_close minus NSE VIX close of the previous session (G1-F): n {len(d)}, |diff|>0.05: {(d.abs()>0.05).sum()}, >0.5: {(d.abs()>0.5).sum()}, max {d.abs().max():.2f}")
# wins definition
for nm,df in (("A2 win (net_pct>0)",A2.win.sum()),):
    out.append(f"{nm}: {df}")
print("\n".join(out)); open("audit_04_crossagent.txt","w").write("\n".join(out)+"\n")
