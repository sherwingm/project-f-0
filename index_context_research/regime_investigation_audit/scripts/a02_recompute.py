"""Audit A02: independent recomputation of regime labels from RAW files (eod2 NIFTY, vix_daily.parquet, GIFT bhavcopy) and comparison with the agents' labels
and with the committed class tables. No agent code imported."""
import json, math
import numpy as np, pandas as pd
from scipy import stats as st
R = "index_context_research/regime_investigation/"
I = R + "interim/"
ctx = pd.read_csv("index_context_research/results/context_dataset.csv")
lab = pd.read_csv(I + "agent3_regimes/regime_labels.csv")
nd = pd.read_csv("data/eod2/nifty 50.csv", parse_dates=["Date"]).set_index("Date")
C, O = nd["Close"], nd["Open"]
vd = pd.read_parquet("../fo-index-data/data/index/vix_daily.parquet"); vd["d"] = pd.to_datetime(vd["date"]); V = vd.set_index("d")["close"].dropna()
# 1 boundaries
hist = C[(C.index >= "2018-01-01") & (C.index <= "2024-09-30")]
r20 = (hist / hist.shift(20) - 1).dropna()
q = np.percentile(r20, [20, 40, 60, 80]) * 100
b = json.load(open(I + "agent3_regimes/boundaries.json"))
print("my ret20 quintile edges (%):", q.round(2).tolist(), "| agent file keys:", list(b.keys())[:8])
for k, v in b.items():
    if "ret20" in k.lower() or "q20" in k.lower():
        print("   agent", k, v)
vh = V[(V.index >= "2018-01-01") & (V.index <= "2024-09-30")]
print("my VIX p25/p75:", np.percentile(vh, [25, 75]).round(2).tolist(), "n sessions", len(vh))
# 2 per-trade labels for G1-F
G = lab[lab.strategy == "G1-F"].copy()
G["d"] = pd.to_datetime(G["date"])
idx = list(C.index)
out = []
for d in G["d"]:
    i = idx.index(d) if d in C.index else None
    if i is None:
        out.append((np.nan,) * 4); continue
    prev = idx[i - 1]
    r20_ = (C.loc[prev] / C.iloc[i - 1 - 20] - 1) * 100
    gap = (O.loc[d] / C.loc[prev] - 1) * 100
    vprev = V.get(prev, np.nan)
    out.append((r20_, gap, vprev, prev))
G["my_r20"], G["my_gap"], G["my_vprev"], G["my_prev"] = zip(*out)
print("labels columns sample:", G[["ret20", "gap_pct", "vix_prev"]].head(3).round(4).to_dict("records"))
lab_r20 = G["ret20"] * (100 if G["ret20"].abs().max() < 1 else 1)
lab_gap = G["gap_pct"] * (100 if G["gap_pct"].abs().max() < 0.2 else 1)
print("ret20 label vs mine: max|diff| (pct points)", float((lab_r20 - G.my_r20).abs().max()), "| gap:", float((lab_gap - G.my_gap).abs().max()), "| vix_prev:", float((G["vix_prev"] - G.my_vprev).abs().max()))
# my classes
def q20(x): return 1 + (x > q[0]) + (x > q[1]) + (x > q[2]) + (x > q[3])
G["my_q20"] = G.my_r20.apply(q20)
G["my_dir3"] = G.my_q20.map({1: "bearish", 2: "bearish", 3: "sideways", 4: "bullish", 5: "bullish"})
p25, p75 = np.percentile(vh, [25, 75])
G["my_vlev"] = np.where(G.my_vprev < p25, "low", np.where(G.my_vprev > p75, "high", "normal"))
print("class agreement with agent labels: q20", float((G.my_q20 == G.q20).mean()), "dir3", float((G.my_dir3 == G.dir3).mean()), "vix_level", float((G.my_vlev == G.vix_level).mean()))
print("  disagreeing VIX-level trades:", G[G.my_vlev != G.vix_level][["date", "my_vprev", "my_vlev", "vix_level"]].round(2).to_dict("records"))
# 3 independent tables vs committed numbers
def tab(df, col):
    for k, g in df.groupby(col):
        print(f"   {k}: n {len(g)}, win {100*(g.net_pct>0).mean():.0f}%, mean {g.net_pct.mean():+.1f}, median {g.net_pct.median():+.1f}, total Rs {g.net_rs.sum():,.0f}")
print("G1-F direction3 (my labels):"); tab(G, "my_dir3")
print("G1-F VIX level (my labels):"); tab(G, "my_vlev")
kw = st.kruskal(*[g.net_pct.values for k, g in G.groupby("my_q20") if len(g) >= 10]); print("KW p direction quintiles n>=10:", round(kw.pvalue, 4))
kw = st.kruskal(*[g.net_pct.values for k, g in G.groupby("my_vlev") if len(g) >= 10]); print("KW p VIX level:", round(kw.pvalue, 4))
# 4 GIFT same-contract independently
gf = pd.read_csv(R + "external_data/gift_bhavcopy_futures.csv")
gf = gf[gf.contract.str.match(r"^FUTIDXNIFTY\d{2}-[A-Z]{3}-\d{4}$")].copy()
gf["d"] = pd.to_datetime(gf.trade_date); gf["exp"] = pd.to_datetime(gf.contract.str[11:], format="%d-%b-%Y")
gf = gf.sort_values(["d", "exp"])
days = sorted(gf.d.unique())
res = {}
for d in G.d:
    if d not in days: res[d] = np.nan; continue
    k = days.index(d)
    if k == 0: res[d] = np.nan; continue
    near = gf[(gf.d == d) & (gf.exp >= d)].iloc[0]
    prevrow = gf[(gf.d == days[k - 1]) & (gf.exp == near.exp)]
    res[d] = (near.open / prevrow.settlement.iloc[0] - 1) * 100 if len(prevrow) and near.open > 0 else np.nan
G["my_gift"] = G.d.map(res)
gg = pd.read_csv(I + "agent3b_gift_regimes/gift_labels_samecontract.csv"); gg = gg[gg.strategy == "G1-F"].copy(); gg["d"] = pd.to_datetime(gg.date)
mm = G[["d", "my_gift"]].merge(gg[["d", "gift_ret_samecontract", "gap_pct"]], on="d")
print("GIFT same-contract: mine vs agent 3b: n", len(mm), "non-null both", int(mm.dropna().shape[0]), "max|diff|", float((mm.my_gift - mm.gift_ret_samecontract).abs().max()), "| missing mine", int(mm.my_gift.isna().sum()), "agent", int(mm.gift_ret_samecontract.isna().sum()))
print("  corr(GIFT same-contract, actual NIFTY gap) on G1-F days:", round(float(mm.dropna().gift_ret_samecontract.corr(mm.dropna().gap_pct)), 3))
mm["cls"] = np.where(mm.my_gift.isna(), None, np.where(mm.my_gift >= .3, "gap-up", np.where(mm.my_gift <= -.3, "gap-down", "flat")))
print("  my class counts:", mm.cls.value_counts().to_dict())
