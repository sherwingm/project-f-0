# S3 G1 · NIFTY downside opening-range breakout, put held overnight, sold at the next open (pre-registered 2026-11-04)

**Why:** the user, 2026-11-04: "now we will optimize the put1", "try applying the rule i have said for b2
optimization", "why dont we use the gift nifty to check whether to hold or sell . this is the strategy to capture the
next day run", then "Yes, pre-register G1". Buy only, 1 lot. Nothing here changes S1, S2 or the live server.

**What was seen before this page (disclosed):** `data/results/S3_PUT1_hold_report.md` (1f23d79b), 2024-10-01 →
2026-10-28 NIFTY option minutes, in-sample (PUT1's puts had already been priced on these minutes). Seven variants of
PUT1 were tried there; G1 was the best:
- 259 trades, **+8.4 % of the premium a trade** after slippage and charges (median −14.2 %, t 1.72, won 42 %),
  +₹122,592; years +7.0 % (128) / +9.7 % (131). Max up while held mean +54 %, median +29 %, ≥ +100 % on 20 %.
- PUT1 itself (sold 15:15, no stop) −1.2 %; 50 % stop, sold 15:15 −1.5 %; held to the next day's 15:15 +6.6 %.
- 191 of 259 trades were held overnight; the next open gapped down on 100 (+65.8 % sold at the open) and up or flat on
  91 (−9.2 %). The gap is not known when the trade is held at 15:15, so it is not a rule; GIFT Nifty history is not
  stored and the opening gap stood in for it.
- Picked as the best of seven on the same data, so +8.4 % is flattered. No unseen option history is left (2022-24 has
  no option minutes, and the user said on 2026-11-03 not to use 2022-24 again), so **the test is forward only**.

## Rules (no open parameters)
- **Opening range:** NIFTY 50 high and low of the 1-minute bars 09:15-09:29.
- **Signal:** the first 1-minute close outside the range, 09:30 → 13:00 (`scanner.s3_b2.signal`, no acceptance).
  **Trade only when it is below the low.** A day whose first breakout is upward has no trade. One trade a day.
- **Option:** the at-the-money put (strike nearest NIFTY's close of the entry minute, 50-point steps) of the nearest
  weekly expiry after the signal day (so at least one session is left).
- **Entry:** the minute after the signal minute.
- **Stop:** the put's value ≤ 50 % of the price paid, checked on every second (minute in the history) from entry to
  the exit, both days; an opening gap through it sells at the first quote.
- **Exit:** if the stop has not acted, hold overnight and **sell at the next session's 09:16** (the minute's last
  quote). No target, no other exit. Overlaps cannot happen (held one night, one trade a day).

## Forward stage (the test)
- **Sessions:** from 2026-11-05 on, as `index_data.pull_1s` brings each day's 1-second file from the live recorder
  (`<store>/nifty_1s/<day>.parquet`). Research only, run from this repo (`python -m scanner.s3_g1_forward`); nothing
  runs on the live server and nothing is ordered.
- **Prices:** NIFTY 50 1-second last prices → 1-minute bars for the signal. The put is **bought at the ask** (the
  last quote of the entry minute) and **sold at the bid** (the stop's second, or the last quote of the 09:16 minute).
  No added slippage: the spread is the real one. Charges from `server/charges.py`, the lot at entry (65 now).
- A day with no quote for the put within 60 seconds of the needed minute is listed as skipped with the reason,
  never filled by guess. A trade waits for the next session's file before it is booked.
- Also reported (no effect on the verdict): max up while held and to the next day's 15:29; the opening gap; the same
  trades priced on minute closes + the engine's slippage (`options_1m`), once the nightly re-fill has them, to see how
  far the history's fills were from the real bid / ask.

## Gate, judged once the 30th trade is booked (the S3 buy gate)
1. 30 trades.
2. Mean net % of the premium > 0.
3. At 2× charges (the real spread kept once) the mean is still > 0.
4. t ≥ 2.
5. Both halves positive (trades 1-15 and 16-30).
6. The worst trade's ₹ loss is smaller than the average month's ₹ result.

Thirty trades are few: with the history's +8.4 % and spread, t ≥ 2 on 30 is unlikely even if the edge is real. A
fail closes G1; it is not rescued by changing the stop, the exit minute or the window.

## After the verdict
- **Pass:** a proposal to the user to run G1 as a paper strategy. Nothing is enabled automatically, and S1 / S2 are
  untouched.
- **Fail:** the overnight-put lead is closed. The result goes to DECISIONS.md either way.
