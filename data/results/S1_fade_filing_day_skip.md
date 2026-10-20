# S1 fade · skip trades whose market-hours filing day already moved the fade's way

Pre-registered: strategies/S1_fade_filing_day_skip.md. D = the stock's move from the minute before the announcement to the filing day's 15:29 close, minus NIFTY 50's; D_bet = D in the fade's direction (-D for puts). Skip when D_bet >= +2 %. Fade trades: v10 backtest, entry at the open, E1 (15:20), net of charges.

Fade trades 2022-26: 870; from market-hours filings: 248.

## Step 0 · counts

| group | 2022-24 | 2025-26 | all |
|---|---|---|---|
| not a market-hours filing | 306 | 316 | 622 |
| market hours, kept | 88 | 63 | 151 |
| SKIP (day already moved >= 2 % the fade's way) | 16 | 21 | 37 |
| mirror (day moved >= 2 % against the fade) | 26 | 34 | 60 |

Gate: the skip group needs >= 30 pooled and >= 10 in each window. **PASSED: results below**.

## Test: **PASS (a candidate filter for the user's decision)**

| test | value | pass |
|---|---|---|
| 1a skipped total Rs < 0 in 2022-24 | -19385 | True |
| 1b skipped total Rs < 0 in 2025-26 | -28987 | True |
| 2 pooled skipped mean < 0 with t <= -2 | -21.96 % / t -2.769 | True |
| 3 skipped mean < 0 under v11 (n 18; required if >= 10) | -1.84 | True |

## The whole fade, with and without the skip (v10, 15:20)

| window | all fade trades Rs | n | with the skip Rs | n kept | saved Rs |
|---|---|---|---|---|---|
| 2022-24 | 24190 | 436 | 43575 | 420 | 19385 |
| 2025-26 | 126164 | 434 | 155150 | 413 | 28987 |
| all | 150354 | 870 | 198725 | 833 | 48371 |

## By group, side and window (v10, 15:20)

| group | side | window | n | win % | mean net % | median net % | total Rs | t |
|---|---|---|---|---|---|---|---|---|
| SKIP (day already moved >= 2 % the fade's way) | both | 2022-24 | 16 | 6.2 | -25.99 | -29.53 | -19385 | -3.514 |
| SKIP (day already moved >= 2 % the fade's way) | both | 2025-26 | 21 | 23.8 | -18.9 | -37.92 | -28987 | -1.445 |
| SKIP (day already moved >= 2 % the fade's way) | both | all | 37 | 16.2 | -21.96 | -34.88 | -48372 | -2.769 |
| SKIP (day already moved >= 2 % the fade's way) | PE | 2022-24 | 10 | 10 | -29 | -33.1 | -12956 | -2.552 |
| SKIP (day already moved >= 2 % the fade's way) | PE | 2025-26 | 14 | 21.4 | -26.92 | -36.12 | -28006 | -2.338 |
| SKIP (day already moved >= 2 % the fade's way) | PE | all | 24 | 16.7 | -27.78 | -34.64 | -40962 | -3.467 |
| SKIP (day already moved >= 2 % the fade's way) | CE | 2022-24 | 6 | 0 | -20.97 | -14.86 | -6428 | -3.234 |
| SKIP (day already moved >= 2 % the fade's way) | CE | 2025-26 | 7 | 28.6 | -2.86 | -37.92 | -981 | -0.091 |
| SKIP (day already moved >= 2 % the fade's way) | CE | all | 13 | 15.4 | -11.22 | -34.88 | -7409 | -0.677 |
| mirror (day moved >= 2 % against the fade) | both | 2022-24 | 26 | 46.2 | 4.58 | -3.73 | 9325 | 0.411 |
| mirror (day moved >= 2 % against the fade) | both | 2025-26 | 34 | 52.9 | -3.71 | 0.82 | -14704 | -0.515 |
| mirror (day moved >= 2 % against the fade) | both | all | 60 | 50 | -0.12 | -0.39 | -5379 | -0.019 |
| mirror (day moved >= 2 % against the fade) | PE | 2022-24 | 19 | 42.1 | -12.07 | -12.18 | -12811 | -1.855 |
| mirror (day moved >= 2 % against the fade) | PE | 2025-26 | 28 | 53.6 | -1.12 | 0.82 | -7674 | -0.141 |
| mirror (day moved >= 2 % against the fade) | PE | all | 47 | 48.9 | -5.55 | -4.84 | -20485 | -1.005 |
| mirror (day moved >= 2 % against the fade) | CE | 2022-24 | 7 | 57.1 | 49.77 | 60.1 | 22135 | 1.533 |
| mirror (day moved >= 2 % against the fade) | CE | 2025-26 | 6 | 50 | -15.79 | -1.17 | -7029 | -1.069 |
| mirror (day moved >= 2 % against the fade) | CE | all | 13 | 53.8 | 19.51 | 1.46 | 15106 | 0.958 |
| market hours, kept | both | 2022-24 | 88 | 29.5 | -4.85 | -17.92 | -33173 | -0.709 |
| market hours, kept | both | 2025-26 | 63 | 42.9 | 8.92 | -7.3 | 36399 | 1.06 |
| market hours, kept | both | all | 151 | 35.1 | 0.9 | -16.27 | 3226 | 0.168 |
| market hours, kept | PE | 2022-24 | 67 | 31.3 | -5.19 | -16.53 | -29023 | -0.736 |
| market hours, kept | PE | 2025-26 | 51 | 43.1 | 14.14 | -7.3 | 44240 | 1.324 |
| market hours, kept | PE | all | 118 | 36.4 | 3.16 | -16.22 | 15218 | 0.51 |
| market hours, kept | CE | 2022-24 | 21 | 23.8 | -3.76 | -19.31 | -4151 | -0.216 |
| market hours, kept | CE | 2025-26 | 12 | 41.7 | -13.23 | -9.05 | -7841 | -0.989 |
| market hours, kept | CE | all | 33 | 30.3 | -7.2 | -16.98 | -11992 | -0.6 |
| not a market-hours filing | both | 2022-24 | 306 | 39.2 | 7.44 | -16.46 | 67423 | 1.523 |
| not a market-hours filing | both | 2025-26 | 316 | 39.2 | 7.62 | -17.41 | 133455 | 1.423 |
| not a market-hours filing | both | all | 622 | 39.2 | 7.53 | -17.31 | 200879 | 2.078 |
| not a market-hours filing | PE | 2022-24 | 222 | 37.4 | 9.19 | -24.14 | 44197 | 1.38 |
| not a market-hours filing | PE | 2025-26 | 229 | 39.7 | 8.56 | -16.35 | 117672 | 1.27 |
| not a market-hours filing | PE | all | 451 | 38.6 | 8.87 | -17.72 | 161869 | 1.875 |
| not a market-hours filing | CE | 2022-24 | 84 | 44 | 2.81 | -10.78 | 23226 | 0.38 |
| not a market-hours filing | CE | 2025-26 | 87 | 37.9 | 5.14 | -23.27 | 15783 | 0.549 |
| not a market-hours filing | CE | all | 171 | 40.9 | 3.99 | -16.35 | 39010 | 0.67 |

## The same groups with v11's exit (minutes, Oct 2024 on)

| group | n | win % | mean net % | median net % | total Rs | t |
|---|---|---|---|---|---|---|
| not a market-hours filing | 345 | 28.4 | 12.5 | -21.13 | 235451 | 2.466 |
| market hours, kept | 69 | 29 | 3 | -21.11 | 17767 | 0.472 |
| SKIP (day already moved >= 2 % the fade's way) | 18 | 22.2 | -1.84 | -20.92 | -2254 | -0.144 |
| mirror (day moved >= 2 % against the fade) | 36 | 38.9 | 1.53 | -20.87 | -49 | 0.249 |

Trades: data/results/S1_fade_filing_day_skip_trades.csv.

## Independent verification (2026-10-20; three separate checks and a judge, nothing taken from this script)
- **The PASS is computed correctly.** Every number was rebuilt independently and matches exactly:
  - D to 1e-15; the 37 skips (16 / 21);
  - totals −19,385 / −28,987; mean −21.96 %, t −2.77;
  - v11: 18 trades, −1.84 %.
- **Timing:** no look-ahead; every trade is bought the session after the filing.
- **Matching:** each trade is matched to its own filing, and the side signs were hand-checked on 5 trades.
- **One data gap:** 14 market-hours trades could not be measured, because their minute data stops early (all of 3-14
  Aug 2026 ends at 15:14; HINDALCO 2024-05-24 at 14:51). This report counted them as "not a market-hours filing".
  Measured to the last minute available, 4 of them would be skips: 41 trades, t −2.90. The test still passes.
- **Robustness in the v10 backtest:**
  - Skipped totals are negative in both windows at every threshold from 1 % to 3 %, adjusted or raw.
  - Leave one trade, day or stock out: t stays ≤ −2.37.
  - The skips spread over 32 dates and 30 stocks.
  - A random 37-trade skip does as well in only 1.3-2.9 % of draws.
- **Caveats, most important first:**
  1. **Under the live v11 exit it saves almost nothing.** About ₹2-7k over two years, a range of −25k to +25k:
     v11's −20 % stop already cuts these same losers to about −21 %. The ₹48k headline is a v10 (15:20 exit) number.
  2. **It is a puts effect only.** Puts: 24 trades, −27.8 %, t −3.5, negative in both windows. Calls: 13 trades,
     t −0.7, slightly positive in 2025-26. The call half is too few to judge.
  3. **The evidence is modest.** The shuffle test gives p ≈ 0.01-0.03, and about 7 related looks at these trades
     were made today.
  4. **It is rare:** about 9 trades a year.
- **Judge's recommendation:** do not change the live fade. At most, track it as a shadow tag (puts whose
  market-hours filing day already fell ≥ 2 %) and look again after about 20 live cases.
