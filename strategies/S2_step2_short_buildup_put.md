# S2 step 2 · Short build-up → one bought put, ₹600–8,000 a lot

S2, step 2, under `DECISIONS.md`. **Pre-registered**: every choice is fixed here before any run.
Run: `python -m scanner.backtest_s2_put`. Long options only: the trade is a bought put; the most it can lose is the
premium paid.

**Where this comes from.** Step 1 (`strategies/S2_oi_buildup_screen.md`, DECISIONS.md 2026-10-14) screened 48 cells
of price + futures OI build-up on the stock itself, year by year 2021-2026. One cell passed: **short build-up** (stock
−3 % or more, combined futures OI +10 % or more, volume ≥ 1.5× its 20-day average): over the next 5 sessions the stock
fell a further 0.62 % on average (965 signals, t 3.17, positive in 5 of 6 years including 2025 and 2026). Step 2 asks
whether a bought put keeps that after time decay and costs.

**No clean holdout.** Every year 2021-2026 was used by the screen. This test therefore judges the put year by year;
if it passes, the live paper days that follow are the real test. The user chose (2026-10-14) the lot budget
(₹600–8,000, as S1), and that paper trading starts only if this test passes.

## Signal (step 1's passing cell, unchanged)
- Day d: price change ≤ −3 % (close d vs close d−1), combined stock-futures OI change ≥ +10 % (all expiries, d vs
  d−1), volume ≥ 1.5× the average of the 20 sessions before d.
- Skipped: a stock-futures expiry day and the session after it; days without the previous session's OI.
- One signal per stock every 5 sessions (the first counts). Not in the F&O ban list on day d+1.
- Window: day d from 2021-01-01 to the last session with stock closes (2026-09-25); a trade must complete (its exit
  day and its expiry's T-1) inside the data.

## The put
- **Expiry:** the current monthly expiry if ≥ 10 sessions remain after day d, else the next monthly
  (`scanner/option_engine.choose_expiry`).
- **Strike:** start at the listed put strike nearest the stock's day-d close (a tie: the higher) and **walk down**,
  one listed strike of that expiry at a time. Take the first put where, on day d+1: it traded **≥ 50 contracts**; the
  fill is **≥ ₹2**; and one lot costs **₹600–8,000**. Too thin or above ₹8,000: next strike down. Below ₹600 or a
  fill under ₹2: stop, no trade (the strikes below are cheaper still). No strike left: no trade.
- **Fill:** day d+1's premium VWAP (`scanner/option_engine.premium_vwap`: NSE reports option turnover as notional,
  (strike + premium) × quantity, so the premium VWAP = turnover ÷ (contracts × lot) − strike), else the close;
  + 1 tick (₹0.05). **1 lot.**

## Exits (on closes from day d+1, in this order)
1. **Stop:** a close ≤ 50 % of the fill → exit at that close.
2. **Time:** the close of day **d+5** → exit.
3. **T-1:** the session before expiry → exit (stock options settle by delivery).

Exit fill: the close − 1 tick (not below 0).

## Costs and exclusions (as S1)
- Slippage per side, % of premium, by AMFI category point in time: large 1 %, mid 2 %, small 3 % (not found 3 %).
- Charges: `server/charges.py` on both orders (an option buy and sell).
- Net = (exit − fill) × quantity − charges − slippage; % of premium = net ÷ (fill × quantity).
- Corporate actions: a trade whose put leaves the bhavcopy, or whose future moves > 3 % differently from the stock's
  adjusted close, is excluded and counted.

## Variants
| Variant | Change | Role |
|---|---|---|
| `h5` | as above | **primary: the pass test** |
| `h3` | exit at the close of day d+3 | side report |
| `h5_nostop` | no 50 % stop | side report |

## Pass (on `h5`)
1. Net mean > 0 after costs (% of premium).
2. Date-clustered t ≥ 2.
3. Mean positive in at least 5 of the 6 calendar years (by entry date), including 2025 and 2026.
4. N ≥ 200.

Also reported: the same signals as a short stock position (step 1's number) on the traded subset; the share of
signals with no affordable put and why; strike distance below the stock; results by year; exit reasons.

## What follows
- Pass → the S2 put enters the live paper account (bought at the 09:15 open), with its own scoreboard on the S2 page.
- Fail → recorded and closed; the signal stays on the S2 page as information.

## Known limits
- Daily data: the signal is known at day d's close; the backtest buys at day d+1's VWAP (the live paper version would
  buy at the open).
- The strike walk reads day d+1's whole-day volume and VWAP.
- Sector membership is today's list applied to all dates.
