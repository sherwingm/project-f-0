"""Exploratory, descriptive (15 Nov 2026, user question: do good / bad periods have anything that predicts them?).
S1 fade daily-candle same-day result (e1) by calendar quarter 2022-2026 vs market conditions KNOWN AT THE START of the quarter
(previous-quarter NIFTY return, VIX at the previous close, NIFTY above its 200-day SMA, previous-quarter fade result) and, for reference, the SAME quarter's NIFTY return and VIX (not usable in advance).
Spearman rank correlation, ~18 quarters: very low power; no pass / fail; nothing is promoted."""
import os, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from lib import REPO, index_close_vix
sys.stdout.reconfigure(encoding="utf-8")
R = os.path.join(REPO, "data", "results")
d = pd.concat([pd.read_csv(os.path.join(R, "S1_v10_trades_2022_24.csv")), pd.read_csv(os.path.join(R, "S1_v10_trades.csv"))]).drop_duplicates(subset=["symbol", "day0", "side"])
d = d[d.e1_excluded.isna()].copy()
d["q"] = pd.PeriodIndex(pd.to_datetime(d["day0"]), freq="Q")
fq = d.groupby("q").agg(n=("e1_net_pct", "size"), fade=("e1_net_pct", "mean"), puts=("side", lambda s: (s == "PE").mean()))
n = pd.read_csv(os.path.join(REPO, "data", "eod2", "nifty 50.csv"), parse_dates=["Date"]).set_index("Date")["Close"]
v = index_close_vix(); v.index = pd.to_datetime(v.index)
sma = n.rolling(200).mean()
rows = []
for q in fq.index:
    s, e = q.start_time, q.end_time.normalize()
    prev_end = (q - 1).end_time.normalize(); prev_start = (q - 1).start_time
    nq = n[(n.index >= s) & (n.index <= e)]; npq = n[(n.index >= prev_start) & (n.index <= prev_end)]
    pe_n, pe_v = n[n.index <= prev_end], v[v.index <= prev_end]
    rows.append({"q": str(q), "n": fq.loc[q, "n"], "fade": fq.loc[q, "fade"], "put_share": fq.loc[q, "puts"],
                 "prev_q_nifty": (npq.iloc[-1] / npq.iloc[0] - 1) * 100 if len(npq) > 1 else np.nan,
                 "vix_prev_close": pe_v.iloc[-1], "above_sma200": float(pe_n.iloc[-1] > sma[sma.index <= prev_end].iloc[-1]),
                 "same_q_nifty": (nq.iloc[-1] / nq.iloc[0] - 1) * 100, "same_q_vix": v[(v.index >= s) & (v.index <= e)].mean()})
T = pd.DataFrame(rows).dropna(subset=["fade"])
T["prev_q_fade"] = T["fade"].shift(1)
pd.set_option("display.width", 220)
print(T.round(2).to_string(index=False))
print("\nSpearman correlation of the quarter's fade result with:")
for c, lab in (("prev_q_nifty", "previous quarter NIFTY return (known in advance)"), ("vix_prev_close", "VIX at the previous close (known)"),
               ("above_sma200", "NIFTY above 200-day SMA at the previous close (known)"), ("prev_q_fade", "previous quarter's fade result (known)"),
               ("put_share", "share of puts in the quarter (not known in advance)"), ("same_q_nifty", "SAME quarter NIFTY return (not usable)"), ("same_q_vix", "SAME quarter average VIX (not usable)")):
    x = T[[c, "fade"]].dropna()
    r, p = spearmanr(x[c], x["fade"]); print(f"  {lab}: rho {r:+.2f} (p {p:.2f}, n {len(x)})")
T.to_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "regime_quarters.csv"), index=False)
