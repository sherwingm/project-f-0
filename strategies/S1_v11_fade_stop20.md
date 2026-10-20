# S1 v11 · results-day fade with a −20 % stop (paper; **live from 2026-10-21**)

> **Switched live on 2026-10-20 by the user's decision** ("make this strategy as main, and the old 15:20 exit as
> shadow"), before the 30-trade test below was run. From 2026-10-21 the live fade exit is the −20 % stop (from 09:16,
> at the best bid), else 15:20. The v10 exit (hold to 15:20) is tracked on every fade trade as a shadow tag
> (`rule.shadow_v10`): for a stopped trade, the contract's best bid at the first poll from 15:20 that day (else the
> last price − 1 tick), netted with real charges; for a trade not stopped, the same as the real result. The test
> below now runs in reverse: at 30 closed fade trades, if the v10 shadow beats v11 (mean (v10 − v11) net % > 0 with a
> date-clustered t ≥ 2), the user is asked whether to switch back. Otherwise v11 stays.

**Pre-registered 2026-10-20**, at the user's request ("Write it"), before any live trade is judged under it. v11 is
**v10 with one change, the exit**. **The live paper trader stays on v10** (sold at 15:20) until the user agrees to
switch. Switching needs this file's pass test, the user's yes, and an entry in DECISIONS.md, in its own commit.

## The rule
Everything in `strategies/S1_v10_results_day_fade_paper.md` is unchanged: signals, day 0, put on strong numbers,
call on weak ones, expiry, strike walk, ₹2 floor, ₹600–8,000 lot, 1 lot, entry at the live ask 09:15–15:20.

**Exit (the only change):**
1. **Stop:** from **09:16:00** on the entry day (and never before the entry), at each poll, if the option's **best
   bid ≤ 0.80 × the entry price**, sell at that best bid. With no bid that poll, wait for the next poll. A gap
   through the stop fills at the lower bid.
2. **Else 15:20:** the first poll from 15:20, at the best bid (else the last price − 1 tick), as in v10.
3. A position still open on a later day (server down) is sold at the first poll of that day, as in v10. It is
   reported, never judged.

No target, no trailing stop. The +100 % shadow exit and the sub-₹2 shadow entries stay tags only.

## Why (all of it seen before this page, so none of it is out of sample)
- **1-minute prices, Oct 2024 → Sep 2026** (`data/results/S1_v10_s20_minutes.md`; 468 v10 ₹2+ trades, entry day-0
  open + 1 tick, stop fill = min(stop, that minute's open) − 1 tick):
  - −20 % stop active from 09:16: +₹2,50,916, t 2.47;
  - the v10 15:20 exit: +₹1,70,405, t 1.71;
  - the stop is better in each window: Oct–Nov 2024 +31k vs +29k; 2025 +93k vs +62k; 2026 +1.27 L vs +80k.
- It fired on 316 of 468 trades. Of those that fired from 09:15, 56 % got back to entry later that day but only 23 %
  closed above it, with a median close of −31 %.
- **Against it:** daily prices on 2022-24 and 2025-26 (`data/results/S1_v10_stoploss_study.md`, fills at the level)
  found "no real gain": +3.3 % vs +3.6 % and +6.2 % vs +5.6 % a trade. Daily data cannot order the day's high and
  low, so it is weaker evidence, but it is the only evidence for 2022-24, where no minute data exists.
- The v11 numbers were found after looking at three exits (no stop, stop from 09:15, stop from 09:16) on one window,
  and the 09:16 start was chosen after seeing the 09:15 result. So the backtest edge is expected to be smaller live.

## How it is judged (fixed now)
**Fresh live trades only.** Every v10 fade position opened from 2026-10-20 carries `rule.shadow_s20`
(`strategies/S1_v10_s20_shadow_track.md`). This page aligns that tag to the rule above: from 09:16:00, best bid ≤
0.80 × entry, filled at that bid. Each tagged trade has a real v10 result and a v11 result on the same fill prices.

- **When:** at **30 closed tagged trades** that were sold on their entry day (the v10 review's own rule), or later if
  the user wants more.
- **Measure:** per trade, d = v11 net % of premium − v10 net % of premium, with a date-clustered t over the 30+.
- **v11 passes only if all of these hold:**
  1. mean d > 0 with t ≥ 2;
  2. the v11 total net ₹ > the v10 total net ₹ over the same trades;
  3. the v11 total net ₹ > 0;
  4. the result is not carried by one day: it still holds without the best day's trades;
  5. the user agrees.
- **Pass:** the live paper trader switches its fade exit to v11 (a code change in `server/fade.py`, with tests), and
  DECISIONS.md records it. **Fail or too close to call:** v10 stays; the result is recorded here and in DECISIONS.md.
- The v10 review (30 closed trades or 6 weeks) runs as before and is not affected.

## Known limits
- Live polls are about 30 s apart, and a slow or sleeping server can make a stop fill late and lower. That counts
  against v11, as it would in real trading.
- One tick (₹0.01) is small next to −20 % of a ₹2+ option, so the stop fills close to its level unless the price
  gaps.
- 30 trades is a small sample. A pass is evidence, not proof; a fail at t < 2 means "not shown", not "wrong".
