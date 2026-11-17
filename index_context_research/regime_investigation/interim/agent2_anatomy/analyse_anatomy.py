"""Agent 2: descriptive analysis of the anatomy dataset (explanatory only, nothing here is a predictor test).
Run: python -W ignore analyse_anatomy.py [anatomy_dataset.csv]   -> analysis_<tag>.md and cut_tables_<tag>.csv
Bootstrap: resample trading days with replacement (4000 reps, seed 11), 95 % percentile interval of the mean net %.
Cells with n < 10 are flagged 'too few'."""
import os
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
OUT = os.path.dirname(os.path.abspath(__file__))
fn = sys.argv[1] if len(sys.argv) > 1 else "anatomy_dataset.csv"
tag = "G1F" if fn == "anatomy_dataset.csv" else fn.replace("anatomy_dataset_", "").replace(".csv", "")
D = pd.read_csv(os.path.join(OUT, fn))
D["qtr"] = D["quarter"]
rng = np.random.default_rng(11)
NB = 4000


def boot_ci(x, days):
    x = np.asarray(x, float)
    ud = pd.unique(days)
    if len(x) < 2:
        return (np.nan, np.nan)
    idx = {d: np.where(days == d)[0] for d in ud}
    means = np.empty(NB)
    for b in range(NB):
        pick = rng.choice(len(ud), len(ud))
        sel = np.concatenate([idx[ud[j]] for j in pick])
        means[b] = x[sel].mean()
    return tuple(np.percentile(means, [2.5, 97.5]))


def stats(g, label):
    n = len(g)
    w = g[g.net_pct > 0]
    l = g[g.net_pct <= 0]
    lo, hi = boot_ci(g.net_pct.values, g.day.values) if n >= 10 else (np.nan, np.nan)
    return {"cell": label, "n": n, "wins": len(w), "losses": len(l), "win_rate_pct": 100 * len(w) / n if n else np.nan,
            "mean_net_pct": g.net_pct.mean(), "ci95_lo": lo, "ci95_hi": hi, "median_net_pct": g.net_pct.median(),
            "total_net_rs": g.net_rs.sum(), "avg_profit_rs": w.net_rs.mean() if len(w) else np.nan,
            "avg_loss_rs": l.net_rs.mean() if len(l) else np.nan,
            "avg_win_pct": w.net_pct.mean() if len(w) else np.nan, "avg_loss_pct": l.net_pct.mean() if len(l) else np.nan,
            "stop_rate_pct": 100 * (g.exit_reason == "stop").mean(),
            "MFE_mean_pct": g.maxup_pct_next_close_file.mean(), "MFE_median_pct": g.maxup_pct_next_close_file.median(),
            "MAE_mean_pct": g.mae_held_pct.mean(), "MAE_median_pct": g.mae_held_pct.median(),
            "too_few": "too few" if n < 10 else ""}


CUTS = [("ret1_class", "prev-session return quintile (1 = most negative)"), ("ret5_class", "previous 5-session return quintile"),
        ("ret10_class", "previous 10-session return quintile"), ("ret20_class", "previous 20-session return quintile"),
        ("ma_structure", "close vs SMA20/SMA50 structure"), ("vix_level_class", "VIX at signal minute level (history p25/p75)"),
        ("vix_dir_class", "VIX 5-session change (rising >= +5 %, falling <= -5 %)"), ("vix_chg1_sign", "VIX 1-day change sign"),
        ("gap_class", "opening gap (<= -0.3 / flat / >= +0.3)"), ("dte_class", "sessions to expiry"),
        ("breakout_time_class", "breakout time"), ("weekday_name", "weekday"), ("qtr", "quarter of entry"),
        ("exit_reason", "exit reason")]
lines, tabs = [], []
P = lines.append
P(f"# Analysis output {tag} (n = {len(D)}); descriptive only\n")
P(f"Total net Rs {D.net_rs.sum():,.0f}; mean net % {D.net_pct.mean():.1f}; median {D.net_pct.median():.1f}; win rate {100*(D.net_pct>0).mean():.1f} %\n")
allrow = stats(D, "ALL")
tabs.append({"cut": "ALL", **allrow})
for col, desc in CUTS:
    P(f"\n## {desc}  (`{col}`)\n")
    P("cell | n | W/L | win% | mean % [95% CI] | median % | total Rs | avg win Rs | avg loss Rs | stop% | MFE mean/med | MAE mean/med | note")
    P("--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---")
    keys = sorted(D[col].dropna().unique(), key=lambda v: (str(type(v)), v)) if col != "weekday_name" else ["Mon", "Tue", "Wed", "Thu", "Fri"]
    for v in keys:
        g = D[D[col] == v]
        if not len(g):
            continue
        s = stats(g, f"{v}")
        tabs.append({"cut": col, **s})
        ci = f"[{s['ci95_lo']:.0f}, {s['ci95_hi']:.0f}]" if s["n"] >= 10 else "-"
        P(f"{v} | {s['n']} | {s['wins']}/{s['losses']} | {s['win_rate_pct']:.0f} | {s['mean_net_pct']:.1f} {ci} | {s['median_net_pct']:.1f} | "
          f"{s['total_net_rs']:,.0f} | {s['avg_profit_rs']:,.0f} | {s['avg_loss_rs']:,.0f} | {s['stop_rate_pct']:.0f} | "
          f"{s['MFE_mean_pct']:.0f}/{s['MFE_median_pct']:.0f} | {s['MAE_mean_pct']:.0f}/{s['MAE_median_pct']:.0f} | {s['too_few']}")
pd.DataFrame(tabs).to_csv(os.path.join(OUT, f"cut_tables_{tag}.csv"), index=False)

# ---------- winners vs losers
P("\n## Winners vs losers (net % > 0 vs <= 0), all fields\n")
W, Lz = D[D.net_pct > 0], D[D.net_pct <= 0]
P(f"winners {len(W)}, losers {len(Lz)}\n")
try:
    from scipy.stats import mannwhitneyu
except Exception:
    mannwhitneyu = None
num = ["ret1_pct", "ret5_pct", "ret10_pct", "ret20_pct", "prev_vs_sma20_pct", "prev_vs_sma50_pct", "vix_signal", "vix_prev_close",
       "vix_chg5_pct", "vix_chg1_pct", "vix_signal_vs_prev_pct", "gap_pct_open", "intraday_ret_to_signal_pct", "beyond_or_pct",
       "or_width_pct", "breakout_min_after_0930", "dte_calendar", "dte_sessions", "breadth_prev", "atm_iv", "iv_skew", "pcr_oi",
       "gift_basis", "us_prev_ret", "fut_oi_chg", "fut_px_chg", "fii_fut_longshare", "paid_price", "premium_rs",
       "maxup_pct_next_close_file", "mae_held_pct", "mae_before_peak_pct", "duration_trading_min",
       "post_next_open_gap_pct", "post_next_close_vs_entrydayclose_pct", "post_spot_move_signal_to_nextclose_pct"]
P("field | win mean | win median | lose mean | lose median | MWU p (uncorrected, descriptive) | label")
P("--- | --- | --- | --- | --- | --- | ---")
wl = []
for c in num:
    if c not in D:
        continue
    a, b = W[c].dropna(), Lz[c].dropna()
    p = mannwhitneyu(a, b).pvalue if mannwhitneyu and len(a) > 5 and len(b) > 5 else np.nan
    lab = "POST-ENTRY" if (c.startswith("post_") or c in ("maxup_pct_next_close_file", "mae_held_pct", "mae_before_peak_pct", "duration_trading_min")) else "PRE-ENTRY"
    P(f"{c} | {a.mean():.2f} | {a.median():.2f} | {b.mean():.2f} | {b.median():.2f} | {p:.3f} | {lab}")
    wl.append({"field": c, "win_mean": a.mean(), "win_median": a.median(), "lose_mean": b.mean(), "lose_median": b.median(), "mwu_p": p, "label": lab})
pd.DataFrame(wl).to_csv(os.path.join(OUT, f"winners_vs_losers_{tag}.csv"), index=False)
P("\nShares (% of winners vs % of losers):")
for c in ["event_window", "expiry_day"]:
    P(f"- {c}=1: winners {100*W[c].mean():.0f} %, losers {100*Lz[c].mean():.0f} %")
for c in ["ma_structure", "vix_level_class", "vix_dir_class", "gap_class", "dte_class", "breakout_time_class", "weekday_name", "exit_reason"]:
    a = W[c].value_counts(normalize=True) * 100
    b = Lz[c].value_counts(normalize=True) * 100
    P(f"- {c}: " + "; ".join(f"{k} W {a.get(k,0):.0f}/L {b.get(k,0):.0f}" for k in sorted(set(a.index) | set(b.index))))

# ---------- concentration
P("\n## Concentration (top 5 % of trades by net Rs)\n")
k = int(np.ceil(0.05 * len(D)))
S = D.sort_values("net_rs", ascending=False)
top = S.head(k)
tot = D.net_rs.sum()
pos = D[D.net_rs > 0].net_rs.sum()
P(f"top {k} trades: Rs {top.net_rs.sum():,.0f} = {100*top.net_rs.sum()/tot:.0f} % of total net Rs ({tot:,.0f}); {100*top.net_rs.sum()/pos:.0f} % of gross profit of all winners (Rs {pos:,.0f})")
rest = S.iloc[k:]
P(f"without them: n {len(rest)}, total Rs {rest.net_rs.sum():,.0f}, mean % {rest.net_pct.mean():.1f}, median % {rest.net_pct.median():.1f}, win rate {100*(rest.net_pct>0).mean():.0f} %")
for kk in (1, 3, 5, 10):
    P(f"- top {kk}: Rs {S.head(kk).net_rs.sum():,.0f} ({100*S.head(kk).net_rs.sum()/tot:.0f} % of total)")
cols = ["day", "weekday_name", "entry_time", "dte_sessions", "net_pct", "net_rs", "maxup_pct_next_close_file", "ret20_pct", "vix_signal", "gap_pct_open",
        "breakout_min_after_0930", "post_next_open_gap_pct", "post_next_close_vs_entrydayclose_pct", "exit_reason"]
P("\n" + top[cols].round(2).to_string(index=False))
P(f"\nTop {k} vs the rest, means: " + "; ".join(f"{c} {top[c].mean():.2f} vs {rest[c].mean():.2f}" for c in
  ["ret5_pct", "ret20_pct", "vix_signal", "vix_chg5_pct", "gap_pct_open", "breakout_min_after_0930", "dte_sessions", "atm_iv", "intraday_ret_to_signal_pct", "post_next_open_gap_pct"]))
P(f"Top {k} days to expiry: {list(top.dte_sessions)}; expiry_day flag: {list(top.expiry_day)}")
# bootstrap total Rs without top winners
P("\nLargest single-trade shares: " + ", ".join(f"{r.day}:{r.net_rs:,.0f}" for r in S.head(5).itertuples()))

# ---------- stops
P("\n## Stop-outs (exit reason = stop)\n")
st = D[D.exit_reason == "stop"]
ns = D[D.exit_reason != "stop"]
P(f"stops {len(st)} of {len(D)} ({100*len(st)/len(D):.0f} %). Stop exit on entry day: {(st.exit_day.astype(str)==st.day.astype(str)).sum()}, next day: {(st.exit_day.astype(str)!=st.day.astype(str)).sum()}")
P(f"duration (trading minutes) of stops: mean {st.duration_trading_min.mean():.0f}, median {st.duration_trading_min.median():.0f}, quartiles {st.duration_trading_min.quantile(.25):.0f}/{st.duration_trading_min.quantile(.75):.0f}; <=30 min: {(st.duration_trading_min<=30).sum()}, <=60: {(st.duration_trading_min<=60).sum()}")
P(f"stops net %: mean {st.net_pct.mean():.1f}, median {st.net_pct.median():.1f}; MAE held (option min close vs paid): mean {st.mae_held_pct.mean():.1f}, median {st.mae_held_pct.median():.1f}")
P(f"max up before the stop (mfe_held): mean {st.mfe_held_pct.mean():.1f}, median {st.mfe_held_pct.median():.1f}; share with max up >= +20 % before the stop: {100*(st.mfe_held_pct>=20).mean():.0f} %")
P(f"POST-ENTRY: after the stop minute the option, through the next close: highest value vs paid mean {st.stop_after_max_up_pct.mean():.1f}, median {st.stop_after_max_up_pct.median():.1f}; went back to >= paid (0 %) at some minute: {(st.stop_after_max_up_pct>=0).sum()} of {len(st)}; ended next close above paid: {(st.stop_nextclose_vs_paid_pct>0).sum()}; ended >= +50 %: {(st.stop_nextclose_vs_paid_pct>=50).sum()}; ended >= +100 %: {(st.stop_nextclose_vs_paid_pct>=100).sum()}")
P("Recovered (ended next close above paid) stop trades: " + ", ".join(f"{r.day}({r.stop_nextclose_vs_paid_pct:.0f}%)" for r in st[st.stop_nextclose_vs_paid_pct > 0].itertuples()))
P("\nStop rate by quarter: " + "; ".join(f"{q} {100*(g.exit_reason=='stop').mean():.0f} % (n {len(g)})" for q, g in D.groupby("qtr")))
P("Non-stop trades (held to next close): n {}, win rate {:.0f} %, mean {:.1f} %, median {:.1f} %, total Rs {:,.0f}".format(len(ns), 100*(ns.net_pct>0).mean(), ns.net_pct.mean(), ns.net_pct.median(), ns.net_rs.sum()))
P(f"Share of the stopped trades that sat on a 'failed breakout' (entry-day close back above the signal close, post-entry): {100*(st.post_entryday_close_vs_signalclose_pct>0).mean():.0f} % vs {100*(ns.post_entryday_close_vs_signalclose_pct>0).mean():.0f} % of non-stop")

# ---------- winners: time to peak
P("\n## Winners: how long to the peak (POST-ENTRY)\n")
w = D[D.net_pct > 0]
P(f"winners {len(w)}; peak (highest option minute close vs paid through next close): on the entry day {int(w.peak_on_entry_day.sum())}, on the next day {int((1-w.peak_on_entry_day).sum())}")
P(f"trading minutes from entry to peak: median {w.peak_trading_min_after_entry.median():.0f}, mean {w.peak_trading_min_after_entry.mean():.0f}, quartiles {w.peak_trading_min_after_entry.quantile(.25):.0f}/{w.peak_trading_min_after_entry.quantile(.75):.0f}")
big = D[D.net_pct >= 100]
P(f"net >= +100 %: n {len(big)}; peak minutes median {big.peak_trading_min_after_entry.median():.0f}; next day {int((1-big.peak_on_entry_day).sum())}; mean MAE before peak {big.mae_before_peak_pct.mean():.1f} %, worst {big.mae_before_peak_pct.min():.1f} %")
P(f"Winners' net % vs their peak: mean net {w.net_pct.mean():.1f} %, mean MFE {w.mfe_any_pct.mean():.1f} %; share of MFE kept at exit (net/MFE, median): {(w.net_pct/w.mfe_any_pct).median():.2f}")
P(f"Max up share of ALL trades (MFE, no stop, through next close): >= +50 %: {100*(D.maxup_pct_next_close_file>=50).mean():.0f} %, >= +100 %: {100*(D.maxup_pct_next_close_file>=100).mean():.0f} %, >= +200 %: {100*(D.maxup_pct_next_close_file>=200).mean():.0f} %; mean {D.maxup_pct_next_close_file.mean():.0f}, median {D.maxup_pct_next_close_file.median():.0f}")

# ---------- 2026 Q3
P("\n## 2026 Q3 versus other quarters\n")
q = D[D.qtr == "2026Q3"]
o = D[D.qtr != "2026Q3"]
if len(q):
    P(f"2026Q3: n {len(q)}, wins {int((q.net_pct>0).sum())}, win rate {100*(q.net_pct>0).mean():.0f} %, mean {q.net_pct.mean():.1f} %, median {q.net_pct.median():.1f} %, total Rs {q.net_rs.sum():,.0f}, stop rate {100*(q.exit_reason=='stop').mean():.0f} % (others {100*(o.exit_reason=='stop').mean():.0f} %)")
    P(f"others: n {len(o)}, win rate {100*(o.net_pct>0).mean():.0f} %, mean {o.net_pct.mean():.1f} %, median {o.net_pct.median():.1f} %, total Rs {o.net_rs.sum():,.0f}")
    P("\nfield | 2026Q3 mean | 2026Q3 median | other-quarters mean | other median | label")
    P("--- | --- | --- | --- | --- | ---")
    for c in num + ["expiry_day", "event_window"]:
        if c in D:
            lab = "POST-ENTRY" if (c.startswith("post_") or c in ("maxup_pct_next_close_file", "mae_held_pct", "mae_before_peak_pct", "duration_trading_min")) else "PRE-ENTRY"
            P(f"{c} | {q[c].mean():.2f} | {q[c].median():.2f} | {o[c].mean():.2f} | {o[c].median():.2f} | {lab}")
    P("\nWithin 2026Q3 and other quarters, shares by category:")
    for c in ["ma_structure", "vix_level_class", "vix_dir_class", "gap_class", "dte_class", "breakout_time_class", "weekday_name", "ret20_class"]:
        a = q[c].value_counts(normalize=True) * 100
        b = o[c].value_counts(normalize=True) * 100
        P(f"- {c}: " + "; ".join(f"{k_} Q3 {a.get(k_,0):.0f}/other {b.get(k_,0):.0f}" for k_ in sorted(set(a.index) | set(b.index), key=str)))
    P("\n2026Q3 by month of entry:")
    q2 = q.copy(); q2["m"] = q2.day.astype(str).str[:7]
    for m, g in q2.groupby("m"):
        P(f"- {m}: n {len(g)}, win {int((g.net_pct>0).sum())}, mean {g.net_pct.mean():.1f} %, total Rs {g.net_rs.sum():,.0f}, stop {100*(g.exit_reason=='stop').mean():.0f} %, next-open gap mean {g.post_next_open_gap_pct.mean():.2f} %, next-close move mean {g.post_next_close_vs_entrydayclose_pct.mean():.2f} %")
    P("\n2026Q3 losses vs 2026Q3 wins (means): " + "; ".join(f"{c} {q[q.net_pct>0][c].mean():.2f} vs {q[q.net_pct<=0][c].mean():.2f}" for c in ["ret5_pct", "ret20_pct", "vix_signal", "gap_pct_open", "breakout_min_after_0930", "dte_sessions", "post_next_open_gap_pct", "post_next_close_vs_entrydayclose_pct"]))
    P("\nPer-quarter summary (all quarters): n, win %, mean %, median %, total Rs, stop %, mean next-close move %")
    for qq, g in D.groupby("qtr"):
        P(f"- {qq}: n {len(g)}, win {100*(g.net_pct>0).mean():.0f} %, mean {g.net_pct.mean():.1f}, median {g.net_pct.median():.1f}, total Rs {g.net_rs.sum():,.0f}, stop {100*(g.exit_reason=='stop').mean():.0f} %, next-close move {g.post_next_close_vs_entrydayclose_pct.mean():.2f} %, next-open gap {g.post_next_open_gap_pct.mean():.2f} %")

# ---------- post-entry explanation
P("\n## POST-ENTRY explanation: the next session (never a predictor)\n")
P("Correlation of net % with the next open gap / next-day spot move (Spearman): " +
  ", ".join(f"{c} {D['net_pct'].corr(D[c], method='spearman'):.2f}" for c in ["post_next_open_gap_pct", "post_next_close_vs_entrydayclose_pct", "post_spot_move_signal_to_nextclose_pct"]))
for lab, g in (("winners", W), ("losers", Lz)):
    P(f"- {lab}: next-open gap mean {g.post_next_open_gap_pct.mean():.2f} % (median {g.post_next_open_gap_pct.median():.2f}); next-close vs entry-day close mean {g.post_next_close_vs_entrydayclose_pct.mean():.2f} % (median {g.post_next_close_vs_entrydayclose_pct.median():.2f}); share with next-close below entry-day close {100*(g.post_next_close_vs_entrydayclose_pct<0).mean():.0f} % ")
if side_col := D.side.iloc[0]:
    P(f"(side = {side_col}; a put gains when the spot falls)")
open(os.path.join(OUT, f"analysis_{tag}.md"), "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
