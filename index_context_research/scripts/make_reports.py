"""Writes the deliverable .md files of the index context research from results/*.csv. New files only (index_context_research/)."""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
S1 = pd.read_csv(os.path.join(RES, "ctx_stage1_discovery.csv"))
VAL = pd.read_csv(os.path.join(RES, "ctx_validation.csv"))
Y = pd.read_csv(os.path.join(RES, "ctx_yearly.csv"))
NAMES = {"G1": "G1 puts (259)", "G1F": "G1-F (154)", "G1C": "G1-C calls (235)", "XP": "XP expiry-day straddle (107)"}
HDR = "Index context research, 16 Nov 2026. Plan: `PREREG_CONTEXT.md`. Research only; nothing existing was changed; nothing committed. Net % = net per trade after costs (live-rule replays, 1 lot). Max up first.\n\n"


def fmt_rows(df):
    out = []
    for _, r in df.iterrows():
        if not r.get("tested", False):
            out.append(f"- {NAMES[r['tset']]} | {r['feature']}: not tested ({r.get('why', '')})")
            continue
        out.append(f"- {NAMES[r['tset']]} | {r['feature']}: high side {r['mean_high']:+.1f} % (n {int(r['n_high'])}, share reaching +100 % {r['maxup100_high']:.0f} %) vs low side {r['mean_low']:+.1f} % (n {int(r['n_low'])}, {r['maxup100_low']:.0f} %); "
                   f"difference {r['diff']:+.1f} points, t {r['t']:+.2f}, p {r['p']:.3f}, 95 % interval {r['ci_lo']:+.0f} to {r['ci_hi']:+.0f}; multiple-testing pass: {'YES' if r.get('bh_pass') == True else 'no'}")  # noqa: E712
    return "\n".join(out)


def w(name, text):
    open(os.path.join(ROOT, name), "w", encoding="utf-8").write(text)


def topic(name, title, feats, extra=""):
    d = S1[S1["feature"].isin(feats)].sort_values("p")
    w(name, f"# {title}\n\n" + HDR + extra + "\nDiscovery half only (entries to 2025-09-30); split at the discovery median. Verdict per factor is in `INDIVIDUAL_FACTOR_RESULTS.md`.\n\n" + fmt_rows(d) + "\n")


topic("GIFT_NIFTY_ANALYSIS.md", "GIFT Nifty (basis and overnight move)", ["gift_basis", "gift_ret_prev"],
      "Data: NSE IX daily settlement prices (fetched 16 Nov, 861 days from 10 Jul 2023). **Daily settlements, not the pre-open level**: `gift_basis` = previous settlement vs NIFTY previous close; `gift_ret_prev` = previous session's settlement change. Neither is the 09:00 gap, so the question 'does GIFT predict the opening' is NOT answered here. `gift_basis_dev` (basis minus its 20-day mean) was planned but not built.\n")
topic("FII_DII_ANALYSIS.md", "FII positioning (index futures)", ["fii_fut_longshare", "fii_fut_chg"],
      "Data: NSE participant open-interest files (previous session). FII / DII cash buy-sell flows are not available historically; DII is not tested separately. This repeats E-20261108-05 / E-20261109-01 (no candidate) on the trade sets.\n")
topic("INDEX_FUTURES_ANALYSIS.md", "Index futures price and open interest", ["fut_oi_chg", "fut_px_chg"],
      "Data: NIFTY near-month future from the daily bhavcopy (previous session vs the one before, same expiry). Quadrants (price up / OI up etc.) were not built separately; price and OI changes are tested as two numeric features. Futures minutes are not in the store.\n")
topic("VIX_VOLATILITY_ANALYSIS.md", "India VIX", ["vix_signal", "vix_chg5", "vix_pct1y"],
      "Data: VIX 1-minute and daily (store). Repeats parts of the stress audit regimes and the G1 searches; included for the unified table.\n")
topic("INDEX_BREADTH_ANALYSIS.md", "Index breadth proxy", ["breadth_prev"],
      "**Survivorship-biased proxy**: share of TODAY's F&O list that closed up on the previous session (`data/eod2`), not NIFTY 50 constituents at the time. Heavyweight contribution and sector participation were not built. Do not trust beyond a lead.\n")
topic("INDEX_OPTIONS_ANALYSIS.md", "Index options at the entry minute (IV, put-call OI, skew)", ["atm_iv", "pcr_oi", "iv_skew"],
      "Data: NIFTY option 1-minute prices and OI at the entry minute; IV by Black-Scholes (r 6.5 %, no dividends) from the last traded price, so thin-trading strikes add noise. Bid-ask spreads are not in the history. Ablation between IV, OI and skew was not run (see COMBINATION_ANALYSIS.md).\n")
topic("NEWS_IMPACT_ANALYSIS.md", "News and scheduled events", ["event_window"],
      "Only scheduled events are available as timestamps (RBI / Budget / FOMC dates from Oct 2024, `scanner/s3_buy4`). No news archive with publication times exists in the repo; the GDELT tone series tested earlier (E-20261108-04) is a global daily number and is not used here. Categories such as inflation, GDP, geopolitics, reaction after 5 / 15 / 30 / 60 minutes and unexpected news were NOT tested: no timestamped source. `event_window` = the entry day or the next session is such a date (about 10-15 trades per set).\n")
w("EXECUTION_DISCIPLINE_ANALYSIS.md", "# Emotional control and execution discipline\n\n" + HDR +
  "**Not testable, and not faked.** The index paper systems (G1, G1-F, G1-C, XP, NT) are automated: entries, stops and exits follow code, so there is no chasing, revenge trading or moved stop to measure. The live ledgers are on the VM, which this study may not connect to. The only execution effect observable offline is the gap between backtest and live stops (G1's first live trade stopped at -73 % against a 50 % stop; the stress audit's S5 test). Market 'psychology' proxies were not built (no sentiment data beyond VIX). Mandatory checklists, trade limits and cooldowns are therefore NOT recommended on evidence from this study.\n")

# individual factors + verdicts
tested = S1[S1["tested"] == True]  # noqa: E712
rows = []
for _, r in tested.sort_values("p").iterrows():
    v = VAL[(VAL["tset"] == r["tset"]) & (VAL["feature"] == r["feature"])]
    if len(v) and bool(v["passes_validation"].iloc[0]):
        verdict = "REQUIRES LIVE PAPER VALIDATION (passed out-of-sample)"
    elif len(v):
        verdict = "FAILED out-of-sample (passed discovery, did not hold)"
    elif r["p"] < 0.05:
        verdict = "PROMISING BUT INSUFFICIENT EVIDENCE (nominal p < 0.05, failed multiple-testing correction)"
    else:
        verdict = "NO PREDICTIVE VALUE"
    rows.append(f"- {NAMES[r['tset']]} | {r['feature']}: t {r['t']:+.2f}, p {r['p']:.3f} -> {verdict}")
w("INDIVIDUAL_FACTOR_RESULTS.md", "# Individual factor results (Stage 1)\n\n" + HDR +
  f"67 cells (4 trade sets x 17 features, minus those with a side under 5 trades) tested on the DISCOVERY half; Benjamini-Hochberg 10 % over all 67. **1 survivor** (XP, VIX change over 5 sessions), **which failed validation**. Everything else: no predictive value, or promising-but-insufficient where the nominal p was under 0.05.\n\n"
  + "\n".join(rows) + "\n\n## Full numbers per cell (max up first)\n\n" + fmt_rows(tested.sort_values('p')) + "\n")

v = VAL
w("OUT_OF_SAMPLE_VALIDATION.md", "# Out-of-sample validation\n\n" + HDR +
  "Validation (entries from 2025-10-01 to 2026-10-28) was opened once, for the frozen survivors only. Pass rule: the same side is better, |t| >= 1.5 in the same direction, the better side's mean is > 0, n >= 20.\n\n"
  + "\n".join(f"- {NAMES[r['tset']]} | {r['feature']}: discovery difference {r['discovery_diff']:+.1f}; validation high n {int(r['val_n_high'])} / low n {int(r['val_n_low'])}, difference {r['val_diff']:+.1f} points (t {r['val_t']:+.2f}); better side's mean {r['val_mean_better_side']:+.1f} % -> {'PASSED' if r['passes_validation'] else 'FAILED (sign reversed)' if (r['val_diff'] > 0) != (r['discovery_diff'] > 0) else 'FAILED'}" for _, r in v.iterrows())
  + "\n\nNo walk-forward beyond this one chronological split was run (sample too small). Costs and slippage are those of the replay engine (0.5 % / 1 %, dated charges).\n")
w("COMBINATION_ANALYSIS.md", "# Combination analysis\n\n" + HDR +
  "**Not run, by the plan's own rule:** pairs are tested only among factors that pass validation. None did (the single discovery survivor reversed in validation). The 12 combinations in the mission (GIFT + VIX, news + VIX, etc.) are therefore untested hypotheses, and with 107-259 trades per set a combination would have 25-60 trades per cell: not enough to separate from noise. Ablation tables were not produced for the same reason. The earlier combination study on index futures proxies (A4) also found nothing.\n")

# yearly md
def ytab(tset):
    d = Y[(Y["tset"] == tset) & (Y["by"] == "year")]
    lines = [f"- {int(r['period'])}{' (partial)' if r['partial'] else ''}: n {int(r['n'])}, max up >= +100 % on {r['maxup_ge100']:.0f} % (mean {r['maxup_mean']:.0f} %), win {r['win_pct']:.0f} %, mean {r['mean_pct']:+.1f} %, median {r['median_pct']:+.1f} %, profit factor {r['pf']:.2f}, total Rs {r['total_rs']:,.0f}, max drawdown Rs {r['max_dd_rs']:,.0f}" for _, r in d.iterrows()]
    q = Y[(Y["tset"] == tset) & (Y["by"] == "quarter")]
    lines.append("  Quarters: " + "; ".join(f"{r['period']} {r['mean_pct']:+.0f} % (n {int(r['n'])})" for _, r in q.iterrows()))
    for lab in ("weekday", "expiry_day", "trend_prev", "gap_tercile", "vix_tercile"):
        z = Y[(Y["tset"] == tset) & (Y["by"] == lab)]
        lines.append(f"  By {lab}: " + "; ".join(f"{r['period']} {r['mean_pct']:+.0f} % (n {int(r['n'])})" for _, r in z.iterrows()))
    c = Y[(Y["tset"] == tset) & (Y["by"] == "concentration")]
    if len(c):
        lines.append(f"  Concentration: the top 5 % of trades earned Rs {c['total_rs'].iloc[0]:,.0f} of the set's total Rs {c['mean_pct'].iloc[0]:,.0f}.")
    return "\n".join(lines)


w("YEARLY_INDEX_PERFORMANCE.md", "# Yearly index performance (NIFTY only)\n\n" + HDR +
  "Only NIFTY has option-trade history for these rules (no BANKNIFTY / SENSEX trade records), and the minute option data starts Oct 2024, so there are only 2024 (3 months), 2025 and 2026 (to Oct): no 2021-2023 rows exist for these strategies. 2026 is partial.\n\n"
  + "\n\n".join(f"## {NAMES[s]}\n{ytab(s)}" for s in ["G1", "G1F", "G1C", "XP"]) + "\n")
print("reports written")
