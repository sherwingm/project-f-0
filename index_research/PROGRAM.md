# Index strategy research program (pre-registration, written 14 Nov 2026 before any number of this program)

**Request:** the user, 14 Nov 2026, after pasting a two-part "Master Research Report" (Reddit / Varsity / QuantInsti / SEBI summaries): research every
reasonable strategy family for Indian index markets autonomously, challenge every result, record failures as carefully as successes, do not touch
sealed data, holdouts or frozen strategies, deploy nothing, place no orders.

**Scope decisions (stated now):**
- **Research only.** Nothing here changes S1, S2, G1, G1-F, G1-C, XP, NT, the live server, the paper ledgers or any frozen file.
- **Option selling and futures are researched as backtests.** The user's 30 Oct decision "buy only" governs what is traded and what was researched
  after it; the 14 Nov request explicitly asks for options, futures, volatility and statistical approaches, so selling structures and futures
  (index futures proxied by the index) are tested here as research. Any pass is reported as research only; trading any of it would need a new user
  decision (capital, margin, buy-only).
- **Sealed data:** `expiry_research/data/sealed/` is not opened. The 13 Nov prospective holdout (G1 / S1, after the freeze) is not used.
- **Sources:** the pasted report is a summary of third-party claims. Reddit cannot be opened by our tools. Every claim is a hypothesis, tested on our data.

## Data (all local, `INDEX_STORE=../fo-index-data/data/index`, plus `data/eod2`)
- Index 1-minute (open/high/low/close, no volume): NIFTY50, NIFTYBANK, SENSEX, INDIAVIX, 2021-10-20 to 2026-10-28.
- Index options 1-minute: NIFTY, SENSEX, 2024-10 to 2026-10 (engine `scanner/s3_engine.py`).
- Index options and futures daily bhavcopy: NIFTY, BANKNIFTY, 2018-01 to 2026-10 (`options_daily`, futures rows `FinInstrmTp == IDF`).
- Stocks daily (`data/eod2`): HDFCBANK, ICICIBANK, AXISBANK, KOTAKBANK, SBIN and others.
- Not available: bank-nifty option minutes, index futures minutes, any bid/ask history, tick data, an RBI/Budget calendar before Oct 2024.

## Periods (chronological; the latest period is touched once per candidate)
- **Index-minute studies (futures proxy), 2021-10-20 to 2026-10-28:** discovery D = 2021-10-20 to 2023-12-31; validation V = 2024-01-01 to 2025-09-30;
  late period L = 2025-10-01 to 2026-10-28, opened only for candidates that pass V, once.
  Disclosed contamination: NIFTY minutes of all years were used for opening-range follow-through (`g1_research/UNDERLYING_*`, 2021-10 to 2026-10),
  PUT1 / B2 (2022-24) and the expiry-afternoon studies; ORB-type results here are therefore not clean.
- **Option-minute studies, 2024-10-01 to 2026-10-28:** D = to 2025-09-30, V = from 2025-10-01 (both years were looked at by S3 pods; disclosed per study). No L.
- **Daily bhavcopy studies, 2018-01 to 2026-10:** D = 2018-2021, V = 2022-01 to 2024-09, L = 2024-10 to 2026-10.
- **Stock daily (pairs):** D = 2012-2018, V = 2019-2022, L = 2023 to 2026-11.

## Costs and fills (baseline; every candidate is also run at 2x)
- Index futures proxy: entry / exit at the 1-minute open or close of the decision minute + slippage 1 point NIFTY, 3 BANKNIFTY, 3 SENSEX a side
  (stress: 3 / 8 / 8); charges `server/charges.leg("FUT", ...)` with the trade date (dated STT). Lot NIFTY 65, BANKNIFTY 30, SENSEX 20 (current lots; results in % and Rs at 1 lot).
  The index is not the future: the basis (carry about 0.02 % a day) is ignored intraday and stated for overnight trades.
- Options: the S3 engine (0.5 % / 1 % slippage, charges with the trade date) for minute studies; for daily bhavcopy studies, settlement / close prices
  with 1 % slippage a side (2 % stress) and charges.
- Signals use only closed bars; an entry is at the next bar.

## Pass rules (identical for every study)
1. **Discovery:** each pre-named cell: mean net > 0, date-clustered t >= 2, both halves of D > 0, n >= 30. Benjamini-Hochberg 10 % across the study's cells (one-sided p from t).
2. **Validation (once, survivors only):** mean > 0, t >= 1.5, > 0 at 2x costs, > 0 without the best 5 % of trades, n >= 20.
3. **Robustness battery (validation passers):** neighbours of every parameter (+-1 step), walk-forward (re-fit on expanding years, test next year), cluster bootstrap 95 % interval,
   Monte Carlo drawdown and risk of ruin at 1 lot on Rs 5 lakh, regime split (VIX tercile, trend), execution delay (+1 bar), slippage x3.
4. **Late period (once)** for battery survivors. Only a candidate that passes all of 1-4 is called "a candidate for paper trading"; nothing is called profitable.
5. Every study writes its cells and numbers to `results/`, one registry row in `docs/research/experiments.csv`, and a line in `NOTES.md` (resume log).

## Studies (family fixed now; each script header repeats its own cells before it is run)
- **R01 Gap-and-go** (report section 3, 15-4): NIFTY, BANKNIFTY, SENSEX futures proxy. Gap >= 0.5 / 0.75 / 1.0 %, follow the gap, entry 09:16 open, exit 15:15; stop: none or the first 5-minute candle's far end; skip filter (prev close > 2.5 % above SMA20) on or off. 3 x 2 x 2 = 12 cells per index. Also gap FADE (the opposite) as 3 cells.
- **R02 Overnight and intraday drift:** buy 15:25 sell next 09:16; buy 09:16 sell 15:25; each with no filter, VIX tercile, previous-day sign. 2 x 4 = 8 cells per index (futures proxy; then on daily futures 2018+ for overnight).
- **R03 Initial-balance breakout and failed-break reversal:** IB = 09:15-10:14; first close beyond it until 14:00, follow, stop the other side / IB midpoint, exit 15:15 (2 cells); "liquidity sweep": price pierces the previous day's high (low) by < 0.1 % and closes back inside within 5 minutes, fade it, stop at the sweep extreme, exit 15:15 (2 cells, both sides pooled and split = 3 cells).
- **R04 Supertrend pullback:** 60-minute Supertrend(10,3) direction; 5-minute Supertrend(10,3) flips against then back with it; enter next bar; ADX(14, 60-min) > 25 filter on / off; exit at the 5-minute flip against or 15:15 (2 cells); intraday only.
- **R05 Mean reversion:** price > 3 (2.5) standard deviations from the session's running TWAP (no volume: VWAP not computable) and 5-minute RSI(14) > 85 (< 15): fade, target TWAP, stop 1 x distance, exit 15:15 (4 cells: 2 thresholds x RSI on/off).
- **R06 Overnight option selling (VolGuard-like) and its long mirror:** NIFTY option minutes. 15:15 short ATM straddle, wings +-500 (iron fly) or none, exit next 09:16; filters VIX 12-18 and VoV (5-day std of daily VIX) < its 1-year median, on / off. Cells: {short fly, short straddle, long straddle} x {no filter, VIX, VIX+VoV} = 9.
- **R07 Pre-event short straddle / strangle:** NIFTY option minutes, events of `scanner/s3_buy4` (RBI, Budget, FOMC) Oct 2024 to Oct 2026. Sell at 15:15 three sessions before, exit 1 minute before the announcement (RBI 09:58; Budget 10:58; FOMC = next session 09:16); stop 30 % of credit on or off; straddle or 0.2-delta-like strangle (+-2 strikes = 100 points) (2 x 2 = 4 cells). Small n; reported even if < 30.
- **R08 Expiry choice for directional buys (the "next-week" claim):** G1 puts and G1-C calls signals, ATM vs 1 ITM, nearest weekly vs the next weekly expiry, live exit (4 cells per side).
- **R09 VRP with regime filters (daily bhavcopy, NIFTY and BANKNIFTY 2018+):** weekly ATM short straddle entered at the close 4 sessions before expiry, held to expiry settlement; filters: none, VIX percentile (1-year) > 70, VIX percentile < 30, VoV low, VoV high (5 cells x 2 indices); a long-straddle mirror for the filter cells (5 cells).
- **R10 Pairs (stock daily):** HDFCBANK-ICICIBANK, HDFCBANK-KOTAKBANK, ICICIBANK-AXISBANK, SBIN-ICICIBANK; log-price spread, rolling 60-day hedge ratio, z-score 20; enter |z| > 2, exit z crosses 0, stop |z| > 3.5; ADF (p < 0.05 on the formation window) required on / off (4 pairs x 2 = 8 cells). Costs 0.1 % a side a leg (futures-like).
- **R11 Simple daily ML (walk-forward):** NIFTY next-day direction from 12 daily features (returns 1/5/20, gap, range, VIX level / change, VoV, SMA gaps, day of week), logistic regression and random forest, expanding-window yearly refit; trade futures at the open in the predicted direction (2 cells) and only when probability > 0.55 (2 cells).
- **R12 Combinations:** only of strategies that pass validation, or of the standing live tracks (G1-F) with any passer; equal weights; correlation of daily P&L.
- **Failure analysis:** for every failed family, the report states the most likely reason (costs, decay, no signal, regime) from its own numbers.
Cells added after a number is seen are labelled "post-hoc exploration", never used for a pass.

## Amendment A1 (14 Nov, before R06-R08 were run; R01-R03 results had been seen, none of R04-R11)
- R07: the FOMC decision is announced after the Indian close, so "exit before the announcement" = 15:25 on the FOMC date (the text above said the next 09:16, which would hold through it).
- R02 overnight trades on the index ignore the futures carry (about 0.02 % a night at 6-7 % a year); the R02b check on real daily futures (2018+) settles it.
- R02b (added now, after R02's numbers): overnight close -> next open on the real near-month NIFTY / BANKNIFTY future from the daily bhavcopy, cells all / previous day up; D = 2018-2021, V = 2022-01 to 2024-09, L = 2024-10 ->. It is a follow-up of a seen result (labelled as such), testing whether the futures carry kills it.

## Amendment A2 (14 Nov, new studies R13-R19 written before any of them was run; seen so far: R01, R02, R02b, R03, R07, R10, R11, all without a pass)
Daily futures proxy = the NIFTY50 daily close / open (`data/eod2/nifty 50.csv`, 2012-02 ->) with 1 point slippage a side and dated FUT charges, lot 65;
NIFTYBANK daily from `index_close_daily.parquet` (2018 ->). Daily periods: D = 2012-2017, V = 2018-2021, L = 2022-01 to 2026-10-28.
- **R13 Intraday momentum** (Gao, Han, Li, Zhou 2018, "Market intraday momentum"): the first half-hour return (prev close -> 09:45) predicts the last half-hour (15:00 -> 15:29). Trade the last half hour in the sign of the first; cells: all days, |first| > 0.5 %, and also using the 14:30 -> 15:00 return as a second predictor in agreement (3 cells x NIFTY / BANKNIFTY / SENSEX; minute periods of the program).
- **R14 Trend filter (time-series momentum):** long NIFTY futures at the next open while the close is above its 200-day SMA, else flat (cell sma200); 50/200 cross long-only (cell cross); 20-day breakout long, exit on a 10-day low (cell donchian); long/short version of sma200 (cell sma200_ls). One trade = one holding spell. Also reported: buy and hold.
- **R15 Short-term reversal:** long NIFTY futures at the close when RSI(2) < 10 and close > SMA200 (Connors), exit at the close when close > SMA5 (cell rsi2); after 3 down closes in a row, hold 1 day (cell down3); mirrors short (cells rsi2_short, up3_short).
- **R16 VIX spike buying:** long NIFTY futures at the close when VIX closes >= 30 % above its 20-day mean (one entry per episode), hold 5 / 10 sessions (2 cells); the mirror after VIX falls >= 20 % below its 20-day mean, hold 5 (1 cell).
- **R17 Calendar anomalies:** long NIFTY futures close -> close on the last 3 and first 2 sessions of each month (turn of the month, cell tom); Monday open -> close short / long (cells mon_short); Friday close -> Monday open (cell weekend); each a separate cell.
- **R18 NIFTY / BANKNIFTY ratio reversion (index pair):** log ratio, 60-day hedge, z over 20 sessions, enter |z| > 2, exit at 0, stop 3.5 (one cell); on daily closes 2018 -> (D 2018-2021, V 2022-01 to 2024-09, L 2024-10 ->), futures costs on both legs.
- **R19 Calendar straddle (daily bhavcopy, NIFTY):** at the close 4 sessions before a weekly expiry, sell the ATM straddle of that expiry and buy the ATM straddle of the next weekly expiry; close everything at the expiry-day close (near at intrinsic, far at its close). Cells: all, VIX 1-year percentile < 30 (the report's "low VIX -> calendars"). Option periods of R09.
Same pass rules. Each study's BH runs over its own cells.
