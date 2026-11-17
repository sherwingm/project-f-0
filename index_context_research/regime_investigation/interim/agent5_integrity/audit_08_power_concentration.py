"""Agent 5: power / minimum detectable effect, and concentration (mean without top-3 trades) of every G1-F single-condition class with n>=10."""
import pandas as pd, numpy as np
from scipy import stats
I="C:/Users/sherw/project-f-0/index_context_research/regime_investigation/interim/"
c=pd.read_csv("C:/Users/sherw/project-f-0/index_context_research/results/context_dataset.csv",parse_dates=["day"]); g=c[c.tset=="G1F"].copy()
out=[]
sd=g.net_pct.std(); sdD=g[g.half=="D"].net_pct.std(); sdV=g[g.half=="V"].net_pct.std()
out.append(f"G1-F n={len(g)}: mean {g.net_pct.mean():.2f} %, median {g.net_pct.median():.2f} %, sd {sd:.2f} %, SE of mean {sd/np.sqrt(len(g)):.2f} %, 95% CI of mean {g.net_pct.mean()-1.96*sd/np.sqrt(len(g)):.1f}..{g.net_pct.mean()+1.96*sd/np.sqrt(len(g)):.1f}; skew {stats.skew(g.net_pct):.2f}")
out.append(f"discovery n={int((g.half=='D').sum())}: mean {g[g.half=='D'].net_pct.mean():.2f}, sd {sdD:.2f}; second half n={int((g.half=='V').sum())}: mean {g[g.half=='V'].net_pct.mean():.2f}, sd {sdV:.2f}")
out.append(f"net Rs: sd per trade {g.net_rs.std():.0f}, mean {g.net_rs.mean():.0f}")
za={0.05:stats.norm.ppf(1-.025),0.003:stats.norm.ppf(1-.0015)}; zb=stats.norm.ppf(.8)
out.append("Minimum detectable difference in mean net % between two classes of equal size n (two-sided, 80 % power, normal approximation, sd pooled = whole-sample sd):")
out.append("n per cell | alpha 0.05 | alpha 0.003 | alpha 0.05, discovery sd")
for n in (10,20,40,80):
    out.append(f"{n:4d} | {(za[.05]+zb)*sd*np.sqrt(2/n):6.1f} pts | {(za[.003]+zb)*sd*np.sqrt(2/n):6.1f} pts | {(za[.05]+zb)*sdD*np.sqrt(2/n):6.1f} pts")
out.append("Unequal split e.g. 20 vs 134 (small class vs rest): "+f"{(za[.05]+zb)*sd*np.sqrt(1/20+1/134):.1f} pts at 0.05; {(za[.003]+zb)*sd*np.sqrt(1/20+1/134):.1f} at 0.003")
out.append("Class vs rest, class n=10/20/40/80 of 154: "+", ".join(f"{n}: {(za[.05]+zb)*sd*np.sqrt(1/n+1/(154-n)):.0f} pts (0.05) / {(za[.003]+zb)*sd*np.sqrt(1/n+1/(154-n)):.0f} (0.003)" for n in (10,20,40,80)))
out.append(f"Whole-sample difference needed to move the G1-F mean from +19.7 % to a class mean significantly different from zero (one class, alpha 0.05): n=40 -> mean must exceed {1.96*sd/np.sqrt(40):.0f} %; n=10 -> {1.96*sd/np.sqrt(10):.0f} %")
# concentration
L3=pd.read_csv(I+"agent3_regimes/regime_labels.csv",parse_dates=["date"]); L3=L3[L3.strategy=="G1-F"].set_index("date")
GL=pd.read_csv(I+"agent3b_gift_regimes/gift_labels.csv",parse_dates=["date"]); GL=GL[GL.strategy=="G1-F"].set_index("date")
GS=pd.read_csv(I+"agent3b_gift_regimes/gift_labels_samecontract.csv",parse_dates=["date"]); GS=GS[GS.strategy=="G1-F"].set_index("date")
A4=pd.read_csv(I+"agent4_external/external_features.csv",parse_dates=["date"]); A4=A4[A4.strategy=="G1F"].set_index("date")
g=g.set_index("day")
cols={}
for n,col in (("H1 dir5 (ret20 quintile)","q20"),("H1x dir3","dir3"),("H2 VIX level","vix_level"),("H3 VIX direction","vix_dir"),("H5 gap","gap_cls"),("H6 US (ctx)","us_cls"),("R ret5 quintile","q5"),("R ret10 quintile","q10"),("R MA","ma_struct")):
    cols[n]=L3[col]
for n,col in (("H10 GIFT (prev_settle col)","gift_cls"),("H11 IvsA (prev_settle col)","ivsa_cls"),("H12 Asia (3b)","asia_cls")): cols[n]=GL[col]
for n,col in (("H10 GIFT (same contract)","gift_cls"),("H11 IvsA (same contract)","ivsa_cls")): cols[n]=GS[col]
for n,col in (("A4 H12 Asia","asia_class"),("A4 H13 risk","risk_class"),("A4 H14 breadth","breadth_class"),("A4 H15 FII/DII","fiidii_class"),("A4 X02 USDINR","usd_class"),("A4 X03 Brent","brent_class"),("A4 X04 US VIX","usvix_class"),("A4 X07 sector","sector_class"),
              ("A4 X08 FII fut level","fii_fut_level_class"),("A4 X10 DII fut level","dii_fut_level_class"),("A4 X12 FII opt level","fii_opt_level_class"),("A4 X14 GDELT","tone_class"),("A4 X15 events","event_class")):
    cols[n]=A4[col]
rows=[]
tot=g.net_rs.sum()
for n,s in cols.items():
    s=s.reindex(g.index)
    for k,idx in s.dropna().groupby(s.dropna()).groups.items():
        x=g.loc[idx]
        if len(x)<10: continue
        top=x.sort_values("net_rs",ascending=False).head(3)
        rest=x.drop(top.index)
        rows.append(dict(test=n,cls=str(k),n=len(x),mean=x.net_pct.mean(),median=x.net_pct.median(),mean_ex_top3_rs=rest.net_pct.mean(),median_ex_top3=rest.net_pct.median(),total_rs=x.net_rs.sum(),top3_rs=top.net_rs.sum(),
                         top3_share_of_class_rs=100*top.net_rs.sum()/x.net_rs.sum() if x.net_rs.sum()>0 else np.nan,rs_ex_top3=rest.net_rs.sum(),
                         win_pct_pct=100*(x.net_pct>0).mean(),win_pct_rs=100*(x.net_rs>0).mean(),excess_vs_all=x.net_pct.mean()-g.net_pct.mean()))
C=pd.DataFrame(rows); C.to_csv("audit_08_concentration.csv",index=False)
# overall
top3=g.sort_values("net_rs",ascending=False)
out.append(f"G1-F overall: top1 {top3.net_rs.iloc[0]:.0f} ({100*top3.net_rs.iloc[0]/tot:.0f}%), top3 {top3.net_rs.head(3).sum():.0f} ({100*top3.net_rs.head(3).sum()/tot:.0f}%), top8 {top3.net_rs.head(8).sum():.0f} ({100*top3.net_rs.head(8).sum()/tot:.0f}%); mean net % ex top 3 {top3.net_pct.iloc[3:].mean():.1f}, ex top 8 {top3.net_pct.iloc[8:].mean():.1f}; Rs ex top 8 {top3.net_rs.iloc[8:].sum():.0f}")
tp=g.sort_values("net_pct",ascending=False)
out.append(f"top 3 by net %: {tp.net_pct.head(3).round(0).tolist()}, mean ex top3 by % {tp.net_pct.iloc[3:].mean():.1f}")
out.append("\nClasses with n>=10 whose mean is notably above/below G1-F mean (|excess|>=10 pts), with mean ex top-3-by-Rs:")
sel=C[C.excess_vs_all.abs()>=10].sort_values("excess_vs_all",ascending=False)
out.append(sel[["test","cls","n","mean","median","mean_ex_top3_rs","top3_share_of_class_rs","total_rs","rs_ex_top3"]].round(1).to_string(index=False))
# win definition consistency
out.append(f"\nwin definitions: net_pct>0 : {int((g.net_pct>0).sum())}; net_rs>0 : {int((g.net_rs>0).sum())}; disagreements {int(((g.net_pct>0)!=(g.net_rs>0)).sum())}; zero Rs trades {int((g.net_rs==0).sum())}")
print("\n".join(out)); open("audit_08_power_concentration.txt","w").write("\n".join(out)+"\n")
