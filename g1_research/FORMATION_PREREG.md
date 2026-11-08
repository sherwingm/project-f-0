# Formation patterns, one at a time: pre-registered 2026-11-08 (before any feature was computed)

**Question (the user):** "try more of the formation pattern, even without any combination." So: price-shape facts about how the
opening range and the breakout formed, each tested ALONE (no combinations, no scores). Record-only research; nothing here changes
a live rule. Max up is the outcome.

## Data and split
The 259 G1 history signals (same as before). Discovery = entry day before 2025-10-01 (128); validation = from 2025-10-01 (131).
All cut-points come from discovery. NIFTY 1-minute spot bars for each day (`index_data`), daily bars (`scanner.s3_regime.daily`).
Everything is known by the signal minute (bars up to and including it; no later data).

## Outcome (fixed)
`reach` = max up through the next close (`peak_k1`, put's highest later minute close, no stop) **>= +100 %**. Shown with it: share
>= +50 %, mean and median max up, then the booked result (next-close exit, 50 % stop).

## The features (28, each alone). "OR" = 09:15-09:29 range, "signal bar" = the 1-minute bar whose close broke below the OR low.
Opening-range formation
1. or_close_pos: OR close (09:29) position inside the OR, 0 = at the low, 1 = at the high
2. or_trend: OR close vs OR open, %
3. or_lo_time: minutes from 09:15 to the OR low
4. or_hi_time: minutes from 09:15 to the OR high
5. or_front: range of the first 5 minutes / OR range
6. or_last5: OR close vs close at 09:24, %
7. or_low_touches: number of OR minutes whose low is within 0.02 % of the OR low
8. open_pos: day open position inside the OR, 0 = low, 1 = high
Between 09:30 and the signal
9. retest_hi: highest high from 09:30 to the signal minus OR high, % of OR high (a failed up-break first)
10. low_half: share of closes from 09:30 to the signal that sit in the lower half of the OR
11. n_inside: number of 1-minute closes inside the OR before the break
12. squeeze: signal-bar open vs OR low, %  (how close it was sitting to the low before it broke)
Signal bar (the breakout candle)
13. bo_body: (open - close) / (high - low)
14. bo_close_pos: (close - low) / (high - low), 0 = closed on the low
15. bo_range: (high - low) / close, %
16. bo_range_x: signal-bar range / mean range of the 14 bars before it
17. bo_gap_prev: signal-bar open vs previous bar close, %
Yesterday and recent days (daily bars)
18. pd_close_pos: yesterday's close position in yesterday's range
19. pd_body: (yesterday close - open) / yesterday range
20. pd_range: yesterday's range, % of close
21. pd_nr7: yesterday's range / mean range of the 7 days before it
22. pd_inside (0/1): yesterday inside the day before it (inside day)
23. pd_low_break (0/1): signal close below yesterday's low
24. open_vs_pd: today's open position inside yesterday's range (can be outside 0-1)
25. or_vs_pd: OR width / yesterday's range
26. or_vs_atr: OR width / mean daily range of the last 5 days
27. down_streak: number of down-close days in the last 3 days (0-3)
28. lo_vs_pdl: OR low vs yesterday's low, %

## Rules (fixed)
- Continuous feature: two rules, "high" = at or above the discovery 67th percentile and "low" = at or below the 33rd. 0/1 feature: one
  rule ("= 1"). Rule count about 50; one family; Benjamini-Hochberg at FDR 10 % across all of it, Fisher exact two-sided on `reach`.
- **Candidate** = q <= 0.10, at least 25 signals in the bucket, effect (bucket reach - outside reach) in either direction. A bucket
  that picks LOWER reach is as useful (a warning).
- **Validation, once:** same direction, one-sided Fisher p < 0.05, at least 20 signals in the bucket, effect at least half the
  discovery effect. Labels: Observed / Suggestive (BH in discovery) / Passed validation / Rejected.
- Robustness of anything that passes: by year, G1-F only, without the 10 largest max-ups.
- No re-tuning afterwards. "No formation pattern" is a valid answer. It is a search with no third untouched period, so a pass is
  "passed validation", and the live paper run is the real test.
