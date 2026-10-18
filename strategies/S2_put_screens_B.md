# S2 puts: parent indicators, sector rotation, gap fill, weak results, fundamentals - stock-level screens

**Pre-registered** (2026-10-14). Every choice below is fixed before any return is computed. These are screens of the stock's own move in the short direction. None of them is a strategy. A cell that passes gets its own put backtest, written and pre-registered separately. Run: `python -m scanner.s2_parent_screen`, `scanner.s2_market_filter`, `scanner.s2_rotation_screen`, `scanner.gap_screen`, `scanner.s2_weak_results_screen` (new modules; no existing module is edited). This is **S2 screen B** in DECISIONS.md. S2 step 1 (`strategies/S2_oi_buildup_screen.md`) was price + futures OI build-up. This page tests the user's other S2 ideas on the same window.

**Why.** For the S2 put side, the user asked for these:
- (a) **Parent indicators.** Watch the commodity or overseas series that leads each stock: Brent for oil, iron ore (FEF1!) for steel, the INFY ADR for IT.
- (b) **Market backdrop.** Brent and GIFT Nifty for the short term, NIFTY 50 for the long term, used as support.
- (c) **Sector rotation.** A cyclical sector falls (e.g. metals on global news) while one or two of its stocks have "gone too high" and may fall back.
- (d) **Gap-fill theory.**
- (e) **Weak results / negative cash flow.** Either the correction already happened in the days before, or it is still to come.
- (f) **Fundamentals.** High debt/equity, order book far above what can be executed (the RVNL example), QIP dilution, negative cash flow.

Window: 2021-01-01 → 2026-09-25, the last session with stock closes. Every year is judged on its own. No holdout is left, so a pass is followed by a put backtest and then live paper days.

## Order of work (gates before any screen runs)
1. **Run the pre-registered S2 step 2 first** (`python -m scanner.backtest_s2_put`) and record it in DECISIONS.md. It answers the cheap question that comes before everything here: can a bought put keep a +0.6 % stock edge over 5 sessions?
2. Cache the external series once, after the window has closed:
   - yfinance 1.7.0, `auto_adjust=False`, column `Close`, index tz-stripped to the exchange trade date.
   - Range 2020-04-01 → 2026-09-27. Never a bar dated on or after the download day.
   - Save to the **tracked** path `data/parents/yf_<ticker>.csv`, with download time and SHA-256 recorded in DECISIONS.md.
   - Add `yfinance==1.7.0` to `requirements-dev.txt`. Reruns read the cache and never download again.
3. Wait for the running `financials.json` backfill to finish (only §5 needs it). Then freeze it: SHA-256, mtime and stock count go into DECISIONS.md. No refresh is allowed between this freeze and the run.
4. **Recount events (no returns) from the cached data with the final definitions.** Publish N, distinct dates and N per year for every pass cell. A pass cell that falls below its minimums is dropped before any return is looked at, and the drop is recorded.

## Common rules
- **Calendar.** NSE sessions from eod2 `nifty 500.csv`.
  - Muhurat sessions (2021-11-04, 2022-10-24, 2023-11-12, 2024-11-01, 2025-10-21) and weekend budget sessions (2024-01-20, 2025-02-01, 2026-02-01) are never a signal day or an entry day.
  - Entry and exit must be on the true next or h-th NSE session, and the stock must have an eod2 EQ row on each. Stepping by the stock's own row positions is not allowed. A missing row drops the event, and drops are counted.
  - Returns use `pct_change(fill_method=None)`. The first return after a gap in a stock's rows is NaN.
- **Universe.** Stock futures OI > 0 in the **last F&O bhavcopy before entry**: day d for a d+1 entry, day i−1 for a day-0 entry. OI panel: `data/cache/s2_oi_panel_2021-01-01_2026-09-25.csv`.
  - Renamed tickers are joined through `EOD2_ALIASES`, plus TATAMOTORS→TMPV, MOTHERSUMI→MOTHERSON and LTIM→LTM.
  - Names with no eod2 file drop out and are counted: HDFC, MINDTREE, LTI, CADILAHC, SRTRANSFIN, AMARAJABAT, GUJGASLTD, IDFC.
- **Corporate actions.**
  - eod2 adjusts splits and bonuses but **not demergers**. The demerger list is:
    - rows of `data/cache/corp_actions.csv` with kind `other` and a subject containing "Demerger";
    - plus any EQ one-day move ≤ −30 % or ≥ +50 % with no matching action;
    - known cases: VEDL 2026-04-30, TMPV 2025-10-14, SIEMENS 2025-04-07, MOTHERSON 2022-01-14, NMDC 2022-10-27, RELIANCE 2023-07-20, GMRAIRPORT 2022-01-11.
  - An event is dropped if its stock has a listed action anywhere in d−20 … d+h.
  - In every leave-one-out sector, that stock's return on its ex-date is set to NaN. Drops are counted per action.
- **Return.**
  - Short = −(Close[exit] ÷ Open[entry] − 1) × 100 − **0.1 %**. Entry is the official open of the stated session; exit is the close of the stated session.
  - Live note: the open is the pre-open auction price, and a put can only be bought from 09:15.
- **External series (§1, §2).**
  - The value used for an entry on session E comes from the last bar dated **strictly before E** and **on or before signal day d**. Lookup is `series.loc[index < E].iloc[-1]`. `asof`, `ffill` or reindexing onto E is never used.
  - Unit tests cover: Friday→Monday; an NSE holiday with a US session; a US holiday on d; the 2025-02-01 Saturday session; known closes (BZ=F 127.98 on 2022-03-08 and 111.14 on 2022-03-09, CL=F −37.63 on 2020-04-20).
  - A test checks that the BZ=F, HG=F, ALI=F and INFY daily Close dated D matches that product's settlement or close on the 1h bars of ET date D, for every day the 1h data covers. **The run aborts if this fails.**
- **Reported per cell.** N; distinct signal dates G; ISO weeks; mean; median; hit rate; mean and N per year 2021–2026; means for the periods 2021-22, 2023-24 and 2025-26; the minimum mean that could reach t = 3 at that N.
- **Pass (a cell):**
  1. N ≥ 100 and G ≥ 60 distinct signal dates (§1: ≥ 100 shock dates; see §1).
  2. **t ≥ 3**, where t is the smaller of the date-clustered and the ISO-week-clustered t (`stats.clustered_t`). Overlapping 3–5 session holds share weeks.
  3. Mean ≥ **+0.6 %**, short direction.
  4. Mean positive in ≥ 5 of the 6 years, including 2025 and 2026.
  5. **Robustness:**
     - t ≥ 2 with the 5 dates of largest absolute contribution removed;
     - t ≥ 2 with the single largest stock removed;
     - **not the step-1 effect again:** t ≥ 2 and mean ≥ +0.6 % on the events that are not S2 step-1 signals (the step-1 class named per screen) on the same stock in d−10 … d.
- **Side reports never promote.** No descriptive row, split, side report, opposite-sign result or alternative horizon can become a lead, a new screen or step 2 on 2021-2026 data. A later idea from any of them is judged only on data after 2026-09-25 (live paper).
- **Test accounting.**
  - This page has **14 pass-eligible cells forming 11 pass tests**. §1 and §5 cells must pass at h3 and h5 jointly. §2 uses Holm across 3.
  - Before this page, the same window already carries about 165 tests: S2 step 1 48, event screens 69, S1 v9 options 48. The new total goes into DECISIONS.md. One t ≈ 3 among about 176 tests is consistent with chance, which is why a pass goes to paper before money.

| § | Screen | Pass tests | Pass-eligible cells | Descriptive rows |
|---|---|---|---|---|
| 1 | Parent indicator (Brent, iron ore, copper, INFY ADR) | 2 | 4 | 6 |
| 2 | Market backdrop filter on the S2 step-1 cell | 3 | 3 | 7 |
| 3 | Sector rotation: stretched stock in a falling cyclical sector | 2 | 2 | 7 |
| 4 | Gap-fill short | 3 | 3 | 9 |
| 5 | Weak results × pre-move | 1 | 2 | 8 |
| | **Total** | **11** | **14** | 37 |

## 1. Parent indicator (user ideas a, f-metal, "same we can use the infy")
**Hypothesis.** F&O stocks under-react to an adverse move in their parent that is known before the next NSE open. After a large adverse parent move, the child keeps falling from the next open for 3–5 sessions. **Null:** the next open prices the move fully, so the short from the open earns ≈ 0, or loses if the gap fills.

**Parent map** (fixed; link +1 means a parent fall is adverse; −1 means a parent rise is adverse):

| Parent | Link | Children | Cells |
|---|---|---|---|
| INFY ADR (NYSE, USD) | +1 | INFY, TCS, WIPRO, HCLTECH, TECHM, LTM (panel LTIM + LTM), COFORGE, MPHASIS, PERSISTENT, BSOFT | k=1, k=5 |
| BZ=F (NYMEX Brent last-day financial) | +1 | ONGC, OIL | k=1, k=5 |
| BZ=F | −1 | BPCL, HINDPETRO, IOC, ASIANPAINT, BERGEPAINT, INDIGO, APOLLOTYRE, MRF, BALKRISIND | k=1, k=5 |
| HG=F (COMEX copper) | +1 | HINDCOPPER, VEDL, HINDZINC | k=1, k=5 |
| TIO=F (CME TSI 62 % iron ore, a **stand-in for SGX FEF**, not FEF1! itself) | +1 | TATASTEEL, JSWSTEEL, JINDALSTEL, SAIL, NMDC, JSL | **k=5 only**, lagged one session |
| ALI=F (thin COMEX aluminium, not LME) | +1 | HINDALCO, NATIONALUM | side report only |

The map was chosen after seeing full-sample next-open-gap correlations, so the choice is itself a degree of freedom. Exclusions:
- Excluded as unclear links: ADANIENT, COALINDIA, RELIANCE, city gas, and the IT ER&D/product names (KPITTECH, TATAELXSI, LTTS, CYIENT, TATATECH, OFSS, INTELLECT, SAGILITY and the other non-F&O sector_map IT names).
- WIT is not used (6 % zero returns).
- MINDTREE and LTI cannot be priced (no eod2 file) and are counted as dropped.

**Parent level.**
- Daily log returns on the parent's own bars.
- **Roll guard:** for TIO=F and BZ=F, the return on the first exchange trading day of each month is set to 0, because the continuous series rolls there. A no-guard version is a side row; it keeps real shocks such as Brent on 2026-04-01 visible.
- TIO=F days with a zero return are treated as missing, not as 0.

**Measures** (z = link × measure ÷ (σ × √k); adverse = z ≤ −1.5):
- **k=1, IT:** g(d) = ln(ADR_d) + ln(USDINR_d) − ln(NSE INFY close_d) − the median of the same over d−20 … d−1.
  - `USDINR=X` "Close" is a ≈ 09:00 IST snapshot on d. That is causal, but it is not simultaneous with the ADR close, so g carries the NSE-session INR move as noise.
  - g = NaN (no signal, no σ contribution) if the ADR's last bar is not dated d (US holiday), or within one session of an INFY ex-date on NSE or NYSE.
  - σ = sd of g over d−60 … d−1.
- **k=1, BZ=F and HG=F:** the residual e(d) = r_P(d) − b × r_child(d).
  - r_P(d) is the guarded return of the bar dated exactly d. Otherwise no signal; a forward-filled value is never used.
  - b is the OLS slope of r_P on the child's NSE close-to-close return over d−60 … d−1.
  - This removes the part of the parent's move already priced during NSE session d.
  - σ = sd of e over d−60 … d−1.
- **k=5:** L(d) − L(d−5 sessions) on the aligned guarded level (IT: ln(ADR × USDINR)).
  - TIO=F uses bars dated ≤ d−1. Its settlement against Platts IODEX falls in Asian hours, and Yahoo serves no 1h bars to verify it.
  - σ = sd of the aligned 1-session changes over 60 sessions ending d−5.
  - k=5 is a slow catch-up measure. Most of it is known during NSE sessions.
- **Event.**
  - z ≤ −1.5 on day d for an eligible child.
  - One signal per stock per cell every 5 sessions.
  - **Entry: open of d+1**, short. Exits: close of d+1, d+3, d+5.

**Judged on dates, not stocks.** One IT shock hits about 10 stocks at once. So each shock date is one observation: the equal-weight mean of its children's returns. N, t and the year test run on these date means. A cell needs **≥ 100 shock dates** in total and **≥ 15 shock dates in every year**.

**Cells:**

| Cell | Measure | Horizons | Role |
|---|---|---|---|
| P1 | k=1, z ≤ −1.5 | h3 **and** h5 (both must pass) | pass test |
| P2 | k=5, z ≤ −1.5 | h3 **and** h5 (both must pass) | pass test |
| — | P1, P2 at h1 | | descriptive |
| — | k=1 and k=5 at z ≤ −2.0, h3 / h5 | | descriptive |

Extra pass condition for P1 and P2: with each parent group left out in turn, the mean stays positive and t ≥ 2. The step-1 class for the overlap rule is **short build-up** (3 % / 10 %).

**Expected N** (draft definitions, before the fixes above):
- k=1 z ≤ −1.5: 1,670 events on 304 dates (287/269/275/315/316/208 events a year).
- k=5 z ≤ −1.5: 1,080 events on 195 dates.

Removing TIO from k=1, moving ALI to the side report, and the NaN rules all lower these. The recount (gate 4) decides.

**Power.** Per-date sd at h5 is ≈ 4.5 %. To reach t = 3 at h5 the true mean must be ≈ 0.8 % (≈ 300 dates) or ≈ 1.0 % (≈ 195 dates), and more under week clustering. A true +0.6 % effect would usually fail.

**Side reports** (no pass):
- per parent group;
- ALI=F group;
- no-guard roll;
- d+1 opening gap ≤ −1 % vs above (gap fill vs continuation);
- the "not yet followed" subset (the child's k-session return above the parent's adverse move);
- return net of NIFTY 500 over the same open d+1 → close d+h window.

The leave-one-out sector is not used here, because a parent shock hits the whole sector.

## 2. Market backdrop filter (user idea b; GIFT Nifty proxy)
**Question.** Does a risk-off backdrop make the one passing S2 step-1 cell work better?

The base cell is short build-up: close-to-close ≤ −3 %, combined futures OI ≥ +10 %, volume ≥ 1.5× its 20-session average, expiry day and the session after skipped, 5-session cooldown. It had 965 events at h5, mean +0.62 %, t 3.17. It was the best of 48 cells, so its true mean is probably lower (winner's curse). Its h3 version failed step 1, so h3 is descriptive only.

**Entry session E** is the stock's own next eod2 row after d, which is the row r5 used. It must equal the NIFTY 500 next session. Mismatches are dropped and listed (ALKEM and DIXON on 2022-05-10). Every input is dated < E: external bars dated < E, NSE closes on d.

**Filters** (states are fixed; the look-backs are frozen and no other length will be tried on 2021-2026):

| Cell | State (on) | Role |
|---|---|---|
| F1 | BRENT_UP5: BZ=F close of the last bar < E ÷ the close 5 bars earlier − 1 > 0. NA if that bar is dated before d | pass test (primary) |
| F2 | US_OVERNIGHT_DOWN (GIFT Nifty proxy): ^GSPC's last bar < E closed below the bar before. NA if that bar is dated before d (stale: the US was shut on d) | pass test |
| F3 | NIFTY_DOWNTREND: NIFTY 50 close on d < its 50-session SMA ending d | pass test |
| — | F4 SPX_DOWNTREND (^GSPC < SMA50; 146 of 303 events in 2022, 6 in 2021) | descriptive |
| — | F5 = F1 AND F3 (counts as a pass only if F1 and F3 both show a diff t ≥ 1; it has no pass authority here) | descriptive |
| — | F0 base, h5 and h3; every filter at h3 | descriptive |

NA events are excluded from both the on and the off group, and their count is reported.

**Pass (h5 only)**, all of:
1. The on-state passes the common bar.
2. On minus off > 0 with `stats.clustered_diff_t` past **Holm** across F1–F3. One-sided 5 % family: the smallest p must clear t ≥ 2.13, the next t ≥ 1.96, the last t ≥ 1.65.
3. On minus off is positive in each of 2021-22, 2023-24 and 2025-26.
4. A **permutation null**: shift each filter's date-level state series circularly along the calendar, 1,000 times (this keeps each filter's persistence), and rerun rules 1–3. The family-wise false-pass p must be < 0.05.

**Expected N** (on-state; per year 2021–2026):
- F1: 508 events on 312 dates (67/116/99/91/62/73).
- F2: 470 on 295 dates (before removing stale bars).
- F3: 389 on 237 dates (27/99/59/52/77/75).

**Needed means.** The level test alone needs on-means of about 0.80 % (F1), 0.83 % (F2) and 0.92 % (F3). The difference test pushes F1 to about 0.98 % on against 0.21 % off: the filter must roughly double the edge. Power for a true 0.5 pp lift is only about 16–27 %, so a fail is not evidence of no effect. Each on-mean is also shown beside the step-1 short build-up family average (≈ 0.33–0.62 %).

Side reports on the QIP and block-deal cells are dropped. QIP has N 20, and the block-deal "down day" cells are long-direction.

## 3. Sector rotation: stretched stock in a falling cyclical sector (user idea c)
**Hypothesis.** When a cyclical sector's other F&O members fall together, a member still well above its own 20-session average and well ahead of its sector catches down within 1–3 sessions. Direction: **short**.

S2 step 1's long build-up result (strength followed by falling, t −4 to −7 at h1–h3) was known when this direction was chosen. It supports the short; it is prior evidence, not a risk. A significantly negative result (momentum) is recorded only, not re-tested.

**Universe.** F&O names (OI > 0 on d) in the six cyclical map sectors: nifty metal, nifty auto, nifty realty, nifty oil & gas, nifty energy (power utilities in the map), nifty psu bank. **nifty infrastructure** (45 mixed names: defence, telecom, cement, cables, renewables) is a separate descriptive family.

**Features** at the close of d, on the session calendar, with all 20 closes present:
- **LOO sector:** a new function, not `s2_screen.sector_loo`.
  - The equal-weight daily return of the other members with OI > 0 on both d−1 and d.
  - Requires ≥ 3 such peers, `fill_method=None`, and demerger ex-dates set to NaN.
- SEC5 = the compounded LOO return over d−5 → d.
- DIST20 = close[d] ÷ mean(close[d−19 … d]) − 1.
- REL10 = (close[d] ÷ close[d−10] − 1) − the compounded 10-session LOO return.

**Event.**
- SEC5 ≤ −2 %, DIST20 ≥ +5 % and REL10 ≥ +8 %.
- At most the 2 highest REL10 per sector per day.
- One signal per stock every 5 sessions.
- **Entry: open of d+1**, short.

| Cell | Rule | Horizon | Role |
|---|---|---|---|
| R1 | W −2 %, R +8 %, six cyclical sectors | h1 | pass test |
| R2 | same | h3 | pass test |
| — | same, h5 | | descriptive |
| — | W −2 % R +10 %; W −3 % R +8 % (h1/h3/h5 each) | | descriptive |
| — | infrastructure family, W −2 % R +8 %, h1/h3 | | descriptive |

Extra pass conditions:
- The step-1 class for the overlap rule is **long build-up** (2 % / 5 %) on the same stock in d−10 … d. In the draft count 32–38 % of events overlap with it.
- The cell must also hold (t ≥ 2) with ADANIENT removed.

**Expected N.** W −2 % / R +8 % gave 259 events on all seven sectors (189 dates; 2023 only 17). Infrastructure held 102 of them, leaving ≈ 157 before the demerger and missing-row exclusions. The recount must show ≥ 100 events and ≥ 60 dates, or the screen is reported descriptive only.

**Power.** sd is 2.65 % at h1 and 4.78 % at h3. At N ≈ 150, t = 3 needs ≈ 0.65 % (h1) or ≈ 1.2 % (h3).

**Side reports** (N, episodes, median and hit rate only; no t and no pass flag below N 100):
- (a) sector weakness from the NSE index files via `sectors.index_closes`, for metal, auto, realty and PSU bank only. These are the sectors whose memberships match the map.
- (b) metal events with TIO=F or HG=F 5-bar return ≤ −3 %, using the last bar dated ≤ d.
- (c) oil & gas and energy events with BZ=F 5-bar return ≤ −3 %, same rule.
- (d) non-cyclical sectors as a placebo.
- The return net of sector over the same open d+1 → close d+h window, built from member opens and closes.

## 4. Gap-fill short (user idea d)
**Hypothesis.** A large gap-up that is specific to the stock, not results-driven and not market-wide partly reverts from the open over the next sessions.

**Definitions.**
- Day 0 = session i.
- G = Open_i ÷ Close_{i−1} − 1.
- M = the median of G over the day i−1 F&O universe.
- REL = G − M.

**Event:**
- **G ≥ X AND REL ≥ X** (a real gap up), with **|M| < 1 %** (no market-wide gap day), and G < 20 %.
- Close_{i−1} inside [Low_{i−1}, High_{i−1}]. No condition uses day i's high or low.
- **Not a results day.** Excluded: (i) day 0 of any results filing (`day0_index`); (ii) the first session on or after a `results_date` board-meeting date, and the next session. Rule (ii) covers the thin results months 2022-07/08/10/11 and 2025-04/05. Its removals are counted by year.
- One event per stock every 3 sessions.
- Stretched variant: Close_{i−1} ≥ 1.05 × the mean of the 20 closes i−20 … i−1. The 1.05 level was fixed from counts only, after 1.10 left 6 events in 2026.

**Entry: day 0's open**, short. Exits: close of day 0, +1, +3. The **pass horizon is h1**. h0 is an auction-price upper bound and is descriptive only.

| Cell | Rule | Horizon | Role |
|---|---|---|---|
| G1 | G ≥ 2 %, REL ≥ 2 % | h1 | pass test |
| G2 | G ≥ 3 %, REL ≥ 3 % | h1 | pass test |
| G3 | G ≥ 2 %, REL ≥ 2 %, stretched | h1 | pass test |
| — | G1–G3 at h0 and h3 | | descriptive |
| — | G ≥ 5 %, REL ≥ 5 % (≈ 130 before filters; t = 3 needs ≈ 1.0–1.5 %) at h0/h1/h3 | | descriptive |

Extra pass conditions:
- **Entry-latency haircut:** each passing cell must also pass with cost 0.35 % (0.1 % + 0.25 % adverse fill).
- The step-1 class for the overlap rule is **long build-up** (2 % / 5 %) ending on day i−1.

**Expected N.** Draft counts, before the G ≥ X and |M| < 1 % filters: REL ≥ 2 % 1,565, REL ≥ 3 % 597, stretched 369. In the REL ≥ 2 % set, 373 events (24 %) were on days with |M| ≥ 1 % and 157 had G < 2 %, so the recount will be lower. Kish effective N under date clustering was ≈ 243 for REL ≥ 2 % before the filters.

**Side reports** (descriptive):
- fill_d0 (Low_i ≤ Close_{i−1}) and fill_3 rates. The paired difference from the stock's own baseline (share of sessions in the prior 250 with |REL| < 0.5 % and Low/Open − 1 ≤ −G/(1+G); at least 60 baseline sessions) is tested by `clustered_t` on the per-event differences.
- A sector-gap split: the other members' median REL ≥ 1 % that morning vs < 1 %.
- The return net of the sector from Open_i to Close_{i+h}.

Results-day gaps are not reported here; they belong to S1 v9.

## 5. Weak results × pre-move (user idea e: "correction done the previous days, or still to come")
**Hypothesis.** A weak quarter keeps falling only when the stock had not already fallen into the filing. **Null:** no drift after the open.

**Run order.** This screen runs only after the pre-registered S1 v9 results screen (`python -m scanner.event_screens --only results`) is saved to `data/results/event_screen_results.*` and its weak side report is recorded. The disclosure stays: a smoke run on about 45 % of filings, never written down, was seen before this design, and the YoY-only definition is a fork from the S1 v9 core definition.

**Event.**
- A results filing, using the **earliest** event_time among that stock's results filings that day.
- Day 0 = that day if filed before **09:00**, which is before the pre-open order window closes; otherwise the next session.
- Universe on day i−1. One event per (stock, day 0).

**Numbers.**
- Quarter = the "period ended" date parsed from the filing subject. Events where it cannot be parsed, or where it disagrees with the financials quarter, are excluded (at least IRFC 2021-07-12, SONACOMS 2021-08-05, NBCC 2022-07-04).
- **Weak = NP YoY < −10 %.** YoY must be known with a base > 0; QoQ may be missing.
- As-filed rule: the event is excluded if the current or year-ago quarter's XBRL is dated more than 1 day after the event date. Only the date part of the filename stamp is used; the clock is 12-hour and ambiguous. Exclusions are counted.

**Pre-move.**
- k = the last session whose close is strictly before the filing: the filing day for after-close filings; the session before for pre-open and intraday filings.
- pre5 = close[k] ÷ close[k−5] − 1.
- NOT CORRECTED = pre5 ≥ 0. ALREADY CORRECTED = pre5 < 0 (the control).

**Entry: day 0's open**, short. Exits: close of day 0, +1, +3, +5.

| Cell | Rule | Horizons | Role |
|---|---|---|---|
| W1 | weak, pre5 ≥ 0 | h3 **and** h5 (both must pass) | pass test |
| — | W1 at h0, h1 | | descriptive |
| — | weak, pre5 < 0 (control) at h0/h1/h3/h5; on-minus-control `clustered_diff_t` | | descriptive, PASS blanked in code |
| — | pre10 split; the S1 v9 core definition (YoY < −10 % AND QoQ < 0) with the same split | | descriptive |

The step-1 class for the overlap rule is **short build-up** (3 % / 10 %) on day 0 or the filing day.

**Expected N.** On the 2026-10-14 snapshot, which is still being backfilled: weak 383; W1 161 (20/14/29/23/31/44 a year). The as-filed and period rules will lower this, and the frozen-file recount decides.

**Power.** At N ≈ 160, t = 3 needs ≈ +1.4 % (h3) and ≈ +1.5–1.7 % (h5), using an sd of 4.9 / 5.5 % from non-weak results events. A mean below that is a fail, whatever its sign, and is not relabelled a lead.

Prior evidence against this idea, cited:
- S1 v2's results-miss short (no drift: t −0.7 / −0.2, N 119);
- the closed "Shorting short-buildup" idea (−₹487 a trade);
- the arm A peak study (no QoQ/YoY separation).

## What follows
- **Put backtest only for passing cells**, each pre-registered on its own page with the S2 step 2 rules:
  - walk down from the strike nearest spot, 1 lot ₹600–8,000, ≥ 50 contracts, fill ≥ ₹2;
  - exits: 50 % stop, the passing horizon, T-1;
  - net of `server/charges.py` and AMFI-category slippage;
  - pass: N ≥ 100, mean > 0, t ≥ 2, positive in ≥ 5 of 6 years including 2025 and 2026.
- **§1–§3 (d+1 entry):** expiry, strike and liquidity come from day d's bhavcopy; the fill is d+1's option open + 1 tick, with d+1's premium VWAP as a side report.
- **§4–§5 (day-0 entry):** spot = the stock's Open_i (never day 0's UndrlygPric or futures close). Strike, expiry and the ≥ 50 contracts test come from day i−1's chain. The fill is day 0's `OpnPric` + 1 tick, with no VWAP or close fallback; a missing open is a counted skip. `walk_put` and `fill_at` are not reused unchanged.
- **If S2 step 2 fails** (the put cannot keep +0.62 % over 5 sessions), a stock-level pass here goes to a put backtest only if its mean is ≥ **+1.0 %**. Otherwise it is recorded and closed.
- A put pass → live paper days on the S2 page, bought at 09:15. Paper results are the only clean evidence.
- DECISIONS.md gets one row per screen with N, G, t and pass/fail, plus the running test count.

## Addendum 2026-10-18: the user's order-book and QIP ideas, added before any return is computed
The user asked (2026-10-18) to test "order book vs execution (the RVNL example)" and QIP along with screen B. No
screen-B return had been computed when this was written; only the gates' data (F&O 2021 files, NIFTY 500 calendar,
corporate actions, QIP list, the yfinance cache) had been fetched.

### 6. Order-book hype (user idea f, the RVNL example), a proxy
The true order book vs execution capacity is only in investor-presentation PDFs and cannot be tested. The testable part
of the idea is the **market's reaction to order wins**: when a stock has already run up and keeps announcing orders, the
price may be ahead of what the company can execute, and it falls back.
- **Events:** the event store's `order_win` announcements (NSE corporate announcements, 2021-12-01 → 2026-09-15; the
  store starts in Dec 2021), bucket ≠ `ignore`. Day 0 = `day0_index` (a pre-open filing trades the same day).
  Universe: OI > 0 on day i−1. One event per stock every 5 sessions (the first counts). Common rules apply
  (calendar, corporate actions, return, cost 0.1 %).
- **Features at the close of day i−1** (known before entry): DIST20 = close ÷ mean of the 20 closes − 1;
  RUN20 = close[i−1] ÷ close[i−21] − 1; N60 = the stock's order-win announcements in the 60 sessions up to and
  including this filing.
- **Entry: day 0's open**, short. Exits: close of day 0, +1, +3, +5.

| Cell | Rule | Horizons | Role |
|---|---|---|---|
| O1 | order hype: DIST20 ≥ +5 % and RUN20 ≥ +10 % | h3 **and** h5 (both must pass) | pass test |
| O2 | order pile-up: N60 ≥ 3 and DIST20 ≥ +5 % | h3 **and** h5 (both must pass) | pass test |
| — | every order win; O1 / O2 at h0, h1; order value ≥ 5 % of annual revenue (`materiality`, where known) | | descriptive |
| — | per stock for the most frequent announcers (NBCC, LT, RVNL, BEL, HAL, BHEL, SUZLON) | | descriptive |

- **Year rule for §6 only:** the store has almost no 2021 events, so the years are 2022-2026: mean positive in ≥ 4 of
  the 5, including 2025 and 2026. All other common pass rules apply; the step-1 class for the overlap rule is **long
  build-up** (2 % / 5 %) on the same stock in d−10 … d.
- **Limit:** a proxy for the user's idea, not the order book itself; NBCC alone is ~13 % of the announcements.

### 7. QIP, re-run unchanged
The closed QIP screen (`scanner.event_screens --only qip`, 4 cells, short from day 0's open) is re-run unchanged on the
freshly fetched `qip_events.csv` and reported beside screen B. With N ≈ 20 it cannot meet the common N ≥ 100 bar, so it
is descriptive only and cannot pass.

**Test accounting with the addendum:** 13 pass tests (16 pass-eligible cells); the running total of tests on the
window goes into DECISIONS.md.

## Addendum 2026-10-18 (2): the external-series check, corrected before §1 / §2 ever ran
The first run stopped §1 and §2 at the daily-vs-1h check, implemented as "the daily Close is within 0.5 % of a 1h close
on the same ET date on ≥ 95 % of days" (BZ=F 92.8 %, HG=F 82.1 %, ALI=F 42.2 %, INFY 100 %). That form tests the
price level, and a futures **settlement** is not a traded 1h close, so it fails for reasons that do not affect the
screens. What the screens depend on is the **date**: the strict lookup ("last bar dated before the entry session")
is wrong only if Yahoo's daily bars are shifted by a day. No §1 / §2 return had been computed when this was written
(the run stopped before them); the user chose to fix the check on 2026-10-18.
- **New check (replaces the old one; the run still aborts if it fails):** for BZ=F, HG=F and INFY, build a daily
  series from the 1h bars (the last 1h close of each ET date) and take its close-to-close log returns. Correlate them
  with the daily bars' returns at lag 0, −1 and +1 days, over every day the 1h data covers. **Pass:** lag-0
  correlation ≥ 0.80 and at least 0.50 above both the lag −1 and the lag +1 correlation, for each of the three.
- ALI=F is a side report only, so it is reported but not required. TIO=F has no 1h bars (as the spec already says).
- Nothing else changes: §1 and §2 run exactly as pre-registered.

## Known limits
- **Daily data.** The official open is the pre-open auction price (≈ 09:08). A live short fills later, and a put can only be bought from 09:15 and often trades later still. The official close is the 15:00–15:30 VWAP. §4 applies a latency haircut; the others do not.
- **External series.**
  - TIO=F is CME TSI iron ore. It is not the SGX FEF1! the user charts: different session and cut-off. It is thin, settlement-only (96 % zero volume) and rolls at month start.
  - ALI=F is thin COMEX aluminium, not LME.
  - BZ=F is NYMEX's Brent last-day contract, not dated or spot Brent.
  - USDINR=X is a morning snapshot.
  - Yahoo can revise history; the pinned cache is the record.
- **Timing overlap.** Commodity close-to-close bars overlap NSE session d by about 6 hours. The §1 residual removes the part explained by the child's own day-d move, not all of it. Only the ADR measure is truly after the close.
- **Membership.** Sector lists are today's (`data/sector_map.csv`) applied to all dates, which adds survivorship and selection look-ahead. The F&O panel fixes tradability, not selection. Renamed or merged names without eod2 files are missing. Today's 212-stock `financials.json` also conditions §5 on later F&O survival.
- **Power.** The year rule (5 of 6 including 2025 and 2026) rests on 12–40 events in thin years, so a real effect of the target size often fails. Per-cell minimum detectable means are stated above; a fail at N near 100–160 is underpowered, not proof of no effect.
- **No holdout.** Every year 2021–2026 has been used by earlier screens, and design choices (parent map, thresholds, sectors) were made after counts or correlations on this same window.
- **Options.** A stock-level edge of 0.6–1 % over 1–5 sessions may not survive put theta, spread and charges. Results weeks and post-gap mornings carry high IV.

## Not testable / dropped
- **Fundamentals filter** (D/E ≥ 1, equity ≤ 0, or negative TTM operating cash flow on S2 short build-ups): **dropped (fatal).**
  - The XBRL has no balance sheet before the Sep-2022 filings, and 2020–21 cash flow is missing or tagged in the wrong context.
  - Filename stamps use a 12-hour clock with no AM/PM.
  - 66 short build-up symbols have no results event, so availability times are unreliable.
  - The non-financial base cell itself fails (N 747, t 2.89, 2023 −1.09 %), and the fragile subset projects to about 40–80 events over 2023–26.
  - It could return later only as a 2023–26 report-only study using NSE broadcast timestamps. Until then the D/E and cash-flow state can be shown as information on the S2 page.
- **Order book vs execution capacity (the RVNL example):** not in XBRL, any NSE API or yfinance; it exists only in investor-presentation PDFs. Manual watchlist note only.
- **QIP:** already screened and closed (`data/results/event_screen_qip.md`: 20 F&O events, 0 of 4 cells pass). The QIP / dilution side rows are not repeated.
- **GIFT Nifty:** no history. Only the S&P 500 session before entry is used, as a proxy in §2.
- **NIFTY METAL as an overnight leader:** it trades at the same time as its stocks, so it cannot lead them overnight. It appears only in §3 side report (a).
- **Dropped from the drafts:**
  - §1: ALI=F from the pass cells; TIO=F from k=1; z ≤ −2.0 and h1 as pass legs.
  - §2: h3 as a pass leg; F4 and F5 as pass cells; the QIP and block-deal side reports.
  - §3: W −3 % / R +10 %; infrastructure in the primary.
  - §4: REL ≥ 5 % as a pass row; h0 and h3 as pass legs; the results-day side report.
  - §5: pre10 and the control cells as pass cells.
  - All of these are descriptive or removed, as listed in each section.