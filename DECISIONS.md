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
  - Backtests size **one lot costing ₹600–8,000** (lot size × entry fill), from S1 v6 on (2026-10-12). Reason: at
    the at-the-money strike, v4's ₹2,000–8,000 budget left 3 trades and v5's ₹10,000–30,000 band left 57, short of
    the 200 the gate needs; v6 keeps lots cheap by walking up the strikes instead. S1 v5 and earlier used
    ₹10,000–30,000.
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
| S1 v6 · results-beat continuation, long calls, ₹600–8,000 per lot by walking up the strikes, decay exit (`strategies/S1_v6_results_beat_walk.md`) | **Closed**: failed the gate | Test window 2021-2024, primary variant (3-session decay, ≥ 50 contracts). Arm A: 234 trades, mean −19.0 % of premium, median −37.9 %, hit rate 9 %, t −2.32 (2021-22 −9.3 %, 2023-24 −23.2 %). Arm B: 75 trades, mean −3.7 %, t −0.17 (2021-22 +64.1 % on 17 trades, 2023-24 −23.5 %). The decay exit sold after 3.6 sessions on average (99 % of exits), long before the 20-session drift. Side reports: 5-session decay, arm B 74 trades, +37.5 %, t 1.27; arm A −12.3 %, t −1.10; ≥ 20 contracts changes little. Futures diagnostic (not a trade), 20 sessions net of 0.1 %: A +1.59 %, t 3.22, N 389; B +3.66 %, t 4.25, N 139 (`data/results/S1_v6_backtest_report.md`) |
| S1 v7 · results-beat continuation, long calls, near-expiry calls allowed (3-9 sessions left: ≥ 500 contracts, ₹600–3,000), 5-session decay + 50 % stop, T-1 (`strategies/S1_v7_results_beat_near_expiry.md`) | **Closed**: failed the gate | Test window 2021-2024 (looked at for v2-v6 and v6 what-ifs before v7 was written), primary variant. Arm A: 258 trades, mean −17.3 % of premium, median −58.1 %, hit rate 10 %, t −1.52 (2021-22 −10.5 %, 2023-24 −20.5 %). Arm B: 84 trades, mean +31.8 %, median −56.9 %, t 1.07 (2021-22 +124.6 % on 18 trades, 2023-24 +6.5 %), N 84 < 200. Near-expiry trades lost most: A 75 trades −37.3 %, B 19 trades −12.1 %; the 50 % stop closed 87–95 % of them, after 2.2 sessions on average. The stop closed 69 % (A) / 62 % (B) of all trades. Side reports: v6's expiry rule with the same exits, A −11.8 % (t −1.01), B +37.8 % (t 1.21, N 74); no stop, A −20.9 %, B +25.4 %; near-expiry at ≥ 50 contracts changes little. Futures diagnostic unchanged: A +1.59 %, t 3.22; B +3.66 %, t 4.25 (`data/results/S1_v7_backtest_report.md`, sheet `S1_v7_trade_sheet.xlsx`) |
| S1 v8 · calls on any result (beat or miss) in a strong sector, with the live paper rules (arms A, B) beside it, on recent data (`strategies/S1_v8_strong_sector_any_result.md`) | **Closed**: failed the gate; the live rules failed too | **Holdout used by the user's choice on 2026-10-14**: day 0 2025-04-01 → stock closes to 2026-09-25. Live rules (v7 old_expiry): arm S 168 trades, mean −27.6 % of premium, median −56.4 %, t −3.42 (2025 −43.2 %, 2026 −19.5 %); S_miss 94 trades, −37.8 %, t −4.91; arm A (all beats) 172 trades, −3.3 %, t −0.25 (2025 −46.3 %, 2026 +27.7 % from a few large winners, median −57.7 %); arm B 74 trades, −14.5 %, t −1.01. Futures diagnostic (not a trade), 20 sessions net of 0.1 %: S +0.37 %, t 0.68, N 227; A +0.19 %, t 0.35, N 243; B +0.09 %, t 0.13, N 107: the 2021-24 results-beat drift (A t 3.2, B t 4.2) did not persist. In 2021-24 the same code gives S +0.3 % (t 0.02), A −11.8 %, B +37.8 % (= v7). After this run the only unseen evidence is the live paper account from 2026-10-14 (`data/results/S1_v8_backtest_report.md`) |
| S2 step 1 · price + futures OI build-up, stock-level screen (`strategies/S2_oi_buildup_screen.md`) | **1 of 48 cells passes** → step 2 (option design) may be written for it | 2021-01-01 → 2026-09-25, enter at d+1's open, signed, net of 0.1 %. Pass: **short build-up** (price ≤ −3 %, combined futures OI ≥ +10 %, volume ≥ 1.5× its 20-day average), short for 5 sessions: N 965, mean +0.62 %, median +0.85 %, hit 59 %, t 3.17; years 2021 +1.10, 2022 +1.31, 2023 −0.79, 2024 +0.38, 2025 +0.98, 2026 +0.74; net of the sector +0.77 %, t 4.51. The whole short build-up family is positive (t 2-3.9) but below the bar elsewhere. Long build-up is consistently negative for a long (the stock falls after it; t −4 to −6 at 1-3 sessions) — not the pre-registered direction, recorded as a lead for a later screen. Short covering and long unwinding: nothing (`data/results/S2_screen_report.md`) |

## Closed earlier ideas
Closed before the S1 structure; not reopened except as a component of an S1 version.

| Idea | Headline result |
|---|---|
| Buildup labels, long | +₹54 per lakh of alpha against ₹250 of costs |
| Shorting short-buildup | −₹487 per trade |
| Options under ₹2, 3–7 sessions to expiry | −26 % to −65 % of stake |
| EOD model | Brier 0.674 vs 0.667 for the base rate |
