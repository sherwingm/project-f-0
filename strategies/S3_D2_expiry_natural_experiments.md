# S3 D2 · expiry natural experiments on spot (descriptive, no trades)

Pre-registered 2026-10-23, before running. Spot and VIX diagnostics may use 2021 → latest (DECISIONS.md S3).
Source claims (the user's research note, Section 2):
- when an index lost its expiry, its last half hour became calmer (4 of 5 cases);
- on Bank Nifty expiry days in 2023-2025, the last half hour tended to reverse the day's move.

Measure: `r_last` = ln(close 15:29 / close 15:00); `r_day` = ln(close 15:00 / previous close 15:29). Data: 1-minute
spot `NIFTY50`, `NIFTYBANK`, 2021-10 → latest.

## 1. NIFTY lost Thursday, gained Tuesday (weekly expiry Thursday until 2025-08-28, Tuesday from 2025-09-02)
- **Before:** 2021-10-21 → 2025-08-31. **After:** 2025-09-01 → latest. Expiry days are as traded (bhavcopy XpryDt + the
  1-minute files), so holiday shifts are respected.
- For Thursday and for Tuesday: the mean r_last² after / before.
- **Control:** the same ratio on Monday, Wednesday and Friday pooled (the market-wide change).
- **Headline:** the difference-in-differences ratio = (weekday after / before) / (control after / before).
  - The claim predicts Thursday < 1 and Tuesday > 1.
  - A 95 % bootstrap interval (2,000 draws, resampling days within each of the 4 groups).

## 2. BANKNIFTY lost its weekly expiry (its last weekly: 2024-11-13; weekly on Wednesday from 2023-09-06)
- **Lost weekday:** Wednesday. Before = BANKNIFTY weekly expiry Wednesdays 2023-09-06 → 2024-11-13; after = Wednesdays
  from 2024-11-20 that are not a BANKNIFTY expiry.
- **Control:** BANKNIFTY Mon / Tue / Thu / Fri non-expiry days, the same two periods.
- Same difference-in-differences ratio and bootstrap.

## 3. BANKNIFTY last-half-hour reversal on its expiry days, 2023-01-01 → 2025-12-31
- On BANKNIFTY expiry days (weekly and monthly, as traded) vs its other days:
  - the share of days where r_last has the opposite sign to r_day;
  - the slope of r_last on r_day with its t.

  The claim predicts a negative slope on expiry days.

No parameter is tuned. This is descriptive: it can point to a pod, but cannot pass one.
