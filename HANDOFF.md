# Handoff (2026-10-27, 09:00 IST)

Repo: `sherwingm/project-f-0` (**public**, kept so by the user: free Actions minutes, Pages, token-free raw files;
never commit secrets), local clone `C:\Users\sherw\project-f-0`. Records: `PROGRESS.md`, `DECISIONS.md` (rule and
result changes), `INDEX_DATA_REPORT.md`, `DATA_ACCESS_AUDIT.md`, `STRATEGY_AUDIT.md`.

## House rules
- **S1 and S2 stay separate.** Commit and push every step, and log it in PROGRESS.md. A rule or result change goes
  into DECISIONS.md in its own commit. Write a study's method in `strategies/*.md` and commit it **before** any number.
- **The live server is the AWS VM.** Deploy yourself (the user wants that), **never 09:00-15:40 IST on weekdays**:
  `ssh -o BatchMode=yes fo-scanner` (direct key login) **or** `"C:/Program Files/Tailscale/tailscale.exe" ssh ubuntu@ip-172-26-4-64
  'bash -s' < script.sh` (the user set Tailscale SSH to `accept` on 26 Oct: no approval any more; the AWS console login and
  the Lightsail browser terminal are NOT needed), then `cd ~/fo_scanner && git pull && sudo systemctl restart fo-scanner`,
  guarded by a market-hours check on the VM's own clock (reuse the 26 Oct deploy script pattern: guard, ledger counts
  before/after, strategy constants, restart, `is-active`, errors, commit, page 200, `PAPER=true`).
  After: `systemctl is-active`, 0 errors in `journalctl -u fo-scanner --since -60s`, `/api/paper/summary` ->
  `version.commit` = the pushed commit. Fallback: the Lightsail browser terminal via Claude in Chrome (its AWS session
  expires; never type into the sign-in page). Render is a mirror only, so `[skip render]` no longer matters for trading.
- **Excel files must be readable on first open:** use the `xlsx` skill (LibreOffice installed 23 Oct for recalc);
  plain-word headers, widths, Rs `#,##0`, % one decimal, frozen top row, filters, a Summary sheet first.
- **The user reads on a phone.** Plain words; send files with SendUserFile; end replies with a **"Still running"** list.
- **Secrets** stay in the VM's `.env`, Render and GitHub secrets, never in chat or the repo. The user rotated the GitHub
  token and the site password on 23 Oct after a screenshot showed them.
- **Another Claude session works in the same folder** (S3 index options, other templates). Commit only your own files,
  check the staged diff is yours (it has left colour edits in `templates/*.html` unstaged), pull with `--autostash`.
- **No multi-agent workflows** unless the user asks by name. **No ML** until the user decides (descriptive first).

## Live system: AWS Lightsail Mumbai VM, commit `25669145` (deployed Mon 26 Oct 22:49)
- **Pushed 27 Oct, NOT deployed yet:** `bd8ae35f`, the **scan watcher** (`_scan_watch_once`): while the next session's lists are
  not on the server it pulls `SCAN_URL` every 10 min outside 09:15-15:45 and reloads only what changed. Deploy it **after
  15:45 on 27 Oct**, guarded.
- **27 Oct plan (loaded by the 08:40 pull):** fade APLAPOLLO, MANKIND, MAHABANK, RECLTD, TATACONSUM, SONACOMS, PAYTM;
  Arm A COFORGE, DRREDDY, JSWSTEEL, SHREECEM; Arm B none.
- **Telegram plan alerts** (`server/plan_alert.py`, live 26 Oct): "List for <day> is ready" once when the next session's lists
  land; at **09:08** the plan, or "No full list for <day>" naming the stale list; "arrived after the open" if a missing
  list lands 09:15-15:00. A list for another day is never shown as the plan.
- **`server/autoupdate.py` is untracked and NOT wired in** (a self-updating server: pulls `main` after 15:45 and restarts). The
  permission check blocked wiring it on 26 Oct, and it runs whatever lands on `main` while the VM holds a token that can write
  there, so it needs the user's explicit OK (safer: only tagged or signed commits). Never `git add -A` it by accident.
- **Phone alerts by Telegram** (`server/alerts.py`, bot token + chat id in the VM `.env` since 24 Oct): fills, unfilled
  buys, stuck sells, stream lost/back, errors, restarts, the day's result after 15:31. Live vs backtest per trade:
  `python -m scanner.fade_live_vs_backtest data <date>`.
- **Paper rule trades fill as real orders from Mon 26 Oct** (`strategies/S1_paper_real_order_fills.md`,
  `server/order_sim.py`): buy = limit at ask + Kotak protection, filled from the next quote only if the lot fits,
  cancelled after 60 s; sell chases the bid each second; A/B 15:20 entry at the real ask. `closed.instant` keeps the
  old instant-fill net, `fill_cost_rs` the gap. `PAPER_REAL_ORDERS=false` turns it off. Monday: check the first
  fills (`order` area in `fade_live_validate`).
- `fo-scanner`, static IP 3.109.99.56, `~/fo_scanner`, systemd `fo-scanner` + market-hours watchdog (`deploy/aws/`,
  guide 17). `.env`: `DATA_PROVIDER=kotak`, `ORDERS=true PAPER=true BROKER=none`, `PUBLIC_ACCESS=false` + `APP_PASSWORD`,
  `LEDGER_GITHUB_TOKEN` (writes `paper-state`), `UPSTOX_ANALYTICS_TOKEN`.
- **Site:** `https://ip-172-26-4-64.tail956abb.ts.net/` (Tailscale Funnel, public HTTPS), themed `/login` page with a
  1-year cookie; Basic auth still works for scripts.
- **Prices: the Upstox WebSocket** (`server/upstox_stream.py`, ~848 keys, `full` mode), **Kotak automatic fallback** if
  no message for 15 s. While streaming: feed, A/B entries, fade entries and exits every **1 s**; on Kotak only, 30 s.
  PCR from the Kotak chain sweep (4 stocks / 10 s). `/api/live` -> `stream`, `interval_s`.
- **Fade entry every second from 09:15:00** (`entry_tick`); **1-second exit check** (`fast_tick`).
- **No loss halts** (weekly removed 21 Oct, daily 22 Oct).
- **Entry probe** (record only): asks every second 09:14:50-09:20 (10 s to 10:00) for fade signals' strikes, in
  `paper-state:data/entry_probe/<date>.json` (`strategies/S1_v11_entry_probe.md`).
- **Deploy route (26 Oct):** the user set Tailscale SSH to `accept`, so `tailscale ssh ubuntu@ip-172-26-4-64` works from the PC with no
  approval; the page fix (dd3dae0b) was deployed that way, after 15:40, and the ledger was identical before and after (21 closed, 2 open).
- **26 Oct stale list (fixed, live 26 Oct 22:49):** Friday's nightly scan built everything but its final `git push` lost a race
  with two index-data pushes, so no Monday list existed (same on 21 Oct). daily / fade-morning / retrain now pull-rebase and
  retry 5x (**proved**: the 26 Oct build ran 20:11 UTC and pushed 20:21 UTC = 01:51 IST). The page hides an Arm A/B list that
  is not for today (`forward.for_today`, `server.rules.forward_is_current`). The trader itself was right: it ignores a list
  from another session.
- **List timing:** GitHub's 20:30 IST schedule really runs ~00:15-02:00 IST; the server pulls the scan at 08:40, 09:05, 21:00
  and 22:00 IST (plus the watcher above once deployed), so overnight lists reach it at 08:40 at the latest.
- **Sellable-peak measurement** (`server/peak.py`, measurement only):
  - `held_bid`: highest / lowest best bid while held, with times, bid size, quote count, longest gap;
  - `peak_capture` at the exit: net if sold at the peak bid (an estimate; `lot_fits_at_peak`), Rs left, capture %
    (N/A when the peak never paid), price give-back;
  - `entry_quote`: bid, ask, spread, sizes, `ltt` + `ltt_age_s` + `stale_ltt` (last trade before 09:15 or > 5 min old;
    a warning only, it never refuses a trade);
  - `data/observations/<date>.jsonl`: every bid/ask change while held, plus **60 min after the exit** (phase
    `after_exit`, 1 s streaming / 30 s on Kotak, fetched in one batched call outside the ledger lock); mirrored to
    `paper-state` once the day is over;
  - exits priced from the last trade (no bid) are not counted as bid observations;
  - **0 measured trades so far**: the first come Mon 26 Oct.
- `/api/paper/summary` -> `version` = `{commit, commit_source}` from the server's `.git` (`server/version.py`).

### Strategy state (S1 v12, unchanged)
- **Fade (arm F), v12** (`strategies/S1_v12_fade_trail2.md`): v10 entry (strong numbers -> put, weak -> call; Rs 2 floor;
  lot Rs 600-8,000; spread <= 10 %; buys the ask); on the best bid: -20 % stop from 09:16; trail on at >= 1.10 x entry,
  sells at <= 0.98 x the highest bid since; else 15:20.
- **Below-Rs 2 rule** (`strategies/S1_v12_sub2_listing.md`): a signal refused only by the Rs 2 floor is bought at the
  first two-sided strike if its listing-day price was Rs 2-7, max lots <= Rs 8,000; exit v12. Listing prices in
  `data/listing/<expiry>.csv`.
- **Shadows on every v12 trade:** `shadow_v11`, `shadow_v10`, `shadow_trail` (5 %), `shadow_t100`, `shadow_np25`,
  `shadow_fd2`. Review **v12 vs v11/v10 at 30 closed v12 trades**.
- **Arms A / B:** open walk and 15:20 entries; skip ban stocks. **Known gap, confirmed 24 Oct:** the 15:20 "close" entry
  books the day's average price, not a 15:20 price (all 4 checked fills were outside the 15:20 candle). A fix is a rule
  change for the user to decide.

## S1 strategy work (records: PROGRESS.md, DECISIONS.md, `strategies/`, `data/results/`)
**Practice:** write the rule in `strategies/*.md` and commit **before** any number; rule changes need the user's
decision + a DECISIONS.md entry. **Do not run multi-agent workflows unless the user explicitly asks by name** (the user
was unhappy about the token cost of the 21–22 Oct workflows). Keep replies short and plain.

### Key findings (all realistic entry = 09:16 candle open + 1 tick; Oct 2024 – Aug 2026)
- **The old backtest entry (09:15:00 opening print) was unrealistic** (often a stale print; a third never traded again
  that day). v11 +₹3.23 L → **+₹0.66 L** (t 0.9) on the realistic entry. Live bot buys ~09:15:45 at the ask (checked on
  16 Oct trades: half within 7 % of the open print, half 18–41 % off).
- **Exits (live set B ≥ ₹2, 339 trades):** v12 +2.86 % a trade (t 1.79, win 55 %) is the best. v11 +2.2 %, v10 +3.2 % /
  +3.9 % on other cuts but neither proven. Failed: wider stops, 1-min wait, re-entry, negative/step-down trails, looser
  gaps (3–30 %), a gap that widens past +40 % (verified), and the **peak-pattern study** (learn on train, freeze, test
  once: all 5 rules lost to v12 on Nov 2025 – Aug 2026; v12 +3.20 %). Peaks are real (winners ~+100 %) but cannot be
  recognised live. Reports: `S1_fade_stop_trail.md`, `S1_fade_trail20_grid.md`, `S1_fade_negative_trail.md`,
  `S1_fade_trail_gap_loosen.csv`, `S1_fade_trail_tiered.md`, `S1_fade_peak_patterns.md`, `S1_fade_peak_rules_test.md`.
- **Pre-open:** stock options have no pre-open (NSE/FAOP/71092); a fair-price limit fails; the stock in its auction is a
  first-minute effect only. `S1_fade_preopen_entry.md`.
- **Peak capture and entry quality (23-24 Oct, descriptive; candle estimates):** `S1_fade_entry_quality_audit.md/.xlsx`,
  `S1_v12_measurement_audit.md`, `S1_fade_decline_recovery_report.md/.xlsx` (protocols in `strategies/`).
  - 102 of 152 losers never rose +2 % (Rs 1.32 L of Rs 1.74 L lost): the weakness is entry/direction, not the exit.
  - At entry the never-profitable losers look like the winners (premium, strike distance, expiry, gap, NP YoY: no
    difference); the stock running on with the headline (open -> close, retrospective) is the main post-entry cause.
  - The >= Rs 15 premium edge is not robust (1st half worse; bootstrap CI includes 0). Strike distance: no link (11 rows
    with split-adjusted stock prices excluded).
  - After the -20 % stop (136 trades): 56 % touch entry again later (median ~22 min), 24 % close above it.
  - Paper entry check (23 positions): 11 inside the minute's traded range, 8 outside (incl. all 4 15:20 close
    entries), 4 unresolved. ADANIENSOL 23 Oct was bought at Rs 10.55 on a book whose last trade was the previous day.
- **Below ₹2:** buying refused signals anyway loses (−4.4 %); expiry-gap filters don't fix it; **listing price ₹2–7 with
  max lots** is the best cut (+2.3 % v12, +5.8 % v11; 71 % of trades reach +20 %), now live; **listed under ₹2 loses with
  every exit**. `S1_refused_listing_price.md/.xlsx`, `S1_fade_cheap_dte.md`, `S1_refused_below_floor_all.xlsx`,
  `S1_refused_below_floor_3months.xlsx`, `S1_fade_oct27_contract_history.xlsx`.
- Explanation doc for the user: https://claude.ai/artifact/57eiLHEierozKUxdFdSxkE ("S1 Fade Study: What We Learned"; not
  yet updated with the exit / peak / below-₹2 work).

### Tools
- Option minutes (gitignored, local): `data/results/S1_v10_{bandv10,band12,band12q4,band050,band050q4}_minutes.csv`;
  re-fetch with the `stock-options-probe` workflow. Daily NSE option prices: `data/cache/fo_prices_*.csv` (fetched Apr–Oct
  2026), `fo_bhavcopy_*.csv` (to 2026-09-25).
- Python with openpyxl / pytest: `C:\Users\sherw\.venvs\fo\Scripts\python.exe` (moved 2026-10-26: %TEMP% was cleared). Tests: all pass except the known
  `test_spec12_step7_model.py::test_infer_for_scan_adds_the_model_block`.
- Backtests need `EVENTS_DB=$TEMP/fo-seed/events.sqlite`. Print ASCII on the Windows console (`PYTHONIOENCODING=utf-8`).

## S3 index options, NIFTY first (a separate chat; DECISIONS.md "S3 · index options", 2026-10-22)
- Research and backtest only: no S3 paper or live trade until a pod passes its gate and holdout and the user agrees.
  Selling options is outside "Long options only" for any trading use.
- **Split:** test 2024-10 → 2025-09; holdout 2025-10 → latest, once per pod. **The NIFTY holdout option returns are still
  unseen.** Expiry-afternoon spot work stops at 2025-09-30 (part of the holdout's spot has been seen in descriptive
  tables; DECISIONS 2026-10-23).
- **Data:** a sparse checkout of `index-data` at `C:\Users\sherw\fo-index-data` (NIFTY options; NIFTY / BANKNIFTY /
  SENSEX / VIX spot; NIFTY + BANKNIFTY daily). Run with `INDEX_STORE=C:/Users/sherw/fo-index-data/data/index`. Refresh
  with `git -C ../fo-index-data pull`.
- **Code:**
  - `index_data/load.py`: read side, merge rule, lot by contract, VIX rescale;
  - `scanner/s3_engine.py`: multi-leg, multi-day, stops / targets / trail, vectorised;
  - `scanner/s3_pods.py`: the shared runner, gate and report. It writes the page commit and refuses an uncommitted page;
  - pod runners `s3_p1 … s3_p7`, `s3_r1`; diagnostics `s3_diagnostics`, `s3_diag2`, `s3_d3_d5`, `s3_d6_d7`;
  - `s3_regime.py`: ADX, EMA, delta.
- **Verdicts (DECISIONS "S3 pods" + "re-run with the review fixes"), all closed:**

  | Pod | Result |
  |---|---|
  | P1 expiry fly | −4.0 % |
  | P2 long last-40-min straddle | −34.8 %, t −3.1 |
  | P2s short fly | −7.9 % |
  | P3 1-3 DTE condor | −12.2 % |
  | P4 ORB long | −3.6 % |
  | P5 VIX-spike condor | untestable: 15 spikes in 2008-26 |
  | P6 naked late straddle | +15.2 %, t 1.77; fails t, halves and worst day |
  | P7 late fly, 5 lots | +14.8 %, t 1.59; fails the same |
- **Findings (descriptive):**
  - **Late-expiry premium:** the edge is expiry-day only (D3 placebo −1.7 %, t −3.3). On 2021-24 expiry days a VIX
    proxy says the late short straddle averaged −28 % of the credit (D4), so the test year was calm. Not reopened on
    the holdout;
  - **Plain short vol loses:** the weekly ATM straddle −7.2 % (2021-24, D6). Put-writes win small for years, then one
    month costs 7.5x the credit;
  - **VIX regime:** VIX exceeds the next week's RV everywhere except VIX > 22 and rising (D7);
  - **Expiry calendar:** BANKNIFTY's Wednesday got calmer after losing its weekly expiry (DiD 0.39x). The BANKNIFTY
    expiry last half hour reverses the day (t −2.8). NIFTY's Thu → Tue change and SENSEX are unresolved.
- **The review (23 Oct)** found 10 issues, all fixed or recorded; none flipped a verdict. About 420 looks at the NIFTY
  test window so far: re-mining it is not useful.
- **Next:**
  - **R1, the SENSEX replication: done 26 Oct, does not replicate.** Both sides lose on SENSEX expiry afternoons
    (`data/results/S3_R1_summary.md`). The late-expiry short-premium idea is closed. SENSEX options are now in the
    sparse checkout.
  - **Paid 2018 → data (the user asked, 25 Oct):** a Telegram seller of "GDFL" data (OptionVault repo, ₹18k for
    everything). My advice: get a free January 2025 NIFTY options sample first and check it against our data before
    paying. Licence and quality risk; its public sample is mislabelled. The free alternative: extend the NSE daily
    bhavcopy back to 2018 (the user has not chosen yet).
  - Open, low priority:
    - the CBOE VIX → India VIX link (needs a download, so the user's OK);
    - max pain from the full bhavcopy OI;
    - the 2024-12-26 expiry and the quarterly round-strike gaps in the store.

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
- **Tue 27 Oct, before 09:15:** the **09:08 Telegram plan** should arrive (not yet seen sent); trades start 09:15 (11 planned).
- **After Tue 27 Oct's close (after 15:45):** deploy `bd8ae35f` (guarded); then `python -m scanner.fade_live_validate` on the
  first measured trades (no trade was measured on 26 Oct: no list that day; entry quote and stale flag, held peak/low,
  exit bid, 60-min post-exit rows, backup); `python -m scanner.fade_live_checkpoint` (target 30 measured trades); the
  first real-order fills; the entry probe's A / B / C verdicts. Check that tonight's build ran and pushed.
- Review v12 vs v11/v10 at 30 closed v12 trades; the below-Rs 2 rule's live trades as they come.
- Hypotheses for live data (no rule change without the user): recovery after the stop on real bids; stale first-second
  entries; entry spread vs the 2 % trail gap and early bid moves.
- **A/B catch-up** for a missed 15:20 check; **A/B "close" entry at the 15:20 ask** (rule change).
- The new `LEDGER_GITHUB_TOKEN` on the VM: check its expiry date (the old one ended 2026-10-30).
- Clean the `index-data` history when the repo passes ~3 GB.

## After a context compaction
- Read this file first, then the tail of `PROGRESS.md`.
- This chat is a fork of "rem works in fade", renamed "S1 fade live fixes 26 Oct" (the desktop app nests forks under their parent;
  `claude://claude.ai/epitaxy/local_7712e1b3-d385-48bb-a87b-25789c0bada8` opens it). The user's mods `live-trades` (a paper-account
  pane) and `pet-crab` are in `C:/Users/sherw/.claude/dev-mods/7712e1b3-d385-48bb-a87b-25789c0bada8/`; they only draw in a terminal
  Claude Code >= 2.1.308 (`claude` on the PATH is 2.1.96; the desktop app shows no mod panes).
- `gh` is at `C:/Program Files/GitHub CLI/gh.exe`. Python: `C:\Users\sherw\.venvs\fo\Scripts\python.exe` (tests: all pass
  except `test_spec12_step7_model.py::test_infer_for_scan_adds_the_model_block`).
- Claude Code plugins on this PC (user scope): `skin-code` and `skins` (a custom "trader" skin is applied).
- Stray untracked files from other sessions (`calib_cash.csv`, `fills_mech.csv`, `data/cache/s2_expiries_*.txt`): not ours.
