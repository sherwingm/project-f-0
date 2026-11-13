# Changelog analysis (draft, 13 Nov 2026, not yet committed)

Classifies the important changes found in `DECISIONS.md`, `PROGRESS.md`, `HANDOFF*.md`, the stress audit and the commit log.
"Evidence" names a file, a test or a re-run. A commit message alone is **not** counted as evidence. See `PROJECT_JOURNAL.md` for dates and context.
Coverage limit: the commit log (715 commits) and `PROGRESS.md` were sampled, not read in full, so smaller changes are missing.

## A. Good changes (evidence of improvement)
1. **Always-on AWS VM instead of a sleeping server** (22 Oct). Evidence: the 16 Oct outage left eight fade trades unsold (`DECISIONS.md` S1 v10 row); no equivalent outage is recorded after the move. Not verified: uptime statistics.
2. **Live rule trades follow their written rules** (20 Oct: tick Rs 0.01, F&O ban for arms A / B). Evidence: DECISIONS entry names the mismatch and the fix; `tests/` cover rule paths. Caveat: the mismatch existed for a week of live paper trades.
3. **Paper buys wait for today's order book** (2 Nov). Evidence: three 29 / 30 Oct fills used yesterday's ask; 23 live trades were -3.5 % as booked vs -12.2 % on today's book; the probe check held back 3 old-book buys and delayed 0 of 14 normal ones; `tests/test_todays_book.py` has 12 tests.
4. **Spot store repair** (30 Oct, data commit `62a23257`). Evidence: Kotak's 09:15 open matched NSE on 35 % of sessions; the repaired open equals NSE's official open on 923 / 923; Budget sessions restored; all S3 buy pods re-run with the same code and **verdicts unchanged**.
5. **S3 independent review and fixes** (23 Oct, `32bd807c`). Evidence: wrong RBI date, lot-size bug (lot 25 instead of 75 on four weeklies), stray Saturday bar and faulty expiry calendar confirmed by a skeptic who reproduced each; all pods re-run; provenance (strategy-page commit in each report) added; the runner now refuses an uncommitted page.
6. **Rejected circular results** (7 Nov): the first holding-pattern run passed three tests circularly; they were discarded and a corrected target found nothing. Evidence: `g1_research/HOLD_PATTERN_RESULT.md`, `experiments.csv`.
7. **Daily-candle tests replaced by 1-minute tests** (10 Nov, user instruction). Evidence: arm A / B and the fade were re-run on minutes (`S1_armab_minutes.md`, `S1_fade_minutes_retest.md`); minute entries were on average 7.2 % dearer than the daily VWAP entry, so the daily results had been flattering.
8. **Marks saved every 30 s on open G1 positions** (10 Nov, `162dd2953`). Evidence: a restart on 10 Nov had reset a best bid; the ledger values were restored from the recorder file; `tests/test_g1_live.py` has a marks-saved test.
9. **Research infrastructure** (13 Nov): `CLAUDE.md`, `docs/research/` (trial registry with 17 rows to E-20261113-01, sources, validation inventory), skills `/deploy-vm` and `/research-loop`, agent `research-verifier`. Evidence: files in git; the validation inventory lists existing checks and gaps. Value for results: indirect.
10. **Validation tests** (13 Nov, 32 tests): look-ahead property over 400 seeded days, history-vs-live signal parity, entry timing, stop parity with named known differences. Evidence: documented run, whole suite 803 passed, 0 failed (quoted, not re-run here).
11. **Dated STT in the S3 engine** (13 Nov). Evidence: `tests/test_charges_dated.py` (9 tests); effect on G1 +Rs 861, G1-F +Rs 556, 0 trades flipped (`CHARGES_DATED_RESULT.md`). Secondary sources only for the old rates.
12. **Stress and reality audit** (13 Nov). Evidence: S1 baseline reproduced exactly, G1 simulator within Rs 0.00 of the engine on 259 trades, pre-registered scenarios all reported including negatives, run manifest with hashes.
13. **Honest reporting standard** ("max up first", "numbers only", disclosure of what was seen before each page). Evidence: present in strategy pages and amendments (e.g. Depth Amendment 1 disclosure).
14. **1-second recorders** (stocks earlier; NIFTY from 1 Nov). Evidence: recorder data exists from 2 Nov; value will show when stops and orders can be judged on real seconds (not yet used in a result).

## B. Bad changes or process failures (what went wrong, and whether corrected)
1. **v11 went live before its pre-registered 30-trade test** (20 / 21 Oct, user decision). Consequence: the pre-registered comparison had to be re-framed as shadows; v12 followed the next day. Not reversed; documented as a decision.
2. **v12's 2 % trail gap was chosen after seeing results** (21 Oct). The strategy page states it; the stress audit counts 71 exit variants on the same data. **Not corrected**; the live review at 30 trades is the only clean test and live v12 so far is below the backtest (58 trades, -5.7 %, descriptive).
3. **G1 went live on paper at the same time as it was pre-registered**, and was chosen as the best of seven in-sample variants (4 Nov). The page says "+8.4 % is flattered". Not corrected; the forward test is the only fresh evidence.
4. **G1-F's three filters were chosen from nine bucket tables on the same 154 trades** (4 Nov). Not corrected; stated in the audit as high overfitting risk.
5. **G1-C built although history said it loses** (12 Nov, at the user's request, documented). Its first live trade stopped at -50.75 %. Works as designed: paper only.
6. **Loss halts removed** (21 / 22 Oct, user decisions). A reasonable choice for paper but removes a control; the risk caps per trade and position counts remain.
7. **Spot store wrong 09:15 bar** went into the first round of S3 results (before 30 Oct). Corrected, results re-run, verdicts unchanged. The error existed from the data pipeline's start and was found by checking against NSE.
8. **S3 first-round errors** (23 Oct): the P1 page's "correction" to the RBI date was itself wrong (7 Aug instead of 6 Aug), skipping a Thursday expiry that was the worst day of P6 / P7. Corrected.
9. **The old-book fills** (29 / 30 Oct) were an entry-quality bug that biased the live record by roughly 3 to 9 points (-3.5 % vs -12.2 %). Fixed 2 Nov; the earlier trades remain in the ledger.
10. **Depth Amendment** (12 Nov): thresholds were chosen after the first run printed some rows; disclosed in the file header. Disclosed, not hidden.
11. **Process risk: several sessions edit one folder.** Merge conflicts in `PROGRESS.md`, a session resetting another's uncommitted edits (memory note), untracked files not ours. Mitigated by rules (stage own files), not eliminated.
12. **A 404 on `/api/near-tighty`** after NT routes were reorganised (now `/api/index/nt`); caused by another session's reorganisation, recorded in the index chat. No test caught it.

## C. Incomplete or unverified changes
1. **Later pushes not deployed.** The VM runs `1d46d134e` (12 Nov); docs, tests, dated STT, skills and handoff are on `main` but not deployed. They do not change live behaviour (the live code passes no date to `charges.leg`).
2. **Dated STT is only for the S3 engine.** S1 / S2 backtests and every other caller still charge the 2026 table on all dates. Effect on S1 +Rs 670 (informational); not versioned.
3. **Exchange charge Rs 35.53 vs 35.03 from 2024-10-01:** unconfirmed; NSE circular FA64232 was cited via a search summary and not opened.
4. **v12 live review at 30 trades.** The DECISIONS rows set the test; the result was not found in the files read. Status: **unverified**.
5. **The 09:16 vs 09:15 re-run at 30 fresh pairs** (pre-registered 30 Oct): the outcome was not found in the files read. Status: **unverified**.
6. **Walk-forward for the S3 pods and G1**, a **sealed holdout policy for G1**, a shared Benjamini-Hochberg helper, an environment lock, a property test for S1 / S2 signals: listed as missing in `VALIDATION_INVENTORY.md`; not started.
7. **Survivorship of `data/eod2/` and the universe** (current F&O list applied to past dates): unverified.
8. **Autoupdate server module** (`server/autoupdate.py`): untracked, deliberately not wired in.
9. **Shadow tracks** (np25, fd2, trail, t100, s20): started with review sizes; results not found in the files read.
10. **Shadow log of hold lengths on live G1 trades**, **SENSEX live paper:** proposed, not started.

## D. Regressions (worked before, stopped or degraded after a later change)
Evidence for causation is thin in each case; none is marked "confirmed".
1. **Live P&L versus backtest after v11 / v12 switches.** The fade's backtest edge appeared when the exit moved to a stop on minute data; the live paper record of v12 (58 closed trades) is below the backtest. Candidate cause: no slippage in the backtest, a first-minute fill that the live entry cannot match. Not proven.
2. **`/api/near-tighty` 404** after the NT routes were moved (see B12). Likely commit: the 10 Nov NT-on-`/index` change (DECISIONS 2026-11-10). Behaviour change, not necessarily a bug.
3. **A restart on 10 Nov reset an open G1 trade's best bid.** Cause: marks kept only in memory since the G1 live module was created (4 Nov). Fixed 10 Nov.
4. **Test exclusion label:** `tests/test_spec12_step7_model.py` was long excluded as "known failing"; run alone on 12 Nov it passed 9 of 9. The cause of the old exclusion was not found. Whether it ever really failed is unknown.
5. No regression was found in the signal logic of G1 / G1-C (history-vs-live parity tests pass).

## E. Unresolved weaknesses (still true on 13 Nov)
1. **No independent out-of-sample evidence for any traded rule.** S1 v12, G1, G1-F are judged on the data they were chosen on; the live paper account is the only holdout and it is small.
2. **No historical bid/ask.** Spreads are assumed (S3: 0.5 % / 1 % flat slippage; S1: none).
3. **S1 v12 backtest has no slippage term and fills at the first print of a very wide candle** (median 09:16 candle range 16.4 %).
4. **Intrabar order unknowable on 1-minute candles** (S1: 200 of 339 trades flip). The 1-second recorder could settle it for new trades; not yet used.
5. **Look-ahead in the S1 strike pick** (whole-day volume used, known only after the close). Documented; not removed from the backtest.
6. **Stops: history vs live** (minute close / candle low vs per-second bid); gaps through the stop fill below it.
7. **Trial counting for S1 v2 to v10 and the 71-variant exit grid:** none before 5 Nov 2026.
8. **Same data re-used:** the 2025-11-03 split in the fade studies is no longer untouched; the 2024-10 to 2026-10 index window has about 420+ looks.
9. **Short history:** 22 months of minute options, one regime (index rose about 9 % in late Oct / early Nov).
10. **Charges history from secondary sources;** S1 not date-versioned.
11. **Survivorship and universe construction** unverified.
12. **Reproducibility:** loose requirements (`pandas>=2.0`), venv outside the repo, data in a sibling repo, result files without commit hashes before 12 Nov.
13. **Operational:** data feed frozen 15:15 to 15:28 since 3 Aug 2026 (NSE); special sessions require a manual calendar entry; one VM, no failover.
