# Handoff (2026-10-22, 22:15 IST)

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
- **Excel files must be readable on first open** (user, 23 Oct): use the `xlsx` skill; plain-word headers (wrapped, bold),
  columns wide enough, ₹ `#,##0` and % one decimal, frozen top row, filters, a Summary sheet first. Check before sending.
- **The user reads on a phone.** Use plain words and send files with SendUserFile. End every reply with a
  **"Still running"** list.
- **Secrets stay in Render and GitHub secrets** (`KOTAK_CONSUMER_KEY`, `UPSTOX_ANALYTICS_TOKEN`, `APP_PASSWORD`,
  `LEDGER_GITHUB_TOKEN`, which needs renewing before 2026-10-30), never in chat or the repo.
- **Another Claude session works in the same folder** (S1 v10 / v11 studies, `stock-options-probe`). Commit only your own
  files (`git add <paths>`) and pull with `--autostash`.

## Live system: AWS Lightsail Mumbai VM (from 22 Oct 18:13 IST), code `43dd806`
- **Primary = AWS** (`fo-scanner`, static IP 3.109.99.56, Ubuntu, `~/fo_scanner`, systemd `fo-scanner` + market-hours
  watchdog; `deploy/aws/`, guide 17). Phone: Tailscale `https://ip-172-26-4-64.tail956abb.ts.net/` (PUBLIC_ACCESS=true,
  no password; port 8000 closed). The VM's `.env` holds the new `LEDGER_GITHUB_TOKEN` (writes `paper-state`).
  Update: `cd ~/fo_scanner && git pull && .venv/bin/pip install -r requirements-server.txt && sudo systemctl restart fo-scanner`.
  **Render is a mirror only** (`DATA_PROVIDER=none`, no ledger token): Render deploys no longer matter for trading,
  but **a VM restart during market hours** does. The external pinger is no longer needed.
- To check on 23 Oct: the live feed on AWS in market hours (guide 17 step 8), and step 9 (NSE archives from the VM IP).
- Login: themed `/login` page, 1-year cookie (Tailscale **Funnel** = public HTTPS, no VPN needed). Updates: Claude runs
  `git pull && sudo systemctl restart fo-scanner` in the Lightsail browser SSH via Claude in Chrome (after market only).
- **Daily loss halt removed** 22 Oct (DECISIONS.md): no loss halts at all now.
- **Sellable-peak measurement** (from 23 Oct evening, `server/peak.py`, audit `data/results/S1_v12_measurement_audit.md`):
  every long-option trade keeps the highest / lowest best bid while held (`held_bid`), `peak_capture` at the exit
  (net at peak = estimate; `lot_fits_at_peak`, `max_gap_s`), `entry_quote`, and `data/observations/<date>.jsonl`
  (mirrored once the day is over; from 24 Oct also 60 min of post-exit bid/ask, phase `after_exit`, and the entry
  quote's last-trade time `entry_quote.ltt` with `ltt_age_s` / `stale_ltt` (before 09:15 or > 5 min; a warning only)).
  Validate the first measured trades: `python -m scanner.fade_live_validate`. `/api/paper/summary` → `version.commit`
  now comes from the server's .git (`server/version.py`). Checkpoint: `python -m scanner.fade_live_checkpoint` (target 30 measured trades;
  0 on 23 Oct). **The GitHub repo is PUBLIC, kept so by the user (23 Oct)**: free Actions minutes, free Pages, token-free raw
  downloads. Never commit secrets; scan before pushing data.
- **Upstox stream live** (from 23 Oct, DECISIONS.md): `server/upstox_stream.py`, prices pushed by the Upstox WebSocket,
  Kotak fallback when it is down; feed + A/B + fade retries every 1 s while streaming, 30 s on Kotak only.
  Check: `/api/live` -> `stream` (healthy, keys, streamed, served stream vs kotak) and `interval_s` = 1 in market hours.
- **Fade entry every second from 09:15:00** (from 23 Oct, user decision, DECISIONS.md): `entry_tick` in the 1-s loop, one
  quote call a second for all waiting signals; still buys at the ask with the same walk. Check on 23 Oct: fills near 09:15:0x.
- **Entry probe** (record only, from 23 Oct, `strategies/S1_v11_entry_probe.md`): asks every second 09:14:50-09:20 for the
  fade signals' strikes + the opening print, in `paper-state:data/entry_probe/<date>.json`. After each session: compute
  the pre-registered A / B / C verdicts (what entry gets v11's ₹3.23 L price); a rule needs >= 20 signals.

### Strategy state (unchanged by the move)
- **S1 fade (arm F) exit = v12** (from 22 Oct, `strategies/S1_v12_fade_trail2.md`): on the entry day, on the best bid:
  −20 % stop from 09:16; once the bid ≥ 1.10 × entry a trail sells at the first bid ≤ 0.98 × the highest bid since
  (`fade_trail`); else 15:20. Entry unchanged (v10: strong numbers → put, weak → call; ₹2 floor; ₹600–8,000 lot; live
  ask from 09:15, retried every 30 s).
- **Below-₹2 rule** (from 23 Oct, `strategies/S1_v12_sub2_listing.md`, user decision 22 Oct): a fade signal refused only
  by the ₹2 floor ("premium below Rs 2" / "never fits") is bought at the first two-sided strike (spread ≤ 10 %) if its
  **listing-day price** was **₹2 to < ₹7**, with **as many lots as cost ≤ ₹8,000**; exit v12; `rule.sub2` on the
  position; refusal reasons in `rules.fade_sub2_why`. Listing prices: `data/listing/<expiry>.csv` (`scanner/listing_prices.py`;
  backfilled 22 Oct for the 27 Oct / 23 Nov / 29 Dec series; `fade_live` adds each night's new contracts and attaches
  `signal.listing`; `daily.yml` commits `data/listing`). Fade only, not Arm A refusals.
- **1-second exit check** (`server/fade.py` `fast_tick`, `FADE_FAST_SECONDS=1`, thread in `server/app.py`): one quote call
  for today's open fade contracts, then stop / v12 trail / shadow checks. The 30 s universe poll is unchanged.
- **Shadows on every v12 trade (no orders):** `shadow_v11` (stop only), `shadow_v10` (15:20), `shadow_trail` (5 % gap),
  plus `shadow_t100`, `shadow_np25`, `shadow_fd2` (puts; review at 20). Reviews: **v12 vs v11/v10 at 30 closed v12 trades**
  (`/api/paper/summary` → `fade_v12`, Arm F panel "Live v12 vs v11 and v10"); trail tag at 30.
- **Weekly loss halt removed** (21 Oct). Daily halt 2 % stays; halts block manual orders only, never rule trades.
- **Arms A / B:** rule trades (open walk and 15:20), skip F&O-ban stocks. Known gaps: no catch-up for a missed 15:20
  check; the "close" entry books the day's average price.
- **Data:** Kotak. Upstox built in; shadow comparison `/api/data/compare` (from 21 Oct). Switch only after clean days.
- **Render free tier sleeps:** GitHub's keep-awake cron runs hours late (21 Oct: started 13:30 IST). **The user is setting
  up an external pinger** (`/api/live` every ≤ 5 min, 08:30–15:45 IST weekdays). Better host: Oracle Always Free VM
  (`guides/17-always-on-host.md`), not done.
- Page: each fade position card shows the stop / trail level; closed trades show v10 and trail shadow ₹; the why drawer
  shows both shadows.

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
- Python with openpyxl / pytest: `%TEMP%\fo-venv\Scripts\python.exe`. Tests: all pass except the known
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
  - **R1, the SENSEX replication** (pre-registered and amended before any SENSEX data was read). The SENSEX path-band
    re-fill was dispatched at 15:31 IST on 23 Oct (`upstox_expired --underlying SENSEX --max-minutes 300`; it re-queues
    itself if stopped). When `data/index/status.json` shows SENSEX `stopped: null`:
    1. `git -C ../fo-index-data sparse-checkout add /data/index/options_1m/SENSEX/` (with `MSYS_NO_PATHCONV=1`), then pull;
    2. run `python -m scanner.s3_r1`;
    3. record R1 in DECISIONS.
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
- Review v12 vs v11/v10 at 30 closed v12 trades; review the below-₹2 rule's live trades as they come.
- Update the explanation doc with the newer findings (if the user wants).
- **A/B catch-up** for a missed 15:20 check; **A/B "close" entry at the 15:20 ask** (rule change).
- **Switch to Upstox** after clean shadow days (`/api/data/compare`).
- Always-on host (Oracle VM, guide 17) if the pinger is not enough.
- `LEDGER_GITHUB_TOKEN` renewal before 2026-10-30.
- Clean the `index-data` history when the repo passes ~3 GB.

## After a context compaction
- Read this file first, then the tail of `PROGRESS.md`.
- `gh` is at `C:/Program Files/GitHub CLI/gh.exe`.
- Check after 23 Oct's session: fade positions carry `trail`, `shadow_v11`, `shadow_v10`; any `fade_trail` / `fade_stop`
  exits fire within seconds (fast_tick); a below-₹2 refusal either buys with `rule.sub2` (lots > 1) or logs a reason in
  `rules.fade_sub2_why`; `data/forward/fade.json` signals carry `listing`; the nightly job committed `data/listing`.
- Stray untracked files from verification agents in the repo root (`calib_cash.csv`, `fills_mech.csv`): not ours to commit.
