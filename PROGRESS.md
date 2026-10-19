# Progress

Updated at the end of every session. `DECISIONS.md` is authoritative for rules and the strategy record.

**State as of 2026-10-18.**

## Core idea tracker (updated with every step, from 2026-10-18)
How each piece of work moves the user's core ideas forward. Facts and numbers stay in the sections below and in
`DECISIONS.md`; this is the thread that connects them.

### S1 core idea: a company's quarterly results move its stock, and an option can ride that move
| Stage | What it asked | What it found | Where the idea stands |
|---|---|---|---|
| v2-v3 (results miss / strength score) | Do weak results in weak sectors keep falling? | No drift (t −0.7); strength score went the wrong way | Direction "miss → fall" not supported |
| v4-v7 (results-beat continuation, calls) | Does a beat keep rising, and can a call catch it? | The **stock** drifted up after beats in 2021-24 (+1.6 % to +3.7 % over 20 sessions, t 3-4), but **calls lost** after decay and costs | Drift real in the stock, not tradable with cheap calls |
| v8 (2025-26 holdout) | Does the drift still exist? | Gone in 2025-26 (stock +0.2 %) | Continuation idea fails on recent data |
| v9 (results-day calls at the open) | Buy strong numbers on results day itself? | The opposite: strong numbers **fall** from the open, weak ones **rise** (t −5.7 / +) | The first reaction tends to **reverse** within day 0 |
| v10 (results-day fade, paper since 2026-10-15) | Bet on that reversal: strong → put, weak → call, same day | Backtest 2025-26 (descriptive): +5.6 % of premium a trade, t 1.3; stock fades +0.64 % (t 4.2); the result depends on the entry price | **Current form of the idea**, on paper; review at 30 trades / 6 weeks |
| Stop-loss study 2025-26 | Can a stop or target improve it? | A −20 % stop fires on 71 % of trades that end near −21 % anyway: no gain; early targets cut the winners; dips and peaks cluster in the first 15 minutes | Exits: hold to 15:20, no stop, for now |
| 2022-24 re-run (2026-10-18) | Did the fade and the exit findings hold in earlier years? | Fade weaker: +3.6 % a trade, t 0.9 (2023 H1 −14 %), stock fade +0.37 % (t 2.4); exits repeat exactly: stops neutral, early targets hurt, noise in the first 15 minutes | The exit rule (hold to 15:20, no stop) is stable; the fade's edge is small and regime-dependent, so the live paper run decides |
| Diagnostics 2022-26 (2026-10-18) | Why do losers lose? Does a pre-fall, the market or the size of the numbers matter? "Run done → opposite"? | Losers = the stock moving with the numbers (option wins 4-5 % then); pre-run and other pre-entry measures: nothing; NIFTY / sector on day 0 matter but are known only after the close; run done → opposite: no (54-56 %); the fade grows with how extreme NP YoY is, and puts at NP YoY 10-25 % lose in both periods | The core reversal is the stock's own (not the market); the biggest numbers fade most, but no pre-entry filter is proven (the NP YoY 10-25 % lead fails with the VWAP entry in 2025-26): watch item |
| Strike distance study (2026-10-18) | Would a closer strike turn the losers into winners? | No: caps cut the far-strike winners, one step closer is much worse, at the money is worse with the open entry and better only with the VWAP entry, where everything loses | The fade's edge comes from cheap far options multiplying the big fades, and it needs the open price; the live fills decide |
| NP YoY > 25 % shadow track (live, from 2026-10-18) | Do puts on only modest profit growth (10-25 %) lose on live fills too? | Tagging started; so far 1 of 9 live fade trades is a left-out put (INDIANB, +13.9 %) | Tests the strength-of-number lever on new data; judged after ≥ 40 left-out puts |

**Open questions for the idea:** does the day-0 fade survive a realistic live entry (the ask after 09:15, not the open)?
(2022-24 answered: the exit findings hold, the fade is weaker.) Can a time-based exit or a smarter stop help once real minute paths of live trades
are recorded?

### S2 core idea: price plus futures open-interest build-up predicts the next few days
| Stage | What it found | Where the idea stands |
|---|---|---|
| Step 1 screen (48 cells, 2021-26) | Only the **short build-up** (price −3 %+, OI +10 %+, volume 1.5×) kept falling: +0.62 % over 5 sessions, t 3.2 | Real but small edge in the stock |
| Step 2 bought put | −14.2 % of premium (t −2.7): a ₹600-8,000 put is too far below the stock for a 0.6 % move | Not tradable with cheap puts |
| Screen B (run 2026-10-18) + order-book proxy + QIP | Parent indicators and market backdrop: not run (the pinned futures series failed the pre-registered hourly check); sector rotation, gap fill, weak results: 0 of 8 tests pass; order wins and QIP: no fall | No new way to catch a fall; weak results tend to **rise** after day 0 (the fade's call side again), not fall |

## How we work
- **The core idea tracker above is updated with every step**, alongside the detailed log.
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
- **2026-10-17 · sizing question, decided: no change.** The user asked whether trades could be sized by money (as many lots as fit in
  ₹600-8,000, e.g. 7 lots of a ₹1,000 lot instead of 1 lot) in all strategies, then chose to **keep everything as it is**: one lot, ₹600-8,000,
  for the S1 rule trades, the v10 fade, S2 and every backtest. Nothing was changed and the reviews are not restarted.
- **2026-10-17 · fade trade sheet v2: max peak and max dip of the day** (`data/results/S1_v10_fade_trade_sheet.xlsx`, force-added):
  each of the 434 same-day-exit backtest trades now carries the option's day open / high / low / close (from the cached bhavcopy
  price files), MAX PEAK (high vs entry) and MAX DIP (low vs entry) in ₹ per lot and %, the summary adds the average peak / dip and
  the share of trades whose peak reached +30 % / +50 % and whose dip reached −20 %; the live sheet shows the ledger's peak / trough
  since entry. Result: average max peak +83.5 %, average max dip −38.0 %; peak ≥ +30 % in 62 % of trades, ≥ +50 % in 49 %, dip ≤ −20 %
  in 71 %. Hindsight numbers (whole-day high / low, order within the day unknown), not exits. 38 trades have a peak slightly below
  the entry (entry is the open + 1 tick). Verified against pandas with a Python formula engine; LibreOffice is NOT installed (the
  install was abandoned), so there was no LibreOffice recalculation.
- **2026-10-18 · S2 screen B run** (the user's request, with order-book and QIP added; addendum `bf898a9` before any
  return; gates: yfinance 1.7.0 cache pinned in `data/parents/`, financials frozen, F&O 2021 files, corp actions and QIP
  list fetched; recount dropped the order-book cells (50 / 36 events < 100) before returns; an XBRL-date bug found and
  fixed at the recount). Results `data/results/S2_screen_B.md` / `.xlsx` (sent to the phone), 30 events rebuilt from raw
  prices with no mismatch: §1 / §2 not run (hourly check failed: Brent 92.8 %, copper 82.1 % of days within 0.5 %);
  rotation, gap fill, weak results 0 of 8 pass; weak results rose afterwards (already-fallen ones +1.3 % in 5 days,
  descriptive); order wins and QIP showed no fall. DECISIONS updated. Core idea tracker updated.
  Then the user chose "fix check": a date-alignment check written down first (`866d56e`) also failed (Brent 0.60,
  copper 0.53, INFY 0.998); Yahoo's hourly and daily Brent differ by 4-7 % on the same day (different contracts), so
  the free futures data cannot be verified and §1 / §2 stay not run (not changed a second time).
- **2026-10-18 · results site refresh: Arm F workspace** (the user asked; code `e8a6dd5`, `2112408`). `templates/results.html`
  rebuilt as strategy-aware workspaces on one design system: tabs Paper / Arm A / Arm B / **Arm F**, each a config of
  panels rendered by one panel component (same header / loading / empty states), design tokens for arm colours and
  radii (also in `templates/s2.html`). Arm F shows: scoreboard + booked-net line, the next fade list and skipped filings
  (`meta.fade`, new read-only `GET /api/fade`, also embedded in the GitHub Pages copy), the NP YoY > 25 % shadow split
  with progress to 40 left-out puts, open / closed / refused fade trades, earlier lists, and the backtest headlines.
  New everywhere: a 'why' drawer on any trade or signal (numbers, strong / weak, shadow, strike distance, stock
  entry → exit), search (Ctrl+K / 🔍), shareable links (`#armf/POLYCAB`), small booked-net lines per arm. No trading
  rule changed. Checked at phone and desktop width with live data, no console errors.
- **2026-10-18 · NP YoY > 25 % shadow track on live paper** (the user's choice; pre-registered `c01d331`, code
  `23a3d88`). `server/fade.py` tags each fade entry with `np_yoy` / `np_qoq` / `rev_yoy` and `shadow_np25`
  (calls always in; puts only above +25 %); older trades are read from their `why` note. `/api/paper/summary`
  now has `fade_split`: v10 all / shadow / left-out puts / unknown (closed, wins, net ₹, mean net %, open,
  unrealised). v10 still takes every trade. Today's ledger: 9 fade trades, 1 left-out put (INDIANB). Judged after
  ≥ 40 left-out puts have closed. Core idea tracker updated.
- **2026-10-18 · strike distance study done** (the user chose 'a'; pre-registered `afb5a76`, code `6a8bdd6`,
  results `bb930c2`: `data/results/S1_v10_strike_distance.md` / `.xlsx`, sent to the phone). Same signals in both
  windows; baseline reproduces the backtest exactly; 60 sampled trades rebuilt from the price files, no mismatch. No
  variant better: caps 3 / 5 % drop winners, one step closer −14 to −17 points, at the money mixed by entry (worse at
  the open, better at VWAP but still −6 %). v10's strike walk stays; no rule changed. Core idea tracker updated.
- **2026-10-18 · fade diagnostics 2022-26 done** (pre-registered `a5b66f0`, addendum before any table `1521b04`, code `768ea67`; `data/results/S1_v10_fade_diagnostics.md` / `.xlsx` with the answers sheet, sent to
  the phone). 864 fade trades + 2,489 results filings; NIFTY day OHLC from NSE index files (cached, git-ignored).
  Every headline number re-checked from the raw files by separate code (matched). Answers: Q1 partly (1 in 3 losers
  never up; the stock moved with the numbers); Q2 pre-fall no, market yes but only after the fact; Q3 NP YoY yes as a
  candidate (puts 10-25 % lose), QoQ no, revenue no / unclear; Q4 run done → opposite no; other measures mostly no.
  123 bucket tests, ~3.5 expected by chance, 10 passed (9 same-day market / sector). No rule changed; S1 v11 (puts
  only above NP YoY 25 %) waits for the user's go-ahead. Core idea tracker updated.
  **Adversarial check (ultracode workflow, 3 refuters + critic):** all 9 claims survive; corrections folded in —
  the NP YoY lead fails with the VWAP entry in 2025-26 and is chance level (watch item, no v11); "already fell →
  better" is outlier-driven (no difference); POLYCAB / SONACOMS had faded ~6 % before entry; far strikes lose even
  when the stock fades. Code: EPS bands now as in the spec, day range per loser class, blanked features listed.
- **2026-10-18 · the same tests on 2022-24** (pre-registered `ad913d3`, code `02ded63`): 2022 results back-filled from NSE
  into the temporary event store (Jul-Nov 2022 thin: ~20 filings a month), F&O files 2021-12 → 2024-12 cached, day-0 minute
  data for 429 of 436 trades through `/api/history`. Backtest (`S1_v10_backtest_report_2022_24.md`): same-day +3.6 % (t 0.9),
  VWAP entry −14.2 %, stock fade +0.37 % (t 2.4). Stop-loss study (`S1_v10_stoploss_study_2022_24.md` / `.xlsx`, sent to the
  phone): stops neutral (−20 %: +3.3 % vs +3.6 %), targets worse, dips and peaks in the first 15 minutes — the 2025-26 exit
  findings repeat. No rule changed. Core idea tracker updated.
- **2026-10-18 · stop-loss study 2025-26 done** (pre-registered `863c4f6`, proxy-B addendum `b434787`, results in
  `data/results/S1_v10_stoploss_study.md` / `.xlsx`, sent to the phone). Minute data: day-0 1-minute stock candles for all 434
  trades (424 usable) through the new server endpoint `/api/history` (Kotak key stays on Render; refused in market hours).
  **Exact on real prices:** a −20 % stop fires on 71 % of trades that closed at −20.8 % anyway (+6.2 % vs +5.6 % no stop);
  wider stops slightly worse; targets +30 / +50 % worse (they cut winners), +100 % about the same. **Timing:** 53 % of dips and
  42 % of peaks in the first 15 minutes; dip first in 56 %. **Proxies unreliable for levels** (same-day +26-28 % vs +5.6 % real:
  they miss the post-results fall in option value), so trail / stop-from-09:45 are not judged. No rule changed. Next idea if
  wanted: record real minute paths of live trades to judge path rules on real option prices.
- **2026-10-17 · fade timeline, 16 Oct (SL study, with the user)** (`data/results/S1_v10_fade_timeline_2026-10-16.xlsx`,
  force-added): 1-minute option candles for the 8 fade trades from Kotak history via the live server's `/api/intraday`
  (it serves the last session only, for the chain's expiry). All 8 traded above entry at some point; 4 of 8 reached +30 %. Four
  peaked in the first 8 minutes (INDIANB, POLYCAB, TECHM, LTF) and then fell 22-77 % by 15:20; 6 of 8 touched −20 % by 10:03.
  Exits on these paths (mean % of entry, before charges): same-day 15:20 −2.4; stop −20 % +4.9; target +30 % −5.6; stop −20 % +
  target +30 % −1.2; trail 25 % +3.1 — one day, 8 trades, ANGELONE (+179 %) dominates: not evidence, and no rule changed. The
  434 backtest trades have no intraday times (daily high/low only), so a stop study needs minute paths of live trades; the
  user studies the sheet on their side too.
- **2026-10-17 · S1 rule trades: expiry rule changed to ≥ 2 sessions** (DECISIONS `1f6e8a6`; code + data next commit):
  the current monthly expiry is kept while at least 2 sessions remain after day 0 (NSE holidays counted), as the fade does
  (was 10, S1 v7). `python -m scanner.forward_s1 --repick 2026-10-16` moved Monday's queue to the 27 Oct expiry: arm A IRFC
  (no strike ≥ ₹2 at the night pick; the live walk retries), TECHM (1840 CE, ~₹6,350 a lot), WIPRO (187.5 CE, ~₹6,330); arm B
  TECHM, WIPRO. `data/scan.json` meta.forward patched so the server reads it at 08:40 / 09:05 on 19 Oct. Open trades keep their
  expiry (TATAELXSI stays on 23 Nov). The rule trades' paper record is split at this date. Check on Monday that the buys use
  the 27 Oct contracts.
- **2026-10-17 · keep-awake hardened** (`f9c1e3c`): three overlapping starts (08:17, 11:47, 14:17 IST, odd minutes, no longer
  serialised), each to 15:45 IST or 5 h 45 min; the run **fails** (GitHub e-mails the owner) after 3 missed visits in a row; a
  `test_minutes` input for manual runs. Test run 39053665149: 3 of 3 visits answered. A real trading day (Mon 19 Oct) is the first proof.
- **2026-10-17 · fade sheet fixed for phones**: the earlier file had formulas without stored results (openpyxl cannot store them
  and LibreOffice is not installed), so phone viewers showed blank columns. Rebuilt with XlsxWriter, which stores each formula's
  result: 0 empty cells in the 434-row trade sheet when read without calculating.
- **2026-10-17 · why TATAELXSI bought the Nov call, not the Oct one**: the S1 rule trades use S1 v7's expiry rule without near-expiry
  trades: the current monthly only if ≥ 10 sessions remain after day 0. Day 0 was 14 Oct and the 27 Oct expiry had 8 sessions left
  (20 Oct holiday), so the rule took 23 Nov. In hindsight the Oct 4000 CE did better in %: close 10.15 on 15 Oct → 25.10 on 16 Oct
  (+147 %; ₹1,269 a lot), the Nov 4000 CE 57.85 → 93.80 (+62 %; ₹7,231 a lot, so more rupees per lot). One trade; v7's backtest found
  near-expiry calls lost the most (arm A −37 %). No rule change.
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

### 2026-10-19: fade list shows why a signal has not filled
- UJJIVANSFB PE (19 Oct) was not bought because the rule blocks it. At spot ~63 the nearest put asks ~Rs 1.40, under the
  Rs 2 floor, so `walk` stops there (walking further out of the money only gets cheaper). The trader retries every 2
  min and refuses it at 15:20. Before this change the reason lived only in memory.
- `server/fade.py` now keeps today's reason in `rules.fade_wait` (served by `/api/paper/rules`). The walk's
  premium/band reasons name the strike and price. The fade list on the results page has a "Today" column that shows
  bought / refused (reason) / waiting (reason, time checked).
- Pushed with `[skip render]` during market hours. The change goes live on the next deploy.

### 2026-10-19: S1 v10 premium-floor sweep 2025-26 (descriptive, user's request)
- Pre-registered in `strategies/S1_v10_backtest_2025_26.md` (addendum 2026-10-19). `backtest_s1_v10 --min-premium`
  at Rs 2 / 1 / 0.50 / 0.25 / 0.05. Table: `data/results/S1_v10_floor_sweep.md` (`python -m scanner.fade_floor_sweep`).
  The Rs 2 run reproduces the original report exactly.
- Same-day exit (E1). A lower floor adds 50-59 trades with a fill under Rs 2: hit 31-33 %, median -28 to -30 %. Their
  mean looks good (+40 to +52 %), but that comes from one trade: KALYANKJIL 560 PE on 2025-08-08, bought at 1.25 and
  sold at 43.10 (+3,267 %, +Rs 48k). **Without it, the added trades average -13 to -16 % (t about -1.8 to -2.2) and
  lose Rs 45-58k.** E2 is worse.
- No rule change: the live trader stays at Rs 2 (the user decides; DECISIONS.md if it changes).

### 2026-10-19: Arm A / B show why a stock is not bought yet (user's request)
- IRFC (arm A, 19 Oct) was not bought by mid-morning, and nobody could see why. The open-window walk's reason lived only
  in memory. `server/rules.py` now keeps it in `rules.open_wait` (served by `/api/paper/rules`), the same way
  `fade_wait` works. It is cleared on a buy and at the 15:20 refusal. The walk reasons name the strike and price.
- Results page:
  - Paper tab: the "Not bought today" box lists "Still trying" stocks, with the reason and the time checked.
  - Arm A / B: the "Buy next session" table has a "Paper today" column: open entry bought (strike, price), refused or
    waiting, plus the 15:20 entry. It shows only once the paper's first try of the day is on record, so it stays
    hidden on weekends, holidays and stale lists.
  - The page redraws every tab on each paper poll and keeps open sections and the tables' sideways scroll.
- A 3-agent review found 6 low-severity issues; all are fixed:
  - the rules edits and the `/api/paper/rules` copy now run under the ledger lock (`fade_wait` too);
  - the "bought" mark is saved at once, so a restart cannot buy the stock twice (pre-existing gap);
  - the 15:20 refusal uses the saved reason after a restart;
  - a leftover "waiting" row reads "not bought" after 15:20;
  - the column hides when the server is not buying;
  - the sideways scroll is kept.
- No rule change: the walk, the Rs 600-8,000 band, the Rs 2 floor and the 2-minute retry are as before. Tests: the full
  suite passes (the known `test_spec12_step7_model` deselected). Pushed with `[skip render]`; live from the next deploy.

### 2026-10-19: lot-size range check and one-call pricing (the user's idea)
- One lot must cost Rs 600-8,000 and the premium must be at least Rs 2, so a share's premium must lie in
  [max(2, 600 / lot), 8,000 / lot]. Examples: HCLTECH (lot 400) Rs 2-20; WIPRO (3,000) Rs 2-2.67. When the range is
  empty (lot > 4,000), no strike can ever fit. That is 24 of 213 option stocks in the 16 Oct bhavcopy, e.g. IRFC
  (5,425 → at most Rs 1.47), UJJIVANSFB, CANBK, PNB, SAIL, NHPC, IDEA.
- `server/rules.py` `never_fits()`: the open and 15:20 entries (Arm A / B) and the fade entry (`server/fade.py`) now
  refuse such a stock at the first try, with the reason ("never fits: 1 lot is 5,425 shares ..."). Before, they retried
  every 2 minutes all day and refused at 15:20.
- One-call pricing: each try prices every strike its walk may visit (up to 15) in one Kotak `quotes()` call
  (`KotakProvider.quote_many`, `QuoteSource.get_many`). Before, it made one call per strike.
- No rule change: the same strike is picked, and a never-fit stock was never bought before either. The 2-minute retry
  stays (user's choice). Full suite passes. Pushed with `[skip render]`; live from the next deploy.

### 2026-10-19: S1 v10 profit-target exit on day 0 (descriptive, user's request)
- Pre-registered (addendum 2026-10-19 (2)). `python -m scanner.fade_target_exit` → `data/results/S1_v10_target_exit.md`
  / `.xlsx`. A sell at entry × (1 + target) if day 0's high ≥ target + 1 tick, else 15:20. The 15:20 baseline reproduces
  the backtest on all 493 trades.
- Rs 2 floor, 434 trades. 15:20: +5.6 % mean, +Rs 1.26 lakh. +25 %: -2.0 %, -Rs 70k. **+50 %: +1.8 %, +Rs 22k.**
  **+100 %: +6.9 %, +Rs 1.37 lakh (t 2.2).** +200 %: +8.5 %, +Rs 1.40 lakh. Small targets win more often (68 % / 55 %)
  but cap the few big winners that carry the fade. +100 % / +200 % are close to 15:20 and lose in 2025 H1. Optimistic:
  daily data has no timing, and the live buy is later than the open.
- Rs 1 floor: the same pattern, about Rs 20-35k lower than the Rs 2 floor at every target. No rule change.

### 2026-10-19: +100 % target as a shadow exit on live fade trades
- Pre-registered: `strategies/S1_v10_t100_shadow_track.md`. Each new fade position gets `rule.shadow_t100` with a target
  of 2 × entry. `server/fade.py` marks it hit the first time a poll before 15:20 on the entry day sees the best bid at or
  above it. The real exit stays 15:20.
- `/api/paper/summary` → `fade_t100`: real vs shadow closed, wins, mean net %, booked net, targets hit. A new panel on
  the Arm F tab shows it. Judged after 30 tagged trades have closed (t ≥ 2 and the user's agreement to change the rule).
- Goes live with the 15:35 deploy today, so the first tagged trades are the next fade session's.
- Deployed 2026-10-19 at ~15:56 IST with the fade-list "Today" column (60e8551) and this shadow tag (35175c0). Render
  skipped the empty 15:35 commit (383bdd5) and built e2b067a. Today: FEDERALBNK 315 PE sold at 15:20 for Rs 0.25 (bought
  at Rs 2.60, net Rs -5,926). UJJIVANSFB was refused: "premium below Rs 2".

### 2026-10-19: Upstox built as a live source, with a shadow check against Kotak (user's request)
- `server/upstox.py` can now do everything the paper trader needs from Kotak:
  - full market quotes (500 contracts a call) with 5-level depth, ATP, OI, circuits and previous close, in Kotak's
    shape;
  - `quote_one` / `quote_many` for the fill engine and the entry walks;
  - `futures()` for every live contract;
  - `history()` from the v3 candles (intraday for today);
  - options asked by the feed are priced from full quotes, with the chain only as a fallback.
- Its limiter follows the documented 50/s, 500/min, 2,000/30 min, kept lower (40 / 400 / 1,500) so the GitHub jobs
  on the same token keep ~500.
- The instrument file (40 MB of JSON) is now streamed row by row: peak 27 MB instead of 138 MB, the same result.
  Checked on the real file: IRFC lot 5,425, HCLTECH 400.
- **Shadow check, nothing switched:** `server/provider_compare.py` runs while Kotak is live and the Upstox token is
  set.
  - Every 5 minutes of a session (09:20-15:25) it prices the same contracts on both providers: open positions, plus 10
    rotating stocks' near future and near-money call and put.
  - It records last-price gaps, same best bid / ask, volume ratio (the unit check), OI and quote-time lag in
    `data/provider_compare/<date>.json`, mirrored to paper-state, and serves them at `GET /api/data/compare`.
- Tests: `tests/test_upstox.py`; the full suite passes. Pushed with `[skip render]`; live with the 15:35 deploy, so the
  first rounds run on 20 Oct.
- The switch itself (`DATA_PROVIDER=upstox` on Render) comes after a few days of clean rounds, done after market and
  logged in DECISIONS.md. The live stream (WebSocket) is the next step after that.

### 2026-10-19: sub-Rs 2 entries, backtest + live shadow entry
- Pre-registered: `strategies/S1_v10_subfloor_entry.md`. `python -m scanner.fade_subfloor` →
  `data/results/S1_v10_subfloor_entry.md` (+ `S1_v10_subfloor_trades.csv`). The new run: `backtest_s1_v10 --start
  2022-01-01 --end 2024-12-31 --min-premium 0.05 --tag _2022_24_floor0p05`.
- **Fails all three pass conditions.** Tick model: entry open + Rs 0.10, exit close - Rs 0.10, real charges. The 140
  sub-Rs 2 trades lose Rs 52,517 (2022-24: -23k on 81 trades; 2025-26: -29k on 59), win 34 %, t 0.58, and lose
  Rs 1.01 lakh without KALYANKJIL. With 1 tick each side they make +Rs 29k (t 0.95). Under Rs 1 they lose in every
  split. For comparison the >= Rs 2 set under the same tick model makes +Rs 67k (2022-24) and +Rs 1.88 lakh (2025-26).
- Live shadow entry (`server/fade.py`): when a signal is refused only by the Rs 2 floor ("premium below Rs 2" or "never
  fits"), the same walk runs with the floor at one tick. A strike it finds becomes a shadow entry at its ask, kept in
  `rules.fade_shadow_entries`, tracked each poll and netted at the 15:20 bid. `/api/paper/summary` → `fade_subfloor`, and
  the Arm F panel "Shadow entries: sub-₹2 refusals". Judged at 30 closed. The real exit and the +100 % shadow exit
  are untouched. 7 new tests in `tests/test_fade.py`.

### 2026-10-19: nightly 19:30 job saves more data
- From 2026-10-19 the 19:30 GitHub job also saves: each S1 paper trade's 1-minute stock and option candles (the last 7
  days each night); index spot / VIX 1-minute and NSE daily OHLC top-ups; and, on Fridays, a weekly Upstox
  expired-contract top-up.
- The 870 S1 backtest day-0 stock 1-minute files (`data/cache/intraday/*.json`, git-ignored on main) are now on the
  `index-data` branch under `data/index/s1_backtest_intraday/` (`ea6f543`).
- The code was pushed during market hours with `[skip render]`; Render confirmed not redeployed.

### 2026-10-19: Rs 0.50-1 band, +20 % target with a trailing stop on 1-minute data (fails)
- Pre-registered: `strategies/S1_v10_band050_trail.md`. The sample is every 2025-26 fade signal's strike nearest the
  money priced Rs 0.50-1, with >= 50 contracts and a lot of Rs 600-8,000: 147 contracts.
- Minute candles: Upstox expired-instruments covers stock options from the Oct 2024 expiries
  (`index_data/probe_stock_expired.py`). They are fetched on GitHub by the manual `stock-options-probe` workflow
  (`script=fetch_band_minutes`), an artifact that is not committed. 142 of 147 fetched. The minute open and high match
  the bhavcopy on 99 % of contracts.
- `python -m scanner.fade_band050 run` → `data/results/S1_v10_band050_trail.md`. 124 trades simulated (18 had no trade
  by 09:20). Chosen on 2025: R10 (10 % trail), the "best" at -Rs 37k. **2026 test: R10 -Rs 36,802 on 58 trades (mean
  -24.8 %, win 12 %), so it fails.** The 15:20 baseline is worse (-Rs 58k). Every variant loses in both years; stops
  close 65-88 % of trades. Crossing the spread costs about Rs 0.25 on a Rs 0.89 average entry. Per the
  pre-registration, the Rs 1-2 step is not run on this rule.

### 2026-10-19: Rs 0.50-1 band, +100 % variants (fails)
- Addendum 2 of `strategies/S1_v10_band050_trail.md`: A = +100 % target with a 10/20/30 % trailing stop before it;
  B = no stop until +100 %, then a 10/20/30 % trail from the peak. `python -m scanner.fade_band050 run100` →
  `data/results/S1_v10_band050_t100.md`.
- Chosen on 2025: B30 (+Rs 1,293 on 66 trades, the only non-negative variant; 20 % of trades reached +100 %).
  **2026 test: B30 -Rs 56,321 on 58 trades (win 12 %), so it fails.** Only 5 % reached +100 % in 2026. Every A variant
  loses in both years; their stops close 83-100 % of trades. The +20 % test reproduces exactly after the refactor.

### 2026-10-19: audit of the "everything fails" sub-Rs 2 results + "never fits" subset
- **Audit (user: "there is a data or entry problem, check it twice").** The minute data is sound: entry bars all have
  trades, no-trade minutes repeat the last price, and the open and high match the bhavcopy on 99 %. Two real issues:
  - **The tick for cheap stock options is Rs 0.01 since about 2025-11-07.** Sub-Rs 2 prices are all on the Rs 0.05
    grid up to 2025-10-30 and 19-31 % are off it after. The ±2 ticks of Rs 0.05 cost overstates the spread from then
    on.
  - **The Rs 0.50-1 minute trades roughly break even before costs** (-Rs 11k on 124 trades, -0.6 % a trade). The
    assumed Rs 0.10 each side alone makes it about -Rs 81k. The opening-minute spike costs about Rs 3k more than the
    open. Buying later (09:30 / 10:00 / 11:00) is worse.
- **"Never fits" subset** (addendum 2 of `strategies/S1_v10_subfloor_entry.md`; user: trade sub-Rs 2 only when no
  Rs 2+ option fits Rs 600-8,000). `python -m scanner.fade_subfloor_neverfits` → `data/results/S1_v10_subfloor_neverfits.md`.
  Existing backtest costs:
  - Primary (2 × lot > 8,000): 105 trades, 2022-24 +Rs 14k, 2025-26 -Rs 62k, together -Rs 48k (t -0.7), so it **fails**.
  - Secondary (the walk passed a dear Rs 2+ strike): 112 trades, +Rs 32k (t 0.98) but -Rs 16k without KALYANKJIL, so
    it **fails**.

### Known issues
- **Render free tier sleeps** after 15 minutes without visits: on 2026-10-16 the ledger was last saved at 11:21, the
  server came back only after 16:00, and the eight fade positions were not sold at 15:20 (they sell at the first poll
  of 19 Oct, per `server/fade.py`). Fixed from 19 Oct by the keep-awake workflow; GitHub may start scheduled runs
  late or skip one, so an external pinger (e.g. cron-job.org, every 5 min, 08:30–15:45 IST) or the guide-17 VM is
  the stronger fix. (Decided 2026-10-17: the eight are closed on Monday and stay out of the v10 review.)
- `paper-state` gets repeated `live_snapshots/*` commits of the same files on every restart (16 Oct 16:17, 16:53;
  17 Oct 00:10, 09:12).
- HCLTECH (arm A, 14 Oct), checked 2026-10-19. The forward test holds it (1350 CE at the day's VWAP ₹18.35 × 400 =
  ₹7,340, after walking 2 strikes up); the paper account never bought it, for two reasons:
  1. **Open entry:** refused at 09:15 by the old one-strike rule. The 1330 CE cost ₹14,440 a lot. The strike walk
     went live at 13:35 that day, but a refusal is final for the day.
  2. **Close entry:** never ran. The ledger's last save that day was 13:41 and `exits_checked` stayed empty. The
     server restarted only at 15:37, after the close (Render free-tier sleep, fixed from 19 Oct by keep-awake). The
     same sleep made the 15 Oct "open" entry of TATAELXSI fill at 15:17, not 09:15.
  - No back-dated trade is added: the paper account records only what it really did.

## Next
1. Check on Mon 19 Oct that the keep-awake runs (08:30), the 8 carried fade positions sell at the first poll (09:15), and the
   new day's fade trades (FEDERALBNK PE, UJJIVANSFB PE) sell at 15:20. Then the always-on VM (guide 17) or an external
   pinger as a second layer.
2. Renew `LEDGER_GITHUB_TOKEN` before 2026-10-30.
3. S2: run screen B in the pre-registered order (cache parents → freeze financials → recount → screens).
4. S1: keep the paper runs untouched; review v10 at 30 closed trades / 6 weeks.
