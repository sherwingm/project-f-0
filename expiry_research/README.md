# Expiry research (independent project)

Started 2026-11-04 at the user's request: an independent study of whether market behaviour in the sessions before an
options expiry is predictable early enough to trade. It is **not** built on S1 / S2 / S3 or any of their trades,
backtests or conclusions, and it changes nothing in the live system.

## Rules for this folder
- Everything lives under `expiry_research/`. Nothing outside it is written. Source data is read-only.
- No orders (real or paper), no deployment, no commits or pushes without the user's approval.
- No missing data is invented. A test the data cannot support is reported as **Untestable**.
- Every prediction has an explicit decision time; only information published by then is used (see `PREREGISTRATION.md`).
- The final out-of-sample period is opened once, by the coordinator, only for candidates that passed validation.
- An LLD (`reports/lld/<module>.md`) is written before each research module's code.

## Data (read-only, the index-data checkout `../fo-index-data/data/index`, env `INDEX_STORE`)
| Set | What | Span |
|---|---|---|
| `options_daily/{NIFTY,BANKNIFTY}` | NSE F&O bhavcopy: futures + options OHLC, settle, OI, OI change, volume | 2018-01 → 2026-10 |
| `index_close_daily.parquet` | NIFTY 50, NIFTY BANK, India VIX daily OHLC | 2018-01 → 2025-09 |
| `spot_1m/{NIFTY50,NIFTYBANK,SENSEX,INDIAVIX}` | 1-minute OHLC | 2021-10 → 2026-10 |
| `vix_daily.parquet` | India VIX daily | 2008 → 2026-10 |
| `options_1m/{NIFTY,SENSEX}/<expiry>/<day>.parquet` | option 1-minute prices | 2024-08/09 → 2026-10 |

Stock options: no history in the store, so stock-option questions are Untestable here.

## Layout
`data/` built datasets · `scripts/` reproducible code · `results/` CSVs · `reports/` the markdown reports and LLDs ·
`tests/` checks. Panels are read with `scripts/panel_io.py` (`load_panel`: discovery + validation only); the final
period is sealed in `data/sealed/` for the coordinator. Python: `../.venvs/fo/Scripts/python.exe` from the repo root, with
`INDEX_STORE=../fo-index-data/data/index`.

## Report index (start with the final report)
| # | Report | What it answers |
|---|---|---|
| 1 | `reports/FINAL_RESEARCH_REPORT.md` | the ten questions, strongest pattern, paper-test decision (**read first**) |
| 2 | `reports/DATA_AUDIT.md` | what data exists, gaps, defects |
| 3 | `reports/EXPIRY_CALENDAR_ANALYSIS.md` | verified expiry calendar (§1); behaviour by expiry type (§2) |
| 4 | `reports/GAP_TRANSITION_ANALYSIS.md` | gap transitions, reversals, gap fill (Agent 1) |
| 5 | `reports/PRE_EXPIRY_PATTERN_ANALYSIS.md` | D-5 → D+1 price path, candle features (Agent 2) |
| 6 | `reports/NEXT_SESSION_PREDICTION.md` | can the next session / expiry day be predicted (Agent 4) |
| 7 | `reports/OPTIONS_CHAIN_ANALYSIS.md` | PCR, OI, walls, max pain, straddle (Agent 3) |
| 8 | `reports/FEATURE_DISCOVERY.md` | rule search, frozen candidates (Agent 4) |
| 9 | `reports/MACHINE_LEARNING_ANALYSIS.md` | models vs baselines (Agent 4) |
| 10 | `reports/WALK_FORWARD_VALIDATION.md` | walk-forward and the single final out-of-sample test |
| 11 | `reports/TRADEABILITY_ANALYSIS.md` | NIFTY ATM straddle on real option minutes |
| – | `reports/BIAS_AND_VALIDITY.md`, `reports/PANEL.md` | bias checks, mining null (Agent 5a); the shared panel |

**Reporting default (the user, 2026-11-07):** results lead with max up after entry (share reaching +50 / +100 / +200 %, mean, median), then the booked result.
