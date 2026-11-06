# Expiry-day option blasts (2026-11-05, descriptive)

The user's screenshot: SENSEX 05 Nov 79000 call ₹12.75 → ₹309.95 (+2,331 %) on expiry day, SENSEX +2.6 %. "check how many have these happens previous". Code `scanner/expiry_blasts.py`, workbook `expiry_blasts_2026-11-05.xlsx`.

- 2x is common: the best option of the day doubled from 09:20 on 87 of 108 NIFTY and 84 of 107 SENSEX expiry days; every day the index moved ≥ 1 % one way had one.
- A single fixed option (one side, one strike, chosen at 09:20) doubles on 30-49 % of expiry days (NIFTY calls ~30-36 %, NIFTY puts ~43-49 % near the money, SENSEX ~38-47 %), but is still ≥ 2x at 15:15 on only 5-23 %.
- Selling at 2x if touched, else at 15:15, averages −8 % to −58 % a trade for calls and +8 % (at the money) to −75 % (10 strikes out) for puts, before charges and slippage (sheet 2x by strike). Puts doing better is this two-year window, not a rule.
- About 1 expiry day in 7 has an option that goes 10x from its 09:20 price (NIFTY 14 of 108, SENSEX 15 of 107, Oct 2024 → Oct 2026). With weekly NIFTY and SENSEX expiries that is ~2 a month.
- They need the index to travel 1 % or more one way after 09:20: under 0.5 % none of 80 days blasted, 0.5-1 % 6 of 83, 1-1.5 % 11 of 36, 1.5 % or more 12 of 16.
- Most give it back: of the 29 10x days, the best option was still ≥ 10x at 15:15 on 9 and below the 09:20 price on 10.
- The side and strike are known only afterwards: the best of 22 strikes is picked here in hindsight. Buying both sides every expiry day lost on average (data/results/S3_expiry_day_scan.md: call + put 4 strikes out −8 %, median −98 %).
- Today, 5 Nov 2026: SENSEX +2.6 % (+2,008 points) is a big index day (top ~4 % of expiry days here); the 79000 call ₹12.75 → ₹309.95 is ~24x from the previous close. Today's SENSEX minutes arrive with the nightly data update.
