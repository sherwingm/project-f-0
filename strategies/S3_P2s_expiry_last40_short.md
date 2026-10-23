# S3 P2s · NIFTY expiry-day last-40-minutes short iron fly, with a stop

Pre-registered 2026-10-23, before any P2s run. Rules: DECISIONS.md "S3 · index options". Engine: `scanner/s3_engine.py`.
Prompted by P2's result (the long ATM straddle 14:45 → 15:25 lost −35.8 % of the premium a trade, t −3.17). The user
asked (2026-10-23): "sell the NIFTY ATM straddle or fly 14:45 -> 15:25 on expiry, with a stop".

**Not independent of P2.** P2's grid (`data/results/S3_P2_report.md`) is close to the mirror image of this trade on the
same days:
- the long +50 % / +100 % target cells are near this pod's 50 % / 100 % stops;
- they differ by the costs, the 1 % slippage and the STT on the sold legs.

So the test window mostly tells whether the costs of the sell side eat the edge. **The holdout (2025-10 → latest,
Tuesday expiries) is the real test.** It runs once, if the gate passes.

## Trade (primary cell)
- **Days:** every NIFTY weekly expiry day in the window. **Skip** event days (DECISIONS / P1 list, as for every
  premium-selling pod) and days where any leg has no traded price within 3 minutes of entry.
- **Entry 14:45:** ATM = the 14:45 spot close rounded to 50.
  - Sell the ATM CE and PE.
  - Buy the CE 4 strikes above and the PE 4 strikes below (±200 points, defined risk, as P1).
  - 1 lot.
- **Exit**, whichever comes first:
  - combined stop: cost to close ≥ 1.30 × the credit (−30 % of the credit). This is the research note's intraday-theta
    stop, 25-30 %, at its upper value. It is not taken from P2's grid;
  - time: 15:25.

  All legs are bought back or sold before the close, so no exercise STT applies.
- **Fills and costs:** engine defaults: the minute close; 0.5 % slippage at 14:30 / 14:45; 1 % for the wings and for any
  fill from 15:00 (the exit is always 1 %); `server/charges.py`, with STT on the sold legs.
- **Measure:** net % of the credit and net ₹ per trade; % of margin (the fly's maximum loss) alongside.

## Grid (reported in full; the gate is judged on the primary cell)
- Structure: iron fly ±4 strikes · iron fly ±2 strikes · short straddle (naked, margin estimated at 12 % of notional).
- Entry: 14:30 · 14:45 · 15:00.
- Exit: 15:15 · 15:25.
- Stop: 25 · 30 · 35 · 50 · 100 % · none.

## Gate (test window 2024-10-01 → 2025-09-30), all of
- Net mean per trade > 0, and still > 0 at 2× costs.
- t ≥ 2.
- Positive in each half: 2024-10 → 2025-03 and 2025-04 → 2025-09.
- The worst day is smaller (in ₹) than the average month's net profit.
- The neighbours (fly ±4, 14:45 → 15:25 with stop 25 % and 35 %; entry 14:30 and 15:00 with stop 30 %; exit 15:15 with
  stop 30 %) each net positive.
- At least 30 trades.

Also reported:
- by VIX band at entry and weekday;
- the stop rate;
- a Monte Carlo drawdown (10,000 reshuffles);
- % of margin.

**Holdout 2025-10-01 → latest**, once, only if the gate passes and after an independent review of the test-window
run (look-ahead, fills, data). It passes if the net mean is > 0 and the Sharpe (mean / std per trade) is within 30 %
of the test window's. It is reported with the same tables.
