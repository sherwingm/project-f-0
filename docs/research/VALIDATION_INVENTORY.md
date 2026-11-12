# Validation inventory (2026-11-12)

What the project already checks, what it does not, and the known production differences. Nothing here changed production code; findings are
documented, not fixed. Evidence is a file path; "verified" means read in the source or run.

## Tests added on 2026-11-12 (new files only)
- `tests/test_validation_lookahead.py` (18 tests):
  - A: over 400 seeded random days and both acceptance modes (about 180 PE and 220 CE signals), the history signal (`scanner/s3_b2.signal`) is identical when the day is cut at the signal minute, unchanged when every later bar is replaced by garbage, and absent when cut one minute earlier.
  - B: the live traders use a minute only after it is over; the entry minute is signal + 1.
  - C: history and live agree on the signal minute and side on 12 seeded days for both `G1Trader` (puts) and `G1CTrader` (calls).
- `tests/test_validation_execution.py` (14 tests):
  - C: the engine fills at the entry minute's own close (+ slippage), uses the last fresh price (at most 3 minutes old) and never a later bar; live buys at the entry minute's last ask.
  - D: a sustained drop stops in both (prices within 0.6 %); `known_difference`: a one-minute dip stops live (per-second bid) but not in history (minute close).
  - E: empty chain, missing exit bar (last carried mark), missing leg, 13:00 / 13:01 boundary, half session, 15 % missing candles, no opening range, expiry strictly after today, no live quote at entry; `known_gap`: a partly missing opening range is accepted.
- Result of the run (2026-11-13): the 32 new tests pass; the whole suite passed (794 tests, 0 failed, 0 skipped, 201 s), including `tests/test_spec12_step7_model.py`.

## Existing checks (verified)
- Look-ahead (new tests above); independent leakage verification of the expiry panel: `expiry_research/results/verify/verify_leakage.py`.
- Date-clustered t-statistics: `scanner/stats.py`; gates with two halves and pre-registration: `DECISIONS.md` "S3 pods", `strategies/*.md`.
- Sealed final period: `expiry_research` (`data/sealed/`, `FINAL_TEST_PLAN.md`); chronological discovery / validation / confirmation in `g1_research/*_PREREG.md`.
- Walk-forward: `expiry_research/scripts/model_walkforward.py`; `scanner/model.py` (the verdict model's Brier score; weight 0 because it is no better than the base rate).
- Parameter sensitivity: neighbour cells in `scanner/s3_b2.py` and `scanner/s3_buy4.py`; stop / target sweeps in `scanner/fade_floor_sweep.py`, `scanner/fade_trail20_grid.py`.
- Execution realism: `scripts/s3_execution_audit_*.py`, `scanner/real_vs_paper_fills.py`; cost stress `cost_mult=2` in `scanner/s3_engine.py`.
- Multiple testing: permutation draws in `scanner/fade_diagnostics.py`; Benjamini-Hochberg and Bonferroni inside the `g1_research/` scripts.
- Survivorship for S1 stock options: each day's contracts come from that day's cached bhavcopy (`scanner/backtest_s1_v10.py`, line 135).

## Partial or missing
- **Walk-forward for strategies:** only for the expiry model; the S3 pods and G1 are judged on halves, not rolling windows. Missing.
- **Out-of-sample for G1 / G1-F:** every history number is in-sample (the filters were chosen on the same 2 years); the live paper trades are the only holdout. Partial.
- **Regime robustness:** ad hoc VIX / ADX cuts and halves; no standard per-strategy regime report. Partial.
- **Multiple-testing correction:** a Benjamini-Hochberg function is copy-pasted across `g1_research/` scripts; nothing in `scanner/` shares one. Missing as a shared helper.
- **Trial counting:** S1 went through versions v2 to v10 with no trial count; `docs/research/experiments.csv` starts counting from 2026-11-05 (back-filled). Partial.
- **Survivorship for `data/eod2/` (473 files) and `scanner/universe.py`:** the universe is the CURRENT F&O list fetched live; what eod2 covers was not verified. Unverified.
- **Reproducibility:** requirements are loose (`requirements.txt`: `pandas>=2.0`; only `yfinance` pinned), the venv lives outside the repo (`~/.venvs/fo`), data sits in a sibling repo via `INDEX_STORE`, and result files carry no commit hash (the registry now records it from 2026-11-12). Partial.
- **A property test for the S1 / S2 stock-option signals:** not written (only the index-option path was covered).

## Known production differences and gaps (documented, not changed)
1. **Stops:** history marks every minute on the CLOSE and exits at that minute's mark; live stops on any second's best bid and sells at it (`server/g1_live.py` `_manage_open`). Pinned by `known_difference_a_dip_inside_one_minute_stops_live_but_not_in_history`. A live stop can fire where history would not, and gaps through the stop fill below it (G1's first live trade: stop at 50 % filled at -73 %).
2. **Charges:** `server/charges.py` now versions the STT by trade date for the S3 engine (`STT_HISTORY`, `leg(..., on=date)`, 2026-11-13); everything else (brokerage, exchange charge Rs 35.53 vs 35.03 from 2024-10-01, SEBI fee, stamp, GST) is one table for all dates, and the S1 / S2 backtests and every other caller still pass no date. Effect on the G1 history: +Rs 861 on G1, +Rs 556 on G1-F, no verdict changes (`g1_research/CHARGES_DATED_RESULT.md`). The pre-2026 STT rows come from secondary sources.
3. **Slippage:** flat 0.5 % of premium (1 % for 2+ strikes from the money, 09:15-09:30 and from 15:00) in `scanner/s3_engine.py`; the history has trade prices but no bid / ask.
4. **Entry price age:** the engine accepts an entry price up to 3 minutes old (`ENTRY_STALE`); pinned by `test_c_engine_uses_the_last_fresh_price...`.
5. **Opening range:** a partly missing range is accepted (`known_gap_a_partly_missing_opening_range_is_accepted_as_is`).
6. **Expiry choice:** `scanner/s3_buy4.expiry_after` / `s3_p4.expiry_after` use the existence of a chain file that day (mild hindsight: a cancelled or moved expiry is known from files).
7. **Test status label:** `tests/test_spec12_step7_model.py` was long excluded as "known failing"; run alone on 2026-11-12 it passed 9 of 9 (the cause of the old exclusion was not investigated).
