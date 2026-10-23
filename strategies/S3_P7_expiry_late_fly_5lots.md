# S3 P7 · NIFTY expiry-day late short iron fly, no stop, 5 lots (lead from P2s / P6)

Pre-registered 2026-10-23, before its 5-lot test-window numbers were computed. Rules: DECISIONS.md "S3 · index options".
Runner: `scanner/s3_p7.py`.

**Two findings lead here:**
1. **P6** (the naked late short straddle) earned +18.7 % of the credit (t 2.45, in-sample) but failed on its tail:
   the worst day was −₹4,421 against an average month of +₹1,064. Wings cap that tail.
2. **Fees at 1 lot are a sizing artefact.** The ₹20 an order is fixed, and a fly is 8 orders (~₹190 with GST),
   against a 1-lot credit of ~₹1,500-2,000. Re-pricing the saved trades at 5 lots (descriptive, 2026-10-23) moved every
   short pod up 6-18 points; the long straddle (P2) stayed at −27 %. So the late-expiry premium looks overpriced, not
   just under-measured.

**Not independent:** this cell (fly ±4, 14:30 → 15:15, no stop) sits in P2s's grid. At 1 lot it was +4.7 % (t 0.6).
The test window is in-sample. **The holdout (2025-10 → latest, Tuesday expiries) is the test**, run once after an
independent review.

## Trade (primary cell)
- **Days:** every NIFTY weekly expiry day. Skip event days and days without prices within 3 minutes of entry.
- **Entry 14:30:** ATM = the 14:30 spot rounded to 50.
  - Sell the ATM CE and PE.
  - Buy the CE 4 strikes above and the PE 4 strikes below (±200 points).
  - **5 lots.**
- **Exit 15:15** (time). There is no stop and no target: the wings cap the loss.
- **Fills and costs:** engine defaults (0.5 % at 14:30; 1 % for the wings and from 15:00), and `server/charges.py` at
  5 lots.
- **Measure:** net % of the credit and net ₹; % of margin (the fly's maximum loss).

## Gate on the test window (in-sample; opens the holdout only)
- Net mean > 0, and still > 0 at 2× costs.
- t ≥ 2.
- Positive in each half.
- The worst day is smaller than the average month's profit.
- The neighbours (14:30 → 15:25, 14:45 → 15:15, 14:45 → 15:25; fly ±4, no stop, 5 lots) each net positive.
- At least 30 trades.

## Holdout (the test)
Passes if **all** of:
- the net mean is > 0;
- the Sharpe is within 30 % of the test window's;
- the worst holdout day is smaller than the holdout's average month.

## Note
Selling options is outside DECISIONS.md "Long options only" for paper or live. A pass is a research result. Any
trading use needs the user's decision and its own DECISIONS entry. At 5 lots the margin is about ₹50-60k a day.
