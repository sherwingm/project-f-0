# Statistical integrity audit of Agents 2, 3, 3b, 4 (Agent 5, 17 Nov 2026)

Read-only audit. All numbers below come from `audit_01..09_*.py` in this folder (outputs `audit_*.txt/csv`, `consolidated_tests.csv`, `consolidated_summary.csv`, input hashes in `hashes.txt`). Nothing outside this folder was written. Agent 1's inventory was read but not re-audited except where it bears on the others.

## Bottom line
- No look-ahead found in any predictor actually used. Date alignment is correct in agents 2, 3, 3b and 4 (strictly previous session, previous US session, pre-open Asian opens, GIFT 06:30 open).
- The Yahoo `local_offset_s` problem does NOT affect any series the agents used: 0 mis-dated rows (details in 1b).
- Headline tables reproduce exactly (direction, GIFT) or to one trade (VIX level, a boundary effect).
- After one consolidated Benjamini-Hochberg at 10 % per strategy (36 testable tests for G1-F), nothing survives for any strategy on the whole sample. G1-F has 4 nominal p < 0.05 against 1.8 expected (P about 0.10 if tests were independent). In the discovery period G1-F has NO nominal p < 0.05 at all (smallest 0.070).
- G1-F is too small to see anything but very large effects: sd of net % is 101, so two classes of 40 trades need a gap of 64 points (alpha 0.05) or 86 points (alpha 0.003) to be seen at 80 % power.
- One breach of the restrictions: Agent 1 opened two `nifty_1s` files (2026-11-02 and 2026-11-17) for metadata (section 7).

## 1. Look-ahead and alignment

### 1a. Per agent
- **Agent 2 (anatomy)**: pre-entry fields use `prev = ses[i-1]` (store calendar, includes the weekend special sessions); VIX at signal uses bars with timestamp <= signal minute (entry minus 1); gap uses the 09:15 open; opening-range fields use bars before 09:30 only and the signal-minute close. Post-entry fields (`post_*`, MFE, MAE, peak, stop recovery) are named and kept separate in the draft. Fine. Caveats: closes are the last minute bar (15:29) not the official close (median difference to Agent 3's ret20 0.04 points, 90th percentile 0.19, maximum 1.05); `vix_prev_close` from `lib.vix_daily` differs from the NSE file by a median 0.04 and by 2.07 on 2025-02-03 (the Saturday special session). The price paid (a significant "winner vs loser" field, p 0.018) is known at entry, so not look-ahead, but it is a mechanical function of the entry and not a market condition.
- **Agent 3 (regimes)**: boundaries from 2018-01-01 to 2024-09-30 only (1,669 NIFTY sessions, 1,649 VIX days); ret5/10/20 from the previous session (`searchsorted(day) - 1` on `eod2`, which includes the Saturday Budget sessions); VIX level and direction from the previous daily close; `vix_signal` and gap are the context-dataset values at the signal minute / 09:15. No look-ahead. Edge case: for G1 / G1-C trades on 2024-11-04 and 2025-10-23 and 2026-02-02 the "previous session" is a Muhurat evening or a weekend special session (the draft does not say so); none of these is a G1-F trade except 2025-02-03 (Saturday session, which is correct).
- **Agent 3b (GIFT)**: `open` of row D is the 06:30 session open: pre-entry. Settlement columns of the same row are not used. Two definitions exist and both are pre-entry: (i) primary `open / prev_settle` column, (ii) same-contract `open(D) / settlement(D-1, same contract)` (the literal Amendment 1 wording, built in the addendum). Asia gap uses open/previous close of the same Yahoo row.
- **Agent 4 (external)**: US, Brent, US VIX, DXY and 10-year use the last row dated strictly before the trade date, with the UTC date of the stamp; USD/INR uses the hourly Indian-session change of the previous session (daily bar rejected correctly); breadth, sector, FII/DII cash and participant OI are keyed to the previous session on a calendar that adds the two Budget weekend sessions (their data stay missing); GDELT is the previous UTC day with a trailing median that excludes that day; events are calendar items.

### 1b. Yahoo timestamps (quantified, `audit_01_yahoo_dates.txt`)
- `local_offset_s` is a single constant per file for all 18 daily files. Applying it would mis-date 1,487 of 2,237 rows for each of Brent, WTI, gold, ES, NQ (offset -5 h moves a 04:00 UTC stamp to the previous day), 1,793 of 2,700 for DXY, 1,103 of 2,250 for ASX 200.
- Agent 4 used the UTC date for US/commodity/VIX/10-year series and +1 h for USD/INR: correct, 0 mis-dated rows.
- Agent 3b and Agent 4 used `UTC + local_offset_s` for Nikkei and Hang Seng. For these two the stamps are 00:00 UTC (Nikkei, offset +9 h) and 01:30 UTC (Hang Seng, +8 h), so the local date equals the UTC date on all 2,176 and 2,184 rows: 0 mis-dated rows. The code is fragile (it would be wrong for any DST market) but the result is right.
- Stamps are bar OPEN stamps; both agents use the open of the trade-date row and the close of the previous row, as intended.

### 1c. Independent re-derivation (30 random G1-F trades, seed 5, from raw files, `audit_03_rederive.txt`)
| Feature | Agent | Matches | Notes |
|---|---|---|---|
| S&P previous US session return | 4 | 30/30 | exact |
| Nikkei opening gap | 3b and 4 | 28/28 defined (2 closed) | exact |
| Hang Seng opening gap | 3b and 4 | 25/25 defined | exact |
| GIFT open / prev_settle column | 3b | 29/29 | exact (1 trade has no GIFT row, 2025-01-01) |
| GIFT same-contract | 3b | 29/29 | exact |
| Breadth advance share, previous session | 4 | 29/29 | exact |
| Nifty Bank minus Nifty previous day | 4 | 29/29 | exact |
| FII cash net (limited window) | 4 | 9/9 defined | exact |
| FII index-futures long share (participant file) | 4 | 29/29 | exact |
| ret20 | 3 | 27/30 | the 3 differences (2025-02-03, 2025-02-27, 2026-02-13) are MY error: the NSE file lacks the Saturday/Sunday Budget sessions; Agent 3's `eod2` has them, so Agent 3 is right |
| ret20 | 2 | 6/30 within 0.01 point | Agent 2 uses last-minute closes; differences are small (median 0.04 points), except special-session dates |
| VIX previous close | 3 | 30/30 | exact |
| VIX previous close | 2 | 6/30 within 0.01 | differs by 0.02 to 0.33; 2.07 on 2025-02-03 |
| Opening gap (minute store) vs context | 2 and context | 29/30 | the one difference (2025-02-03) is again my calendar |

Cross-agent class agreement for G1-F (`audit_04_crossagent.txt`): US class A3 vs A4 151/151 where both exist; Asia class 3b vs A4 133/133 where both exist (A4 requires both markets, so 21 trades are missing; 3b averages whichever market is open, 19 G1-F trades use one market only). BUT class DEFINITIONS differ between agents with the same names: ret20 quintile class differs in 20 of 154 trades (Agent 2 boundaries come from 727 store days 2021-10..2024-09, Agent 3's from 2018..2024); VIX level class differs in 25 of 154 (Agent 2 classes the VIX at the signal minute against 12.57 / 18.24, Agent 3 the previous close against 13.51 / 19.94). VIX dir differs in 11. The coordinator must not mix Agent 2's and Agent 3's class tables.

### 1d. Other alignment issues
- **Agent 4 participant-OI terciles** (X08, X10, X12) are cut on session days 2024-10-01 to 2025-09-30, i.e. the discovery period, not on history before 2024-10 as the regime cuts are. No returns are used, but the cut drifts: for G1-C the "high FII futures" class has 37 trades in discovery and 0 in the second half (X08 is therefore partly a calendar split; see section 3).
- **FII / DII cash (H15)**: all 59 usable G1-F trades are after 2025-12-01, so there is no discovery test; the classes seen are diverge 44, both-buy 15, both-sell 0. Descriptive only, as the pre-registration says.
- **Agent 3 `us_cls`** (H6) takes the S&P value from the context dataset, whose cache ends 2026-09-25. For 20 trades it is NaN, and for two trades (2026-09-29, G1 and XP) it holds a stale value (+0.51 against the true -0.77). No G1-F trade is affected beyond 3 missing. Agent 4's S&P (X01) is complete and correct. H6 and X01 are the same hypothesis built twice.
- GIFT definition: Amendment 1 says "previous trade date's settlement". Agent 3b's PRIMARY run uses the `prev_settle` column, which Agent 1 showed is not the previous row's settlement (differs on 817 of 825 days; it already contains the US-hours move). The literal definition is the "same-contract" addendum. For G1-F the two give different classes for 38 of 152 trades (GIFT) and 63 of 152 (indicated vs actual). Both are pre-entry, but the coordinator must say which is the pre-registered one and cannot present the prev_settle run as the Amendment definition.

## 2. Reproduction of key G1-F tables (`audit_05_reproduce_tables.txt`)
My own labels (ret20 from `eod2`, edges 2018-01-01..2024-09-30; VIX from the NSE index file; GIFT from the raw bhavcopy) and my own statistics from `context_dataset.csv`:
- **Direction (ret20 quintiles)**: all five rows identical to Agent 3 (n 36 / 39 / 60 / 13 / 6; means +18.80, +5.24, +16.92, +18.11, +149.22; medians -3.24, -31.95, -32.63, -51.22, +112.60; Rs 56,384 / 34,290 / 63,606 / 13,639 / 79,127). Kruskal-Wallis p 0.5106, same as Agent 3. Quintile assignment identical for all 154 trades.
- **VIX level (previous close)**: Agent 3: low 108, normal 46 (mean +11.82 / +38.05). Mine: low 109, normal 45 (+11.44 / +39.57). The one trade is 2026-01-29 (VIX 13.53): Agent 3's p25 is 13.51 (from `vix_daily.parquet`), mine 13.54 (from the NSE file). A boundary effect of 0.03 VIX points moves one trade; KW p 0.0204 (Agent 3) vs 0.0183 (mine). Not an error, but shows how fragile a class edge is.
- **GIFT (both definitions)**: identical to Agent 3b in all six rows (n, mean, median, Rs). prev_settle column: gap-down 8 (+52.0), flat 134 (+20.1), gap-up 10 (+1.9), KW p 0.6095. Same-contract: gap-down 28 (+26.7), flat 111 (+19.4), gap-up 13 (+17.5), KW p 0.9472.
- Win counts: wins 63 under both net % > 0 and net Rs > 0 (0 disagreements, 0 zero-Rs trades in any of the four sets), so the different definitions used by the agents do not change any number here (section 5).

## 3. Multiple comparisons (`consolidated_tests.csv`, `consolidated_summary.csv`, `audit_07_discovery_bh.txt`)
Family: raw Kruskal-Wallis p (whole sample) of every main hypothesis from Agent 3 (H1-H9), Agent 3b (H10, H11, H12, C1, C2 for the prev_settle run, plus H10, H11, C1, C2 for the same-contract run; the repeated H12 is listed as duplicate), Agent 4 (H12-H15, X01-X15). Excluded and listed as robustness (agent-marked): A3 X1_dir3, R1_ret5, R2_ret10, R3_ma; A3b R1, R2 (both runs); A4 S01-S03. Agent 3's and Agent 4's overlapping hypotheses (US overnight H6 / X01, Asia H12 in 3b and 4) are counted twice, as asked.

| Strategy | Tests (testable) | Expected p<0.05 by chance | Observed p<0.05 | Observed p<0.10 | Smallest p | Smallest BH q | BH survivors (10 %) |
|---|---|---|---|---|---|---|---|
| G1-F | 37 (36) | 1.8 | 4 | 6 | 0.0203 | 0.367 | none |
| G1 | 37 (36) | 1.8 | 1 | 2 | 0.0343 | 0.929 | none |
| G1-C | 37 (36) | 1.8 | 3 | 4 | 0.0028 | 0.101 | none (X08 FII-futures level, q 0.1008, just misses) |
| XP | 37 (32) | 1.6 | 1 | 1 | 0.0105 | 0.338 | none (A3 H3 would pass in a family of 9) |

- G1-F nominal hits: A3b C2 VIX x GIFT 0.0203, A3 H2 VIX level 0.0204, A3 H9 VIX x gap 0.0388, A4 X02 USD/INR 0.0416. Next: same-contract H11 0.077, H15 0.082, X08 0.103. P(at least 4 of 36 at p<0.05 under independence) = 0.10: unremarkable. Agent 3's own statement "H2 fails BH (first threshold 0.011)" is correct for its family of 9 and remains true (q 0.37) in the family of 37.
- Robustness items for G1-F: ret5 quintile 0.0149 (R1_ret5), prev-row indicated-vs-actual 0.0315 (R2). They are outside the family but, if counted, raise the nominal hits to 6 of 38 with no change to BH.
- Discovery-only p-values (31 testable G1-F tests): none below 0.05 (smallest 0.070, A4 X02); expected 1.6. Second half (31 tests): 2 below 0.05 (smallest 0.033, same-contract H11), no BH survivor.
- G1-C and XP: in discovery, A4 X08 (G1-C, p 0.00047, q 0.017) and A3 H3 (XP, p 0.00016, q 0.005) survive BH. XP H3 reverses in the second half (Agent 3 reports it). G1-C X08 cannot be checked in the second half: the "high" class has 0 trades there (the tercile cut is from 2024-10..2025-09), so it is a calendar split in disguise (high FII long share: 37 trades, all in the first period, mean -37 %).
- The Agent 3 / Agent 4 within-family "q" values are not comparable with the above (Agent 4's own q uses 19 tests, Agent 3's 9).

**Dependence (cells that are not independent)**
- G1-F is a strict subset of G1: all 154 G1-F trades are G1 trades with identical net % (154 of 154). G1 tests contain G1-F evidence; do not count G1 and G1-F as independent confirmations.
- G1 and G1-C share 0 dates, but XP shares 61 dates with G1 (38 with G1-F) and 45 with G1-C: same market days, same underlying moves, correlated outcomes.
- Within G1-F: H7, H8, H9, C1, C2 contain H2, H5, H10 classes (a combination test is not independent of its components; H9 and H2 are the same signal, as Agent 3 says); the indicated-vs-actual class equals actual gap minus GIFT return, so H5, H10 and H11 are mechanically linked; H6 / X01 / H13 (US, Asia, risk-on) overlap; VIX level, FII-futures level, DII level and USD/INR classes are all strongly period-dependent (e.g. VIX normal: 38 of 75 discovery trades, 8 of 79 later), so many "regime" tests are partly the same early-versus-late split.
- Every test is on the same 154 trades; the effective number of independent tests is below 36, so BH is somewhat conservative here, but the trade count and variance (section 4) make the conclusion unchanged.

## 4. Sample size and power (`audit_08_power_concentration.txt`)
G1-F: n 154, mean +19.66 %, median -18.24 %, sd 101.36 % (skew 1.74), SE of the mean 8.17, 95 % CI of the mean 3.6 to 35.7. Discovery n 75: mean +25.2, sd 103.6; second half n 79: mean +14.4, sd 99.6. Net Rs per trade: sd 7,715, mean 1,604.

Smallest detectable difference in mean net % between two classes of equal size (two-sided, 80 % power, whole-sample sd, normal approximation):
| n per cell | alpha 0.05 | alpha 0.003 |
|---|---|---|
| 10 | 127 points | 173 points |
| 20 | 90 | 122 |
| 40 | 64 | 86 |
| 80 | 45 | 61 |
Class versus the rest (class 10 / 20 / 40 / 80 of 154): 93 / 68 / 52 / 46 points at alpha 0.05 and 126 / 93 / 71 / 62 at 0.003. The mean of a single class must exceed 31 % (n 40) or 63 % (n 10) to differ from zero.
Could never have been seen: any class difference below roughly 45 points (the whole-strategy mean is 20), any effect on a class under 10 trades (high VIX has none, gap-up none, sudden VIX expansion 2, bullish direction 19, strongest quintile 6, GIFT gap classes 8 to 13), and any effect inside the second half alone (79 trades, e.g. VIX normal has only 8). The KW test on skewed returns has different power from this mean-based calculation, but the order of magnitude is the same: the result is dominated by a handful of large winners.

## 5. Concentration and selection (`audit_08_concentration.csv`)
- Whole G1-F: top 1 trade Rs 44,422 (18 % of Rs 247,046), top 3 Rs 91,666 (37 %), top 8 Rs 190,146 (77 %). Mean net % without the top 3 is +14.1, without the top 8 +5.8 (Rs 56,900).
- Notable classes (mean net % -> mean without that class's top 3 trades by Rs):
  - bullish direction (n 19) +59.5 -> +14.6; the top 3 are 85 % of the class rupees. Strongest quintile (n 6): +149, all 6 winners, top 3 carry most of it.
  - VIX normal (n 46) +38.1 -> +21.3 (median 7.4); top 3 = 50 % of class rupees; low VIX +11.8. Mann-Whitney low vs normal p 0.020, Welch p 0.140. Without the overall top 8 trades, normal +16.7 vs low +1.3 and KW p 0.039. So the VIX-normal advantage is partly but not entirely concentration.
  - ret5 middle quintile (n 41, robustness) +55.0 -> +38.0: the most concentration-robust positive cell.
  - same-contract indicated-vs-actual "stronger" (n 24) +53.5 -> +18.0; "weaker" (n 26) +39.5 -> +9.1 (top 3 = 90 %); prev_settle "stronger" (n 23) +32.8 -> +1.1 (top 3 = 85 %).
  - USD/INR up (n 24) +46.1 -> +23.3; down (n 15) +36.3 -> -23.5 with median -51: noise.
  - FII options level low (n 15) +61.2 -> 0.0 (top 3 = 130 % of class rupees: without them the class loses money). FII futures high (n 24) +45.2 -> +4.1.
  - GIFT classes: prev_settle gap-down (n 8) +52 is too small; same-contract gap-down (n 28) +26.7 is not different from flat +19.4.
- Win definition: Agent 2 wins = net % > 0 (losses <= 0); Agents 3 and 3b wins = net Rs > 0 (losses = net Rs <= 0); Agent 4 wins = net Rs > 0 (losses = net Rs < 0, zero trades are neither). In these data no trade has net Rs = 0 and net % and net Rs have the same sign for all 755 rows, so the counts coincide (G1-F 63 wins). Inconsistent in code, harmless in numbers; the final report should state one definition.
- "Top 5 % share" is defined differently: Agent 3 and 3b divide by total net Rs (so shares above 100 % occur, e.g. 134 %, 1,023 %), Agent 4 divides by gross profit, Agent 2 reports top-8 / top-N shares of total net Rs. Not comparable across files.

## 6. Predictive validation (`audit_09_predictive.txt`)
Chronology: discovery = entries to 2025-09-30 (G1-F 75 trades), second half = 79 trades. The second half has been seen descriptively before, so it is a consistency check, not a clean holdout. No random train/test split exists anywhere (grep of all scripts: random numbers are used only for bootstrap resampling of trading days, seeds 20261117 and 11). No threshold was tuned on returns: ret quintiles, VIX p25/p75, gap +/-0.3, GIFT +/-0.3, IvsA +/-0.2, breadth p25/p75, US +/-0.3 are fixed from history or in the pre-registration. Agent 4's "best and worst class in discovery" rule is a fixed procedure on discovery only.

Smallest-p G1-F hypotheses, class versus rest, mean difference in points (discovery / second half / half-year signs):
- **H2 VIX normal vs low (p 0.020)**: discovery +5 points only (normal 27.9 vs rest 22.5, Mann-Whitney p 0.48); second half +80 (n 8 vs 71, p 0.008). The whole-sample gap comes from 8 later trades; half-year: 2024H2 -80 (reverses), 2025H1 and later cells too small. Six of the 8 later normal-VIX trades are winners (Rs 0.7k to 22.8k); only one is in the overall top 8. Verdict: not predictive evidence; period and VIX are confounded (normal VIX = Oct 2024 to mid 2025).
- **H9 normal VIX and flat gap (p 0.039)**: +16 discovery, +73 second half (n 7); 2024H2 -77, 2025H1 +62. Same signal as H2, no independent support.
- **C2 VIX x GIFT (p 0.020, prev_settle col)**: the small p comes from cells with 1 to 8 trades each (e.g. normal / gap-down 4 trades +104, normal / flat second half 7 trades +98). Not testable in the second half for most cells.
- **X02 USD/INR up (p 0.042)**: same sign, discovery +54 (n 11), second half +19 (n 13); half-year only one testable cell (+82). Weak same-sign persistence, small n, concentration (top 3 = 62 % of class Rs).
- **H11 indicated-vs-actual, "in line" vs rest (same-contract p 0.077; prev-row variant, agent-marked robustness, 0.031)**: same sign in both periods (-41 and -34 points; Mann-Whitney 0.31 and 0.045) and in 4 of 5 half-years (-82, -56, +4, -93, -15). The only G1-F pattern with same-sign persistence; but it is not significant after correction, the prev_settle-column version does NOT persist (-28 then +5), and the contrast "in line vs rest" lumps stronger and weaker.
- **H15 FII/DII diverge** (p 0.082): second period only, so untestable chronologically.
- **ret5 middle quintile (robustness, p 0.015)**: +61 discovery, +44 second half, all 4 testable half-years positive: persistent in sign, but non-monotonic across quintiles (agent 2 notes the same) and outside the family.
- **H1 direction (p 0.51)**: bullish +31 discovery, +65 second half (n 12 and 7).
- Agent 3's consistency flags (4 same sign, 4 reversed of 8 contrasts) and Agent 3b's same-contract flags (3 same, 4 reversed, 2 untestable) match my reading: coin-flip consistency.

## 7. Restriction compliance
- Existing files modified: none. `git status` shows no tracked change; the untracked set equals the start-of-session set plus the `interim/` folders. Files newer than the pre-registration outside `interim/` are the coordinator's own manifest / quality files and `data/events.sqlite-shm` / `-wal` (git-ignored side files created when Agent 1 opened `events.sqlite` with `mode=ro`; the database file itself is unchanged, mtime 14 Nov).
- Network: no use of `requests`, `urllib`, `socket`, `http`, `ssh`, `subprocess` in any agent script (grep).
- Sealed / holdout data: no reference to `expiry_research/data/sealed`, `FREEZE.json` or holdout files in any agent script.
- **BREACH (minor)**: Agent 1's `inventory_checks.py` (lines 163-167) reads `nifty_1s/2026-11-17.parquet` and `nifty_1s/2026-11-02.parquet` with `pd.read_parquet` and prints counts, kinds and time spans (output in `checks_output.txt` lines 129-131). These files lie in the prospective window (1-second NIFTY data from 2 Nov 2026; the freeze is 13 Nov 17:48 IST). Only metadata (row counts, instrument kinds, first and last timestamp) was produced; no return, price or trade statistic was computed or used, and Agent 1 itself says "do not use". The older `agent1_data_inventory` run listed file names only. The coordinator should disclose this in the final report.
- Agents 2, 3, 3b, 4 trade data end 2026-10-23 (entries), minute and option data used by Agent 2 end by 2026-10-28; the GIFT, NSE-index, breadth and Yahoo files include dates to 2026-11-17 (approved downloads); Agent 3b prints GIFT-return percentiles and correlations over all GIFT days (to 2026-11-17) as descriptive data checks, not against any trade.
- Agent 2 imports project modules (`lib`, `scanner.s3_engine`) which read the options minute store for the recorded contracts only; no live ledger or VM access.

## 8. Corrections the coordinator should apply (most important first)
1. State the GIFT definition explicitly. The literal Amendment 1 definition is the same-contract one (open of D over previous trade date's settlement of the same contract). Agent 3b's primary run used the `prev_settle` column, which Agent 1 showed measures only the leftover move after the US session. Report the same-contract results as primary (H10 p 0.95, H11 p 0.077 for G1-F), the other as robustness, and count both in the correction.
2. Report the correction over the enlarged family (G1-F: 36 testable tests, none survives, smallest q 0.37), not Agent 3's 9-test "BH" or Agent 4's per-agent q. State expected versus observed nominal hits (1.8 vs 4) and that in discovery there are 0 of 31.
3. Do not present H2 (VIX normal vs low) as a lead without saying that discovery shows only +5 points, the gap arises from 8 later trades (+86 mean), 2024H2 reverses, and VIX level is confounded with calendar period. Same for H9, C2, X02.
4. Use one set of class definitions. Agent 2's quintile and VIX classes (store history, signal-minute VIX) differ from Agent 3's (2018 history, previous close) for 20 and 25 of 154 G1-F trades. The final report should use Agent 3's pre-registered ones and label Agent 2's tables as descriptive with their own cuts.
5. Disclose the nifty_1s read by Agent 1 (metadata only) as a breach of the "do not touch the prospective window" rule.
6. Fix or flag known data issues: Agent 3 H6 uses a stale context S&P value for 20 NaN plus 2 wrong rows (use Agent 4 X01, which is complete and verified 30/30); Agent 4 requires both Asian markets (133 of 154) while Agent 3b averages available ones (152): pick the Amendment's "average of Nikkei and Hang Seng" and say which; Agent 4's participant terciles use the discovery window, so the G1-C X08 "high" class has zero second-half trades and cannot be checked.
7. Report concentration next to every positive class: bullish +59.5 becomes +14.6 without its top 3; VIX normal +38.1 becomes +21.3; FII-options low +61.2 becomes 0.0. Whole strategy: top 8 trades = 77 % of rupees, mean +5.8 % without them.
8. State the power limit in the report: for 154 trades (sd 101), class differences below about 45 to 65 points cannot be detected in cells of 40 to 80 trades; classes under 10 trades (high VIX, gap-up, expansion, strongest quintile) carry no conclusion; "no evidence" is not "no effect".
9. Harmonise win and concentration definitions (one win rule; top-5 % share relative to net total or to gross profit, not both) and note the undated-STT disclosure for the Rs figures.
10. Minor: mention that Agent 3's VIX class edge (13.51) puts 2026-01-29 (VIX 13.53) in "normal" while the NSE-file edge (13.54) would put it in "low"; one trade, but it shows that VIX-level class results depend on single trades. Also note the Muhurat / weekend special "previous session" convention for G1 and G1-C (3 trades).
