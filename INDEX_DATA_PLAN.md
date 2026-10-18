# Index-options data layer: plan (2026-10-18)

Goal: collect and store index-option, index-spot and India VIX data so later index strategies ("pods") can be
backtested and paper-traded. **No strategy or trading logic in this task.** The existing stock-options code is not
touched: new package `index_data/`, new server modules `server/index_api.py` and `server/index_pages.py`, new
workflows. Sources: Kotak Neo (consumer key), Upstox (free Analytics Token), yfinance, NSE public files. Nothing paid.

## What the probes already established (DATA_ACCESS_AUDIT.md)

| | Kotak Neo | Upstox (Analytics Token) |
|---|---|---|
| Live index options, 1-min / 5-min | yes, by scrip-master token | yes, by `NSE_FO\|token` / `BSE_FO\|token`, **OI in candle[6]** |
| Expired index options, 1-min | no token after expiry (being probed: §2) | **yes**, `/v2/expired-instruments/...`, NIFTY from **2024-10-03** |
| Index spot / India VIX, 1-min | yes, back 5 years (`nse_cm\|Nifty 50`, `nse_cm\|INDIA VIX`), < 30 days a call; old VIX ×100 | yes, back to 2022 |
| Daily | `D`, ≤ 180 days a call | yes |

The free Analytics Token already reaches the expired-instruments API, so §9 does **not** need the OAuth login. The
OAuth helper (`index_data/upstox_login.py`) is still added as the requested fallback, but every Upstox script
reads the Analytics Token first.

## Where data lives

| Data | Size | Where |
|---|---|---|
| Large Parquet (options 1-min, options daily, spot 1-min, instrument snapshots, chain snapshots) | ≈ 3-5 MB a recorder day; backfills a few hundred MB | Orphan branch **`index-data`** in the same repo, written by the Actions (and by the PC for the NSE bhavcopy backfill, since NSE refuses cloud IPs). Never merged into `main`. |
| Small JSON (`data/index/status.json`, `coverage.json`, `expiries_next.json`, `probe_expired.json`) | KB | Committed to **`main`**, under `data/index/`. Added to `render.yaml` `ignoredPaths` so they never redeploy Render. |
| The Upstox OAuth token | — | `data/index/.upstox_token` (git-ignored); in Actions only the secret |

**The Render page reads the small JSON from GitHub's raw URL** (the same idea as `SCAN_URL`), because Render has no
persistent disk and does not redeploy on these commits.

## Order of work (priority from the request)

1. **§1 instruments:** `index_data/instruments.py` loads OPTIDX / FUTIDX from `nse_fo.csv` (NIFTY, BANKNIFTY,
   FINNIFTY, MIDCPNIFTY) and IO / IF from `bse_fo.csv` (SENSEX), plus the four spot names. Fix the BSE expiry date:
   BSE `pExpiryDate` is a plain Unix time, not NSE's 1980 epoch; check against 22-Oct-2026. Daily snapshot
   → `index-data:data/index/instruments/YYYYMMDD.parquet`.
2. **§3 recorder:** `index_data/recorder.py` + `.github/workflows/index-recorder.yml`, 19:30 IST Mon-Fri.
   - **Contracts:** NIFTY, SENSEX, BANKNIFTY; the two nearest expiries each; strikes within ±5 % of the day's spot
     close (Kotak `D`); CE and PE.
   - **Candles:** 1-min from Kotak, one call per contract, ≥ 1.5 s apart. On a contract's first appearance, back to
     its listing date in < 30-day windows. Parquet per `<underlying>/<expiry>/<date>.parquet`, deduplicated on
     (token, timestamp), `source = 'kotak'`.
   - **EOD chain snapshot:** quotes for the same contracts.
     - The Action runs at 19:30, so this is the **post-close** quote (last price, OI, the book as left at the close),
       not a 15:25 live snapshot.
     - A true 15:25 snapshot would need a job during market hours (GitHub cron is not punctual enough); this is
       documented as a limit.
   - **Status and failure:** `status.json` with run time, contracts, rows per underlying, calls, runtime and
     failures. A non-zero exit if any underlying returns zero contracts.
   - **Tonight:** a manual first run proves Kotak answers GitHub's runners.
3. **§4 spot / VIX backfill (Action, Kotak):** `index_data/backfill_spot.py`.
   - Nifty 50, Nifty Bank, SENSEX and INDIA VIX, 1-min, Oct 2021 → today, in < 30-day windows.
   - VIX open > 200 → ÷ 100, logged. Pre-09:15 rows dropped.
   - India VIX daily from yfinance, cross-checked against Kotak `D` (mismatches > 1 % reported).
4. **§5 daily OHLC (PC):** `index_data/bhavcopy_ohlc.py` re-downloads the raw NSE F&O bhavcopies 2021 →, keeping
   IDO / IDF rows with the full OHLC column set → `options_daily/<underlying>/<YYYY>.parquet`. BSE: look for a public
   derivatives bhavcopy URL; document if none.
5. **§6 expiry calendar:** `index_data/expiry_calendar.py`.
   - Built from the bhavcopy `XpryDt` (2021 →) plus the scrip master (forward).
   - Weekly vs monthly: the monthly is the last expiry of its month.
   - Reconciled with `data/nse_holidays.json`.
   - Output: `expiries.parquet` (index-data) + `expiries_next.json` (main).
   - Function `nearest_expiry(underlying, day, weekly=True)`.
6. **§8 page:** `server/index_pages.py` (`/index`), `server/index_api.py` (`/api/index/...`), template
   `templates/index_trading.html` in the style of `/s2`.
   - Shows data coverage, recorder health, probe results, the next three expiries per underlying, and an empty
     "Pods" results table.
   - Nav links from `/` and `/s2`.
   - No order controls.
7. **§9 Upstox expired backfill:** `index_data/upstox_expired.py`.
   - Expiries from the expired-instruments API (NIFTY from 2024-10-03; SENSEX and BANKNIFTY as listed).
   - Strikes within ±5 % of the close on each contract's first listed day, taken from `options_daily` or the cached
     bhavcopy (SENSEX: from Upstox's own daily index candles).
   - 1-min from listing to expiry, with OI. Restart-safe (skips work already on disk), 429 backoff, stop on
     `UDAPI1149`, and the total is estimated before starting.
   - Runs in chunks as a manual Action (6-hour job limit).
   - `index_data/reconcile.py` compares Kotak and Upstox on the overlapping live contracts.
8. **§2 expired-token probes:** `index_data/probe_expired.py` + `.github/workflows/index-probe-expired.yml` (manual).
   - The scheduled tasks on 2026-10-20, 10-27 and 11-19 at 16:00 IST dispatch it and record the result.
   - The 10-20 task is switched to this workflow instead of re-adding server endpoints.
9. **§7 report:** `INDEX_DATA_REPORT.md`, updated as each piece runs.

## Rate limits and run time (estimates)

- **Kotak recorder:** NIFTY ±5 % at 50-point steps ≈ 46 strikes, SENSEX at 100 ≈ 74, BANKNIFTY at 100 ≈ 56. × 2
  sides × 2 expiries ≈ 700 contracts ≈ 700 calls at 1.5 s ≈ **18 minutes a night** (first night longer: the history
  back to listing).
- **Spot / VIX backfill:** 4 series × ~62 windows ≈ 250 calls ≈ 6 minutes.
- **Upstox expired backfill (NIFTY alone):** 107 expiries × ~46 strikes × 2 ≈ 9,800 contracts × 1-3 calls. With
  the 1,000 calls per 30 minutes limit, that is **many hours, in several runs**. Exact numbers are printed by the
  script's estimate step.
