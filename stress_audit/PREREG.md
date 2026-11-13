# Stress test and backtest reality audit: S1 fade v12, G1, G1-F (pre-registration, 13 Nov 2026)

Written and committed BEFORE any stress-test number is computed. Approved by the user on 13 Nov 2026 with 14 conditions (below).
Purpose: challenge the backtests, not improve them. No strategy rule, production engine, charge table, live server or VM is changed.
Everything runs offline on files already on this PC. No broker call, no API call, no VM connection.

## The user's conditions, and where each is met
1. Scope: S1 fade v12, G1 and G1-F. Arms A and B are reference cases only (baseline numbers copied from `S1_armab_minutes`, and the same
   execution stress run on them only if the fade run works; otherwise "not run").
2. The sealed expiry dataset (`expiry_research/data/sealed/`) is not opened, listed, read or hashed.
3. Live paper trades are the prospective holdout, counted only if the trade was ENTERED after the freeze time in `FREEZE.json`.
   G1 has very little live history; it is not called validated.
4. The exchange-charge difference Rs 35.03 versus Rs 35.53 per lakh is its own scenario. `server/charges.py` and every stored result are untouched;
   the rate is overridden only inside the audit's own process (`charges.configure`, never saved).
5. No optimisation. Parameter grids are sensitivity maps; no best cell is chosen, ranked or recommended.
6. Every scenario in this file is reported, negative or not. No trade is dropped except by a rule written here.
7. Observed prices and assumed execution prices are labelled in every table. Candle highs and lows are stress BOUNDS, never claimed fills.
8. Each run records the git commit hash, the dataset manifest (file names, sizes, SHA-256 for the files the run reads), the configuration, the random
   seed (20261113) and the run date/time, in `stress_audit/results/RUN_MANIFEST.json` and the registry row.
9. This file and `FREEZE.json` are committed first. Scripts that produce results are committed after, and the results after the run.
10. Offline only (see above).
11. Deliverables: trade-level audit workbook and technical report with all metrics and scenarios.
12. After the work: report and wait. No further change is made without approval.
13. Freeze date/time, strategy version and parameters are in `FREEZE.json`, written before any holdout tracking.
14. Where the sample is too small the verdict is "insufficient evidence" (rule in section 7).

## 1. Strategies and data

S1 fade v12 (stock options, bought, same day). Rule: results-day signal, strong numbers buy a put, weak numbers buy a call; strike walk from the money,
first strike with price >= Rs 2 and one lot Rs 600-8,000; entry 09:16 candle open + 1 tick; exit -20 % stop (from 09:17, candle low touches it, fill
min(stop, candle open) - 1 tick), trail on at a candle high >= +10 %, sold when a later candle low touches 0.98 x the highest high (fill min(level, open)
- 1 tick), else the 15:19 close - 1 tick. 1 lot, real charges, NO slippage term (the existing backtest has none; this is a finding, section 2).
- Backtest set: the 339 trades of `data/results/S1_fade_minutes_retest_trades.csv` (rows with `lot_ok` and `entry_B >= 2`), built from
  `S1_v10_{bandv10,band12,band050,band12q4,band050q4}_minutes.csv` (Upstox expired 1-minute traded-price candles, day 0). Oct 2024 - Aug 2026.
- Baseline B0 must reproduce `S1_fade_minutes_retest.md`: n 339, mean +2.86 %, total Rs 68,160, t 1.79 (tolerance: mean within 0.02 points). If it does
  not, the audit stops and reports the difference.
- Live comparison (descriptive, NOT holdout): the S1 paper ledger snapshot already on this PC (`paper_ledger.json`, saved 9 Nov 2026 15:29, copied
  from the earlier session's scratch folder, hashed in the manifest). Fresh live data cannot be pulled (offline).

G1 and G1-F (NIFTY puts, held overnight). Rule (`strategies/S3_G1_put_overnight.md`, live code `server/g1_live.py`): 09:15-09:29 opening range, the first
1-minute close below the low from 09:30 to 13:00, ATM put of the nearest weekly expiry after the signal day, 1 lot (65), bought the minute after the
signal; 50 % stop; exit the next session's 15:29 (live rule since 6 Nov 2026 13:32). G1-F takes the same trade when the next-day gap < +0.3 %, range
width not in 0.5-0.8 % and India VIX < 17.
- Baseline B0 = `scanner.s3_engine` at the current commit (dated STT) on NIFTY option and spot minutes in `../fo-index-data/data/index`
  (`options_1m`, `spot_1m`, `vix_daily.parquet`), 2024-10-01 to 2026-10-28, collected with `scanner.s3_put1_hold`'s own signal and expiry functions.
- B0 must reproduce `g1_research/results/g1_live_replay_trades.csv` (259 trades, 154 with `g1f`; total Rs 40,448 and 247,046 under the undated STT
  table that wrote that file; Rs 41,309 and 247,602 under the dated STT now in the engine, from `g1_research/CHARGES_DATED_RESULT.md`). Tolerance:
  trade count equal; total within Rs 5 of either figure. If not, the audit stops and reports it.
- Live evidence: G1 had its first live trade on 9 Nov 2026 (HANDOFF); the ledger (`data/g1_ledger.json`) is not on this PC. It is reported from the
  repo's own notes only and marked "not independently checked".

Not used: `expiry_research/data/sealed/`, G1-C (started 12 Nov), Near Tighty, XP, closed S3 pods, anything fetched online.

## 2. Findings to verify in the source before experiments (reported as verified / not verified)
- V1 S1 v12 backtest has no slippage term (`scanner/fade_stop_trail.py` `one()`). V2 S1 liquidity check uses the whole day's volume
  (`scanner/backtest_s1_v10.py` `walk`); the minute backtests inherit the pick. V3 stop fill min(stop, open) - tick assumes a counterparty at that price.
  V4 trail activation: the activating candle's own later low is not tested against the new peak (order inside a candle). V5 G1 engine marks and stops
  on the minute CLOSE; live stops on any second's bid. V6 engine entry price may be up to 3 minutes old (`ENTRY_STALE`). V7 S1 backtests charge STT at the
  2026 rate on all dates; the S3 engine versions STT by date; exchange charge 35.53 for all dates. V8 flat slippage in the S3 engine (0.5 %, 1 % far from the
  money, 09:15-09:30 and from 15:00). V9 trial history: S1 v2-v10 and the many fade variants have no trial counter before 5 Nov 2026.
  Each is marked verified (read in the code at the commit hash in the manifest) or not verified.

## 3. Scenarios (every one is run on every strategy where the data allows it)

Observed = a traded price in the candle files. Assumed = a price this audit chooses. Bound = a candle high/low used as the worst or best the minute allowed.

Costs and slippage (all fills assumed; applied on top of the observed price):
- C0 baseline unchanged (S1: tick penalty and charges only; G1: engine slippage and charges). C1 slippage +1 % of price per side (S1 adds it; G1 adds to the
  engine's). C2 slippage doubled: S1 uses 2 % per side (the daily test's mid-cap level) and also the daily test's own by-cap 1/2/3 % ("S1 daily-test
  slippage"); G1 uses 2 x the engine's. C3 charges x 2 (every component). C4 exchange charge Rs 35.03 per lakh instead of 35.53 (alone). C5 STT at the
  old undated table (reference for the reported G1 numbers). C6 combined: C2 slippage and C3 charges together. C7 volatile-day adversity: on the
  top decile of days by |NIFTY close-to-close return| (computed on the audit window) add 2 % slippage per side (S1) / 1 % (G1).

Execution timing (assumed unless stated):
- E1 entry one candle later (S1: 09:17 candle open + tick; G1: the engine's entry minute + 1). E2 entry two candles later. E3 entry at that candle's high
  (BOUND, not a fill). E4 no trade when the entry candle's range exceeds 10 % of its open (a thin-market skip, written here before results).
- E5 missed eligible entries: a random 10 %, 20 % and 30 % of trades not taken, 1,000 draws each, seed 20261113; report mean and 5th-95th percentile of
  expectancy and of total rupees.

Stops and exits:
- S0 baseline order inside a candle (S1: stop checked first, trail activation after the candle). S1 order-conservative: if a candle both reaches +10 % and,
  with the new high as the peak, touches the trail level, the trail sells in that candle (high first, then low). S1 order-optimistic is also computed and shown
  as the bracket's other end; it is never used as the baseline and never chosen.
- S2 stop fills at the stop candle's LOW (BOUND). S3 stop is detected on that candle but sold at the NEXT candle's open - 1 tick (assumed delay). S4 trail
  fills at the trail candle's low (BOUND). G1 only: S5 stop checked on the minute LOW instead of the close (touch, as live checks every second), fill
  min(stop level, that minute's open), and S6 stop checked on the minute close but sold one minute later (late fill).
- A trade with a missing next candle is exited at its last observed candle and flagged; none is dropped.

Parameter sensitivity (maps only, no ranking, nothing recommended):
- S1: stop {15, 20, 25} % x trail start {5, 10, 15} % x trail gap {1, 2, 3, 4} % = 36 cells. G1: stop {40, 50, 60} % x exit {same-day 15:15, next 09:16,
  next 15:29} x strike offset {one strike in the money, at the money, one strike out} = 27 cells. Each cell: n, expectancy, total Rs, win %. The report
  states the share of cells with expectancy above 0, the v12/G1 cell's position among its neighbours and the spread; it does not name a best cell.

Regimes and periods (all with n and the same metrics; cells with n < 30 are labelled "too few"):
- VIX terciles (India VIX daily close of the day before the trade, tercile cuts from the audit window). NIFTY trend: daily close above / below its 50-day
  average the day before. NIFTY 20-day realised-volatility terciles. Half-years. For G1: the day-1 range tercile as well.

## 4. Metrics (every scenario)
Net Rs, trades, expectancy per trade (mean net % of premium and mean Rs), win rate, average win, average loss, profit factor (gross profit / gross loss,
"inf" if no loss), maximum drawdown in Rs on the date-ordered cumulative sum of 1-lot trades, longest time under water (days) and days from the worst
trough to a new high, exposure (S1: mean minutes in position per trade and share of sessions with a position; G1: mean hours held and share of sessions
with a position), and the delta against B0 in Rs and in points. Every scenario table lists B0 on its first line.

## 5. Statistics
Date-clustered t (`scanner.stats.clustered_t`); 95 % confidence interval of the mean by a cluster bootstrap over trade DATES (5,000 draws, seed
20261113), which keeps same-day trades together; a moving-block bootstrap (blocks of 5 consecutive trade dates, 5,000 draws) as the time-dependence
check; mean without the top 3 trades and without the top 5 %; the share of total profit from the top 5 % of trades; consistency across halves; the
multiple-testing note: this audit runs about 60 scenarios and 2 sensitivity maps, so any single "significant" scenario is reported with a Holm adjustment
across the scenario family and is not a finding by itself. The audit makes no probabilistic claim about future profit.

## 6. Overfitting and validation assessment (read from the repo, not run)
Written from `DECISIONS.md`, `PROGRESS.md`, the strategy pages and `docs/research/experiments.csv`: where each parameter came from, whether it was chosen on
the data it is judged on, how many variants were tried (counted from the pages where stated; "not recorded" otherwise), and whether any untouched period
exists. Proposed process for strategies without a sealed holdout: (a) freeze the rules at `FREEZE.json`; (b) count only trades entered after it; (c)
review at a fixed number of trades written in advance (30, 60, 90, 120, 150) with the verdict rule in section 7; (d) never reuse trades already reported.
The `expiry_research` sealed data is not read; its existence is noted from the repo's own file names in `FINAL_TEST_PLAN.md` only.

## 7. Verdict rules (fixed now)
Per strategy and per question the label is one of: adequate / inadequate; low / medium / high; strong / moderate / weak; or "insufficient evidence".
- A result is "insufficient evidence" when n < 30 in the cell, or when the 95 % cluster-bootstrap interval of the expectancy contains 0 AND the
  block-bootstrap interval contains 0. It is not forced positive or negative.
- Positive evidence for a scenario needs: both bootstrap intervals above 0, mean > 0 in both halves, and mean still > 0 without the top 3 trades.
  Negative evidence needs both intervals below 0. Anything else = insufficient.
- Robustness: strong = the expectancy stays above 0 in C6 (combined), E1, S3 and the order-conservative variant; moderate = above 0 in some but not all;
  weak = below 0 in C6 or E1. Overfitting risk is judged only from the repo record (section 6), not from these runs.
- Backtest engine correctness (does it compute what it claims), statistical robustness, execution realism and live performance are four separate rows.

## 8. Trade-level audit (Excel, formatted)
Deterministic selection, seed 20261113: S1 fade, 30 trades; G1, 20 trades: the 3 largest wins, the 3 largest losses, 4 stop trades, 4 trail/time exits (S1)
or next-close exits (G1), 3 ambiguous-candle trades (S1 trades where one candle both touched the stop and reached +10 %; G1 trades where the minute close is
above the stop but the minute low is at or below it), 3 gap-through stops, and the 3 trades with the largest slippage-to-premium ratio; fill to the
count with a seeded random draw from the rest. Each row: signal time, order/entry minute, entry price (observed candle + assumed tick/slippage), stop and
trail levels, exit minute and price (observed + assumed), charges by component, net Rs, and a "candles around the event" sheet (the candles the decision used).
Live-vs-history differences are listed per trade when a live record exists.

## 9. Prospective holdout (freeze)
`FREEZE.json` records: freeze timestamp (IST), the commit hash of this pre-registration, strategy versions and exact parameters for S1 v12, G1 and G1-F, the
last commit that changed each live rule, and the counting rule: a paper trade counts only if its entry time is after the freeze timestamp, the rules at
the entry were those in the file, and the trade has not been reported before. `stress_audit/holdout_track.py` (offline) reads a ledger JSON file given to it,
counts such trades per strategy and prints n, mean, win rate and the verdict label of section 7; run on the snapshot now on this PC it must print 0 trades.
Live trades before the freeze (S1 from 22 Oct, G1 from 9 Nov) were seen and discussed before this audit: they are shown as "live, previously inspected,
descriptive" and are not holdout. G1 and G1-F are not described as validated until the review sizes in section 6 are reached with a passing verdict.

## 10. Limits stated now
No historical bid/ask, so spread is a stress assumption. Upstox candles are traded prices; quiet minutes are carried-forward and zero-volume. The S1 pick
used whole-day volume (hindsight). 22-24 months of data, one regime of the market, strategies chosen after seeing this data. Official charge rates, the
Finance Act texts and NSE circulars are not readable offline: charges stay "reported", the 35.03 rate is a stress case only. The VIX series and NIFTY
regimes come from files already on this PC. Anything the data cannot support is reported as "not run" with the reason.

## 11. Outputs
`stress_audit/results/`: `STRESS_REPORT.md` (technical audit, baseline vs stress, strategy-by-strategy robustness, weaknesses, look-ahead and leakage list,
parameter sensitivity, validation assessment, prioritised improvements), `scenario_results.csv` (one row per strategy x scenario x metric set),
`sensitivity_s1.csv`, `sensitivity_g1.csv`, `TRADE_AUDIT.xlsx`, `RUN_MANIFEST.json`. A row in `docs/research/experiments.csv`. Scripts in `stress_audit/`.
