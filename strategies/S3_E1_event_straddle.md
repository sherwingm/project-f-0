# S3 E1 · NIFTY long ATM straddle across a scheduled event

Pre-registered 2026-10-30, **before any E1 option return was computed**. Buy only. Rules: DECISIONS.md "S3 · index
options" and "S3 · buy-only, tested on 2024 → today". Engine: `scanner/s3_engine.py`; runner `scanner/s3_buy4.py`.
Idea (the user, 2026-10-30): buy a straddle 1-2 days before a known big day and sell after it.

## Window
2024-10-01 → 2026-10-28 (the 1-minute option era to the latest stored session). Halves: 2024-10-01 → 2025-09-30 and
2025-10-01 → 2026-10-28.

## Events (fixed now; the "event session" E is the NSE session where the news lands)
- **RBI MPC decision** (10:00 IST). 2024-10-09, 2024-12-06, 2025-02-07, 2025-04-09, 2025-06-06, 2025-08-06 (moved to
  4-6 Aug, RBI press release 2025-2026/497), 2025-10-01, 2025-12-05, 2026-02-06, 2026-04-08, 2026-06-05, 2026-08-05,
  2026-10-07. 2026 dates: RBI press release "Meeting Schedule of the Monetary Policy Committee for 2026-2027"
  (23 Mar 2026); the April, June, August and October decisions were reported on those dates.
- **Union Budget** (11:00 IST): 2025-02-01 (Saturday session), 2026-02-01 (Sunday special live session, NSE circular).
- **US FOMC statement** (≈ 23:30-00:00 IST, after NSE's close), so E = **the first NSE session after the statement
  date**. Statement dates (federalreserve.gov FOMC calendar): 2024-11-07, 2024-12-18; 2025-01-29, 03-19, 05-07, 06-18,
  07-30, 09-17, 10-29, 12-10; 2026-01-28, 03-18, 04-29, 06-17, 07-29, 09-16. (2026-10-28's reaction session, 10-29, is
  after the window.)
- **US presidential election 2024**: results came in during the Indian session of 2024-11-06, so E = 2024-11-06.

That is 32 events. If E has no spot session in the store (known gap: 2025-02-01), the event is skipped and listed.

## Trade (primary)
- **Entry:** 14:45 on the session before E (E − 1). Buy 1 lot each of the ATM call and ATM put (the strike nearest
  the spot at 14:45).
- **Expiry:** the nearest NIFTY expiry strictly after the exit session, with a chain file on the entry and exit
  sessions. So no position is held into its own expiry day.
- **Exit:** 14:45 on E. No stop, no target.
- **Costs:** engine fills (0.5 % slippage; 1 % before 09:30 / after 15:00 or ≥ 2 strikes out), `server/charges.py`.
  1 lot by the traded contract (bhavcopy lot).
- Events are independent: two event trades may overlap in time (each is its own trade).

## Gate (unchanged S3 gate)
At least 30 trades; net mean % of the premium paid > 0 and > 0 at 2× costs; t ≥ 2; positive in each half; worst trade
smaller than the average month (₹); neighbours net positive.

**Neighbours (fixed):** enter E − 2 (14:45) → exit E (14:45); enter E − 1 → exit E + 1 (14:45); enter E − 1 → exit
12:00 on E.

## Also reported (no effect on the verdict)
- By event type (RBI, Budget, FOMC, US election).
- **Baseline:** the same E − 1 → E straddle on every ordinary session pair in the window (E not an event and not the
  session after an FOMC date). Is an event better than an ordinary day?
- Every trade with its legs, fees and exit.

## Look-ahead
Every event date is published weeks ahead (RBI calendar, Fed calendar, Budget date). Entry uses the 14:45 spot and
option prices of E − 1 only; the exit is a fixed time. No parameter is picked from E1's results.
