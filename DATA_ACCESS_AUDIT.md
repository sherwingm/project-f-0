# Data access audit: index options, India VIX, index spot (2026-10-18)

Done on Sunday 2026-10-18 (market closed). **Credentials:**
- **This machine** has none: no `.env`, and no `KOTAK_*`, `KITE_*`, `GROWW_*` or `UPSTOX_*` variables.
- **Kotak Neo:** the consumer key exists only in the Render server's environment (`render.yaml`: `KOTAK_CONSUMER_KEY`,
  `DATA_PROVIDER=kotak`). The live Kotak probes therefore ran through **temporary read-only endpoints** on the
  Render server (`/api/research/scrip`, `/api/research/candles`; commits `74efd2e`, `bfa16dc`). They were removed
  afterwards (`c8331e0`), and `server/app.py` is byte-identical to its state before the probes.
- **Kite, Groww, Upstox:** no credentials are configured on Render or locally, so they are untested.

## 1. What the code already does

| Adapter | History endpoint in code | Parameters | Max lookback / range per request | Rate limits coded |
|---|---|---|---|---|
| **Kotak Neo** (`server/kotak.py`) | `KotakProvider.history()`, `server/kotak.py:384-420` → `client().historical_data(neosymbol, interval, from_date, to_date)` | `key` (`NSE:<SYMBOL>` or an NFO trading symbol), `tf` ∈ {1, 3, 5, 15, 30} min (`HISTORY_INTERVALS`, `:256`), one `day` per call (from = to) | One day per call in code. The API itself: under 30 days for 1-minute and 5-minute, ≤ 180 days for `D`, nothing older than 5 years (probes below) | `historical_data` spaced ≥ 1.5 s (`HISTORY_MIN_INTERVAL`, `:255`); quotes 20/s and 200/min (`RateLimiter`, `:148-152`) |
| Kotak via the server | `GET /api/history/{symbol}?day=&tf=` (`server/app.py:452-484`) | **Stocks only** (`"NSE:" + sym`), past days only, refused 09:15-15:30 | As above | As above |
| **Kite** (`server/broker.py`, `server/live.py:67`) | **None.** `KiteProvider` is quotes only; there is no `historical_data` call anywhere in `server/` or `scanner/` | — | — | — |
| **Groww** (`server/groww.py`) | **None.** The module docstring mentions candles, but no candle method exists (`server/groww.py:120-220` are quotes / OI) | — | — | 10/s, 300/min (`server/groww.py:87`) |
| **Upstox** (`server/upstox.py`) | **None.** Quotes and option chains only | — | — | 25/s, 250/min, 1,000 per 30 min (`server/upstox.py:45`) |
| **yfinance** (`scanner/s2_parents.py`) | `yf.download(ticker, start, end, interval="1d")`, daily commodities / ADR / ^GSPC only | — | Not used for Indian indices | — |

**How instruments are identified:**
- **Kotak.** The scrip master files listed by `client().scrip_master()` are `nse_cm-v1.csv`, `nse_fo.csv`,
  `bse_fo.csv`, `bse_cm-v1.csv`, `cde_fo.csv`, `mcx_fo.csv` and `nse_com.csv`. A contract is
  `neosymbol = "<pExchSeg>|<pSymbol>"`.
  - **The code ingests only stock F&O** (`if inst not in ("FUTSTK", "OPTSTK")`, `server/kotak.py:209`) and `-EQ`
    equities. Index options (`OPTIDX`), indices, BSE and VIX are never loaded, so the current code cannot look them up.
  - **Lookup for NIFTY 27-Oct-2026 25000 CE:** row `pInstType = OPTIDX`, `pSymbolName = NIFTY`,
    `pTrdSymbol = NIFTY26OCT25000CE` (monthly form; weeklies read `NIFTY26O19<strike>CE`), expiry from `pExpiryDate`
    + `EPOCH_OFFSET` (`server/kotak.py:63`).
  - Example found by the probe: `NIFTY26OCT23050CE` → `nse_fo|51354`.
  - BSE `pExpiryDate` does **not** use the NSE offset: it came out 10 years late (2036-10-21 for 22-Oct-2026).
- **Kite.** The instrument dump's `instrument_token`. Not implemented in this repo for history.
- **Groww.** Symbols like `NSE-NIFTY-28Oct26-25000-CE`. Not implemented for history.

## 2. Live probes

All Kotak calls went through `historical_data(neosymbol, interval, from_date, to_date)`. **HTTP is 200 for every call**
(errors come back in the body). "Last 5 sessions" means 2026-10-12 → 2026-10-16. ATM strikes came from the spot on
2026-10-16: NIFTY ≈ 23,050, BANKNIFTY ≈ 55,900, SENSEX ≈ 74,400.

### Kotak Neo

| # | Probe | neosymbol, interval, dates | Rows | First → last | Error / note |
|---|---|---|---|---|---|
| a | NIFTY 50 spot, 1-min, 5 sessions | `nse_cm\|26000`, 1min | 0 | — | `422 Invalid neosymbol`: the numeric token does not work for indices |
| a | NIFTY 50 spot, 1-min, 5 sessions | `nse_cm\|Nifty 50`, 1min, 10-12 → 10-16 | **1,807** | 2026-10-12 09:15 → 2026-10-16 15:28 | Works by the **index name** |
| b | NIFTY **weekly** 19-Oct-2026 22650 CE (nearest weekly; Monday, moved for the 20-Oct holiday) | `nse_fo\|47141`, 1min | **1,923** | 10-12 09:15 → 10-16 15:39 | Volume present (71,695 in the first minute) |
| b | NIFTY 27-Oct-2026 23050 CE (nearest Tuesday expiry, the October monthly) | `nse_fo\|51354`, 1min | **1,870** | 10-12 09:15 → 10-16 15:39 | — |
| b | Same weekly contract, by trading symbol | `nse_fo\|NIFTY26O1922650CE`, 1min | 0 | — | **No error, silently empty**: the token is required |
| c | NIFTY weekly 19-Oct 22650 CE, 5-min | `nse_fo\|47141`, 5min | **385** | 10-12 09:15 → 10-16 15:35 | — |
| d | NIFTY that **expired last week** (13-Oct-2026 23050 CE) | `nse_fo\|NIFTY26O1323050CE`, 1min, 10-12 → 10-13 | 0 | — | **Silently empty.** Expired contracts are **not in the scrip master** (it lists only live expiries, 2026-10-19 → 2031), so no token exists to ask for |
| e | NIFTY options expired Jan 2025 / Jan 2023 | — | not callable | — | Same: no token for any expired contract. The index **spot** lookback was probed instead (rows below) |
| e′ | NIFTY 50 spot, 1-min, 2025-01-15 | `nse_cm\|Nifty 50` | 376 | 09:15 → 15:30 | — |
| e′ | NIFTY 50 spot, 1-min, 2023-01-16 | `nse_cm\|Nifty 50` | 376 | 09:15 → 15:30 | — |
| e′ | NIFTY 50 spot, 1-min, 2022-01-03 | `nse_cm\|Nifty 50` | 390 | **09:01** → 15:30 | Pre-open minutes included in 2022 |
| e′ | NIFTY 50 spot, 1-min, 2020-03-23 | `nse_cm\|Nifty 50` | 0 | — | `422 fromDate cannot be older than 5 years` |
| f | India VIX by token / other names | `nse_cm\|26017`, `India Vix`, `INDIAVIX`, `India VIX` | 0 | — | `422 Invalid neosymbol` (VIX has no scrip-master row) |
| f | India VIX, 1-min, 2026-10-16 | `nse_cm\|INDIA VIX`, 1min | **376** | 09:15 → 15:30 | Exact name works |
| f | India VIX, daily, last 180 days | `nse_cm\|INDIA VIX`, `D`, 2026-04-20 → 2026-10-16 | **125** | 2026-04-20 → 2026-10-16 | — |
| f | India VIX, daily, oldest allowed | `nse_cm\|INDIA VIX`, `D`, 2021-10-25 → 2022-04-20 | **121** | 2021-10-25 → 2022-04-20 | Daily back to ≈ 5 years |
| f | India VIX, 1-min, 2022-01-03 | `nse_cm\|INDIA VIX`, 1min | 390 | 09:01 → 15:30 | **Values ×100** (open 1622.25 for VIX ≈ 16.2): a scaling issue in older minutes |
| f | Daily interval names | `day`, `1day`, `1D` | 0 | — | `422 Invalid interval value`. Only `D` is accepted |
| g | SENSEX **weekly** 22-Oct-2026 74400 CE (BSE, Thursday) | `bse_fo\|1125427`, 1min | **1,825** | 10-12 09:15 → 10-16 15:39 | BSE index options work. SENSEX spot `bse_cm\|SENSEX`: 362 rows on 10-16 |
| h | BANKNIFTY **monthly** 27-Oct-2026 55900 CE | `nse_fo\|49465`, 1min | **1,908** | 10-12 09:15 → 10-16 15:39 | BANKNIFTY spot `nse_cm\|Nifty Bank`: 362 rows. (A far OTM strike, 50600 CE, returned 0 rows: no trades.) |

**Range limits per request:**

| Call | Result |
|---|---|
| 1-min, 29 days (2026-09-17 → 10-16) | 7,607 rows |
| 1-min, 30 / 90 / 365 days | **Rejected:** `422 Date range exceeds maximum allowed for 1min interval. It must be 30 days or less.` |
| 5-min, 29 days | 1,548 rows |
| 5-min, 90 days | Rejected (same "30 days" message) |
| `D`, 180 days | 125 rows |

- Older than 5 years: **rejected with an error**, not truncated.
- An expired or unknown symbol in trading-symbol form: **silently empty**.

### Kite Connect, Groww
Untested: no credentials, and the code has no history call for either. From Kite's **documentation** (not tested
here): minute data is 60 days per request; expired option contracts drop out of the instrument dump.

### yfinance (local, version 1.7.0)

| Ticker | 1-min (`period=8d`) | 1-min, last 30 days | 1-min, 2025-01-13 → 15 | 5-min (`60d`) | Daily (`max`) |
|---|---|---|---|---|---|
| ^NSEI | 2,988 rows, 2026-10-07 → 10-16 | Empty: "Only 8 days of 1m per request" | Empty: "must be within the last 30 days" | 4,496, 2026-07-23 → 10-16 | 4,682, **2007-09-17** → 2026-10-16 |
| ^INDIAVIX | 2,988 | Empty | — | 4,496 | 4,563, **2008-03-03** → 2026-10-16 |
| ^NSEBANK | 2,988 | Empty | — | 4,496 | 4,697, 2007-09-17 → |
| ^BSESN | 2,988 | Empty | — | 4,496 | 7,217, 1997-07-01 → |

yfinance has no Indian option contracts.

## 3. Local data already on disk

- **`data/cache/fo_bhavcopy_YYYYMMDD.csv`:** 1,422 files, **2021-01-01 → 2026-10-16**, every session. They contain
  **index options** (`FinInstrmTp = IDO`) and index futures (`IDF`) for NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY and
  NIFTYNXT50.
  - Example: on 2021-12-01 there are 6,308 IDO rows; on 2026-10-16, 5,785.
  - **No SENSEX:** that is BSE, and these are NSE files.
  - Cached columns: `TradDt, TckrSymb, FinInstrmTp, XpryDt, StrkPric, OptnTp, ClsPric, UndrlygPric, OpnIntrst,
    ChngInOpnIntrst, TtlTradgVol` (+ `NewBrdLotQty` in recent files). So it is daily **close, OI and volume only**:
    open / high / low are dropped by the cache (`scanner/nse_fo.py:58`, `_WANTED`).
  - **Weekly expiries are present.** NIFTY expiries listed on 2022-01-03: 2022-01-06, 01-13, 01-20, 01-27, 02-03, …
    NIFTY expiries seen in the Jan-2025 files: **2025-01-02, 01-09, 01-16, 01-23, 01-30** (the Thursday weeklies).
- **`data/cache/fo_prices_*.csv`:** 377 files, 2022-01-13 → 2026-10-16, with daily OHLC, but **stock options only**
  (0 index rows), and only for the fade-trade days.
- **India VIX:** `data/cache/index/ind_close_all_*.csv`, 474 days of NSE's daily index file. They hold daily
  open / high / low / close for `India VIX`, `Nifty 50` and `Nifty Bank`, but only for the days the studies needed.
  `scanner/fade_diagnostics.py:88` (`index_ohlc`) can fetch any other date from NSE's archive.
- **Index daily closes:** `data/eod2/nifty 50.csv` and `nifty 500.csv` (closes only).
- **Index minute candles:** none on disk. `data/cache/intraday/` holds 870 **stock** 1-minute day files (from the
  stop-loss studies).

## 4. Summary table

| Data need | Kotak (via the server's key) | Kite | Groww | yfinance | Local bhavcopy |
|---|---|---|---|---|---|
| Index spot, 1-min | **Yes**, to 5 years back (2021-10); under 30 days per call; by index name (`nse_cm\|Nifty 50`) | Untested (no credentials) | Untested (no credentials) | Last ~30 days only (8 days per call) | No |
| Index option, 1-min, **current** contracts | **Yes** (NIFTY weekly / monthly, BANKNIFTY, SENSEX); needs the scrip-master token | Untested | Untested | No | No |
| Index option, 1-min, **expired** contracts | **No**: expired contracts are not in the scrip master, and calls without a token return empty | Untested (docs: not in the instrument dump) | Untested | No | No |
| Option, 5-min | Yes, current contracts only; under 30 days per call | Untested | Untested | No | No |
| India VIX, daily | **Yes**, `nse_cm\|INDIA VIX`, `D`, back to 2021-10 (180 days per call); older 1-min looks ×100 | Untested | Untested | **Yes**, back to 2008-03-03 | Yes, from NSE's daily index file (474 days cached; any date fetchable) |
| SENSEX options | **Yes** (current; `bse_fo`, inst `IO`) | Untested | Untested | No | No (NSE files only) |
| BANKNIFTY options | **Yes** (current, monthly) | Untested | Untested | No | Daily close / OI / volume 2021-01 → 2026-10 |
| Daily option OHLC / OI | Current contracts only (`D`) | Untested | Untested | No | **Yes, every index option strike, 2021-01-01 → 2026-10-16**: close / OI / volume cached; OHLC needs a re-download of the raw files |

## 5. Verdict

**No.** As it stands, this repo **cannot** assemble a strike-level 1-minute dataset for NIFTY weekly options back to
2022.

**The blocker is expired contracts.** Kotak's `historical_data` needs the contract's scrip-master token. The scrip
master lists only live contracts (expiries 2026-10-19 → 2031). There is no token for any contract that has already
expired, and calls by trading symbol return silently empty.

The other limits are workable:
- the **5-year cap** reaches back to 2021-10;
- **30 days per request** only means more calls;
- **the interval** is fine: 1- and 5-minute both work for live contracts.

Kite and Groww are untested and have no history code. Kite's documentation also excludes expired options.

**What is obtainable instead:**
1. **Index spot and India VIX, 1-minute, Oct 2021 → today** from Kotak. That is about 5 years × 250 sessions ÷
   ~20 sessions per call ≈ 65 calls per series, ≈ 2 minutes at the coded 1.5 s spacing. Older VIX minutes need the
   ×100 fix.
2. **Daily close / OI / volume for every NIFTY / BANKNIFTY / FINNIFTY / MIDCPNIFTY option strike, 2021 → today,**
   already on disk. Full daily OHLC needs a re-download of the raw NSE bhavcopies. SENSEX daily options would need
   BSE's bhavcopy, which is not implemented.
3. **Option minute data from today forward:** record the live contracts' 1-minute candles before they expire. Each
   weekly is listed weeks ahead, so a nightly job can fetch every strike within ±5 % daily.
   - **Per weekly:** ±5 % of 23,000 at 50-point steps is about 46 strikes × 2 (CE/PE) ≈ 92 contracts. With one call
     per contract per week (under 30 days), that is ≈ 92 calls ≈ 2.3 minutes at 1.5 s spacing.
   - **Hypothetical full history:** if expired tokens were obtainable, 2022 → today is ≈ 250 weeklies × 92
     contracts × 1-2 calls ≈ 23,000-46,000 calls ≈ 10-19 hours at the coded 1.5 s spacing.

**Still open:** whether Kotak keeps serving a token **after** its contract expires. The 19-Oct-2026 weekly (token
47141) expires tomorrow, so re-probing it on 2026-10-20 would answer that. Only a token learned before expiry can be
tested this way.
