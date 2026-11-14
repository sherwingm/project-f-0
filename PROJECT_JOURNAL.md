# Project journal: F&O options research and paper trading (repo project-f-0)

Written 13 Nov 2026 (draft, not yet committed). Evidence-based reconstruction from git history, `DECISIONS.md`, `PROGRESS.md`,
`HANDOFF.md`, `HANDOFF_INDEX_G1.md`, `STRATEGY_AUDIT.md`, `strategies/*.md`, `docs/research/*` and `stress_audit/results/STRESS_REPORT.md`.
Day-by-day log of the last week: `RECENT_CHANGES_2026-11-09_to_2026-11-14.md`. Companion files: `CHANGELOG_ANALYSIS.md` (good / bad / incomplete / regressions / unresolved), `CURRENT_PROJECT_STATE.md`, `STRATEGY_HISTORY.md`.
Existing documents were not edited. Where an older document is wrong or out of date it is noted here, not corrected there.

## Executive summary
- **What it is.** A research and paper-trading system for buying NSE options (buy only, 1 lot, paper only, no real orders). Three tracks:
  **S1** (stock options around quarterly results), **S2** (stock options from price and futures-OI build-up), **S3** (NIFTY / SENSEX index options,
  including G1 / G1-F / G1-C and XP). A fourth, **Near Tighty (NT)**, is a separate paper track and is only summarised here.
- **How old.** The git history starts on **24 Sep 2026** with a "baseline as received" commit. 715 commits to 13 Nov 2026 (80 in Sep, 465 in Oct,
  170 in Nov). What existed before 24 Sep **cannot be reconstructed** from the repository.
- **What the evidence says.** Roughly 40 pre-registered or logged studies, nearly all negative. The only results that survive their own tests are
  **small, in-sample and fragile**: S1 fade v12 (+2.9 % a trade, t 1.79) and G1-F (+19.7 % a trade, t 2.41, filters chosen on the same data).
  The 13 Nov stress audit finds both unproven: S1 v12 shrinks to about zero with 1 to 2 % slippage a side; G1-F survives its stress set but is in-sample
  with a live record of days.
- **Nothing is validated as profitable or production-ready.** The live paper records are small: S1 v12 58 closed trades, mean -5.7 % (descriptive);
  G1 1 trade, G1-C 1, XP 1, G1-F 0.
- **What genuinely improved** is the research process: pre-registration, a trial registry, validation tests, a dated STT, a spot-store repair, a 1-second
  recorder, a stress audit. What did **not** improve is the amount of independent (out-of-sample) evidence for any trading rule.
- **Biggest open weaknesses:** no sealed holdout for S1 or G1; no historical bid/ask; the S1 backtest has no slippage and an unknowable intrabar order;
  no trial count for S1 v2 to v10; backtest stops differ from live stops.

## How this journal was built (and its limits)
- Read in full: `DECISIONS.md` lines 1 to 450, `stress_audit/results/STRESS_REPORT.md`, `HANDOFF.md` (first 120 lines), `HANDOFF_INDEX_G1.md`,
  `docs/research/{experiments.csv,SOURCES.md,VALIDATION_INVENTORY.md}`, `STRATEGY_AUDIT.md` (first part).
- Sampled: `PROGRESS.md` (headings, core idea tracker, 10 Nov entries), about 14 strategy pages (status lines only), the commit log (about 60 sampled lines plus counts).
- **Not read:** most of `PROGRESS.md` (137 KB), the other 45 or so strategy pages, result CSVs, source code line by line, the memory files beyond the index,
  the Claude Code session transcripts. No code was run and no tests were run: test counts are quoted from documents.
- Not touched, by instruction: the sealed expiry dataset, the VM, any API, `.env`.
- Git authors as recorded: `sherwingm` 524 commits, `Sherlyn` 117, `fo-scanner-bot` 74 (automatic nightly scan / ledger commits). Who "Sherlyn" is was not established.
- A commit message is a claim, not proof. Where this journal says "fixed", it names the evidence (a test, a re-run, a document) or says none was found.

## Timeline

### Before 24 Sep 2026: not reconstructable
- The first commit (`0f5a34b90`, 24 Sep) is "Baseline: fo_scanner as received, plus build spec 11": 53 files (13 `guides`, 13 `server` modules, 10 `scanner` modules, a render.yaml,
  a daily GitHub workflow). The project name then was **fo_scanner**. How it was built, by whom, and what it did before is **not in the repository**.
- `DECISIONS.md` opens with a stock-only scope and a position-limit regime (6 % of capital a position, 3 open positions, loss halts) that look inherited from that baseline.

### 24 to 30 Sep: build specs on the received code
- Steps of "spec 12" are committed one at a time: live depth, charges (`server/charges.py`), liquidity classification, an event store, F&O bhavcopy reading for pre-July-2024 files.
- 25 Sep: paper-engine tests read a fixed clock. 29 Sep: "no buckets" (paper trades are one group). 30 Sep: paper account survives restarts; position limits; login.
- Risk: Kotak credentials were leaking into SDK logs and error messages; fixed in the second commit (24 Sep).

### Oct 2026: S1 research, then the paper account, then the index
- **1 to 14 Oct (S1 v2 to v8).** Each version was a pre-registered page in `strategies/`. v2 (results-miss put spread) and v3 (strength score) closed at the stock-level diagnostic. v4 to v7 (results-beat
  continuation, long calls) found real 2021-24 stock drift but **calls lost after decay and costs**. v8 used the 2025-26 holdout by the user's choice (14 Oct): the drift was gone and the live rules lost (arm S -27.6 %, t -3.42).
- **13 to 14 Oct.** The paper account starts taking the S1 rule trades (arms A / B, calls). S2 step 1 screen: 1 of 48 cells passed (short build-up); step 2 (a bought put) failed (-14.2 %, t -2.71).
- **14 to 18 Oct (S1 v9, v10).** v9 (calls on results day) found the opposite: strong numbers fall from the open, weak ones rise. v10, the **results-day fade** (strong -> put, weak -> call, same day), starts as paper on **15 Oct**.
  Descriptive backtest 2025-26: +5.6 % a trade, t 1.33, and dependent on the entry price (VWAP entry -14.9 %).
- **16 to 17 Oct: first operational failure.** The live server slept from 11:21 to after 16:00; eight fade trades missed the same-day 15:20 exit. The user decided to close them on Monday and retire the carry rule.
  Root cause: the server was not always on. Fixed by moving to an AWS VM on 22 Oct.
- **18 Oct.** `STRATEGY_AUDIT.md` (an audit of the code; it states that no index options existed yet), the core idea tracker in `PROGRESS.md`, the v10 diagnostics (adversarial check: all nine claims survive, one lead is weak).
- **19 to 21 Oct.** 1-minute option prices (from Oct 2024) arrive. A -20 % stop looks better on minutes than on daily candles: **v11** (v10 + a -20 % stop) goes live on 21 Oct by the user's decision,
  **before** its pre-registered 30-trade test. On 20 Oct two live rule bugs were found against the written rules (tick Rs 0.05 vs 0.01; F&O ban not applied to arms A / B) and fixed.
  Weekly loss halt removed (21 Oct); daily halt removed (22 Oct). **v12** (v11 + a trail on at +10 %, 2 % gap) live from 22 Oct, chosen after seeing results; the page itself says "not proven".
- **22 Oct.** AWS VM becomes primary; Upstox WebSocket price stream with Kotak fallback; fade entry retried every second. S3 (index options) opened by the user for research; index data pipeline (`index_data/load.py`).
- **23 Oct (S3 round 1).** Pods P1 to P7 (expiry-day flies, straddles, condors, ORB) all closed on the test window. An independent 4-agent review confirmed 10 issues (wrong RBI event date, wrong lot size, a stray Saturday bar, a faulty expiry calendar); fixes `32bd807c`, re-runs, **no verdict changed**.
  About 420 looks at the same NIFTY data are recorded.
- **26 Oct.** Paper rule trades are filled "as real orders" (limit at ask, 60 s cancel, bid chase on sell). SENSEX replication R1: the late-expiry premium **does not replicate**.
- **29 to 30 Oct.** L1 (long straddle on VIX spike) and D6R (short vol, 2018-21) closed. User decision (30 Oct): **buy only**, test 2024-10 -> today. E1, Q1, B1, G1-gap pods closed.
  The spot store's 09:15 bar was found wrong (Kotak; open matched NSE on only 35 % of sessions), repaired from Upstox on 923 of 923 sessions; re-runs, same verdicts.

### Nov 2026: G1, recorders, infrastructure
- **1 to 3 Nov.** 1-second NIFTY recorder on the VM (record only). B2 (accepted breakout), PUT1 (downside breakout, spot 2022-24), X1 (expiry-day put) closed. 2 Nov: paper buys wait for **today's** order book
  (three fills on 29 / 30 Oct had used yesterday's ask).
- **4 Nov.** **G1** pre-registered and put on live paper in the same step (the user: "make this live in the website"). G1 had been picked as the best of seven in-sample PUT1 variants. **G1-F** (three filters) added before any forward session,
  chosen from nine bucket tables on the same 154 trades. NT created as a separate track. V1 (cheap straddle) closed.
- **5 Nov.** Independent expiry research (`expiry_research/`): no direction edge (AUC 0.44 to 0.56). XP expiry-day straddle starts as a forward log. `docs/research/experiments.csv` starts (back-filled).
- **6 to 7 Nov.** G1-F made the main track; G1 exit changed to the next session's close (user); "max up first" reporting default; breakout score (0 to 7, record only).
- **7 to 9 Nov.** Searches for anything that predicts follow-through: holding patterns (first run had **circular** passes and was rejected), score methods (10), formation shapes, 5 years of spot, FII/DII positions (three variants), news tone,
  heavyweights. **None passed.** 9 Nov: public claims verified on our data (ATM vs ITM, Zerodha ORB, forum rules); all negative.
- **9 to 14 Nov.** Moved to `RECENT_CHANGES_2026-11-09_to_2026-11-14.md` (day-by-day log). Headlines: 1-minute re-tests of S1 arms A / B and the fade; G1's first live trade stopped at -73 %; G1-C and XP added; infrastructure (CLAUDE.md, registry, validation tests, dated STT); the stress audit, its independent review and a corrections addendum.

## The stress audit of 13 Nov (summary; detail and corrections in `RECENT_CHANGES_2026-11-09_to_2026-11-14.md`)
Pre-registered, offline, no parameter tuned (`stress_audit/`). Reproduced by an independent review (`stress_audit_review/`; arithmetic verified, process errors noted) and qualified by a corrections addendum (`stress_audit_corrections/`, 14 Nov, awaiting the user's approval).
- S1 fade v12: +2.86 % a trade (t 1.79) shrinks to -1.13 % at 2 % slippage a side; first-candle uncertainty range +1.786 % to +3.876 %; intrabar bracket -2.33 % to +5.42 %; strike pick has a look-ahead. **Insufficient evidence; execution assumptions unrealistic.**
- G1: +5.54 %, t 0.94, interval contains 0; robustness to stress: split. **G1-F:** +19.7 %, t 2.41, held up in every stress line, but the stress lines do not vary its three filters, which were fitted on the same data: **in-sample, not validated.**
- Charges are not the problem; slippage and entry timing are. Prospective holdout frozen 13 Nov 17:48:58 IST, 0 trades so far.

## Backtest and execution: how the approach evolved
Detailed comparison is in `CURRENT_PROJECT_STATE.md`. In short:
- **S1:** daily-candle tests (v2 to v9) -> realistic entry (09:16 open + tick) -> minute candles (Oct 2024 on) -> live "real-order" paper fills (26 Oct) -> stress audit (13 Nov).
- **S3:** daily bhavcopy -> a tested engine on 1-minute prices (`scanner/s3_engine.py`) with slippage (0.5 %, 1 % wide / early / late) and charges, 2x-cost gate -> dated STT (13 Nov).
- **Live vs history:** the live rule stops on any second's bid; history stops on the minute close (G1) or candle low (S1). The first G1 live trade showed what that gap can mean (-73 % vs a 50 % stop).

## What the pre-registration discipline did and did not do
- Worked: dozens of ideas were closed with their numbers; several apparent leads (call mirror, FII/DII, score, formation) did not survive the discipline; the discipline caught circular passes (7 Nov) and
  its own errors (event date, lot size, stray bar).
- Did not: the user's decisions twice put a rule live **before** its pre-registered test (v11, G1), S1 v12's trail gap was chosen after seeing results, and for S1 v2 to v10 there is no trial counter.
  Every "history" number for G1 / G1-F / S1 v12 is in-sample.

## Maintaining this journal
Add an entry per major change (date, commit, what, evidence). Update the four files together. Do not rewrite earlier entries: append, and mark corrections as corrections.
