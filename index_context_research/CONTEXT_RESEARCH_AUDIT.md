# Audit of the index market-context research (17 Nov 2026)

Forensic audit of the work done 15-17 Nov. **Read-only:** no backtest was run, no rule or parameter changed, no dataset downloaded or generated, no existing result changed, no sealed or holdout data opened, the live system untouched. The only computations were descriptive reads of existing files (stated where used). Every statement names its file.
Plain-words answer first, then sections A to G, then the executive summary.

## Short answers
- **Was the previous work mostly a quarterly NIFTY-vs-strategy comparison?** Partly. The statement "nothing known at the start of a quarter predicted good or bad quarters" came from a quarterly test on the **S1 fade (19 quarters)**, not on G1-F or any index strategy. The quarterly NIFTY-vs-G1-F table and the every-period report are **descriptive only**. The only predictive tests on the index strategies are the **trade-level context study** (67 cells).
- **Is "our strategies do not work consistently" justified?** Not by the context research. What the evidence supports: the strategies' results differ across periods; the options-based conditions were weakly tested; the market-condition questions that matter most for G1-F were **mostly not tested**. See the executive summary.

---
## A. What we actually tested (inventory)

### Tests executed (inferential)
**T1. Index context study, Stage 1 + validation (16-17 Nov).** Files: `index_context_research/PREREG_CONTEXT.md`, `scripts/build_dataset.py`, `scripts/analyse_context.py`, `results/context_dataset.csv`, `ctx_stage1_discovery.csv`, `ctx_frozen.csv`, `ctx_validation.csv`, registry `E-20261116-CTX`.
- Question: does any information known before entry separate better from worse trades of G1, G1-F, G1-C, XP?
- Data: NIFTY option replays (G1 259, G1-F 154, G1-C 235 priced of 240, XP 107 expiry days), Oct 2024 to Oct 2026; 17 features (gap, VIX level / 5-day change / 1-year percentile at the signal, GIFT settlement basis and previous-session change, S&P 500 previous session, NIFTY future price and OI change, FII index-futures long share and its change, ATM IV, put-call OI, put-call IV skew, breadth proxy, event window, expiry day).
- Timeframe: per trade (daily entry dates). Variables compared: trade net % above vs below the discovery median (event_window and expiry_day: 1 vs 0).
- Method: Welch t of the difference of means, bootstrap interval, Benjamini-Hochberg 10 % over the 67 cells tested in discovery (entries to 2025-09-30), validation (from 2025-10-01) once for survivors.
- Observations: discovery G1 128, G1-F 75, G1-C 112, XP 52; validation the rest.
- Result: 1 survivor (XP, 5-day VIX change), reversed in validation; 6 cells nominal p < 0.05; none corrected.
- Establishes: with these 17 features and a median split, no single factor shows a very large effect in this sample.
- Does NOT establish: that no factor matters. See section E (power, range restriction, binary splits, no interactions).

**T2. Quarterly regime check of the S1 fade (15 Nov).** Files: `index_research/scripts/regime_quarters.py`, `results/regime_quarters.csv`, registry `E-20261115-Y2`.
- Question: do start-of-quarter market conditions predict a good or bad quarter of the **S1 fade** (daily-candle same-day result)?
- Data: S1 trade files 2022-01 to 2026-09 and NIFTY / VIX daily. Quarterly; variables: previous-quarter NIFTY return, VIX at the previous close, NIFTY above 200-day average, previous-quarter fade result (and two same-quarter measures for reference).
- Method: Spearman rank correlation. Observations: 19 quarters (two with fewer than 10 trades; 5 to 85 trades per quarter).
- Result: all rho between -0.06 and +0.25 for what is known in advance; none significant.
- Establishes: with 19 quarters, no *strong* link to those four S1-fade variables.
- Does NOT establish: anything about G1-F or any index strategy, anything about individual trades, or "nothing predicts". **The sentence "nothing known at the start of a quarter predicted good or bad quarters" referred to this test, was given in answer to a question about good and bad years, and should not have been read as covering the index strategies.**

**T3. Earlier external-factor tests on G1 follow-through (7-9 Nov), registry E-20261107-0x to E-20261109-0x; files `g1_research/*_RESULT.md`.** Score (10 methods), formation shapes, 5-year spot follow-through, FII/DII positions (three variants: 16-27 features), GDELT news tone, heavyweight stocks, holding patterns, IV crush, minimum break size, ATM vs ITM. Target: max up / follow-through of the G1 breakout, mostly on NIFTY **spot** moves, not option trades. No candidate. These tested *follow-through of breakouts*, not G1-F's period-to-period profitability.

**T4. Stress audit regime splits (13 Nov), `stress_audit/results/regimes_g1.csv`, `STRESS_REPORT.md` section 7.** G1 and S1 by VIX and volatility terciles and by year: descriptive, G1 loses in high VIX (-12.1 %), no tests.

### Analyses that were only descriptive
- **Quarterly NIFTY move vs G1-F, G1, G1-C and XP (17 Nov chat answers).** No test was run; I read the table and described patterns ("puts follow the market"). **Not saved as a script:** the NIFTY-by-year and quarter tables in those answers were produced by inline Python that was not committed; only their outputs exist in `index_context_research/EVERY_PERIOD_RESULTS.md` (also generated inline) and in chat. They are reproducible in principle (the method is stated in section E) but there is no script file. This is a reproducibility gap.
- `index_context_research/EVERY_PERIOD_RESULTS.md`, `YEARLY_INDEX_PERFORMANCE.md`, `results/ctx_yearly.csv`: years, quarters, months, weekday, expiry day vs not, previous-close trend, gap and VIX terciles, top-5 % concentration. Descriptive; no tests.
- Year-by-year daily vs daily comparison (15 Nov): `data/results/S1_daily_vs_minute_vs_live.md` (S1 fade, arms; Welch t between consecutive years) and `index_research/results/Y1_by_year.md` (daily futures-proxy studies sliced by year, Covid excluded). Year-to-year changes, not predictors.
- Daily-candle analogs (A7, `results/DP_summary.md`) and model-priced proxy replay (A8, `results/PX_*.md`): extensions of history, not market-context tests.

### Hypotheses discussed but never tested
GIFT gap up / down / flat and the difference between the overnight indication and the actual open; FII / DII cash flows; news sentiment and news events as conditions on trades; global risk-on / risk-off beyond the S&P 500 daily move; Asian markets; USD/INR; crude oil; real market breadth; sector performance; five-bucket market direction (strongly bullish to strongly bearish); trending vs range-bound sessions; intraday reversals; breakouts and failed breakouts as conditions; large directional days; interactions between any two factors for G1-F.

### Attempted but failed or discarded
- First context-analysis run skipped XP through an `n < 60` rule that was not in the plan (corrected before validation; recorded in `EXPERIMENT_MANIFEST.json`).
- First proxy replay discarded (unrepaired VIX minutes 2021-23); R02 and the combination study re-run (`index_research/PROGRAM.md` A8 erratum). The context study itself was **not** affected: it used VIX only from Oct 2024 plus a 250-session percentile reaching back to about Oct 2023, which is after the faulty period (2021-10 to 2023-08).
- `yfinance` is not installed in the environment, so no new Yahoo data could be fetched; GIFT fetch by `urllib` timed out (curl worked).

### Data available but never used (details in section D)
DII index-futures and all participant **options** positions (the participant files hold them); `data/parents` USDINR, Brent crude, copper, aluminium, iron ore; GDELT (not in the context dataset); NIFTYBANK and SENSEX spot (not used as conditions); the 1-second NIFTY recorder (Nov 2026 only); NIFTY option chain end-of-day (9 days).

---
## B. What we discovered (what the existing files support)
1. **At trade level, no single one of 17 features gave a large, correctable effect** on G1, G1-F, G1-C or XP; one discovery survivor reversed (`OUT_OF_SAMPLE_VALIDATION.md`).
2. **Nominal near-misses** (not significant after correction): ATM IV (G1 puts better in low IV, t -2.5, p 0.012; G1-C calls better in high IV, t +2.1) and put-call OI for G1-C (t +2.7, p 0.007). Opposite signs for puts and calls.
3. **G1-F** (`ctx_yearly.csv`, `EVERY_PERIOD_RESULTS.md`): positive in 6 of the 7 quarters with 10 or more trades by mean %, negative in 2026 Q3 (-11.2 %, 33 trades). In **rupees** 2025 Q4 is also negative (-Rs 6,741) although its mean % is +2.4 (percent averages and rupee sums can disagree when premiums differ). Both 2025 Q4 and 2026 Q3 are lower-return quarters; the two biggest quarters (2025 Q1 +54 %, 2026 Q1 +55 %) are both in flat-to-falling market quarters. These are observations, not tests.
4. G1 puts follow the market in the quarterly table (good when NIFTY fell, weak when it rose), G1-C calls lose in most quarters, XP loses in most quarters (descriptive, 9 quarters).
5. Daily-candle analogs and the proxy replay show the put edge absent before Oct 2024 and the pattern sign-flipping with the market era (other studies; not context tests).

---
## C. What we did not test (G1-F and the others), against your list
**A. Direction.** Not tested as five buckets. Available only as: previous close above or below its 20-day average (`trend_prev`, descriptive split only, never tested), the quarter's NIFTY move (descriptive, 9 quarters, **not** a known-in-advance condition). Untested: strongly / moderately bullish, sideways, bearish regimes as trade-level conditions.
**B. Volatility.** Tested (G1-F included): VIX level at the signal, 5-day VIX change, 1-year VIX percentile (median splits). Not tested: "normal" vs "high" bands with fixed cut-offs, rising / falling over other windows, sudden expansion (a one-day jump), VIX vs realised volatility. Caution: G1-F by construction only trades VIX < 17.
**C. Overnight.** Tested only as **daily GIFT settlement proxies** (previous-session basis and change). Untested: gap-up / gap-down / flat GIFT classes, indication vs actual open (the 09:00 GIFT level is not in the data).
**D. Institutional.** Tested: FII index-futures long share and its 1-day change. Untested: FII / DII cash net buying and selling (not available historically), DII at all in the trade tests, both-buying / both-selling, FII-DII divergence, participant options positions (the files exist).
**E. News and external events.** Tested: a yes / no flag for RBI / Budget / FOMC dates (10 to 15 trades per set). Untested: news sentiment on trade days (GDELT exists but was only used against G1 spot follow-through on 7-9 Nov), election events, global risk-on / off, the other days' events, any 5 / 15 / 30 / 60-minute reaction.
**F. Market structure.** Tested: opening gap (G1-F is restricted to gap < +0.3 %), expiry day yes / no. Untested: trending vs range-bound sessions (opening-range width is a G1-F filter but not a tested factor), intraday reversals, failed breakouts, large directional moves, the breakout minute's timing as a condition (tested for G1-C optimization only).
**Also untested:** any pair or interaction of conditions (the plan allowed pairs only after a single-factor survivor), nonlinear / bucketed effects beyond a median split, quarter-level conditions for the index strategies, per-trade conditions for the 2026 Q3 losses.

---
## D. Available data inventory (local, nothing downloaded for this audit)
- **NIFTY, NIFTYBANK, SENSEX spot 1-minute:** `../fo-index-data/data/index/spot_1m/`, 2021-10-20 to 2026-10-28, complete on session days; aligned to trades by timestamp. Used (NIFTY).
- **India VIX 1-minute:** same store; **2021-10 to 2023-08 has unrepaired rows in the raw files; use `index_data.load.vix_1m`** (repaired). Daily: `vix_daily.parquet` 2008-2026-10. Used.
- **NIFTY options 1-minute with OI:** `options_1m/NIFTY`, `SENSEX`, Oct 2024 to Oct 2026; OI present for most rows (put-call OI missing on 2 % of trades). Used.
- **NIFTY / BANKNIFTY daily options and futures (price, OI):** `options_daily/`, 2018 to 2026-10. Used for the futures price / OI change only.
- **GIFT NIFTY:** `index_context_research/data/gift/` (git-ignored; fetched 16 Nov): daily settlement prices of the index futures (NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY and others) and combined OI, 861 weekdays 10 Jul 2023 to 13 Nov 2026, **daily only**. The 09:00 level is not available. 547 of 861 days overlap the NIFTY daily-close file; the dataset joins it to trades from Oct 2024 (1 to 2 % missing). Used as two daily proxies.
- **FII / DII:** `g1_research/data/external/participant_oi/`, one file per day 2021-09-01 to 2026-11-06 (1,280): Client, DII, FII, Pro and total, index and stock futures long / short, **index options call / put long / short**. Cash-market FII / DII flows: **not available**. Used: FII index-futures long share only (previous session). Unused: DII, Client, Pro, all options positions.
- **News:** `g1_research/data/external/gdelt/` daily tone and volume 2021-2026 (global machine-scored, one number a day). Scheduled event dates (RBI, Budget, FOMC, US election) in `scanner/s3_buy4.py` from Oct 2024 only. Used: event flag only; GDELT not in the context dataset.
- **Global:** `data/parents/` (Yahoo, cached 2020-04-01 to 2026-09-25, daily; hourly for some): ^GSPC (S&P 500), USDINR=X, BZ=F (Brent), HG=F, ALI=F, TIO=F, INFY. Used: S&P only. USD/INR and crude exist and were never used. A DECISIONS entry (S2 screen B, 18 Oct) records that the Yahoo Brent daily and hourly series disagree by 4-7 % on some days: crude needs checking before use. No Nasdaq, no Asian indices, no US VIX.
- **Breadth / sectors:** `data/eod2/` (473 files) and `data/sector_map.csv` (440 stocks to sector indices): today's F&O list applied to the past (survivorship); sector aggregates could be built but were not. NIFTY 50 constituents at the time are not stored.
- **Intraday volatility, gaps, ranges, trend days:** derivable from the spot minutes; only the opening gap and opening-range width were used.
- **Option chain snapshots:** `chain_eod/` 9 days; `nifty_1s/` 1-second NIFTY recorder, 2-17 Nov 2026 only (too short).
- **Expiry calendars:** `expiries.parquet` and bhavcopy; the expiry-day flag was built.
- **Strategy trade records:** `g1_research/results/g1_live_replay_trades.csv` (G1 259 / G1-F 154), `g1_research/data/g1c_opt_trades.csv` (G1-C), `g1_research/data/xp_history_minute.csv` (XP). No BANKNIFTY / SENSEX option-trade records for these rules; live ledgers are on the VM (not accessible).

---
## E. Methodological weaknesses (what could make the conclusions misleading)
1. **The quarterly claim rested on S1 fade, n = 19.** Nine quarters of G1-F (seven with 10+ trades) cannot establish that conditions known on each trade day carry no information. A quarter averages 17 to 27 G1-F trades under many different daily conditions.
2. **Low power at trade level.** G1-F discovery has 75 trades; the standard deviation of a trade's net % is about 104 points, so the standard error of a half-vs-half difference is about 24 points and a corrected-significance effect needs roughly **70 to 80 points** (G1-F's whole average is +25). G1: about 57 points; G1-C about 51; XP about 77. Only very large effects could have been seen. (Descriptive arithmetic from `context_dataset.csv`; not a new test.)
3. **Range restriction on G1-F.** Its filters (gap < +0.3 %, VIX < 17, width) were applied before the context test, so the gap and VIX tests on G1-F run on a truncated range (G1-F max gap 0.29 %, max VIX 16.9 vs G1 4.9 % and 26.3). The full G1 set covers the wider range but also mixes in the losing trades G1-F excludes.
4. **Binary median splits, no interactions.** Information is discarded and conditional or non-monotonic effects (e.g. low IV and falling market together) are invisible.
5. **Multiple-testing correction assumes independence.** G1-F is a subset of G1, G1 (puts) and G1-C (calls) are the two sides of the same daily breakout on different days of the same markets and use the same feature values, and XP trades expiry days that overlap other days' conditions: the 67 cells are strongly dependent, so the corrected threshold is only an approximation.
6. **Selection bias.** G1-F's three filters were chosen from tables on the same history (strategy page; stress audit). Everything measured on G1-F is in-sample for those filters.
7. **Proxies, not the real variables.** GIFT is a daily settlement (not the pre-open level); breadth is survivorship-biased; IV is Black-Scholes from last-trade prices (no bid / ask); the US overnight move is the S&P only; event flag counts are 9 to 18 trades.
8. **Market return per quarter is computed from the first close in the quarter, not the previous quarter's last close.** This drops the first day's return: differences up to about 1.7 points (2025 Q2: 10.15 % computed vs 8.49 % correct; 2026 Q4 partial: 1.23 % vs 0.35 %). The direction of every quarter is unchanged, but the figures in the 17 Nov answers and `EVERY_PERIOD_RESULTS.md` carry this small error. `regime_quarters.csv`'s `prev_q_nifty` and `same_q_nifty` use the same method. **Not corrected here (no results were rewritten).**
9. **Percent vs rupee disagreement.** Mean net % per trade and total Rs can have opposite signs (G1 and G1-F 2025 Q4), because % averages ignore premium size. Both are reported in the files, but the prose in some answers cited percent only.
10. **Costs and slippage.** All trade returns come from the S3 engine (`scanner/s3_engine.py`): slippage 0.5 % of premium a side (1 % for 2+ strikes from the money or 09:15-09:30 / from 15:00), charges from `server/charges.py` (brokerage, STT, exchange, SEBI, stamp, GST). The G1 replay file used by the context dataset was written with the **undated 2026 STT table** (G1 Rs 40,448, G1-F Rs 247,046); the dated STT replay gives Rs 41,309 and Rs 247,602 (`stress_audit`, `g1_research/CHARGES_DATED_RESULT.md`): a difference below 0.5 %, no sign changes. Flat slippage (no bid / ask) remains an assumption.
11. **Trade-to-period assignment.** Trades are assigned to the quarter of their **entry day**; G1 holds overnight, so the last trades of a quarter close in the next one. Quarter labels for 2026 Q4 (3 to 7 trades, to 28 Oct) are partial.
12. **Concentration.** G1's top 5 % of trades earned Rs 298,305 against a set total of Rs 40,448; G1-F's top 5 % Rs 190,146 of Rs 247,046 (`ctx_yearly.csv`). Means are strongly influenced by a few trades; medians (-18 % to -51 %) and win rates (24 % to 48 % by year) were reported but not used in any test.
13. **Reconciliation.** Quarterly Rs sums equal the yearly sums equal the totals of the replay files (G1 40,448; G1-F 247,046) because all come from the same trade rows. G1-C is 235 trades in the context set versus 240 signals (5 had no price); XP is 107 of 108 rows. No unexplained difference was found.
14. **Look-ahead.** Features were checked as known before the entry minute (VIX at the signal minute, gap at the open, previous-session GIFT / futures / FII / S&P). The quarterly **same-quarter** NIFTY and VIX figures (T2, descriptive table) are **not** known in advance and were labelled so. No look-ahead was found in T1, but the check was by reading the code and the plan, not by an automated test.
15. **Reproducibility.** The context study has scripts and a manifest; T4 / the every-period report and the "NIFTY by year" table were made with inline code that was never saved as a script.
16. **Pre-registration timing.** The context study's plan was written and hashed (`EXPERIMENT_MANIFEST.json`) but not committed before the run, as the mission asked; the hash makes later edits detectable.

---
## F. G1-F investigation gaps
What exists (descriptive reads of `context_dataset.csv` for this audit, no tests):
- **Profitable quarters** (2024 Q4, 2025 Q1, 2025 Q2, 2026 Q1; +33 %, +54 %, +20 %, +55 %): NIFTY moved -8 %, -1 %, +8 %, -15 %; average ATM IV 15.5 / 15.7 / 15.1 / 10.6; average VIX 14.2 / 14.4 / 15.0 / 11.9. No common level of VIX or IV; two were falling-market quarters.
- **Weak quarters** (2025 Q3 +4.5 %, 2025 Q4 +2.4 %): the lowest VIX-percentile quarters (average 3.5 and 15.5 vs 31-70 elsewhere) and the lowest ATM IV (10.8). 2026 Q1 also had low IV (10.6) but was strongly profitable, so low volatility alone does not explain it.
- **Losing quarter** (2026 Q3, -11.2 %, 33 trades, the largest recent sample): average VIX 12.0, VIX percentile 36 (middling), ATM IV 11.3, NIFTY about -5 %, previous close above its 20-day average on 42 % of trades (vs 56 % in other quarters), a larger 5-day VIX fall (-2.8 vs -1.2), GIFT basis lower (0.18 vs 0.28 %). Nothing stands out as an obvious separator; each difference is small compared with the trade-to-trade spread.
- **Winning vs losing G1-F trades** (63 winners, 91 losers): the means and medians of 14 pre-entry features are nearly identical (gap -0.05 / -0.05, VIX 12.9 / 12.5, ATM IV 12.5 / 12.5, put-call OI 0.92 / 0.90, trend-prev 52 % / 53 %); the largest differences are expiry-day trades (33 % of winners, 20 % of losers) and put-call IV skew (+0.38 vs -0.10 points). Not tested for significance; the context study's own tests on these features were not significant (G1-F cells: gap p 0.07, event window p 0.15, skew p 0.16).
- **Still not understood:** which combinations of conditions precede the very large winners (the top 5 % earn 77 % of G1-F's rupees); whether the 2026 Q3 losses cluster by day-of-week, by expiry distance (days to expiry), by the time of the breakout, by a particular move size, or by the next-day open (the overnight gap matters because exits are the next close); how G1-F behaves as a function of the NIFTY **direction in the following sessions** (the strategy holds a put overnight, so the realised next-day move is the whole outcome); whether the losing trades share a failed-breakout pattern (price back inside the range soon after entry); how often 2026 Q3 stops were hit versus earlier quarters (the stop rate by quarter was not tabulated).
- **Do not conclude:** that G1-F works consistently, or that one losing quarter breaks it. The G1-F sample is 154 trades over two years with filters chosen on the same data.

---
## G. Recommended next research stages (priority order; nothing started)
**1. Trade-level G1-F loss anatomy (no new data).**
- Question: what distinguishes G1-F trades that stop out or lose from those that profit, using only existing fields (days to expiry, breakout minute, depth beyond the range, opening range width, next-day gap, hold outcome, stop timing)?
- Data: `g1_live_replay_trades.csv`, spot minutes, option minutes; Method: descriptive tables first (stop rate and result by quarter, by days to expiry, by breakout time, by next-day open gap), then pre-registered logistic or regularised regression on win / loss with all pre-entry fields and cross-validation by time.
- Output: ranked list of conditions with intervals. Risks: n 154, overfitting, filters already tuned on the same data; report effect sizes with bootstrap intervals, no thresholds chosen on the evaluation data.

**2. Market-regime classification known before the open, tested on all four sets.**
- Question: do five direction regimes (e.g. NIFTY vs its 20 / 50 / 200-day averages and recent return) and three volatility regimes change results at trade level?
- Data: spot minutes and VIX (repaired) from 2021; trade sets from Oct 2024, plus the model-priced proxy replay (A8) for 2021-2024 with its caveats. Method: pre-registered buckets, one-way and two-way tables, mixed-effects or clustered standard errors, walk-forward across years.
- Output: regime x strategy table with intervals. Risks: only about 2 years of real trades; proxy prices; many cells.

**3. Overnight and gap dimension.**
- Question: does the actual NIFTY open versus the previous close, and any pre-open indication, change G1-F's outcome?
- Data: gap from spot is available now; real GIFT pre-open prices would need a new source (vendor or NSE IX intraday). Method: bucketed gap and continuous gap vs outcome; compare with GIFT basis once pre-open data exists. Output: gap-by-outcome tables. Risk: the GIFT daily settlement is not the pre-open level and must not be presented as such.

**4. Institutional positioning with the full participant files.**
- Question: do DII, Client, Pro and the options-positioning columns, and FII-DII divergence, relate to G1-F and G1 outcomes?
- Data: participant OI (available, no cash flows). Method: standardised changes, trade-level regression, BH. Output: factor table. Risk: positions are not flows; many columns; dependence between columns.

**5. Global and macro context from data already stored.**
- Question: do USD/INR, crude (after checking its quality), the S&P and VIX-like measures add information?
- Data: `data/parents` (to 2026-09-25 only). Method: previous-session changes as pre-entry features; trade-level tests with correction. Risk: Yahoo data issues, coverage ending before the latest trades.

**6. News and event windows with timestamps.**
- Question: do scheduled and unexpected news categories change results?
- Data: event dates exist for Oct 2024 on; a timestamped news archive does not. Method: event-window flags with minute data around the announcements; interactions with strategy entries. Risk: 10 to 15 trades per category; do not read anything into it without more data.

**7. Interactions and combinations (only after 1-6).**
- Pairs among factors that show consistent signs in trade-level analysis, evaluated with time-ordered cross-validation; ablation vs the original rule. Risks: dependence between factors, sample size, in-sample filters.

**8. Quarter-level analysis done correctly (small, but fixes the gap).**
- Redo the NIFTY-vs-strategy quarter table with correct market returns, rupee and percent side by side, using a saved script; report that nine quarters can only describe, not test.

**9. Live record.** The prospective holdout (frozen 13 Nov 17:48:58 IST) and the live paper ledgers remain the only out-of-sample evidence; join conditions to live trades as they accrue.

---
## Executive summary
1. **What exactly did we test?** (a) A trade-level study of 17 pre-entry factors on G1, G1-F, G1-C and XP (67 cells, discovery plus one validation); (b) a quarterly test of start-of-quarter conditions on the **S1 fade** (19 quarters); (c) descriptive year / quarter / month / weekday tables for the index strategies; (d) daily-candle analogs and a model-priced replay for earlier years.
2. **How comprehensive was it?** Moderate in the number of factors (17) and honest about failures, but narrow in method: median splits only, no interactions, no regime buckets, tiny samples (G1-F 75 in discovery), and several important variables were proxies.
3. **What important information did we leave out?** Real GIFT pre-open data; FII / DII cash flows; DII and options positioning (files exist but unused); news with timestamps; USD/INR, crude and global markets (data exists); breadth with real constituents; five-way market-direction regimes; trending vs range days; intraday reversals and failed breakouts; any combination of conditions; trade-by-trade anatomy of G1-F's losses.
4. **Did we investigate whether market conditions predict G1-F performance?** Only partly: single factors at trade level on 75 discovery trades (nothing significant, but the test could only detect very large effects and the gap / VIX tests are range-restricted by G1-F's own filters), plus descriptive quarter tables. The **quarterly "nothing predicts" claim did not test G1-F at all.**
5. **Most important missing research:** a trade-level G1-F loss anatomy and a pre-registered market-regime study (direction x volatility x gap) on all four strategies, using the data we already have, with correct market-return calculations and saved scripts.
6. **Are the conclusions strong enough to say our strategies do not work consistently?** The evidence supports "results vary a lot between periods and are not proven", not "no market condition explains it". The context research was too low-powered and too narrow to show that conditions do not matter. It also cannot show the strategies fail: G1-F is in-sample, 154 trades, and one losing quarter is not conclusive. The honest status is "unproven and not yet understood".

**Stopping here, as asked. No further research has been started.**
