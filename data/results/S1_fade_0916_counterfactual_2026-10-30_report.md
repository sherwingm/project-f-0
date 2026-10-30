# S1 fade · 09:15 vs 09:16 entry: counterfactual results (30 Oct 2026)

Read-only research. **No rule, parameter, order, sizing or deployment change.** v12 stays live as it is.
Method (written and committed before any result): `strategies/S1_fade_0916_entry_counterfactual.md` (`9a5bfa43`, with its
"Changes" section). Tables: `S1_fade_0916_counterfactual_2026-10-30.md`. Per trade: `..._trades.csv`. Code:
`scanner/fade_entry_0916_cf.py`.

**Observed vs simulated.** The 09:15 results are the **booked** trades. Every 09:16 entry price is an **observed best
ask** (level-1 size covered the lot in every case), and every 09:16 exit is a **simulated sale at an observed bid**.
None of them is a fill, and none is guaranteed to have been executable.

## 1. Inputs
| File | SHA-256 (first 16) |
|---|---|
| `paper_ledger.json` (VM, saved 2026-10-29 15:29:58) | 9aef3cd1f9f140e1 |
| `observations/2026-10-27.jsonl` / `-28` / `-29` (VM; 29 Oct now identical on `paper-state`) | 0c270bfc09741824 / d809a1a4ef179f63 / ffb7170007c25292 |
| `entry_probe/2026-10-23.json` / `-27` / `-28` / `-29` (`paper-state`) | 5994c4173131f710 / dfa66c7e6ca649dc / 043398a547b7f7bd / 0d66f6f89f8d826a |

## 2. Which signals could be compared
| | Count | Notes |
|---|---|---|
| v12 fade signals bought | 19 | ADANIENSOL (23 Oct) + 18 on 27-29 Oct |
| Already bought at or after 09:16:00 (**unchanged**: the 09:16 rule does not bind) | 4 | MANKIND, MARUTI, TVSMOTOR, CUB |
| **Changed** (09:15 → 09:16 entry built) | 13 | |
| **Unavailable** | 2 | ADANIENSOL: at 09:16 the spread was over 10 % and then one lot cost more than ₹8,000 until 09:20. BANDHANBNK: the ask was below ₹2 from 09:16 to 09:20. In both cases the walk would have looked for another strike, which is not reconstructed. |
| 09:16 exit decided by recorded rows / by the 15:20 extremes test / unresolved | 13 / 0 / 0 | |
| 09:16 entry row from: probe (1 s) / server's 1-s exit check / 30-60 s post-exit poll | 2 / 7 / 4 | the 4 coarse ones are all on 27 Oct |
| The live walk at 09:16 picks **the same strike** / a different strike / unknown | **5** / 5 / 3 | a different strike means the same-contract counterfactual is not what live would have bought |

**Engine check.** Replaying the actual 09:15 entries through the same exit engine reproduces every booked exit reason
(17 / 17). The total is −₹28,342 against −₹27,429 booked: the ₹913 gap is the fill model (the paper real-order fills vs
the observed bid). Comparing 09:16 with the **replay** removes that execution difference.

## 3. Results
Paired trades only (unchanged trades count as identical pairs). Return % is on each entry's own premium paid.

| Group | n pairs | Method | Wins | Total net | Mean / median net % | Avg win / loss | Stop / trail | Max DD |
|---|---|---|---|---|---|---|---|---|
| **27-29 Oct** | 17 | 09:15 booked | 4 | −₹27,429 | −24.0 / −23.0 | ₹612 / −₹2,298 | 13 / 4 | −₹27,429 |
| | | 09:15 replayed | 4 | −₹28,342 | −24.8 / −22.5 | ₹397 / −₹2,302 | 13 / 4 | −₹28,342 |
| | | **09:16 simulated** | 5 | **−₹12,231** | −14.2 / −22.0 | ₹541 / −₹1,245 | 12 / 5 | −₹12,231 |
| **28-29 Oct** (fresh books) | 11 | 09:15 booked | 4 | −₹10,239 | −14.4 / −21.5 | ₹612 / −₹1,813 | 7 / 4 | −₹10,239 |
| | | 09:15 replayed | 4 | −₹11,152 | −15.6 / −21.9 | ₹397 / −₹1,820 | 7 / 4 | −₹11,152 |
| | | **09:16 simulated** | 4 | **−₹7,288** | −11.9 / −21.2 | ₹537 / −₹1,348 | 7 / 4 | −₹7,288 |
| **27 Oct** (previous-day books) | 6 | 09:15 booked | 0 | −₹17,190 | −41.6 / −39.7 | – / −₹2,865 | 6 / 0 | −₹17,190 |
| | | **09:16 simulated** | 1 | **−₹4,943** | −18.5 / −22.5 | ₹556 / −₹1,100 | 5 / 1 | −₹4,943 |

| Group | 09:16 − 09:15 booked | Mean diff, net % pts (paired t, scale only) | Better / worse / same | 09:16 − 09:15 replayed |
|---|---|---|---|---|
| 27-29 Oct | +₹15,198 | +9.7 (2.66) | 10 / 3 / 4 | +₹16,111 |
| 28-29 Oct | +₹2,951 | +2.4 (1.21) | 5 / 3 / 3 | +₹3,864 |
| 27 Oct | +₹12,247 | +23.1 (3.24) | 5 / 0 / 1 | +₹12,247 |

**Entry price and first minute (changed trades).** The 09:16 ask averaged **21.9 % below** the 09:15 price (27 Oct
−34.8 %, 28-29 Oct −13.8 %). The median lowest bid in the first 60 s after entry was **−35.8 %** after a 09:15 buy
and **−11.7 %** after a 09:16 buy (28-29 Oct: −25.2 % vs −9.8 %). Median exit about 1.5 min later than the booked exit.

**Per trade (changed only; full table in the tables file):**
| Day | Symbol | 09:15 buy → sell (booked) | 09:16 buy → sell (simulated) | Net 09:15 → 09:16 | Diff | Walk same? |
|---|---|---|---|---|---|---|
| 27 | RECLTD CE | 4.90 09:15:01 → 2.85 stop 09:16:01 | 3.00 09:16:00 → 2.15 stop 09:17:29 | −3,288 → −1,395 | +1,893 | no (305) |
| 27 | TATACONSUM PE | 12.10 → 5.25 stop | 6.10 09:16:12 → 4.70 stop 09:22:12 | −3,823 → −824 | +3,000 | no (910) |
| 27 | APLAPOLLO PE | 16.70 → 11.05 stop | 13.70 09:18:11 → 10.80 stop 09:19:55 | −2,035 → −1,072 | +963 | unknown |
| 27 | SONACOMS PE | 6.50 → 2.95 stop | 3.30 09:16:27 → 2.60 stop 09:19:05 | −4,406 → −913 | +3,494 | unknown |
| 27 | PAYTM PE | 8.80 → 5.65 stop | 7.20 09:17:09 → 8.05 trail 09:22:02 | −2,342 → +556 | +2,897 | unknown |
| 28 | WAAREEENER CE | 31.85 → 25.35 stop | 26.75 09:16:00 → 21.40 stop 09:33:45 | −1,196 → −993 | +203 | no (2320) |
| 28 | LT PE | 30.75 → 18.45 stop | 19.10 09:16:00 → 15.20 stop 09:17:09 | −2,208 → −736 | +1,472 | no (3700) |
| 28 | BAJAJ-AUTO PE | 79.85 → 86.85 trail | 83.00 09:16:00 → 89.85 trail 09:17:00 | +463 → +451 | −12 | yes |
| 28 | MAZDOCK CE | 31.85 → 34.90 trail | 31.85 09:16:00 → 33.85 trail 09:16:13 | +621 → +385 | −236 | yes |
| 29 | JSWENERGY PE | 6.60 → 4.35 stop | 4.55 09:16:00 → 3.55 stop 09:17:53 | −2,478 → −1,132 | +1,346 | no (470) |
| 29 | ADANIPORTS PE | 16.90 → 13.60 stop | 15.75 09:16:00 → 12.55 stop 09:17:13 | −1,631 → −1,582 | +49 | yes |
| 29 | NAUKRI PE | 9.05 → 9.90 trail | 7.85 09:16:00 → 8.60 trail 09:16:40 | +408 → +354 | −53 | yes |
| 29 | HEROMOTOCO PE | 51.00 → 40.15 stop | 46.35 09:16:00 → 36.70 stop 09:17:29 | −1,690 → −1,508 | +181 | yes |

## 4. Robustness
| Check | Pairs | 09:16 − 09:15 booked | Mean pts (t) | Better / worse / same |
|---|---|---|---|---|
| 27-29 Oct, all | 17 | +₹15,198 | +9.7 (2.66) | 10 / 3 / 4 |
| … without 27 Oct (= 28-29 Oct) | 11 | +₹2,951 | +2.4 (1.21) | 5 / 3 / 3 |
| 27-29 Oct without the largest (SONACOMS) | 16 | +₹11,704 | +8.3 (2.32) | 9 / 3 / 4 |
| 28-29 Oct without the largest (LT) | 10 | +₹1,478 | +0.8 (0.62) | 4 / 3 / 3 |
| Comparable quotes, as committed (probe entry row), 28-29 Oct | 4 (1 changed) | −₹236 | −0.8 | 0 / 1 / 3 |
| Comparable incl. 1-s exit-check rows (post hoc), 28-29 Oct | 11 | +₹2,951 | +2.4 (1.21) | 5 / 3 / 3 |
| **Walk would pick the same strike at 09:16** (5, all 28-29 Oct) | 5 | **−₹71** | – | 2 / 3 / 0 |
| Standing book at 09:16:00 instead of the first row at or after it (8 probe-polled) | 8 | BAJAJ-AUTO flips +₹451 → −₹1,436; the rest move by < ₹30 | – | – |

## 5. What this says, and how sure it is
1. **27 Oct is a different problem.** On the previous-day-book day, waiting to 09:16 would have cut the loss from
   −₹17,190 to −₹4,943 (all 5 changed trades better). That mostly repeats what `32595932` already fixed (no buy on
   yesterday's book). Its 09:16 entries also rest on coarse rows (4 of 5 from 30-60 s post-exit polls) and on
   contracts the walk would not, or might not, have chosen. **Observed, but not evidence about normal timing.**
2. **On normal days (28-29 Oct) the gain is small and fragile:** +₹2,951 on 11 pairs (+2.4 points a trade, t 1.2).
   Without LT: +₹1,478 (t 0.6). The number of stops is unchanged (7 vs 7) and wins are unchanged (4 vs 4). A 09:16 buy
   did not avoid the stops: of the 5 changed trades that stopped, 4 stopped again within 2 minutes of the 09:16 buy
   (WAAREEENER after 18 minutes). **Unproven.**
3. **Most of the rupee gain is a smaller stake, not a better trade.** Buying the same contract after a fall of up to 50 %
   costs fewer rupees, so the same percentage loss costs less. The live walk would instead have moved to a nearer
   (pricier) strike in 5 of 13 cases, and on the 5 trades where it would have kept the same strike the 09:16 entry
   changed nothing (−₹71). **Suggestive.**
4. **Winners did slightly worse at 09:16** (MAZDOCK, NAUKRI, BAJAJ-AUTO: −₹301 together): the first-minute move that
   hurts losers is part of what the winners captured. **Observed, n 3.**
5. **Sensitivity.** One 1-second shift in the entry row turns BAJAJ-AUTO from +₹451 to −₹1,436. The committed
   "comparable" set has 1 changed trade. The result therefore depends on execution and recording details at the
   ±₹1,500 level, which is the size of the 28-29 Oct effect itself.

## 6. Recommendation (not implemented; waiting for approval)
**The sample is too small to decide, and the evidence does not by itself support changing the entry time.** It does
support **continued, cheap investigation**, because the first-minute fall is large and real (median lowest bid −25 %
in the first 60 s on fresh-book days). The next steps, all read-only or measurement-only:
1. **Re-run this script unchanged at 30 v12 trades on fresh-book days** (`python -m scanner.fade_entry_0916_cf <ledger>
   <observations> <probe dir> <stem>`). Decision gate to pre-register before then: a 09:16 effect worth considering
   should show more stops avoided (not only smaller stakes) and hold without the largest trade.
2. **Measure the walk's own 09:16 choice** instead of the same contract. This needs the probe to cover the strike the
   walk would buy at 09:16, beyond the first 8 (measurement only: widen `PROBE_STRIKES` or record the walk's choice
   each second 09:15-09:17). It needs your approval because it touches server code.
3. Report results in **net % of premium** first and rupees second, because the two entry times put different rupee
   amounts at risk.
