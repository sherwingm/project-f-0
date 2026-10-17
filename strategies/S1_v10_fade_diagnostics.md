# S1 v10 fade · diagnostics: why losers lose, market vs pre-run, result-number rules, other measures

**Pre-registered 2026-10-18**, before any of these numbers is computed. Descriptive only: no rule change follows; a
measure that stands out can only become a component of a new pre-registered paper version (S1 v11).
Code: `python -m scanner.fade_diagnostics` → `data/results/S1_v10_fade_diagnostics.md` / `.xlsx`.

## The user's questions (2026-10-18)
1. Do heavy losers (calls and puts) lose because the option **never moved up**? Why?
2. Their example charts (BPCL, OBEROIRLTY, BEL, ADANIPORTS, BAJFINANCE, BOSCHLTD, HCLTECH, POLYCAB, SONACOMS):
   does a stock that **already fell** before results make the put worse, or better, or is it the **market**
   (benchmark NIFTY 50)?
3. Should there be a threshold on **NP YoY %, NP QoQ % or revenue YoY %** (each)?
4. "If the run is already done before the results, then for sure it does the opposite" — and do we need **other
   measures** than the three result numbers?

## Data
- **Fade trades:** `data/results/S1_v10_trades_2022_24.csv` (2022-24) and `S1_v10_trades.csv` (2025-26), with a valid
  same-day exit. Outcome = net % of premium with the **open entry** (primary) and with the **VWAP entry** (realism check).
- **All results filings of F&O stocks** (Q6): the event store's `results` events whose day 0 falls in either window
  (2022-01-01 → 2024-12-31, 2025-01-01 → 2026-09-25), the stock in the previous session's F&O bhavcopy, one per stock and
  day 0 (the earliest filing). 2022 filings are thin for Jul-Nov 2022 (NSE classification gap): stated as a limit.
- Stock daily OHLC and volume: eod2 (`scanner/equity.load_symbol`, adjusted). NIFTY 50: daily open / close from NSE's
  `ind_close_all` file for day 0, closes from eod2 for the pre-runs. Sector: `data/sector_map.csv`, leave-one-out
  equal-weight mean of the other stocks' day-0 close→close (≥ 3 peers).
- Option day OHLC: the bhavcopy price files; futures OI: the cached F&O bhavcopies (all expiries combined).

## Features (fixed now; all known before day 0's open unless marked "day 0")
- **Option (day 0):** peak % = day high ÷ entry − 1; dip % = day low ÷ entry − 1; classes among losers: **never up**
  (peak < +10 %), **round trip** (peak ≥ +30 % and net < 0), **other**.
- **Stock:** pre-run 5 / 20 / 60 sessions = close(d−1) ÷ close(d−1−N) − 1; the same net of NIFTY 50; place in the
  52-week range (0 = low, 1 = high, on the 252 sessions to d−1); volume ratio = volume(d−1) ÷ mean of the 20 sessions
  before it; futures OI change over the 5 sessions to d−1. Day 0: gap = open ÷ close(d−1) − 1; open→close; close→close;
  **stock faded** = the signed open→close > 0 (moved against the headline).
- **Market (day 0):** NIFTY 50 open→close and close→close; sector leave-one-out close→close.
- **Option context:** strike distance from the stock (% out of the money, against the previous close), sessions to
  expiry, lot cost, filing time (before 09:15 on day 0 = **pre-open**, else **after the close / overnight**).
- **Result numbers:** NP YoY, NP QoQ, revenue YoY (the rule's three) and EPS YoY / QoQ (from the filing's XBRL).

## Questions and fixed buckets (each table for 2022-24 and 2025-26 side by side, per side PE / CE)
- **Q1 loser anatomy:** shares of never up / round trip / other among losers and their mean net %; the 2×2 stock faded ×
  option won (count, mean net %).
- **Q2 market:** NIFTY day-0 open→close down < −0.3 %, flat, up > +0.3 %; the same for close→close; the stock's fade
  raw vs net of NIFTY vs net of its sector (mean, date-clustered t).
- **Q3 pre-run and position:** pre-run 20: ≤ −5 %, −5 to +5 %, > +5 %; pre-run 5: ≤ −3 %, −3 to +3 %, > +3 %; the same
  two net of NIFTY; gap: ≤ −2 %, −2 to +2 %, ≥ +2 %; 52-week place: < 0.33, 0.33-0.67, > 0.67.
- **Q4 result numbers:** PE: NP YoY 10-25 / 25-50 / 50-100 / > 100 %; NP QoQ 0-10 / 10-30 / > 30 %; revenue YoY 0-10 /
  10-20 / > 20 %. CE: NP YoY −10 to −25 / −25 to −50 / < −50 %; NP QoQ 0 to −10 / −10 to −30 / < −30 %; revenue YoY < 0 /
  0-10 / > 10 %.
- **Q5 the user's 9 stocks:** every fade trade of theirs, with its features and a one-line reading.
- **Q6 "run done → the opposite" (all filings, stock level):** reversal = −sign(pre-run) × day-0 reaction (positive =
  moved opposite to the run), for pre-run 5 and 20, raw and net of NIFTY, reaction open→close and close→close; by run
  size |run| < 3 %, 3-8 %, > 8 %: share opposite, mean reversal, date-clustered t. Then on the fade trades: puts after
  a run-up (pre-run 20 > +5 %) vs after a fall (≤ −5 %), calls likewise.
- **Q7 other measures:** EPS YoY (PE: 10-25 / 25-50 / > 50; CE: −10 to −25 / −25 to −50 / < −50), EPS QoQ (same split by
  sign as NP QoQ), volume ratio < 1 / 1-2 / > 2, futures OI 5-session change ≤ −5 / −5 to +5 / > +5 %, filing time
  pre-open / after close, strike distance < 2 / 2-5 / > 5 %, sessions to expiry ≤ 5 / 6-15 / > 15, sector day-0
  down / flat / up (±0.5 %).

## The consistency guard (decides "stands out")
A bucket stands out only if, **in both windows**, it has N ≥ 30 and its mean net % differs from the rest of its side in
the **same direction**, and the pooled date-clustered t of the difference (`scanner/stats.clustered_diff_t`) is
≥ 2 in absolute value. Every such bucket is also shown with the VWAP entry; one that only works with the open entry is
flagged. The report states how many bucket tests were run; with that many, a few will pass by chance.

## Verification of the headline claims
Each headline claim in the report is checked by a workflow of independent agents that recompute it from the feature
CSV with their own code and try to refute it (three per claim, majority decides), plus a completeness critic. Claims that
do not survive are dropped or reworded, and the report says so.

## Known limits
- Not out of sample (2021-26 has been used by S1 v2-v10); many tests; descriptive only.
- eod2 prices are adjusted for splits / bonuses; a corporate action inside a pre-run window is not removed.
- No analyst consensus, guidance or margins beyond the XBRL: "surprise" cannot be measured, only the reported change.
