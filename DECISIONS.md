# Decisions

Standing decisions for this repository. Code, specs and prompts follow this file; changing a decision means
editing this file on purpose, in its own commit, with the reason.

## Scope
- **Stock F&O only.** No index derivatives (NIFTY, BANKNIFTY or any other index), ever, unless this file is
  changed on purpose. The universe loader already drops index rows (`scanner/universe.py`).

## Orders
- **Paper before real.** Real orders need a deliberate configuration change (`PAPER=false` plus a configured
  broker); nothing switches it implicitly. `PUBLIC_ACCESS=true` refuses real orders outright.
- **Risk defaults unchanged** (`server/config.py`, guide 12). **`ALLOW_LOTTERY=false`.**
- **No buckets.** Paper trades are one group; no A/B/C/D or other tags on trades anywhere.

## One strategy at a time: the strategy gate
A strategy moves forward only through these steps, in order:
1. **Define** it on one page with no open parameters.
2. **Backtest** 2021-01-01 to the latest session with the engine's fills and the post-April-2026 charges
   (`server/charges.py`, `CHARGES_EFFECTIVE = 2026-04-01`). Pass = all of:
   - net mean per trade > 0 after costs;
   - date-clustered t >= 2;
   - positive in each of 2021-22, 2023-24 and 2025-26;
   - at least 200 trades.
3. **Paper** for at least 6 weeks or 30 trades, with fills and costs within 20 % of the backtest and no rule
   changes during the run.
4. **Live** only after 2 and 3 pass, one lot.
5. **Combinations** only from strategies that passed individually, and then through the same gate.

## Closed strategies
Closed; not reopened without a new definition that goes through the gate.

| Strategy | Headline result |
|---|---|
| Buildup labels, long | +₹54 per lakh of alpha against ₹250 of costs |
| Shorting short-buildup | −₹487 per trade |
| Options under ₹2, 3–7 sessions to expiry | −26 % to −65 % of stake |
| EOD model | Brier 0.674 vs 0.667 for the base rate |
| S1 weak-sector results-miss put (v2 spread, S1-alt naked put, technical arm) | Closed at the signal level: results-miss signals in weak sectors show no drift net of the leave-one-out sector (10 sessions −0.34 %, t −0.7; 20 sessions −0.11 %, t −0.2; N 119); the option arms were untradable on liquidity (0 trades); the technical arm had 17 trades, t 0.56, one trade = the mean (`strategies/S1_weak_sector_put.md`, `data/results/S1_backtest_report.md`) |
