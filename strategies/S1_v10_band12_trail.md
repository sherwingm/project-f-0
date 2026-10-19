# S1 v10 fade · options priced ₹1–2: the ₹0.50–1 minute test applied to the ₹1–2 band

**Pre-registered 2026-10-19**, before any ₹1–2 contract is picked or any minute candle is fetched. The user's
request: "now we will try the test little success of range .5 to 1 with the 1-2 range only this". That is the ₹0.50–1
test (`strategies/S1_v10_band050_trail.md` and its addendum 2), run on the ₹1–2 band only. The ₹0.50–1 rule failed its
own test, and that file said the ₹1–2 step would then not run. **The user chose to run it anyway**, so this is a
separate study, not a follow-on pass. Descriptive. **The live v10 rule (₹2 floor, 15:20 exit) is not changed.**

## Trades
- As the ₹0.50–1 study: every S1 v10 fade signal with day 0 in 2025-01-01 → 2026-09-25 (`S1_v10_trades_floor0p05.csv`).
  From v10's start strike, walk away from the money. Take the first strike with **day-0 open + 1 tick in [₹1.00,
  ₹2.00)**, ≥ 50 contracts on day 0, and one lot at that price within ₹600–8,000. One lot.
- Day-0 1-minute candles from Upstox's expired-instruments API, fetched on GitHub
  (`index_data/fetch_band_minutes.py`, band 12).

## Ticks and costs (corrected after the 2026-10-19 audit)
- **The NSE tick for stock options was ₹0.05 up to 2025-10-31 and ₹0.01 from 2025-11-03.** In the cached option files,
  every price under ₹5 is on the ₹0.05 grid up to 31 Oct, and about 20 % are off it from 3 Nov.
- **Primary cost per side:**
  - before 2025-11-03: ₹0.10 (the ask + 1 tick of ₹0.05, as before);
  - from 2025-11-03: **₹0.04**, about half the ₹0.04–0.07 spreads seen live today on ₹1–2 options (FEDERALBNK /
    UJJIVANSFB chains, 2026-10-19) plus 1 tick of ₹0.01, rounded up.
- Entry = the 09:15 minute's close + that cost (else the first minute up to 09:20; none, excluded). Exit = the price
  − that cost, not below 0.
- Targets round up and stops round down to that date's tick. Charges from `server/charges.py` on both orders.
- **Sensitivity (shown, not judged):** ±₹0.10 throughout (the old model), and ±₹0.02 from 2025-11-03 (optimistic).

## Exits (the same ten as the ₹0.50–1 study)
- **Baseline:** the 15:20 sale (the 15:19 minute's close − cost).
- **R10 / R20 / R30:** +20 % target, with a 10 / 20 / 30 % trailing stop before it.
- **A10 / A20 / A30:** +100 % target, with a 10 / 20 / 30 % trailing stop before it.
- **B10 / B20 / B30:** no stop until +100 %. Then a 10 / 20 / 30 % trailing stop from the peak; else 15:20.
- Fills as before. A target fills at the first minute whose high ≥ target + 1 tick. A stop is checked against each
  minute's low before the peak updates, and fills at min(stop, open) rounded down to the tick − cost. If one minute
  touches both, the stop is taken.

## Choose, then test once
- **Choose on 2025** (day 0 2025-01-01 → 2025-12-31): of the nine, the highest total net ₹. A tie goes to the wider
  trail, then R, A, B.
- **Test on 2026** (day 0 2026-01-01 → 2026-09-25): the chosen exit only, once.
- **Pass:** on 2026, the chosen exit's total net ₹ > 0, **and** mean net % > 0 with a date-clustered t ≥ 2, **and** it
  beats the 15:20 baseline's total.

## Known limits
- Nine exits on about 60–80 trades per year, so the best of nine on 2025 is expected to look better than it is.
- The 2026 fade signals were seen in earlier studies, but not this band with these exits.
- The ₹0.04 cost after Nov 2025 comes from a few live chains on one day; the sensitivity rows bracket it.
- Minute candles show trades, not quotes.

## Addendum 2026-10-19 (2) · 2022-24, before vs after (user's request: "Make the backtest in 2022 to 2024 and give me before and after result")
Written before any 2022-24 band number is computed.
- **No minute data exists for 2022-24.** Upstox's expired stock-option candles start with the Oct 2024 expiries, so
  this run uses the day-0 option open / high / low / close from the cached NSE files. That window had a ₹0.05 tick,
  so the cost is ₹0.10 a side throughout.
- **Trades:** the same pick as the 2025-26 study, on the 2022-24 fade signals (`S1_v10_trades_2022_24_floor0p05.csv`),
  for both bands: ₹1–2 and ₹0.50–1.
- **Before:** the 15:20 exit = buy at day 0's open + ₹0.10, sell at day 0's close − ₹0.10, real charges.
- **After:** B30, the exit chosen on 2025 for ₹1–2 (hold until +100 %, then a 30 % trailing stop). Daily data cannot
  order the prices inside the day, so it is reported as a range:
  - armed when the day's high ≥ 2 × entry + 1 tick, else the 15:20 exit;
  - **optimistic** when armed: max(close, 0.70 × high, rounded down to the tick) − ₹0.10;
  - **pessimistic** when armed: min(close, 0.70 × the target, rounded down to the tick) − ₹0.10. That is the stop
    firing right after arming, at the lowest peak it can have.
- **Check of the method:** the same daily calculation on the 2025 trades, set beside the minute-data results
  (₹1–2: baseline +₹36,757, B30 +₹47,775), to show how far the daily range is from the real one.
- Also: v10 as today (₹2+, 2022-24: 436 trades, +₹24,190) alone, and with each band's trades added (before / after).
- Descriptive; nothing here changes the verdict of the 2026 test or the live rule.
