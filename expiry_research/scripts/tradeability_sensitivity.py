"""Tradeability sensitivity (review fixes, LLD reports/lld/tradeability.md "Review fixes" 2). Descriptive only.

(a) +20 % target exit filled at the close of the next minute with both legs (up to 15:16), not the trigger minute.
(b) Slippage per leg = max(s % x price, Rs 0.05 tick), at entry and exit.
Reads results/tradeability/trades.csv and the same option minutes. Writes sensitivity.csv.
Run from the repo root: ../.venvs/fo/Scripts/python.exe expiry_research/scripts/tradeability_sensitivity.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats_utils as su  # noqa: E402
import tradeability_common as tc  # noqa: E402

OUT = os.path.join(tc.ROOT, "results", "tradeability")
TICK = 0.05
SLIPS = (0.5, 1.0, 2.0)
UP5 = ["PPC032", "OC13", "OC17", "OC21", "M143"]
RULES = ["PPC032", "PPC062", "OC13", "OC17", "OC21", "M143", "M218", "M220"]

T = pd.read_csv(os.path.join(OUT, "trades.csv"), dtype={"trade_date": str, "exit_date": str, "expiry": str,
                                                          "signal_date": str})


def net_tick(ce_in, pe_in, ce_out, pe_out, hm_in, hm_out, s, lot):
    """tc.net_pct with a one-tick floor on the slippage of each leg."""
    si, so = tc.slip_pct(hm_in, s) / 100, tc.slip_pct(hm_out, s) / 100
    b_ce, b_pe = ce_in + max(ce_in * si, TICK), pe_in + max(pe_in * si, TICK)
    s_ce, s_pe = max(ce_out - max(ce_out * so, TICK), 0.0), max(pe_out - max(pe_out * so, TICK), 0.0)
    cost = lot * (b_ce + b_pe)
    ch = (tc.leg_charges("BUY", lot, b_ce) + tc.leg_charges("BUY", lot, b_pe)
          + tc.leg_charges("SELL", lot, s_ce) + tc.leg_charges("SELL", lot, s_pe))
    return (lot * (s_ce + s_pe) - cost - ch) / cost * 100


# check: with a zero tick the floor version equals the run's net
TICK0 = TICK
for _, r in T.head(50).iterrows():
    TICK = 0.0
    v = net_tick(r.ce_in, r.pe_in, r.ce_out, r.pe_out, "09:16", r.exit_hm, 0.5, r.lot)
    assert abs(v - r["net_0.5"]) < 1e-9, (v, r["net_0.5"])
TICK = TICK0

# (a) next-minute fill for target hits
T["hit"] = (T["exit"] == "ii_tgt20") & (T["gross_pct"] >= 20 - 1e-6)
T["nm_hm"], T["nm_ce"], T["nm_pe"] = T["exit_hm"], T["ce_out"], T["pe_out"]
n_moved = n_kept = 0
for i, r in T[T["hit"]].iterrows():
    od = tc.opt_day(r.expiry, r.trade_date)
    ce, pe = tc.leg_series(od, r.strike, "CE"), tc.leg_series(od, r.strike, "PE")
    both = pd.concat([ce, pe], axis=1, keys=["ce", "pe"]).dropna()
    nxt = both[(both.index > r.exit_hm) & (both.index <= "15:16")]
    if len(nxt):
        hm = nxt.index[0]
        T.loc[i, ["nm_hm", "nm_ce", "nm_pe"]] = [hm, float(nxt.loc[hm, "ce"]), float(nxt.loc[hm, "pe"])]
        n_moved += 1
    else:
        n_kept += 1
print(f"target hits {int(T['hit'].sum())}: moved to next minute {n_moved}, kept {n_kept}")

for s in SLIPS:
    T[f"tick_{s}"] = [net_tick(r.ce_in, r.pe_in, r.ce_out, r.pe_out, "09:16", r.exit_hm, s, r.lot)
                      for r in T.itertuples()]
    T[f"nextmin_{s}"] = [tc.net_pct(r.ce_in, r.pe_in, r.nm_ce, r.nm_pe, "09:16", r.nm_hm, s, r.lot)[0]
                         for r in T.itertuples()]
    T[f"both_{s}"] = [net_tick(r.ce_in, r.pe_in, r.nm_ce, r.nm_pe, "09:16", r.nm_hm, s, r.lot)
                      for r in T.itertuples()]


def groups(g):
    out = {"EVERY_DAY": g, "D0": g[g.ctx == "D0"], "D-1": g[g.ctx == "D-1"], "other": g[g.ctx == "other"]}
    u = g[[f"{r}_flag" for r in UP5]]
    out["UP5|flagged"] = g[(u == 1).any(axis=1)]
    out["UP5|unflagged"] = g[(u == 0).all(axis=1)]
    for rid in RULES:
        out[f"{rid}|flagged"] = g[g[f"{rid}_flag"] == 1]
        out[f"{rid}|unflagged"] = g[g[f"{rid}_flag"] == 0]
    return out


rows = []
for (ech, ex), g in T.groupby(["exp_choice", "exit"]):
    for name, x in groups(g).items():
        for s in SLIPS:
            o = {"exp_choice": ech, "exit": ex, "slip": s, "group": name, "n": len(x)}
            for col in ("net", "tick", "nextmin", "both"):
                v = x[f"{col}_{s}"].values
                o[f"mean_{col}"] = float(np.mean(v)) if len(v) else np.nan
                o[f"win_{col}"] = float(np.mean(v > 0)) if len(v) else np.nan
                o[f"t_{col}"] = su.t_stat(v) if len(v) > 1 else np.nan
            rows.append(o)
R = pd.DataFrame(rows)
# plan rule under each variant
for col in ("net", "tick", "nextmin", "both"):
    R[f"plan_pass_{col}"] = np.nan
    fl = R["group"].str.endswith("|flagged")
    for i in R[fl].index:
        r = R.loc[i]
        un = R[(R.exp_choice == r.exp_choice) & (R.exit == r.exit) & (R.slip == r.slip)
               & (R.group == r.group.replace("|flagged", "|unflagged"))].iloc[0]
        R.loc[i, f"plan_pass_{col}"] = float(r[f"mean_{col}"] > un[f"mean_{col}"] and r[f"mean_{col}"] > 0)
R.to_csv(os.path.join(OUT, "sensitivity.csv"), index=False)

pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 300)
show = ["EVERY_DAY", "D0", "D-1", "UP5|flagged", "M220|flagged"]
x = R[R.group.isin(show) & (R.slip == 0.5)]
print("\n=== mean net %, slip 0.5: run / tick floor / next-minute target fill / both ===")
print(x[["exp_choice", "exit", "group", "n", "mean_net", "mean_tick", "mean_nextmin", "mean_both", "win_net",
         "win_both"]].round(2).to_string(index=False))
print("\n=== cells where the plan rule (flagged > unflagged and flagged > 0) holds, any variant ===")
pp = R[R[[f"plan_pass_{c}" for c in ("net", "tick", "nextmin", "both")]].fillna(0).max(axis=1) > 0]
print(pp[["exp_choice", "exit", "slip", "group", "n", "mean_net", "mean_tick", "mean_nextmin", "mean_both",
          "t_net"]].round(2).to_string(index=False))
