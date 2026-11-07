# Final research report: options-expiry patterns (NIFTY, BANKNIFTY, SENSEX)

Written 2026-11-05 by the coordinator. It sums up every report in `reports/` and the module outputs in `results/`.
Each number below is in the file named next to it. Labels: **Observed** (seen, not tested), **Suggestive**
(discovery only), **Validated** (passed discovery, validation and the single final test), **Rejected**,
**Untestable**. Periods: discovery 2018-01 → 2022-12, validation 2023-01 → 2024-06, final 2024-07 → 2026-10
(`PREREGISTRATION.md`). Nothing was committed, pushed, deployed or ordered.

## 1. The answer in one paragraph
There is **no expiry pattern that tells the direction** of the next session or of the expiry day. About 36,600
discovery tests across five modules found nothing for gap direction, first 15 / 30 / 60 minutes, open-to-close or
gap fill that survived validation; a broad direction search finds no more hits than shuffled data does. The expiry
day itself is not a bigger or different day for the index. What *is* predictable is the **size** of the next
session's move, on any day, not just near expiry: after a sharp 5-day fall, a big down close, a wide or costly
option chain, a bigger move follows; after calm, high-PCR days the next low is shallower. 11 of 13 such size rules
held in the untouched final period (**Validated (size)**). But the option market already prices this. Buying the
NIFTY ATM straddle on the flagged days **lost money net of costs** in every bigger-move rule, every expiry choice,
exit and slippage level (`TRADEABILITY_ANALYSIS.md`). The one striking fact is intraday: on NIFTY expiry day the
same-day ATM straddle touched **+100 % at some minute on 21 % of days** (22 of 107; max up mean +53 %, median +27 %),
yet held to 15:15 it averaged −7.2 %. That is hindsight, not a strategy. **There is not enough evidence to start
paper trading any strategy.**

## 2. The ten questions

**Q1. Is there a repeatable pattern in the sessions approaching expiry?** — **Rejected.**
Discovery: expiry-day range vs ordinary days +0.02 % (NIFTY, n 216, p 0.83), −0.07 % (BANKNIFTY, n 261, p 0.50);
big-move rate 46.8 % [40.2-53.4] vs 45.9 % base. 14 expiry-context controls and 4 gap-module candidates were frozen;
0 passed validation (they were Monday / weekend or 2018 effects). Final period: expiry-day gap-up and up-close rates
equal other days (p 0.055-0.70). (`EXPIRY_CALENDAR_ANALYSIS.md` §2, `BIAS_AND_VALIDITY.md` §6, `WALK_FORWARD_VALIDATION.md`)

**Q2. Does a gap up or gap down tell anything about the next session?** — **Rejected.**
NIFTY gap up → next gap down 24.7 % [21.7-27.9] (n 733) vs 24.3 % base, p 0.83. Large gaps neither continue nor
reverse (continuation after |gap| ≥ 0.5 %: 45-50 % vs 47-49 % base). Reversal does not rise toward expiry (trend p 0.52 / 0.78). The one
discovery dependence (BANKNIFTY, χ² p 0.008) vanished in validation (p 0.19) and final (p 0.83).
(`GAP_TRANSITION_ANALYSIS.md`, `results/final/observed_gap_transition_final.csv`)

**Q3. Can we see an expiry-day gap or directional move one day ahead?** — **Rejected** (direction);
**Validated (size)** for the size of the move.
Walk-forward logistic, NIFTY expiry-day gap up at TCLOSE: AUC 0.482 [0.407-0.558], n 235; no direction target at
any cutoff (D-2, TCLOSE, 15:15) passed the pre-set rule. 73 frozen direction rules: 0 passed. 893 option-chain
direction tests: 2 BH hits, both failed validation. In the final period NIFTY expiry days gapped up 41.0 %
[32.7-49.9] (n 122) vs 42.9 % on all days. (`NEXT_SESSION_PREDICTION.md`, `OPTIONS_CHAIN_ANALYSIS.md`)

**Q4. Which previous-day and option-market features are most informative?** — **Validated (size only).**
All are volatility-level features: ATM straddle % per √(days to expiry), VIX, ATR14, 5-day momentum (a fall),
the day's close-to-close drop, distance below the 20-day high, distance between the call and put OI walls.
For direction, none: PCR, max pain, OI change, build-up, basis all failed. Expiry does not settle toward max pain
(closer on 18-24 % of expiries vs 18-27 % base, all p ≥ 0.06). (`FEATURE_DISCOVERY.md`, `OPTIONS_CHAIN_ANALYSIS.md` §4)

**Q5. Which combinations give the strongest relationship?** — **Validated (size)**, modest.
NIFTY PCR(OI) > 1.006 **and** a calm market (straddle/√dte ≤ 0.6675, M218; or ATR14 ≤ 1.231 %, M220) → next
session's low is shallower: final −0.32 % [−0.40, −0.24] (n 138) and −0.33 % [−0.41, −0.25] (n 126) vs −0.48 %
base, p ≤ 0.0003. Pairs did not beat single volatility features in general; for big moves a VIX-only model equals
the full model (0 of 24 rows significantly better). (`FEATURE_DISCOVERY.md`, `MACHINE_LEARNING_ANALYSIS.md`)

**Q6. Does it survive unseen data?** — **Validated (size)** for 11 of 13; nothing directional reached the test.
Final test (one run, fixed gate, BH over 13): 11 Validated (size), 2 Rejected (PPC129 p 0.066; OC08 effect below half
of discovery). 9 of 11 also add to a VIX-only model; PPC062 and OC118 do not. OC13 and OC21 are one rule.
(`WALK_FORWARD_VALIDATION.md` "Final out-of-sample", `results/final/final_results.csv`)

**Q7. Does it work across expiry cycles and instruments?** — Size: **Validated** on NIFTY and BANKNIFTY, on all
days (not an expiry effect); weekly vs monthly expiry: no difference (**Observed**). SENSEX: only Observed in the
final period (calendar starts 2024-10). Stock options: **Untestable** (no data). The rules held through NIFTY's move
to Tuesday expiries and the end of BANKNIFTY weeklies (flags spread over 18-28 months).
(`results/final/extras_summary.csv`, `EXPIRY_CALENDAR_ANALYSIS.md`)

**Q8. Can it be turned into a realistic option trade?** — **Rejected.**
Long NIFTY ATM straddle, 09:16 entry, real option minutes, charges and 0.5 % slippage: every day −4.6 % mean
(n 503, t −2.5); UP5 flagged −4.0 % (n 305) vs unflagged −5.4 %, p 0.35; M143 −9.5 % (n 63). The plan's pass rule
holds in 2 of 162 flagged cells, both M220 with an overnight hold (+0.8 %, t 0.18; +0.7 %, t 0.20), negative at 1 %
slippage and against the rule's own logic. (`TRADEABILITY_ANALYSIS.md`)

**Q9. What is the simplest strategy that captures the behaviour?** — **None with positive expectancy.**
The simplest true statement is: "after a sharp 5-day fall, or when the ATM straddle per √day is high, expect a
≥ 1 % move next session". It is right more often than the base rate, but the straddle price has already risen for
it. The expiry-day straddle swing (+53 % mean max up) has no tested exit rule; the +20 % target won 63 % [53-72] of
days but averaged −8.1 % (−8.5 % with a next-minute fill). (**Observed**)

**Q10. Is there enough evidence to begin paper testing?** — **No.** See section 7.

## 3. Strongest candidate pattern
**For direction: none exists.** No direction rule passed validation, so none was taken to the final test.

**Strongest size pattern: "a sharp 5-day fall comes before a bigger next session"** (PPC032 NIFTY, PPC098 BANKNIFTY;
PPC092 is the one-day version). Chosen because it holds in both indices, all three periods, from the open, and
beyond VIX.

| Item | NIFTY (PPC032) | BANKNIFTY (PPC098) |
|---|---|---|
| Condition at close of t | f_mom5 = close(t)/close(t−5) − 1 ≤ −1.383 % | f_mom5 ≤ −2.116 % |
| Signal available | after the official close of t (TCLOSE) | same |
| Earliest entry | t+1 open (09:15-09:16) | same |
| Predicts | t+1 moves ≥ 1 % from close(t) at some point | same |
| Discovery | 71.4 % vs 45.9 % (n 245) | 84.5 % vs 67.8 % (n 245) |
| Validation | 40.0 % vs 21.4 % (n 45) | 61.4 % vs 39.7 % (n 44) |
| Final | 46.2 % [37.4-55.2] vs 31.0 % (n 117), p 0.0004 | 77.8 % [66.9-85.8] vs 39.7 % (n 72), p < 1e-4 |
| From t+1 open (tradeable part) | +10.9 pp, p 0.004 | +21.8 pp, p 0.0001 |
| Beyond VIX (residual) | +0.11, p 0.008 | +0.26, p < 1e-4 |
| Circular-shift p | 0.0005 | 0.0005 |

Uncertainty: the rate moves 2-3 times between regimes (base 46 % → 21 % → 31 % for NIFTY), so the rule only says
"more than today's normal". It says nothing about direction. Trading limits: for NIFTY the straddle on PPC032 days
lost −10.1 % (n 105, t −2.7); BANKNIFTY has no option minutes, so PPC098 could not be priced at all.

## 4. What was tested
| Module | Discovery tests | BH hits (10 %) | Frozen | Passed validation | To final | Validated |
|---|---|---|---|---|---|---|
| gaps (Agent 1) | 239 | 4 | 4 | 0 | 0 | 0 |
| pricepath (Agent 2) | 1,899 | 154 | 170 | 23 | 5 | 4 |
| optionchain (Agent 3) | 1,647 | 156 | 153 | 19 | 5 | 4 |
| model (Agent 4) | 28,518 | 3,336 | 241 | 9 | 3 | 3 |
| bias (Agent 5a) | 4,275 | 615* | 14 | 0 | 0 | 0 |
| ML walk-forward | 792 + 96 VIX | 103 + 4 | – | – | – | – |
\* whole bias log of 5,400, mostly volatility, regime and AUC checks. Totals: about 36,600 discovery tests, 582 frozen
candidates, 51 passed validation, 13 sent to the final test, 11 Validated (size). All 13 and all 11 are size rules.

Mining-null yardstick (`BIAS_AND_VALIDITY.md` §2): a 200-rule search on discovery, re-run on 200 week-shuffled
copies. Direction targets: 31 (NIFTY) and 16 (BANKNIFTY) hits at p < 0.05 vs a chance 95th percentile of 46 / 45, and
0 BH hits (chance also 0). Volatility targets: 204 hits vs chance 70. Chance best edge: 22-27 pp for rules with
30-59 rows, 9-14 pp for 120-249 rows. So direction "hits" were what noise gives; size hits were real.

## 5. Disagreements and how they were resolved
| Issue | Who said what | Resolution |
|---|---|---|
| Option-chain size rules | Module: 19 passed. Reviewer: only OC13, OC118 "hold"; OC08, OC17, OC21 "weaker" (z 1.75-2.10 beyond VIX); 5 refuted | All five went to the final test. Why: the reviewer's summary to the coordinator said "holds" for all five, while its own `verdicts.csv` says "weaker" for OC08, OC17 and OC21. The coordinator used the summary when writing FINAL_TEST_PLAN.md. This inconsistency in the reviewer's output is stated here, not hidden. Final: OC08 Rejected, OC17 / OC21 Validated |
| NIFTY monthly D-3 weakness (PPC009) | Module: passed validation (n 18) | Reviewer: refuted, rests on 2020-03-23 (without it p 0.15). Not sent to the final |
| Model's 9 passes | Module: 9 of 241 passed | Reviewer: 9 is what chance gives in the 188-test validation family (9.4 expected; BH 4, Bonferroni 0). The final test decided: M143, M218, M220 held |
| Weekend / Monday confound | Discovery D-3 "more big moves", BANKNIFTY D-1 "smaller gap" | D-3 is Monday, D-1 was Wednesday (no weekend). Both failed validation once BANKNIFTY's expiry moved. Rejected |
| Volatility restatement | Size rules "predict big days" | VIX-only model equals the full model (ML); IV-level OC rules lose their edge inside VIX terciles. Final: 9 of 11 add beyond VIX; PPC062, OC118 do not |
| Expiry vs weekday (BANKNIFTY) | Thursday-era expiry days looked quieter (pricepath) | After the move to Wednesday the expiry day was not quieter; bias hints the effect follows the expiry, n < 40. Observed only |
| Gap-up base rate | Discovery 59.8 % NIFTY | Final 42.9 % (p < 1e-4), on all day types. Close definition explains ≤ 2.2 pp (bias §5). No expiry base rate carries over |
| Tradeability wording (final review) | Report said "every rule loses" | 2 M220 cells meet the plan rule; wording, CSV and limits fixed, sensitivity added (next-minute fill, tick floor): no conclusion changes |

## 6. Data limits and Untestable items
| Item | Status | Why |
|---|---|---|
| Stock options | Untestable | no stock-option history in the store |
| Market breadth, sectors, global markets, FII / DII, news | Untestable | none stored |
| Bid / ask, depth | Untestable as a backtest | only nifty_1s (3 days) and chain_eod (9 days); slippage is assumed 0.5-2 % |
| SENSEX expiries | Observed only (final period) | calendar from 2024-10-04, no BSE bhavcopy, the 2024-10-25 expiry missing |
| BANKNIFTY option minutes | Untestable | none stored; PPC092 / PPC098 / OC118 cannot be priced |
| NIFTY option minutes | final period only | start with expiry 2024-10-03; 2024-07 to 09 unpriced; 2024-12-26 and 2026-10-27 folders partial |
| Minute index data | from 2021-10 | minute-era discovery has about 300 rows, 63 expiry days |
| Thin cells | Untestable at this power | monthly-eve option tests (60 rows), BANKNIFTY Wednesday-regime expiry cells (17-35) |
| Data defects | handled | VIX minute unit errors (455 days), settle ≤ 0 rows, re-dated expiries, duplicate option rows on 2026-10-19 |

## 7. Paper testing: **No**
No rule or trade has positive expected value after costs on real option prices. Paper-testing any of the 11 size
rules as a bought straddle would test something the final period already rejected.

If more forward data is wanted, the only defensible next step is a **new, pre-registered forward observation**, with
no orders and no money, of the NIFTY expiry-day same-day ATM straddle (entry 09:16 close, strike nearest the 09:15
open). Its exit rule must be written down **before** any new day is seen (the +100 % max-up figure is hindsight and
cannot pick it). Gate: at least 40 new expiry days; mean net > 0 at 1 % slippage with one-sided p < 0.05; and better
than the same straddle held to 15:15. Until it passes that, it is a hypothesis, not a strategy.

## 8. File index
| What | Where |
|---|---|
| Design, rules | `README.md`, `PREREGISTRATION.md`, `FINAL_TEST_PLAN.md`, `reports/lld/*.md` (one per module and review) |
| Data audit, calendar | `reports/DATA_AUDIT.md`, `reports/EXPIRY_CALENDAR_ANALYSIS.md`, `data/expiry_calendar.csv`, `data/sessions_*.csv` |
| Gaps (Agent 1) | `reports/GAP_TRANSITION_ANALYSIS.md`, `results/gaps/` |
| Price path (Agent 2) | `reports/PRE_EXPIRY_PATTERN_ANALYSIS.md`, `results/pricepath/` |
| Option chain (Agent 3) | `reports/OPTIONS_CHAIN_ANALYSIS.md`, `results/optionchain/` |
| Model (Agent 4) | `reports/NEXT_SESSION_PREDICTION.md`, `FEATURE_DISCOVERY.md`, `MACHINE_LEARNING_ANALYSIS.md`, `results/model/` (per-expiry `predictions_*.csv`) |
| Bias (Agent 5a) | `reports/BIAS_AND_VALIDITY.md`, `results/bias/` |
| Reviews | `results/review_gaps/`, `review_pricepath/`, `review_optionchain/`, `review_model/`, `review_final/` |
| Final test | `reports/WALK_FORWARD_VALIDATION.md`, `results/final/` (`final_results.csv`, `flags_*.csv`, `code_path_checks.csv`) |
| Tradeability | `reports/TRADEABILITY_ANALYSIS.md`, `results/tradeability/` (`trades.csv`, `summary_*.csv`, `sensitivity.csv`) |
| Panel | `reports/PANEL.md`, `scripts/build_panel.py`, `scripts/panel_io.py` |
| Code, tests | `scripts/*.py`, `tests/` (61 tests pass, 2026-11-05) |
