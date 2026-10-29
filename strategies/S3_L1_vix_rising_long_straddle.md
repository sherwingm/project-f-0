# S3 L1 · NIFTY long ATM straddle when India VIX is above 22 and rising (pre-registered)

Written 2026-10-29, **before any L1 option return was computed**. Long options only (fits the project's "long options
only" rule). Research only: a pass does not turn anything on in the paper or live system.

**Source of the idea:** D7 (`data/results/s3_d6_d7.md`). On 2021-10 → 2025-09, India VIX was above the realised vol of
the next 5 sessions in every bucket except "VIX > 22 and rising". That suggests options are under-priced only then, so
buying a straddle might pay. D7 was descriptive and on a different period (2021-10 → 2025-09). L1 is tested on years
no S3 study has read option prices for: **2018-01-01 → 2021-12-31**.

## Data (all free, NSE)
- **Options:** NSE F&O bhavcopy, daily, `options_daily/NIFTY/<YYYY-MM>.parquet` (downloaded 2026-10-29 with
  `index_data/bhavcopy_ohlc.py`, the same code as 2021+). Used fields: TradDt, XpryDt, StrkPric, OptnTp, ClsPric,
  TtlTradgVol (contracts).
- **India VIX and NIFTY 50 daily close:** NSE's official `ind_close_all_DDMMYYYY.csv` (`index_data/index_close.py`).
  This is the **source of record** for the signal. `vix_daily.parquet` (yfinance) is only a cross-check. Days where
  the two disagree on the signal are listed.
- **Sessions:** the days that have a NIFTY options bhavcopy.

## Signal (known at the close of day d, nothing later)
- **"VIX above 22 and rising"** on session d means both of these hold:
  - VIX close(d) > 22.00;
  - VIX close(d) > VIX close(d − 5 sessions).
  This is the same 5-session change D7 used, applied to closes only.
- Both values are published at the close of d. **The trade is entered at the close of the next session (d + 1)**, not
  at d's own close, so the signal is never traded on the same price print it was measured on.

## Trade
- **Entry:** the close of session d + 1, at ClsPric.
- **Expiry:** the nearest NIFTY expiry at least **10 calendar days** after the entry day. This needs only the expiry
  list on the entry day. It almost always lands after the planned exit, so the straddle is sold rather than settled.
  - Before Feb 2019 only monthly expiries exist, and the rule then picks the next monthly. That is allowed; those
    trades are flagged.
- **Strike (ATM):** of the strikes on that expiry where **both** the CE and the PE traded at least **100 contracts** on
  the entry day, the one with the smallest |CE close − PE close| (put-call parity ATM; uses that day's closes only).
  - If no strike passes, the signal is skipped and listed. It is not retried on a later day.
  - Sanity check, report only: the chosen strike against the official NIFTY close that day.
- **Size:** 1 lot. Lot by contract, from NSE circular 28/2021:
  - 75 for contracts expiring before 2021-07-29;
  - 50 from then on.
  - `NewBrdLotQty` is empty in the old-format files.
- **Exit:** the close of the **5th session after entry**, at ClsPric. If the expiry is sooner, exit at the close of the
  last session before the expiry.
  - **No stop and no target:** daily closes cannot show intraday prices, so a stop would be invented fills.
- **One position at a time:** a signal on a day when a position is still open is ignored. A signal on the exit day
  itself is allowed (entry the next session).
- **Window edge:** a signal whose planned exit falls after 2021-12-31 is not taken (listed). No 2022 price is read.

## Missing data (no invented prices)
- **Entry:** both legs must have traded at least 100 contracts at the chosen strike (above). Otherwise skip and list.
- **Exit:** each leg uses that day's ClsPric only if TtlTradgVol > 0. Otherwise:
  - use the next session where that leg traded, up to 2 sessions later, and never on or after the expiry date;
  - if there is still none, the trade is marked **data gap**, excluded from the stats, and listed with both legs'
    last prices.

## Costs and P&L
- **Slippage:** 1 % of the price on every fill (buy at close × 1.01, sell at close × 0.99). These are daily closes
  with no bid or ask, so this is wider than the 0.5 % used for minute fills.
- **Fees:** `server/charges.leg` on each of the 4 orders (BUY at entry, SELL at exit), at today's rates. Those are
  higher than the 2018-21 rates (STT on option sells has risen since), so this is conservative.
- **Debit (capital at risk):** (CE + PE) × 1.01 × lot. This is the most a long straddle can lose, before fees.
- **net_rs** = exit value − debit − all fees.
- **net_pct_premium** = net_rs ÷ debit × 100.
- **Equity:** 1 lot fixed, trades in date order. Max drawdown in ₹, plus a Monte Carlo drawdown (10,000 reshuffles,
  seed 11, as in P1).
- **2× costs:** the slippage and fees doubled (`cost_mult = 2`).

## Gate (the S3 gate from DECISIONS.md, unchanged)
| Check | Rule |
|---|---|
| Trades | at least 30 traded (not counting skips or data gaps) |
| Net mean | net mean % of the debit > 0, and still > 0 at 2× costs |
| t | t ≥ 2 on net % of the debit |
| Halves | net mean > 0 in each half: 2018-01-01 → 2019-12-31 and 2020-01-01 → 2021-12-31 |
| Worst trade | the worst trade's loss is smaller than the average month (months with trades) |
| Neighbours | net mean > 0 for each of: VIX level 17.6 and 26.4 (22 ± 20 %), and holds of 4 and 6 sessions (5 ± 20 %) |

Also reported, with no effect on the verdict:
- by year;
- each trade with its VIX, strike, expiry, fills and fees;
- the skipped and data-gap signals;
- **the baseline:** the same straddle entered on every session's close with the same rules and no VIX filter. Is
  VIX > 22 and rising better than buying at random?

## What was counted before writing this (signal dates only, no option prices)
**Step 2 count (NSE official India VIX close, `python -m scanner.s3_l1 count`, 2026-10-29):**
- 2018-01-01 → 2025-09-30: 1,913 sessions, **146 qualifying days**. By year: 2018 0, 2019 16, 2020 59, 2021 34,
  2022 30, 2023 0, 2024 6, 2025 (to Sep) 1.
- That is at least 30, so the minimum-evidence rule lets L1 go on.
- **In the test window 2018-2021: 109 days.**
- The yfinance copy gives 145. The one difference is 2021-01-27, which qualifies only on the official close. The two
  series differ by more than 0.05 on 3 of 1,896 common days (largest 1.01).

The first count, with vix_daily, 2018-01 → 2021-12:
- 108 qualifying days;
- about 32 non-overlapping 5-session trades (2019: 3, 2020: 19, 2021: 10). 2018 has none.

The 30-trade rule is met only just. Holds of 6 give about 28 trades and VIX 26.4 about 11. Those are neighbour checks,
which need a positive mean only, not 30 trades.

## Windows after this test: a structural limit, stated now
- **Validation window, Oct 2022 → Sep 2024:** the same signal gives only about **2 trades** (both 2024). That window
  **cannot meet the 30-trade rule**. The rule is not lowered.
  - If L1 passes 2018-21, the result is reported with this limit, and the user decides; L1 is not promoted.
- **Holdout, Oct 2025 →:** about 3 trades. It stays locked and is not read.
- **Jan → Sep 2022** (about 10 trades) belongs to no window and is not read.
- **Paid data (₹18k):** considered only if L1 passes and needs intraday fills. A free sample first.

## Look-ahead review (done before committing)
| Rule | Information it uses | When that information is known |
|---|---|---|
| Signal on d | VIX closes on d and on d − 5 sessions | the close of d |
| Entry at d + 1 | the next session's close | one session after the signal |
| Expiry choice | the expiry list on the entry day | the entry day |
| ATM strike | entry-day option closes and volumes | the entry day (closes of the same print as the fill: a slight optimism, covered by the 1 % slippage) |
| Exit day | a fixed count of 5 sessions | the entry day (the next sessions' dates are known from the holiday calendar) |
| Exit price | the close on the exit day | the exit day |
| Exit fallback | only later sessions, at most 2 | after the exit day, never before |
| Lot | NSE's published circular | before the trades |

No parameter is chosen from L1's results. The thresholds (22, 5 sessions, 10 days, 100 contracts, 1 %) are fixed here.
