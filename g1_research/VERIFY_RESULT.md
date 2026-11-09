# Verification of the public research claims: results (2026-11-09). Plan: VERIFY_PREREG.md (committed fab94a8b5 before any number)
NIFTY option 1-minute trade prices, 2024-10-01 to 2026-10-28. History only. Scripts: scripts/verify_strikes.py, scripts/verify_intraday.py.
Data: data/verify_*.csv. Summaries: results/verify_strikes_summary.csv, results/verify_intraday_summary.csv. Hand-checked fills on two Test 2 days.

## Test 1: ATM vs ITM on G1's own signals (exit next close, 50 % stop)
Puts, all 259 G1 signals (max up through next close first, then booked % of premium):
| Strike | Premium avg | Max up >= +100 % | Max up avg / median | Win | Booked avg | Booked median | Stopped | Total, 1 lot |
|---|---|---|---|---|---|---|---|---|
| 1 OTM | Rs 114 | 35 % | +100 / +60 % | 32 % | +7.7 % | -51 % | 54 % | +Rs 51k |
| ATM (live) | Rs 135 | 34 % | +90 / +57 % | 34 % | +5.5 % | -51 % | 52 % | +Rs 40k |
| 1 ITM | Rs 159 | 32 % | +83 / +54 % | 37 % | +6.0 % | -40 % | 49 % | +Rs 72k |
| 2 ITM | Rs 188 | 28 % | +74 / +52 % | 40 % | +6.5 % | -27 % | 43 % | +Rs 120k |
| 4 ITM (deep) | Rs 254 | 20 % | +60 / +47 % | 45 % | +6.6 % | -8 % | 34 % | +Rs 188k |
- **Decision: no strike beats ATM** on return per rupee at risk (paired differences -0.4 to +1.3 points, t 0.1 to 1.5; bar t >= 2). G1-F: same (all strikes +16 to +21 %, none beats ATM).
- ITM changes the SHAPE, not the edge: more wins and smaller typical loss (median -51 % -> -8 %), fewer stops, fewer +100 % runs. The bigger rupee totals come from paying a bigger premium (more money at risk), not a better return on it.
- **Call mirror (G1-C) booked for the first time: it LOSES at every strike** (ATM -10.8 % a trade, -Rs 1.6 lakh over 235 trades; 2x costs -12.7 %). ITM calls lose less per rupee (+2.6 points vs ATM, t 0.9: not significant) but still lose.

## Test 2: Zerodha ORB on option premium (replication, exit 15:15 fixed in advance)
415 trades (CE 202, PE 213): win 38.8 % (theirs ~48 %: **does not match**), mean -1.1 % of premium, median -5.1 %, -Rs 56k at 0.2 % slippage, -Rs 1.0 lakh at 0.5 %; drawdown -Rs 74k (about 49 % of their Rs 1.5 lakh per lot, close to their ~45 %). Every year negative (2024, 2025, 2026); 15:25 exit also negative. Weak since mid-2024 = **matches their own words**. Puts slightly positive (+1.2 %, t 0.7), calls negative (-3.4 %, t -2.2). Not profitable here.

## Test 3: forum "2 % target / 2 % stop at 09:29" (open vs previous close, 1 ITM, 15 minutes)
504 trades, win 41.7 %, mean -3.1 % (t -4.3), -Rs 1.13 lakh; **negative in every year** (2024, 2025, 2026). Matches the commenter's claim that it loses every year (their 19 % win rate is not reproduced; different exits likely).

## Test 4: the 30-minute ORB bot (ATM, 30 % stop, square-off 15:15)
468 trades. Gross (no charges, no slippage): -3.6 %, -Rs 1.37 lakh. Net: -5.5 %, -Rs 2.02 lakh, win 28 %. **Costs make it worse (by about Rs 64k) but it already lost before costs here**; the claim "+Rs 43k gross" is not reproduced on two years (their test was 60 days). Max up was decent (14 % of trades reached +100 %) but the 30 % stop hit 61 %.

## Test 5: the "11.5-year" exit rules (30 % stop, after +20 % move the stop to entry and trail 20 % below the peak) on our 15-minute breakout entries, intraday
494 trades: trail rule -2.2 % (-Rs 1.14 lakh), plain 30 % stop -3.7 % (-Rs 1.83 lakh), no stop -3.0 % (-Rs 1.71 lakh). **The trail rule is the least bad but still loses**; all intraday versions lose. The same entries held to the NEXT close (G1) were positive (Test 1), so for this breakout the overnight hold, not the stop style, is what carried the result.

## Bottom line
- None of the public option-buying ideas tested here makes money on two years of real NIFTY option prices after costs. That agrees with SEBI's loss data.
- Strike choice does not create an edge; ITM only trades fewer big wins for smaller losses.
- G1 / G1-F (puts, held to the next close) stays the only positive result, and it is in-sample. The call mirror held overnight lost; building G1-C is NOT supported by this history.
