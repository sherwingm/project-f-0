# Progress

Updated at the end of every session. `DECISIONS.md` is authoritative for rules and the strategy record.

**State as of 2026-10-17.**

## How we work
- **S1 and S2 are kept separate**: their own specs (`strategies/S1_*`, `strategies/S2_*`), modules, pages, paper
  records and sections below. One commit never mixes S1 and S2 changes.
- **Every step is committed and pushed** to `origin/main` (GitHub is the source of truth across machines), and
  recorded in this file in the same push. A rule or strategy result goes into `DECISIONS.md` in its own commit.
- Working clone from 2026-10-17: `C:\Users\sherw\project-f-0` (fresh `gh repo clone`). Earlier checkouts:
  `D:\project-f-0-main\project-f-0-main` (2026-10-13). `paper-state` is written by the live server only.

---

## S1 · results-based calls (and v10 puts / calls)

### Where it stands (2026-10-17)
- **Backtested versions v2–v9: all closed** (DECISIONS.md). The 2021-24 results-beat drift did not persist in
  Apr 2025 – Sep 2026 (v8 used the holdout by the user's choice, 2026-10-14).
- **Two paper-only runs are live**, and they are the only fresh evidence:
  1. **S1 rule trades** (v7 rules without near-expiry trades; `scanner/forward_s1.py` nightly + `server/rules.py`
     live), arms A / B, each signal bought twice (open, close). Ledger epoch "2026-10-14 S1 rules".
  2. **S1 v10 results-day fade** (`strategies/S1_v10_results_day_fade_paper.md`; `scanner/fade_live.py` +
     `server/fade.py`): strong numbers → put, weak → call, bought 09:15–15:20 on day 0, sold at 15:20 the same day.
     Review at 30 closed trades or 6 weeks, whichever is later; no rule changes during the run.
- **Live paper account at its last save (2026-10-16 11:21 IST)**, cash ₹4,28,829 of ₹5,00,000:
  - S1: TATAELXSI 26 NOV 4000 CE twice (open entry 57.85, close entry 59.21; mark 87.50, about +₹7,100 together).
  - Fade, opened 16 Oct 09:15: NESTLEIND 1250 PE, INDIANB 810 PE, POLYCAB 7700 PE, PERSISTENT 5900 CE,
    TECHM 1620 PE, ANGELONE 300 PE, JIOFIN 220 CE, LTF 245 PE (Oct expiry). **Not sold at 15:20 on 16 Oct**:
    the server stopped saving at 11:21 (see Known issues); `server/fade.py` sells them at the first poll of the next
    session (Mon 19 Oct), which the v10 page does not intend.
  - Closed: BHEL 410 PE (fade, 15 Oct), −₹192 (−3.3 %). Refused: HCLTECH open entry 14 Oct (one lot ₹14,440 >
    ₹8,000); CANBK fade 15 Oct (premium < ₹2).
- **Queued for Mon 19 Oct** (20 Oct is an NSE holiday): S1 forward arm A IRFC, TECHM, WIPRO; arm B TECHM, WIPRO.
  Fade: FEDERALBNK PE, UJJIVANSFB PE (5 filings skipped: numbers neither strong nor weak).

### Log
- **2026-10-13**
  - **S1 v6 closed**: the 3-session decay exit sold after 3.6 sessions on average and lost money (arm A −19 %,
    t −2.3; arm B −3.7 %, N 75), while the futures diagnostic of the same signal stayed strong (B +3.66 % over 20
    sessions, t 4.25). The 2021-22 results events were back-filled into the local event store.
  - **S1 v7 closed**: current-month calls down to 3 sessions left, 5-session decay exit, 50 % stop, T-1. Arm A
    −17.3 % (t −1.5); arm B +31.8 % but t 1.1 and N 84. Near-expiry calls lost most (A −37 %). Per-trade sheets:
    `python -m scanner.trade_sheet`, `data/results/S1_v6_trade_sheet.xlsx`, `S1_v7_trade_sheet.xlsx`.
  - **Forward paper test from 14 Oct** (`scanner/forward_s1.py`, nightly Action, page buttons Arm A / Arm B): S1 v7
    rules without near-expiry trades, one session at a time from NSE's closing files; state
    `data/forward/s1_forward.json`.
  - **Paper account restarted for the S1 rule trades** (`server/rules.py`, epoch "2026-10-14 S1 rules"; the 30 Sep
    system-test trades are archived inside the ledger): each "buy next session" signal bought twice, 1 lot each, at
    the open and at the close (ATP + 1 tick); exits at 15:20 on the last price: 50 % stop, 5 sessions without a new
    closing high, T-1; sold at the best bid. One scoreboard per arm on the results page.
- **2026-10-14**
  - **S1 v8 closed, and the live rules fail on recent data** (holdout used by the user's choice; NSE F&O files for
    2025-02 → 2026-10 cached, ban lists back-filled): calls on any result in a strong sector −27.6 % a trade
    (t −3.4); live rules arm A −3.3 % (t −0.25), arm B −14.5 % (t −1.0); the stock's own 20-session move ≈ 0.
  - **Arm A studies (hindsight)**: `scanner.peak_study` + `scanner.peak_study_sheet`, workbook
    `S1_armA_peak_study.xlsx`, two reports in `data/results/`. No exit or result-quality rule beats the live rule in
    both samples; the losses are entries whose stock does not move.
  - **Quiet results days skipped** (user's decision): a signal whose results-day range is under 3 % of the previous
    close is not bought (forward test and rule trades). The expiry and day-1 rules from the loss study were not
    adopted.
  - **Rule trades' open entry** now walks the day-0 liquid strikes on live prices 09:15–15:20 (retry every
    2 minutes) instead of one strike fixed overnight (HCLTECH's 1330 CE cost ₹14,440 at the 14 Oct open).
  - **S1 v9 and event screens closed** (pre-registered, then run): results-day calls on strong numbers, stock screen
    0 of 32 cells, options 0 of 48 groups; block deals, ex-dividend and QIP screens: no tradable pass
    (`data/results/S1_v9_backtest_report.md`, `event_screen_*.md`). Side observation: on results day the stock moves
    against the headline numbers from the open.
  - **S1 v10 results-day fade, paper only**, pre-registered and built from that observation (the user chose "paper
    only, no backtest claim"): signals nightly and before the open (`.github/workflows/fade-morning.yml`, 07:17 IST),
    NSE F&O holidays in `data/nse_holidays.json` (20 Oct and 10 Nov), fade cards on the results page.
- **2026-10-15**: first fade trades (BHEL closed −₹192; CANBK refused); TATAELXSI arm A bought at the open and close.
- **2026-10-16**: 8 fade positions opened at 09:15; last ledger save 11:21; no 15:20 exits.

---

## S2 · price + futures OI build-up, stock options (1–5 day holds)

### Where it stands (2026-10-17)
- **Step 1 screen** (`strategies/S2_oi_buildup_screen.md`): 1 of 48 cells passed — short build-up (price ≤ −3 %,
  futures OI ≥ +10 %, volume ≥ 1.5×), 5-session short +0.62 %, t 3.2.
- **Step 2 put: closed, failed** (`strategies/S2_step2_short_buildup_put.md`, `data/results/S2_put_backtest_report.md`):
  580 puts, mean −14.2 % of premium, t −2.71, positive only in 2024; the same trades as a short stock +0.66 %. The
  ₹600–8,000 lot puts the strike 5–10 % below the stock, which a 0.66 % move does not reach.
- **S2 page** (`templates/s2.html`, `/s2` on the server, `docs/s2.html` on Pages): the last session's short
  build-ups nightly (`scanner/s2_live.py` → `data/s2/signals.json`), as information only — no S2 trades.
- **Screen B pre-registered, not run** (`strategies/S2_put_screens_B.md`, 2026-10-14): parent indicators, market
  backdrop, sector rotation, gap fill, weak results × pre-move. Gates before any run: cache the yfinance series
  (`data/parents/`, not created yet), freeze `data/financials.json`, recount events. The new modules
  (`scanner.s2_parent_screen`, `s2_market_filter`, `s2_rotation_screen`, `gap_screen`, `s2_weak_results_screen`)
  do not exist yet.

### Log
- **2026-10-14**
  - S2 started (the user stopped tuning S1; its paper trades keep running). Step 1 screen year by year 2021-2026
    (`python -m scanner.s2_screen`, all NSE F&O files 2021-2026 cached). Long build-up is consistently negative for
    a long (recorded as a lead, not promoted).
  - Step 2 pre-registered, run and closed (above). S2 page built.
  - Screen B pre-registered (14 pass-eligible cells, 11 pass tests; about 176 tests on the window so far).

---

## Shared platform

### Built and working
- EOD scan (labels, OI/PCR, strikes, events, verdict card), phone page, GitHub Pages; nightly GitHub Action.
- **Results page is the home page** (`templates/results.html`, `/` on the server; the terminal is at `/terminal`):
  paper account, Arm A, Arm B, fade; each open position is a card (entry, now, max up / dip, stop, auto-exit, P&L,
  Close); closed trades are followed after the sale until T-2.
- **Trading-terminal page** (`templates/index.html`): watchlist, candle chart (Lightweight Charts 4.2.0), option
  charts, tabs Overview / Options / News / Results / Signals, heatmap, movers, alerts, light/dark, phone layout.
  Options only: "Buy CE / Buy PE"; the server refuses futures orders.
- Server: Kotak `avg_cost` (ATP), OHLC, depth, 52-week range, circuits; intraday tick buffer and `server/candles.py`;
  with no live polls the 1m/5m/15m charts show the last session from Kotak's historical API.
- Quarterly results: `scanner/financials.py` (NSE XBRL) → `data/financials.json`, refreshed nightly for stocks that
  just reported (40 a run at most).
- Scan freshness: when eod2_data lags, the build fills missing sessions from NSE's cash-market bhavcopy
  (`scanner/cm_fallback.py`, gaps up to 60 days). The events job re-reads the last 3 days and the next ban list.
- Live server on Render: Kotak feed ~213 stocks every 30 s, live labels, paper orders with real-depth fills,
  charges, stops, kill switch.
- Paper account persistence (`server/durable.py`): committed to `paper-state` on fills, exits, stop triggers and a
  15-minute snapshot; restored on start.
- Position limits (DECISIONS.md): long-option cost ≤ 6 % of capital, max 3 open positions, daily loss halt 2 %
  (rule trades are outside the manual-order limits).
- Backtest engine (`scanner/option_engine.py`): fills, expiry rule, test/holdout split, date-clustered t.
- Guide 17: always-on Mumbai VM (Lightsail or Oracle), IST + NTP, systemd, Tailscale — **not created yet**.

### Secrets and expiries (never the values)
- `LEDGER_GITHUB_TOKEN`: fine-grained GitHub token, Contents read/write on `project-f-0` only, in Render →
  Environment. **EXPIRES 2026-10-30**: renew before then, or the paper account stops being saved
  (`persistence.error` in the summary).
- `APP_PASSWORD`: local `.env` and Render. Render runs `PUBLIC_ACCESS=true` (no login; real orders refused).
- `KOTAK_CONSUMER_KEY`: Render and local `.env` (regenerated 2026-10-13); market data only.

### Log
- **2026-10-17**: **Keep-awake workflow** (`.github/workflows/keep-awake.yml`): visits `/api/live` every 4 minutes
  08:30–15:45 IST on NSE trading days (two starts, 08:30 and 12:00, because a job may run at most 6 hours; skips
  `data/nse_holidays.json` days). Cause found: nothing visited Render during market hours since the opening-snapshot
  workflow was deleted on 2026-09-30; a cold start took 72 s on 17 Oct. First scheduled run: Mon 19 Oct 08:30.

- **2026-10-17 · carried fade trades: closed, rule retired** (S1; docs `c24e9ef` → `584a045`, code `832aad9` → `33fde93`): the eight
  fade trades opened 2026-10-16 and not sold at 15:20 (server asleep) are **excluded from the S1 v10 review**. First they were
  to be kept under a −20 % stop / 25 % trail / T-1 rule (`server/fade.py::_carry_exits`, tested). After the backtest below the
  user decided (later the same day) to **close them and keep the same-day exit strict for every fade trade from Monday
  19 Oct**: `CARRY_DATES` is empty, so the eight are sold at the first poll of 19 Oct (reason `fade_late`, 20 Oct is a holiday)
  and the carry rule never ran live. The code and its tests stay; a guard test pins `CARRY_DATES == set()`. Their result is
  reported beside the v10 review, never in it. The suite's one failure (`test_spec12_step7_model::test_infer_for_scan_adds_the_model_block`)
  fails without these changes too. Not done: a results-page badge for carried trades.
- **2026-10-17 · fade trade sheet** (`data/results/S1_v10_fade_trade_sheet.xlsx`, force-added; `data/results/` is git-ignored): the 434
  backtest trades under the same-day exit (premium, gross and net P&L, net %, the stock's open → close), the live paper fade trades
  from the last ledger save (stale marks), a summary on formulas, and the rule notes. Formulas were checked against pandas with a
  Python formula engine because LibreOffice is not installed here (Excel recalculates on open; a plain-number copy of the summary
  is on the Summary sheet for phone viewers). It was sent to the user's phone.
- **2026-10-17 · deploy check** (`e420aa1`): `/api/paper/summary` now returns `version.commit` (Render's `RENDER_GIT_COMMIT`) and
  `version.fade_carry_dates`, so a deploy can be verified from outside. Confirmed: Render runs `e420aa1`, `fade_carry_dates` is `[]`,
  10 positions open, no persistence error. The Render connector exists in the registry (`mcp.render.com`) but is not connected here.
  LibreOffice install (`winget install TheDocumentFoundation.LibreOffice`) was started and then **abandoned at the user's request**:
  winget was stopped; one elevated `msiexec` could not be stopped from here (access denied) and `soffice.exe` was not present. The
  fade sheet stays verified against pandas (formula engine), not recalculated in LibreOffice.
- **2026-10-17 · TATAELXSI twice on 15 Oct is by design, but not a clean comparison**: each S1 buy signal is bought twice (open
  walk from 09:15, close walk at 15:20) to compare entry times. On 15 Oct the server was asleep until about 15:17 (first
  `paper-state` write that day was 15:16:58), so the "open" entry filled at 15:17, three minutes before the close entry:
  that pair is not a valid open-versus-close comparison.
- **2026-10-17 · S1 v10 descriptive backtest 2025-26** (pre-registered `d0a4339`, code `1997818`, result `b87037d`;
  `python -m scanner.backtest_s1_v10`, report `data/results/S1_v10_backtest_report.md`, force-added because
  `data/results/` is git-ignored; the trade list stays local). 1,259 results filings → 499 signals → 433 trades (322 puts,
  111 calls), entry day-0 open + 1 tick. **Same-day exit: +5.6 % of premium, median −17 %, hit 40 %, t 1.33, +₹1.24 lakh.
  Carried-trade rule: −10.8 %, median −36.5 %, hit 24 %, t −2.60, −₹2.86 lakh** (the −20 % stop closed 68 % of trades on
  their first close; holding the survivors past day 0 lost money). With a VWAP + 1 tick entry both are negative (−14.9 %,
  −24.9 %), so the result hinges on the entry price and the live fill is later than the open. The stock's day-0 open →
  close moved against the headline by +0.64 % (t 4.2). Descriptive only; not out of sample (2025-26 is the S1 v8
  holdout and the window where the fade was seen). Nothing changed in the live rules. Data fetched for it (local, not in
  git): F&O bhavcopies 2024-12 → 2026-09 in `data/cache`, eod2 in `data/eod2`, the event store from the `state-seed`
  release (used via `EVENTS_DB`, the local `data/events.sqlite` untouched). The suite's one failing test is unchanged.

### Known issues
- **Render free tier sleeps** after 15 minutes without visits: on 2026-10-16 the ledger was last saved at 11:21, the
  server came back only after 16:00, and the eight fade positions were not sold at 15:20 (they sell at the first poll
  of 19 Oct, per `server/fade.py`). Fixed from 19 Oct by the keep-awake workflow; GitHub may start scheduled runs
  late or skip one, so an external pinger (e.g. cron-job.org, every 5 min, 08:30–15:45 IST) or the guide-17 VM is
  the stronger fix. (Decided 2026-10-17: the eight are closed on Monday and stay out of the v10 review.)
- `paper-state` gets repeated `live_snapshots/*` commits of the same files on every restart (16 Oct 16:17, 16:53;
  17 Oct 00:10, 09:12).
- HCLTECH (arm A, 14 Oct): only the open-entry refusal is logged; no close-entry position or refusal — to check.

## Next
1. Check on Mon 19 Oct that the keep-awake runs (08:30), the 8 carried fade positions sell at the first poll (09:15), and the
   new day's fade trades (FEDERALBNK PE, UJJIVANSFB PE) sell at 15:20. Then the always-on VM (guide 17) or an external
   pinger as a second layer.
2. Renew `LEDGER_GITHUB_TOKEN` before 2026-10-30.
3. S2: run screen B in the pre-registered order (cache parents → freeze financials → recount → screens).
4. S1: keep the paper runs untouched; review v10 at 30 closed trades / 6 weeks.
