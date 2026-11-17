"""Agent 5: independent re-derivation of features for random G1-F trades from RAW files (not from agent code). Read-only."""
import pandas as pd, numpy as np, re, sys
sys.stdout.reconfigure(encoding="utf-8")
REPO="C:/Users/sherw/project-f-0"; RI=REPO+"/index_context_research/regime_investigation"; I=RI+"/interim"
STORE="C:/Users/sherw/fo-index-data/data/index"
ctx=pd.read_csv(REPO+"/index_context_research/results/context_dataset.csv",parse_dates=["day"])
g1f=ctx[ctx.tset=="G1F"].reset_index(drop=True)
rng=np.random.default_rng(5)
samp=g1f.iloc[np.sort(rng.choice(len(g1f),30,replace=False))].copy()
# ---- raw sources
ix=pd.read_csv(RI+"/external_data/nse_index_closes.csv",usecols=["date","index_name","open","close"],parse_dates=["date"])
nif=ix[ix.index_name=="Nifty 50"].set_index("date").sort_index(); bank=ix[ix.index_name=="Nifty Bank"].set_index("date").sort_index()
vixn=ix[ix.index_name=="India VIX"].set_index("date").sort_index().close
SES=nif.index
gf=pd.read_csv(RI+"/external_data/gift_bhavcopy_futures.csv"); gf=gf[gf.contract.astype(str).str.match(r"^FUTIDXNIFTY\d{2}-[A-Z]{3}-\d{4}$")].copy()
gf["d"]=pd.to_datetime(gf.trade_date); gf["exp"]=pd.to_datetime(gf.contract.str[11:],format="%d-%b-%Y")
for c in ("open","settlement","prev_settle"): gf[c]=pd.to_numeric(gf[c],errors="coerce")
gf=gf[gf.exp>=gf.d].sort_values(["d","exp"])
def y(n):
    d=pd.read_csv(RI+f"/external_data/yahoo/{n}.csv"); d["d"]=pd.to_datetime(d.timestamp_utc).dt.normalize(); return d.set_index("d")
N,H,S=y("N225_1d"),y("HSI_1d"),y("GSPC_1d")
br=pd.read_csv(RI+"/external_data/nse_breadth_daily.csv",parse_dates=["date"]).set_index("date")
fd=pd.read_csv(RI+"/external_data/fii_dii_cash_stockezee.csv",parse_dates=["date"]).set_index("date")
def minute_day(d):
    m=pd.read_parquet(f"{STORE}/spot_1m/NIFTY50/{d:%Y-%m}.parquet"); m=m[m.timestamp.dt.date==d.date()]; return m.sort_values("timestamp")
# ---- agent outputs
A3=pd.read_csv(I+"/agent3_regimes/regime_labels.csv",parse_dates=["date"]); A3=A3[A3.strategy=="G1-F"].set_index("date")
A2=pd.read_csv(I+"/agent2_anatomy/anatomy_dataset.csv",parse_dates=["day"]).set_index("day")
GL=pd.read_csv(I+"/agent3b_gift_regimes/gift_labels.csv",parse_dates=["date"]); GL=GL[GL.strategy=="G1-F"].set_index("date")
GS=pd.read_csv(I+"/agent3b_gift_regimes/gift_labels_samecontract.csv",parse_dates=["date"]); GS=GS[GS.strategy=="G1-F"].set_index("date")
A4=pd.read_csv(I+"/agent4_external/external_features.csv",parse_dates=["date"]); A4=A4[A4.strategy=="G1F"].set_index("date")
PO="C:/Users/sherw/project-f-0/g1_research/data/external/participant_oi"
def fiishare(d):
    t=pd.read_csv(f"{PO}/{d:%Y-%m-%d}.csv",skiprows=1); t.columns=[c.strip() for c in t.columns]; t=t.set_index(t.columns[0]); t.index=t.index.str.strip().str.upper()
    return t.loc["FII","Future Index Long"]/(t.loc["FII","Future Index Long"]+t.loc["FII","Future Index Short"])*100
rows=[]
for T in samp.day:
    pi=SES.searchsorted(T,side="left")-1; P=SES[pi]; special_gap = (T-P).days>1 and False
    r={"date":T.date(),"prev_session_indep":P.date()}
    r["ret20_indep"]=nif.close.iloc[pi]/nif.close.iloc[pi-20]-1
    r["ret20_A3"]=A3.loc[T,"ret20"]; r["ret20_A2"]=A2.loc[T,"ret20_pct"]/100
    r["vixprev_indep"]=vixn.iloc[vixn.index.searchsorted(T,side="left")-1]; r["vixprev_A3"]=A3.loc[T,"vix_prev"]; r["vixprev_A2"]=A2.loc[T,"vix_prev_close"]
    m=minute_day(T); mp=minute_day(P)
    r["gap_indep"]=(m.open.iloc[0]/mp.close.iloc[-1]-1)*100; r["gap_ctx"]=samp.set_index("day").loc[T,"gap_pct"]; r["gap_A2"]=A2.loc[T,"gap_pct_open"]
    gd=gf[gf.d==T]
    if len(gd):
        gd=gd.iloc[0]; r["gift_ps_indep"]=(gd.open/gd.prev_settle-1)*100
        pr=gf[(gf.d<T)].d.max(); sc=gf[(gf.d==pr)&(gf.contract==gd.contract)].settlement
        r["gift_same_indep"]=(gd.open/sc.iloc[0]-1)*100 if len(sc) else np.nan
    else: r["gift_ps_indep"]=r["gift_same_indep"]=np.nan
    r["gift_ps_A3b"]=GL.loc[T,"gift_ret"]; r["gift_same_A3b"]=GS.loc[T,"gift_ret_samecontract"]
    nk=N.loc[T] if T in N.index else None
    if nk is not None:
        pos=N.index.get_loc(T); r["nk_indep"]=(nk.open/N.close.iloc[pos-1]-1)*100
    else: r["nk_indep"]=np.nan
    hk=H.loc[T] if T in H.index else None
    if hk is not None:
        pos=H.index.get_loc(T); r["hsi_indep"]=(hk.open/H.close.iloc[pos-1]-1)*100
    else: r["hsi_indep"]=np.nan
    r["nk_A3b"]=GL.loc[T,"nikkei_gap"]; r["nk_A4"]=A4.loc[T,"n225_gap"]; r["hsi_A3b"]=GL.loc[T,"hsi_gap"]; r["hsi_A4"]=A4.loc[T,"hsi_gap"]
    si=S.index.searchsorted(T,side="left")-1; r["sp_indep"]=(S.close.iloc[si]/S.close.iloc[si-1]-1)*100; r["sp_A4"]=A4.loc[T,"sp_ret"]
    if P in br.index: r["adv_indep"]=br.loc[P,"advances"]/(br.loc[P,"advances"]+br.loc[P,"declines"])*100
    else: r["adv_indep"]=np.nan
    r["adv_A4"]=A4.loc[T,"adv_share_prev"]
    r["bankdiff_indep"]=(bank.close.iloc[pi]/bank.close.iloc[pi-1]-nif.close.iloc[pi]/nif.close.iloc[pi-1])*100; r["bankdiff_A4"]=A4.loc[T,"bank_minus_nifty_prev"]
    r["fii_indep"]=fd.fii_cash_net.get(P,np.nan); r["fii_A4"]=A4.loc[T,"fii_cash_prev"]
    try: r["fiishare_indep"]=fiishare(P)
    except Exception as e: r["fiishare_indep"]=np.nan
    r["fiishare_A4"]=A4.loc[T,"fii_fut_share"]
    rows.append(r)
R=pd.DataFrame(rows); R.to_csv("audit_03_rederive_sample.csv",index=False)
def cmp(a,b,tol):
    x=R[a]; y_=R[b]; m=x.notna()&y_.notna(); d=(x[m]-y_[m]).abs()
    return f"{a} vs {b}: compared {m.sum()}/{len(R)}, within {tol}: {(d<=tol).sum()}, max diff {d.max():.4g}"+("" if (d<=tol).all() else f"; mismatch dates {list(R.date[m][d>tol])}")
out=[f"sample {len(R)} random G1-F trades (seed 5)"]
for a,b,t in [("ret20_indep","ret20_A3",1e-6),("ret20_indep","ret20_A2",1e-4),("vixprev_indep","vixprev_A3",0.01),("vixprev_indep","vixprev_A2",0.01),("gap_indep","gap_ctx",0.01),("gap_indep","gap_A2",0.01),
 ("gift_ps_indep","gift_ps_A3b",1e-6),("gift_same_indep","gift_same_A3b",1e-6),("nk_indep","nk_A3b",1e-6),("nk_indep","nk_A4",1e-6),("hsi_indep","hsi_A3b",1e-6),("hsi_indep","hsi_A4",1e-6),
 ("sp_indep","sp_A4",1e-6),("adv_indep","adv_A4",1e-6),("bankdiff_indep","bankdiff_A4",1e-6),("fii_indep","fii_A4",1e-6),("fiishare_indep","fiishare_A4",1e-6)]:
    out.append(cmp(a,b,t))
out.append("rows where nikkei/hsi gap missing in A4 but present independently: "+str(int((R.nk_A4.isna()&R.nk_indep.notna()).sum()))+" / "+str(int((R.hsi_A4.isna()&R.hsi_indep.notna()).sum())))
print("\n".join(out)); open("audit_03_rederive.txt","w").write("\n".join(out)+"\n")
