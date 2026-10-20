# S1 fade · re-run the backtest with a realistic entry price (09:16 candle)

**Pre-registered 2026-10-20**, before any new number is computed. The user said yes to: "Re-run the fade backtest with a
realistic entry price (the 09:16 candle)". **Nothing live changes.** Numbers only.

## Why
The backtest buys at day 0's bhavcopy open + 1 tick. On 1-minute data that print is often stale (median swing inside
the 09:15 minute: 51 %; BAJFINANCE 2024-10-23 bought 54.45, the 09:15 candle low 7.15, close 8.19). The live bot buys at
the live ask on a poll after 09:15. So the old totals (v10 +₹1.70 L, v11 +₹2.51 L) may be wrong in both directions.

## Trades
- The same trades as `data/results/S1_v10_bandv10_contracts.csv` (the v10 ₹2+ band trades, day 0 from Oct 2024 to
  2026-09-25) that have day-0 minute candles in `S1_v10_bandv10_minutes.csv`. The contract is not changed.
- **Old entry (A):** the backtest's `entry_price`.
- **New entry (B):** the **09:16 candle's open + 1 tick** (tick ₹0.05 before 2025-11-03, ₹0.01 from it). No 09:16 candle
  (no trade that minute): the trade is excluded from B and counted.
- Both entries use the **same exit code**, so only the entry differs:
  - v10 exit: sold at the 15:19 candle's close − 1 tick;
  - v11 exit: the −20 % stop (0.80 × that entry), fired in the first candle whose low ≤ the stop, **from the candle after
    the entry candle** (A: from 09:16 as in the live rule; B: from 09:17), filled at min(stop, that candle's open) − 1
    tick; otherwise the v10 exit.
  - Real charges (`server.charges`), no extra % slippage, for A and B alike (so A will differ a little from the old
    published totals; the old totals are quoted beside it).

## Reported (descriptive; no pass test, nothing is chosen from it)
1. Per exit (v10, v11) and entry (A, B): N, win %, mean and median net % of premium, total ₹, date-clustered t.
2. By window (Oct 2024-Oct 2025, Nov 2025-Sep 2026) for B.
3. How many trades fail the rules at entry B (fill < ₹2, or one lot outside ₹600–8,000): their count and totals; B with
   those dropped.
4. The change in the 55 trades that lost −30 % to −85 % under A, and how many of the 104 trades whose first candle
   closed ≥ 20 % above A now look normal.
5. The biggest winners under A (≥ +300 %): what they are under B.
6. Whether the v11 − v10 gap (stop vs no stop) keeps its sign and size under B. This answers whether the live v11 rule
   still looks better than its shadow v10.

Reported honestly even if B kills the edge. A re-run of the other studies (floor, band, target, filter) is a separate
decision for the user.
