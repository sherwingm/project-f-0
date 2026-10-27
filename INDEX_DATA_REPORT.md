# Index data layer: what ran and what it stored

Plan: `INDEX_DATA_PLAN.md`. Code: `index_data/`, `server/index_api.py`, `server/index_pages.py`,
`.github/workflows/index-recorder.yml` (nightly) and `index-jobs.yml` (manual jobs). This report is updated as each
piece runs.

## Where the data lives
- **Large Parquet:** orphan branch **`index-data`** of `sherwingm/project-f-0` (never merged into `main`), under
  `data/index/`:
  - `options_1m/<underlying>/<expiry>/<date>.parquet` (source `kotak` | `upstox`)
  - `options_daily/<underlying>/<YYYY>.parquet`
  - `spot_1m/<name>/<YYYY-MM>.parquet`
  - `vix_daily.parquet`
  - `instruments/YYYYMMDD.parquet`
  - `chain_eod/YYYYMMDD.parquet`
  - `expiries.parquet`
- **Small JSON (committed to `main`):** `data/index/`
  - `status.json`
  - `coverage.json`
  - `expiries_next.json`
  - `probe_expired.json`
  - `reconcile.json`
  - `chain_latest.json`

  `render.yaml` ignores `data/index/**` and `index_data/**`, so these commits never redeploy the live server. The
  `/index` page reads them from GitHub's raw URL.

## Runs

| Piece | Run | What it stored | Rows / files | Range | Calls / runtime | Notes |
|---|---|---|---|---|---|---|
| §1 instruments + §3 recorder | first run, manual, session 2026-10-16 (run 39144565929) | 1-min options, contract snapshot, EOD chain | **712 contracts; 2,306,906 rows** (NIFTY 922,908; SENSEX 735,424; BANKNIFTY 648,574); 712 chain rows | each contract from its listing date (≤ 120 days) to 2026-10-16 | 1,348 calls, 44 min | Kotak answers GitHub's runners. Expiry check: nse_fo 9,261 / bse_fo 3,275 contracts, **0 mismatches**; SENSEX26O22 → 2026-10-22 (the BSE offset bug is fixed). 41 failures: 40 empty-candle SENSEX contracts (a bug, fixed) and 1 dropped connection (now retried) |
| §3 recorder re-run | session 2026-10-16 (run 39148299710) | the 41 missing contracts | 712 contracts | — | 736 calls, 21 min | **0 failures**. A normal night: ~712 calls, ~18-21 min |
| §4 spot / VIX backfill | Action run 39150059647 | `spot_1m/<name>/<YYYY-MM>.parquet`, `vix_daily.parquet` | NIFTY50 461,682; NIFTYBANK 461,613; SENSEX 459,981; INDIAVIX 462,121 one-minute rows; VIX daily 4,563 rows (yfinance) | 1-min **2021-10-20 → 2026-10-16** (61 months each); VIX daily 2008-03-03 → 2026-10-16 | 471 calls, 17 min | See the VIX sections below |
| §5 daily OHLC (PC) | 2021-01-01 → 2026-10-16 | `options_daily/<underlying>/<YYYY>.parquet` | **8,002,227 rows** (IDO + IDF); 1,425 sessions; 82 weekday holidays; 0 errors; 114 MB | 2021-01-01 → 2026-10-16; NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY, NIFTYNXT50 (+ NIFTYFPI) | 1,507 file downloads, 106 min | Full open / high / low / close / settle / OI / turnover. UndrlygPric and NewBrdLotQty are null before the 2024-07-05 UDiFF switch. Pushed to `index-data` on 2026-10-19 (commit fb18422) |
| §6 expiry calendar | local 2026-10-18, then Action run 39151451108 | `expiries.parquet`, `expiries_next.json` | NIFTY 334, BANKNIFTY 252, FINNIFTY 240, MIDCPNIFTY 188, NIFTYNXT50 35, SENSEX (from the scrip master) | 2021-01-07 → 2031 | — | `nearest_expiry("NIFTY","2023-07-05")` = 2023-07-06; `("NIFTY","2026-10-14")` = 2026-10-19 (the week's Tuesday moved to Monday for the 20-Oct holiday). Next SENSEX: 22 Oct, 29 Oct, 5 Nov |
| §9 Upstox expired backfill, NIFTY part 1 | Action run 39151549409 (2026-10-18 17:52 → 23:25 UTC) | expired NIFTY options, 1-min with OI, source `upstox` | **4,448 contracts; 31,486,660 rows** | expiries **2024-10-03 → 2025-08-14** (107 listed in all, 2024-10-03 → 2026-10-13) | 10,882 calls, 5.5 h | Stopped at its 320-minute budget as designed (restart-safe). Full NIFTY estimate ~24,400 calls. No `UDAPI1149`: the free Analytics Token works |
| §9 Upstox expired backfill, NIFTY part 2 | Action run 39194783874 (2026-10-19 03:27 → 08:30 UTC) | expired NIFTY options, 1-min with OI | **4,026 more contracts**; 32,302,488 rows in the run | continues after part 1 (4,448 contracts skipped as done) | 9,966 calls, 5.0 h | Stopped at its time budget again: about 8,500 of ~24,400 estimated calls remain → **part 3 needed** (after SENSEX, outside market hours) |
| §9 Upstox expired backfill, NIFTY part 3 | Action run 39327471145 (2026-10-19 21:26 → 22:50 UTC) | expired NIFTY options | 2,020 contracts; 17,326,692 rows | **NIFTY complete**: all 107 expiries 2024-10-03 → 2026-10-13 | 5,307 calls, 1.4 h | **NIFTY in all: 10,494 contracts, ~81.1 M one-minute rows** |
| §9 Upstox expired backfill, SENSEX part 2 | Action run 39337787123 (2026-10-19 22:51 → 2026-10-20 03:59 UTC) | expired SENSEX options | 7,039 contracts; 18,840,538 rows | resumed after part 1 (3,395 contracts done) | 17,322 calls, 5.1 h | Stopped at its time budget; part 3 runs on 20 Oct (an NSE holiday) after the 19 Oct recorder re-run |
| §3 recorder, 19 Oct session | scheduled run 39313223207 **started 02:40 IST on 20 Oct** (GitHub's cron ~6.7 h late) | — | **0 contracts**: it recorded 20 Oct (an NSE holiday), not 19 Oct | — | — | The S1-trades step also crashed (`itertuples` renames the `dStrikePrice;` column). Both fixed in 6ff3289: a start before 08:00 IST records the previous evening's session; the column is renamed first. Re-run for 19 Oct: run 39367758327. The 19-Oct NIFTY weekly expired that day, so it may be missing from today's scrip master; Upstox's expired data covers it |
| §9 Upstox expired backfill, SENSEX part 3 | Action run 39372515324 (2026-10-20 05:00 → 10:03 UTC) | expired SENSEX options | 4,022 contracts; 12,520,131 rows | — | 10,102 calls, 5.1 h (the daytime cap: the code does not know NSE holidays) | Stopped at its time budget; the queue's scheduler then failed (see PROGRESS 2026-10-20 evening) |
| §9 Upstox expired backfill, SENSEX part 4 | Action run 39433699241 (2026-10-20 13:49 → 15:27 UTC) | expired SENSEX options | 2,450 contracts; 7,877,739 rows | **SENSEX complete**: all 106 expiries 2024-10-04 → 2026-10-15 | 6,238 calls, 1.6 h | **SENSEX in all: 16,906 contracts.** All three indices are now complete from Oct 2024 |
| §9 reconciliation (Kotak recorder vs Upstox) | Action run 39223454396 (2026-10-19 08:32 UTC) | `reconcile.json` | 120 contracts, 29,126 matched minutes | session 2026-10-16 | 120 Upstox calls | See "Source reconciliation" |
| §9 Upstox expired backfill, BANKNIFTY | Action run 39279563934 (2026-10-19 15:38 → 18:50 UTC) | expired BANKNIFTY options, 1-min with OI | **3,248 contracts; 31,555,677 rows** | **complete**: 30 expiries 2024-10-01 → 2026-09-29 (monthly only; the weeklies ended in Nov 2024) | 11,783 calls, 3.2 h | First run at the new night cap (1,800 / 30 min) |
| §9 Upstox expired backfill, SENSEX part 1 | Action run 39306143329 (2026-10-19 18:52 → 21:07 UTC) | expired SENSEX options | partial (saved: the commit steps run `if: always()`) | 106 expiries 2024-10-04 → 2026-10-15; estimate ~38,900 calls (~11 h) | ~2.2 h | **Failed on HTTP 429**, still rate-limited after 5 tries. A `stock-options-probe` run used the same token at the same time (20:47-21:00 UTC). Fix e46c20a: a 429 is now waited out for ~38 min. Resumes after NIFTY part 3 (`run_jobs5.sh`) |

## Expired-token retention
NIFTY 19-Oct-2026 22650 CE, Kotak token 47141 (expired 2026-10-19). Probed by `index_data/probe_expired.py` through
`.github/workflows/kotak-probes.yml` on 2026-10-20, 10-27 and 11-19 (its cron did not fire on 20 Oct; that run was started
by hand at 19:19 IST). The rows below are written by `index_data/probe_report.py`.

**Probe 1 (one day after expiry): retained.** Kotak still serves the expired contract's 1-minute (1,923 rows, the same
as before expiry), expiry-day (384) and 5-minute candles, although the token is gone from the scrip master. Daily
candles return 0 rows. So a contract's history can be fetched by its token after expiry, as long as the token was
saved beforehand (the recorder keeps `recorded_tokens.json`).

| Probe | Date | 1-min 10-12 → 10-16 | Expiry day | 5-min | Daily | Still listed | NIFTY control | Verdict |
|---|---|---|---|---|---|---|---|---|
| before expiry (DATA_ACCESS_AUDIT) | 2026-10-18 | 1,923 | — | 385 | — | yes | 1,807 | — |
| probe 1 | 2026-10-20 (run 2026-10-20) | 1923 | 384 | 462 | 0 | no | 376 | retained |
| probe 2 | 2026-10-27 (run 2026-10-27) | 1923 | 384 | 462 | 0 | no | 361 | retained |

## VIX corrections
Kotak's India VIX minutes with open > 200 were divided by 100: **92,936 rows corrected**, from **2021-10-20 09:15** to
**2023-08-22 15:29**. Kotak's daily `D` VIX candles show the same scale and are corrected the same way in the cross-check.

## yfinance vs Kotak India VIX
Daily closes, 2022-01-01 → 2026-10-16: **1,177 days compared, 0 mismatches above 1 %**.

## Source reconciliation
Run 2026-10-19 on the 16 Oct session (Kotak's recorder vs Upstox's history, 120 contracts, 1-min closes):
- **29,126 minutes on both.** **77.3 %** have the identical close; the mean absolute difference is **Rs 0.35**,
  and the largest single gap is Rs 93.8 (one outlier, to look at).
- 0 minutes are Kotak-only, and **16,083 minutes are Upstox-only**. Checked 2026-10-19 on the files (the 120
  contracts are BANKNIFTY 27-Oct / 23-Nov): **16,037 of them (99.7 %) have volume 0**. Upstox writes a flat candle
  for every minute without a trade; Kotak leaves those minutes out. The other 46 fall at 15:30-15:39.
- **No time offset.** Shifting Upstox by ±1 or ±2 minutes drops the identical closes from 77 % to ≤ 2 %, so both
  label a candle by the same minute.
- On minutes with trades on both, the candles still differ somewhat: same volume 63.7 %, same close 77.5 %, same
  open / high / low / close 41.2 %. The vendors build 1-minute bars from the trade feed slightly differently.
- The largest gaps (Rs 58-94) are deep in-the-money BANKNIFTY calls in minutes where Kotak shows a few trades
  (volume 30-90) and Upstox shows none (volume 0, previous close). Upstox's filler candle there is stale, not a
  price.
- **Merge rule:** keep `source` on every row, and never mix sources inside one contract-day.
  - Kotak wins where it has the day.
  - Upstox's volume-0 rows are fillers: drop them or carry the last close forward, and never treat them as a
    trade price. A study's fill must use a minute with volume > 0.
- Verdict: close enough to combine under the merge rule (mean gap Rs 0.35, mostly the same price). They are not
  identical bar for bar, so a backtest should say which source it used.

## What is available, at which resolution
Filled in after the first runs (see also the coverage table on `/index`).

## Failures and limits
- **EOD chain snapshot:** the GitHub Action runs at 19:30 IST, so the chain is the **closing book** (last price, OI,
  the bid / ask as left at the close), not a 15:25 live snapshot. GitHub's cron is not punctual enough for 15:25.
- **SENSEX daily OHLC:** no stable public BSE derivatives bhavcopy URL is used. SENSEX options are covered at 1-minute
  only (Kotak recorder, Upstox).
- **Upstox expired history:** starts at NIFTY 2024-10-03. 2022 → Sep 2024 expired contracts are not listed.
