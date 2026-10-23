# S3 D3-D5 · placebo, tail study, SENSEX natural experiment (descriptive)

Pre-registered 2026-10-23, before running. They follow up the independent review's open items. All are descriptive:
none can pass a pod. Expiry-afternoon spot work stops at 2025-09-30 (DECISIONS.md, 2026-10-23), and nothing here reads
holdout option returns.

## D3 · NIFTY placebo: is the late premium an expiry-day effect?
- The P6 trade on **test-window NIFTY days that are not NIFTY expiry days**: sell the ATM straddle of the nearest
  weekly expiry with a chain that day, 14:30 → 15:15, no stop, event days skipped. At 1 and 5 lots.
- Reported overall and by sessions left to the expiry (1, 2, 3+), next to P6's expiry-day result.
- **Reading:** if P6's edge is an expiry-day effect, the placebo is clearly weaker, near zero or negative.

## D4 · Tail study on spot, NIFTY expiry days 2021-10-20 → 2025-09-30
- For each NIFTY expiry day (traded on its date): the 14:30 → 15:15 move |S(15:15) / S(14:30) − 1| and the largest
  excursion from S(14:30) between them, in %.
- **Premium proxy:** credit % of spot = k × India VIX at 14:30. k is the median of (P6 credit / spot / VIX) over P6's
  re-run test-window trades.
- **Proxy P&L** (% of credit) = (credit % − move %) / credit %. It ignores the time value left at 15:15. Its bias is
  measured against P6's actual trades on the test window, and the mean bias is subtracted.
- Reported for 2021-10 → 2024-09 (before the minute options) and for the test window:
  - the mean proxy P&L;
  - the share of days losing more than 1× and 2× the credit;
  - the worst day;
  - the worst day against the average month (in % units: the worst day's % against the average monthly sum of
    trade %).

  Also the proxy on the stress-window expiry days (2022-02-24, the nearest expiries to 2024-06-04 and 2024-08-05).
- **Reading:** whether P6 / P7's worst-day failure is typical of longer history or a one-off.

## D5 · SENSEX natural experiment: Friday lost its weekly expiry (last Friday expiry 2025-01-03)
- SENSEX weekly expiries (from the store's directory names; Oct 2024 →): Friday until 2025-01-03, Tuesday 2025-01-07 →
  2025-08-26, Thursday from 2025-09-04. Before Oct 2024, Fridays from the 2023-05-15 relaunch are taken as SENSEX
  expiries; a Friday holiday has no session, so it drops out on its own.
- **Friday:** before = Fridays 2023-05-19 → 2025-01-03 (expiry); after = Fridays 2025-01-10 → 2025-09-30 (no expiry).
- **Tuesday:** before = Tuesdays 2023-05-16 → 2024-12-31 (no SENSEX expiry); after = SENSEX Tuesday expiries
  2025-01-07 → 2025-08-26.
- **Control:** SENSEX Mondays, the same periods.
- Same difference-in-differences ratio and bootstrap as D2, on SENSEX 1-minute spot. r_last = 15:00 → 15:29.
- Also the D2 §3 reversal (the slope of r_last on r_day) on SENSEX expiry days 2025-01-07 → 2025-09-30 against other days.
