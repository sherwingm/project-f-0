# S3 P5 · NIFTY iron condor after a VIX spike: closed on counts, not run

Written 2026-10-23. No P5 returns were computed. Source: the user's research note, Section 4 pod "Vol-spike": an iron
condor after a 1-2 day India VIX spike into 22-30, never naked, with a profit target.

## Event definition (fixed before counting)
- India VIX close (`vix_daily.parquet`) between 22 and 30, and at least 20 % above its close two sessions earlier.
- One event per episode: a spike day within 5 sessions of the previous one does not count again.

## Counts
| Window | Spike days | Episodes | Dates |
|---|---|---|---|
| Test 2024-10 → 2025-09 | 1 | 1 | 2025-04-07 |
| Holdout 2025-10 → latest | 2 | 2 | 2026-03-09, 2026-03-20 |
| 2021-01 → 2024-09 (daily data only) | 3 | 3 | 2022-01-24, 2022-02-14, 2022-02-22 |

That is 6 episodes in about 5¾ years. A test needs at least 30 trades (DECISIONS.md S3). Even 2021-2026 together give
6, so loosening the definition (for example a 15 % rise, or 20-35) would still not get near 30 without changing the
idea itself.

## Verdict
**Closed as not testable** on this data. It is not reopened by loosening the event rule. If a long daily history is
built later (for example NIFTY options from the NSE bhavcopy back to 2008, against VIX from 2008), the same rule can be
counted again there.
