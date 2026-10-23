# S3 P2 · NIFTY expiry-day last-30-minutes long straddle (gamma)

Pre-registered 2026-10-23, before any P2 run. Rules: DECISIONS.md "S3 · index options". Engine: `scanner/s3_engine.py`.
Source idea: the user's research note, Section 2 (on expiry days the last half hour's variance is 50-70 % higher) and
Section 4 (the "Expiry last-30-min gamma" pod: a small long ATM straddle, 14:45 to 15:25, time exit).

Seen before writing this page (descriptive, `data/results/s3_diagnostics.md`):
- On NIFTY spot 2021-26 the 15:00 → 15:29 variance on expiry days is 1.31x other days (95 % interval 0.97-1.73x).
- In the test window, the expiry-day ATM straddle fixed at the 09:20 strike was worth a median 81 % of its 09:20 value
  at 14:45 and 90 % at 15:25. That straddle is not P2's: P2's strike is set at 14:45.
- P1 (short fly / straddle 09:20-11:15 → 14:45) failed.

## Trade (primary cell)
- **Days:** every NIFTY weekly expiry day in the window (the expiry as traded). There is no VIX filter and no event
  skip: a long straddle wants movement, so events are kept. VIX bands and event days are reported on the side.
- **Skip:** a day where either leg has no traded price within 3 minutes of entry (counted and listed).
- **Entry 14:45:** ATM = the 14:45 spot close rounded to 50. Buy the ATM CE and the ATM PE, 1 lot (the lot on that day).
- **Exit 15:25** (time). There is no stop and no target: the loss is capped at the premium paid. Both legs are sold
  before the close, so no exercise STT applies.
- **Fills and costs:** engine defaults: the minute close, 0.5 % slippage at 14:45, and 1 % on fills from 15:00
  (the exit is always 1 %). Plus `server/charges.py`.
- **Measure:** net % of the premium paid and net ₹ per trade.

## Grid (reported in full; the gate is judged on the primary cell)
- Entry: 14:30 · 14:45 · 15:00.
- Exit: 15:15 · 15:25.
- Target: none · +50 % · +100 % of the premium (checked on each minute's last traded closes).

## Gate (test window 2024-10-01 → 2025-09-30), all of
- Net mean per trade > 0, and still > 0 at 2× costs.
- t ≥ 2.
- Positive in each half: 2024-10 → 2025-03 and 2025-04 → 2025-09.
- The worst day is smaller (in ₹) than the average month's net profit.
- The neighbours (entry 14:30 and 15:00 with exit 15:25, and entry 14:45 with exit 15:15, no target) each net
  positive.
- At least 30 trades.

Also reported:
- by VIX band at entry, by weekday, and event vs other days;
- a Monte Carlo drawdown (10,000 reshuffles);
- the share of trades where the index moved more than the premium paid (break-even before costs).

**Holdout 2025-10-01 → latest**, once, only if the gate passes: net mean > 0 and Sharpe within 30 % of the test
window's.
