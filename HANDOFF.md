# Handoff (2026-10-20, ~12:15 IST; market holiday)

Repo: `sherwingm/project-f-0`, local clone `C:\Users\sherw\project-f-0`. The detailed records are in `PROGRESS.md`
(log and the Core idea tracker), `DECISIONS.md` (rule and result changes), `INDEX_DATA_REPORT.md`,
`DATA_ACCESS_AUDIT.md` and `STRATEGY_AUDIT.md`. Two sessions work in this checkout (S1 strategy work, and the index
data layer). Pull before editing, and rebase before pushing (`git fetch origin main && git rebase origin/main`;
`git pull --rebase` once failed with "Cannot rebase onto multiple branches").

## House rules
- **S1 and S2 stay separate.** Commit and push every step, and log it in PROGRESS.md. A rule or result change goes
  into DECISIONS.md in its own commit.
- **Write the rules down before any new test** (a `strategies/*.md` file or addendum, before any number is
  computed), the user's standing practice. Live rule changes need the user's decision and a DECISIONS.md entry.
- **During market hours (09:15-15:30 IST), do not redeploy Render**: it restarts the live paper trader.
  - Changes under `data/index/**`, `index_data/**`, `**/*.md` and the data files listed in `render.yaml` are safe.
  - Anything else needs **`[skip render]`** in the commit message, as the only commit in the push. Afterwards, check
    `/api/paper/summary` → `version.commit` is unchanged.
  - Never deploy with an empty commit: Render's `buildFilter` skips it. Touch a watched file (e.g. `DEPLOY_STAMP`).
- **The user reads on a phone, often over Remote Control** (no next-step box is shown). Use plain words, short tables,
  and SendUserFile for files. End every reply with a **"Still running"** list.
- **Secrets stay in Render and GitHub secrets** (`KOTAK_CONSUMER_KEY`, `UPSTOX_ANALYTICS_TOKEN`, `APP_PASSWORD`),
  never in chat or the repo. There is no Upstox / Kotak token on this PC: anything that needs one runs on GitHub
  (`stock-options-probe.yml`, below).

## Where things stand

### S1 fade (arm F): **S1 v11 is the live rule from 2026-10-21** (live server `1bb3190`)
- **Rule** (`strategies/S1_v11_fade_stop20.md`): v10's entry, unchanged (strong numbers → put, weak → call, ₹2
  floor, ₹600–8,000 lot, live ask 09:15–15:20, retried every 30 s since 2026-10-21). **Exit:** from **09:16** on the
  entry day, the first poll whose best bid is at or below **0.80 × entry** sells at that bid (reason `fade_stop`);
  else the 15:20 bid as before.
- **Why it was switched:** the user's decision on 2026-10-20, taken *before* the pre-registered 30-trade test. The
  evidence was 1-minute prices for 468 v10 trades, Oct 2024 → Sep 2026: stop +₹2,50,916 (t 2.47) vs 15:20
  +₹1,70,405 (t 1.71), better in each window (`data/results/S1_v10_s20_minutes.md`). That result is descriptive,
  not pre-registered. Daily-price studies had said "no real gain".
- **v10 is now the shadow** (`rule.shadow_v10`): for a stopped trade, the contract's bid at the first poll from 15:20
  that day (status `pending` → `done`, `late` if missed); for a trade not stopped, `same`. `/api/paper/summary` →
  `fade_v10_shadow`, shown in the Arm F panel "Live v11 (−20 % stop) vs the old 15:20 exit".
- **Review at 30 closed v11 trades:** if the v10 shadow beats v11 (mean (v10 − v11) > 0 with t ≥ 2), ask the user
  whether to switch back (DECISIONS.md S1 v11 row).
- **Day 0 = 21 Oct.** New fade positions carry `rule.version = "v11"`. The Arm F scoreboard, the paper tab's Arm F
  row and its "Closed trades" list count v11 only. The 10 v10 trades (15–19 Oct, 2 won, −₹16,391) are a collapsed
  **side record**. Equity and booked P&L still include them, because cash cannot be split.
- **Tomorrow's (21 Oct) fade list:** UNIONBANK, HINDZINC, BAJFINANCE.
- **Other tags on every fade trade (judged later, never change the trade):**
  - `shadow_np25`: puts with NP YoY > 25 %; judged after 40 left-out puts.
  - `shadow_t100`: +100 % target; judged at 30 tagged trades.
  - **Sub-₹2 shadow entries** (`rules.fade_shadow_entries`, `/api/paper/summary` → `fade_subfloor`, Arm F panel).
    A refusal caused only by the ₹2 floor ("premium below Rs 2" or "never fits") reruns the walk with no floor. A
    strike it finds is tracked at its ask and netted at the 15:20 bid. Judged at 30.
  - The fade list's "Today" column shows why a signal has not filled yet (`rules.fade_wait`).
- The retired `shadow_s20` never tagged a trade (`strategies/S1_v10_s20_shadow_track.md`, marked superseded).

### Kill switch
The weekly loss halt latched on 19 Oct (week P&L −₹23,097, mostly the v10 trades sold that day). **It blocks manual
paper orders only; the rule trades (A, B, F) never go through it** (checked 2026-10-20). DECISIONS.md records it, and
the page banner says so. It clears on Monday 26 Oct.

### S1 arms A / B (live rules = S1 v7 `old_expiry`)
- 6 open positions: TATAELXSI ×2, TECHM ×2, WIPRO ×2. TECHM and WIPRO are near the 50 % stop.
- **The −20 % stop does not fix them** (`data/results/S1_arms_ab_stop20.md`): A −₹88k → −₹1.32 L (worse), B −₹70k →
  −₹32k (still a loss); t < 1. No rule change. The losses come from the entry.
- Known gaps, not fixed:
  1. If the server is down at 15:20, that day's A/B exit check is skipped, with no catch-up.
  2. The "close" entry books the day's average price + 1 tick, which is not tradable at 15:20 (TECHM was booked at
     ₹13.12 while the market was ₹9.25).

### Studies done 2026-10-19 / 20 (descriptive; all in `data/results/` + `strategies/`; none changed a rule except v11)
| Study | Result |
|---|---|
| Premium floor sweep (`S1_v10_floor_sweep.md` / `.xlsx`) | Sub-₹2 trades lose; one outlier (KALYANKJIL 2025-08-08) carries them |
| Profit-target exit (`S1_v10_target_exit.md` / `.xlsx`) | +50 % hurts; +100 % ≈ 15:20 |
| Sub-₹2 entries, tick costs, 2022-26 (`S1_v10_subfloor_entry.md`) | Fails all 3 tests (−₹52k on 140) |
| "Never fits" subset (`S1_v10_subfloor_neverfits.md`) | Fails (−₹48k on 105) |
| ₹0.50–1 band, +20 % / +100 % with trails, minutes (`S1_v10_band050_trail.md`, `_t100.md`) | Fails |
| ₹1–2 band, real ticks, minutes (`S1_v10_band12_trail.md`) | Fails on 2026 (B30 −₹30k) |
| Bands 2022-24, daily, before / after (`S1_v10_band_daily_2022_24.md`) | ₹1–2 B30 ≈ break-even; ₹0.50–1 loses |
| All minute windows (`S1_v10_band_minutes_all.md`) | ₹1–2 B30 +₹16k on 206 (t −0.6); ₹0.50–1 loses |
| −20 % stop on minutes (`S1_v10_s20_minutes.md`) | Basis for v11 (above) |
| Arms A/B with −20 % stop (`S1_arms_ab_stop20.md`) | No (above) |

- **Audit facts:**
  - The NSE tick for stock options is **₹0.01 since 2025-11-03** (₹0.05 before).
  - Upstox has 1-minute candles for expired **stock** options from the **Oct 2024 expiries** only.
  - Nothing free covers 2022 → Sep 2024 (Upstox v2/v3 and Kotak probed; `DATA_ACCESS_AUDIT.md` addendum). Paid
    options were priced (Stolo ₹199 trial plus tokens; GDFL / TrueData about ₹15–20k a year). The user chose to work
    with the data available.
- **R:** 1R = the premium paid. v10 backtest 2022-26: +0.046R a trade (870 trades, t 1.60).

### S2, website, index data (from the other session; unchanged here)
- **S2:** screen B closed; nothing passed; no strategy to trade.
- **Website** (fo-scanner.onrender.com): tabs Paper / Arm A / Arm B / Arm F; `/s2`; `/index` (data status).
- **Index data layer** (`INDEX_DATA_PLAN.md`, `index_data/`). Large files go on branch **`index-data`**; small JSON
  goes in `data/index/` on main.
  - Nightly recorder `.github/workflows/index-recorder.yml`, 19:30 IST.
  - Job queue `data/index/job_queue.json` with the hourly `index-scheduler.yml`.
  - Manual jobs `index-jobs.yml`. Only one may wait at a time.
  - Backfilled:
    - spot / VIX 1-min, Oct 2021 →;
    - daily OHLC of every NSE index option, 2021 →, now one file per month;
    - expiry calendar;
    - Upstox expired NIFTY (complete) and BANKNIFTY (complete) options;
    - SENSEX in progress.
- **Upstox vs Kotak shadow check** on the live server (`/api/data/compare`), from 20 Oct.

## Still running
| What | Where | Finishes | Needs the PC |
|---|---|---|---|
| Index job queue (the rest of SENSEX, then the one-off `bhavcopy_ohlc --split-yearly`) | GitHub, hourly | SENSEX ~20 Oct evening | no |
| Nightly recorder (+ S1 trades' minutes, spot / VIX, OHLC top-ups) | GitHub cron 19:30 IST | ~20:00 IST | no |
| Upstox-vs-Kotak shadow check | Render | a few days, then decide the switch | no |
| Kotak expired-token probes (`kotak-probes.yml`) | GitHub, 16:00 IST weekdays | 20 Oct, 27 Oct, 19 Nov | no |
| Results-day fade signals before the open (`fade-morning.yml`) | GitHub | daily | no |

## Tools made in this session
- **`stock-options-probe.yml`** (manual, read-only, separate from the index queue, 60-minute limit). It is a
  separate file from `upstox-probe.yml`; don't confuse the two. `script` options:
  - `probe_stock_expired`: what exists;
  - `probe_old_options`: before Oct 2024;
  - `fetch_band_minutes` with `args` = `050` / `12` / `12q4` / `050q4` / `v10` / `ab`. It reads
    `data/results/S1_v10_band<args>_contracts.csv` (optional `from` / `to` spans).
  - The artifact is always named `band050-minutes`. Download it with
    `gh run download <id> -n band050-minutes -D <dir>`.
- **Minute CSVs are not committed** (`data/results/` is gitignored; `git add -f` only the reports and contract
  lists). Re-fetch them if needed.
- Analysis entry points:
  - `python -m scanner.fade_band050 pick|pick12|run|run100|run12|all`
  - `python -m scanner.fade_s20_minutes`
  - `python -m scanner.arms_ab_stop20`
  - `python -m scanner.fade_subfloor` and `scanner.fade_subfloor_neverfits`
  - `scanner.fade_band_daily`, `scanner.fade_floor_sweep` / `fade_floor_sheet`, `scanner.fade_target_exit`
- Backtests need `EVENTS_DB=$TEMP/fo-seed/events.sqlite`; without it, signals are 0.
- Windows console: print ASCII only in reports (a "→" crashed `print` once; the file was still written).

## After a context compaction
- Read this file first, then the tail of `PROGRESS.md`, DECISIONS.md's S1 v10 / v11 rows and `INDEX_DATA_REPORT.md`.
- `gh` is at `C:/Program Files/GitHub CLI/gh.exe`. The Python venv is `%TEMP%\fo-venv\Scripts\python.exe` (pandas,
  pyarrow, openpyxl, yfinance 1.7.0, requests, xlsxwriter). Excel (COM) is installed for recalculating `.xlsx`;
  LibreOffice is not.
- The test suite has **one known failure** (`test_spec12_step7_model.py::test_infer_for_scan_adds_the_model_block`);
  everything else passes (39 fade tests).

## Next steps
1. **21 Oct (v11 day 0):**
   - After 09:16, check that the new fade positions carry `version`, `stop` and `shadow_v10`, and whether a
     `fade_stop` fires at a sensible bid.
   - After 15:20, check that `shadow_v10` resolves (`done` / `same`) and that the Arm F panel shows both columns.
   - Keep the server awake at 15:20 (keep-awake runs 08:17 / 11:47 / 14:17 IST).
2. **Reviews:**
   - v11 vs the v10 shadow at 30 closed v11 trades;
   - `shadow_t100` and the sub-₹2 entries at 30;
   - np25 at 40 left-out puts;
   - the A/B forward test as before.
3. **Index data (other session):**
   - when the jobs finish, fill `INDEX_DATA_REPORT.md` (BANKNIFTY / SENSEX / reconciliation / "what is available")
     and check `/index`;
   - after tonight's recorder, check `data/index/status.json`;
   - probe results go into "Expired-token retention".
4. **Open questions to the user:**
   - Switch `DATA_PROVIDER=upstox` after clean shadow rounds? After market, with a DECISIONS.md entry.
   - Add a catch-up for missed A/B exit checks?
   - Should the A/B close entry buy at the 15:20 ask instead of the day's average? That is a rule change, so it
     needs the user's decision.
5. No index strategy ("pod") exists. One gets added only with its own pre-registered rules.
