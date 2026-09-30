# Decisions

Standing decisions for this repository. Code, specs and prompts follow this file; changing a decision means
editing this file on purpose, in its own commit, with the reason.

## Scope
- **Stock F&O only.** No index derivatives (NIFTY, BANKNIFTY or any other index), ever, unless this file is
  changed on purpose. The universe loader already drops index rows (`scanner/universe.py`).

## Orders
- **Paper before real.** Real orders need a deliberate configuration change (`PAPER=false` plus a configured
  broker); nothing switches it implicitly. `PUBLIC_ACCESS=true` refuses real orders outright.
- **Position limits** (paper, and live when it comes; `server/config.py`):
  - a long-option position may cost at most **6 % of paper capital** in premium (₹30,000 on ₹5,00,000);
  - at most **3 open positions**;
  - **daily loss halt at 2 %** of capital (no new entries until the next session); the other defaults in guide 12
    are unchanged.
  - Backtests size a position inside a **₹10,000–30,000 budget band**.
- **`ALLOW_LOTTERY=false`.**
- **No buckets.** Paper trades are one group; no A/B/C/D or other tags on trades anywhere.
- **Long options only.** No option selling, no spreads, no futures positions: every trade is a bought CE or
  PE, with maximum loss = the premium paid. (Futures may appear in a diagnostic, never as a trade.)

## One strategy: S1, by version
There is one strategy, **S1**, iterated by pre-registered versions (S1 v1, v2, v3 …) until one clears the gate.
Ideas from elsewhere (for example a results-beat signal) enter only as components of a new S1 version.

Each version moves forward only through these steps, in order:
1. **Define** it on one page with no open parameters (`strategies/S1_vN_*.md`), committed before any run.
2. **Diagnostic** on the stock returns first, as the version's page specifies.
3. **Backtest on the test window only: 2021-01-01 to 2024-12-31**, with the engine's fills and expiry rule
   (`scanner/option_engine.py`) and the post-April-2026 charges (`server/charges.py`,
   `CHARGES_EFFECTIVE = 2026-04-01`).
4. **Gate** on the test window. Pass = all of:
   - net mean per trade > 0 after costs;
   - date-clustered t >= 2;
   - positive in each sub-period of the test window (2021-22 and 2023-24);
   - at least 200 trades.
5. **Holdout: 2025-01-01 to the latest session**, evaluated **once**, and only for a version that passed the gate
   on 2021-2024. It must be positive with date-clustered t >= 1.
6. **Paper** for at least 6 weeks or 30 trades, with fills and costs within 20 % of the backtest and no rule
   changes during the run.
7. **Live** only after 4, 5 and 6 pass, one lot.

A version that fails is **closed with its numbers**. The next version starts from the diagnostic, not from
re-tuning the same rules. Every report states the test-window / holdout split.

## S1 versions

| Version | Status | Record |
|---|---|---|
| S1 v1 · weak-sector naked put, 1-month-low exit | Superseded before running | Replaced by v2 before any v1 result was read |
| S1 v2 · weak-sector results-miss put debit spread (`strategies/S1_v2_weak_sector_put.md`) | **Closed** at the signal level | Results-miss signals in weak sectors, net of the leave-one-out sector: 10 sessions −0.34 %, t −0.7; 20 sessions −0.11 %, t −0.2; N 119. Option arms untradable on liquidity (0 trades); the technical arm had 17 trades, t 0.56 (`data/results/S1_v2_backtest_report.md`) |
| S1 v3 · strength score, one trade a day (`strategies/S1_v3_strength_score.md`) | **Closed** at the diagnostic stop | Selected stocks, signed, net of the leave-one-out sector, 2021-2024: 5 sessions −0.16 %, t −1.66; 20 sessions −0.46 %, t −2.34 (< 1.5: stop); N 1,923. Option backtest not run (`data/results/S1_v3_backtest_report.md`) |
| S1 v4 · results-beat continuation, long calls (`strategies/S1_v4_results_beat.md`) | **Closed**: failed the gate | Test window 2021-2024, 20-session exits: arm A 3 trades, mean −13.9 %, t −0.48; arm B 1 trade. Of 434 beats reaching entry, 320 (A) had an ATM call premium per lot above the ₹8,000 budget cap (median ₹25,000–37,000 per lot) and 110 traded < 50 contracts on day +1. Futures diagnostic (not a trade), 20 sessions net of 0.1 %: A +1.17 %, t 2.40, N 432 (2021-22 −1.24 %, 2023-24 +3.04 %); B +3.12 %, t 3.76, N 152 (`data/results/S1_v4_backtest_report.md`) |
| S1 v5 · results-beat continuation, long calls, ₹10,000–30,000 band (`strategies/S1_v5_results_beat.md`) | **Closed**: failed the gate (N) | Test window 2021-2024, 20-session exits. Arm A: 170 trades, mean −1.23 % of premium, t −0.13 (2021-22 −17.0 %, 2023-24 +6.3 %). Arm B (strong sector): 57 trades, mean +42.7 %, median −14.0 %, t 2.29, positive in both sub-periods (+42.2 %, +42.9 %), N 57 < 200. Of the beats reaching entry, 131 (A) had a one-lot premium above ₹30,000 and 110 traded < 50 contracts on day +1 (`data/results/S1_v5_backtest_report.md`) |

## Closed earlier ideas
Closed before the S1 structure; not reopened except as a component of an S1 version.

| Idea | Headline result |
|---|---|
| Buildup labels, long | +₹54 per lakh of alpha against ₹250 of costs |
| Shorting short-buildup | −₹487 per trade |
| Options under ₹2, 3–7 sessions to expiry | −26 % to −65 % of stake |
| EOD model | Brier 0.674 vs 0.667 for the base rate |
