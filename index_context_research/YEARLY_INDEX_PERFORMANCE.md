# Yearly index performance (NIFTY only)

Index context research, 16 Nov 2026. Plan: `PREREG_CONTEXT.md`. Research only; nothing existing was changed; nothing committed. Net % = net per trade after costs (live-rule replays, 1 lot). Max up first.

Only NIFTY has option-trade history for these rules (no BANKNIFTY / SENSEX trade records), and the minute option data starts Oct 2024, so there are only 2024 (3 months), 2025 and 2026 (to Oct): no 2021-2023 rows exist for these strategies. 2026 is partial.

## G1 puts (259)
- 2024: n 32, max up >= +100 % on 47 % (mean 119 %), win 41 %, mean +30.0 %, median -19.4 %, profit factor 1.52, total Rs 18,891, max drawdown Rs -18,520
- 2025: n 123, max up >= +100 % on 31 % (mean 80 %), win 37 %, mean +2.3 %, median -51.2 %, profit factor 1.08, total Rs 26,593, max drawdown Rs -114,686
- 2026 (partial): n 104, max up >= +100 % on 33 % (mean 94 %), win 30 %, mean +1.8 %, median -43.7 %, profit factor 0.98, total Rs -5,036, max drawdown Rs -106,706
  Quarters: 2024Q4 +30 % (n 32); 2025Q1 +11 % (n 35); 2025Q2 -11 % (n 27); 2025Q3 +0 % (n 34); 2025Q4 +6 % (n 27); 2026Q1 +32 % (n 32); 2026Q2 -19 % (n 27); 2026Q3 -8 % (n 39); 2026Q4 +2 % (n 6)
  By weekday: 0 -4 % (n 53); 1 +8 % (n 61); 2 -19 % (n 42); 3 +13 % (n 53); 4 +26 % (n 50)
  By expiry_day: 0 +5 % (n 197); 1 +6 % (n 62)
  By trend_prev: 0 +0 % (n 135); 1 +11 % (n 124)
  By gap_tercile: low +17 % (n 86); mid +8 % (n 86); high -8 % (n 87)
  By vix_tercile: low +7 % (n 87); mid +25 % (n 86); high -15 % (n 86)
  Concentration: the top 5 % of trades earned Rs 298,305 of the set's total Rs 40,448.

## G1-F (154)
- 2024: n 21, max up >= +100 % on 57 % (mean 121 %), win 48 %, mean +32.6 %, median -2.0 %, profit factor 1.86, total Rs 15,921, max drawdown Rs -6,907
- 2025: n 77, max up >= +100 % on 38 % (mean 92 %), win 43 %, mean +16.4 %, median -47.6 %, profit factor 1.82, total Rs 140,256, max drawdown Rs -35,580
- 2026 (partial): n 56, max up >= +100 % on 39 % (mean 115 %), win 36 %, mean +19.3 %, median -18.2 %, profit factor 1.97, total Rs 90,869, max drawdown Rs -41,611
  Quarters: 2024Q4 +33 % (n 21); 2025Q1 +54 % (n 16); 2025Q2 +20 % (n 11); 2025Q3 +4 % (n 27); 2025Q4 +2 % (n 23); 2026Q1 +55 % (n 17); 2026Q2 +116 % (n 3); 2026Q3 -11 % (n 33); 2026Q4 +56 % (n 3)
  By weekday: 0 +4 % (n 31); 1 +29 % (n 32); 2 -16 % (n 24); 3 +39 % (n 30); 4 +32 % (n 37)
  By expiry_day: 0 +20 % (n 115); 1 +18 % (n 39)
  By trend_prev: 0 +10 % (n 73); 1 +28 % (n 81)
  By gap_tercile: low +30 % (n 52); mid +27 % (n 50); high +2 % (n 52)
  By vix_tercile: low +17 % (n 52); mid +12 % (n 51); high +31 % (n 51)
  Concentration: the top 5 % of trades earned Rs 190,146 of the set's total Rs 247,046.

## G1-C calls (235)
- 2024: n 25, max up >= +100 % on 16 % (mean 62 %), win 20 %, mean -17.7 %, median -52.1 %, profit factor 0.65, total Rs -14,301, max drawdown Rs -15,037
- 2025: n 120, max up >= +100 % on 23 % (mean 73 %), win 35 %, mean +0.0 %, median -51.1 %, profit factor 1.13, total Rs 47,875, max drawdown Rs -62,560
- 2026 (partial): n 90, max up >= +100 % on 16 % (mean 56 %), win 24 %, mean -23.2 %, median -51.2 %, profit factor 0.48, total Rs -192,354, max drawdown Rs -207,689
  Quarters: 2024Q4 -18 % (n 25); 2025Q1 +18 % (n 27); 2025Q2 +7 % (n 31); 2025Q3 -26 % (n 29); 2025Q4 +1 % (n 33); 2026Q1 -30 % (n 25); 2026Q2 -12 % (n 33); 2026Q3 -36 % (n 25); 2026Q4 -9 % (n 7)
  By weekday: 0 -31 % (n 47); 1 -4 % (n 40); 2 -11 % (n 57); 3 +6 % (n 44); 4 -9 % (n 45); 5 -53 % (n 1); 6 -51 % (n 1)
  By expiry_day: 0 -14 % (n 190); 1 +4 % (n 45)
  By trend_prev: 0 -11 % (n 124); 1 -11 % (n 111)
  By gap_tercile: low -14 % (n 78); mid -2 % (n 79); high -16 % (n 78)
  By vix_tercile: low -15 % (n 80); mid -6 % (n 77); high -11 % (n 78)
  Concentration: the top 5 % of trades earned Rs 273,561 of the set's total Rs -158,781.

## XP expiry-day straddle (107)
- 2024: n 12, max up >= +100 % on 25 % (mean 49 %), win 42 %, mean -4.8 %, median -20.9 %, profit factor 0.73, total Rs -4,925, max drawdown Rs -9,191
- 2025: n 53, max up >= +100 % on 21 % (mean 57 %), win 32 %, mean -7.3 %, median -21.0 %, profit factor 0.72, total Rs -44,387, max drawdown Rs -59,499
- 2026 (partial): n 42, max up >= +100 % on 21 % (mean 50 %), win 33 %, mean -2.9 %, median -25.4 %, profit factor 0.76, total Rs -30,323, max drawdown Rs -63,989
  Quarters: 2024Q4 -5 % (n 12); 2025Q1 -6 % (n 13); 2025Q2 +27 % (n 13); 2025Q3 -13 % (n 14); 2025Q4 -37 % (n 13); 2026Q1 -23 % (n 13); 2026Q2 +10 % (n 13); 2026Q3 -11 % (n 13); 2026Q4 +63 % (n 3)
  By weekday: 0 -11 % (n 5); 1 -11 % (n 55); 2 -67 % (n 2); 3 +5 % (n 45)
  By expiry_day: 1 -5 % (n 107)
  By trend_prev: 0 -14 % (n 57); 1 +5 % (n 50)
  By gap_tercile: low -7 % (n 36); mid +9 % (n 35); high -18 % (n 36)
  By vix_tercile: low -15 % (n 36); mid +7 % (n 35); high -8 % (n 36)
  Concentration: the top 5 % of trades earned Rs 85,414 of the set's total Rs -79,635.
