# Option-chain and OI behaviour (module `optionchain`, Agent 3)

Written 2026-11-05. Design: `reports/lld/optionchain.md` (written before the code). Code:
`scripts/optionchain_features.py` → `scripts/optionchain_discovery.py` → `scripts/optionchain_validation.py`
(shared definitions `scripts/optionchain_common.py`); tests `tests/test_optionchain.py` (9 pass,
`results/optionchain/tests_stdout.txt`). Every number below is in a CSV under `results/optionchain/`.
Independent work: no S1/S2/S3 material, no other agent's results, no sealed data. Raw bhavcopy read only for
2018-01 → 2024-06 (rows `TradDt <= 2024-06-30`).

## 1. What was asked and how
Does the end-of-day option chain and futures OI of session t (known at TCLOSE(t)) predict session t+1 — gap
direction and size, first-30-minute return, open-to-close, range, big move (max excursion ≥ 1 %), gap fill — over all
days, on the eve of a weekly expiry (NW), the eve of a monthly expiry (NM), and two sessions before an expiry (D2,
target = the expiry session t+2)? NIFTY and BANKNIFTY separately. Plus: does expiry settle toward max pain, and is
the expiry-day move larger or smaller than the ATM straddle implied?

- 24 signals (12 directional, 10 volatility; full list in the LLD). Each continuous signal is split into its top and
  bottom tercile, cut points from DISCOVERY rows of the same underlying and context (`thresholds.csv`).
- Each bucket's hit rate is compared with all rows of the same underlying / context / period (exact binomial,
  two-sided). Structural tests (max pain, straddle) and conditional straddle P&L tests join the same family.
- **Family size 1,647 tests** (`hypotheses.csv`), Benjamini-Hochberg at FDR 10 %. 548 tests have n < 30 (flagged).
- Frozen before any validation number: every test with BH q ≤ 0.10 and n ≥ 30 → **153 candidates**
  (`candidates_frozen.csv`). Validation run once (`validation.csv`); robustness on discovery + validation
  (`robustness.csv`, `robustness_summary.csv`). The robustness code had a sort-direction bug in the "drop best 1 %"
  check; it was fixed and re-run; the validation table was byte-identical between the two runs.

## 2. Data handling
| Issue | Handling | Evidence |
|---|---|---|
| `UndrlygPric` empty before 2024-07 (100 % of rows 2018-2024) | underlying = panel `px_close`; expiry settlement = official close | `bhavcopy_quality.csv` |
| Settle ≤ 0: NIFTY 7.1 % (2018), 6.5 % (2019), ≤ 1.2 % later; BANKNIFTY 4.2 / 3.8 % then < 0.6 % | never used as a price; OI / volume kept | `bhavcopy_quality.csv` |
| On expiry day the expiring options' `SttlmPric` is the index final settlement value (same on every strike); it is 0 on 2018-19 expiries | settlement = that value, else official close of the expiry day; the two agree exactly where both exist | `features_stdout.txt` |
| Untraded rows 45-89 % of option rows per year | OI-based features only; ATM straddle uses the panel's settle > 0 rule | `bhavcopy_quality.csv` |
| Strike sparsity | near-expiry strikes with OI inside ±5 % cover 99-100 % of the 50 / 100-point grid every year; ATM-zone features need ≥ 3 strikes each side | `bhavcopy_quality.csv` |
| No IV column | IV proxy = ATM straddle time value / 0.7979 / √(sessions to expiry) × √252 (annualised %) | LLD |
| No bid-ask history | none exists in the bhavcopy; every straddle cost here is a settle price, not a fill | DATA_AUDIT §6 |
| 1 of 294 NIFTY and 1 of 339 BANKNIFTY eve rows list a re-dated (ghost) expiry | settlement taken from the official close of t+1 | `features_stdout.txt` |

## 3. Results in short
- **Direction: nothing.** 893 directional tests (PCR OI / volume, PCR change, CE vs PE OI change, ATM-zone PCR and
  flow, monthly PCR, max-pain distance, wall skew, futures basis, futures and options build-up classes). Only 2 were
  BH-significant, both NIFTY all-days close-to-close (which includes the untradeable overnight gap): long build-up
  (60.4 % vs 54.1 %) and ATM-zone put-writing flow (60.6 % vs 54.1 %). Both failed validation (55.7 % vs 56.6 %;
  58.9 % vs 56.6 %, p 0.34). No directional signal for gap, open-to-close or first 30 minutes reached BH even in
  discovery, on any context.
- **Expiry eves: too few rows.** NM has 60 discovery rows per underlying (20 per tercile), so no monthly-eve test
  could be frozen. Expiry-context directional p-values (best p 0.02 at n 8-20) are what 893 tests produce by chance.
- **Range / big move: yes, but it is volatility clustering.** 154 of 640 volatility tests were BH-significant; 19
  of the 151 frozen volatility candidates passed validation. Every passer says "a volatile-looking chain → a wider
  next session": high IV proxy, walls far from spot, wide distance between walls, big max-pain distance, big
  straddle drop, option volume surge, IV rise. Many failed because the validation period (2023 → mid-2024) was calm:
  the share of sessions above the discovery median range fell from 50 % to 22-25 %, so fixed level thresholds put few
  validation rows in the "high" buckets (55 of 134 failures have validation n < 30).
- **Max pain: expiry does not settle toward it.** On weekly and monthly eves the close moved closer to max pain on
  18-24 % of expiries vs 24-27 % on all days; direction agreement 29-53 % vs 44-47 %. No test significant.
- **Straddle: the expiry-day move is smaller than implied.** A D-1 ATM straddle bought at settle and held to final
  settlement returned −0.07 (NIFTY weekly) to −0.14 (BANKNIFTY weekly) pct points of spot in discovery; median
  realised / implied 0.71-0.84; payoff beat cost on 36-38 % of expiries. The strongest version (BANKNIFTY D-2,
  −0.23 pp, q 0.045) failed validation (−0.03 pp, p 0.38).

## 4. Structural tests (discovery only; `hypotheses.csv` kind = structural, `structural_discovery.csv`)
Max pain, D-1 (NW / NM) and D-2. "Closer" = |max pain − settlement| < |max pain − close(t)|.
| UL | ctx | n | closer | base | p | agree (\|dist\| ≥ 0.25 %) | base | p |
|---|---|---|---|---|---|---|---|---|
| NIFTY | NW | 156 | 20.5 % | 26.6 % | 0.09 | 46.1 % (n 89) | 44.2 % | 0.75 |
| NIFTY | NM | 60 | 18.3 % | 26.6 % | 0.19 | 29.3 % (n 41) | 44.2 % | 0.06 |
| NIFTY | D2 | 215 | 19.1 % | 20.0 % | 0.80 | 48.6 % (n 140) | 44.7 % | 0.40 |
| BANKNIFTY | NW | 201 | 24.4 % | 23.7 % | 0.80 | 53.5 % (n 129) | 47.5 % | 0.19 |
| BANKNIFTY | NM | 60 | 18.3 % | 23.7 % | 0.37 | 34.1 % (n 41) | 47.5 % | 0.12 |
| BANKNIFTY | D2 | 260 | 20.4 % | 18.5 % | 0.42 | 51.4 % (n 185) | 47.7 % | 0.34 |

ATM straddle (settle on t) vs final settlement payoff, % of spot. Block-bootstrap 95 % CI of the mean difference.
| UL | ctx | n | cost | payoff | diff (CI) | p | payoff > cost | median ratio | max exc > cost | range > cost |
|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY | NW | 156 | 0.89 | 0.83 | −0.07 (−0.17, +0.05) | 0.30 | 35.9 % | 0.84 | 66 % | 76 % |
| NIFTY | NM | 60 | 0.84 | 0.87 | +0.03 (−0.11, +0.20) | 0.77 | 38.3 % | 0.81 | 72 % | 73 % |
| NIFTY | D2 | 215 | 1.27 | 1.18 | −0.09 (−0.21, +0.04) | 0.22 | 40.0 % | 0.81 | 39 % | 38 % |
| BANKNIFTY | NW | 201 | 1.19 | 1.05 | −0.14 (−0.26, −0.03) | 0.036 | 37.3 % | 0.75 | 64 % | 82 % |
| BANKNIFTY | NM | 60 | 1.17 | 1.09 | −0.07 (−0.30, +0.15) | 0.58 | 38.3 % | 0.71 | 78 % | 82 % |
| BANKNIFTY | D2 | 260 | 1.71 | 1.48 | −0.23 (−0.39, −0.08) | 0.004 | 36.5 % | 0.73 | 37 % | 50 % |
"max exc > cost" and "range > cost" use the expiry-day index excursion from close(t) and the day's range; they say
the index often travels further intraday than the straddle cost, which matters only to someone who can exit one leg
at the right minute (no option-minute data before 2024-08 to test that). Conditional straddle tests (96 tests: does a
signal pick the expiries where the straddle pays?) gave one BH hit, NIFTY NM high max-pain distance, n = 20, not
frozen (n < 30).

## 5. Candidates that passed validation (19 of 153; all volatility, label Passed-validation)
Rate = share of t+1 sessions with range above the discovery median of that context (range_big) or with max
excursion ≥ 1 % (big_move) or |gap| above the discovery median (gap_big). Thresholds are frozen discovery values.
| cand | UL | ctx | rule (TCLOSE t) | target | disc n: rate vs base | val n: rate vs base | val p (1-sided) |
|---|---|---|---|---|---|---|---|
| OC01 | BN | ALL | iv ≥ 22.65 | range_big | 411: 82.7 vs 50.0 | 12: 83.3 vs 22.5 | 1e-5 |
| OC02 | NIFTY | ALL | iv ≥ 15.66 | range_big | 411: 78.6 vs 50.0 | 17: 70.6 vs 25.0 | 1e-4 |
| OC04 | NIFTY | ALL | iv ≥ 15.66 | big_move | 411: 72.7 vs 45.9 | 17: 47.1 vs 21.2 | 0.015 |
| OC10 | BN | ALL | iv ≥ 22.65 | gap_big | 411: 72.5 vs 50.0 | 12: 75.0 vs 34.6 | 0.005 |
| OC08 | BN | ALL | wall_width ≥ 5.29 % | range_big | 410: 73.9 vs 49.9 | 111: 37.8 vs 22.5 | 2e-4 |
| OC17 | NIFTY | ALL | wall_width ≥ 6.04 % | range_big | 411: 69.3 vs 50.0 | 58: 43.1 vs 25.0 | 0.002 |
| OC25 | NIFTY | ALL | wall_width ≥ 6.04 % | big_move | 411: 61.8 vs 45.9 | 58: 34.5 vs 21.2 | 0.013 |
| OC11 | BN | ALL | wall_near ≥ 1.71 % | range_big | 410: 72.2 vs 49.9 | 79: 36.7 vs 22.5 | 0.003 |
| OC13 | NIFTY | ALL | wall_near ≥ 1.83 % | range_big | 411: 70.3 vs 50.0 | 63: 47.6 vs 25.0 | 9e-5 |
| OC21 | NIFTY | ALL | wall_near ≥ 1.83 % | big_move | 411: 63.5 vs 45.9 | 63: 38.1 vs 21.2 | 0.002 |
| OC39 | NIFTY | ALL | wall_near ≤ 0.75 % | range_big | 411: 37.2 vs 50.0 | 225: 18.2 vs 25.0 | 0.010 |
| OC24 | BN | ALL | \|maxpain dist\| ≥ 0.58 % | range_big | 411: 65.9 vs 50.0 | 39: 41.0 vs 22.5 | 0.007 |
| OC22 | BN | ALL | straddle chg ≤ −0.40 pp | big_move | 410: 82.7 vs 67.8 | 37: 62.2 vs 39.5 | 0.004 |
| OC43 | NIFTY | ALL | straddle chg ≤ −0.29 pp | range_big | 410: 62.7 vs 50.1 | 36: 47.2 vs 24.8 | 0.003 |
| OC59 | NIFTY | ALL | straddle chg ≤ −0.29 pp | big_move | 410: 57.1 vs 45.9 | 36: 47.2 vs 20.9 | 4e-4 |
| OC52 | NIFTY | ALL | vol_surge ≥ 1.16 | range_big | 386: 63.5 vs 51.5 | 99: 35.4 vs 25.0 | 0.014 |
| OC118 | BN | ALL | iv_chg ≥ +0.65 | range_big | 323: 58.5 vs 49.9 | 77: 35.1 vs 20.8 | 0.003 |
| OC94 | NIFTY | NW | wall_near ≥ 1.21 % | big_move | 52: 69.2 vs 45.5 | 10: 50.0 vs 21.7 | 0.045 |
| OC97 | BN | NW | wall_width ≥ 4.31 % | range_big | 67: 70.1 vs 49.8 | 21: 47.6 vs 28.3 | 0.047 |
wall_near = distance from close to the nearer of call wall / put wall; wall_width = call wall − put wall distance;
straddle chg = same-expiry ATM straddle % change from t−1; vol_surge = near-expiry option volume / median of the last
5 sessions with the same days-to-expiry. OC01, OC02, OC04, OC10 (val n 12-17), OC94 (10) and OC97 (21) pass on
n < 30 in validation: weak evidence.

Robustness (`robustness_summary.csv`): all 19 keep their sign in every year with n ≥ 10, in both weekday regimes
(BANKNIFTY Thursday → Wednesday weekly from 2023-09; NIFTY monthly-only 2018 / Thursday weekly), at 30 % and 40 %
tails, and after dropping the best 1 % of outcomes. Inside VIX terciles the IV-level rules lose most of their edge
(OC01: +11 pp in the high-VIX tercile, no rows in the low one) — they restate VIX. Wall distance, max-pain distance,
straddle drop and volume surge keep the sign in all three VIX terciles (e.g. OC13 +14 / +13 / +8 pp), so they carry
some information beyond VIX, but they were not tested against the IV proxy or days-to-expiry, which they also track.

## 6. Frozen candidates that failed validation (134; label Rejected)
| family | frozen | ids (see `candidates_frozen.csv`) | note |
|---|---|---|---|
| directional | 2 | OC139 (long build-up → cc up), OC148 (ATM-zone put flow → cc up) | validation effect −0.9 / +2.3 pp |
| straddle P&L | 1 | OC128 BN D-2 straddle | −0.23 pp → −0.03 pp |
| iv level | 32 | OC03 … OC126 | 14 with val n < 30; "iv lo" buckets hold most calm-period rows, so bucket ≈ base |
| top3 OI share | 23 | OC26 … OC151 | high concentration → smaller range in discovery; did not hold |
| wall width / near | 44 | OC15 … OC153 | mostly the "low" and expiry-context versions |
| straddle chg / iv chg / iv − hv | 21 | OC19 … OC152 | |
| vol surge, futures OI change, max-pain distance | 11 | OC70, OC87, OC99, OC130, OC112, OC122, OC38 … | same sign, too small in validation |
20 of the 134 had the wrong sign in validation.

## 7. What this means for buying options (no trade is recommended)
Every passer forecasts **size**, not direction, and size is what option prices already charge for. The one direct
price test (straddle held into expiry) shows the buyer losing on average in discovery. So a range forecast becomes a
buying edge only if the bought straddle's price did not already rise with it. That needs option prices at t+1 open,
which exist only from 2024-08 (final period, options_1m) — the coordinator's test. A trade idea to test there:
buy the ATM straddle at t+1 open when the TCLOSE(t) chain has walls far from spot or a volume surge and the IV
proxy is NOT already in its top tercile; exit by the max-up rule per days-to-expiry.

## 8. Findings
| id | finding | n (disc / val) | effect | CI / p | label |
|---|---|---|---|---|---|
| F1 | Chain PCR, OI flow, build-up, max-pain distance, wall skew, basis do not predict gap, open-to-close or first-30-min direction | 893 tests | best q 0.077 (cc only) | — | Rejected |
| F2 | NIFTY long build-up / ATM put-writing flow → next close-to-close up | 462, 411 / 140, 112 | +6.3, +6.5 pp → −0.9, +2.3 pp | val p 0.62, 0.34 | Rejected |
| F3 | Expiry does not settle toward max pain (weekly, monthly, D-2; both UL) | 60-260 per cell | closer 18-24 % vs 18-27 % base | all p ≥ 0.06 | Rejected |
| F4 | D-1 ATM straddle (settle) loses into expiry: realised move ≈ 0.71-0.84 × implied | 60-260 | −0.07 to −0.23 pp of spot | BN NW p 0.036, BN D2 q 0.045 | Observed (BN D2 Rejected in validation) |
| F5 | Wide walls / walls far from spot → wider next session, beyond VIX | 410-411 / 58-111 | +19 to +24 pp disc, +13 to +23 pp val | val p ≤ 0.013 | Passed-validation |
| F6 | High IV proxy → wider next session (restates VIX) | 411 / 12-17 | +22 to +33 pp | val p ≤ 0.015 (n < 30) | Passed-validation (weak) |
| F7 | Same-expiry straddle drop, option volume surge, IV rise, big max-pain distance → wider next session | 323-411 / 36-99 | +9 to +16 pp | val p ≤ 0.014 | Passed-validation |
| F8 | Expiry-eve range rules (OC94 NIFTY weekly, OC97 BN weekly) | 52, 67 / 10, 21 | +24, +20 pp | val p 0.045, 0.047 | Passed-validation (n < 30) |
| F9 | Monthly-eve questions | 60 disc rows / UL | — | 20 rows per tercile | Untestable at this power |
| F10 | SENSEX option-chain questions (no option history before 2024-09, no BSE bhavcopy) | 0 | — | — | Untestable before the final stage |

## What this does NOT show
- Not that any signal makes money: no option was priced at an executable time (no bid-ask, no option minutes
  before 2024-08; settle prices are not fills).
- Not that range signals add anything beyond the IV proxy or days-to-expiry: only VIX terciles were checked.
- Not anything about the final period (2024-07 →), BANKNIFTY after weeklies ended (2024-11-13), the 2025 Tuesday
  NIFTY regime, or SENSEX.
- Not that max pain or PCR "work" on other horizons or with intraday OI: only end-of-day bhavcopy, next-session and
  D-2 horizons were tested.
- Not Validated: Passed-validation candidates still await the coordinator's single final test.
