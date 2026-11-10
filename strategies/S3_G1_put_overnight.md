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

## Second track: G1-F (added 2026-11-04, before any forward session exists)
The user, after the datasheet (`data/results/S3_G1_datasheet.xlsx`, `S3_G1_filters.md`): "check whether removing the
negative mean and increasing the doubt trade of positive mean help", then "Yes, add G1-F".
- **Same trades as G1, but skip the day** when any of these holds at the signal (all known then):
  1. **day-1 opening gap ≥ +0.3 %**: the 09:15 open against the previous session's last close;
  2. **opening-range width 0.5 % to under 0.8 %**: (range high − range low) ÷ range low;
  3. **India VIX ≥ 17** at the signal minute (its last 1-second print up to the end of that minute).
- 1 lot (doubling was tried and not kept: it added ₹ and drawdown, not return on the ₹ paid). A day whose previous
  close or VIX is missing is not traded by G1-F, and is listed.
- **Seen before (disclosed):** in-sample on 2024-10 → 2026-10, G1-F was 154 trades, +18.3 % a trade, +17.9 % on the ₹
  paid, t 2.56, worst −₹6,359; the three buckets were picked from nine tables on the same data. Picked on year 1
  alone and applied to year 2, bucket filters lifted year 2 only from +4.3 % to +7.0 % on the ₹ paid. Each of the three
  skip buckets was negative in both years.
- **Gate:** the same six checks on G1-F's own first 30 trades (about 6 a month, so roughly five months). G1 and G1-F are
  judged apart; a G1-F pass with a G1 fail is reported as such, and neither is enabled automatically.

## Live paper on the website (added 2026-11-04, the user: "make this live in the website ... the same as how the s1 do")
- `server/g1_live.py` runs the same rules on the live server every second from the Upstox stream (the NIFTY recorder's
  subscriptions), in its own paper ledger `data/g1_ledger.json`: bought at the live best ask, stop and exit at the live
  best bid, charges from `server/charges.py`. G1-F is a flag on the same trade. Shown on `/index` (G1 section and Pods
  table), API `/api/index/g1`. Paper only: no order is sent; the S1 account and rules are not touched. Switch:
  `G1_PAPER` (default on).
- The verdict still comes from `scanner/s3_g1_forward.py` on the recorder's 1-second files (the written record); the
  live ledger is the same trade seen in real time and should match it. Any gap between the two is reported.

## Exit change: hold to the next session's close (2026-11-06, before any live trade)
The user: "keep the next day close rule as live", then chose "next-day close, keep the 50 % stop". From 2026-11-06 the live
paper exit of G1 / G1-F is: the 50 % stop as before (any second, both days), else sell at the best bid at the first quote of
the next session's **15:29 minute** (the close) instead of the last bid of the 09:16 minute. If the server misses that close,
it sells at the first bid of the following session and says so. The entry, the filters and the 30-trade gates are
unchanged, and the gates count only trades under this exit (there were 0 live trades before the change).
- Why: the user's measure is max up after entry, not the exit. Through the next close 38 % of G1-F history trades (31 % of G1)
  reached +100 %, against 23 % (20 %) by 09:16 (`g1_research/`). It is a peak measure, not a booked result: in history
  holding to the next day booked about the same or a little less than the 09:16 exit (PUT1 held to next-day 15:15 +6.6 %
  vs G1 +8.4 %, descriptive, same trades).
- The 2025 → 2026 history results quoted for G1 / G1-F elsewhere on this page still describe the 09:16 exit. Near Tighty
  (its own part) keeps the 09:16 exit.

## G1-F is the main track (2026-11-06)
The user: "make the g1-f as main". From 2026-11-06 G1-F is the main track: shown first on `/index` (G1 is the
baseline beside it), and the open / close alerts say whether G1-F counts the trade. Nothing else changes: the rules, the
skip filters, the paper ledger (every G1 trade is still recorded with its G1-F flag), and the two separate gates (30
trades each). Paper only; no real order, and no change to S1 or S2. A G1-F pass with a G1 fail (or the reverse) is still
reported as it is.

## Reporting default (2026-11-07)
Every G1 / G1-F report shows max up first (share reaching +50 / +100 / +200 %, mean, median), then the booked result. The `/index` Pods table does the same.

## Strike choice checked: ATM stays (2026-11-09, verification of public claims)
Pre-registered ATM vs 1 / 2 / 4 strikes ITM (and 1 OTM) on the 259 history signals, live exit, 1x and 2x costs (`g1_research/VERIFY_RESULT.md`): no strike beats ATM per rupee at risk.
ITM wins more often and loses less on a bad trade but reaches +100 % less often (34 % ATM, 28 % two ITM, 20 % deep ITM) and costs about twice the premium per lot; its bigger rupee totals come from more money at risk.
So the live strike stays ATM. The call mirror held overnight lost at every strike, so G1-C is not built.

## After the verdict
- **Pass:** a proposal to the user to run G1 as a paper strategy. Nothing is enabled automatically, and S1 / S2 are
  untouched.
- **Fail:** the overnight-put lead is closed. The result goes to DECISIONS.md either way.
