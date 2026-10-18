# Strategy audit (2026-10-18)

Written by Claude Code from the code, configs, data folders and recorded results in this repository
(`sherwingm/project-f-0`). Where the code does not implement something, it says **not implemented**.

> **Scope correction.** The question list assumes an *index* options strategy. This repository trades **NSE stock
> options** (single stocks in the F&O list), **long options only**, on **results and price/OI events**. Index
> options are not traded anywhere. Indices appear only as benchmarks (NIFTY 50, NIFTY 500, sector indices). Answers
> below describe what the code actually does.

## 1. Instruments and contracts

- **Indices traded:** none. Not implemented for Nifty, Bank Nifty, Sensex, FinNifty or Midcap. The universe is NSE's
  F&O stock list (`fo_mktlots.csv`, `scanner/build.py:163`). Index files are benchmarks only:
  - `data/eod2/nifty 50.csv` and `nifty 500.csv`;
  - NSE `ind_close_all` files, read in `scanner/fade_diagnostics.py:88`.
- **Expiries:** stock options, **monthly** expiries only (the last listed expiry of each month,
  `scanner/option_engine.py:77-82`).
  - **How the expiry is found:** from the expiries listed in NSE's F&O bhavcopy (`XpryDt`) or Kotak's scrip master
    (`server/kotak.py:224`). It is never a hard-coded weekday.
  - **Current rule (S1 v10 fade and the arm A/B rule trades):** keep the nearest monthly expiry while at least 2
    sessions remain after day 0 (`scanner/fade_live.py:68-74`, `MIN_LEFT = 2`; `scanner/forward_s1.py:51`).
  - **Holidays:** counted from `data/nse_holidays.json` (`server/sessions.py:27-35`), which `scanner/fade_live.py`
    refreshes from NSE.
  - **2024-25 index expiry-weekday changes:** not applicable, because no index options are traded. Holiday-shifted
    stock expiries are handled implicitly, because the expiry date is read from NSE's own files rather than computed.
- **Lot sizes:** never hard-coded. They are loaded per contract:
  - **Backtests:** `NewBrdLotQty` in each day's F&O bhavcopy (`scanner/backtest_s1_v10.py`, `quotes_of`), so
    historical lot sizes are used per date.
  - **Live:** Kotak scrip master `lLotSize` (`server/kotak.py:224`) and the quote's `mktLot` (`server/kotak.py:483`).
  - **Universe:** `fo_mktlots.csv` (`scanner/build.py:140`).

## 2. Strategy logic

**All variants are options buying, naked single leg** (1 lot). No selling, spreads, straddles, strangles, condors or
flies are implemented. Strategy pages are in `strategies/`; outcomes are in `DECISIONS.md`.

| Strategy | Status | Structure |
|---|---|---|
| **S1 arm A** (every results beat), **arm B** (beat in a strong sector) | Forward paper test + live paper rule trades since 2026-10-13 | Long call |
| **S1 v10 fade, arm F** | Live paper since 2026-10-15 | Long **put** on strong results, long **call** on weak results |
| S2 short build-up put | Closed (failed backtest) | Long put |
| S1 v2-v9, S2 screen B, event screens | Closed research | Stock-level screens / long calls or puts |
| Manual paper orders (terminal page) | Available | Any single leg the user enters |

### S1 v10 fade, arm F (`server/fade.py`, `scanner/fade_live.py`)

**Signal (night before / pre-open),** with numbers from the filing's XBRL (`scanner/event_screens.py:47-55`,
`scanner/fade_live.py:38-44`):

| Numbers | Side bought |
|---|---|
| **Strong:** net profit YoY > +10 %, QoQ > 0, revenue YoY > 0 | Put (`PE`) |
| **Weak:** net profit YoY < −10 %, QoQ < 0 | Call (`CE`) |

- **Day 0** is the first full session after the filing; a filing before 09:15 trades the same day
  (`scanner/backtest_s1_v2.py:116-127`).
- **Entry window:** any poll 09:15-15:20, retried every 120 s per stock (`server/fade.py:29-30`).
- **Strike selection:** walk from the strike nearest the live stock price away from the money (puts down, calls up),
  at most 15 strikes (`server/fade.py:31`, `96-117`). It takes the first strike with:
  - a two-sided quote;
  - a spread of 10 % of the ask or less;
  - an ask of ₹2 or more;
  - 1 lot at the ask within ₹600-8,000.
- **DTE at entry:** at least 2 sessions to the monthly expiry.
- **No price indicator is used.** The signal is purely the results numbers.
- **Exit:** sold at the first poll from 15:20 the same day at the best bid, else last price − 1 tick
  (`server/fade.py:228-245`).
  - No stop, no target, no trailing stop.
  - A position missed at 15:20 (server asleep) is sold at the first poll of the next day (`fade_late`).
  - The carried-trade rule (stop −20 %, trail 25 %, T-1) is coded but disabled (`CARRY_DATES = set()`, `server/fade.py`).
- **No re-entry.** One trade per stock per day.
- **Shadow tag:** each position records whether it is in the "puts only above NP YoY 25 %" track
  (`server/fade.py`, `in_shadow`; `strategies/S1_v10_np25_shadow_track.md`). This is a tag only, not a filter.

### S1 arm A / B rule trades (`server/rules.py`, `scanner/forward_s1.py`)

- **Signal:** a results beat, i.e. a day-0 stock move at least 2 % above its sector and under 10 % raw
  (`scanner/forward_s1.py:6-12`, `52`). Arm B also requires a strong sector. One position per stock and arm, with a
  10-session cooldown.
- **Entry:** two positions per signal on the next session (`server/rules.py:1-15`):
  - **open:** any poll 09:15-15:20 (retried every 120 s). From the strike nearest the live price upward, over strikes
    that traded at least 50 contracts on day 0, take the first whose ask × lot is within ₹600-8,000, bought at the ask.
  - **close:** the first poll from 15:20, the same walk on live volume, bought at ATP + 1 tick.
  - Constants: `server/rules.py:30-33`, `scanner/backtest_s1_v7.py:35-36`.
- **Exit:** checked once a session at the first poll from 15:20 (`scanner/backtest_s1_v7.py:86-92`), in this order:
  1. 50 % stop on the close;
  2. 5 sessions without a new closing high;
  3. T-1, the session before expiry.

  The sale fills at the best bid.

### Position sizing and filters

- **Sizing:** a fixed 1 lot per trade, everywhere.
  - Not capital-based and not volatility-based.
  - Rule trades are outside the manual-order limits (`server/rules.py:1`).
  - Manual orders are capped by the risk gate (section 3).
- **Regime / filters:**
  - **India VIX:** not implemented.
  - **Trend filter:** not implemented for the live strategies.
  - **Event blocklist:** F&O ban stocks are skipped (`scanner/fade_live.py`, "in the F&O ban on day 0").
  - **Expiry-day entries:** blocked for manual orders (`server/config.py:134`, `BLOCK_EXPIRY_DAY_ENTRIES=true`).
  - **Time of day:** the entry windows above.
- **Multi-strategy coordination:** the arms run side by side in one paper account. Each position carries its arm
  (`A`, `B`, `F`), and the results page scores them separately.
  - No capital allocation between strategies.
  - No net-delta or correlation cap.

## 3. Risk management

- **Paper-account kill switch** (`server/risk.py:38-75`, defaults in `server/config.py:122-134`). These are the
  **code defaults**; the docstring at `server/risk.py:4-15` quotes older, smaller numbers (see section 8).

  | Control | Default |
  |---|---|
  | Daily loss halt | 2.0 % of capital (`DAILY_LOSS_HALT_PCT`), latched for the day |
  | Weekly loss halt | 3.0 % |
  | Drawdown review banner | 10 % |
  | Risk per trade | 6 % (`RISK_PER_TRADE_PCT`) |
  | Margin cap | 30 % |
  | New positions | at most 3 a day and 20 a month |

- **Scope of the kill switch:** it governs manual orders. Rule trades (arms A, B, F) bypass the manual-order limits
  (`server/rules.py:1`).
- **Not implemented:** a max-open-positions cap for rule trades, net-delta caps and gamma caps.
- **Gap open:** no special handling. The entry walk simply uses the live price at the time of the poll.
- **Broker disconnect:**
  - Polling is time-driven. A missed 15:20 exit sells at the next day's first poll (`fade_late`, `server/fade.py:228`).
  - The free Render instance sleeps without visits. A GitHub Action pings it at 08:17, 11:47 and 14:17 IST
    (`.github/workflows/keep-awake.yml:12-14`).
- **Rejected order (paper):** recorded as a refusal with the reason (`refusals.jsonl` in the paper data dir, `server/paper.py:133`; `/api/paper/refusals`), and
  the entry walk retries until 15:20.
- **Partial fill (paper):** cannot happen. The fill engine walks visible depth and fills any overflow at the worst
  level plus one spread (`server/fills.py:1-17`).
- **Partial fill / reject (real orders):** not implemented beyond what the broker API returns.
- **End-of-day square-off:**
  - Fade positions: 15:20 the same day.
  - Arm A/B: held for days, but always exited at T-1, so never held to expiry.
  - Expiry-day entries are blocked for manual orders.
  - Exercise STT is modelled (`server/charges.py:100-102`), but no strategy holds to settlement.

## 4. Data and backtesting

- **Sources and timeframes:**

  | Data | Source | Timeframe / range |
  |---|---|---|
  | Option and futures prices | NSE F&O bhavcopy (UDiFF and the old format), cached as `data/cache/fo_bhavcopy_YYYYMMDD.csv`; per-strike open / high / low / close, volume, turnover, OI | Daily, 2021-01-01 → 2026-10-16 |
  | Day-0 option prices | `fo_prices_*.csv` | Daily |
  | Stock prices | eod2 (`data/eod2/*.csv`) | Daily, adjusted for splits / bonuses but **not demergers** |
  | Stock minute candles | Kotak history through `/api/history` | 1-minute; day-0 candles for 2022-26 backtest trades |
  | Live quotes | Kotak quotes and depth | Polled every 30 s (`server/config.py:92`) |
  | Results events and times | NSE corporate announcements, event store `events.sqlite` | From Dec 2021 |
  | Results numbers | XBRL, `data/financials.json` (212 stocks) | — |
  | Futures / ADR series | yfinance 1.7.0, `data/parents/` | — |

  - **India VIX:** not used.
  - **Option chain snapshots:** only the live polls; no history.
- **Backtest engine:** custom pandas code, e.g. `scanner/backtest_s1_v10.py`. It uses **strike-level real option
  prices** (bhavcopy daily open / close / VWAP), not prices approximated from the index.
  - Entry is the day-0 open + 1 tick, or the VWAP + 1 tick (`scanner/backtest_s1_v10.py:62-73`).
  - Exit is the 15:20 close − 1 tick.
- **Cost model:** `server/charges.py:8-41`, rates effective 2026-04-01. It is used by both the backtests (`net_of`,
  `scanner/backtest_s1_v10.py:118-123`) and paper trading.

  | Component | Options (premium) |
  |---|---|
  | Brokerage | ₹20 per order |
  | STT | 0.15 % of premium, sell side; 0.15 % of intrinsic on exercise |
  | NSE transaction charge | ₹35.53 per lakh of premium, each side |
  | SEBI fee | ₹10 per crore, each side |
  | Stamp duty | 0.003 %, buy side |
  | GST | 18 % on brokerage + NSE charge + SEBI fee |
  | Backtest slippage | 1 % / 2 % / 3 % of premium per side for large / mid / small caps (`scanner/backtest_s1_v4.py:39`) |

- **Historical lot sizes:** yes, per date from the bhavcopy. **Expiry weekdays:** taken per date from the listed
  expiries.
- **Lookahead / bias risks:**
  - **The backtest's liquidity test uses day-0 volume.** "At least 50 contracts traded on day 0" is known only after
    the close (`scanner/backtest_s1_v10.py:35`, `walk`). This selects strikes with hindsight.
  - **The VWAP entry uses the full day's VWAP.** That is only a side report.
  - **The open entry uses the official open,** which is the pre-open auction price (≈ 09:08). A live fill comes later
    and at the ask. The diagnostics found the whole backtest profit depends on this price: entering at VWAP gives
    about −14 % a trade.
  - **Survivorship / look-ahead in membership:** today's sector map and today's 212-stock financials file are applied
    to past dates.
  - **No current-bar use before completion** was found in the live code. Signals are made from the previous session's
    files and the filing's numbers.

## 5. Results so far

All results are descriptive, 1 lot per trade, net of costs. Sharpe was **not computed**. Drawdowns below are on the
cumulative 1-lot rupee sum; no capital base is defined for the backtests, so there is no % of capital.

**S1 v10 fade backtest** (`data/results/S1_v10_trades*.csv`; same-day exit):

| Window / entry | Trades | Win % | Avg win | Avg loss | Total ₹ | Max DD ₹ | Worst day | Worst month |
|---|---|---|---|---|---|---|---|---|
| 2022-24, open + 1 tick | 436 | 36.5 | 4,684 | −2,601 | +24,190 | −1,16,814 | 2023-02-15 −16,594 | 2023-05 −52,632 |
| 2022-24, VWAP + 1 tick | 431 | 23.9 | 1,206 | −1,471 | −3,58,364 | −3,56,630 | 2023-10-30 −11,077 | 2024-10 −40,450 |
| 2025-26, open + 1 tick | 434 | 40.1 | 4,768 | −2,705 | +1,26,164 | −50,371 | 2025-01-31 −18,585 | 2025-02 −14,663 |
| 2025-26, VWAP + 1 tick | 436 | 25.0 | 1,268 | −1,641 | −3,98,482 | −3,96,594 | 2026-08-03 −11,316 | 2026-05 −63,420 |

- **Per trade:** +3.6 % / +5.6 % of premium with the open entry (t 0.9 / 1.3); −14.2 % / −14.8 % with the VWAP entry.
- **Average lot:** about ₹6,300-6,600.
- **Splits run:**
  - by half-year;
  - by side (puts / calls);
  - by NIFTY day-0 move (puts lose about −21 % on NIFTY-up days);
  - by result-number bands, pre-run, gap, strike distance and others (`data/results/S1_v10_fade_diagnostics.md`);
  - exits and stops (`S1_v10_stoploss_study*.md`);
  - strike distance (`S1_v10_strike_distance.md`).
- **Not run:** a VIX split (no VIX data) and an expiry-day split.

**Live paper, arm F** (2026-10-15 → 16): 9 trades.
- Closed: 1 (BHEL, −₹192, −3.3 %).
- Still open at the last snapshot: 8, MTM about −₹6,882.

**Arm A / B:** forward test from 2026-10-13. One rule position (TATAELXSI) open; the others are queued for 19 Oct.
Too few trades to summarise.

**Closed backtests** (one row each in `DECISIONS.md`), all failed:
- S1 v2-v9;
- S2 step 2: short build-up put, 580 trades, −14.2 % of premium, t −2.7;
- S2 screen B: 0 of 8 tests run passed; §1 / §2 not testable with free futures data.

**Out-of-sample / walk-forward:**
- There is no clean out-of-sample test left. 2021-24 was the S1 test window and 2025-26 the S1 v8 holdout; both have
  since been used repeatedly.
- No walk-forward test was run.
- The live paper run (from 2026-10-15) is the only clean evidence.

**Named dates:**
- **March 2020:** not in the data (it starts 2021).
- **Feb 2022:** 20 fade trades, +₹7,041 (mean +6.9 %, open entry).
- **4 June 2024 and 5 Aug 2024:** no fade trades (not results days).

## 6. Execution and infrastructure

- **Brokers:** Kotak Neo (`kotakneoapi>=3.0.7`) is primary for live market data (`server/kotak.py`). Kite Connect
  (`server/broker.py:196-200`) and Groww (`server/groww.py:260`) adapters exist.
- **Stack:** Python 3.12, FastAPI + uvicorn, pandas, requests, xlsxwriter, pyotp (`requirements-server.txt`).
- **Paper trading:** own simulator (`server/paper.py`, `server/fills.py`).
  - Buys walk the live ask depth and sells walk the bid, filling at the VWAP of the levels used + 1 tick for latency.
  - Orders placed while the market is closed fill at the first poll from 09:20.
  - Real orders are refused while `PAPER=true` (`server/config.py:6`, `179-181`); `render.yaml` keeps `PAPER=true`.
- **Order types:** MARKET and LIMIT only (`server/broker.py:41-54`; Kotak `MKT` / `L`, `server/kotak.py:518`, `532`).
  SL and SL-M are not implemented; stops are simulated by the paper engine.
- **Throttling:** a Kotak rate limiter of 20 calls/s and 200/min (`server/kotak.py:148-152`).
- **Login / auth:**
  - Kotak market data needs only the consumer key, held in Render's environment and never committed.
  - Kotak real orders use TOTP automation (`KOTAK_TOTP_SECRET` + MPIN, `server/kotak.py:105-121`,
    `server/kotak_login.py`).
  - Kite uses a manual daily access token (`server/kite_login.py`).
  - Groww uses a token or TOTP.
- **Hosting:** Render free web service (`render.yaml`).
  - **No static IP.** `render.yaml` notes that real orders need a SEBI-whitelisted static IP, which the free tier
    lacks.
  - The nightly scan and the fade list are built by GitHub Actions: `daily.yml` at 20:30 IST and `fade-morning.yml`
    at 07:17 IST.
- **Logging / monitoring:**
  - Python logging on the server.
  - Paper ledger, orders and refusals in JSON / JSONL, mirrored to the `paper-state` branch through the GitHub API
    (`server/durable.py:41-104`).
  - Results pages at `/` and `/s2`.
  - **No Telegram, email or push alerts.**

## 7. SEBI April 2026 framework readiness

- **Strategy registration / strategy ID:** not implemented.
- **Static IP whitelisting:** not implemented (Render free tier; `render.yaml` header).
- **Orders tagged with an algo ID:** not implemented. Kotak and Kite orders carry no algo tag.
- **Market-to-limit / MPP conversion:** not implemented. MARKET orders are sent as `MKT`.
- **Today's position:** compliant only because nothing is sent to the exchange (paper only). Live trading would need
  all four items above.

## 8. Known problems and open questions

**Bugs, inconsistencies and risks:**
- **Risk docstring vs defaults.** `server/risk.py:4-15` says 0.5 % risk per trade and a 1 % daily halt, but
  `server/config.py:122-123` defaults to 6 % and 2 %.
- **Rule trades skip the risk gate.** Arms A, B and F bypass the manual-order kill switch and daily position caps
  (`server/rules.py:1`). A burst of results days (8 fade buys on 2025-01-31 in the backtest) is not capped.
- **Single point of failure.** If the free Render instance sleeps or restarts, polls are missed, the 15:20 exit can be
  late (`fade_late`), and the local disk is wiped. The ledger survives only through the `paper-state` mirror.
- **The backtest edge depends on the open print.** At the realistic VWAP entry the fade loses about −14 % a trade.
  Live fills at the ask after 09:15 may look more like VWAP than the open.
- **Lookahead in the backtest liquidity filter.** It uses day-0 volume (section 4).
- **Unadjusted demergers in eod2.** SIEMENS, TMPV, VEDL and others distort longer stock features. They are handled by
  drop lists in the studies, not fixed at the source.
- **Membership look-ahead.** Today's sector map and financials file are applied to the past.
- **Revised results numbers.** XBRL numbers can be revised; the live signal uses whatever is filed by the night run.
- **Thin options.** Bid/ask spreads on cheap far strikes are wide (a 3.8 % bid/ask gap was seen on INDIANB).
  Paper fills walk the book, but real fills can be worse.
- **Unreliable free futures data.** Yahoo futures series disagree with their own 1h bars by up to 7 % (S2 screen B
  addendum 2).

**Assumptions that may not hold live:**
- a fill at the live ask is available when the walk finds the strike;
- quotes at 15:20 are two-sided;
- the server is awake at 09:15 and 15:20;
- the results numbers parsed overnight match the filing the market reacts to;
- NSE holiday and expiry files are current;
- no regime change (e.g. new SEBI F&O rules on lot sizes or weekly expiries) alters stock-option liquidity.

**Open questions:**
- Does the fade survive real entries? It is judged at 30 closed trades or 6 weeks, whichever is later.
- Does the "puts above NP YoY 25 %" shadow track separate after at least 40 left-out puts?
- An always-on host with a static IP is needed before any live order.
