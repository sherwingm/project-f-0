# S1 fade · 09:15 vs 09:16 entry timing counterfactual: methodology (written 30 Oct 2026, before any result)

Read-only research. **No rule, parameter, order, sizing or deployment change.** v12 stays the live rule. Committed
before the analysis script was run; any later change to these definitions is listed at the end with its reason.

## Question
The 29 Oct checkpoint (`data/results/S1_fade_checkpoint_2026-10-29_report.md`) found that live fade buys at
09:15:0x, the v12 stop checks only from 09:16, and in 9 of 14 stops the bid was through the stop before 09:16. The
backtest that selected v12 bought at the 09:16 candle open. **Had each live signal been bought at 09:16 instead, with
the same v12 exit, would the outcome have been materially different?**

## Inputs (copies taken after the close; hashes in the results report)
- `paper_ledger.json` (VM, saved 2026-10-29 15:29:58 IST): the actual trades, `entry_quote`, `rule.shadow_v10`
  (the recorded 15:20 bid) and `after` (post-exit bid extremes to `t2_date`).
- `data/observations/<day>.jsonl` (VM): best bid/ask rows of each position while held and 60 min after the sale.
- `data/entry_probe/<day>.json` (`paper-state`): best bid/ask, sizes and last-trade time of the first 8 walk strikes of
  every fade signal, every second 09:14:50-09:20:00, then every 10 s to 10:00.
- Both recorders write a row **only when the book changes**; between two rows the book is taken as unchanged.

## Signals in scope
Every v12 fade signal that was bought: 19 (ADANIENSOL 23 Oct; 18 on 27-29 Oct). MAHABANK 27 Oct was refused at every
time (one lot never fits the price limits) and is out of scope for both entries. ADANIENSOL has no observation file
(23 Oct); it is included only if the probe alone resolves its counterfactual, and is always reported separately.

## Definitions
1. **09:15 entry (baseline):** the actual trade as booked. Time = `opened_at`; price = `entry.price` (the paper
   real-order fill); outcome = the ledger's `net_pnl`, `reason`, `closed_at`, `exit.price`. Nothing is re-derived.
2. **09:16 entry time.**
   - Trades actually bought **before 09:16:00**: the first recorded row (probe or observation, same contract) with a
     timestamp at or after 09:16:00.000 that is **eligible** (item 4). If that row is not eligible, the next eligible
     row is used, up to 09:20:00. None by 09:20:00 → **unavailable**.
   - Trades actually bought **at or after 09:16:00** (the "not before 09:16" rule does not bind): the 09:16 entry is
     the actual entry, unchanged. Their difference is zero by definition and they are flagged `unchanged`.
3. **Executable entry price:** the **best ask** of that row (the price a buy pays). It is an observed quote, **not a
   fill**: only level-1 size is known. The flag `size_ok` says whether the ask size covered the lot.
4. **Eligible row** (the live walk's own tests, `server/fade.py` `walk`, and the first-trade-today gate from
   `32595932`): bid > 0 and ask > 0; ask ≥ bid; last trade time on the trade date (a book from a previous day is
   **stale** and skipped); ask ≥ ₹2; ask − bid ≤ 10 % of the ask; ask × lot within ₹600-8,000. Missing fields →
   not eligible. The **same contract** as the actual trade is kept, so only the timing changes. Whether the walk
   at 09:16 would have picked a different strike is reported as a flag where the probe has the nearer strikes
   (`walk_same`: yes / no / unknown); the other strike's outcome is not reconstructed.
5. **Bid stream after the 09:16 entry:** all probe rows for the contract and all observation rows for the position id
   (held and after-exit phases are both market data for the hypothetical trade), merged and sorted by time; only rows
   **strictly after** the entry row are used. Rows without a bid are skipped. No interpolation.
6. **v12 exit, applied from the 09:16 entry price E** (`strategies/S1_v12_fade_trail2.md`), row by row:
   - if the trail is off: bid ≤ 0.80 × E → **stop**, sold at that bid; else bid ≥ 1.10 × E → trail on, peak = bid;
   - if the trail is on: peak = max(peak, bid); bid ≤ 0.98 × peak → **trail**, sold at that bid;
   - the stop is checked from the first row after the entry (the entry is after 09:16, so "from 09:16" holds).
   - Sale price = the observed bid of the triggering row: a **simulated fill**, no slippage, no order simulation.
7. **Coverage end and the 15:20 exit.** The stream ends at the last recorded row (probe to 10:00; observations to the
   actual sale + 60 min). If neither stop nor trail fired by then:
   - **resolved at 15:20** only if the trail never switched on and the server's post-exit extremes rule out any trigger
     in the unrecorded time: `after.low_bid` > 0.80 × E and `after.peak_bid` < 1.10 × E (these cover from the actual
     sale to `t2_date`, a superset of the rest of the day, so the test is conservative). Exit price = the recorded
     15:20 bid (`rule.shadow_v10.fill`), reason `eod`;
   - otherwise **unresolved** → the trade's 09:16 outcome is **unavailable** (not guessed).
8. **Charges and size:** the actual lot quantity (`qty`, 1 lot) and `server/charges.py round_trip(type, "BUY", qty,
   E, X)` for both legs. Net % = net / (E × qty).
9. **Engine check (09:15 replay):** the same engine (items 5-7) is also run from the actual 09:15 entry (time and
   price), giving a "replayed 09:15" outcome under identical execution assumptions. The headline difference uses the
   actual 09:15 outcome; the replay shows how much of the difference is the execution model rather than the timing.

## Measures
Per method: eligible count, unavailable count, wins (net > 0), win %, total net, mean / median net %, average win and
loss, stop / trail / 15:20 counts, maximum drawdown of the chronological realised net (trades ordered by day, then
entry time), mean entry-price difference (09:16 ask − 09:15 price, ₹ and %), first-minute adverse move (lowest bid in
the 60 s after each entry vs that entry's price), exit time and price differences. A per-trade table lists both
entries, both exits and the net difference.

## Groups and robustness
- All available; **28-29 Oct only** (fresh books, the entry rule from `32595932`); **27 Oct separately**; ADANIENSOL
  separately.
- With and without 27 Oct; with and without the trade with the largest absolute net difference.
- **Valid comparable quotes only:** `size_ok`, the 09:16 entry row from the 1-second probe (not a 30-60 s observation
  row), and the exit decided by recorded rows (not the 15:20 extremes test).
- Standing-book variant: the 09:16 entry at the book standing at 09:16:00 (the last row at or before 09:16:00, if the
  probe was polling the contract), to show the effect of the change-only recording.
- Statements: n is small (≤ 19 signals, 4 days). Differences are described, not tested for significance beyond a
  paired t shown for scale. Nothing here is a validated edge or a rule recommendation by itself.

## Changes after this was committed
(none yet)
