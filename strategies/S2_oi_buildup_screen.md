# S2 · Price + futures OI build-up — step 1: the stock-level screen

S2, step 1, under `DECISIONS.md`. **Pre-registered**: every choice is fixed here before any run. This is a screen of
the stock's own move (not a trade); an option design (step 2) is written only for a cell that passes.
Run: `python -m scanner.s2_screen`.

**Why S2, and why this way.** S1 (the results-day drift) worked in 2021-24 and not in Apr 2025 – Sep 2026, after 8
versions (DECISIONS.md, 2026-10-14). The user chose to stop tuning S1 (its paper rule trades keep running) and to
start S2 on stock options, held 1-5 days, with signals from **price and futures open interest together**. S1 also
showed that a signal can be real in old years and gone in recent ones, so this screen judges every cell **year by
year, 2021 to 2026**, and needs it to hold in the latest years too.

## Data
- Universe: the stocks with stock-futures rows in that day's NSE F&O bhavcopy, 2021-01-01 → 2026-09-25 (the last
  session with eod2 stock closes).
- Stock open / close / volume: eod2 (adjusted). Futures open interest: **all expiries combined**, from the day's
  F&O bhavcopy (cached under `data/cache`).

## Day-d inputs (at the close of day d)
- Price change % = close d ÷ close d−1 − 1.
- OI change % = combined futures OI d ÷ combined futures OI d−1 − 1.
- Volume ratio = volume d ÷ the average of the 20 sessions before d.
- Skipped: day d that is a stock-futures expiry day, or the session after one (the monthly rollover makes the
  combined OI jump), and days without the previous session's OI.

## Classes (the trade direction is fixed in advance)
| Class | Price | OI | Direction |
|---|---|---|---|
| Long build-up | up | up | long (a call) |
| Short build-up | down | up | short (a put) |
| Short covering | up | down | long |
| Long unwinding | down | down | short |

## Grid (4 × 2 × 2 × 3 = 48 cells)
- |price change| ≥ **2 %** or ≥ **3 %**; |OI change| ≥ **5 %** or ≥ **10 %**; volume ratio ≥ **1.5** always.
- Holding **h = 1, 3, 5** sessions.
- One signal per stock per class per cell every 5 sessions (the first counts).

## Measure
- Enter at the **open of day d+1**, exit at the **close of day d+h**. Signed return (a short = −return), net of
  **0.1 %**. Also shown: the same net of the stock's leave-one-out sector over the same days.
- Per cell: N, mean, median, hit rate, date-clustered t, and the mean in **each calendar year 2021 … 2026**.

## Pass rule (per cell)
1. Date-clustered t ≥ **3** over all years (48 cells are tested, so 2 is too low).
2. Mean ≥ **+0.6 %** for h = 3 or 5, ≥ **+0.4 %** for h = 1 (big enough to survive option costs).
3. Mean positive in at least **5 of the 6 years, including both 2025 and 2026**.

## What follows
- No cell passes → S2's OI family is closed and recorded.
- A cell passes → step 2, pre-registered separately: the option trade for that cell (at the money or slightly in the
  money to cut time decay, nearest monthly with ≥ 10 sessions left, 1 lot, exit at h), backtested, then paper.

## Known limits
- Combined OI hides which expiry moved; expiry and rollover days are skipped instead.
- Sector membership is today's list applied to all dates.
- Daily data only: a signal is known at day d's close and traded from d+1's open.
