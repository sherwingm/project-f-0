# Near-expiry option buying: max up by sessions to expiry (2026-11-04, descriptive)

The user, 2026-11-04: build to trade near expiry, "to capture the trade more than 100%". Before any rule: how often a
near-expiry option bought by a fixed rule reaches +100 %, and what holding it pays. Code `scanner/near_expiry_maxup.py`,
workbook `near_expiry_maxup_2026-11-04.xlsx` (`scripts/near_expiry_xlsx.py`). The stock trades CSV (126 MB) is not
committed; re-run the scanner to rebuild it. In-sample, no rule chosen, charges not included.

Kotak Neo (the order broker) allows buying near expiry through the API: NIFTY options are cash-settled; stock options get
extra delivery margin from 4 sessions before expiry (10 → 25 → 45 → 70 → 100 %) on ITM longs, and full delivery margin
from 12:00 on expiry day on long strikes within 3 % of the price (from 2026-09-29), or the risk team squares them off.
Our own guards block it today: `ALLOW_LOTTERY=false` (≤ 2 sessions or < ₹2) and `BLOCK_EXPIRY_DAY_ENTRIES=true`.

## NIFTY weekly options, Oct 2024 → Oct 2026 (107 expiries), bought 09:20, all strikes 0-6 out pooled

Max up = highest minute high up to expiry 15:29. Session 0 reproduces `S3_expiry_day_scan.md` exactly.

| Option | Sessions to expiry | Trades | Median paid (₹) | Max up median | Reached +100 % | Reached +500 % | Held to expiry, mean | Held to expiry, median | Sell at +100 % else hold, mean | Sold same day 15:15, mean |
|---|---|---|---|---|---|---|---|---|---|---|
| Call | 0 | 749 | 16.87 | +43 % | +31 % | +6 % | -20 % | -99 % | -35 % | -20 % |
| Call | 1 | 748 | 44.95 | +60 % | +33 % | +6 % | -19 % | -100 % | -30 % | -4 % |
| Call | 2 | 747 | 72.97 | +59 % | +36 % | +5 % | -28 % | -100 % | -25 % | -7 % |
| Call | 3 | 749 | 91.81 | +44 % | +30 % | +5 % | -32 % | -100 % | -35 % | -9 % |
| Call | 4 | 735 | 114.18 | +46 % | +31 % | +4 % | -25 % | -100 % | -33 % | -4 % |
| Put | 0 | 749 | 17.27 | +78 % | +43 % | +9 % | -5 % | -98 % | -10 % | -5 % |
| Put | 1 | 749 | 42.12 | +66 % | +41 % | +6 % | -13 % | -99 % | -12 % | -9 % |
| Put | 2 | 749 | 65.65 | +61 % | +42 % | +9 % | +8 % | -100 % | -11 % | +1 % |
| Put | 3 | 748 | 81.69 | +87 % | +47 % | +11 % | +22 % | -100 % | +0 % | +6 % |
| Put | 4 | 732 | 99.13 | +117 % | +52 % | +10 % | +16 % | -100 % | +9 % | +1 % |

## Stock options, monthly expiries Jan 2021 → Aug 2026, every F&O stock, bought at the close, strikes 0-5 out pooled

Max up here uses daily CLOSES only (a lower bound). 3,130 of 1,468,785 rows left out (corporate actions, re-struck
contracts). A few ₹0.05 prints remain and make the means jumpy; read medians and the +100 % rate first.

| Option | Sessions to expiry | Trades | Median paid (₹) | Max up median | Reached +100 % | Reached +500 % | Held to expiry, mean | Held to expiry, median | Sell at +100 % else hold, mean |
|---|---|---|---|---|---|---|---|---|---|
| Call | 1 | 74,711 | 1.06 | -86 % | +7 % | +2 % | -50 % | -100 % | -79 % |
| Call | 2 | 74,930 | 2.31 | -50 % | +13 % | +3 % | -38 % | -100 % | -68 % |
| Call | 3 | 74,974 | 3.47 | -24 % | +17 % | +4 % | -31 % | -100 % | -59 % |
| Call | 4 | 74,894 | 4.92 | -21 % | +18 % | +4 % | -31 % | -100 % | -56 % |
| Call | 5 | 74,798 | 6.43 | -20 % | +17 % | +3 % | -35 % | -100 % | -58 % |
| Call | 7 | 74,563 | 8.69 | +3 % | +21 % | +3 % | -35 % | -100 % | -51 % |
| Call | 10 | 74,108 | 12.21 | +18 % | +24 % | +3 % | -27 % | -100 % | -44 % |
| Put | 1 | 71,778 | 0.95 | -79 % | +10 % | +3 % | -18 % | -100 % | -73 % |
| Put | 2 | 72,208 | 2.01 | -46 % | +15 % | +3 % | -27 % | -100 % | -62 % |
| Put | 3 | 72,287 | 3.01 | -26 % | +18 % | +4 % | -20 % | -100 % | -57 % |
| Put | 4 | 72,125 | 4.37 | -12 % | +23 % | +4 % | -15 % | -100 % | -47 % |
| Put | 5 | 72,177 | 5.78 | +9 % | +28 % | +5 % | -6 % | -100 % | -36 % |
| Put | 7 | 72,039 | 7.79 | +22 % | +29 % | +5 % | -2 % | -100 % | -33 % |
| Put | 10 | 71,313 | 10.95 | +24 % | +28 % | +4 % | -11 % | -100 % | -34 % |

## What it says

1. **+100 % is common in hindsight.** NIFTY: 30-36 % of calls and 41-53 % of puts touch +100 % before expiry; on
   expiry day itself up to 9-11 % of out-of-the-money options touch +500 %. Stocks (closes only): 7-24 % of calls and
   10-29 % of puts, rising with time to expiry.
2. **Holding loses.** The median held-to-expiry trade is −100 % in every NIFTY and stock bucket. NIFTY calls held lose
   19-32 % a trade on average; NIFTY puts are positive for 2-4 sessions out (+8 to +22 %), but that is this window's
   falls (two-year sample, one regime), not a rule. Stock calls held lose 27-50 %, stock puts 6-27 %.
3. **"Sell as soon as it doubles" is worse than holding** in nearly every bucket (NIFTY calls −25 to −35 %, stock calls
   −44 to −79 %): it caps the few +500 % trades that pay for the many −100 % ones, and the trades that never reach +100 %
   still go to zero.
4. **Selling the same day is the least bad NIFTY exit** for calls bought 1-4 sessions out (−4 to −9 % against −19 to
   −32 % held), still negative.
5. So time to expiry alone gives no edge: the 100 % moves are there, but which trade gets one is the question. A
   near-expiry build needs an entry signal that picks direction (as G1 does for puts) and is judged on its own pre-registered page.
