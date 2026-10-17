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

## Addendum 2026-10-18 (before any table was produced)
The first full build crashed in the feature step (a missing eod2 close), so no table had been computed. An independent
design review (one agent, read-only) found real gaps; these changes are fixed **now, before any bucket result is seen**.
**Disclosure:** while checking the loser thresholds the reviewer computed the Q1 loser-class counts (open entry): losers
2025-26 260 (puts 191 / calls 69), 2022-24 277 (205 / 72); never up — puts 62 / 69, calls 23 / 26; round trip — puts
81 / 71, calls 22 / 27 (2025-26 / 2022-24). Nothing for Q2-Q7 was computed.
1. **Filing slot** (from the event time): pre-open day 0 / in session day −1 (09:15-15:30) / after the close day −1 /
   non-session day or earlier. For an in-session filing the day −1 close already holds part of the reaction, so **every
   pre-run, the 52-week place and the volume ratio end at the last close before the filing** (day −2 for in-session
   filers, else day −1). The filing-time bucket uses these four slots.
2. **Reaction before entry** (known at 09:15): day 0's open ÷ the last close before the filing − 1, per side,
   buckets ≤ −2 % / −2 to +2 % / ≥ +2 % (Q7). The day-0 gap stays as fixed.
3. **Beta-adjusted market benchmark:** beta from 250 daily close→close returns to the pre-run base (≥ 150 needed);
   Q2 shows the fade raw, net of NIFTY with beta = 1, net of beta × NIFTY, and net of the sector.
4. **Special sessions:** Muhurat and short special sessions (2022-10-24, 2023-11-12, 2024-03-02, 2024-05-18,
   2024-11-01, 2025-10-21) are left out of every table and counted; full special sessions (2024-01-20, budget days
   2025-02-01, 2026-02-01) stay and are flagged.
5. **Corporate-action guard:** a one-day close→close move > 20 % inside a feature's look-back window sets that feature to
   blank (listed in a coverage table), since eod2 misses some demergers.
6. **The guard, sharpened:** per window, the bucket-vs-rest date-clustered t; pooled t = (t₁ + t₂) ÷ √2 (the windows
   have different means, so they are not simply stacked). **Consistent** = N ≥ 30 and ≥ 15 distinct day-0 dates in
   each window, the same sign in both, |t| ≥ 1 in each and |pooled t| ≥ 2. **Strong** = consistent and |pooled t| at
   the Bonferroni 5 % level for the number of tests run. The report prints the number of tests and the number of
   "consistent" buckets expected by chance. Each bucket also shows the median, the hit rate, the VWAP-entry mean and,
   as a second outcome with more power, the **stock's own fade** (signed day-0 open→close, + = moved against the
   headline) with its own pooled t.
7. **Q4 extension, all filings with numbers (stock level, more power than the trades):** the day-0 open→close net of
   NIFTY, and the reaction before entry, in bins over the whole range — NP YoY < −50 / −50 to −25 / −25 to −10 / −10 to 0
   / 0 to 10 / 10 to 25 / 25 to 50 / 50 to 100 / > 100 %; NP QoQ < −30 / −30 to −10 / −10 to 0 / 0 to 10 / 10 to 30 /
   > 30 %; revenue YoY < 0 / 0 to 10 / 10 to 20 / > 20 % — per window. This shows where a fade starts, including the
   zones the rule never trades (NP YoY −10 to +10 %).
8. **Q1 extension:** the stock's best move in the bet's direction on day 0 (puts: open → low; calls: open → high) and
   its day range, per loser class, separating "the stock never moved" from "it moved but the option did not pay".
9. **Q5:** each example also shows how many fade trades were taken that day and how many won, and its distance below
   the 52-week high. The examples were picked with hindsight: illustrations, not evidence.
10. **Verification** (within this session's small-workflow limit): three independent agents each try to refute every
    headline claim from the feature CSVs with their own code (a claim survives with at least 2 of 3), one of them also
    rebuilds about 15 random trades and the examples from the raw files; plus a completeness critic.
