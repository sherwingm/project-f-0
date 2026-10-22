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
- **The user reads on a phone.** Use plain words and send files with SendUserFile. End every reply with a
  **"Still running"** list.
- **Secrets stay in Render and GitHub secrets** (`KOTAK_CONSUMER_KEY`, `UPSTOX_ANALYTICS_TOKEN`, `APP_PASSWORD`,
  `LEDGER_GITHUB_TOKEN`, which needs renewing before 2026-10-30), never in chat or the repo.
- **Another Claude session works in the same folder** (S1 v10 / v11 studies, `stock-options-probe`). Commit only your own
  files (`git add <paths>`) and pull with `--autostash`.

## Live system (Render, fo-scanner.onrender.com), deployed `3e7a469` (22 Oct, after market)
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
