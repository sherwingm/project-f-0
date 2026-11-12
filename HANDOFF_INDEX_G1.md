# Handoff: index chat "nifty index" (G1 / G1-F, expiry research, index max up) , 2026-11-07

This chat is for the **normal index build** (NIFTY / SENSEX index puts, G1 / G1-F, the independent expiry research).
The user said (6 Nov): **keep Near Tighty (NT) and the near-expiry (1-3 sessions) rule OUT of this chat.** NT is its own
part (`strategies/NT_near_tighty.md`, `server/nt_live.py`, `near_tighty_research/`). One NT folder was added here by mistake
(commit `4ffae4e83`); the user did not ask to remove it. Repo `sherwingm/project-f-0` (public; never commit secrets), local
clone `C:\Users\sherw\project-f-0`. The older `HANDOFF.md` is the S1 / shared one.

## House rules for this chat (the user's, in force)
- **Reporting default (7 Nov):** every result leads with **max up after entry**: the share reaching +50 / +100 / +200 %,
  the mean and the median max up, THEN the booked result (win %, average, median, total ₹). Max up is the measure; the
  exit is not (there is no perfect exit). Split by days held / days to expiry. Written into PROGRESS.md, DECISIONS.md, the
  G1 page, the folder READMEs and memory (`max-up-is-the-real-measure`).
- Buy only (options). Paper only: **no real order, no deploy of a rule change without the user, no auto-promotion.**
- Phone reader: plain words, narrow tables, end every reply with **"Still running:"**. Teach, then do (interview lines).
- Commit and push every step, log in PROGRESS.md, decisions in DECISIONS.md; pre-register before any number
  (`strategies/*.md` or a PREREG file). Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- **The PC clock is ~5.5 h behind IST.** Read market time from the VM: `ssh -o BatchMode=yes fo-scanner 'TZ=Asia/Kolkata date +%H:%M'`.
  Never restart the live server 09:00-15:40 IST on a session day (weekends are safe). The user once asked to use Opus: that
  can only be set from the app's model menu (the session cannot switch itself); it has been Sonnet 5.5.
- **Another session edits the same folder** (`templates/results.html` etc.): stage only your own files, check the staged
  diff, `git pull --rebase --autostash`. Stray untracked files (`calib_cash.csv`, `fills_mech.csv`, ...) are not ours.

## Live system (AWS VM, `ssh -o BatchMode=yes fo-scanner`, dir `/home/ubuntu/fo_scanner`)
Deploy recipe that works: back up modified files to `~/deploy_backup_<stamp>`, `git checkout -- .` (the server rewrites
`data/scan.json`), `git pull --rebase`; untracked `data/live_snapshots/<day>.json` can block the pull (move it away after
`cmp` with origin), `sudo systemctl restart fo-scanner`, wait ~45 s, then check `systemctl is-active`, HTTP 200 on
`/index`, `/api/index/g1`, `/api/index/xp`, `/api/near-tighty` with `curl -u user:$APP_PASSWORD` (read from `.env` inside the
VM shell, never printed), `PAPER=true`, no errors in `journalctl -u fo-scanner --since -3min`.
- VM was at `7e0b66582` (another session's results-page change) on 7 Nov 13:04 IST; my last deploy was `9ee8f67d7`.
- **G1-F is the MAIN track** (user, 6 Nov), G1 the baseline: `server/g1_live.py` (G1Trader; own ledger `data/g1_ledger.json`,
  git-ignored), shown on `/index` (G1 section, Pods table with max up avg / median / ≥ +100 % first), API `/api/index/g1`.
  Rules `strategies/S3_G1_put_overnight.md`: opening range 09:15-09:29; first close outside it 09:30-13:00; only a close
  below the low trades; ATM put (50-pt step) of the nearest weekly after today; buy at the last ask of the minute after the
  signal; **stop at bid ≤ 50 % of price paid (any second, both days); else exit = best bid at the first quote of the NEXT
  session's 15:29 minute (changed 7 Nov from 09:16, before any live trade; a missed close sells at the first bid next
  session)**. G1-F takes the same trade only if day-1 gap < +0.3 %, range width not in 0.5-0.8 %, VIX < 17. Two separate
  30-trade gates (mean > 0, still > 0 at 2× charges, t ≥ 2, both halves > 0, worst loss < average month).
  `HOLD_TO_CLOSE` is a class attribute: G1 True, Near Tighty False (NT keeps its 09:16 exit).
- **Live results so far: 0 trades** (5 and 6 Nov both broke upward first = no trade). Next session **Mon 9 Nov**; **Tue 10 Nov
  is a holiday** (Diwali Balipratipada), so the NIFTY weekly expiry moved to Mon 9 Nov; Sun 8 Nov is the one-hour evening
  Muhurat session (not a full session, not traded, listed as a holiday).
- **XP forward log** (`server/xp_live.py`, `expiry_research/FORWARD_TEST.md`, ledger `data/xp_ledger.json`, `/api/index/xp`,
  section on `/index`): NIFTY expiry days only, buys the same-day ATM CE + PE at the 09:16 asks, +20 % target on the pair else 15:15,
  hold-to-15:15 logged alongside, max up recorded; verdict at 40 expiry days. **First day is Mon 9 Nov** (not Tue 10 Nov).
- **Calendar fix (7 Nov):** `server/sessions.py` `is_index_session` counts announced full Saturday / Sunday sessions
  (`SPECIAL_SESSIONS` env or `data/special_sessions.json`, empty now) for G1 / NT / XP / the NIFTY recorder; `is_session` is
  unchanged so S1 / S2 are untouched; a holiday always wins. Add a date when NSE announces a weekend session.

- **Breakout score (7 Nov, record only):** `server/g1_score.py`; score 0-7 + % + percentile + running avg on every G1 signal (ledger day + trade + buy alert); never gates a trade; NT not scored. History check: no link to max up (SCORE_RESULT.md); judge again at 30 live signals, max up first by band. VM at `ed98cb1ef`.

- **9 Nov update:** score board on /index (deployed 23e55edb2). FIRST LIVE G1 TRADE 9 Nov: signal 09:40, bought NIFTY 17 Nov 24900 PE at Rs 289.85, G1-F skips (gap, width, VIX), score 1/7 (low band, percentile 2), all 7 inputs live. Searches since 7 Nov (score methods, formation, 5-year spot, FII/DII x3, news, heavyweights) found nothing; verification of public claims (VERIFY_RESULT.md): no strike beats ATM, the call mirror (G1-C) LOSES held overnight, Zerodha ORB / forum ideas all negative. Do not build G1-C without the user.

- **12 Nov update:** first live G1 trade (9 Nov put, score 1/7) was stopped at Wed's open: -73 %, -Rs 13.8k (gap through the stop). **G1-C (call mirror) set up as PAPER** at the user's request (server/g1c_live.py, strategies/S3_G1C_call_overnight.md, /api/index/g1c, own ledger g1c_ledger.json, deployed 1d46d134e): the history says it loses (VERIFY_RESULT.md), so it is a forward record judged at 30 trades. Marks / best bid are now saved every 30 s (a restart reset a trade's max up once).

## Research done this chat (all history, in-sample unless stated; folders are separate, do not mix)
- `expiry_research/` (independent project, all years 2018-2026, sealed final period Jul 2024 →): **no direction edge** at
  any decision time (gap transitions, 5 sessions before expiry, option chain / OI, ML all ~chance, AUC 0.44-0.56). Size of
  the next move is partly predictable (11 of 13 rules passed the one-time final test) but it is volatility clustering and a
  long ATM straddle on it loses (−4.6 % every day). Report `expiry_research/reports/FINAL_RESEARCH_REPORT.md`.
  Max up from a 09:16 ATM buy: expiry day 68 % of days a leg ≥ +100 %, 1 day out 38 %, 2: 29 %, 3: 15 %, 4+: 12 %.
- `g1_research/` (normal index): max up after entry with NO exit (`g1_maxup_free`), SENSEX put side, call mirror (NIFTY, SENSEX),
  exit comparison (`g1_next_close_exit`), holding-days sweep (`g1_hold_days`), holding-pattern search (pre-registered,
  `HOLD_PATTERN_PREREG.md`, result `HOLD_PATTERN_RESULT.md`), IV-crush check. Key numbers (G1-F since 2025, 133 trades):
  - Max up through next 09:16: mean +59 % / median +30 %, ≥ +100 % on 23 %; through next close +102 % / +70 %, 38 %;
    2 days +129 % / +103 %, 50 %; 3 days +155 % / +122 %, 56 % (peak, not profit). SENSEX puts about the same; calls about half.
  - Booked (50 % stop): old exit (next 09:16) win 49 %, mean +17.6 %, median −3.9 %, ₹1.91 L; new exit (next close) win 40 %,
    mean +17.6 %, median −29 %, ₹2.31 L, 44 % stopped. Longer holds: 3 days +31.8 %, to expiry +30.2 % / ₹3.25 L but 62 % stopped.
  - G1 (no filters) is much weaker with longer holds (next close +2.0 %, t 0.3). Without the top 10 trades every variant is ~0.
  - Pace: G1 ≈ 10.4 trades a month, G1-F ≈ 6.2 (30 trades ≈ 5 months for G1-F).
  - **Holding-pattern search: none found** (96 rules, 0 candidates after BH; the first run's 3 "passes" were circular and
    rejected; VIX change after entry (IV crush) explains the put's level at the decision but does not predict the follow-up).
- `near_tighty_research/` (NT only, made on 6 Nov): `nt_maxup.py`, `NT_MAXUP.md`; keep NT work there.

## Open / waiting on the user
- Live paper needs trades: G1-F gate at 30 trades; do not change entry rules, filters or the stop before it is judged
  (my advice: stop tuning). Optional, not started: record "what each hold length would have given" on every live trade
  (shadow, no rule change); SENSEX live paper (needs a SENSEX option feed on the server and its own gate); special-session dates.
- On the first live trades, check the ledger (`data/g1_ledger.json` on the VM), the phone alert (says whether G1-F counts it),
  and that max up is recorded per trade (`max_bid`, `max_up_pct`).
- The user's PC has `S1_web_project.pptx` etc. untracked: not ours.

## After the compaction
Read this file, then the tail of `PROGRESS.md` and the last entries of `DECISIONS.md`. Python:
`C:\Users\sherw\.venvs\fo\Scripts\python.exe` (tests: `pytest -q -p no:warnings tests`, all pass except
`test_spec12_step7_model.py`); data env `INDEX_STORE=../fo-index-data/data/index`. Latest commits of this chat:
`767b4ca4e` (IV-crush check), `581f771b9` (hold pattern), `9ee8f67d7` (reporting default), `45ab842fc` (calendar fix),
`60a058f0b` (next-close exit), `76dc84328` (G1-F main), `01d0602c1` (XP log), `7d47ae69e` (expiry research).
