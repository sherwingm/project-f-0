# S1 fade · weak results in market hours: does an already-corrected filing day predict the next day's call?

Pre-registered: strategies/S1_weak_result_day_reversal.md. D = the stock's move from the minute before the announcement to the filing day's 15:29 close, minus NIFTY 50's. Corrected = D <= -2 %. Next day = the fade's day 0: gap = close to next open; next day = next open to next close (market-adjusted). Calls = the v10 backtest's real call trades for these filings (entry at the open, sold 15:20, net of charges). t date-clustered.

Weak market-hours cases: 66; matched fade call trades: 59.

## Test: **FAIL (nothing changes)**

| test | value | pass |
|---|---|---|
| 1 at least 20 corrected call trades | 13 | False |
| 2a corrected calls mean > 0 in 2022-24 | 49.77 | True |
| 2b corrected calls mean > 0 in 2025-26 | -15.79 | False |
| 3a corrected - not corrected > 0 in 2022-24 | 57.35 | True |
| 3b corrected - not corrected > 0 in 2025-26 | -6.38 | False |
| 4 pooled corrected t >= 2 | 0.958 | False |

## The fade's call trades (v10, 15:20 exit)

| group | window | n | win % | mean net % | median net % | total Rs | t |
|---|---|---|---|---|---|---|---|
| corrected (D <= -2 %) | 2022-24 | 7 | 57.1 | 49.77 | 60.1 | 22135 | 1.533 |
| corrected (D <= -2 %) | 2025-26 | 6 | 50 | -15.79 | -1.17 | -7029 | -1.069 |
| corrected (D <= -2 %) | all | 13 | 53.8 | 19.51 | 1.46 | 15106 | 0.958 |
| not corrected (D > -2 %) | 2022-24 | 27 | 18.5 | -7.58 | -19.31 | -10579 | -0.555 |
| not corrected (D > -2 %) | 2025-26 | 19 | 36.8 | -9.41 | -34.88 | -8822 | -0.704 |
| not corrected (D > -2 %) | all | 46 | 26.1 | -8.34 | -19.8 | -19401 | -0.866 |

## The stock the next day (market-adjusted %)

| group | window | N | gap mean | gap median | gap up % | gap t | next day mean | next day median | next day up % | next day t |
|---|---|---|---|---|---|---|---|---|---|---|
| corrected (D <= -2 %) | 2022-24 | 9 | -1.227 | -1.126 | 22.2 | -2.968 | 0.146 | 1.497 | 55.6 | 0.09 |
| corrected (D <= -2 %) | 2025-26 | 6 | -1.678 | -1.129 | 40 | -1.662 | -1.634 | 0.288 | 60 | -0.746 |
| corrected (D <= -2 %) | all | 15 | -1.388 | -1.128 | 28.6 | -3.243 | -0.49 | 0.298 | 57.1 | -0.384 |
| not corrected (D > -2 %) | 2022-24 | 30 | -0.347 | -0.515 | 31 | -1.37 | -0.262 | 0.146 | 51.7 | -0.609 |
| not corrected (D > -2 %) | 2025-26 | 21 | -0.35 | -0.414 | 33.3 | -1.012 | 0.413 | 0.517 | 66.7 | 0.967 |
| not corrected (D > -2 %) | all | 51 | -0.349 | -0.464 | 32 | -1.708 | 0.021 | 0.406 | 58 | 0.07 |

## By filing-day move

| D bucket | cases | next-day move mean % | call n | call win % | call mean net % | call median net % | call total Rs | call t |
|---|---|---|---|---|---|---|---|---|
| <= -3 % | 10 | 0.272 | 9 | 66.7 | 28.45 | 6.72 | 15385 | 1.115 |
| -3..-1 % | 14 | -1.017 | 12 | 25 | -16.62 | -23.29 | -13730 | -1.279 |
| -1..+1 % | 23 | -0.04 | 22 | 27.3 | -7.4 | -18.15 | -4257 | -0.474 |
| > +1 % | 19 | 0.294 | 16 | 25 | -1.48 | -27.79 | -1693 | -0.085 |

## The same calls with v11's exit (minutes, Oct 2024 on; descriptive)

| group | n | win % | mean net % | median net % | total Rs | t |
|---|---|---|---|---|---|---|
| corrected (D <= -2 %) | 7 | 28.6 | 9.94 | -21.13 | 4739 | 0.525 |
| not corrected (D > -2 %) | 20 | 25 | -8.03 | -22.08 | -7344 | -0.693 |

Cases: data/results/S1_weak_day_reversal_cases.csv; trades: S1_weak_day_reversal_trades.csv.

## Independent verification (2026-10-20; three separate checks, nothing taken from this script)
- **Recompute from the raw files:** every call-trade number matches exactly:
  - 66 cases, 59 calls;
  - corrected 13 calls: +49.77 / −15.79 / +19.51 %;
  - not corrected 46 calls: −7.58 / −9.41 %.
  - D is identical in all 66 cases.
- **One fix after the check:** two filings came the day before a special session that the NIFTY minute files lack
  (M&M 2023-11-10 → Muhurat 2023-11-12; AMBUJACEM 2026-01-30 → Budget Sunday 2026-02-01). The next session now comes
  from the F&O bhavcopy calendar, and those two get no market-adjusted next-day value. The corrected gap is now
  −1.39 % (14 cases), as the independent recompute found. The trade results did not change.
- **Bias audit:**
  - no look-ahead: D uses only filing-day prices;
  - all 59 trades are on the first session after the filing;
  - no missing-minute fallbacks; no corporate action in the gaps;
  - all 59 calls are weak on the trade's own numbers.
- **Robustness (descriptive):**
  - **Other thresholds:** at every D threshold from −1 % to −3 %, adjusted or raw, the 2025-26 corrected calls lose
    (−7.7 to −25.4 %).
  - **Ranking:** the rank correlation of D with the call's result flips sign between windows (−0.16 vs +0.13).
  - **Big trades:** the pooled +19.5 % rests on two or three big 2022-24 trades; without the top two (CUMMINSIND,
    UPL) it is −3.3 %.
  - **Sample size:** only 15 cases have D ≤ −2 %, so test 1 (at least 20 trades) could never pass with this data.
  - **Overnight:** the one pattern with the same sign in both windows is that corrected stocks keep falling overnight
    (gap −1.2 % / −1.7 %; raw −1.1 % / −1.8 %). That is continuation, the opposite of a bounce, and the next day
    shows no reversal either (open to close −0.5 %, t −0.4). Descriptive only.
