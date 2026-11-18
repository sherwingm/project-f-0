"""Audit A03: (1) opening-gap source difference and class flips; (2) re-derive Asia gap, breadth, FII cash, US VIX features from raw downloads;
(3) multiple-testing recomputation from the consolidated test list; (4) selected headline numbers."""
import math
import numpy as np, pandas as pd
from scipy import stats as st
R = "index_context_research/regime_investigation/"
I = R + "interim/"
EXD = R + "external_data/"
ctx = pd.read_csv("index_context_research/results/context_dataset.csv")
lab = pd.read_csv(I + "agent3_regimes/regime_labels.csv")
nd = pd.read_csv("data/eod2/nifty 50.csv", parse_dates=["Date"]).set_index("Date")
C, O = nd["Close"], nd["Open"]
# (1) gap source
for s in ("G1-F", "G1", "G1-C", "XP"):
    L = lab[lab.strategy == s].copy(); L["d"] = pd.to_datetime(L.date)
    idx = list(C.index)
    L["gap_eod"] = [(O.loc[d] / C.iloc[idx.index(d) - 1] - 1) * 100 if d in C.index else np.nan for d in L.d]
    L["gap_lab"] = L.gap_pct * (100 if L.gap_pct.abs().max() < 0.2 else 1)
    cls = lambda x: np.where(x.isna(), None, np.where(x >= .3, "gap-up", np.where(x <= -.3, "gap-down", "flat")))
    flips = (cls(L.gap_eod) != cls(L.gap_lab)).sum()
    print(f"[gap] {s}: max|diff| {float((L.gap_eod-L.gap_lab).abs().max()):.3f} pts, median|diff| {float((L.gap_eod-L.gap_lab).abs().median()):.3f}, trades with |diff|>0.05: {int(((L.gap_eod-L.gap_lab).abs()>0.05).sum())}, class flips at +/-0.3: {int(flips)}")
# (2) re-derive features for G1-F
e = pd.read_csv(I + "agent4_external/external_features.csv"); e = e[e.strategy == "G1F"].copy(); e["d"] = pd.to_datetime(e.date)
def yahoo(n):
    y = pd.read_csv(EXD + f"yahoo/{n}_1d.csv"); y["t"] = pd.to_datetime(y.timestamp_utc); y["d"] = y.t.dt.normalize(); return y.set_index("d")
n225, hsi = yahoo("N225"), yahoo("HSI")
def gap(y, d):
    if d not in y.index: return np.nan
    i = list(y.index).index(d)
    if i == 0: return np.nan
    pc = y.close.iloc[i - 1]; return (y.open.iloc[i] / pc - 1) * 100
rows = []
for d in e.d:
    a, b = gap(n225, d), gap(hsi, d)
    rows.append(np.nanmean([a, b]) if not (np.isnan(a) and np.isnan(b)) else np.nan)
e["my_asia"] = rows
both = ~(e.my_asia.isna() | e.asia_avg_gap.isna())
print(f"[asia] agent4 asia_avg_gap vs my mean(N225,HSI): matched {int(both.sum())}, max|diff| {float((e.my_asia[both]-e.asia_avg_gap[both]).abs().max()):.4f}; agent4 non-null {int(e.asia_avg_gap.notna().sum())}, mine {int(e.my_asia.notna().sum())}")
br = pd.read_csv(EXD + "nse_breadth_daily.csv"); br["d"] = pd.to_datetime(br.date); br = br.drop_duplicates("d").set_index("d")
br["adv_share"] = br.advances / (br.advances + br.declines)
sessions = sorted(pd.to_datetime(pd.read_csv(EXD + "nse_index_closes.csv", usecols=["date"]).date.unique()))
prev = {d: max([s for s in sessions if s < d], default=None) for d in e.d}
e["my_adv"] = [br.adv_share.get(prev[d], np.nan) for d in e.d]
bb = ~(e.my_adv.isna() | e.adv_share_prev.isna())
print(f"[breadth] agent4 adv_share_prev vs mine (previous NSE session in index file): matched {int(bb.sum())}, max|diff| {float((e.my_adv[bb]-e.adv_share_prev[bb]).abs().max()):.5f}; unit check agent mean {e.adv_share_prev.mean():.3f} mine {e.my_adv.mean():.3f}")
fd = pd.read_csv(EXD + "fii_dii_cash_stockezee.csv", parse_dates=["date"]).set_index("date")
e["my_fii"] = [fd.fii_cash_net.get(prev[d], np.nan) for d in e.d]
ff = ~(e.my_fii.isna() | e.fii_cash_prev.isna())
print(f"[fii] matched {int(ff.sum())}, max|diff| {float((e.my_fii[ff]-e.fii_cash_prev[ff]).abs().max()):.3f}; non-null agent {int(e.fii_cash_prev.notna().sum())} mine {int(e.my_fii.notna().sum())}")
vs = yahoo("VIX_US")
def usv(d):
    p = vs[vs.index < d]; p = p[p.close.notna()]
    return (p.close.iloc[-1] / p.close.iloc[-2] - 1) * 100 if len(p) > 1 else np.nan
e["my_usv"] = [usv(d) for d in e.d]
uu = ~(e.my_usv.isna() | e.usvix_chg.isna())
print(f"[usvix] matched {int(uu.sum())}, max|diff| {float((e.my_usv[uu]-e.usvix_chg[uu]).abs().max()):.4f}")
# FII/DII both-buying vs diverge Welch on G1-F
x = e.dropna(subset=["fiidii_class"]); a = x[x.fiidii_class == "both_buy"].net_pct; b2 = x[x.fiidii_class == "diverge"].net_pct
print(f"[fii/dii] both_buy n {len(a)} mean {a.mean():.1f} | diverge n {len(b2)} mean {b2.mean():.1f} | Welch p {st.ttest_ind(a,b2,equal_var=False).pvalue:.4f} | KW p {st.kruskal(a,b2).pvalue:.4f}; wins in both_buy: {(a>0).sum()}")
# (3) multiple testing
t = pd.read_csv(I + "agent5_integrity/consolidated_tests.csv")
print("[mc] consolidated rows", len(t), "families:", t.family.value_counts().to_dict())
for s, g in t.groupby("strategy"):
    m = g[g.family == "main"].dropna(subset=["raw_p"]).sort_values("raw_p").reset_index(drop=True)
    n = len(m); q = (m.raw_p * n / (np.arange(n) + 1)); q = q[::-1].cummin()[::-1].clip(upper=1)
    print(f"   {s}: main tests {n}, nominal p<0.05 {int((m.raw_p<0.05).sum())}, expected {0.05*n:.2f}, min p {m.raw_p.min():.4f}, my min BH q {q.min():.3f}, survivors at 10% {int((q<=0.10).sum())}")
n = 36
print("   P(X>=4 | n=36, p=.05) =", round(1 - st.binom.cdf(3, 36, 0.05), 3))
# are consolidated p-values identical to the agents' own files?
a3 = pd.read_csv(I + "agent3_regimes/regime_tests.csv"); print("   agent3 tests columns:", list(a3.columns)[:10])
# (4) headline numbers
anat = pd.read_csv(I + "agent2_anatomy/anatomy_dataset.csv")
top = anat.sort_values("net_rs", ascending=False)
print(f"[headline] G1-F total Rs {anat.net_rs.sum():,.0f}; top 8 Rs {top.net_rs.iloc[:8].sum():,.0f} = {top.net_rs.iloc[:8].sum()/anat.net_rs.sum()*100:.1f}%; without top 8 mean net% {top.net_pct.iloc[8:].mean():.1f}, median {top.net_pct.iloc[8:].median():.1f}")
held = anat[anat.exit_reason != "stop"]; stp = anat[anat.exit_reason == "stop"]
print(f"   stops {len(stp)} ({len(stp)/len(anat)*100:.0f}%), mean {stp.net_pct.mean():.1f}%; held {len(held)}, win {(held.net_pct>0).mean()*100:.0f}%, mean {held.net_pct.mean():.1f}, Rs {held.net_rs.sum():,.0f}; stops Rs {stp.net_rs.sum():,.0f}")
