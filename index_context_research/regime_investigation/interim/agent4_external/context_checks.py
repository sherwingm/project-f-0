"""Agent 4: descriptive confound checks (previous-session NIFTY return by class); output context_checks.csv. Run: python -W ignore context_checks.py"""
import os, pandas as pd, numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
F = pd.read_csv(OUT + "/external_features.csv", parse_dates=["date"])
ix = pd.read_csv(OUT + "/../../external_data/nse_index_closes.csv", usecols=["date", "index_name", "close"], parse_dates=["date"])
n = ix[ix.index_name == "Nifty 50"].set_index("date")["close"].sort_index().pct_change() * 100
F["nifty_prev_ret"] = pd.to_datetime(F["prev_session"]).map(n)
rows = []
for col in ["asia_class", "us_class", "risk_class", "breadth_class", "sector_class", "fiidii_class", "usd_class", "usvix_class", "fii_fut_level_class", "dii_fut_level_class", "fii_fut_chg_class", "dii_fut_chg_class"]:
    for (s, c), g in F[F.strategy.isin(["G1F"])].groupby(["strategy", col]):
        rows.append(dict(strategy=s, column=col, cls=c, n=len(g), mean_prev_session_nifty_ret_pct=g.nifty_prev_ret.mean(), mean_net_pct=g.net_pct.mean()))
pd.DataFrame(rows).round(3).to_csv(OUT + "/context_checks.csv", index=False)
print(pd.DataFrame(rows).round(2).to_string(index=False))
