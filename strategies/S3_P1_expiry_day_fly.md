# S3 P1 · NIFTY expiry-day iron fly (intraday theta)

Pre-registered 2026-10-22, before any P1 run. Rules: DECISIONS.md "S3 · index options". Engine: `scanner/s3_engine.py`.
Source idea: the user's research note (Section 4 "Intraday theta" pod; practitioner results: 11:15 entry with a 30 %
stop beat 09:20, stop tightness matters more than entry time, and the iron fly has far smaller drawdowns than the
straddle).

Seen before writing this page (descriptive, `data/results/s3_diagnostics.md` §3b, test window, 45 of 54 expiry days):
the 09:20 ATM straddle's median value falls to 76 % by 14:45, but a short straddle 09:20 → 14:45 with no stop averaged
−7.5 % (worst −429 %).

## Trade (primary cell)
- **Days:** every NIFTY weekly expiry day in the window (the expiry as traded: 1-minute files under
  `options_1m/NIFTY/<expiry>/<expiry>.parquet`).
- **Skip:**
  - India VIX at the entry minute outside 13-20 (inclusive);
  - an event day (list below);
  - a day where any leg has no traded price within 3 minutes of entry (counted and listed).
- **Entry 11:15:** ATM = the 11:15 spot close rounded to 50. Sell the ATM CE and PE, buy the CE 4 strikes above and the
  PE 4 strikes below (±200 points). 1 lot (the lot on that day: 25 before 2025-01-31, then 75).
- **Exit**, whichever comes first:
  - combined stop: cost to close ≥ 1.30 × the credit (−30 % of the credit), checked on each minute's last traded closes;
  - time: 14:45. There is no profit target.
- **Fills and costs:** engine defaults: the minute close, 0.5 % slippage (1 % on the wings, being 4 strikes out, and
  on fills 09:15-09:30 / 15:00-15:30), and `server/charges.py`.
- **Measure:** net % of credit and net ₹ per trade; % of margin (the fly's maximum loss) is reported alongside.

## Grid (reported in full; the gate is judged on the primary cell)
- Structure: iron fly (±4 strikes) · short straddle (no wings; margin estimated at 12 % of notional).
- Entry: 09:20 · 10:00 · 11:15.
- Stop: 20 · 25 · 30 · 35 % · none.
- Each cell is run with the VIX 13-20 filter, and also without it (as a side report).

## Gate (test window 2024-10-01 → 2025-09-30), all of
- Net mean per trade > 0, and still > 0 at 2× costs (`cost_mult=2`).
- t ≥ 2 (one trade a day, so trades are already one per date).
- Positive in each half: 2024-10 → 2025-03 and 2025-04 → 2025-09.
- The worst day is smaller (in ₹) than the average month's net profit.
- The neighbours (fly at 11:15 with stop 25 % and 35 %, and the fly at 10:00 with stop 30 %) each net positive.
- At least 30 trades. With fewer, P1 is closed as not testable on this window.

Also reported (never part of the gate):
- by VIX band and by entry weekday;
- the stop rate;
- a Monte Carlo drawdown (10,000 reshuffles of the trade order: the 5th / 50th / 95th percentile of the deepest drawdown).

**Holdout 2025-10-01 → latest**, once, only if the gate passes: net mean > 0 and Sharpe (mean / std per trade) within
30 % of the test window's.

## Event days (no trade)
Union Budget 2025-02-01; RBI policy decisions 2024-10-09, 2024-12-06, 2025-02-07, 2025-04-09, 2025-06-06,
2025-08-06; holdout: 2025-10-01, 2025-12-05. Taken from memory: they are checked against the RBI press releases before
the run, and any correction is recorded here before the run. Only 2025-04-09 is an expiry day in the test window.

## Data
- The run waits for the Upstox path-band re-fill (queued 2026-10-22), so that the expiry days whose ATM strike was
  missing are included.
- Expiry days still without a priced ATM after the re-fill are listed as skipped, with their spot move, so a gap
  cannot hide the bad days.
