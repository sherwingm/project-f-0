"""Agent 5: discovery / second-half / half-year persistence for the G1-F hypotheses with the smallest p. Own computation from label files."""
import pandas as pd, numpy as np
from scipy import stats
I="C:/Users/sherw/project-f-0/index_context_research/regime_investigation/interim/"
L3=pd.read_csv(I+"agent3_regimes/regime_labels.csv",parse_dates=["date"]); L3=L3[L3.strategy=="G1-F"].set_index("date")
GL=pd.read_csv(I+"agent3b_gift_regimes/gift_labels.csv",parse_dates=["date"]); GL=GL[GL.strategy=="G1-F"].set_index("date")
GS=pd.read_csv(I+"agent3b_gift_regimes/gift_labels_samecontract.csv",parse_dates=["date"]); GS=GS[GS.strategy=="G1-F"].set_index("date")
A4=pd.read_csv(I+"agent4_external/external_features.csv",parse_dates=["date"]); A4=A4[A4.strategy=="G1F"].set_index("date")
D=L3[["net_pct","net_rs","period","halfyear","vix_level","gap_cls","q5","ma_struct","dir3","vix_dir"]].copy()
D["gift_ps"]=GL.gift_cls; D["ivsa_ps"]=GL.ivsa_cls; D["ivsa_prevrow"]=GL.ivsa_cls_rob; D["gift_sc"]=GS.gift_cls; D["ivsa_sc"]=GS.ivsa_cls
D["usd"]=A4.usd_class; D["fiidii"]=A4.fiidii_class; D["fiiopt"]=A4.fii_opt_level_class; D["fiifut"]=A4.fii_fut_level_class
out=[]
def desc(title,col,focus,rest_label="rest"):
    out.append(f"--- {title}: class '{focus}' vs rest")
    s=D[D[col].notna()]
    for per,P in (("discovery",s[s.period=="discovery"]),("second half",s[s.period=="second_half"])):
        a=P[P[col]==focus]; b=P[P[col]!=focus]
        mw=stats.mannwhitneyu(a.net_pct,b.net_pct).pvalue if len(a)>=5 and len(b)>=5 else np.nan
        out.append(f"   {per:11s} class n={len(a):3d} mean {a.net_pct.mean():7.1f} med {a.net_pct.median():7.1f} | rest n={len(b):3d} mean {b.net_pct.mean():7.1f} med {b.net_pct.median():7.1f} | diff of means {a.net_pct.mean()-b.net_pct.mean():7.1f} | MW p {mw:.3f}")
    hy=[]
    for h,P in s.groupby("halfyear"):
        a=P[P[col]==focus]; b=P[P[col]!=focus]
        hy.append(f"{h}: {len(a)}/{len(b)} -> "+(f"{a.net_pct.mean()-b.net_pct.mean():+.0f}" if len(a)>=5 and len(b)>=5 else "n/a"))
    out.append("   half-year (n class/rest -> diff of means): "+"; ".join(hy))
desc("H2 VIX level","vix_level","normal"); desc("H9 base: VIX normal (H9 = VIX x gap)","vix_level","normal")
D["vix_gap"]=np.where((D.vix_level=="normal")&(D.gap_cls=="flat"),"normal_flat","other"); desc("H9 normal VIX & flat gap","vix_gap","normal_flat")
desc("C2-type: GIFT flat (prev_settle col) vs other","gift_ps","flat"); desc("A4 X02 USD/INR up","usd","up"); desc("H11 same-contract: stronger","ivsa_sc","stronger"); desc("H11 same-contract: in line","ivsa_sc","in line")
desc("H11 prev_settle col: in line","ivsa_ps","in line"); desc("R2 prev-row IvsA: in line (agent-marked robustness)","ivsa_prevrow","in line")
desc("H15 FII/DII: diverge","fiidii","diverge"); desc("R1 ret5 mid quintile (robustness)","q5",3); desc("H1x bullish dir3","dir3","bullish")
D["vgc"]=D.vix_level.astype(str)+"|"+D.gift_ps.astype(str)
# C2 largest p: VIX x GIFT cells
out.append("--- C2 VIX x GIFT cells (prev_settle col), n and mean by period")
for k,P in D.groupby("vgc"):
    if "nan" in k: continue
    a=P[P.period=="discovery"]; b=P[P.period=="second_half"]
    out.append(f"   {k:20s} disc n={len(a):3d} mean {a.net_pct.mean():7.1f} | 2nd n={len(b):3d} mean {b.net_pct.mean():7.1f}")
out.append("--- VIX level by period counts: "+str(D.groupby(["period","vix_level"]).size().to_dict()))
# fraction of ex-top3 stats for VIX normal
n=D[D.vix_level=="normal"]; lo=D[D.vix_level=="low"]
out.append(f"VIX normal vs low Mann-Whitney p {stats.mannwhitneyu(n.net_pct,lo.net_pct).pvalue:.3f}; Welch p {stats.ttest_ind(n.net_pct,lo.net_pct,equal_var=False).pvalue:.3f}")
# compare agent consistency files
for fn in ("agent3_regimes/regime_consistency.csv","agent3b_gift_regimes/gift_consistency_samecontract.csv"):
    C=pd.read_csv(I+fn); C=C[C.strategy=="G1-F"]; out.append(f"agents' same_sign flags in {fn}: "+str(C.same_sign.value_counts().to_dict()))
print("\n".join(out)); open("audit_09_predictive.txt","w").write("\n".join(out)+"\n")
