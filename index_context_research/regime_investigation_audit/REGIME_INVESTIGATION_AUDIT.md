# Independent audit of the Index Context Regime Investigation (commit 1380e8d08)

Auditor: separate session, 18 Nov 2026. Method: nothing taken from the summaries; each claim re-computed from the raw files (`data/eod2/nifty 50.csv`, `vix_daily.parquet`, `external_data/*`, `results/context_dataset.csv`, agents' CSVs). Scripts and raw outputs are in this folder: `scripts/a01_integrity.py`, `a02_recompute.py`, `a03_features_mc.py`, `a04_claims.py` and the matching `a0*_*.txt`. The agents' scripts were **not** re-run end to end (see U1).

## Verdict: PASS WITH WARNINGS (PARTIAL PASS), score 84 / 100
No error that changes a conclusion was found. The headline ("no pre-entry condition explains G1-F's periods; nothing survives correction; top 8 trades = 77 % of rupees") reproduces. Marks are lost for definition inconsistencies the report does not disclose, a few over-precise or loosely derived statements, and a missing end-to-end reproduction.

## Findings by area
**1. Deliverables and datasets**
- PASS: trade sets G1 259 / G1-F 154 / G1-C 235 / XP 107 match `context_dataset.csv`; G1-F is a strict subset of G1; no duplicate days; labels vs context dataset net % differ by at most 0.0000 in all four sets.
- PASS: manifest 25 files, all hashes match, 0 problems.
- WARNING: raw agent folders include superseded results (documented as superseded).

**2. Agent merge**
- PASS: anatomy join has 154 / 259 / 235 rows, no missing MAE or MFE.
- PASS: Asia (133 trades), FII cash (59), US VIX (145) re-derived exactly; breadth differs only in units (percent vs fraction).

**3. Strategy mapping (G1F → G1-F etc.)**
- PASS: the final map is correct and class counts equal the agents' (G1-F bearish 75, bullish 19). The earlier wrong-name bug was fixed before the deliverables.

**4. MAE joined by date**
- PASS: join on date and strategy, one row per trade, counts equal, no duplicates.
- WARNING: MAE is the lowest option minute close (not intraminute; carried prices up to 30 min), already disclosed.

**5. Data accuracy, look-ahead, leakage**
- PASS: GIFT same-contract recomputed from the raw bhavcopy: max difference 1e-16, same 2 missing, classes 111 flat / 28 down / 13 up. Uses only the 06:30 open and the prior settlement (known before entry).
- PASS: VIX level classes 100 % agree; ret20 3-way classes 99.35 % agree; five-way 98 %.
- WARNING (W1, undisclosed): the opening gap comes from two sources. The study dataset gap (minute store) differs from the NSE daily open (`eod2`) by up to 0.19 points for G1-F, 36 trades by more than 0.05; 9 G1-F trades change class at ±0.3 % (G1 25, G1-C 10, XP 6). Effect on G1-F's gap p-value is small (flat 133 of 154) but the indicated-vs-actual lead (gap minus GIFT, ±0.2) is the most exposed to this.
- WARNING (W2, undisclosed): the ret20 quintile edges are not what a strict 2018 to 2024-09 recomputation gives (mine -1.93 / +0.48 / +2.47 / +4.71 vs -1.88 / +0.52 / +2.57 / +4.71). 1 to 3 trades change class; the direction KW p is 0.57 mine vs 0.51 theirs. Conclusion unchanged.
- PASS: no future information found in any predictor used.

**6. Statistics**
- PASS: Benjamini-Hochberg recomputed from `consolidated_tests.csv`: G1-F 36 tests, 4 nominal < 0.05 (1.8 expected), min q 0.367, no survivor; G1 min q 0.929; G1-C min p 0.0028, q 0.101; XP min q 0.338; P(X ≥ 4 | 36 at 0.05) = 0.104.
- PASS: G1-C bullish vs bearish Welch recomputed: whole p 0.0048, discovery 0.102, second half 0.0118 (as stated).
- PASS: XP VIX direction: discovery falling +83 % (n 14), KW p 0.00016; second half falling -11 % (n 16), KW p 0.66 (reversal as stated).
- WARNING (W3): the half-year differences quoted for G1-C bullish (-33.4 / -27.7, text "-33 / -28") are -32.3 / -29.3 in my recomputation from the label file (different cut or rounding; same sign, same size). Low impact.
- WARNING (W4): the correction family is approximate (dependence between tests, G1-F inside G1, both GIFT definitions counted). It is stated, and it is conservative on the count side, but the p-value dependence makes BH only indicative.
- WARNING (W5): G1-F direction in the second half alone has KW p 0.10 (bullish only 7 trades) and the agent file lists 0.0499 for a 3-group test on a different cut; the discovery count "0 of 31 below 0.05" is correct but the second-half 0.0499 is not mentioned. Not reported as a finding, so no harm, but undisclosed.

**7. Do the conclusions follow?**
- PASS: "no evidence found", "not evidence of no effect", power limit about 45 points, top-8 concentration 77.0 % (Rs 190,146), stops 64 (42 %), held trades 70 % wins.
- WARNING (W6): "11 of 13 fields are the same for winners and losers" is loosely derived (about 25 comparisons, two nominal). Prefer "no pre-entry field separated them after allowing for about 25 comparisons".
- WARNING (W7): `MARKET_REGIME_RESULTS.md:12` prints the raw mean (+149 %) of an n = 6 cell. It is labelled too few, but the number should not be shown.
- WARNING (W8): the lead lists (FINAL_FINDINGS "Interesting but unproven") are exploratory; the second half was already seen, and the claim "same sign in both years" is weak support. The wording is guarded, which is right.
- WARNING (W9): G1 puts "bearish -0.8 % vs bullish +22.6 %" is stated as "puts did not do better in bearish regimes"; all intervals include zero, so it is "no evidence they do", not "they do not".

**8. Missed or misread analyses**
- No intraday regime definition (trend vs range day, failed breakout) built; stated as not built.
- No test of regime effect on MFE (max up) as the primary outcome, though the user's standing rule asks for max up first; MFE is shown per class, not tested.
- No time-trend control (calendar) for the VIX and FII levels beyond a description.
- No ex-ante power calculation per hypothesis (a general one is given).

**9. Disclosures**
- PASS: GIFT definition changed after first results, second half already seen, two prospective-window recorder file reads, events.sqlite side effect, undated STT table, agents' definition differences.
- WARNING: W1 and W2 above are not disclosed.

**10. Reproducibility**
- PASS: inputs hashed, seeds fixed, scripts present, my independent recomputation matches the headline numbers.
- UNVERIFIED (U1): the agents' scripts were not re-run end to end here to avoid overwriting committed outputs. Raw git-ignored external data is re-fetchable only by running `fetch_external.py`; FII/DII third-party data was verified on one day only.
- UNVERIFIED (U2): USD/INR hourly alignment and Brent roll artefacts were not re-derived; Agent 5's check is relied on.

## Critical errors that invalidate findings
None.

## Overstated or loose statements
- W6 "11 of 13 fields"; W7 raw +149 % n = 6; W9 puts wording; the lead language should say "second half is not a validation".

## Missing analyses
MFE-based tests; calendar-controlled VIX/FII comparison; sensitivity of the gap classes to the gap source (W1); an end-to-end rerun.

## Corrections needed (files and lines)
- `MARKET_REGIME_RESULTS.md:12`: remove "its raw mean is +149 %".
- `FINAL_FINDINGS.md:9` ("11 of 13 fields"): reword as above.
- `STRATEGY_REGIME_COMPARISON.md:8` and `PREDICTIVE_VALIDATION.md:25`: half-year differences -32 / -29 (recomputed) instead of -33.4 / -27.7.
- `RESEARCH_LIMITATIONS.md`, "Definition issues": add the two opening-gap sources (W1) and the quintile-edge difference (W2).
- `PREDICTIVE_VALIDATION.md` section 2: mention the second-half 0.0499 file entry (W5).

## Reliable for future G1-F decisions?
Yes, for one use only: as evidence that no tested pre-entry market condition justifies a rule change or filter on G1-F (nothing survived and nothing replicated). No, as a basis for any filter built on the leads (in-line-with-GIFT, normal VIX, FII/DII, USD/INR, mid breadth): those are exploratory, small and period-confounded. The right next step is to track the pre-registered conditions on the live paper record, not to change the strategy.

## Score
Data and joins 22/25 (-3: gap source, quintile edges undisclosed); statistics 22/25 (-3: approximate family, small half-year mismatches); conclusions 17/20 (-3: three loose statements); disclosures 11/15 (-4: two missing, one unmentioned file value); reproducibility 12/15 (-3: no full rerun, two inputs unchecked). Total 84.
