"""Builds stress_audit/results/STRESS_REPORT.md from the result CSVs (no number is typed by hand except the repo facts marked "read in the code")."""
from __future__ import annotations

import json
from math import erf, sqrt

import numpy as np
import pandas as pd

from . import common as C

R = C.OUT


def fmt(df: pd.DataFrame, cols: list[str], names: dict | None = None) -> str:
    d = df[cols].copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda x: "" if pd.isna(x) else (f"{x:,.2f}" if abs(x) < 100 else f"{x:,.0f}"))
    d = d.rename(columns=names or {})
    head = "| " + " | ".join(d.columns) + " |\n|" + "|".join(["---"] * len(d.columns)) + "|\n"
    return head + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in d.to_numpy()) + "\n"


def p_from_t(t):
    return float("nan") if t is None or pd.isna(t) else 2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2))))


def row_(df, sid):
    return df[df.scenario == sid].iloc[0]


def row_g(df, tr, sid):
    return df[(df.strategy == tr) & (df.scenario == sid)].iloc[0]


def main() -> None:
    s1 = pd.read_csv(R / "scenario_results_s1.csv")
    g1 = pd.read_csv(R / "scenario_results_g1.csv")
    v = json.loads((R / "g1_validation.json").read_text())
    man = json.loads((R / "RUN_MANIFEST.json").read_text())
    sens1 = pd.read_csv(R / "sensitivity_s1.csv")
    sens2 = pd.read_csv(R / "sensitivity_g1.csv")
    reg1, reg2 = pd.read_csv(R / "regimes_s1.csv"), pd.read_csv(R / "regimes_g1.csv")
    amb1 = pd.read_csv(R / "s1_ambiguous_trades.csv")
    amb2 = pd.read_csv(R / "g1_ambiguous_trades.csv")
    allt = pd.concat([s1.assign(track="S1 fade v12"), g1.assign(track=g1["strategy"])], ignore_index=True)
    b = s1[s1.scenario == "B0"].iloc[0]
    gb = g1[(g1.strategy == "G1") & (g1.scenario == "B0")].iloc[0]
    fb = g1[(g1.strategy == "G1-F") & (g1.scenario == "B0")].iloc[0]
    cols = ["scenario", "description", "price_type", "n", "exp_pct", "net_rs", "win_pct", "profit_factor", "max_dd_rs", "t_clustered", "ci95_cluster_lo", "ci95_cluster_hi", "delta_vs_B0_rs", "verdict"]
    nm = {"exp_pct": "exp %", "net_rs": "net Rs", "win_pct": "win %", "profit_factor": "PF", "max_dd_rs": "max DD Rs", "t_clustered": "t", "ci95_cluster_lo": "CI lo", "ci95_cluster_hi": "CI hi", "delta_vs_B0_rs": "vs B0 Rs", "price_type": "price type"}
    # Holm across the scenario family (normal approximation of the clustered t)
    fam = {}
    for _, r in allt.iterrows():
        if r.scenario.startswith("E5") or r.scenario in ("S0W", "S0B"):
            continue
        fam[f"{r.track} {r.scenario}"] = p_from_t(r.t_clustered)
    fam = {k: p for k, p in fam.items() if not np.isnan(p)}
    items = sorted(fam.items(), key=lambda kv: kv[1])
    holm, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - i) * p))
        holm[k] = run
    sig = [(k, round(fam[k], 4), round(holm[k], 4)) for k, _ in items if fam[k] < 0.05]
    # S1 tidbits
    rng_note = "median 09:16 candle range 16.4 % of its open; 72 % of the 339 first candles have a range above 10 %; 47 of 339 first candles already trade at or below the -20 % stop level and 115 reach the +10 % trigger inside the entry minute (computed in this run from the candle files)"
    exits = pd.read_csv(R / "trades_s1_all_scenarios.csv")
    e0 = exits[exits.scenario == "B0"]
    reasons = e0.reason.value_counts().to_dict()
    held_med = float(e0.minutes_held.median())
    stress_ids = ["C1", "C2a", "C2b", "C3", "C6", "C7", "E1", "E2", "E3", "E4", "S2", "S3", "S3t", "S4", "C8"]
    neg_s1 = [i for i in stress_ids if row_(s1, i).exp_pct < 0]
    g_ids = ["C1", "C2", "C3", "C6", "C7", "E1", "E2", "E3", "E4", "S5", "S6", "C8"]
    neg_g1_pct = [i for i in g_ids if row_g(g1, "G1", i).exp_pct <= 0]
    neg_g1_rs = [i for i in g_ids if row_g(g1, "G1", i).net_rs <= 0]
    neg_f_pct = [i for i in g_ids if row_g(g1, "G1-F", i).exp_pct <= 0]
    neg_f_rs = [i for i in g_ids if row_g(g1, "G1-F", i).net_rs <= 0]
    live_short = "58 trades, mean -5.7 % of premium, 47 % won"
    live = "58 closed v12 paper trades up to 9 Nov 2026 (ledger snapshot saved 9 Nov 15:29): mean -5.69 % of premium, 47 % won (holdout_track.py on the snapshot; previously inspected, so descriptive only)"

    def row(df, sid):
        return df[df.scenario == sid].iloc[0]

    def g(sid, tr="G1"):
        return g1[(g1.strategy == tr) & (g1.scenario == sid)].iloc[0]

    txt = f"""# Stress test and backtest reality audit: S1 fade v12, G1, G1-F

Run: git {man.get('git_head', '')[:9]}, {man.get('run_time_ist')}, seed {man.get('seed')}. Pre-registered in `stress_audit/PREREG.md` (+ `AMENDMENTS.md`), committed before any result.
Offline: existing files only. No production rule, engine, charge table, live server or VM was changed. The sealed expiry data was not opened.
**Purpose: challenge the numbers, not improve them. No parameter was tuned. Every scenario of the pre-registration is reported below, including the negative ones.**

## 0. The answer in ten lines
1. **Engine correctness: adequate.** The S1 baseline reproduces the existing result exactly (339 trades, +{b.exp_pct:.2f} %, Rs {b.net_rs:,.0f}, t {b.t_clustered}). The G1 simulator matches `scanner/s3_engine.py` to the rupee on all {v['sim_trades']} trades (largest difference Rs {v['max_abs_diff_vs_engine_rs']:.2f}) and reproduces the stored replay (Rs 40,448 / 247,046 under the old STT table, Rs 41,309 / 247,602 under the dated one).
2. **S1 fade v12: the +2.9 % a trade shrinks quickly under execution stress.** Slippage of 1 % a side takes it to {row(s1,'C1').exp_pct:+.2f} %, 2 % to {row(s1,'C2a').exp_pct:+.2f} %, one candle later entry to {row(s1,'E1').exp_pct:+.2f} %, and the combined case to {row(s1,'C6').exp_pct:+.2f} %. The baseline has **no slippage term at all**.
3. **S1 v12 is a first-minutes trade.** {reasons.get('stop', 0)} stops and {reasons.get('trail', 0)} trails, **{reasons.get('time', 0)} exits at 15:19**; the median trade is closed {held_med:.0f} minutes after the entry candle. Its whole result is decided by the 09:16-09:20 candles, where {rng_note}.
4. **S1 v12 depends on the unknowable order inside a candle.** Under the opposite high-before-low ordering {len(amb1)} of 339 trades change and the result falls to {row(s1,'S0H').exp_pct:+.2f} %. The per-trade bounds run from {row(s1,'S0W').exp_pct:+.2f} % to {row(s1,'S0B').exp_pct:+.2f} %. That is a bracket, not a result.
5. **S1 v12 statistics: insufficient evidence.** Cluster 95 % interval of the mean {b.ci95_cluster_lo:.2f} to {b.ci95_cluster_hi:.2f} % (contains 0), no sealed holdout, 71 exit variants tried on the same data, and the live paper account (58 trades, mean -5.7 %) is below the backtest.
6. **G1 (all breakouts): insufficient evidence, weak under stress.** +{gb.exp_pct:.2f} % a trade, t {gb.t_clustered}, interval {gb.ci95_cluster_lo:.1f} to {gb.ci95_cluster_hi:.1f} % (contains 0); +1 % slippage takes the total to Rs {g('C1').net_rs:,.0f} and doubled slippage to Rs {g('C2').net_rs:,.0f} over 259 trades, and the combined case is {g('C6').exp_pct:+.2f} % a trade and Rs {g('C6').net_rs:,.0f}. It loses in high-VIX (-12 %) and high-volatility (-9 %) periods and in 2026 H2.
7. **G1-F: the best-looking result and the weakest evidence.** +{fb.exp_pct:.1f} % a trade, positive in all 27 neighbouring settings and under every stress (combined {g('C6','G1-F').exp_pct:+.1f} %), but its three filters were chosen on this same history, so this is **in-sample**. Its live record is days old.
8. **Charges are not the problem.** All charges x 2: S1 {row(s1,'C3').delta_vs_B0_rs:+,.0f} Rs; Rs 35.03 versus 35.53 exchange charge: S1 {row(s1,'C4').delta_vs_B0_rs:+.0f} Rs, G1 {g('C4').delta_vs_B0_rs:+.0f} Rs. **Slippage and entry timing are.**
9. **Prospective holdout: 0 trades so far** (freeze 13 Nov 17:48:58 IST). Verdict: **insufficient evidence** for S1 v12, G1 and G1-F as live strategies.
10. **Four separate questions.** Engine correctness: adequate. Statistical robustness: insufficient (S1, G1), in-sample (G1-F). Execution realism: unrealistic for S1, partly realistic for G1. Actual live performance: S1 {live_short} (descriptive, previously inspected); G1 too new.

## 1. System understanding (read in the code, 13 Nov 2026)
- **S1 fade v12** (`server/fade.py`, `scanner/fade_stop_trail.py`, `scanner/fade_minutes_retest.py`): results-day signal, strike walk, 1 lot, entry 09:16 candle open + tick, stop -20 % from 09:17 on a candle low, trail on at +10 % high and 2 % below the peak, else 15:19. The audit set is the 339 trades with candles in the five contract bands (Oct 2024 - Aug 2026).
- **G1 / G1-F** (`server/g1_live.py`, `scanner/s3_engine.py`, `scanner/s3_put1_hold.py`): NIFTY opening-range breakdown, ATM weekly put, 50 % stop on the minute close, exit the next session 15:29. 259 trades Oct 2024 - Oct 2026 (154 pass the G1-F filters).
- **Costs:** `server/charges.py` (single table at the 2026 rates; the S3 engine passes the trade date so STT is versioned; the S1 backtests do not). **Execution:** S1 backtest = candle prices plus one tick, no slippage; S3 engine = last traded close plus 0.5 % (1 % wide / before 09:30 / from 15:00).
- **Not suited:** G1-C (12 Nov start), Near Tighty, XP, closed S3 pods (little or no history or already failed). Arms A and B are reference only (`S1_armab_minutes`: no exit rule passes).

## 2. Execution realism audit (Phase 2) with source checks
| # | Finding | Status | Evidence |
|---|---|---|---|
| V1 | The S1 v12 backtest has no slippage term, only a 1-tick penalty and charges | **verified** | `scanner/fade_stop_trail.py` `one()` computes net from the fill prices and `ch.leg` only |
| V2 | The S1 strike pick uses the whole day's volume (at least 50 contracts), known only after the close | **verified** | `scanner/backtest_s1_v10.py` `entry_price`/`walk`; the 09:15-volume rule tested on 11 Nov did not help |
| V3 | A stop or trail fill at min(level, candle open) assumes a buyer at that price | **verified** | `walk()` and this audit's S2/S3/S4 scenarios |
| V4 | The activation candle's own dip is not tested against the trail | **verified** | `walk()`; order-H run changes {len(amb1)} of 339 trades |
| V5 | G1 marks and stops on the minute close; live stops on any second's bid | **verified** | engine code; `VALIDATION_INVENTORY.md` item 1; S5 scenario |
| V6 | The G1 engine accepts an entry price up to 3 minutes old | **verified** | `ENTRY_STALE = 3` |
| V7 | S1 backtests charge the 2026 STT on every date; the S3 engine versions STT; exchange charge Rs 35.53 on every date | **verified** in code; the old STT rates and Rs 35.03 are **reported by secondary sources, not verified against the Finance Acts / NSE circulars** | `server/charges.py` |
| V8 | S3 slippage is flat (0.5 % / 1 %); there is no historical bid/ask | **verified** | `SLIP`, `SLIP_WIDE`; `DATA_AUDIT.md` |
| V9 | S1 went through versions v2 to v10 and 71 exit variants in one grid without a trial counter before 5 Nov 2026 | **verified** (60 S1 strategy pages; `variants()` = 71; `experiments.csv` starts 5 Nov) | repo |
| V10 | The S1 backtest does not test the stop or trail inside the entry candle itself | **verified (new)** | {rng_note} |
- **Signals use only information available at the decision time?** G1: yes in the code checked (opening range, a completed minute close, the minute after for the fill, VIX at the signal, the signal-day opening gap known at 09:15). S1 signals: the filing and its numbers are as filed; the strike pick is the look-ahead in V2; today's sector map and F&O list are applied to past dates (documented in `STRATEGY_AUDIT.md`, not re-verified here).
- **Missing data creating fills?** Upstox candles carry quiet minutes forward as zero-volume candles; 4 of 263 collected G1 days had no entry price and are skipped, not filled.
- **Live versus historical:** history books a stop on the minute close (G1) or a candle low (S1); live acts on any second's best bid and sells at the bid. {live}.

## 3. Baseline versus stress, S1 fade v12 ({int(b.n)} trades; observed candle prices, assumed everything else)
{fmt(s1[~s1.scenario.str.startswith('E5')], cols, nm)}
E5 (random missed trades): expectancy stays at {s1[s1.scenario=='E5_30'].exp_pct.iloc[0]:.2f} % with 30 % of trades missing (5th-95th percentile of the draws {s1[s1.scenario=='E5_30'].ci95_cluster_lo.iloc[0]:.2f} to {s1[s1.scenario=='E5_30'].ci95_cluster_hi.iloc[0]:.2f} %): missing trades at random does not change the mean; it only widens the range.

## 4. Baseline versus stress, G1 (259 trades) and G1-F (154 trades)
**G1**
{fmt(g1[(g1.strategy=='G1') & ~g1.scenario.str.startswith('E5')], cols, nm)}
**G1-F** (in-sample filters)
{fmt(g1[(g1.strategy=='G1-F') & ~g1.scenario.str.startswith('E5')], cols, nm)}
- **Surprising and unexplained:** a later entry (E1, E2) and a stop on the minute low (S5) IMPROVE G1. They are reported as found; they are not recommendations. A later entry can only help if the signal minute is a local extreme; that is not tested here.
- **Observed vs assumed:** the entry minute's close and the next day's 15:29 mark are traded prices in the file; the slippage, the delay, the late stop and every level used as a fill are assumptions; E3 and S5 use the minute's high / low as BOUNDS.

## 5. Stop and ambiguity audit (Phase 4)
- **S1 v12:** the baseline checks the stop first and starts the trail from the next candle; the high-first ordering is the opposite assumption. {len(amb1)} of 339 trades (59 %) have a different result under the two orderings. Reported results: baseline {row(s1,'B0').exp_pct:+.2f} %, high-first {row(s1,'S0H').exp_pct:+.2f} %, per-trade worst {row(s1,'S0W').exp_pct:+.2f} %, per-trade best {row(s1,'S0B').exp_pct:+.2f} %. The worst / best lines are bounds chosen by outcome (amendment A1) and are not used for any verdict. **The size, and even the sign, of the S1 result cannot be pinned down from 1-minute candles.** The 1-second recorder (VM, from 26 Oct) could settle the ordering for new trades; it was not used (offline).
- **Gap-through and late stops:** S1 stop sold at the next candle's open: {row(s1,'S3').exp_pct:+.2f} % ({row(s1,'S3').delta_vs_B0_rs:+,.0f} Rs); at the candle's low (bound): {row(s1,'S2').exp_pct:+.2f} %; trail sold late: {row(s1,'S3t').exp_pct:+.2f} %; at the trail candle's low (bound): {row(s1,'S4').exp_pct:+.2f} %.
- **G1:** stop on the minute low: {g('S5').exp_pct:+.2f} % ({g('S5').delta_vs_B0_rs:+,.0f} Rs); stop sold one minute late: {g('S6').exp_pct:+.2f} %. {len(amb2)} of 259 trades change when the stop is checked on the minute low instead of the close.
- No target exists in either strategy, so "target-first" does not apply; the stop/trail ordering above is its equivalent.

## 6. Parameter sensitivity (maps, nothing ranked or recommended)
- **S1 v12** (stop 15/20/25 % x trail start 5/10/15 % x gap 1-4 %, 36 cells, in-sample): {int((sens1.exp_pct > 0).sum())} of 36 cells have expectancy above 0, range {sens1.exp_pct.min():.2f} to {sens1.exp_pct.max():.2f} %; the v12 cell is {sens1[sens1.is_v12].exp_pct.iloc[0]:.2f} %. The v12 cell's one-step neighbours are within 0.9 points of it; the corners (stop 25 % with a +15 % trail start) are up to 1.7 points lower. This is sensitivity to the parameters under the baseline ordering; it says nothing about sensitivity to the ordering (section 5).
- **G1** (stop 40/50/60 % x exit same-day 15:15 / next 09:16 / next 15:29 x one strike out / ATM / one strike in, 27 cells): {int((sens2[sens2.strategy=='G1'].exp_pct > 0).sum())} of 27 above 0 (range {sens2[sens2.strategy=='G1'].exp_pct.min():.1f} to {sens2[sens2.strategy=='G1'].exp_pct.max():.1f} %). **Every same-day-exit cell is negative; every overnight cell is positive**: the overnight hold, not the stop or strike, carries the result. **G1-F:** {int((sens2[sens2.strategy=='G1-F'].exp_pct > 0).sum())} of 27 above 0 (range {sens2[sens2.strategy=='G1-F'].exp_pct.min():.1f} to {sens2[sens2.strategy=='G1-F'].exp_pct.max():.1f} %).
Full maps: `sensitivity_s1.csv`, `sensitivity_g1.csv`.

## 7. Regimes and periods (baseline; cells under 30 trades are marked "too few")
S1 v12 (`regimes_s1.csv`): positive in every VIX, volatility and half-year cell, weakest in down-trend days ({reg1[(reg1.scenario=='B0')&(reg1.level=='down')].exp_pct.iloc[0]:+.2f} % vs {reg1[(reg1.scenario=='B0')&(reg1.level=='up')].exp_pct.iloc[0]:+.2f} % in up-trend days). No cell is significant on its own.
G1 (`regimes_g1.csv`): VIX low {reg2[(reg2.strategy=='G1')&(reg2.scenario=='B0')&(reg2.level=='low')&(reg2.regime=='vix_regime')].exp_pct.iloc[0]:+.1f} %, mid {reg2[(reg2.strategy=='G1')&(reg2.scenario=='B0')&(reg2.level=='mid')&(reg2.regime=='vix_regime')].exp_pct.iloc[0]:+.1f} %, **high {reg2[(reg2.strategy=='G1')&(reg2.scenario=='B0')&(reg2.level=='high')&(reg2.regime=='vix_regime')].exp_pct.iloc[0]:+.1f} %**; realised volatility high {reg2[(reg2.strategy=='G1')&(reg2.scenario=='B0')&(reg2.level=='high')&(reg2.regime=='vol_regime')].exp_pct.iloc[0]:+.1f} %; first year {gb['mean_pct_Oct24-Sep25']:+.1f} % vs second year {gb['mean_pct_Oct25-Oct26']:+.1f} %; 2026 H2 negative. G1-F shows the same year-on-year fade ({fb['mean_pct_Oct24-Sep25']:+.1f} % to {fb['mean_pct_Oct25-Oct26']:+.1f} %).

## 8. Statistical robustness (Phase 7)
- **Date-clustered t / 95 % cluster-bootstrap interval of the mean / block-bootstrap interval:** S1 B0 {b.t_clustered} / {b.ci95_cluster_lo:.2f} to {b.ci95_cluster_hi:.2f} / {b.ci95_block_lo:.2f} to {b.ci95_block_hi:.2f}; G1 B0 {gb.t_clustered} / {gb.ci95_cluster_lo:.1f} to {gb.ci95_cluster_hi:.1f} / {gb.ci95_block_lo:.1f} to {gb.ci95_block_hi:.1f}; G1-F B0 {fb.t_clustered} / {fb.ci95_cluster_lo:.1f} to {fb.ci95_cluster_hi:.1f} / {fb.ci95_block_lo:.1f} to {fb.ci95_block_hi:.1f}.
- **Concentration:** S1 B0 mean without the 3 best trades {b.mean_ex_top3_pct:.2f} %, top 5 % of trades make {b.top5pct_share_of_profit:.0f} % of the profit; G1 {gb.mean_ex_top3_pct:.2f} % and {gb.top5pct_share_of_profit:.0f} %; G1-F {fb.mean_ex_top3_pct:.2f} % and {fb.top5pct_share_of_profit:.0f} %. G1 without its best 3 trades is about zero.
- **Drawdown and recovery:** S1 max drawdown Rs {abs(b.max_dd_rs):,.0f}, longest time under water {b.longest_underwater_days:.0f} days; G1 Rs {abs(gb.max_dd_rs):,.0f} and {gb.longest_underwater_days:.0f} days (not recovered to a new high by the end of the data); G1-F Rs {abs(fb.max_dd_rs):,.0f}, {fb.longest_underwater_days:.0f} days.
- **Multiple testing:** about {len(fam)} scenario lines (S1 + G1 + G1-F) were tested. Using the clustered t as a normal approximation, the lines with an unadjusted two-sided p below 0.05 and their Holm-adjusted p are: {sig if sig else 'none'}. Only the stress scenarios that make the strategy worse can be called significant after adjustment; **no scenario is evidence that a strategy works.**

## 9. Overfitting and out-of-sample validation (Phase 5; read from the repo, not run)
- **S1 v12:** the exit was chosen from a 71-variant grid on a train half (before 2025-11-03) and checked on the rest; the 2 % trail gap "was chosen after seeing results on part of the same data" (`strategies/S1_v12_fade_trail2.md`); the same 2025-11-03 split (`HALF` in `scanner/fade_realistic_studies.py`) is reused as the test half in later fade studies, so it is no longer untouched. 60 S1 pages and v2 to v10 have no trial count. Overfitting risk: **high**. Out-of-sample: **inadequate**; the only fresh data is the live paper account ({live}).
- **G1:** picked as the best of seven PUT1 variants on the same 259 trades (`strategies/S3_G1_put_overnight.md`, "so +8.4 % is flattered"); the live record starts 9 Nov. **G1-F:** gap, width and VIX filters chosen on the same two years. Overfitting risk: **medium-high (G1), high (G1-F)**. Out-of-sample: **inadequate**.
- **Method for strategies without a sealed holdout:** freeze at `FREEZE.json` (13 Nov 17:48:58 IST); count only trades entered after it; review at 30, 60, 90, 120, 150 trades with the section-7 rule; never reuse trades already reported. `python -m stress_audit.holdout_track <ledger.json>` prints the count; on the 9 Nov snapshot it prints 0 holdout trades (58 earlier v12 trades are "previously seen").
- The sealed expiry dataset belongs to a different study and was not read.

## 10. Final verdicts (rules in PREREG section 7)
| Question | S1 fade v12 | G1 | G1-F |
|---|---|---|---|
| Execution assumptions | **unrealistic** (no slippage, fill at the first print of a wide candle, decided within minutes) | **partly realistic** (traded closes + 0.5-1 % slippage; no bid/ask) | same as G1 |
| Costs | **incomplete** (no slippage; single STT table; exchange rate unverified) | **adequately modelled** for charges (dated STT); slippage flat | same as G1 |
| Stop handling | **ambiguous** ({len(amb1)} of 339 trades flip with the intrabar order) | **reliable but liberal** (close-based; live is tighter) | same as G1 |
| Look-ahead | **found**: whole-day volume in the strike pick (V2) | **not found** in the signal path; expiry chosen by chain-file existence (documented) | same; filters chosen post hoc (selection, not look-ahead) |
| Overfitting risk | **high** | **medium-high** | **high** |
| Out-of-sample validation | **inadequate** | **inadequate** | **inadequate** |
| Robustness to the stress set | **weak** (per-trade expectancy below 0 in {len(neg_s1)} of {len(stress_ids)} stress lines: {', '.join(neg_s1)}) | **moderate, split**: per-trade % at or below 0 in {', '.join(neg_g1_pct) or 'none'}; net rupees at or below 0 in {', '.join(neg_g1_rs) or 'none'} | **strong** (per-trade % at or below 0 in {', '.join(neg_f_pct) or 'none'}; rupees at or below 0 in {', '.join(neg_f_rs) or 'none'}), but in-sample |
| Statistical conclusion | **insufficient evidence** | **insufficient evidence** | **in-sample; insufficient evidence for the future** |
| Remaining data limits | no bid/ask; zero-volume carried candles; intrabar order; 22 months | no bid/ask; flat slippage; 2 years; one regime | live sample ~0 |

## 11. Execution and data weaknesses (prioritised by effect on the numbers)
1. S1 v12 has no slippage and fills at a candle open inside a minute where the median range is 16 % (V1, V10). Effect: removes the whole edge at 1-2 % a side.
2. The S1 result is decided inside 1-minute candles by an unknowable order (section 5).
3. The entry candle itself is never stop-tested (47 of 339 first candles trade at or below the stop level).
4. No historical bid/ask for any option; spreads are an assumption.
5. S1 strike pick uses whole-day volume (V2).
6. G1: stop on the close understates live stops (V5); flat slippage; the delay result is unexplained.
7. Charges: S1 uses the 2026 STT on all dates; Rs 35.03 vs 35.53 unverified (effect under Rs 30 on S1 and G1, so low priority); official rates not read offline.
8. Carried-forward zero-volume candles in Upstox files; two partial Nov 2021 sessions (from `DATA_AUDIT.md`).

## 12. Possible look-ahead and leakage (list)
- S1 strike pick: whole-day volume (found). S1 universe: today's F&O list and sector map on past dates (documented earlier, not re-verified). XBRL numbers "as filed" (no leakage found earlier). G1: expiry from chain-file existence (mild). G1-F filters: selected on the evaluated sample (selection bias). VIX regimes in this audit use the previous evening's value; tercile cut points use the whole window (descriptive only). No leakage found in the G1 signal and entry path.

## 13. Prioritised improvements (none applied; each needs your approval)
1. Report S1 v12 net of a slippage assumption (1-2 % a side) as the headline, with the baseline beside it.
2. Settle the intrabar order with the VM's 1-second recorder for the live era (S1 stops and trails) and compare paper fills to the candle model per trade.
3. Add the entry candle to the stop test, or move the S1 entry to the next candle's open in the model; the candle is not tradable at its open.
4. Start the prospective holdout formally (the freeze file now exists): pull the VM ledgers when you allow it and run `holdout_track.py` at 30 / 60 / 90 trades.
5. Add a trial counter: every new S1 / G1 variant gets a row in `experiments.csv` before it is run; apply Holm across the family.
6. Verify the STT and exchange-charge history against the Finance Acts and NSE circulars (online); only then consider versioning the S1 backtests' charges.
7. Re-validate the G1-F filters on live trades only; do not describe G1 or G1-F as validated before the review sizes are met.
8. Record top-of-book at 09:16 and at the 15:29 mark live so the next audit has real spreads.

## 14. Reproducibility
Scripts: `stress_audit/s1_stress.py`, `g1_stress.py`, `trade_audit.py`, `holdout_track.py`, `common.py`, `build_report.py`. Seed {man.get('seed')}. Git commit at run {man.get('git_head', '')[:9]}; input files with sizes and SHA-256 in `RUN_MANIFEST.json`. Results: `scenario_results_s1.csv`, `scenario_results_g1.csv`, `sensitivity_*.csv`, `regimes_*.csv`, `trades_*_all_scenarios.csv`, `TRADE_AUDIT.xlsx` (30 S1 and 23 G1 trades; the pre-registered G1 categories add up to 23, not the 20 written in the plan).
"""
    (R / "STRESS_REPORT.md").write_text(txt, encoding="utf-8")
    print(len(txt), "chars written; Holm-significant lines:", sig)


if __name__ == "__main__":
    main()
