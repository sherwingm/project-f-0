# S1 v10 fade · shadow exit "−20 % stop-loss, else 15:20" (live paper)

> **Superseded 2026-10-20 before any tagged trade:** the −20 % stop became the live exit (S1 v11,
> `strategies/S1_v11_fade_stop20.md`), and the 15:20 exit became the shadow (`rule.shadow_v10`). No trade was ever
> tagged under this page.

**Pre-registered 2026-10-20** at the user's request ("add the -20% stop loss to fade as shadow tag"), before any live
trade is tagged. Paper only. **S1 v10 is not changed**: every fade trade is still bought as before and sold at 15:20.
No extra order is placed. The +100 % shadow exit (`S1_v10_t100_shadow_track.md`) and the sub-₹2 shadow entries are
unchanged. A trade can be tagged by both shadow exits; each is judged on its own against the real 15:20 exit.

## Why
- On real day-0 option highs and lows, a −20 % stop looked best of the stop levels on 2025-26: +₹1,47,707 vs
  +₹1,26,164 with no stop, t 1.76 vs 1.35 (`data/results/S1_v10_stoploss_study.md`).
- But that test filled every stop exactly at −20 %, which is optimistic in a fast fall. The stop fired on 71 % of
  trades, which closed about −20.8 % at 15:20 anyway, and in 2022-24 it was neutral (+3.3 % vs +3.6 % a trade).
- So the rule stayed unchanged (DECISIONS.md, S1 v10 row). Live fills at the real bid show what the stop would have
  done, without the optimistic fill. FEDERALBNK on 2026-10-19 (−91 % at 15:20, about −90 % by 12:00) prompted it.

## The shadow exit (fixed now)
- At entry each fade position gets `rule.shadow_s20 = {"stop": entry × 0.80, "hit_at": null, "fill": null,
  "min_bid": null}`.
- **Aligned 2026-10-20 to S1 v11** (`strategies/S1_v11_fade_stop20.md`), before any tagged trade: the stop is active
  from **09:16:00**, never in the 09:15 minute.
- On every poll while it is open, on the entry day from entry (and from 09:16) until before 15:20, the trader reads the option's
  **best bid**. It keeps the lowest bid seen (`min_bid`).
- **The first poll whose best bid ≤ the stop fires the shadow stop, filled at that best bid**, the price a market
  sell would get at that moment, not the stop level. The time and the fill are recorded.
- A gap through the stop between polls (about 30 s apart) fills at the lower bid, which is realistic. A poll with no
  bid is skipped.
- Shadow net ₹ = (fill − entry) × qty − the real entry charges − the exit charges of a sale at the fill
  (`server/charges.py`). If the stop never fired, the shadow net equals the real 15:20 net.
- Only positions opened after this tag exists are compared; earlier fade trades are "untagged".

## Report
`/api/paper/summary` → `fade_s20`, and an Arm F panel "Shadow exit: −20 % stop, else 15:20". For the tagged closed
trades it shows N, wins, mean net % and total net ₹ under the real exit and under the shadow stop, plus stops fired
and, of those, how many would have done better at 15:20 (the trades the stop cut too early).

## How it is judged (fixed now)
Descriptive until **at least 30 tagged fade trades** have closed. Then the comparison is the per-trade difference
(shadow net % − real net %), with a date-clustered t. The stop can become the rule only if the shadow does better
with t ≥ 2, the user agrees, and a new pre-registered version records it in DECISIONS.md.

## Known limits
- Polls can be late, which can only make a fill later: lower in a fall, or higher if the price recovers.
- Bids on cheap options move in ticks, so −20 % of a ₹2.50 option is a few ticks.
- Most fade trades dip early: in the backtest, 53 % of dips came in the first 15 minutes. So a −20 % stop will fire
  often, including on trades that recover by 15:20. The report counts those.
