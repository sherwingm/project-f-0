# S1 fade · cheap options (< ₹10) only when ≥ 7 / ≥ 10 sessions before expiry, same-day v12 exit (backtest)

**Pre-registered 2026-10-21**, before any of these numbers is computed. The user, after the 146-example sheet of
refused cheap options (`data/results/S1_refused_below_floor_all.xlsx`, median −71 % by 3 days before expiry): "take
the trade if the open price of the contract is below 10 ... if before 7 days before expiry or maybe 10 days". Answers:
exit = **same day, v12**; price band = **everything below ₹10, one lot still ₹600–8,000**; cut-off = **test 7 and 10**.
**Nothing live changes.**

## Trades
- Every contract with day-0 option minutes, pooled from the five sets of `scanner/fade_realistic_studies.py`
  (bandv10, band12, band12q4, band050, band050q4), day 0 Oct 2024 – Aug 2026. A contract in two sets counts once.
  The sets were picked by the old opening-print band, so options under ₹0.50 at the open are missing.
- **Entry B** = the 09:16 candle open + 1 tick (₹0.05 before 2025-11-03, ₹0.01 from it); no 09:16 candle → excluded.
- **Exit v12** on 1-minute candles: `scanner/fade_stop_trail.one` with S 20 touch from 09:17, trail on at +10 %, gap 2 %;
  else the 15:19 close − 1 tick. Real charges.
- **Sessions to expiry** = trading sessions after day 0 up to and including expiry (`backtest_cheap_options.sessions_to`
  on the bhavcopy calendar).

## Groups (all reported)
1. **Baseline** (today's live rule): B ≥ ₹2, one lot ₹600–8,000, any sessions to expiry.
2. **Rule-7:** B < ₹10, one lot ₹600–8,000, ≥ 7 sessions to expiry.
3. **Rule-10:** the same with ≥ 10 sessions.
4. Breakdowns: B < ₹2 vs ₹2–10 (lot rule kept); sessions to expiry < 7, 7–9, ≥ 10.

Per group: N, win %, mean and median net % of premium, total ₹, date-clustered t, both halves (Oct 2024 – Oct 2025,
Nov 2025 – Sep 2026).

## Pass (fixed now), for each rule
Mean > 0 with t ≥ 2; mean > 0 in both halves; mean above the baseline's. A pass only justifies a paper shadow tag (the
user's decision).

**Caveat stated now:** the idea came from looking at this kind of data (the sheet used daily closes days later, a
different holding), and the 2 % trail was itself chosen in-sample, so a pass is weaker than a clean out-of-sample one.
