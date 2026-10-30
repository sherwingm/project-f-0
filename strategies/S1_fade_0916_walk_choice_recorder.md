# S1 fade · the 09:16 walk-choice recorder (record only, from 2 Nov 2026)

Written 30 Oct 2026. Approved by the user ("Do it", 30 Oct 2026) as a measurement-only change. It trades nothing:
no order, no position, no change to the live entry, the exit, sizing or any ledger field.

## Why
The 09:16 counterfactual (`strategies/S1_fade_0916_entry_counterfactual.md`) keeps the **same contract** as the
09:15 trade and only moves the time. But by 09:16 the price has moved, so the live walk would often have bought a
different strike: in the first run, 5 of 13 changed trades. That other strike's prices were not recorded after
10:00 (the entry probe stops there and only covers 8 strikes), so its outcome could not be rebuilt. This recorder
writes down which contract the live entry would have bought at 09:16, and that contract's book until the close.

## What it records (`server/fade.py` `walk_0916`, called by the 1-second loop after `entry_probe`)
1. **The choice, 09:16:00 to 09:20:00.** Every second, for each of today's fade signals not yet decided:
   - one quote of its whole walk path (up to 15 strikes), which reuses entry_tick's quote call from the same second
     when it has one;
   - `decide_0916`, the live entry decision run on that book without buying. It applies the gates in
     `FadeTrader._entries`' order: the first-trade-today gates, the lot-size check, `walk()` and the below-₹2 rule.
     Tests keep it equal to the live entry (`tests/test_fade.py` `test_decide_0916_matches_the_live_entry`: the
     same book gives the same strike, price and lots, the same wait reason or the same refusal);
   - the first second it returns "chosen" is the signal's **09:16 choice**: decision time, strike, ask, lot, lots,
     the entry quote, and the book of every walk-path strike at that second. "Refused" (it never fits) stops the
     tries; "waiting" keeps the first and the latest reason; no choice by 09:20:00 → "none by 09:20".
2. **The follow, choice to 15:21.** The chosen contract's best bid / ask goes into the observation record
   `data/observations/<date>.jsonl` as phase **`walk_0916`**, id **`w0916:<date>:<symbol>`**. A row is written only
   when the best bid or ask **price** changes (size-only changes are skipped, so the day's file stays small). Every existing reader filters rows by its own trade
   id, so these rows enter no trade, peak or page.
3. **The file** `data/walk_0916/<date>.json` (choices, tries, reasons, follow counters: polls, polls without a
   quote, polls on Kotak, first / last poll). It is written when a choice is decided, every 30 minutes, and once
   after 15:21, then mirrored to `paper-state` like the entry probe. After a restart during the day, the server
   reads it back and goes on (`restarts` lists when).

## Cost and safety
- While prices come from the Upstox stream (normal), the extra quotes come from the stream's memory, with no
  broker call. While they come from Kotak (fallback), it tries at most every 10 s and follows every 30 s (the
  60-minute post-exit follow uses the same cadence), to stay inside Kotak's rate limit.
- Any error is logged and swallowed inside `walk_0916`, so the 1-second trading loop (exits, entries, alerts)
  always goes on.
- Disk: about one changed-book row per second per chosen contract at most, roughly 1-3 MB a day for 5-10 signals.

## Used by
The re-run's consistency check C3 (`strategies/S1_fade_0916_rerun_prereg.md`) and its replay rules, written there
before any data exists. It can be switched off after the question is closed, with the user's approval.
