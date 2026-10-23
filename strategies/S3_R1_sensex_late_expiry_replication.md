# S3 R1 · SENSEX replication: is late-expiry option premium overpriced there too?

Pre-registered 2026-10-23, before any SENSEX option data was read. Rules: DECISIONS.md "S3 · index options". It
runs after the SENSEX Upstox path-band re-fill (queued after market hours 2026-10-23), because the old SENSEX download
has the same missing-ATM gap that NIFTY had.

## Why
On NIFTY's test window (in-sample), the late expiry-day ATM premium looked overpriced:
- **P2**, the long straddle 14:45 → 15:25: −35.8 % of the premium, t −3.17;
- **P6**, the naked short straddle 14:30 → 15:15: +18.7 % (t 2.45); at 5 lots +25 % (t 3.2, descriptive).

Both P6 and P7 failed only on the worst day. SENSEX expiries fall on other days (Friday / Tuesday / Thursday
over the window) and form an independent sample of expiry afternoons. The NIFTY holdout is untouched.

## Data and settings
- SENSEX weekly expiry days in 2024-10-01 → 2025-09-30, as traded (the 1-minute directories), and the `SENSEX` 1-minute
  spot. Strike step 100.
- **Lot:** 20 units on every day. SENSEX lot history is not in the store (there is no BSE bhavcopy), so ₹ figures are
  approximate. % of credit does not depend on the lot, apart from the fixed fees.
- **Costs:** `server/charges.py`. Those are NSE rates; BSE's option transaction charge is close (about ₹32.5 vs
  ₹35.5 a lakh of premium). Slippage as the engine.
- Event days skipped (P1 list); days without prices within 3 minutes listed.

## Cells (all fixed now)
1. **R1a = P6's rule:** sell the ATM CE + PE at 14:30, buy back at 15:15, no stop. Reported at 1 lot and at 5 lots.
2. **R1b = P2's rule:** buy the ATM CE + PE at 14:45, sell at 15:25. 1 lot.
3. **R1c = P7's rule:** a short iron fly ±4 strikes (±400 points) at 14:30 → 15:15, no stop, 5 lots.

## What counts
- **The mean effect replicates if** R1a at 5 lots has a net mean > 0 with t ≥ 2, **and** R1b's net mean is < 0.
- Each cell is also scored on the full S3 gate (2× costs, halves, worst day vs the average month, ≥ 30 trades). A
  replication is a research finding. It does not open any trade; selling is outside "Long options only".

## Amendment 2026-10-23, before any SENSEX option data was read (from the independent review)
1. **Neighbours:** each cell gets real neighbours, the same time shifts as P6 / P2:
   - R1a and R1c: 14:30 → 15:25, 14:45 → 15:15, 14:45 → 15:25;
   - R1b: 14:30 → 15:25, 15:00 → 15:25, 14:45 → 15:15.

   Before this, an empty list made "neighbours positive" pass by default.
2. **R1b trades event days**, as P2 did (a long straddle wants movement).
3. **R1c wings ±6 strikes (±600 points, ~0.75 % of SENSEX)** instead of ±4. This matches P7's ±200 on NIFTY (~0.8 %).
   ±4 would be a narrower, different fly.
4. **The lot stays fixed at 20** (SENSEX's lot changed in late 2024; the store has no SENSEX lot history). % figures
   are lot-free apart from the fixed fees. The 2024-10-25 SENSEX expiry is missing from the store, which leaves one day
   out.
5. **Overlap:** days that are also NIFTY expiry days are reported separately (e.g. 2024-10-31, 2024-11-14), and the
   mean effect is shown without them too.
6. **Placebo (R1d, descriptive): is it an expiry effect?** The R1a trade (sell the ATM straddle of the nearest weekly
   expiry 14:30 → 15:15, 1 and 5 lots) on SENSEX days that are not a SENSEX expiry day, reported by sessions to expiry
   (1, 2, 3+). If the late premium is an expiry-day effect, the placebo is near zero or negative.
