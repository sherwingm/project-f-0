"""Near Tighty R-multiples (the user, 2026-11-08: "check the R value"). History only, descriptive.

    python near_tighty_research/scripts/nt_r_multiples.py

1R = the risk planned on a trade = the 50 % stop = 0.5 x price paid x lot. R of a trade = its net rupee result (after slippage and
charges) / 1R. So -1R is a stop at exactly 50 %, +2R is a put that doubled and was kept. Trades: NIFTY (data/nt_target_trades.csv) and SENSEX
(data/nt_sensex_booked_trades.csv, lot 20), NT = 1-3 sessions, sold at the next session's 09:16, no target. Reports mean (expectancy) R,
median, win rate, average win / loss R, payoff ratio, break-even win rate, profit factor, share of trades worse than -1R (a gap through
the stop), best / worst R, date-clustered t, mean R without the 5 best trades. Writes results/nt_r_multiples.csv.
"""
import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ROOT))
from scanner.stats import clustered_t  # noqa: E402

n = pd.read_csv(os.path.join(ROOT, "data", "nt_target_trades.csv"))
n = n[(n.nt == 1) & (n.window == "nt_live") & (n.target == "none")].copy()
n["idx"] = "NIFTY"
s = pd.read_csv(os.path.join(ROOT, "data", "nt_sensex_booked_trades.csv"))
s = s[(s.nt == 1) & (s.window == "next_0916") & (s.target == "none")].copy()
s["idx"], s["lot"] = "SENSEX", 20
T = pd.concat([n, s])
T["day"] = T.day.astype(str).str[:10]
T["R"] = T.net_rs / (0.5 * T.paid * T.lot)


def row(g, name):
    R = g.R
    w, l = R[R > 0], R[R <= 0]
    return dict(set=name, n=len(g), mean_R=R.mean(), median_R=R.median(), won=(R > 0).mean(), avg_win_R=w.mean(),
                avg_loss_R=l.mean(), payoff=w.mean() / abs(l.mean()), breakeven_win=abs(l.mean()) / (w.mean() + abs(l.mean())),
                profit_factor=w.sum() / abs(l.sum()), worse_than_minus1R=(R <= -0.98).mean(), worst_R=R.min(), best_R=R.max(),
                ge_2R=(R >= 2).mean(), ge_4R=(R >= 4).mean(), t=clustered_t(R, g.day),
                mean_R_without_top5=R.drop(R.nlargest(5).index).mean(), total_R=R.sum())


rows = []
for idx in ("NIFTY", "SENSEX"):
    g = T[T.idx == idx]
    rows += [row(g, f"{idx} whole"), row(g[g.day >= "2025-10-01"], f"{idx} 2025-10 -> now"), row(g[g.day < "2025-10-01"], f"{idx} before 2025-10")]
rows += [row(T[T.day >= "2025-10-01"], "both 2025-10 -> now"), row(T, "both whole")]
S = pd.DataFrame(rows)
S.to_csv(os.path.join(ROOT, "results", "nt_r_multiples.csv"), index=False)
pd.set_option("display.width", 250)
print(S.round(2).to_string(index=False))
