# Handoff (2026-10-20, 22:30 IST)

Repo: `sherwingm/project-f-0`, local clone `C:\Users\sherw\project-f-0`. The detailed records are in `PROGRESS.md`
(log and the Core idea tracker), `DECISIONS.md` (rule and result changes), `INDEX_DATA_REPORT.md`,
`DATA_ACCESS_AUDIT.md` (it has the Upstox vs Kotak comparison) and `STRATEGY_AUDIT.md`.

## House rules
- **S1 and S2 stay separate.** Commit and push every step, and log it in PROGRESS.md. A rule or result change goes
  into DECISIONS.md in its own commit.
- **During market hours (09:15-15:30 IST), do not redeploy Render**: it restarts the live paper trader.
  - Changes under `data/index/**`, `index_data/**`, `**/*.md` and the data files listed in `render.yaml` are safe.
  - Anything else needs **`[skip render]`** in the commit message, as the only commit in the push. Afterwards, check
    `/api/paper/summary` → `version.commit` is unchanged.
- **To deploy, the commit must change a watched file.** An empty commit is skipped by Render (this happened at 15:35
  on 19 Oct). Use `DEPLOY_STAMP`.
- **The user reads on a phone.** Use plain words and send files with SendUserFile. End every reply with a
  **"Still running"** list.
- **Secrets stay in Render and GitHub secrets** (`KOTAK_CONSUMER_KEY`, `UPSTOX_ANALYTICS_TOKEN`, `APP_PASSWORD`,
  `LEDGER_GITHUB_TOKEN`, which needs renewing before 2026-10-30), never in chat or the repo.
- **Another Claude session works in the same folder** (S1 v10 / v11 studies, `stock-options-probe`). Commit only your own
  files (`git add <paths>`) and pull with `--autostash`.

## Live system (Render, fo-scanner.onrender.com), deployed `e0788d9` or later
- **S1 v11 fade (arm F), live from 21 Oct:** the v10 entry with a −20 % stop (details in "S1 strategy work" below).
- **Arms A / B:** rule trades, each bought at the open walk and at 15:20. From 21 Oct they skip an F&O-ban stock.
- **Entry walk** (Arm A/B open entry and the fade):
  - retried every **30 s**: DECISIONS.md 2026-10-20, from 21 Oct; the v10 review splits trades before and after;
  - the **lot-range check** refuses a never-fit stock at once (lot > 4,000 shares → no strike can cost ≤ ₹8,000 at ≥ ₹2);
  - all strikes are priced in **one quote call**;
  - the waiting reason is shown (`rules.open_wait`, the Paper tab's "Not bought today", the Arm A/B "Paper today"
    column).
- **Data source:** Kotak. **Upstox is built in** (`server/upstox.py`: full quotes with depth, `quote_one` / `quote_many`,
  futures, history). A shadow check (`server/provider_compare.py`, `/api/data/compare`) compares the two every 5
  minutes of a session, 09:20-15:25. **First rounds: 21 Oct.** Switch (`DATA_PROVIDER=upstox`) only after a few clean
  days, after market, with a DECISIONS.md entry.

## S1 strategy work (this session; records in PROGRESS.md, DECISIONS.md, `strategies/`, `data/results/`)
**Rules of the practice:** write the rule in `strategies/*.md` and commit it **before** any number is computed; a rule
change needs the user's decision and a DECISIONS.md entry; reports are numbers only. Big results were checked by an
independent verification workflow (recompute, bias audit, robustness), which caught real slips each time.

### Done 20 Oct: the backtest entry price was stale; re-run with a realistic entry (nothing live changed)
- The fade backtests bought at the day-0 opening print (bhavcopy open + 1 tick), often stale (median swing inside the
  09:15 minute 51 %; BAJFINANCE 2024-10-23: bought 54.45, 09:15 low 7.15). The live bot buys at the live ask, so it is
  not exposed.
- Re-run with **entry B = the 09:16 candle's open + 1 tick** (pre-registered: `strategies/S1_fade_realistic_entry.md`,
  `S1_fade_realistic_entry_studies.md`; scripts `scanner/fade_realistic_entry.py`, `fade_realistic_studies.py`; reports
  `data/results/S1_fade_realistic_entry.md`, `S1_fade_realistic_studies.md`). Oct 2024 – Sep 2026 only (no option minutes
  before that; 2022-24 daily-data parts cannot be re-priced).
- **v11, ₹2+ set, 409 trades:** old +13.8 % a trade (+₹3.23 L, t 3.0) → new **+2.5 % (+₹0.66 L, t 0.9)**. v10: +12.7 % →
  +3.2 %. The −30 %…−85 % losers and the +690 % winners were mostly the stale-print artefact.
- **Floor ₹2 / ₹1 / ₹0.5 (v11):** +2.2 % / +0.6 % / −2.2 %, all t < 1. **Band ₹0.5–1:** −17 % a trade (t −4.1), the one
  clear signal (the live floor is already ₹2). **Targets** (+25…+200 %, with/without stop): all ≈ 0, none beats plain v11.
  **Arm-A filter:** still fails (dropped trades +19 % then −6 %, t 0.6).
- So the fade's backtest edge is **not established**; every earlier backtest total/study built on the old entry is
  unreliable. The live paper run (real asks) and the shadow reviews are the real test. No rule change was made; any
  change is the user's decision.

### The live fade (S1 v11, from 21 Oct, `strategies/S1_v11_fade_stop20.md`)
- v10's entry unchanged (strong numbers → put, weak → call; ₹2 floor; ₹600–8,000 lot; live ask 09:15–15:20; retried
  every 30 s). **Exit:** from **09:16** the first poll whose best bid ≤ 0.80 × entry sells at that bid (`fade_stop`),
  else the 15:20 bid. v10 (hold to 15:20) is the shadow (`rule.shadow_v10`). Review at 30 closed v11 trades: if v10 beats
  v11 (mean difference > 0, t ≥ 2) ask the user whether to switch back.
- **Day 0 = 21 Oct.** The Arm F scoreboard and Paper tab count v11 only; the 10 v10 trades (15–19 Oct, −₹16k) are a
  collapsed side record (equity still includes them). **21 Oct list:** UNIONBANK, HINDZINC, BAJFINANCE (all puts).
- **Shadow tags (never change a trade):**
  - `shadow_np25` (judged at 40 left-out puts); `shadow_t100` (+100 % target, 30); sub-₹2 shadow entries (30);
  - **`shadow_fd2` (new, puts only):** the results were filed 09:15–14:50 on the session before day 0 and the stock already
    fell ≥ 2 % (market-adjusted) by that day's 15:29 close. The user chose a tag, not a skip. **Review at 20 closed tagged
    puts** (about 5 a year in the backtest, so years). Rule: `strategies/S1_v11_fd2_shadow_track.md`. D is measured by
    `python -m scanner.fade_live --fd2`, run as its own step in **its own venv** (`kotakneoapi` needs pandas < 3) in
    `daily.yml` and `fade-morning.yml` (skipped after 08:35 IST), using the Kotak consumer key. It writes `filing_day` onto
    each signal in `data/forward/fade.json`; `server/fade.py` copies it to the position; `/api/paper/summary` →
    `fade_fd2`; the Arm F panel shows it. First run (manual, 20 Oct): UNIONBANK D +2.8 %, not tagged; HINDZINC and
    BAJFINANCE filed after the close.
  - `fade.json` also carries the session's F&O **ban list** (`ban`), which `server/rules.py` uses to refuse A/B entries.
- **Fixes shipped 20 Oct** (DECISIONS.md): tick ₹0.01 in `server/rules.py` and `server/fade.py` (NSE stock-option tick
  since 2025-11-03; manual orders keep `FILL_TICK` 0.05); A/B ban check; v11 texts on the page; the morning job is 07:17 IST.
- **Kill switch** blocks manual paper orders only, never rule trades (A, B, F). The weekly halt clears Mon 26 Oct.

### Arms A / B
6 open (TATAELXSI, TECHM, WIPRO × 2 arms). The fade's −20 % stop does not help them (`S1_arms_ab_stop20.md`). Known gaps:
no catch-up if the server misses a 15:20 check; the "close" entry books the day's average price + 1 tick (not tradable).

### Studies finished 19–20 Oct (all descriptive; none changed a rule except v11). **Their backtest numbers used the stale entry; the floor/band/target/filter ones were re-run (see above): nothing survives.**
| Study | Result |
|---|---|
| Premium floor, bands ₹0.5–1 and ₹1–2, targets, sub-₹2 entries (`S1_v10_*`) | Nothing passes; ₹2 floor stays |
| −20 % stop on minutes (`S1_v10_s20_minutes.md`) | Basis of v11 (+₹2.51 L vs +₹1.70 L; see the entry-price caveat) |
| Drop trades where Arm A also fires (`S1_v10_armA_overlap_filter.md`) | Fails (only hindsight works; the 09:15-open version t −0.07) |
| Market-hours filings: stock after the first 15 min (`S1_intraday_results_reaction.md`) | Fails; no pattern. The stock is flat after entry; strong results +0.79 % by the next open (t 4.0) |
| Strong market-hours result, call to next open (`S1_intraday_call_overnight.md`) | Fails: −13 % on 64 |
| Weak market-hours result already down ≥ 2 % → next-day call (`S1_weak_day_reversal.md`) | Fails (13 trades; windows disagree) |
| Skip fade trades whose market-hours filing day already moved ≥ 2 % the fade's way (`S1_fade_filing_day_skip.md`) | Passes on v10 (₹48k, puts only), worth ~₹2–7k under v11 → became the fd2 shadow tag |
| Reverse trade on those days (`S1_fade_fd2_reverse.md`) | Fails: +0.8 %, both sides lose |
| Which comes first (`S1_results_source_timing.md`, 6–19 Oct, 12 cases) | NSE first in 10; BSE ~4.5 min later; news 0–10 min after; stock moves within 0–2 min; 2 leaked early |

- Facts: tick ₹0.01 since 2025-11-03; stock 1-minute from Kotak back 5 years; expired **option** minutes only from Oct
  2024 (Upstox); no free option minutes before that. Stock minutes for 3–14 Aug 2026 end at 15:14 (14 cases unmeasured).
  R = premium paid (v10: +0.046 R a trade, t 1.6 on the backtest entry).
- Profit comes from filings **outside** market hours (+₹2.0 L on 608; market-hours filings −₹52k on 262): a lead only.
- The sheet `data/results/S1_fade_peak_dip.xlsx` (peak / dip of every fade trade) shares the entry-price caveat.

### Tools
- `stock-options-probe` workflow (manual): `fetch_band_minutes <band|v10|ab|intra>`, `fetch_results_minutes`,
  `probe_*`. Artifact `band050-minutes` (`gh run download <id> -n band050-minutes -D <dir>`). Minute CSVs are not committed.
- NIFTY 50 minutes: branch `index-data`, `data/index/spot_1m/NIFTY50/<YYYY-MM>.parquet` (`git show origin/index-data:<path>`).
- Backtests need `EVENTS_DB=$TEMP/fo-seed/events.sqlite`. Print ASCII only on the Windows console.
- Test suite: 501 pass, 1 known failure (`test_spec12_step7_model.py::test_infer_for_scan_adds_the_model_block`).

## Index data (all on GitHub; no PC or Claude app needed)
- **Complete:** expired 1-minute option candles from Upstox, with OI, Oct 2024 → Oct 2026.
  - **NIFTY:** 10,494 contracts, ~81 M rows.
  - **BANKNIFTY:** 3,248 contracts.
  - **SENSEX:** 16,906 contracts.
- **Also stored:**
  - spot / VIX 1-min, 2021 →;
  - daily option OHLC, 2021 →, **now monthly files** (split done: 27 yearly → 302 monthly, 8.0 M rows);
  - expiry calendar;
  - the Kotak recorder (from 16 Oct);
  - S1 trades' minute data.
- **Kotak vs Upstox:** 77 % identical closes, a ₹0.35 mean gap. Upstox's volume-0 candles are fillers. The merge rule
  is in INDEX_DATA_REPORT.md.
- **Kotak expired-token probe 1** (20 Oct): **retained.** Probes 2 and 3 are due 27 Oct and 19 Nov
  (`kotak-probes.yml`, catches up if the cron is late).
- **Automation:**
  - `data/index/job_queue.json` (now empty).
  - Every index-jobs and recorder run ends with `scripts/index_handoff.sh`, which starts the next queued job only if
    nothing else is queued or running. On weekdays from 19:15 IST to midnight IST it waits for the day's recorder.
  - `index-scheduler.yml` (hourly) is a backup only: **GitHub's cron is unreliable**; it fired 1 in 8 h on 20 Oct, and
    the recorder cron ran 5-7 h late.
  - A backfill that stops on its time budget re-queues itself. To add a job:
    `python -m index_data.job_queue add --job <job> "--args=<args>" --why "<why>"`, commit, push.
- Upstox job budget: 1,800 calls / 30 min at night, 1,000 in market hours; a 429 is waited out (~38 min).
- **The recorder** records the evening's session even when it starts late (before 08:00 IST → the previous day).
- Today, 20 Oct, is an NSE holiday. GitHub had not started its 19:30 recorder by 22:30; when it runs it finds no
  session.

## Open (ask the user before doing)
- Fade backtest re-run with the realistic entry is done (see the S1 section); decide whether the fade stays on at all once the shadow reviews have data.
- **A/B catch-up** for a missed 15:20 check; **A/B "close" entry at the 15:20 ask** instead of the day's average (rule change).
- **Switch to Upstox** after a few clean shadow days: read `/api/data/compare` from 21 Oct.
- **Clean the `index-data` history:** squash to one commit when the repo passes ~3 GB or every few months. It is ~1.4 GB
  now, with old copies growing ~2 MB a night since the monthly files.
- The NSE-holiday-aware daytime cap for Upstox jobs: nice to have.

## After a context compaction
- Read this file first, then the tail of `PROGRESS.md` and `INDEX_DATA_REPORT.md`.
- `gh` is at `C:/Program Files/GitHub CLI/gh.exe`. The Python venv is `%TEMP%\fo-venv\Scripts\python.exe`.
- There are no background shells or PC scripts. The three Claude-app probe tasks are disabled (moved to GitHub).
- Check after 21 Oct's session:
  - **v11 day 0:** after 09:16 the positions carry `rule.version`, `stop`, `shadow_v10`, `shadow_fd2`; after 15:20
    `shadow_v10` resolves (`done` / `same`) and the Arm F panels show both columns; whether a `fade_stop` fires at a sensible bid;
  - the A/B refusals "in the F&O ban today" (AMBUJACEM, KAYNES, SAIL are banned on 21 Oct);
  - `/api/data/compare` (shadow rounds);
  - the 30-s retries working (`rules.open_wait`, refusals with "never fits");
  - the 21 Oct recorder run in `data/index/status.json`.
