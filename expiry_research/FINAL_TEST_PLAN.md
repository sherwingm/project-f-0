# Final out-of-sample test plan (written 2026-11-05, before the sealed period is opened)

## What reached this point
Five independent modules ran about 34,000 tests on discovery (2018–2022), froze their candidates, then ran
validation (2023–2024 H1) once. Independent reviewers recomputed every pass.
- **Direction** of the next session or the expiry day (gap direction, first 15/30/60 minutes, open-to-close, gap
  fill): **no candidate passed validation**, at any decision time. Nothing directional goes to the final test.
- **Size** (next-session range or a ≥ 1 % move): several candidates passed. Most only restate VIX (volatility
  clustering). The final test takes only those the reviewers judged **holds**.

## Candidates (exact rules and thresholds in the module's `candidates_frozen.csv`; not changed)
| Id | Index | Rule at TCLOSE(t) | Target on t+1 | Direction |
|---|---|---|---|---|
| PPC032 | NIFTY | f_mom5 ≤ −1.383 | max excursion ≥ 1 % (big_exc) | higher |
| PPC062 | NIFTY | f_streak_close ≥ 3 | big_exc | lower |
| PPC092 | BANKNIFTY | o_cc ≤ −0.9088 | big_exc | higher |
| PPC098 | BANKNIFTY | f_mom5 ≤ −2.116 | big_exc | higher |
| PPC129 | BANKNIFTY | f_fut_vol_r20 ≥ 1.211 | big_exc | higher |
| OC08 | BANKNIFTY | wall_width ≥ 5.2894 % | range > discovery median | higher |
| OC13 | NIFTY | wall_near ≥ 1.83441 % | range > discovery median | higher |
| OC17 | NIFTY | wall_width ≥ 6.03737 % | range > discovery median | higher |
| OC21 | NIFTY | wall_near ≥ 1.83441 % | big move (≥ 1 %) | higher |
| OC118 | BANKNIFTY | iv_chg ≥ 0.651378 | range > discovery median | higher |
| M143 | NIFTY | straddle % / √dte ≥ 0.7671 | big_exc | higher |
| M218 | NIFTY | PCR(OI) > 1.006 and straddle % / √dte ≤ 0.6675 | low of t+1 vs previous close (mean) | shallower |
| M220 | NIFTY | PCR(OI) > 1.006 and ATR14 % ≤ 1.231 | low of t+1 vs previous close (mean) | shallower |

Features in the final period are rebuilt with each module's own feature code, from data available at TCLOSE(t).
No threshold, window or definition is changed.

## Pass rule (fixed now)
1. Same sign as discovery, one-sided p < 0.05 against the final period's base rate (or mean), and an effect of at
   least half the discovery effect.
2. Benjamini–Hochberg at FDR 10 % across these 13 tests.
3. Reported but not part of the gate: (a) the gain over a VIX-only logistic model fitted on discovery+validation
   (does it add anything beyond VIX?); (b) the effect measured from the t+1 open, which a TCLOSE signal can actually
   trade, besides the gap-inclusive label.

A candidate that passes 1 and 2 is **Validated (size)**. One that fails is **Rejected**. There are no re-runs.

## Tradeability (NIFTY only; BANKNIFTY has no stored option minutes)
- **Trade:** buy the NIFTY ATM straddle (CE + PE, strike nearest the 09:15 open) at the close of the t+1 09:16 minute,
  for every final-period session that a Validated NIFTY size rule flags.
- **Expiries:** (a) the nearest expiry on or after t+1 (so it can be the expiry day itself), and (b) the nearest
  expiry after t+1.
- **Exits:** (i) 15:15 of t+1; (ii) the first minute the straddle is up 20 %, else 15:15; (iii) a hold to t+2 09:16.
- **Costs:** each leg pays 0.5 % slippage at entry and at exit (1 % before 09:30 or from 15:00), plus charges
  (brokerage, STT, exchange and SEBI fees, GST, stamp). There is no bid / ask history, so 1 % and 2 % slippage are
  also run.
- **Benchmarks:** the same straddle on every session, and on the sessions that are not flagged.
- **Reported:**
  - n, win rate, mean and median net % of premium, t, worst trade, and drawdown;
  - **max up** while held (mean, median, share ≥ +100 %), split by days to expiry;
  - results by expiry type (expiry day / D-1 / other) and by VIX tercile.
- A size signal is worth trading only if the flagged straddles beat the unflagged ones and are positive net of costs.
  The market already prices volatility, so a correct size forecast can still lose money.
