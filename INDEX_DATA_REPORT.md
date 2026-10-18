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
| §1 instruments + §3 recorder | first run (manual, session 2026-10-16) | — | — | — | — | running |
| §5 daily OHLC (PC) | 2021-01-01 → 2026-10-16 | — | — | — | — | running |
| §6 expiry calendar | local build 2026-10-18 | `expiries.parquet`, `expiries_next.json` | NIFTY 334, BANKNIFTY 252, FINNIFTY 240, MIDCPNIFTY 188, NIFTYNXT50 35 expiries | 2021-01-07 → 2031 | — | `nearest_expiry("NIFTY","2023-07-05")` = 2023-07-06; `("NIFTY","2026-10-14")` = 2026-10-19 (the week's Tuesday moved to Monday for the 20-Oct holiday). SENSEX joins with the first scrip-master snapshot. |
| §4 spot / VIX backfill | not run yet | | | | | |
| §9 Upstox expired backfill | not run yet | | | | | |

## Expired-token retention
NIFTY 19-Oct-2026 22650 CE, Kotak token 47141 (expired 2026-10-19). Probed by `index_data/probe_expired.py` through
the `index-jobs` Action on 2026-10-20, 10-27 and 11-19 at 16:00 IST (scheduled tasks).

| Probe | Date | 1-min 10-12 → 10-16 | Expiry day | 5-min | Daily | Still listed | NIFTY control | Verdict |
|---|---|---|---|---|---|---|---|---|
| before expiry (DATA_ACCESS_AUDIT) | 2026-10-18 | 1,923 | — | 385 | — | yes | 1,807 | — |

## VIX corrections
Pending the §4 run (Kotak's older India VIX minutes come ×100).

## yfinance vs Kotak India VIX
Pending the §4 run.

## Source reconciliation
Pending: needs Kotak recorder sessions from 2026-10-19 on, then `index-jobs` → `reconcile`.

## What is available, at which resolution
Filled in after the first runs (see also the coverage table on `/index`).

## Failures and limits
- **EOD chain snapshot:** the GitHub Action runs at 19:30 IST, so the chain is the **closing book** (last price, OI,
  the bid / ask as left at the close), not a 15:25 live snapshot. GitHub's cron is not punctual enough for 15:25.
- **SENSEX daily OHLC:** no stable public BSE derivatives bhavcopy URL is used. SENSEX options are covered at 1-minute
  only (Kotak recorder, Upstox).
- **Upstox expired history:** starts at NIFTY 2024-10-03. 2022 → Sep 2024 expired contracts are not listed.
