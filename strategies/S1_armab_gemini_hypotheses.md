# S1 Arm A and Arm B · three hypotheses from the Gemini handoff (pre-registration, 14 Nov 2026)

Numbers only. Nothing live changes. **Written BEFORE any number of these tests is computed.** Source: `Claude_Technical_Handoff.md` (Gemini deep research), items HYP-A-01, HYP-A-02 and
HYP-B-01 in the order the handoff gives. HYP-B-02 (early kill) is not in that execution order and is not run. HYP-C-01 (NIFTY regime filter for Arm B) is forward-only by the handoff's own
statement and is not run. **Arm A and Arm B are analysed separately; no result is pooled and no improvement for one is assumed for the other.**

## What the handoff says that I could check against the project's own files (before any test)
- "Morning spread averages 7.4 %": **that number is the results-day fade's, not Arm A's or Arm B's.** From the live ledger (13 Nov), the entry spread for the S1 call arms is: open entry (09:15 ask) mean 11.7 %, median 5.3 %,
  max 117 %, n 37; close entry (15:20) mean 2.3 %, median 2.0 %, max 10.6 %, n 34. The direction of the claim (a wider spread at the open) is supported; the figure is not.
- "IV crush / theta bleed explains the stops": not measured anywhere in the project; the observed facts are the stop fills (mean -63.7 % beyond the 50 % level) and a once-a-session check. The mechanism is a hypothesis, not a finding.
- The handoff's bibliography is generic and unverified; per `CLAUDE.md` an article or AI summary is never turned into a rule. These tests are justified only by the project's own evidence (baseline sections 3 and 4).
- Acceptance criterion 3 (out-of-sample on trades after the freeze): `stress_audit/FREEZE.json` does not cover Arm A or Arm B, so no such sample exists; every result below is in-sample.
- Criterion 4 (1 % slippage per side): the minute test already charges the category slippage of `scanner/backtest_s1_v4.py` (large 1 %, mid 2 %, small 3 % per side). It is kept unchanged for baseline and variants.

## Common design
- **Trades:** the Arm A (140) and Arm B (55) trades of `data/results/S1_armab_minutes_trades.csv`, variant LIVE-CLOSE (entry day +1 09:16 open + 1 tick; the S1 v7 `old_expiry` rules; exit once a session on the day's last candle close:
  50 % stop, 5 sessions without a new closing high, T-1; sale at the close minus a tick; real charges and the category slippage). Contracts and candles: `S1_v10_bandarmab2_*`. This is the baseline for every comparison.
- **Paired comparison:** each variant is compared with the baseline on the same signal; a trade enters a pair only if it is valid in both. Per arm: n, win %, mean, median, total Rs, and the paired difference (variant minus baseline) with a date-clustered t and the two half-years
  (entries before 1 Oct 2025 / from 1 Oct 2025).
- **Multiple testing:** three hypotheses per arm are one family; Holm over the three p-values (normal approximation of the clustered t), separately for Arm A and Arm B. Every variant run is a row in `docs/research/experiments.csv`.
- **Pass rule (fixed now), per arm and hypothesis:** the paired mean difference is > 0, its clustered t gives a Holm-adjusted two-sided p < 0.05, and the difference is > 0 in both half-years. A pass only means "improved over the baseline in-sample"; it does not make the variant profitable (its own mean is reported)
  and justifies at most a paper shadow tag. Anything else = no.
- **Caveats stated now:** 140 and 55 trades; the 2025-26 window has been seen; the backtest rules are the older v7 rules (10-session expiry rule, no quiet-day skip), not the live rules.

## HYP-A-01 · enter at 15:20 on day +1 instead of 09:16
- **Variant C20:** entry on day +1 at the day's volume-weighted average price up to 15:20 (typical price (high + low + close) / 3 weighted by candle volume, 09:15 to 15:20) + 1 tick (the live close entry is "today's ATP + 1 tick"). The same contract.
  Excluded if the price is below Rs 2 or one lot is outside Rs 600 to 8,000. Exits: the same rules, first evaluated on the entry day's last close (as the live code does right after the 15:20 buy), then every session.
- **Question:** does the later, tighter-spread entry improve the arm over the 09:16 entry on the same contracts?

## HYP-A-02 · minimum 2 sessions to expiry (live) versus 10 (the tested rules)
- **Variant D2:** the strike walk and expiry choice of the live rules: the current monthly if at least **2** sessions remain after day 0 (the baseline needs 10, else takes the next monthly), normal band Rs 600 to 8,000, at least 50 contracts on day +1 for every expiry.
  Picks are built with the S1 v7 engine (`near_expiry` switched on, near minimum changed from 3 to 2, near band and contract minimum set to the normal ones). Only signals whose pick differs between D2 and the baseline are paired (the near-expiry signals).
  Minute candles for the new contracts are fetched from Upstox (the `stock-options-probe` workflow); contracts without candles or a 09:16 trade are dropped and counted. Entry 09:16 open + 1 tick; the same exits.
- **Question:** are the near-dated picks better or worse than the next-month picks the baseline used for the same signals?

## HYP-B-01 · an underlying-stock stop in place of the 50 % option stop
- **Variant U:** no 50 % option stop. At each session's last candle, if the **underlying stock's** official close is below its **day-0 low**, sell the option at that candle's close minus a tick. The 5-session decay and T-1 rules are unchanged. Underlying closes and the day-0 low come from the daily stock files (`data/eod2`),
  used only to evaluate the underlying rule; the option prices are minute candles. Entry 09:16 as in the baseline.
- **Question:** does stopping on the stock instead of the option improve the arm? Also reported: the effect on the baseline's stopped trades alone (99 for Arm A, 33 for Arm B).

## Read-out and what is not done
Reported per arm and hypothesis: baseline and variant side by side (n, win %, mean, median, total Rs, profit factor, max drawdown), the paired difference, t, Holm-adjusted p, the halves, the verdict by the pass rule, and the usual caveats. Not done here: any combination of changes,
any parameter search around the three rules, any use of the live paper trades as a test.
