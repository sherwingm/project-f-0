# S3 P6 · NIFTY expiry-day late short straddle, no stop (lead from P2s)

Pre-registered 2026-10-23, after P2s and before any P6 holdout run. Rules: DECISIONS.md "S3 · index options". Runner:
`scanner/s3_p6.py` (the `s3_pods` engine path).

**Where it comes from, and why the test window cannot judge it.** In P2s's grid (`data/results/S3_P2s_report.md`)
the naked short ATM straddle with no stop was the best of 108 cells:
- **14:30 → 15:15: +18.7 % of the credit, t 2.4, 50 trades;**
- 14:30 → 15:25: +16.8 % (t 1.8);
- 14:45 → 15:15: +16.0 %;
- 14:45 → 15:25: +13.8 %.

The best of 108 correlated cells at t 2.4 is about what chance gives, so the test-window numbers below are in-sample.
**The holdout (2025-10-01 → latest; Tuesday expiries, a different weekday and lot) is the only real test.** It is run
once, after an independent review.

## Trade (primary cell)
- **Days:** every NIFTY weekly expiry day. Skip event days and days without a price for a leg within 3 minutes of
  entry.
- **Entry 14:30:** ATM = the 14:30 spot close rounded to 50. Sell the ATM CE and PE (naked), 1 lot.
- **Exit 15:15** (time). There is no stop and no target.
- **Fills and costs:** engine defaults (0.5 % slippage at 14:30; 1 % from 15:00) plus `server/charges.py`.
  The margin is estimated at 12 % of notional.
- **Measure:** net % of the credit and net ₹.

## Gate on the test window (in-sample; recorded, but it only opens the holdout)
- Net mean > 0, and still > 0 at 2× costs.
- t ≥ 2.
- Positive in each half.
- The worst day is smaller than the average month's profit.
- The neighbours (14:30 → 15:25, 14:45 → 15:15, 14:45 → 15:25, all no stop) each net positive.
- At least 30 trades.

## Holdout (the test)
Passes if **all** of:
- the net mean is > 0;
- the Sharpe (mean / std per trade) is within 30 % of the test window's;
- the worst holdout day is smaller than the holdout's average month.

It is reported with the 14:45 → 15:25 cell (the research note's window) on the side.

## Note
A naked short straddle is outside DECISIONS.md "Long options only" for any paper or live trade. A pass here is a
research result only. Any trading use needs the user's decision and its own DECISIONS entry.
