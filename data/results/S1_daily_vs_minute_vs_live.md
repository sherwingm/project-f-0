# S1 live strategies: daily-candle old data vs recent vs 1-minute vs live (15 Nov 2026)

Plan: `strategies/S1_daily_vs_minute_vs_live.md` (commit fa02bbb6d, before any number). Descriptive only; nothing live changed.
Net % = net of costs, % of the premium. t = date-clustered. `e1` = sold the same day on daily prices; `e2` = daily-candle -20 % stop path.

## 1. S1 fade, daily-candle backtest by year (entry day-0 open + tick; 2022-01 to 2026-08)

**e1 same-day sale (the v10 rule)**
- 2022: n 105, win 40 %, mean +10.9 %, median -13.7 %, t 1.54, Rs 65,841
- 2023: n 162, win 31 %, mean -7.0 %, median -23.3 %, t -1.26, Rs -105,557
- 2024: n 186, win 38 %, mean +7.2 %, median -19.0 %, t 1.08, Rs 52,650
- 2025: n 222, win 38 %, mean +3.2 %, median -20.2 %, t 0.58, Rs 33,947
- 2026: n 228, win 40 %, mean +5.9 %, median -15.1 %, t 0.98, Rs 64,232
- **Old data (to 2024-09):** n 398, win 36 %, mean +1.4 %, median -16.2 %, t 0.37
- **Oct 2024 to present:** n 505, win 39 %, mean +5.7 %, median -17.4 %, t 1.42
- Recent minus old: +4.3 points (Welch t 0.78); the sign is the same.

**e2 stop path (v11-like)**
- 2022: n 105, win 25 %, mean +21.8 %, median -28.8 %, t 1.35, Rs 158,864
- 2023: n 162, win 20 %, mean -16.2 %, median -38.6 %, t -2.46, Rs -174,945
- 2024: n 186, win 25 %, mean -10.9 %, median -34.5 %, t -2.13, Rs -162,170
- 2025: n 221, win 23 %, mean -9.2 %, median -38.8 %, t -1.45, Rs -109,256
- 2026: n 228, win 24 %, mean -14.6 %, median -35.3 %, t -2.86, Rs -228,103
- **Old data (to 2024-09):** n 398, win 23 %, mean -3.1 %, median -34.3 %, t -0.56
- **Oct 2024 to present:** n 504, win 24 %, mean -12.9 %, median -36.6 %, t -3.43
- Recent minus old: -9.8 points (Welch t -1.50); the sign is the same.

Half-years (e1):
- 2022H1: n 92, win 38 %, mean +10.5 %, median -14.0 %, t 1.35
- 2022H2: n 13, win 54 %, mean +13.8 %, median +15.9 %, t 0.83
- 2023H1: n 87, win 25 %, mean -13.7 %, median -30.4 %, t -1.59
- 2023H2: n 75, win 39 %, mean +0.8 %, median -13.2 %, t 0.12
- 2024H1: n 89, win 38 %, mean +4.9 %, median -16.1 %, t 0.52
- 2024H2: n 97, win 38 %, mean +9.3 %, median -20.7 %, t 0.99
- 2025H1: n 94, win 36 %, mean +1.7 %, median -20.2 %, t 0.16
- 2025H2: n 128, win 40 %, mean +4.3 %, median -20.3 %, t 0.72
- 2026H1: n 143, win 44 %, mean +8.5 %, median -11.0 %, t 1.11
- 2026H2: n 85, win 33 %, mean +1.6 %, median -19.5 %, t 0.16

## 2. S1 arms A / B (daily candles, live rules)

- **Old data 2021-24 (QUOTED from DECISIONS.md, v7 rules, not recomputed):** arm A 258 trades, -17.3 % a trade, t -1.52; arm B 84 trades, +31.8 %, t 1.07 (median -58 % / -57 %).
- **Recent 2025-04 to 2026-08 (recomputed from the v8 file, live rules, entry day+1):**
  - arm A: n 175, win 17 %, mean -5.4 %, median -57.7 %, t -0.46, Rs -62,909
    - 2025: n 72, win 8 %, mean -46.3 %, median -57.2 %, t -10.81, Rs -219,597
    - 2026: n 103, win 22 %, mean +23.1 %, median -57.9 %, t 1.24, Rs 156,688
  - arm B: n 74, win 18 %, mean -14.5 %, median -57.0 %, t -1.01, Rs -69,586
    - 2025: n 26, win 12 %, mean -38.5 %, median -56.7 %, t -3.77, Rs -66,851
    - 2026: n 48, win 21 %, mean -1.5 %, median -57.0 %, t -0.07, Rs -2,734

## 3. The same fade signals on 1-minute candles (entry 09:16 open + tick), Oct 2024 to Aug 2026

Rows passing the live rule: 339 (the retest report quotes 339).

**v10 hold to 15:19**
- 2024: n 40, win 30 %, mean +12.1 %, median -28.3 %, t 0.56; max up mean 91 %, median 40 %
- 2025: n 150, win 41 %, mean +7.1 %, median -16.4 %, t 0.91; max up mean 80 %, median 40 %
- 2026: n 149, win 39 %, mean -1.5 %, median -17.4 %, t -0.27; max up mean 69 %, median 47 %
- all: n 339, win 39 %, mean +3.9 %, median -18.9 %, t 0.78

**v12 live exit**
- 2024: n 40, win 50 %, mean +2.0 %, median +1.8 %, t 0.59
- 2025: n 150, win 57 %, mean +3.4 %, median +6.3 %, t 1.31
- 2026: n 149, win 54 %, mean +2.5 %, median +5.7 %, t 1.06
- all: n 339, win 55 %, mean +2.9 %, median +5.8 %, t 1.79

## 4. Trade-by-trade match, daily vs minutes (same symbol and day0, from 2024-10-01)

- daily trades in the period: 505; minute-rule trades: 339; matched on symbol + day0: 338.
- entry price: minute entry / daily entry median 0.96 (mean 0.94); same strike in 144 of 338 (price within 10 %).
- same-day sale net %: daily e1 mean -0.2 %, minute v10 mean +2.2 %; per-trade difference mean +2.4 points (t 0.75).
- correlation of the two per-trade results 0.83; same sign in 88 % of trades.

## 5. Live paper fade trades (ledger snapshot of 9 Nov; 15 Oct to 9 Nov 2026; distribution only, no date overlap with sections 1-3)

- all closed fade trades: n 70, win 41 %, mean -8.9 %, median -19.9 %, t -1.20, Rs -38,148
- version v11: n 2, win 0 %, mean -30.9 %, median -30.9 %, Rs -3,841
- version v12: n 58, win 47 %, mean -5.7 %, median -16.4 %, t -0.65, Rs -17,916
- version nan: n 10, win 20 %, mean -22.9 %, median -27.5 %, t -2.17, Rs -16,391

## Reading (plain words)
- **Fade, same-day sale (v10 rule), daily candles:** the old data (2022 to Sep 2024) gave +1.4 % a trade (t 0.37) and Oct 2024 to Aug 2026 gave +5.7 % (t 1.42). Same sign, difference not significant (t 0.78). But year by year it swings: 2022 +10.9 %, 2023 -7.0 %, 2024 +7.2 %, 2025 +3.2 %, 2026 +5.9 %. So "about the same" holds only on the average; any single year can look very different.
- **Fade with the daily-candle stop path (e2):** old -3.1 %, recent -12.9 % (t -3.43). The daily stop proxy is known to be unreliable (the 1-minute v12, which actually stops and trails, is +2.9 % over the same dates), so this column should not be used.
- **Arms A / B:** the old result (2021-24, quoted) A -17.3 %, B +31.8 %; recent A -5.4 %, B -14.5 %. Arm B flips sign. Within the recent period arm A is -46 % in 2025 and +23 % in 2026.
- **Daily vs minutes on the same trades:** matched 338 of 339; per-trade results correlate 0.83 and have the same sign 88 % of the time, but the minute entry is about 4-6 % cheaper at the median and in 194 of 338 trades the two sources picked a different strike, so the averages differ by a few points.
- **Live:** 70 closed fade trades (15 Oct to 9 Nov 2026): -8.9 %; the 58 v12 trades -5.7 %. Below both backtests, on a small and short sample, and dates that do not overlap with the backtests.
- **Years 2017-2018:** not available for these strategies: the results filings the S1 signal needs start Dec 2021, and 1-minute option data starts Oct 2024. The index daily bhavcopy goes back to 2018 but no live index strategy has a daily-candle rule.
