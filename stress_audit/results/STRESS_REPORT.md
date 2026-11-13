# Stress test and backtest reality audit: S1 fade v12, G1, G1-F

Run: git 3fa031ee3, 2026-11-13T18:10:16+05:30, seed 20261113. Pre-registered in `stress_audit/PREREG.md` (+ `AMENDMENTS.md`), committed before any result.
Offline: existing files only. No production rule, engine, charge table, live server or VM was changed. The sealed expiry data was not opened.
**Purpose: challenge the numbers, not improve them. No parameter was tuned. Every scenario of the pre-registration is reported below, including the negative ones.**

## 0. The answer in ten lines
1. **Engine correctness: adequate.** The S1 baseline reproduces the existing result exactly (339 trades, +2.86 %, Rs 68,160, t 1.79). The G1 simulator matches `scanner/s3_engine.py` to the rupee on all 259 trades (largest difference Rs 0.00) and reproduces the stored replay (Rs 40,448 / 247,046 under the old STT table, Rs 41,309 / 247,602 under the dated one).
2. **S1 fade v12: the +2.9 % a trade shrinks quickly under execution stress.** Slippage of 1 % a side takes it to +0.89 %, 2 % to -1.13 %, one candle later entry to -1.53 %, and the combined case to -2.36 %. The baseline has **no slippage term at all**.
3. **S1 v12 is a first-minutes trade.** 136 stops and 203 trails, **0 exits at 15:19**; the median trade is closed 3 minutes after the entry candle. Its whole result is decided by the 09:16-09:20 candles, where median 09:16 candle range 16.4 % of its open; 72 % of the 339 first candles have a range above 10 %; 47 of 339 first candles already trade at or below the -20 % stop level and 115 reach the +10 % trigger inside the entry minute (computed in this run from the candle files).
4. **S1 v12 depends on the unknowable order inside a candle.** Under the opposite high-before-low ordering 200 of 339 trades change and the result falls to +0.23 %. The per-trade bounds run from -2.33 % to +5.42 %. That is a bracket, not a result.
5. **S1 v12 statistics: insufficient evidence.** Cluster 95 % interval of the mean -0.35 to 5.92 % (contains 0), no sealed holdout, 71 exit variants tried on the same data, and the live paper account (58 trades, mean -5.7 %) is below the backtest.
6. **G1 (all breakouts): insufficient evidence, weak under stress.** +5.54 % a trade, t 0.942, interval -5.8 to 17.2 % (contains 0); +1 % slippage takes the total to Rs -3,102 and doubled slippage to Rs 5,545 over 259 trades, and the combined case is +3.06 % a trade and Rs -11,194. It loses in high-VIX (-12 %) and high-volatility (-9 %) periods and in 2026 H2.
7. **G1-F: the best-looking result and the weakest evidence.** +19.7 % a trade, positive in all 27 neighbouring settings and under every stress (combined +16.8 %), but its three filters were chosen on this same history, so this is **in-sample**. Its live record is days old.
8. **Charges are not the problem.** All charges x 2: S1 -20,658 Rs; Rs 35.03 versus 35.53 exchange charge: S1 +23 Rs, G1 +27 Rs. **Slippage and entry timing are.**
9. **Prospective holdout: 0 trades so far** (freeze 13 Nov 17:48:58 IST). Verdict: **insufficient evidence** for S1 v12, G1 and G1-F as live strategies.
10. **Four separate questions.** Engine correctness: adequate. Statistical robustness: insufficient (S1, G1), in-sample (G1-F). Execution realism: unrealistic for S1, partly realistic for G1. Actual live performance: S1 58 trades, mean -5.7 % of premium, 47 % won (descriptive, previously inspected); G1 too new.

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
| V4 | The activation candle's own dip is not tested against the trail | **verified** | `walk()`; order-H run changes 200 of 339 trades |
| V5 | G1 marks and stops on the minute close; live stops on any second's bid | **verified** | engine code; `VALIDATION_INVENTORY.md` item 1; S5 scenario |
| V6 | The G1 engine accepts an entry price up to 3 minutes old | **verified** | `ENTRY_STALE = 3` |
| V7 | S1 backtests charge the 2026 STT on every date; the S3 engine versions STT; exchange charge Rs 35.53 on every date | **verified** in code; the old STT rates and Rs 35.03 are **reported by secondary sources, not verified against the Finance Acts / NSE circulars** | `server/charges.py` |
| V8 | S3 slippage is flat (0.5 % / 1 %); there is no historical bid/ask | **verified** | `SLIP`, `SLIP_WIDE`; `DATA_AUDIT.md` |
| V9 | S1 went through versions v2 to v10 and 71 exit variants in one grid without a trial counter before 5 Nov 2026 | **verified** (60 S1 strategy pages; `variants()` = 71; `experiments.csv` starts 5 Nov) | repo |
| V10 | The S1 backtest does not test the stop or trail inside the entry candle itself | **verified (new)** | median 09:16 candle range 16.4 % of its open; 72 % of the 339 first candles have a range above 10 %; 47 of 339 first candles already trade at or below the -20 % stop level and 115 reach the +10 % trigger inside the entry minute (computed in this run from the candle files) |
- **Signals use only information available at the decision time?** G1: yes in the code checked (opening range, a completed minute close, the minute after for the fill, VIX at the signal, the signal-day opening gap known at 09:15). S1 signals: the filing and its numbers are as filed; the strike pick is the look-ahead in V2; today's sector map and F&O list are applied to past dates (documented in `STRATEGY_AUDIT.md`, not re-verified here).
- **Missing data creating fills?** Upstox candles carry quiet minutes forward as zero-volume candles; 4 of 263 collected G1 days had no entry price and are skipped, not filled.
- **Live versus historical:** history books a stop on the minute close (G1) or a candle low (S1); live acts on any second's best bid and sells at the bid. 58 closed v12 paper trades up to 9 Nov 2026 (ledger snapshot saved 9 Nov 15:29): mean -5.69 % of premium, 47 % won (holdout_track.py on the snapshot; previously inspected, so descriptive only).

## 3. Baseline versus stress, S1 fade v12 (339 trades; observed candle prices, assumed everything else)
| scenario | description | price type | n | exp % | net Rs | win % | PF | max DD Rs | t | CI lo | CI hi | vs B0 Rs | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | baseline: existing v12 rule, order L (stop first), tick penalty + charges, no slippage | observed candle + assumed tick | 339 | 2.86 | 68,160 | 55.20 | 1.39 | -11,235 | 1.79 | -0.35 | 5.92 | 0.00 | insufficient evidence (interval contains 0) |
| S0H | order H: high before low inside a candle (as pre-registered) | assumed ordering | 339 | 0.23 | 16,549 | 54.30 | 1.10 | -15,635 | 0.16 | -2.47 | 2.86 | -51,611 | insufficient evidence (interval contains 0) |
| S0W | BRACKET low end: per trade the worse of order L and order H (by outcome, a bound) | BOUND | 339 | -2.33 | -31,984 | 50.10 | 0.82 | -36,839 | -1.75 | -4.90 | 0.19 | -100,144 | bound only - not used for a verdict |
| S0B | BRACKET high end: per trade the better of order L and order H (by outcome, a bound) | BOUND | 339 | 5.42 | 116,694 | 59.30 | 1.71 | -8,498 | 3.28 | 2.15 | 8.53 | 48,534 | bound only - not used for a verdict |
| C1 | slippage 1 % of price per side | assumed | 339 | 0.89 | 28,930 | 53.40 | 1.15 | -13,842 | 0.57 | -2.22 | 3.89 | -39,230 | insufficient evidence (interval contains 0) |
| C2a | slippage 2 % per side (2 x the mid-cap level) | assumed | 339 | -1.13 | -8,476 | 51.30 | 0.96 | -20,002 | -0.73 | -4.20 | 1.83 | -76,636 | insufficient evidence (interval contains 0) |
| C2b | S1 daily-test slippage by cap (1 / 2 / 3 % per side) | assumed | 339 | -0.69 | -829 | 50.70 | 1.00 | -24,811 | -0.44 | -3.81 | 2.37 | -68,989 | insufficient evidence (interval contains 0) |
| C3 | all charges x 2 | assumed | 339 | 1.60 | 47,502 | 55.20 | 1.26 | -11,861 | 1.00 | -1.60 | 4.64 | -20,658 | insufficient evidence (interval contains 0) |
| C4 | exchange charge Rs 35.03 per lakh (stress only; production keeps 35.53) | assumed | 339 | 2.86 | 68,183 | 55.20 | 1.39 | -11,234 | 1.79 | -0.35 | 5.92 | 23.00 | insufficient evidence (interval contains 0) |
| C5s | STT by trade date (informational; baseline charges the 2026 STT on every date) | assumed | 339 | 2.90 | 68,830 | 55.20 | 1.40 | -11,213 | 1.81 | -0.32 | 5.96 | 670 | insufficient evidence (interval contains 0) |
| C6 | combined: slippage 2 % per side and charges x 2 | assumed | 339 | -2.36 | -29,077 | 50.10 | 0.87 | -35,360 | -1.53 | -5.42 | 0.59 | -97,237 | insufficient evidence (interval contains 0) |
| C7 | volatile-day adversity: +2 % slippage per side on the top decile of |NIFTY| days | assumed | 339 | 2.31 | 57,478 | 54.60 | 1.32 | -12,097 | 1.46 | -0.86 | 5.31 | -10,682 | insufficient evidence (interval contains 0) |
| E1 | entry one candle later (09:17 open + tick) | assumed | 339 | -1.53 | -31,369 | 49.60 | 0.85 | -42,287 | -1.16 | -4.18 | 1.08 | -99,529 | insufficient evidence (interval contains 0) |
| E2 | entry two candles later (09:18 open + tick) | assumed | 339 | -2.92 | -56,026 | 49.00 | 0.73 | -66,763 | -2.65 | -5.09 | -0.66 | -124,186 | negative evidence |
| E3 | entry at the 09:16 candle HIGH | BOUND | 339 | -7.10 | -138,563 | 38.60 | 0.49 | -139,746 | -4.89 | -9.86 | -4.26 | -206,723 | negative evidence |
| E4 | skip trades whose 09:16 candle range exceeds 10 % of its open | assumed rule | 95 | 1.19 | 3,908 | 53.70 | 1.07 | -12,179 | 0.31 | -5.63 | 9.35 | -64,252 | insufficient evidence (interval contains 0) |
| S2 | stop sells at the stop candle's LOW | BOUND | 339 | 0.73 | 31,958 | 55.20 | 1.15 | -14,610 | 0.42 | -2.72 | 4.08 | -36,202 | insufficient evidence (interval contains 0) |
| S3 | stop detected on its candle, sold at the NEXT candle's open - tick | assumed | 339 | 2.50 | 61,624 | 55.50 | 1.34 | -11,585 | 1.52 | -0.79 | 5.64 | -6,536 | insufficient evidence (interval contains 0) |
| S3t | trail sold at the NEXT candle's open - tick | assumed | 339 | 2.28 | 52,612 | 51.00 | 1.29 | -18,164 | 1.31 | -1.18 | 5.62 | -15,548 | insufficient evidence (interval contains 0) |
| S4 | trail sells at the trail candle's LOW | BOUND | 339 | -0.84 | -6,569 | 48.40 | 0.96 | -18,181 | -0.55 | -3.86 | 2.10 | -74,729 | insufficient evidence (interval contains 0) |
| C8 | worst case: E1 + slippage 2 % + charges x 2 + stop at next open | assumed | 339 | -7.64 | -152,098 | 38.10 | 0.47 | -160,896 | -5.39 | -10.45 | -4.86 | -220,258 | negative evidence |

E5 (random missed trades): expectancy stays at 2.88 % with 30 % of trades missing (5th-95th percentile of the draws 1.23 to 4.50 %): missing trades at random does not change the mean; it only widens the range.

## 4. Baseline versus stress, G1 (259 trades) and G1-F (154 trades)
**G1**
| scenario | description | price type | n | exp % | net Rs | win % | PF | max DD Rs | t | CI lo | CI hi | vs B0 Rs | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | baseline: live rule, ATM put, 50 % stop on the minute close, sold next session 15:29, engine slippage, dated STT | observed minute closes + assumed slippage | 259 | 5.54 | 41,309 | 34.40 | 1.06 | -114,441 | 0.94 | -5.82 | 17.18 | 0.00 | insufficient evidence (interval contains 0) |
| C1 | slippage +1 % of price per side added to the engine's | assumed | 259 | 3.55 | -3,102 | 33.60 | 1.00 | -143,177 | 0.62 | -7.54 | 14.92 | -44,411 | insufficient evidence (interval contains 0) |
| C2 | slippage doubled (2 x the engine's 0.5 % / 1 %) | assumed | 259 | 3.94 | 5,545 | 34.00 | 1.01 | -137,776 | 0.68 | -7.19 | 15.41 | -35,764 | insufficient evidence (interval contains 0) |
| C3 | all charges x 2 | assumed | 259 | 4.65 | 24,538 | 34.00 | 1.03 | -124,238 | 0.79 | -6.68 | 16.27 | -16,771 | insufficient evidence (interval contains 0) |
| C4 | exchange charge Rs 35.03 per lakh (stress only; production keeps 35.53) | assumed | 259 | 5.54 | 41,336 | 34.40 | 1.06 | -114,435 | 0.94 | -5.82 | 17.18 | 27.00 | insufficient evidence (interval contains 0) |
| C5 | STT at the old undated 2026 table (how the stored replay was written) | assumed | 259 | 5.49 | 40,448 | 34.40 | 1.06 | -114,686 | 0.94 | -5.85 | 17.13 | -861 | insufficient evidence (interval contains 0) |
| C6 | combined: slippage x 2 and charges x 2 | assumed | 259 | 3.06 | -11,194 | 33.60 | 0.98 | -148,375 | 0.53 | -8.03 | 14.53 | -52,503 | insufficient evidence (interval contains 0) |
| C7 | volatile-day adversity: +1 % slippage per side on the top decile of |NIFTY| days | assumed | 259 | 5.26 | 34,581 | 34.40 | 1.05 | -118,103 | 0.90 | -6.05 | 16.85 | -6,728 | insufficient evidence (interval contains 0) |
| E1 | entry one minute later (same strike) | assumed | 259 | 6.32 | 48,071 | 35.10 | 1.07 | -105,209 | 1.07 | -5.18 | 17.88 | 6,762 | insufficient evidence (interval contains 0) |
| E2 | entry two minutes later (same strike) | assumed | 259 | 7.54 | 66,060 | 36.30 | 1.10 | -105,531 | 1.28 | -3.91 | 19.14 | 24,751 | insufficient evidence (interval contains 0) |
| E3 | entry at the entry minute's HIGH | BOUND | 259 | 2.89 | -25,274 | 32.40 | 0.97 | -154,302 | 0.51 | -7.98 | 14.29 | -66,583 | insufficient evidence (interval contains 0) |
| E4 | skip trades whose entry-minute range exceeds 10 % of its open | assumed rule | 223 | 8.98 | 90,986 | 35.00 | 1.15 | -106,673 | 1.38 | -3.07 | 21.84 | 49,677 | insufficient evidence (interval contains 0) |
| S5 | stop checked on every minute's LOW (as live checks every second), sold at min(stop level, that minute's open) | BOUND | 259 | 6.44 | 60,433 | 34.40 | 1.09 | -107,267 | 1.10 | -4.79 | 18.06 | 19,124 | insufficient evidence (interval contains 0) |
| S6 | stop detected on the close, sold one minute later | assumed | 259 | 5.71 | 45,179 | 34.40 | 1.07 | -110,192 | 0.97 | -5.62 | 17.40 | 3,870 | insufficient evidence (interval contains 0) |
| C8 | worst case: E1 + slippage x 2 + charges x 2 + stop sold one minute late | assumed | 259 | 3.77 | -1,449 | 33.20 | 1.00 | -136,273 | 0.65 | -7.28 | 15.27 | -42,758 | insufficient evidence (interval contains 0) |

**G1-F** (in-sample filters)
| scenario | description | price type | n | exp % | net Rs | win % | PF | max DD Rs | t | CI lo | CI hi | vs B0 Rs | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | baseline: live rule, ATM put, 50 % stop on the minute close, sold next session 15:29, engine slippage, dated STT | observed minute closes + assumed slippage | 154 | 19.70 | 247,602 | 40.90 | 1.87 | -41,611 | 2.41 | 4.28 | 35.92 | 0.00 | positive evidence |
| C1 | slippage +1 % of price per side added to the engine's | assumed | 154 | 17.35 | 220,001 | 40.30 | 1.75 | -44,078 | 2.17 | 2.27 | 33.19 | -27,601 | insufficient evidence (interval contains 0) |
| C2 | slippage doubled (2 x the engine's 0.5 % / 1 %) | assumed | 154 | 17.75 | 223,880 | 40.90 | 1.76 | -43,348 | 2.20 | 2.55 | 33.64 | -23,722 | insufficient evidence (interval contains 0) |
| C3 | all charges x 2 | assumed | 154 | 18.73 | 237,617 | 40.90 | 1.82 | -42,894 | 2.30 | 3.33 | 34.93 | -9,985 | insufficient evidence (interval contains 0) |
| C4 | exchange charge Rs 35.03 per lakh (stress only; production keeps 35.53) | assumed | 154 | 19.70 | 247,617 | 40.90 | 1.87 | -41,610 | 2.41 | 4.28 | 35.92 | 15.00 | positive evidence |
| C5 | STT at the old undated 2026 table (how the stored replay was written) | assumed | 154 | 19.66 | 247,046 | 40.90 | 1.87 | -41,611 | 2.41 | 4.24 | 35.87 | -556 | positive evidence |
| C6 | combined: slippage x 2 and charges x 2 | assumed | 154 | 16.79 | 213,920 | 40.30 | 1.72 | -44,740 | 2.09 | 1.62 | 32.65 | -33,682 | insufficient evidence (interval contains 0) |
| C7 | volatile-day adversity: +1 % slippage per side on the top decile of |NIFTY| days | assumed | 154 | 19.45 | 245,068 | 40.90 | 1.86 | -41,611 | 2.39 | 4.02 | 35.56 | -2,534 | positive evidence |
| E1 | entry one minute later (same strike) | assumed | 154 | 20.80 | 254,821 | 42.90 | 1.91 | -41,899 | 2.56 | 5.40 | 36.74 | 7,219 | positive evidence |
| E2 | entry two minutes later (same strike) | assumed | 154 | 21.34 | 258,584 | 44.20 | 1.93 | -39,234 | 2.61 | 5.93 | 37.43 | 10,982 | positive evidence |
| E3 | entry at the entry minute's HIGH | BOUND | 154 | 16.29 | 202,983 | 38.30 | 1.65 | -49,497 | 2.06 | 1.36 | 31.99 | -44,619 | insufficient evidence (interval contains 0) |
| E4 | skip trades whose entry-minute range exceeds 10 % of its open | assumed rule | 131 | 23.56 | 250,896 | 41.20 | 2.08 | -41,611 | 2.61 | 6.59 | 42.09 | 3,294 | positive evidence |
| S5 | stop checked on every minute's LOW (as live checks every second), sold at min(stop level, that minute's open) | BOUND | 154 | 20.36 | 251,750 | 40.90 | 1.90 | -41,318 | 2.51 | 5.02 | 36.40 | 4,148 | positive evidence |
| S6 | stop detected on the close, sold one minute later | assumed | 154 | 19.74 | 247,439 | 40.90 | 1.87 | -41,449 | 2.42 | 4.23 | 35.91 | -163 | positive evidence |
| C8 | worst case: E1 + slippage x 2 + charges x 2 + stop sold one minute late | assumed | 154 | 17.63 | 221,848 | 40.90 | 1.76 | -44,812 | 2.21 | 2.55 | 33.47 | -25,754 | insufficient evidence (interval contains 0) |

- **Surprising and unexplained:** a later entry (E1, E2) and a stop on the minute low (S5) IMPROVE G1. They are reported as found; they are not recommendations. A later entry can only help if the signal minute is a local extreme; that is not tested here.
- **Observed vs assumed:** the entry minute's close and the next day's 15:29 mark are traded prices in the file; the slippage, the delay, the late stop and every level used as a fill are assumptions; E3 and S5 use the minute's high / low as BOUNDS.

## 5. Stop and ambiguity audit (Phase 4)
- **S1 v12:** the baseline checks the stop first and starts the trail from the next candle; the high-first ordering is the opposite assumption. 200 of 339 trades (59 %) have a different result under the two orderings. Reported results: baseline +2.86 %, high-first +0.23 %, per-trade worst -2.33 %, per-trade best +5.42 %. The worst / best lines are bounds chosen by outcome (amendment A1) and are not used for any verdict. **The size, and even the sign, of the S1 result cannot be pinned down from 1-minute candles.** The 1-second recorder (VM, from 26 Oct) could settle the ordering for new trades; it was not used (offline).
- **Gap-through and late stops:** S1 stop sold at the next candle's open: +2.50 % (-6,536 Rs); at the candle's low (bound): +0.73 %; trail sold late: +2.28 %; at the trail candle's low (bound): -0.84 %.
- **G1:** stop on the minute low: +6.44 % (+19,124 Rs); stop sold one minute late: +5.71 %. 137 of 259 trades change when the stop is checked on the minute low instead of the close.
- No target exists in either strategy, so "target-first" does not apply; the stop/trail ordering above is its equivalent.

## 6. Parameter sensitivity (maps, nothing ranked or recommended)
- **S1 v12** (stop 15/20/25 % x trail start 5/10/15 % x gap 1-4 %, 36 cells, in-sample): 36 of 36 cells have expectancy above 0, range 1.15 to 2.91 %; the v12 cell is 2.86 %. The v12 cell's one-step neighbours are within 0.9 points of it; the corners (stop 25 % with a +15 % trail start) are up to 1.7 points lower. This is sensitivity to the parameters under the baseline ordering; it says nothing about sensitivity to the ordering (section 5).
- **G1** (stop 40/50/60 % x exit same-day 15:15 / next 09:16 / next 15:29 x one strike out / ATM / one strike in, 27 cells): 18 of 27 above 0 (range -1.5 to 10.0 %). **Every same-day-exit cell is negative; every overnight cell is positive**: the overnight hold, not the stop or strike, carries the result. **G1-F:** 27 of 27 above 0 (range 2.3 to 21.3 %).
Full maps: `sensitivity_s1.csv`, `sensitivity_g1.csv`.

## 7. Regimes and periods (baseline; cells under 30 trades are marked "too few")
S1 v12 (`regimes_s1.csv`): positive in every VIX, volatility and half-year cell, weakest in down-trend days (+1.53 % vs +4.35 % in up-trend days). No cell is significant on its own.
G1 (`regimes_g1.csv`): VIX low +10.7 %, mid +17.8 %, **high -12.1 %**; realised volatility high -9.4 %; first year +8.4 % vs second year +2.7 %; 2026 H2 negative. G1-F shows the same year-on-year fade (+25.3 % to +14.4 %).

## 8. Statistical robustness (Phase 7)
- **Date-clustered t / 95 % cluster-bootstrap interval of the mean / block-bootstrap interval:** S1 B0 1.79 / -0.35 to 5.92 / 0.24 to 5.49; G1 B0 0.942 / -5.8 to 17.2 / -7.2 to 16.4; G1-F B0 2.411 / 4.3 to 35.9 / 0.3 to 35.3.
- **Concentration:** S1 B0 mean without the 3 best trades 1.75 %, top 5 % of trades make 30 % of the profit; G1 0.70 % and 41 %; G1-F 12.38 % and 36 %. G1 without its best 3 trades is about zero.
- **Drawdown and recovery:** S1 max drawdown Rs 11,235, longest time under water 109 days; G1 Rs 114,441 and 528 days (not recovered to a new high by the end of the data); G1-F Rs 41,611, 258 days.
- **Multiple testing:** about 49 scenario lines (S1 + G1 + G1-F) were tested. Using the clustered t as a normal approximation, the lines with an unadjusted two-sided p below 0.05 and their Holm-adjusted p are: [('S1 fade v12 C8', 0.0, 0.0), ('S1 fade v12 E3', 0.0, 0.0), ('S1 fade v12 E2', 0.0081, 0.3806), ('G1-F E2', 0.0089, 0.4116), ('G1-F E4', 0.009, 0.4116), ('G1-F E1', 0.0106, 0.4672), ('G1-F S5', 0.0121, 0.5221), ('G1-F S6', 0.0157, 0.6591), ('G1-F B0', 0.0159, 0.6591), ('G1-F C4', 0.0159, 0.6591), ('G1-F C5', 0.0161, 0.6591), ('G1-F C7', 0.0168, 0.6591), ('G1-F C3', 0.0217, 0.802), ('G1-F C8', 0.0274, 0.9858), ('G1-F C2', 0.0275, 0.9858), ('G1-F C1', 0.0302, 1.0), ('G1-F C6', 0.0368, 1.0), ('G1-F E3', 0.0399, 1.0)]. Only the stress scenarios that make the strategy worse can be called significant after adjustment; **no scenario is evidence that a strategy works.**

## 9. Overfitting and out-of-sample validation (Phase 5; read from the repo, not run)
- **S1 v12:** the exit was chosen from a 71-variant grid on a train half (before 2025-11-03) and checked on the rest; the 2 % trail gap "was chosen after seeing results on part of the same data" (`strategies/S1_v12_fade_trail2.md`); the same 2025-11-03 split (`HALF` in `scanner/fade_realistic_studies.py`) is reused as the test half in later fade studies, so it is no longer untouched. 60 S1 pages and v2 to v10 have no trial count. Overfitting risk: **high**. Out-of-sample: **inadequate**; the only fresh data is the live paper account (58 closed v12 paper trades up to 9 Nov 2026 (ledger snapshot saved 9 Nov 15:29): mean -5.69 % of premium, 47 % won (holdout_track.py on the snapshot; previously inspected, so descriptive only)).
- **G1:** picked as the best of seven PUT1 variants on the same 259 trades (`strategies/S3_G1_put_overnight.md`, "so +8.4 % is flattered"); the live record starts 9 Nov. **G1-F:** gap, width and VIX filters chosen on the same two years. Overfitting risk: **medium-high (G1), high (G1-F)**. Out-of-sample: **inadequate**.
- **Method for strategies without a sealed holdout:** freeze at `FREEZE.json` (13 Nov 17:48:58 IST); count only trades entered after it; review at 30, 60, 90, 120, 150 trades with the section-7 rule; never reuse trades already reported. `python -m stress_audit.holdout_track <ledger.json>` prints the count; on the 9 Nov snapshot it prints 0 holdout trades (58 earlier v12 trades are "previously seen").
- The sealed expiry dataset belongs to a different study and was not read.

## 10. Final verdicts (rules in PREREG section 7)
| Question | S1 fade v12 | G1 | G1-F |
|---|---|---|---|
| Execution assumptions | **unrealistic** (no slippage, fill at the first print of a wide candle, decided within minutes) | **partly realistic** (traded closes + 0.5-1 % slippage; no bid/ask) | same as G1 |
| Costs | **incomplete** (no slippage; single STT table; exchange rate unverified) | **adequately modelled** for charges (dated STT); slippage flat | same as G1 |
| Stop handling | **ambiguous** (200 of 339 trades flip with the intrabar order) | **reliable but liberal** (close-based; live is tighter) | same as G1 |
| Look-ahead | **found**: whole-day volume in the strike pick (V2) | **not found** in the signal path; expiry chosen by chain-file existence (documented) | same; filters chosen post hoc (selection, not look-ahead) |
| Overfitting risk | **high** | **medium-high** | **high** |
| Out-of-sample validation | **inadequate** | **inadequate** | **inadequate** |
| Robustness to the stress set | **weak** (per-trade expectancy below 0 in 8 of 15 stress lines: C2a, C2b, C6, E1, E2, E3, S4, C8) | **moderate, split**: per-trade % at or below 0 in none; net rupees at or below 0 in C1, C6, E3, C8 | **strong** (per-trade % at or below 0 in none; rupees at or below 0 in none), but in-sample |
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
Scripts: `stress_audit/s1_stress.py`, `g1_stress.py`, `trade_audit.py`, `holdout_track.py`, `common.py`, `build_report.py`. Seed 20261113. Git commit at run 3fa031ee3; input files with sizes and SHA-256 in `RUN_MANIFEST.json`. Results: `scenario_results_s1.csv`, `scenario_results_g1.csv`, `sensitivity_*.csv`, `regimes_*.csv`, `trades_*_all_scenarios.csv`, `TRADE_AUDIT.xlsx` (30 S1 and 23 G1 trades; the pre-registered G1 categories add up to 23, not the 20 written in the plan).
