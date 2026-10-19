# Handoff (2026-10-20, 02:50 IST)

Repo: `sherwingm/project-f-0`, local clone `C:\Users\sherw\project-f-0`. The detailed records are in `PROGRESS.md`
(log and the Core idea tracker), `DECISIONS.md` (rule and result changes), `INDEX_DATA_REPORT.md`,
`DATA_ACCESS_AUDIT.md` and `STRATEGY_AUDIT.md`.

## House rules
- **S1 and S2 stay separate.** Commit and push every step, and log it in PROGRESS.md. A rule or result change goes
  into DECISIONS.md in its own commit.
- **During market hours (09:15-15:30 IST), do not redeploy Render**: it restarts the live paper trader.
  - Changes under `data/index/**`, `index_data/**`, `**/*.md` and the data files listed in `render.yaml` are safe.
  - Anything else needs **`[skip render]`** in the commit message, as the only commit in the push. Afterwards, check
    `/api/paper/summary` → `version.commit` is unchanged.
- **The user reads on a phone.** Use plain words and send files with SendUserFile. End every reply with a
  **"Still running"** list.
- **Secrets stay in Render and GitHub secrets** (`KOTAK_CONSUMER_KEY`, `UPSTOX_ANALYTICS_TOKEN`, `APP_PASSWORD`),
  never in chat or the repo.

## Where things stand
- **S1 v10 fade (arm F):** on live paper since 2026-10-15. Review at 30 closed trades or 6 weeks.
  - **Shadow track** "puts only above NP YoY 25 %": tags only, judged after 40 left-out puts
    (`strategies/S1_v10_np25_shadow_track.md`).
  - **Diagnostics and strike-distance study:** done; no rule change.
- **S1 arms A / B:** forward paper test running.
- **S2:** screen B closed. Nothing passed. §1 / §2 could not be tested: the free futures data is unreliable.
  S2 has no strategy to trade.
- **Website** (fo-scanner.onrender.com):
  - tabs Paper / Arm A / Arm B / Arm F;
  - `/s2`;
  - new `/index` page (read-only data status).
- **Index data layer** (`INDEX_DATA_PLAN.md`, `index_data/`). Large files go on branch **`index-data`**; small JSON
  goes in `data/index/` on main.
  - **Nightly recorder** (`.github/workflows/index-recorder.yml`, 19:30 IST, GitHub, no PC needed):
    - NIFTY / SENSEX / BANKNIFTY options, 1-min;
    - contract snapshot and EOD chain;
    - from tonight also: S1 trades' stock and option 1-min, index spot / VIX and daily OHLC top-ups;
    - Fridays: the Upstox top-up.
  - **Backfilled:**
    - spot / VIX 1-min, Oct 2021 →;
    - daily OHLC of every NSE index option, 2021 →;
    - expiry calendar;
    - Upstox expired NIFTY options from Oct 2024 (31.5 M rows so far).
  - **Manual jobs:** `.github/workflows/index-jobs.yml` (`job` = `backfill_spot`, `probe_expired`, `upstox_expired`,
    `reconcile`, `expiry_calendar` or `instruments`). Only one may wait at a time: a second pending run cancels the first.

## Still running
| What | Where | Finishes | Needs the PC |
|---|---|---|---|
| `scratchpad/run_jobs5.sh` (log `run_jobs5.log`): waits until no other job uses the Upstox token, then NIFTY part 3 (`--max-minutes 180`), then SENSEX resume (300 min). BANKNIFTY is complete; SENSEX part 1 stopped on a shared-token 429 (fixed: 429s are waited out) | this PC | ~20 Oct midday | **yes** |
| Nightly recorder (+ S1 trades' minutes, spot / VIX, OHLC top-ups) | GitHub cron 19:30 IST | ~20:00 IST | no |
| Upstox-vs-Kotak shadow check on the live server (`/api/data/compare`) | Render, from 20 Oct 09:20 | a few days, then decide the switch | no |
| Expired-token probes (Kotak token 47141): 1 / 2 / 3 | Claude app tasks → `index-jobs` `probe_expired` | 20 Oct, 27 Oct, 19 Nov at 16:00 IST | Claude app open |

Done on 2026-10-19:
- Live (deploy `e2b067a` after close; the 15:35 commit was empty, so Render skipped it):
  - the open-entry waiting reason (`open_wait`);
  - the lot-size range check (refuses never-fit stocks at once);
  - one-call pricing;
  - Upstox as a live source, with the shadow check.
- Reconciliation of the two sources recorded in INDEX_DATA_REPORT.md, with a merge rule. Upstox's volume-0 candles
  are fillers.

Open questions to the user:
- Retry every 30 s instead of 2 min? It changes the fade's written rules, so it needs a DECISIONS.md entry and the
  user's yes.
- Switch `DATA_PROVIDER=upstox` after a few days of clean shadow rounds? After market, with a DECISIONS.md entry.
- Never deploy with an empty commit: Render's `buildFilter` skips it. Touch a watched file (e.g. `DEPLOY_STAMP`).

## After a context compaction
- Read this file first, then the tail of `PROGRESS.md` and `INDEX_DATA_REPORT.md`.
- **Job-sequence log:** `C:\Users\sherw\AppData\Local\Temp\claude\C--Users-sherw-project-f-0\5b842267-7121-4684-bc80-f0a9faaaf922\scratchpad\run_jobs3.log`.
  If its background shell died, check the GitHub runs (`gh run list --repo sherwingm/project-f-0`) and re-dispatch
  the remaining jobs **one at a time**, never while the 19:30 recorder is pending.
- `gh` is at `C:/Program Files/GitHub CLI/gh.exe`. The Python venv is `%TEMP%\fo-venv\Scripts\python.exe` (pandas,
  pyarrow, yfinance 1.7.0, requests, xlsxwriter).
- "Move to GitHub" (self-chaining jobs) was never answered; the PC scripts are still used.
  - **Claude cloud:** advised as **not** needed.

## Next steps
1. When the jobs finish:
   - Fill `INDEX_DATA_REPORT.md`: Upstox NIFTY part 2, BANKNIFTY, SENSEX, the reconciliation, the "what is available"
     table.
   - Check `/index` shows the coverage.
2. After tonight's recorder: check `data/index/status.json` (recorder, `s1_trades_1m`, `daily_extras`) for failures.
3. Probe results go into `INDEX_DATA_REPORT.md` → "Expired-token retention".
4. No index strategy ("pod") exists yet. One gets added only with its own pre-registered rules.
