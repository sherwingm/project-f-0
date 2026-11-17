# G1-F trade anatomy (draft, Agent 2; descriptive and explanatory only, nothing here is a predictor test)

Data: the 154 recorded G1-F trades (ATM put, bought the minute after the signal minute, 50 % stop, otherwise out at the next session 15:29), 2024-10-01 to 2026-10-28. Original recorded results only; nothing re-optimised. Full tables: `analysis_G1F.md`, `cut_tables_G1F.csv`; secondary sets in `analysis_G1.md`, `analysis_G1C.md`. Bootstrap CIs resample trading days (4,000 reps). Cells under 10 trades are marked too few.

## 0. Do the trades reproduce?
All 154 reproduce: same contract, same exit reason in 154/154. Net % differs from the recorded value by at most 0.26 points (40 trades exact to 0.01, 132 within 0.1). The tiny differences come from the replay file having been written with the undated 2026 STT table while the engine now uses the dated one (disclosed in the audit). G1 puts 259/259 (max 0.27), G1-C 235/235 (all exact). My MFE equals the file's max up within 0.005 points.

## 1. The shape of the result
- Total net Rs 247,046; mean +19.7 %; median -18.2 %; win rate 40.9 % (63 W / 91 L).
- 64 stops (42 %), mean -54.9 %. 90 trades held to the next close: 70 % wins, mean +72.7 %, median +41.8 %, Rs +486,789. Stops cost Rs -239,743.
- Average win Rs +8.4k, average loss Rs -3.1k (net %: winners +112 %, losers about -44 %). The strategy is a few big winners paid for by many small-to-medium losses.
- Max up through the next close (no stop): >= +50 % in 59 % of trades, >= +100 % in 41 %, >= +200 % in 16 %; mean 104, median 72.

## 2. Winners vs losers: what separates them and what does not
PRE-ENTRY fields (means, winners / losers): ret1 -0.08 / 0.03; ret5 -0.03 / 0.10; ret20 -0.02 / 0.13; VIX at signal 12.87 / 12.52; VIX 5-day change -1.6 / -1.4 %; gap -0.05 / -0.05; intraday move to signal -0.23 / -0.21 %; breakout minutes after 09:30 14.5 / 17.2; breadth proxy 48.4 / 49.5; ATM IV 12.5 / 12.5; put-call OI 0.92 / 0.90. These are the same within noise (Mann-Whitney p 0.19 to 1.0).
Two pre-entry fields differ: sessions to expiry (winners mean 3.25, losers 2.79; p 0.048; calendar days p 0.014) and price paid (127 vs 112 per unit; p 0.018). These are uncorrected p-values from about 25 pre-entry fields (about 1 to 2 would pass 0.05 by chance); read them as descriptive only. Expiry-day trades are 33 % of winners vs 20 % of losers.
Conclusion: no pre-entry field I looked at cleanly separates winners from losers.
What does separate them is post-entry, as expected for a buy-only option held overnight: the next session. Winners saw the next open gap -0.28 % and the next close -0.63 % below the entry-day close; losers +0.08 % and +0.17 %. 90 % of winners had the next close below the entry-day close, 40 % of losers. Spearman of net % with the signal-to-next-close spot move is -0.74. (POST-ENTRY: explains the outcome, not a predictor.)

## 3. Pre-named cuts (n, win rate, mean net % [95 % CI]); full tables with median, Rs, MFE and MAE in analysis_G1F.md
- Previous-session return quintiles (1 = most negative): 25 / 50 / 34 / 31 / 14 trades; means +22, +24, +15, +25, -1; all CIs span zero.
- 5-session quintiles: mean 13, 7, 55, 17, -16. The middle quintile (n 41, win 61 %, mean +55 % [23, 88], Rs 169k) is the only cell whose interval excludes zero among the five; the next quintiles are weak, so this is non-monotonic and likely noise at this sample size.
- 10-session: 3, 22, 2, 55 [10, 107], 16. 20-session: 23, 12, 7, 26, and 127 in the top quintile (n 8, too few).
- MA structure: bear 27 (n 26), bull 25 (n 51), mixed 13 (n 77). Same sign, overlapping intervals.
- VIX level (history p25 = 12.57, p75 = 18.24; G1-F has no VIX above 17 by its own filter): low n 83 mean +12 % [-8, 36], win 35 %, stop 49 %; normal n 71 mean +28 % [7, 52], win 48 %, stop 32 %.
- VIX 5-day direction: falling +24, flat +17, rising +19 (all CIs span zero). VIX one-day sign: down or flat +23 [2, 46], up +15.
- Gap: flat n 133 +22 % [5, 40]; gap_down n 21 +6 % [-26, 45] (gap-up excluded by the rule).
- Sessions to expiry: 1 session n 34, win 24 %, stop 71 %, mean +15 %, MFE mean 145 / median 138 (the biggest swings both ways); 2: n 26, win 50 %, +17; 3: n 32, +33; 4+: n 62, win 48 %, stop 26 %, +16. All CIs span zero.
- Breakout time: before 10:00 n 127 +23 % [5, 41]; 10:00 to 10:59 n 24 +9 %; 11:00+ n 3 too few.
- Weekday: Mon n 31 +4; Tue n 32 +29; Wed n 24, win 25 %, -16 [-41, 12]; Thu n 30 +39 [6, 77], stop 20 %; Fri n 37 +32 (Rs 129k). Wednesday was the only negative weekday, but its interval spans zero.
- Quarter (n): 2024Q4 21 +33; 2025Q1 16 +54 [12, 99]; 2025Q2 11 +20; 2025Q3 27 +4.5; 2025Q4 23 +2.4; 2026Q1 17 +55; 2026Q2 3 (too few); 2026Q3 33 -11 [-30, 10]; 2026Q4 3 (too few).
Reading: no cut shows a clean gradient; the only cells whose interval excludes zero (5-day middle quintile, 10-day Q4, VIX normal, flat gap, Thursday, before-10:00 breakouts, 2025Q1) are not monotonic or are the bulk of the sample. With a mean spread of about 100 points per trade, cells of 30 to 80 trades cannot show effects smaller than about 30 to 40 points.

## 4. Concentration
The top 8 trades (5 %) earned Rs 190,146 = 77 % of total net Rs (top 3 = 37 %, top 5 = 54 %, top 10 = 91 %). Without them: n 146, total Rs 56,900, mean +5.8 %, median -27.5 %, win rate 38 %. Largest single trade: 2025-04-04 (+400 %, Rs 44,422, 18 % of the total; the spot opened 5.0 % lower the next session). All 8 top trades were held to the next close; all 8 had the next close 0.4 % to 2.9 % below the entry-day close; 2 were expiry-day entries; entry weekdays Fri x4, Thu x3, Mon x1. Pre-entry, the top 8 differ from the rest in a larger 5-day VIX fall (-7.5 vs -1.2 %, mean) and earlier breakouts (8.9 vs 16.5 minutes); with n 8 treat as an observation. Their next-open gap averaged -1.04 % vs -0.02 %. G1-F is a convex payoff: the result is dominated by a few large next-session drops.

## 5. Stop-outs
- 64 of 154 (42 %). 35 stopped on the entry day, 29 the next day. Time to stop: median 309 trading minutes (quartiles 149 / 372); none within 30 minutes, 7 within 60. So stops are slow bleeds, not instant failures.
- Mean option move at the stop -54 % (MAE), median -51 % (stop at -50 % plus fill slippage).
- Before the stop, 25 % of the stopped trades had been up 20 % or more; median max up 9.7 %.
- POST-ENTRY: after the stop minute, 15 of 64 options came back to at least the price paid at some minute; 8 ended the next close above paid (172, 109, 22, 80, 244, 131, 62, 128 %), 5 above +100 %. These 8 recoveries: 2024-11-27, 2025-07-02, 2025-08-07, 2026-01-05, 2026-01-19, 2026-02-18, 2026-06-29, 2026-08-17. About 1 in 8 stops would have turned into a gain; 12 % of stops. (Not a rule suggestion; no alternative exit tested.)
- 72 % of stopped trades had the entry-day close back above the signal close (a failed breakout in hindsight) vs 20 % of the held trades (POST-ENTRY).
- Stop rate by quarter: 24, 31, 45, 52, 61, 35, 33, 42, 0 % (2024Q4 to 2026Q4). The 2025Q3 and 2025Q4 stop rates (52 and 61 %) were higher than 2026Q3 (42 %).
- By sessions to expiry: 71 % stops at 1 session, 46 % at 2, 38 % at 3, 26 % at 4+.

## 6. How long winners take to peak (POST-ENTRY)
Of 63 winners, 56 peaked on the next session and 7 on the entry day. Trading minutes from entry to peak: median 575, quartiles 448 / 668 (a session is 375 minutes). Of the 27 trades at +100 % or more, 26 peaked the next day (median 656 minutes), after a median worst dip before the peak of about -20 % (worst -43 %). Winners kept a median 62 % of their peak at exit. Holding overnight is where the profit arises; the winners' MAE (-22 % mean) is much milder than the losers' (-48 %).

## 7. 2026 Q3 against the other quarters
- 2026Q3: 33 trades, 8 wins (24 %), mean -11.2 % [-30, 10], median -29 %, Rs -19,069. Others: 121 trades, 45 % wins, mean +28 %, Rs +266,115.
- The stop rate was not higher (42 % vs 41 %); the loss came from the held trades: the next-session spot did not fall. Mean next close vs entry-day close +0.03 % in Q3 vs -0.21 % in the other quarters; max up mean 67 % vs 115 %. POST-ENTRY.
- PRE-ENTRY differences (means, Q3 vs rest): VIX at signal 11.97 vs 12.85; previous close vs SMA20 -0.19 vs +0.11 %; ret10 -0.41 vs +0.20; VIX 5-day change -2.8 vs -1.1; breakout minute 25 vs 13.7 minutes after 09:30; 30 % of Q3 breakouts came 10:00 to 10:59 vs 12 %; ATM IV 11.3 vs 12.8; FII futures long share 10.8 vs 20.1; GIFT basis 0.18 vs 0.28; paid price 107 vs 121. Low-VIX trades were 76 % of Q3 vs 48 %.
- By month: July n 9, mean -17 %; August n 15, 1 win, mean -35 %, Rs -27,379; September n 9, mean +35 %, Rs +13,593 with 11 % stops.
- So 2026Q3 looks like a quarter of low volatility (cheaper options, lower IV, fewer large next-day gaps) and late-morning breakouts that reversed. The data do not show a single separating condition; August carries most of the loss.

## 8. Other observations (secondary sets, see analysis_G1.md and analysis_G1C.md)
- G1 puts (259): total Rs 40,448, mean +5.5 %, 52 % stops; top 13 trades Rs 298,305 (738 % of the total); without them Rs -257,857.
- G1-C calls (235): total Rs -158,781, mean -10.8 %, 58 % stops; top 12 trades Rs 273,561; without them Rs -432,342. The same shape: held trades win 70 % of the time, stops 100 % lose.
- In all three sets the 1-session-to-expiry cell has the highest stop rate (G1-F 71 %, G1 75 %, G1-C 86 %) and the 4+ cell the lowest, with the highest win rate (48, 43, 43 %).
- Weekday patterns are inconsistent across sets (G1-C Monday -31 %, G1-F Monday +4 %); there is no stable weekday effect.

## Limits
- n 154 over two years, filters chosen on the same data; effects below roughly 30 to 40 points cannot be seen in the cells. About 36 fields were compared, so a handful of p < 0.05 results are expected by chance; no correction applied because nothing here is used as a test.
- Breadth is survivorship-biased; GIFT is a daily settlement; VIX class edges use 2021-10-20 to 2024-09-30 (store start), not 2018.
- The G1-F VIX high class is empty by the rule (VIX < 17); gap-up class empty.
- MAE uses option minute closes (last traded price carried forward, up to 30 minutes); intraminute lows are not available.
- All post-entry fields explain outcomes only.
