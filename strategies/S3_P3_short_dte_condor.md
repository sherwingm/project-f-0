# S3 P3 · NIFTY 1-3 DTE iron condor, shorts near 0.175 delta

Pre-registered 2026-10-23, before any P3 run. Rules: DECISIONS.md "S3 · index options". Engine: `scanner/s3_engine.py`
(multi-day hold). Source: the user's research note, Section 4 pod "Defined-risk premium": 1 to 3 DTE iron condor,
short strikes at 0.15-0.20 delta, active when VIX 14-20 and ADX below 20, 50 % profit target or a stop.

**Regime filter, decided on counts only (no returns seen):** in the test window the research's filter (India VIX 14-20
at entry and ADX(14) < 20 at the previous close) leaves 3-4 trades (T-1: 3, T-2: 4, T-3: 4). With VIX 14-20 alone it
leaves 26-29, and with ADX < 20 alone 10-12. Neither reaches the 30-trade minimum. **So the primary cell has no regime
filter**, and the filtered results are side reports only.

## Trade (primary cell)
- **One trade per weekly expiry**, entered at **15:00 on T-2**: the second trading session before the expiry day.
  For a Thursday expiry that is Tuesday; for a Tuesday expiry, the Friday before.
- **Skip:**
  - an event day (P1 list) anywhere from the entry day to the expiry day;
  - no price for a leg within 3 minutes of entry;
  - no strike with |delta| in 0.10-0.25 on a side.
- **Strikes:**
  - each short leg is the out-of-the-money strike whose |delta| is closest to 0.175. Delta is Black-Scholes, from
    that strike's own implied vol at 15:00 (r 6.5 %, time to 15:30 on the expiry day, calendar);
  - the wings are 2 strikes (100 points) beyond each short.

  Sell the short CE and PE, buy the wings, 1 lot (the lot on the entry day).
- **Exit**, the first of:
  - target: cost to close ≤ 50 % of the credit;
  - stop: cost to close ≥ 2 × the credit (a loss equal to the credit);
  - time: 15:15 on the expiry day.

  Marks are each minute's last traded closes, across nights. A gap at the open is marked at the first fresh prices.
  All legs are closed before 15:30, so no exercise STT applies.
- **Fills and costs:** engine defaults. Every leg is ≥ 2 strikes from the money, so slippage is 1 % on each fill; plus
  `server/charges.py`.
- **Measure:** net % of the credit and net ₹; % of margin (width − credit) alongside.

## Grid (reported in full; the gate is judged on the primary cell)
- Entry: T-1 · T-2 · T-3 at 15:00.
- Short delta: 0.15 · 0.175 · 0.20.
- Wings: 2 · 4 strikes.
- Target: 50 % · none.
- Stop: loss of 100 % · 200 % of the credit · none.

Side reports: the primary cell with VIX 14-20, with ADX < 20 and with both.

## Gate (test window 2024-10-01 → 2025-09-30, by entry day), all of
- Net mean per trade > 0, and still > 0 at 2× costs.
- t ≥ 2.
- Positive in each half.
- The worst trade is smaller (in ₹) than the average month's net profit.
- The neighbours (delta 0.15 and 0.20; entry T-1 and T-3; all else as the primary) each net positive.
- At least 30 trades.

**Holdout 2025-10-01 → latest**, once, only if the gate passes and after an independent review. It passes if the net
mean is > 0 and the Sharpe is within 30 % of the test window's.
