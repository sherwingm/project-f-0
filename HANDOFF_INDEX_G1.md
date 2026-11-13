# Handoff: index chat "nifty index" (G1 / G1-F / G1-C, expiry research, index max up), updated 2026-11-13

This chat is for the **normal index build** (NIFTY index options: G1 / G1-F puts, the G1-C call mirror, XP, the independent expiry research).
The user said (6 Nov): **keep Near Tighty (NT) and the near-expiry (1-3 sessions) rule OUT of this chat.** NT is its own part
(`strategies/NT_near_tighty.md`, `server/nt_live.py`, `near_tighty_research/`). Repo `sherwingm/project-f-0` (public; never commit secrets),
local clone `C:\Users\sherw\project-f-0`. The older `HANDOFF.md` is the S1 / shared one. `CLAUDE.md` (repo root) loads by itself and holds the
short version of the rules below.

## House rules (the user's, in force)
- **Reporting default:** every result leads with **max up after entry** (share reaching +50 / +100 / +200 %, mean, median), THEN the booked result
  (win %, average, median, total Rs). Max up is the measure; the exit is not. Split by days held / days to expiry.
- Buy only (options). Paper only: **no real order, no deploy of a rule change without the user, no auto-promotion.**
- Phone reader: plain words, lists not wide tables (a table once did not display), end every reply with **"Still running:"** and the error-count
  line (memory `error-count-footer`). Teach, then do.
- Commit and push every step, log in `PROGRESS.md`, verdicts in `DECISIONS.md`; **pre-register before any number** (`strategies/*.md` or a `*_PREREG.md`);
  one row per run in `docs/research/experiments.csv`. Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- **The PC clock is ~5.5 h behind IST.** Read market time from the VM: `ssh -o BatchMode=yes fo-scanner 'TZ=Asia/Kolkata date'`. Never restart the live
  server 09:00-15:40 IST on a session day. The model can only be changed in the app's model menu (this session is Sonnet 5.5).
- **Auto-compact is OFF by the user's choice:** use `/context`, then `/compact` (or this handoff + `/clear`).
- **Another session edits the same folder:** stage only your own files, `git pull --rebase --autostash`. Untracked `calib_cash.csv`, `fills_mech.csv`,
  `S1_web_project.pptx`, `server/autoupdate.py` etc. are not ours.

## Live system (AWS VM `ssh -o BatchMode=yes fo-scanner`, dir `/home/ubuntu/fo_scanner`; use `/deploy-vm`)
- VM runs `1d46d134e` (my last deploy, 12 Nov 17:49 IST: G1-C). Later pushes (docs, tests, `server/charges.py` dated STT, skills, handoff) are NOT deployed and
  change no live behaviour (the live code passes no date to `charges.leg`). Deploy them at a quiet restart, outside 09:00-15:40 IST.
- **G1 / G1-F** (`server/g1_live.py`, rules `strategies/S3_G1_put_overnight.md`): opening range 09:15-09:29; first 1-minute close outside it 09:30-13:00; only a
  close BELOW the low trades (a first close above = no G1 trade); ATM put of the nearest weekly after today at the last ask of the next minute; **stop at bid <= 50 %
  of the price paid (any second, both days), else sold at the best bid at the first quote of the next session's 15:29** (a missed close sells at the first bid next
  session). **G1-F (main track)** takes the same trade only if the day-1 gap < +0.3 %, the range width is not 0.5-0.8 % and VIX < 17; G1 is the baseline. No minimum
  break size (median break only 0.017 % beyond the range). Own ledger `data/g1_ledger.json`; API `/api/index/g1`; shown on `/index` with the **score board**.
- **Breakout score 0-7** (`server/g1_score.py`, record only, never gates a trade; puts only, NT not scored): history shows no link to max up; judge again at 30 live signals.
  Marks / best bid of an open position are saved every 30 s (a restart on 10 Nov once reset a trade's best bid).
- **G1-C** (`server/g1c_live.py`, `strategies/S3_G1C_call_overnight.md`, ledger `data/g1c_ledger.json`, `/api/index/g1c`): the call mirror, paper only, the first close ABOVE the range
  buys the ATM call, same stop and exit, no filters, no score. Built at the user's request on 12 Nov although history says it loses (about -11 % a trade); judged at 30 trades.
  `G1Trader` takes the option side from the class attribute `OPT` (G1, G1-F, NT unchanged).
- **XP** (`server/xp_live.py`, `expiry_research/FORWARD_TEST.md`, `data/xp_ledger.json`, `/api/index/xp`): NIFTY expiry days only, ATM CE + PE at the 09:16 asks, +20 % target on the
  pair else 15:15, log only, verdict at 40 expiry days.
- **Calendar:** `server/sessions.py` `is_index_session` counts announced full weekend sessions (`data/special_sessions.json`, empty now); holidays win. Tue 10 Nov was a holiday.
- The index feed is frozen 15:15-15:28 since 3 Aug 2026 (NSE feed; G1 is unaffected).

## Live paper results (13 Nov 2026 16:00 IST, from the VM API; one trade each, nothing is judged yet)
- **G1 1 of 30:** Mon 9 Nov 09:40 bought NIFTY 17 Nov 24900 PE at Rs 289.85 (G1-F skipped: gap +0.31 %, width 0.72 %, VIX 18.03), score 1/7. Wed 11 Nov 09:15 the first quote (Rs 78.70)
  was far below the stop (Rs 144.93) and it sold there: **-73.2 %, -Rs 13,790**, max up only +3.9 %. **G1-F 0 of 30**, no loss.
- **G1-C 1 of 30:** Fri 13 Nov bought NIFTY 17 Nov 25200 CE at Rs 164.45, stopped the same day at Rs 81.95: **-50.75 %, -Rs 5,425**, max up +19.6 %.
- **XP 1 of 40:** Mon 9 Nov straddle 25050 at Rs 245.25, target not reached, sold 15:15 at Rs 69.20: **-72.5 %, -Rs 11,553**, max up +3.6 %. History replay (107 expiry days): the XP rule loses on average
  (-11.0 %, t -2.70); 13 of 107 days at or below -72 %.
- Context: NIFTY rose about 9 % from 29 Oct (22,937) to 6 Nov (25,030); puts idled on up-break days; today (13 Nov) the first break was up at 09:45 (no put).

## Research results (history, in-sample; folders `g1_research/`, `expiry_research/`; one row each in `docs/research/experiments.csv`)
- **G1-F history (live rule, ATM put, 154 trades Oct 2024-Oct 2026, 1 lot):** max up through next close reaches +100 % on 41 %, mean +104 % / median +72 %; booked win 41 %, average +19.7 %, median -18 %,
  total +Rs 2.47 lakh (+Rs 2.13 lakh at 2x costs), max drawdown -Rs 41.6k, 7 of 23 months negative; passes its gate at 60-150 trades, not at 30. **G1 (259 trades):** +Rs 40k, t 0.94, fails at 2x costs.
  Without the top 10 trades every variant is about zero. Only the overnight hold works (same entries intraday lose).
- **Nothing found that predicts follow-through or ranks max up:** score (10 methods), formation shapes, 5 years of NIFTY moves (638 signals, follow-through +0.06 ATR, p 0.11-0.14), FII/DII positions (x3), news tone,
  heavyweight stocks, holding patterns, IV crush, minimum break size. Near-miss lead only: retail net-long positioning -> bigger next-day move (confirmation p 0.051).
- **Verification of public claims (`VERIFY_RESULT.md`):** no strike beats ATM (ITM = more wins, smaller loss, fewer big doubles, about 2x capital); the call mirror loses at every strike; Zerodha ORB on premium, forum 2 %/2 %,
  the 30-minute ORB bot and the 11.5-year trail rule are all negative on our data.
- **Expiry research** (`expiry_research/`, sealed final period from Jul 2024): no direction edge (AUC 0.44-0.56); size partly predictable (volatility clustering) but a long ATM straddle loses.
- **1-minute data audit** (`g1_research/DATA_AUDIT.md`): complete and consistent on all 259 G1 days.
- Capital view given to the user: 1 lot of G1-F history drawdown -Rs 41.6k, longest losing streak 11, so about Rs 1.5-3 lakh for 1 lot (not advice; paper only).

## Infrastructure added 13 Nov (user approved)
- `CLAUDE.md`; `docs/research/{README,SOURCES,VALIDATION_INVENTORY}.md` + `experiments.csv`; `docs/CLAUDE_CODE_CHEATSHEET.md`; skills `/deploy-vm`, `/research-loop` and agent `research-verifier`
  (`.claude/skills`, `.claude/agents`, tracked in git); 32 validation tests (`tests/test_validation_*.py`); STT dated by trade day in the S3 engine (`server/charges.py` `STT_HISTORY`, effect on G1 +Rs 861, no verdict change).
- **Known history-vs-live differences (documented, not changed):** stops on minute closes vs live per-second bid (a gap through the stop fills below it, as on 11 Nov); flat slippage; non-STT charges one table;
  partial opening range accepted; no sealed holdout for G1.
- Connectors Figma, Google Calendar, Google Drive, BigQuery switched off (also default for new sessions). Whole suite: **803 passed, 0 failed**.

## Next steps / waiting
- Let the live paper trades accumulate (G1-F 0 of 30, G1 1 of 30, G1-C 1 of 30, XP 1 of 40). Do not change entry rules, filters or stops before a gate is judged; judge max up first, then booked.
- Optional, not started: shadow log of what each hold length would have given on live trades; SENSEX live paper; date-version the non-STT charges (exchange Rs 35.53 vs 35.03 unconfirmed);
  a shared Benjamini-Hochberg helper; an environment lock; walk-forward for the S3 pods; a sealed holdout policy for G1; deploy the later pushes at a quiet restart.
- After each committed study add one row to `docs/research/experiments.csv` (append only).

## After the compaction
Read this file, then the tail of `PROGRESS.md` (never the whole file) and the last entries of `DECISIONS.md`. Use `/research-loop` for a study and `/deploy-vm` for a VM update.
Python: `C:\Users\sherw\.venvs\fo\Scripts\python.exe` (tests: `pytest -q -p no:warnings tests`); data env `INDEX_STORE=../fo-index-data/data/index`.
Latest commits: `8eb9067a7` (registry row), `e31fd79ec` (skills tracked, dated STT), `851a54cc7` (CLAUDE.md, research docs, validation tests), `365eec3d0` (depth test), `5a0347afd` (XP history), `1d46d134e` (G1-C deployed).
