# Progress

Updated at the end of every session. `DECISIONS.md` is authoritative for rules and the strategy record.

**State as of 2026-09-30.**

## Secrets and expiries (never the values)
- `LEDGER_GITHUB_TOKEN`: fine-grained GitHub token, Contents read/write on `project-f-0` only. Stored in Render →
  Environment (and later the VM `.env`; then deleted from Render). **EXPIRES 2026-10-30**: renew and replace
  before then, or the paper account stops being saved (the summary's `persistence.error` shows it).
- `APP_PASSWORD`: local `.env` and Render → Environment (`PUBLIC_ACCESS=false` is live since 2026-09-30). (A GitHub Actions secret is no longer needed: the
  opening-snapshot workflow was deleted.)
- `KOTAK_CONSUMER_KEY`: Render → Environment and local `.env`; market data only, no login needed.

## Built and working
- EOD scan (labels, OI/PCR, strikes, events, verdict card), phone page, GitHub Pages; nightly GitHub Action.
- Scan freshness: when eod2_data lags, the build fills the missing sessions from NSE's cash-market bhavcopy and
  index-close file (`scanner/cm_fallback.py`; listed in `meta.price_fallback_days`). Checked on 28–29 Sep 2026.
- Live server on Render: Kotak feed 213 stocks every 30 s, live labels, 09:30 snapshot, paper orders with real-depth
  fills, charges, stops, kill switch (first live run 2026-09-30).
- Paper account persistence (`server/durable.py`): committed to the `paper-state` branch on fills, exits, stop
  triggers and a 15-minute snapshot; restored on start. End-to-end restart test passed 2026-09-30.
- Position limits (DECISIONS.md): long-option cost ≤ 6 % of paper capital, max 3 open positions, daily loss
  halt 2 %.
- Backtest engine (`scanner/option_engine.py`): fills (VWAP/close + tick, ≥ 50 contracts), expiry rule,
  test/holdout split, date-clustered t.
- Guide 17: always-on Mumbai VM (Lightsail or Oracle), IST + NTP, systemd, Tailscale, the NSE-archive test.

## Strategy record (DECISIONS.md is authoritative)
- S1 v1 superseded; v2 closed (results-miss: no drift); v3 closed (strength score: selected stocks went the
  wrong way on the long side, 20-session t −2.34); v4 closed (results-beat naked call: 3 and 1 trades under the
  ₹2–8k budget).
- S1 v5 (same signal, ₹10–30k band, 1 lot, long call, current-month expiry) **closed 2026-09-30**: arm A 170
  trades, mean −1.2 %, t −0.13; arm B (strong sector) 57 trades, mean +42.7 %, t 2.29, positive in both
  sub-periods, but N 57 < 200.
- Only positive signal so far: results beats +1.3 % (all) / +1.9 % (strong sector) over 20 sessions net of
  the sector, t ≈ 3, 2021–2024.

## Paper account (live test, Render)
- Opened 2026-09-30 11:52 IST by the system-test rule (top live setups by volume ratio, 1 lot, ATM, stop 0.5x):
  APOLLOHOSP 8200 PE, MAXHEALTH 940 PE, FORTIS 780 PE (October expiry). At the 15:36 close: equity ₹5,15,590.29,
  unrealised +₹15,590.29 after exit charges, no stop triggered, 0 closed trades. Held overnight; the account is
  in the `paper-state` branch and restored on every restart.

## Known issues
- eod2_data stale since 2026-09-25: the fallback fills the gap from tonight's build (first run after the
  2026-09-30 push). The server's scan on 2026-09-30 still had the expired 29 Sep chains; the paper orders used
  the October contracts by hand.
- 2026-09-30 paper test: the ledger was wiped twice (11:05, this PC slept and Render slept; 13:47, Render
  redeployed when environment variables were saved). The three positions were restored from the 13:46 watcher
  log; stops were not watched between 13:47 and the restore. Saving environment variables on Render always
  redeploys: with persistence on, the account now survives it.
- Render free tier sleeps after 15 minutes without visits; until the VM runs, something must visit it during
  market hours.

## Next
1. Create the always-on VM (guide 17; Oracle Mumbai), token in its `.env`; confirm the live feed and a restart.
2. Then Render becomes the mirror: `DATA_PROVIDER=none` and delete `LEDGER_GITHUB_TOKEN` there.
3. Decide the next S1 version (starting from the diagnostic, DECISIONS.md).
4. Renew `LEDGER_GITHUB_TOKEN` before 2026-10-30.
