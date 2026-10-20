# S1 fade · drop the trades where Arm A also fires (descriptive study)

**Pre-registered 2026-10-20**, before any number of this study is computed. The user's request: "now we remove the
Arm A also fired on that stock, same results day and only keep the Arm A did not fire". **The live fade (v11) is not
changed.** A filter that passes becomes a candidate for the user's decision, as its own version with a DECISIONS.md
entry.

## The problem with the plain version
Arm A fires on the stock's **day-0 close** (S1 v4 signal: AR0 = the stock's P0 → day-0 close return minus its
leave-one-out sector's, ≥ +2 %, and the raw move < +10 %). The fade buys from 09:15 on day 0 and sells by 15:20, so
it can never know at entry whether Arm A will fire. Dropping those trades uses the day's result to remove losers.
It is computed (**H**, below) only as the most such a filter could ever be worth, never as a rule.

## The two versions
- **H (hindsight, not usable):** drop a fade trade when its stock is an Arm A beat that day0: AR at the day-0 close
  ≥ +2 % and the raw close move < +10 %. Same calculation as `backtest_s1_v4.signals` (signal level only: Arm A's
  later option filters, ban list and cooldown are not applied).
- **O (at the open, usable):** the same test on day 0's **official open** instead of its close, known at 09:15
  (the pre-open auction):
  - raw gap = day-0 open ÷ previous close − 1;
  - sector gap = the equal-weight mean of the other stocks of its sector (`data/sector_map.csv`) with an open and a
    previous close that day, at least 3 of them; otherwise NIFTY 500's open ÷ previous close − 1;
  - AR open = raw gap − sector gap. **Drop** when AR open ≥ +2 % and raw gap < +10 %.
  - Prices: eod2 daily files (`data/eod2/`), opens and closes on the same adjustment.
- **Both sides are filtered** (puts and calls), as the user asked. Puts and calls are also reported separately.
- A trade whose AR cannot be computed (no eod2 row, no previous close) is **kept** and counted.

## Trades
- The v10 backtest's primary entry (`entry = open`: the option's day-0 open, + costs), E1 same-day exit:
  - 2022-24: `data/results/S1_v10_trades_2022_24.csv`;
  - 2025-26: `data/results/S1_v10_trades.csv`.
- The v11 exit (−20 % stop from 09:16 at the bid, else 15:20) on 1-minute prices, Oct 2024 → Sep 2026:
  `data/results/S1_v10_s20_minutes_trades.csv` (`s20_net` = v11, `e1_net` = v10).
- Cross-check (2025-26): H's flagged trades against the real Arm A trades in `data/results/S1_v8_trades.csv`.

## Report
For all / H-kept / H-dropped / O-kept / O-dropped, per window and pooled, puts and calls separately: N, win rate,
mean and median net % of premium, total ₹, date-clustered t. Also the overlap of O with H (how many of Arm A's days
the open already shows). The 1 % and 3 % thresholds for O are reported as descriptive extras only; they do not count
for the test.

## Pass test for O (fixed now; all three needed)
1. The O-dropped trades lose in **each** window: mean net % < 0 in 2022-24 and in 2025-26 (E1 exit).
2. Pooled 2022-26, the O-dropped trades' mean net % has a date-clustered **t ≤ −2**.
3. On the minute trades, the O-dropped trades also lose under **v11's** exit (mean `s20_net` % < 0).

If all three hold: O is a candidate filter for the user's decision (no live change here). Otherwise nothing changes.
H is never judged; it is the ceiling.

## Limits
- The live fade fills at the live ask from 09:15, often minutes after the open; the backtest's open fill is the
  option's official open.
- The open is the pre-open auction price; the stock may move in the first minutes before the fill.
- 2025-26 has been read many times for the fade (floor, target, stop studies), so its result is not fresh.
