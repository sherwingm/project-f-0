# S1 v10 fade · the sub-₹2 entries the floor refuses (backtest + live shadow entry)

**Pre-registered 2026-10-19**, before any sub-₹2 number from this study is computed. Note: the 2025-26 floor sweep
(addendum 2026-10-19 in `S1_v10_backtest_2025_26.md`) already reported the sub-₹2 trades pooled, under the old cost
model. This study uses a stricter tick-based cost model, adds 2022-24, and adds the splits below. Descriptive. **The
live v10 rule (₹2 floor) is not changed**; any change goes into DECISIONS.md with the user's agreement.

## Hypothesis
The fade trades v10 refuses today because the option's price is below ₹2 add money on top of the ≥ ₹2 trades, after
realistic costs for cheap options.

## Data
- `scanner.backtest_s1_v10` with the floor at one tick (`--min-premium 0.05`), entry = day 0's open:
  - 2025-01-01 → 2026-09-25: `S1_v10_trades_floor0p05.csv` (already run for the floor sweep);
  - 2022-01-01 → 2024-12-31: `S1_v10_trades_2022_24_floor0p05.csv` (run for this study).
- The walk is v10's, unchanged apart from the floor: start at the strike nearest the previous close, walk away from
  the money, first strike with ≥ 50 contracts on day 0 and one lot at the fill within ₹600–8,000.
- **Sub-₹2 set:** trades whose walk fill (open + 1 tick) is below ₹2, the ones the ₹2 floor refuses. Only E1-valid
  trades (a day-0 close exists).
- **≥ ₹2 comparison line, not re-run:** 2025-26 = 434 trades, +₹1,26,164, 40.1 % win rate (15:20 exit, existing
  cost model). 2022-24 = the E1-valid trades in `S1_v10_trades_2022_24.csv`, same model. For information only, the
  same ≥ ₹2 trades are also recomputed under this study's tick model from those CSVs.

## Cost model (primary: tick-based)
- NSE's bhavcopy has no bid or ask, so both are stand-ins. ask ≈ open + 1 tick, and the **entry is the ask + 1 tick
  = day 0's open + ₹0.10**. bid ≈ close − 1 tick, and the **exit is the bid − 1 tick = day 0's close − ₹0.10** (not
  below 0). No % slippage on top.
- Charges from `server/charges.py` on both orders: ₹20 brokerage per order, STT on the sale, exchange, SEBI, stamp,
  GST. Charges are shown as % of lot value per band.
- Sensitivity: 1 tick each side (open + ₹0.05, close − ₹0.05), no % slippage.
- The walk's choice of strike is not changed by the cost model.

## Liquidity
- A two-sided quote **cannot be observed**: the bhavcopy has no bid / ask. Reported as not available.
- Funnel: signals the ₹2 floor refuses; of them, the ones the floor-free walk trades; and on the traded signals'
  walk paths (start strike to traded strike, from day 0's option file), the share of strikes priced below ₹2 that had
  ≥ 50 contracts.

## Report
For each window and both pooled, per band and in total for the sub-₹2 set: N, win rate, mean and median net % per
trade, total net ₹, max drawdown (₹, on cumulative net in day-0 order), date-clustered t, % of trades whose day-0 high
reached 2 × entry, and charges % of lot value. The bands are by walk fill: < ₹0.50, ₹0.50–1, ₹1–1.50, ₹1.50–2.
- Split by **sessions to expiry** after day 0, counting the expiry day: ≤ 2, 3–5, > 5.
- Split by **strike distance out of the money** from the previous close: ≤ 2 %, 2–5 %, 5–10 %, > 10 %.
- The ≥ ₹2 comparison line above.

## Pass criterion ("the sub-₹2 trades add money"), fixed now
Under the primary tick model, all three must hold:
1. Total net ₹ of the sub-₹2 set > 0 in **each** window (2022-24 and 2025-26).
2. Pooled mean net % > 0 with a date-clustered t ≥ 2.
3. Pooled total net ₹ > 0 **without the single largest ₹ winner**. The floor sweep showed one trade, KALYANKJIL
   2025-08-08, can carry the set.

Otherwise the verdict is "does not add money". Either way it is descriptive: not out of sample (2025-26 is the S1 v8
holdout, and the sub-₹2 group was already seen pooled in the sweep), and no live rule changes from it.

## Live shadow entry (fixed now)
- When the live fade walk refuses a signal for "premium below Rs 2", the trader runs the **same walk on the same live
  quotes with the floor at one tick** (₹0.05). If it finds a strike (two-sided quote, spread ≤ 10 %, one lot at the
  ask within ₹600–8,000), that is the **shadow entry**: strike, the ask at that moment as entry, lot, lot cost and time.
  This is the same strike rule as the backtest above, so the shadow never breaks the lot-cost or liquidity rules.
- If that walk finds nothing (lot below ₹600, nothing in band), there is no shadow entry. Refusals for any other
  reason (lot cost, spread, no quote) never create one.
- One shadow entry per signal per session, made at the first refusal. If the real trader later buys the same signal
  (its ask rose to ₹2 or more), the shadow is kept but flagged `real_bought` and left out of the judged set.
- No order and no ledger position. The entry is stored in the rule state (`rules.fade_shadow_entries`). Each poll it
  records the best bid and the highest bid seen. Its exit is the first poll from 15:20 on the entry day, at the best
  bid (else the last price − 1 tick), exactly like the real fade exit. If that poll is missed, the exit is the first
  poll of a later day, flagged late. Net = (exit − entry) × lot − charges on the buy and on the sale (`server/charges.py`).
- Shown on the Arm F tab, "Shadow entries: sub-₹2 refusals", with the real trades' columns.
- **Judged at 30 closed, judged shadow entries.** It becomes a real rule only if the shadow net beats zero (mean net %
  per trade > 0 and total net ₹ > 0) with a date-clustered t ≥ 2, the user agrees, and a new pre-registered version
  records it.
- The +100 % shadow exit and the real exit are not touched.
