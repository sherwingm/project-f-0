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

## Live system (Render, fo-scanner.onrender.com), deployed `d5a0fcf` or later
- **S1 v10 fade (arm F):** paper since 15 Oct, with the shadow tags (NP25, +100 % target, v11 −20 % stop).
- **Arms A / B:** rule trades, each bought at the open walk and at 15:20.
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
- **Switch to Upstox** after a few clean shadow days: read `/api/data/compare` from 21 Oct.
- **Clean the `index-data` history:** squash to one commit when the repo passes ~3 GB or every few months. It is ~1.4 GB
  now, with old copies growing ~2 MB a night since the monthly files.
- The NSE-holiday-aware daytime cap for Upstox jobs: nice to have.

## After a context compaction
- Read this file first, then the tail of `PROGRESS.md` and `INDEX_DATA_REPORT.md`.
- `gh` is at `C:/Program Files/GitHub CLI/gh.exe`. The Python venv is `%TEMP%\fo-venv\Scripts\python.exe`.
- There are no background shells or PC scripts. The three Claude-app probe tasks are disabled (moved to GitHub).
- Check after 21 Oct's session:
  - `/api/data/compare` (shadow rounds);
  - the 30-s retries working (`rules.open_wait`, refusals with "never fits");
  - the 21 Oct recorder run in `data/index/status.json`.
