# S1 v10 fade · shadow exit "+100 % target, else 15:20" (live paper)

**Pre-registered 2026-10-19** at the user's request: "Add a +100% target as a shadow tag on live fade trades (no change
to the real exit) so we can compare it on fresh trades". Written before any live trade is tagged. Paper only. **S1 v10
is not changed**: every fade trade is still bought as before and sold at 15:20. No extra order is placed.

## Why
The pre-registered target-exit backtest (`strategies/S1_v10_backtest_2025_26.md`, addendum 2026-10-19 (2);
`data/results/S1_v10_target_exit.md`) gave a +100 % target +6.9 % a trade (t 2.2, Rs 1.37 lakh) against +5.6 % (t 1.3,
Rs 1.26 lakh) for the 15:20 exit. That is on the Rs 2 floor, 434 trades, 2025-26, and the difference is small. The
backtest is optimistic: daily highs have no timing, and the entry was the open. Live trades show whether the target is
reached after the real entry, at prices a seller can get.

## The shadow exit (fixed now)
- At entry each fade position gets `rule.shadow_t100 = {"target": entry x 2.00 rounded up to Rs 0.05, "hit_at": null,
  "max_bid": null}`.
- On every poll while it is open, before the 15:20 exit, the trader reads the option's **best bid**. The shadow sell
  fills at the target the first time a poll sees **best bid ≥ target**. That means a buyer paying at least the target,
  so a resting sell there would have filled. The time is recorded in `hit_at`, and `max_bid` keeps the highest bid seen.
  Prices between polls (about every 30 s) are not seen, which makes this slightly conservative.
- Shadow net Rs = (target − entry) × qty − the real entry charges − the exit charges of a sale at the target
  (`server/charges.py`). A trade whose target was not hit has the same net as the real 15:20 sale.
- Only positions opened after this tag exists are compared. Earlier fade trades are counted as "untagged".

## Report
`/api/paper/summary` → `fade_t100`, and the Arm F tab of the results page, show for the tagged closed trades: N, wins,
mean net % and total net Rs under the real 15:20 exit and under the shadow exit, plus targets hit.

## How it is judged (fixed now)
Descriptive until **at least 30 tagged fade trades** have closed. Then the comparison is the per-trade difference
(shadow net % − real net %), with a date-clustered t. The target can become a rule only if the shadow does better with
t ≥ 2, the user agrees, and a new pre-registered version records the change (DECISIONS.md).

## Known limits
- A one-sided result is likely: on most days the target is not hit and both exits are the same, so the difference
  comes from a few trades.
- Polls can be late (server sleep, slow quotes). A missed poll can only miss a hit, never invent one.
