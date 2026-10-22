# S1 fade · entry probe: what entry would pay v11's backtest price? (record only, from 23 Oct 2026)

Written 22 Oct 2026 evening, before any probe data exists.

## Question (the user's, 22 Oct)
v11's backtest made +₹3.23 L when it bought at the **09:15:00 opening print**; on the realistic entry (09:16 candle
open + 1 tick) it made +₹0.66 L. Now that the live server is always on (AWS Mumbai, 1-second loop), what kind of entry,
if any, would actually get the opening-print price?

## What is recorded (server/fade.py `entry_probe`, no trades)
For each fade signal of the day, the first 8 strikes of its walk path (nearest the money first), one Kotak quote call:
- every second 09:14:50–09:20:00, then every 10 s to 10:00;
- per row: time, strike, best ask and size, best bid and size, last price, last trade time, day volume, the day's
  **open** (Kotak `ohlc.open`, i.e. the opening print the backtest used), ATP, underlying;
- only rows that changed since the previous second are kept.

File: `data/entry_probe/<date>.json` on the server, mirrored to the `paper-state` branch.

## What is computed after each session (fixed now)
For each signal:
1. **The backtest's contract:** walk the strikes as v11's backtest did, using the opening prints: the first strike
   whose open ≥ ₹2 and whose lot costs ₹600–8,000. Its open = **P0**, the backtest's entry price.
2. For that contract, report:
   - the ask at the first recorded second at or after 09:15:00, and at 09:15:05, 09:15:45 (the old bot's typical
     fill) and 09:16:00 (the realistic entry B), each as % above P0;
   - **the first time the ask was ≤ P0 + 1 tick** (when a market buy at the backtest price was possible), or "never
     by 10:00";
   - whether the last price ever traded ≤ P0 after 09:15:00 (a resting limit buy at P0 could fill), and when;
   - the live entry the bot actually made that day (price and time), if any.
3. **Verdict per signal, one of:**
   - **A. fast market order:** the ask was within 1 tick of P0 in the first 5 seconds;
   - **B. limit order at P0:** not A, but the ask or a trade reached P0 later (time given);
   - **C. not obtainable:** neither, by 10:00.

## Reading it
- One day has few signals. The verdict counts (A / B / C) only become a rule decision after **at least 20 signals**
  across sessions. Until then the daily notes are descriptive only.
- A **limit order at P0 (B)** changes which trades fill. The ones that never come back to P0 are often the winners
  that run straight up. So B's fills alone cannot reproduce ₹3.23 L; the missed trades must be counted too.
- Nothing live changes from this probe; any entry change needs the user's decision and a DECISIONS.md entry.
