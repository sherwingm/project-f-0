# Y1: daily-candle studies by year, 2018 to 2026, Covid period (2020-02-15 to 2020-06-30) excluded

Plan: `index_research/PROGRAM.md` Amendment A6 (commit eb2f7437b, before any number). Slices of saved trade files; nothing re-run, nothing promoted.
Net % per trade after costs (% of notional for futures, of credit / premium for options). Cells with fewer than 8 trades in a year are shown as 'few'.

## R02b: overnight on the real future (daily)
- BANKNIFTY|overnight_all: 2018 -0.11 | 2019 +0.00 | 2020 +0.04 | 2021 -0.01 | 2022 -0.07 | 2023 -0.02 | 2024 -0.04 | 2025 -0.05 | 2026 -0.11 | positive years 2 of 9, sign flips between consecutive years 2; 2018-21 -0.02 (n 854) vs 2022-26 -0.06 (n 1129), diff -0.03 (t -1.19)
- BANKNIFTY|overnight_prevup: 2018 -0.07 | 2019 +0.06 | 2020 -0.00 | 2021 +0.10 | 2022 +0.07 | 2023 +0.04 | 2024 +0.03 | 2025 -0.01 | 2026 -0.13 | positive years 5 of 9, sign flips between consecutive years 4; 2018-21 +0.02 (n 452) vs 2022-26 +0.01 (n 605), diff -0.01 (t -0.36)
- NIFTY|overnight_all: 2018 -0.07 | 2019 -0.04 | 2020 +0.05 | 2021 +0.02 | 2022 -0.08 | 2023 -0.02 | 2024 -0.02 | 2025 -0.05 | 2026 -0.13 | positive years 2 of 9, sign flips between consecutive years 2; 2018-21 -0.02 (n 854) vs 2022-26 -0.06 (n 1131), diff -0.04 (t -1.89)
- NIFTY|overnight_prevup: 2018 -0.03 | 2019 -0.03 | 2020 +0.06 | 2021 +0.04 | 2022 +0.03 | 2023 +0.01 | 2024 +0.02 | 2025 -0.03 | 2026 -0.13 | positive years 5 of 9, sign flips between consecutive years 2; 2018-21 +0.01 (n 487) vs 2022-26 -0.01 (n 593), diff -0.02 (t -0.65)

## R09: weekly ATM straddle to expiry (daily bhavcopy)
- BANKNIFTY|long_all: 2018 +1.20 | 2019 +0.11 | 2020 -10.79 | 2021 -9.31 | 2022 -15.08 | 2023 +1.73 | 2024 -1.36 | 2025 +0.87 | 2026 +0.42 | positive years 5 of 9, sign flips between consecutive years 4; 2018-21 -4.11 (n 190) vs 2022-26 -4.36 (n 171), diff -0.25 (t -0.03)
- BANKNIFTY|long_vixpct_gt70: 2018 few | 2019 -5.72 | 2020 few | 2021 few | 2022 -7.04 | 2023 few | 2024 -8.64 | 2025 few | 2026 few | positive years 0 of 3, sign flips between consecutive years 0; 2018-21 -2.37 (n 22) vs 2022-26 -8.60 (n 55), diff -6.23 (t -0.37)
- BANKNIFTY|long_vixpct_lt30: 2018 - | 2019 +7.61 | 2020 -60.75 | 2021 -2.86 | 2022 -14.62 | 2023 -1.10 | 2024 few | 2025 few | 2026 few | positive years 1 of 5, sign flips between consecutive years 1; 2018-21 -8.54 (n 52) vs 2022-26 +4.38 (n 68), diff +12.93 (t 0.94)
- BANKNIFTY|long_vov_high: 2018 few | 2019 +0.90 | 2020 -11.67 | 2021 +2.04 | 2022 -14.37 | 2023 -0.71 | 2024 -8.11 | 2025 few | 2026 +14.92 | positive years 3 of 7, sign flips between consecutive years 3; 2018-21 -1.96 (n 60) vs 2022-26 -6.34 (n 85), diff -4.37 (t -0.34)
- BANKNIFTY|long_vov_low: 2018 few | 2019 -0.43 | 2020 -9.73 | 2021 -14.67 | 2022 -15.73 | 2023 +3.06 | 2024 +14.55 | 2025 +2.83 | 2026 few | positive years 3 of 7, sign flips between consecutive years 1; 2018-21 -8.17 (n 87) vs 2022-26 -2.41 (n 86), diff +5.76 (t 0.53)
- BANKNIFTY|short_all: 2018 -4.16 | 2019 -2.89 | 2020 +8.19 | 2021 +6.77 | 2022 +12.54 | 2023 -4.42 | 2024 -1.19 | 2025 -3.49 | 2026 -3.00 | positive years 3 of 9, sign flips between consecutive years 2; 2018-21 +1.38 (n 190) vs 2022-26 +1.77 (n 171), diff +0.39 (t 0.05)
- BANKNIFTY|short_vixpct_gt70: 2018 few | 2019 +2.91 | 2020 few | 2021 few | 2022 +4.58 | 2023 few | 2024 +6.14 | 2025 few | 2026 few | positive years 3 of 3, sign flips between consecutive years 0; 2018-21 -0.42 (n 22) vs 2022-26 +6.10 (n 55), diff +6.53 (t 0.39)
- BANKNIFTY|short_vixpct_lt30: 2018 - | 2019 -10.42 | 2020 +58.05 | 2021 +0.26 | 2022 +11.96 | 2023 -1.61 | 2024 few | 2025 few | 2026 few | positive years 3 of 5, sign flips between consecutive years 2; 2018-21 +5.86 (n 52) vs 2022-26 -7.07 (n 68), diff -12.94 (t -0.94)
- BANKNIFTY|short_vov_high: 2018 few | 2019 -3.70 | 2020 +9.08 | 2021 -4.52 | 2022 +11.88 | 2023 -1.93 | 2024 +5.57 | 2025 few | 2026 -17.49 | positive years 3 of 7, sign flips between consecutive years 5; 2018-21 -0.69 (n 60) vs 2022-26 +3.79 (n 85), diff +4.48 (t 0.35)
- BANKNIFTY|short_vov_low: 2018 few | 2019 -2.35 | 2020 +7.13 | 2021 +12.10 | 2022 +13.15 | 2023 -5.78 | 2024 -17.12 | 2025 -5.47 | 2026 few | positive years 3 of 7, sign flips between consecutive years 2; 2018-21 +5.50 (n 87) vs 2022-26 -0.23 (n 86), diff -5.73 (t -0.53)
- NIFTY|long_all: 2018 +10.51 | 2019 -8.93 | 2020 -5.07 | 2021 -5.93 | 2022 -11.60 | 2023 +4.12 | 2024 -2.59 | 2025 -7.10 | 2026 -7.08 | positive years 2 of 9, sign flips between consecutive years 3; 2018-21 -5.35 (n 145) vs 2022-26 -4.80 (n 249), diff +0.55 (t 0.07)
- NIFTY|long_vixpct_gt70: 2018 few | 2019 -22.32 | 2020 few | 2021 few | 2022 +1.37 | 2023 few | 2024 -21.33 | 2025 -28.80 | 2026 -15.44 | positive years 1 of 5, sign flips between consecutive years 0; 2018-21 -12.66 (n 14) vs 2022-26 -14.93 (n 76), diff -2.27 (t -0.09)
- NIFTY|long_vixpct_lt30: 2018 - | 2019 +9.74 | 2020 -33.75 | 2021 -4.33 | 2022 -29.35 | 2023 +4.93 | 2024 few | 2025 -1.20 | 2026 few | positive years 2 of 6, sign flips between consecutive years 2; 2018-21 -4.53 (n 52) vs 2022-26 +8.78 (n 100), diff +13.30 (t 1.00)
- NIFTY|long_vov_high: 2018 - | 2019 -0.15 | 2020 -5.71 | 2021 +9.22 | 2022 -9.96 | 2023 -6.08 | 2024 -7.73 | 2025 -4.73 | 2026 -10.01 | positive years 1 of 8, sign flips between consecutive years 2; 2018-21 +0.95 (n 54) vs 2022-26 -8.20 (n 122), diff -9.15 (t -0.73)
- NIFTY|long_vov_low: 2018 few | 2019 -14.90 | 2020 -4.30 | 2021 -13.08 | 2022 -13.11 | 2023 +9.68 | 2024 +7.98 | 2025 -7.89 | 2026 +1.17 | positive years 3 of 8, sign flips between consecutive years 3; 2018-21 -10.40 (n 81) vs 2022-26 -1.53 (n 127), diff +8.87 (t 0.84)
- NIFTY|short_all: 2018 -13.76 | 2019 +5.84 | 2020 +2.17 | 2021 +3.17 | 2022 +8.95 | 2023 -7.00 | 2024 -0.04 | 2025 +4.41 | 2026 +4.42 | positive years 6 of 9, sign flips between consecutive years 3; 2018-21 +2.41 (n 145) vs 2022-26 +2.09 (n 249), diff -0.31 (t -0.04)
- NIFTY|short_vixpct_gt70: 2018 few | 2019 +19.25 | 2020 few | 2021 few | 2022 -3.91 | 2023 few | 2024 +18.74 | 2025 +26.25 | 2026 +12.89 | positive years 4 of 5, sign flips between consecutive years 0; 2018-21 +9.65 (n 14) vs 2022-26 +12.36 (n 76), diff +2.71 (t 0.11)
- NIFTY|short_vixpct_lt30: 2018 - | 2019 -12.97 | 2020 +30.64 | 2021 +1.48 | 2022 +26.56 | 2023 -7.83 | 2024 few | 2025 -1.55 | 2026 few | positive years 3 of 6, sign flips between consecutive years 2; 2018-21 +1.52 (n 52) vs 2022-26 -11.60 (n 100), diff -13.12 (t -0.99)
- NIFTY|short_vov_high: 2018 - | 2019 -2.96 | 2020 +2.82 | 2021 -11.88 | 2022 +7.38 | 2023 +3.27 | 2024 +5.10 | 2025 +2.12 | 2026 +7.39 | positive years 6 of 8, sign flips between consecutive years 3; 2018-21 -3.84 (n 54) vs 2022-26 +5.56 (n 122), diff +9.40 (t 0.76)
- NIFTY|short_vov_low: 2018 few | 2019 +11.81 | 2020 +1.37 | 2021 +10.28 | 2022 +10.41 | 2023 -12.60 | 2024 -10.63 | 2025 +5.17 | 2026 -3.97 | positive years 5 of 8, sign flips between consecutive years 3; 2018-21 +7.47 (n 81) vs 2022-26 -1.24 (n 127), diff -8.71 (t -0.83)

## R14: trend filters on NIFTY
- cross: 2018 - | 2019 few | 2020 few | 2021 - | 2022 few | 2023 few | 2024 - | 2025 few | 2026 - | positive years 0 of 0, sign flips between consecutive years 0; 2018-21 +5.48 (n 3) vs 2022-26 +6.52 (n 3)
- donchian: 2018 few | 2019 few | 2020 few | 2021 few | 2022 few | 2023 few | 2024 few | 2025 -1.31 | 2026 few | positive years 0 of 1, sign flips between consecutive years 0; 2018-21 +1.21 (n 20) vs 2022-26 +0.10 (n 27), diff -1.11 (t -0.97)
- sma200: 2018 few | 2019 +0.01 | 2020 few | 2021 - | 2022 few | 2023 few | 2024 few | 2025 few | 2026 few | positive years 1 of 1, sign flips between consecutive years 0; 2018-21 +2.83 (n 17) vs 2022-26 +0.96 (n 17), diff -1.88 (t -0.51)
- sma200_ls: 2018 -0.75 | 2019 -0.48 | 2020 few | 2021 - | 2022 -1.40 | 2023 few | 2024 few | 2025 few | 2026 few | positive years 0 of 3, sign flips between consecutive years 0; 2018-21 +0.94 (n 33) vs 2022-26 -0.38 (n 34), diff -1.33 (t -0.70)

## R15: short-term reversal on NIFTY
- down3: 2018 -0.18 | 2019 +0.04 | 2020 +0.12 | 2021 +0.01 | 2022 -0.29 | 2023 -0.14 | 2024 -0.21 | 2025 -0.00 | 2026 -0.07 | positive years 3 of 9, sign flips between consecutive years 2; 2018-21 -0.02 (n 97) vs 2022-26 -0.15 (n 157), diff -0.13 (t -0.89)
- rsi2: 2018 +0.11 | 2019 -0.28 | 2020 +1.39 | 2021 +0.79 | 2022 +0.20 | 2023 +0.29 | 2024 +0.22 | 2025 +0.57 | 2026 few | positive years 7 of 8, sign flips between consecutive years 2; 2018-21 +0.51 (n 38) vs 2022-26 +0.29 (n 44), diff -0.22 (t -0.69)
- rsi2_short: 2018 few | 2019 few | 2020 few | 2021 - | 2022 few | 2023 few | 2024 - | 2025 few | 2026 few | positive years 0 of 0, sign flips between consecutive years 0; 2018-21 -0.26 (n 4) vs 2022-26 -0.49 (n 17), diff -0.24 (t -0.33)
- up3_short: 2018 -0.15 | 2019 -0.03 | 2020 -0.25 | 2021 -0.03 | 2022 -0.12 | 2023 -0.22 | 2024 -0.20 | 2025 -0.19 | 2026 +0.08 | positive years 1 of 9, sign flips between consecutive years 1; 2018-21 -0.11 (n 186) vs 2022-26 -0.16 (n 207), diff -0.04 (t -0.56)

## R17: calendar effects on NIFTY
- mon_short: 2018 +0.03 | 2019 +0.09 | 2020 +0.44 | 2021 +0.07 | 2022 -0.19 | 2023 -0.01 | 2024 +0.08 | 2025 -0.16 | 2026 -0.14 | positive years 5 of 9, sign flips between consecutive years 3; 2018-21 +0.12 (n 180) vs 2022-26 -0.08 (n 239), diff -0.20 (t -2.58)
- tom: 2018 +0.18 | 2019 +0.37 | 2020 few | 2021 +0.96 | 2022 +1.22 | 2023 +0.98 | 2024 +0.07 | 2025 -0.15 | 2026 -0.94 | positive years 6 of 8, sign flips between consecutive years 1; 2018-21 +0.49 (n 43) vs 2022-26 +0.30 (n 57), diff -0.19 (t -0.47)
- weekend: 2018 +0.10 | 2019 +0.16 | 2020 +0.27 | 2021 +0.13 | 2022 -0.22 | 2023 +0.14 | 2024 +0.15 | 2025 -0.10 | 2026 -0.27 | positive years 6 of 9, sign flips between consecutive years 3; 2018-21 +0.15 (n 169) vs 2022-26 -0.06 (n 219), diff -0.21 (t -3.03)

## R18: NIFTY / BANKNIFTY ratio
- ratio: 2018 few | 2019 few | 2020 few | 2021 few | 2022 +0.03 | 2023 few | 2024 few | 2025 few | 2026 few | positive years 1 of 1, sign flips between consecutive years 0; 2018-21 +0.85 (n 21) vs 2022-26 -0.30 (n 31), diff -1.16 (t -1.21)

## R19: calendar straddle
- NIFTY|calendar_all: 2018 - | 2019 -7.17 | 2020 -4.93 | 2021 -4.37 | 2022 -2.86 | 2023 -5.40 | 2024 -5.33 | 2025 -2.07 | 2026 -5.38 | positive years 0 of 8, sign flips between consecutive years 0; 2018-21 -5.48 (n 130) vs 2022-26 -4.15 (n 242), diff +1.33 (t 0.59)
- NIFTY|calendar_lowvix: 2018 - | 2019 -11.96 | 2020 +1.22 | 2021 -4.82 | 2022 -0.21 | 2023 -6.10 | 2024 few | 2025 -5.65 | 2026 few | positive years 1 of 6, sign flips between consecutive years 2; 2018-21 -6.09 (n 52) vs 2022-26 -8.05 (n 96), diff -1.96 (t -0.53)
