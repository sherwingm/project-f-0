# Handoff (2026-10-19, 09:35 IST)

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
| Upstox NIFTY expired backfill, part 2 (Aug 2025 → Oct 2026) | GitHub run 39194783874 | ~14:00 IST | no |
| Job sequence script: reconciliation → wait for the 19:30 recorder → Upstox BANKNIFTY → SENSEX (`scratchpad/run_jobs3.sh`, log `run_jobs3.log`) | this PC | overnight into 20 Oct | **yes** (if it dies, re-dispatch the jobs by hand, one at a time) |
| Scheduled: copy 870 S1 backtest minute files to `index-data` + PROGRESS note | Claude app task | 19 Oct 15:40 IST | Claude app open |
| Nightly recorder, first run with the additions | GitHub cron | 19 Oct ~20:00 IST | no |
| Expired-token probes (Kotak token 47141): 1 / 2 / 3 | Claude app tasks → `index-jobs` `probe_expired` | 20 Oct, 27 Oct, 19 Nov at 16:00 IST | Claude app open |

## Next steps
1. When the jobs finish:
   - Fill `INDEX_DATA_REPORT.md`: Upstox NIFTY part 2, BANKNIFTY, SENSEX, the reconciliation, the "what is available"
     table.
   - Check `/index` shows the coverage.
2. After tonight's recorder: check `data/index/status.json` (recorder, `s1_trades_1m`, `daily_extras`) for failures.
3. Probe results go into `INDEX_DATA_REPORT.md` → "Expired-token retention".
4. No index strategy ("pod") exists yet. One gets added only with its own pre-registered rules.
