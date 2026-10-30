# S3 G1 · NIFTY big-gap follow-through, long ATM option

Pre-registered 2026-10-30, **before any G1 option return was computed**. Buy only. Rules: DECISIONS.md "S3 · index
options" and "S3 · buy-only, tested on 2024 → today". Engine: `scanner/s3_engine.py`; runner `scanner/s3_buy4.py`.
Idea (the user, 2026-10-30): after a big gap open, buy in the gap's direction if the first 15 minutes confirm it.

## Window
2024-10-01 → 2026-10-28. Halves: 2024-10-01 → 2025-09-30 and 2025-10-01 → 2026-10-28.

## Signal on session d
- **Gap:** the 09:15 bar's open of NIFTY 50 spot against the previous session's last 1-minute close. A big gap is
  **|gap| ≥ 0.5 %**. Up gap → call, down gap → put.
- **Confirmation (first 15 minutes):** the close of the 09:29 bar is beyond the 09:15 open in the gap's direction (up
  gap: above the open; down gap: below it).
- No confirmation, no trade.

**Count before the run** (spot only): 90 sessions with |gap| ≥ 0.5 % (119 at 0.4 %, 73 at 0.6 %).

## Trade (primary)
- **Entry:** the minute after the confirmation bar (09:30 for 15 minutes). Buy 1 lot of the ATM option (strike nearest
  the spot at entry).
- **Expiry:** the nearest weekly expiry with at least one session left after d (on an expiry day, the next one).
- **Exit**, the first of: stop at −**25 %** of the premium paid; trailing stop 25 % below the highest value since
  entry (once in profit); time 15:15.
- Costs and lot as in every S3 pod.

## Gate (unchanged S3 gate)
At least 30 trades; net mean % of the premium paid > 0 and > 0 at 2× costs; t ≥ 2; positive in each half; worst trade
smaller than the average month (₹); neighbours net positive.

**Neighbours (fixed):** gap 0.4 % and 0.6 %; confirmation after 12 and 18 minutes; stop 20 % and 30 %.

## Also reported (no effect on the verdict)
- **Baseline:** every big gap traded in its direction with no confirmation (same entry minute and exits).
- Up gaps vs down gaps; exits by reason; every trade.

## Look-ahead
The gap uses the previous session's close and d's first bar; the confirmation uses bars to the end of the window; the
fill is the next minute's close. No parameter is picked from G1's results.
