# S1 fade · live research checkpoint, 29 Oct 2026 (18 measured v12 trades, not 30)

Research only. **No rule, sizing, order or model changed.** v12 stays the control. Every number below is from the
stored records; nothing was reconstructed or filled in. Tables: `S1_fade_checkpoint_2026-10-29_tables.md`; per-trade
file: `S1_fade_checkpoint_2026-10-29_trades.csv`; code: `scanner/fade_checkpoint_live.py` (read-only).

Status words: **Observed** (directly in the records) · **Suggestive** (a pattern, uncertain) · **Unproven** (too little
evidence) · **Not testable** (data missing).

## 0. Headline
1. **The 30-trade target is not met.** There are **18** measured v12 fade trades (27–29 Oct, 3 trading days). Counting
   every measured closed trade in all arms gives 28 (18 fade + 10 Arm A/B, which are a different strategy). Every
   analysis below uses n = 18 unless stated. Observed.
2. **The records are reliable.** All 18 pass every ledger, order, time, quote and backup check (§1). Observed.
3. **Live results are far worse than the backtest:** −₹29,471 net, 4 wins of 18, mean −24.1 % a trade, against the
   339-trade backtest's +2.86 % and 55 % wins. **14 of 18 hit the stop** (backtest 40 %). Observed.
4. **The main mechanism is the first minute.** Live buys at 09:15:01–09:15:06; the stop checks only from 09:16. In
   9 of 14 stopped trades the bid was already below the −20 % stop level before 09:16, so the sale came at the first
   check, a median 16.8 % below the stop level (worst 45.8 %). The backtest that justified v12 bought at the
   **09:16 candle open** with the stop from 09:17, so it never held this minute. Observed for the mechanism; its
   size beyond these 3 days is Suggestive.
5. Peak capture is **not** the problem: 13 of 18 trades never had a sellable peak that paid. Recovery after the stop
   is much rarer than the candle study suggested. ML is **not** justified. Details below.

## 1. Dataset and audit

### Sources (all copied 29 Oct 2026 19:34 IST, after the close)
| File | From | SHA-256 (first 16) |
|---|---|---|
| `paper_ledger.json` (saved 2026-10-29 15:29:58 IST) | VM `fo-scanner` `~/fo_scanner/data/` | 9aef3cd1f9f140e1 |
| `paper_orders.jsonl` | VM | de71b5c404981bac |
| `observations/2026-10-26.jsonl` | VM | 923cf78a408ccf62 |
| `observations/2026-10-27.jsonl` | VM | 0c270bfc09741824 |
| `observations/2026-10-28.jsonl` | VM | d809a1a4ef179f63 |
| `observations/2026-10-29.jsonl` | VM | ffb7170007c25292 |

**Backup check:** the GitHub `paper-state` branch (commit `c3b25bd8`) has a **byte-identical** ledger and orders file,
and byte-identical observation files for 26, 27 and 28 Oct. The **29 Oct observation file was not yet on the
branch** at the time of the audit (it is pushed after the day; re-check). Code run by the VM each day (its git
reflog): 27 Oct `25669145`, 28 Oct `32595932`, 29 Oct `a2a6d2da`. Analysis code: `scanner/fade_checkpoint_live.py`
on repo commit after `de6e5ef0` (this checkpoint's commit).

### Counts
| Item | Count |
|---|---|
| Closed positions in the ledger (all arms) / open | 44 / 21 |
| Unique ids / duplicate ids / duplicate (contract, open time) | 65 / 0 / 0 |
| Fade closed: v10 / v11 / v12 | 10 / 2 / 19 |
| Fade open | 0 |
| **v12 measured** (has `peak_capture` and `entry_quote`) | **18** |
| v12 not measured | 1: ADANIENSOL 23 Oct (before the measurement fields existed) |
| v12 signals 27–29 Oct / bought / refused | 19 / 18 / 1 (MAHABANK 27 Oct: one lot never fits the price limits) |

Because 18 of 19 signals were bought, the measured set is not a selected subset of the signals.

### Checks (per trade; full table in the tables file)
| Check | Result |
|---|---|
| Times in IST (+05:30); placed ≤ filled; opened < closed | 18 / 18 pass |
| gross = (exit − entry) × qty; net = gross − charges; charges = entry + exit legs; buy value = entry × qty; return % = net / buy value | 18 / 18 pass |
| Fill levels match the order records (qty and price) | 18 / 18 pass |
| Held observation rows after the sale / post-exit rows before the sale / post-exit rows past 60 min | 0 / 0 / 0 |
| Held rows with no bid / no ask / bid > ask; post-exit rows with no bid | 0 / 0 / 0 / 0 |
| Ledger held peak and low are a held row's bid and bound every later held row | 18 / 18 |
| Repo validator `scanner/fade_live_validate.py` (17 checks a trade) | 18 / 18, no FAIL or WAIT |
| Post-exit coverage | 59.2–60.0 min on all 18; longest gap 10–100 s |
| Bid size at the peak ≥ the lot | 18 / 18 |

**Held-period coverage.** The observation file writes a row only when the top of the book changes, so it has fewer
rows than the ledger's quote count (`rows / quotes` column). On **27 Oct** only the 30-second feed poll ran (no
1-second exit check yet): each trade has the entry quote plus 1 changed book in ~60 s, and the ledger's longest gap
between quotes was 5.1 s. From **28 Oct** the 1-second check adds rows; the longest held gap is 2–18.5 s. A peak
inside a gap could be missed; this matters most on 27 Oct.

**Stale entry books (27 Oct).** 5 of the 6 entries on 27 Oct (RECLTD, TATACONSUM, APLAPOLLO, SONACOMS, PAYTM) were
priced on a book whose last trade was the **previous day** (last-trade age ~63,300 s; `stale_ltt` = True). Example:
TATACONSUM bought at ₹12.10; 15 s later the live book was ₹5.25 / ₹6.50. The fix that waits for today's first trade
(`32595932`) was live from 28 Oct; no stale entry since. These 5 trades are **kept** (they are real v12 trades under the
rule as it ran), and results are also shown without 27 Oct.

**Other notes, not exclusions.** (a) Fills are the paper real-order simulation (filled from the next quote's book,
no market impact): the fill difference against the instant decision price was −₹1,325 in total (fills helped).
(b) `volume_at_entry` on a stale book is the previous day's volume. (c) NAUKRI's entry quote was ₹5.00 / ₹9.05
(57.7 % of the midpoint); it was bought at ₹9.05 and the book 10 s later was ₹7.25 / ₹7.70.

**Exclusions: none.** ADANIENSOL is outside the measured set only because it has no measurement fields; it is shown as
a sensitivity line where it matters (shadows).

## 2. Performance (18 measured trades; 1 lot each, actual qty, actual charges)
Return % is **on the premium paid** (buy value) for each trade. The paper account (₹5,00,000) is shared with Arms A
and B and has no fade allocation, so **no return on portfolio capital is computed**. The 18 trades put ₹1,19,229 of
premium to work in total (5–7 positions a day, ₹40k–47k of premium per day).

| Trades | Wins / losses / even | Win % | Mean / median net % | Total net | Charges | Avg win / loss | Profit factor | Max drawdown (realised) |
|---|---|---|---|---|---|---|---|---|
| 18 | 4 / 14 / 0 | 22.2 % | −24.1 % / −24.6 % | **−₹29,471** | ₹1,078 | +₹612 / −₹2,280 | 0.08 (4 wins: not stable) | −₹29,471 (the curve never rose above zero) |

| Cut | n | Wins | Stops | Mean net % | Total |
|---|---|---|---|---|---|
| Exit: stop | 14 | 0 | 14 | −33.7 | −₹31,921 |
| Exit: trail | 4 | 4 | 0 | +9.8 | +₹2,450 |
| Exit: 15:20 | 0 | – | – | – | – |
| CE / PE | 4 / 14 | 1 / 3 | 3 / 11 | −19.6 / −25.4 | −₹5,572 / −₹23,899 |
| Premium < ₹5 / ₹5–15 / ≥ ₹15 | 3 / 5 / 10 | 0 / 1 / 3 | 3 / 4 / 7 | −34.3 / −35.2 / −15.4 | −₹7,107 / −₹12,642 / −₹9,722 |
| 27 Oct / 28 Oct / 29 Oct | 6 / 5 / 7 | 0 / 2 / 2 | 6 / 3 / 5 | −41.6 / −13.8 / −16.4 | −₹17,190 / −₹4,030 / −₹8,251 |
| **Without 27 Oct** (fresh books only) | 12 | 4 | 8 | −15.3 | −₹12,281 |

Each contract traded once, so "by contract" is the trade table. With 3 days, day and contract effects can't be told
apart. **Backtest comparison (separate datasets):** 339 trades, v12 +2.86 %, win 55.2 %, stop 136 (40 %, mean −24.1 %),
trail 203 (60 %, mean +21.0 %). Live stops are deeper (−33.7 %) and live trail wins smaller (+9.8 %).

## 3. Peak capture (held bids only; `server/peak.py` definitions)
Peak = the highest observed best bid while held (from the first quote after the entry to the exit decision). Net at
the peak = selling the whole lot at that bid, with the trade's charges: **an estimate, not a fill**. The bid size at
the peak covered the lot in 18 / 18, but deeper levels and the time to sell are unknown.

| | Count |
|---|---|
| Peak net > 0 (a sellable peak that paid) | **5** (MAZDOCK, BAJAJ-AUTO, TVSMOTOR, NAUKRI, MARUTI) |
| Peak was the first quote after the entry (never rose above it) | 10 |
| Peak before the exit / within 5 s of the exit | 5 / 3 |
| Capture defined (peak net > 0) | 5: 93 %, 92 %, 66 %, 65 %, **−276 %** (MARUTI) |
| Sum of positive peak net / realised on those 5 | ₹3,651 / ₹741 |
| Sum of "giveback" (peak net − realised), all 18 | ₹26,676, of which ₹23,765 is on the 13 trades whose peak never paid |

- The 4 trail exits captured 65–93 % of their peak net (₹2,450 of ₹3,033). The 2 % gap is not the problem.
- MARUTI rose to +9.2 % (₹162.20 at 09:17:32), 0.8 % short of the +10 % trail switch, then hit the stop. It is the one
  large giveback on a paying peak.
- **Most of the "giveback" is not missed profit:** 10 trades never bid above the first quote, which was already below
  the price paid (the spread). Capture is N/A there, by definition.
- Data gaps: 27 Oct polls were ~5 s apart, so a short spike could be missed. No trade has a peak in a gap above 18.5 s.

**Status:** peak capture is a minor issue in this sample. Observed.

## 4. Entry quality (features known at or before the buy)
Outcome = net % and stop/win. Medians split each feature; ρ = Spearman rank correlation with net %. **18 trades on
3 days.** 27 Oct differs from the other days on several features at once (stale book, last-trade age, 27 days to
expiry, previous-day volume, earliest entries, all 6 stopped), so all-18 correlations mostly measure "27 Oct". The
right-hand columns use 28–29 Oct only.

| Feature | n (missing) | All 18: ρ / below vs above median, mean net % | 28–29 Oct only (n 12): ρ / below vs above | Reading |
|---|---|---|---|---|
| Stale last trade (flag) | 18 (0) | stale 5: all stopped, −45.4 % · fresh 13: −15.9 % | none stale | Confounded with 27 Oct; fixed from 28 Oct. Suggestive. |
| Last-trade age (s) | 18 (0) | −0.55 / −15.4 vs −32.8 | 0.00 / −13.7 vs −16.9 | No link once 27 Oct is out. |
| Entry delay after 09:15:00 (s) | 18 (0) | +0.58 / −32.8 vs −15.3 | +0.18 / −21.9 vs −8.7 | Later entries did a bit better; small n. Suggestive. |
| Spread, ₹ | 18 (0) | +0.57 | +0.38 / −15.4 vs −15.3 | No split difference. Unproven. |
| Spread, % of midpoint | 18 (0) | +0.04 / −25.9 vs −22.3 | −0.03 / −16.0 vs −14.6 | No link. |
| Entry bid ÷ price paid | 18 (0) | −0.05 | +0.01 | No link. Bid at or below the stop at entry: 2 (WAAREEENER stopped −21 %; NAUKRI trail +8 %). |
| Entry premium | 18 (0) | +0.56 / −34.9 vs −13.3 | +0.40 / −24.7 vs −5.9 | Same direction as the backtest's ≥ ₹15 cut, which was not robust there. Unproven. |
| Strike distance, OTM % | 18 (0) | −0.14 / −24.9 vs −23.2 | +0.15 / −22.0 vs −8.6 | Unproven (backtest: no link). |
| Days to expiry | 18 (0) | −0.55 | 25–26 days only | Not testable: one expiry month. |
| Option type | 18 (0) | CE −19.6 (4) · PE −25.4 (14) | CE −11.9 (3) · PE −16.5 (9) | Unproven. |
| Volume at entry | 18 (0) | −0.67 | −0.32 / −13.5 vs −17.1 | Previous-day volume on stale books; unproven. |
| Open interest at entry | 18 (0) | −0.36 | **−0.63** / −2.8 (4 of 6 won) vs −27.8 (0 of 6) | The strongest split in 28–29 Oct, but 1 of 10 features on 12 trades. Unproven; worth watching. |
| Filing-day move vs market (PE only) | 4 (14) | – | – | Not testable (n 4). |
| Net profit YoY % | 18 (0) | +0.11 | +0.04 / −21.9 vs −8.8 | No link. |
| Ask size ≥ lot | 18 (0) | all True | – | Not testable (no variation). |
| Stock move before entry (opening gap) | 0 | – | – | Not testable: no previous close stored with the trade. |

No feature is shown to predict outcomes. With ~15 features and 12–18 trades, one ρ near ±0.6 is expected by chance.
**Failed hypothesis:** "wide entry spreads (vs the 2 % trail gap) cause the losses". The spread did not separate
winners from losers on either cut.

## 5. Early behaviour and recovery (observed bids)
"Held" = rows while the position was open; "path" adds post-exit rows from the same contract (hypothetical, never
P&L). All dips are versus the price paid (the ask), so a dip includes the spread.

| | Live (bids, n 17 with a first-minute row) | Backtest (339, 1-minute candles; ESTIMATES) |
|---|---|---|
| Reference start | 09:15:01–09:17:51 (the actual buy) | 09:16 candle open |
| Median max dip, first 1 / 3 / 5 min (path) | −26.3 % / −29.6 % / −34.3 % | −4.6 % / −9.9 % / −12.6 % |
| Max dip ≤ −20 % in the first minute | **9 of 17** | 17 % |

**The stop (14 stopped trades):**
| | Count |
|---|---|
| Bid at or below the stop level before 09:16, when the stop was not yet checking | **9** |
| Sold at the first stop check (closed ≤ 09:16:30) | 11 |
| Exit vs the stop level: median / worst | −16.8 % / −45.8 % |
| Back to the entry price within 60 min after the sale (post-exit rows) | 3: PAYTM 13.2 min, MARUTI 17.1, HEROMOTOCO 7.9 |
| Back to entry on the exit day by any record (60-min rows or the server's same-day after-peak) | 4 (adds WAAREEENER, 13:08) |
| 15:20 bid above the sale price / above entry | 4 / 2 (PAYTM, HEROMOTOCO) |
| Post-exit low within 60 min below the sale price | 13 |

- **Stopped trades mostly kept falling.** On 10 of 14 the 15:20 bid was below the stop sale. Holding the 14 to 15:20
  (v10 shadow) would have lost ₹38,697 instead of ₹31,921.
- **Recovery after the stop is rarer live:** 4 of 14 (29 %) touched entry again on the day vs 56 % in the candle study;
  2 of 14 (14 %) were above entry at 15:20 vs 24 %. The datasets differ (bids vs candle highs; 09:15 vs 09:16
  start), so this is a comparison, not a test. Suggestive.
- Held recoveries: all 4 trail trades and MARUTI went back to the price paid while held, at 0.4–3.8 min.
- Coverage limits: post-exit rows cover 60 min. After that only the extremes are kept (`after`), and they run into
  later days without a per-day split (PAYTM's and BAJAJ-AUTO's after-peaks are on the next day). Same-day recovery after
  60 min is therefore known only when the after-peak is dated the same day.

## 6. v12 vs its shadows (same entry, same qty; shadows are hypothetical, no orders)
The shadows are tracked on the same live bids after a real trail sale (v11: its stop, else 15:20; v10: the 15:20 bid;
5 % trail: the 5 % gap). They share every entry with the real trade, so they are **not additional trades**. Charges
are the same schedule (`server/charges.py`).

| Set | Rule | Wins | Total net | Mean net % | v12 minus it, mean points (t) | Trades that differ |
|---|---|---|---|---|---|---|
| 18 measured | **v12 (real)** | 4 | −₹29,471 | −24.1 | – | – |
| 18 measured | v11 shadow | 2 | −₹33,483 | −27.5 | +3.5 (1.27) | 4 |
| 18 measured | v10 shadow | 5 | −₹41,236 | −33.8 | +9.7 (1.00) | 18 |
| 18 measured | 5 % trail shadow | 4 | −₹30,775 | −25.2 | +1.1 (2.08) | 4 |
| 19 incl. ADANIENSOL | v12 (real) | 5 | −₹28,457 | −22.1 | – | – |
| 19 incl. ADANIENSOL | v11 shadow | 3 | −₹6,094 | −5.9 | −16.2 (−0.82) | 5 |
| 19 incl. ADANIENSOL | v10 shadow | 6 | −₹13,847 | −11.8 | −10.3 (−0.47) | 19 |

- On the 18 measured trades v12 is ahead of each shadow. **Adding one trade flips it:** ADANIENSOL (23 Oct, bought on
  a stale book at ₹10.55) was trail-sold for +₹1,014, while held to 15:20 it was +₹27,389 (+385 %). One outlier
  decides the total.
- v12 vs v11 differs on only 4–5 trades (the trail exits); the paired t is far from conclusive either way.
- The v12 review rule (`strategies/S1_v12_fade_trail2.md`) is due at **30 closed v12 trades**: 19 now. **Not due.**

**Status:** v12 is not shown to outperform its shadows, nor to underperform them. Unproven.

## 7. Is ML justified now? No.
| Factor | Value |
|---|---|
| Usable labelled trades | 18 (4 wins; 14 stops): strong imbalance |
| Candidate entry features | ~15, several redundant (premium, OI, volume, spread ₹) |
| Independence | 3 trading days, 5–7 trades a day sharing the same market open; 2 entry regimes (stale books 27 Oct, fresh after) |
| Leakage risks | volume/LTT on stale books carry the previous day; anything after 09:15 (dips, stock moves) is post-entry |
| Chronological validation | train on 27–28 Oct (11) → test 29 Oct (7): the test set is one day |
| Baseline | a single descriptive cut (e.g. stop timing) explains more than any feature fit could be validated on |

A chronological split cannot be both large enough to fit and large enough to test. A model here would learn
"27 Oct". **Needed first:** ≥ 100 trades over ≥ 30 distinct trading days under one fixed entry rule, with the
opening gap and the previous close stored at entry. Any ML must then beat a simple pre-registered rule on a later,
untouched block. (The backtest ML attempt, `S1_fade_ml.xlsx`, uses candle proxies and is not comparable.)

## 8. Code and specification findings (documented, **not** changed)
1. **Entry minute vs the evidence base.** The live fade buys from 09:15 (v10 spec: "from 09:15, at the live ask") with
   the stop from 09:16. The realistic backtest that selected v12 bought at the 09:16 open with the stop from 09:17.
   Live therefore holds an unprotected first minute that the backtest never held: 9 of 14 stops were breached in it.
   This is a spec/backtest mismatch, not a coding error. **Options for the user (each a rule change, needs a
   DECISIONS entry):** (a) buy from 09:16:00 to match the backtest; (b) check the stop from the first quote after the
   buy; (c) keep as is and record more. A pre-registered paired comparison on the entry probe and the 1-second candles
   (both already recorded, `data/entry_probe/`, `data/candles_1s/`) can measure (a) vs live without trading.
2. **Observation writer de-duplication.** `server/peak.py` `ObsWriter.add` skips a book identical to the last written
   row, so a first poll equal to the entry quote is not written (the ledger peak then shows only on the entry-quote
   row). Harmless, but a measurement-only fix would always write the first held quote.
3. **After-exit extremes span days.** `closed["after"]` keeps one peak/low until `t2_date`, not per day. A per-day
   (or exit-day-only) extreme would make same-day recovery measurable after the 60-minute rows. Measurement-only.
4. **The checkpoint script's default source** (`scanner/fade_live_checkpoint.py`, GitHub branch) lacks the current
   day's observations until the backup runs; its "30" counts only fade trades with `peak_capture`. No change needed;
   noted so the count is not misread.
5. **Backup timing:** the 29 Oct observation file was not on `paper-state` when audited. Re-check tomorrow.

## 9. Comparison with earlier findings
| Earlier finding (backtest, candle estimates) | Live (18 trades, bids) | Agreement |
|---|---|---|
| Losers mostly never rose +2 %; weakness is entry/direction, not exit | 13 of 18 never had a paying peak; trail exits captured 65–93 % | Agrees |
| ≥ ₹15 premium edge not robust | ≥ ₹15 −15.4 % vs < ₹15 −35 % (n 10 vs 8) | Same direction, unproven |
| Strike distance: no link | no link | Agrees |
| After the stop, 56 % touch entry later, 24 % close above | 29 % / 14 % | Live is weaker; different data |
| First-minute dip median −4.6 % (from 09:16) | −26.3 % (from 09:15) | Different start minute: the key difference |
| ADANIENSOL bought on a stale book (23 Oct) | 5 more on 27 Oct; fixed 28 Oct | Confirmed, fixed |

## 10. Decision table
| Research question | Evidence | Confidence | Recommended next step |
|---|---|---|---|
| Is the measurement data reliable? | 18/18 pass all ledger, order, time, quote and separation checks; backup identical (29 Oct obs pending). 27 Oct coverage coarser (5 s polls). | **Observed**, high | Confirm the 29 Oct backup; optional measurement-only fixes §8.2–8.3. |
| Are entries associated with weak outcomes? | The stale-book day (27 Oct) lost on all 6; within 28–29 Oct no feature separates outcomes except an unconfirmed OI split (ρ −0.63, n 12). The strongest link is **entry timing**: the unprotected 09:15 minute. | Stale books: **Observed** (fixed). Timing: **Suggestive**. Features: **Unproven**. | Measure 09:15-live vs a 09:16 buy on the same signals (entry probe + 1-s candles), pre-registered. |
| Is peak capture a significant issue? | 5 paying peaks; trail exits kept 65–93 %; most giveback is the stop on trades that never paid. | **Observed**: not significant here | No exit change; keep measuring. |
| Do stopped trades recover after exit? | 4 of 14 touched entry the same day, 2 above entry at 15:20; 10 of 14 lower at 15:20 than the sale; holding all would have lost ₹6,776 more. | **Suggestive** (n 14; 60-min rows + extremes only) | Keep the 60-min record; add per-day after-extremes (measurement only). |
| Is v12 outperforming its shadows in this sample? | Ahead on 18 (+3.5 pts vs v11, t 1.27); behind on 19 because of one trade (ADANIENSOL +₹27k held). | **Unproven** | Review at 30 closed v12 trades, as the spec says; report with and without the largest trade. |
| Is ML justified now? | 18 trades, 4 wins, 3 days, 2 entry regimes, ~15 features. | **Not testable** now | ≥ 100 trades over ≥ 30 days on one entry rule; store opening gap / previous close at entry. |

## 11. Three most valuable next research steps
1. **Quantify the first-minute effect without trading.** For every signal from 28 Oct, compare the live 09:15 buy with
   a hypothetical 09:16:00 buy at the recorded ask (entry probe / 1-second candles), with the v12 exit on recorded
   bids. Pre-register the definitions before running it. This tests the single biggest observed gap between live and
   backtest.
2. **Keep collecting to 30, then ~100, measured v12 trades under one fixed entry rule** (the rule from 28 Oct). Report
   with and without 27 Oct and with and without the single largest trade.
3. **Store the stock's previous close and opening gap at entry** (measurement only), so the backtest's "stock runs on
   with the headline" cause can be checked with entry-time data. Then re-run §4 at 30 trades.

## Unresolved questions
- Whether the 27 Oct and 29 Oct opens were typical (3 days; market context not analysed).
- The entry probe's A / B / C verdicts (`data/entry_probe/`) were not analysed here.
- Whether displayed bid size at the peak would have filled in practice (depth beyond level 1 unknown).
