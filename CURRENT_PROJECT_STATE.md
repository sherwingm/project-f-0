# Current project state (13 Nov 2026, draft, not yet committed)

Snapshot of what is true now, with the evidence. "Previous" = early/mid October 2026 unless stated; the pre-24 Sep state is not recoverable.
Statuses: improved, unchanged, degraded, incomplete, unresolved, unverified. Companion: `PROJECT_JOURNAL.md`, `CHANGELOG_ANALYSIS.md`, `STRATEGY_HISTORY.md`.

## Status table
| Area | Previous state | Current state | Status |
|---|---|---|---|
| Strategies | S1 arms A/B and v10 fade on paper; S2 screens | S1 fade v12 (paper), arms A/B (reference), G1 / G1-F / G1-C / XP (paper), NT (paper, separate); all research pods closed | improved in breadth; **no validated edge** |
| Backtesting | Daily candles, no engine for index | 1-minute data from Oct 2024; `s3_engine.py`; stress simulators validated against the engine | improved |
| Execution realism | Instant paper fills; no seconds | Real-order paper fills (26 Oct); today's-book rule; 1-s recorders; but S1 backtest has no slippage, stops differ live vs history | improved, **unresolved gaps** |
| Data quality | Kotak spot with wrong 09:15 bar | Spot repaired and audited; G1 days audited complete; no bid/ask history; zero-volume carried candles | improved, gaps remain |
| Research validation | Pre-registered pages, no trial count | Registry (17 rows), validation tests, stress audit, verifier agent; no sealed holdout for S1 / G1 | improved process, **evidence unchanged** |
| Risk management | Loss halts, 6 % per position, 3 positions | Halts removed (user); per-trade cap and position counts remain; paper only | changed by decision |
| Automation | Server slept; manual deploys | Always-on VM, systemd, Telegram alerts, nightly jobs; deploy via skill; no auto-promotion | improved |
| Documentation | README, DECISIONS, PROGRESS | + CLAUDE.md, handoffs, registry, SOURCES, VALIDATION_INVENTORY, cheat sheet, this journal | improved (some docs stale, see below) |
| Testing | 739 pass, 1 skipped (about 8 Nov, HANDOFF) | 803 pass, 0 failed (13 Nov, quoted; not re-run for this journal) | improved |

## Live paper results (descriptive; nothing is judged)
- **S1 fade v12:** 58 closed trades to 9 Nov, mean -5.69 % of premium, 47 % won (from the 9 Nov ledger snapshot; previously inspected).
- **G1:** 1 of 30 trades, -73.2 % (gap through the 50 % stop). **G1-F:** 0 of 30. **G1-C:** 1 of 30, -50.75 %. **XP:** 1 of 40 days, -72.5 %. (Figures from `HANDOFF_INDEX_G1.md`, 13 Nov 16:00 IST; not re-fetched.)
- Prospective holdout (freeze 13 Nov 17:48:58 IST): 0 trades.

## Backtest results that exist (all in-sample unless stated)
- S1 fade v12 (339 trades, Oct 2024 to Aug 2026): +2.86 %, t 1.79; bracket -2.33 % to +5.42 %; slippage 2 % a side -> -1.13 %.
- G1 (259): +5.54 %, t 0.94; G1-F (154): +19.7 %, t 2.41, positive in 27 / 27 neighbours and every stress; max drawdown Rs 41.6k; 7 of 23 months negative.
- G1 history says calls (G1-C) lose about 11 % a trade; XP loses (-11.0 %, t -2.70).
- 40 or so other studies: negative (see `STRATEGY_HISTORY.md`).

## Backtest vs execution: original and current
- **Entry price.** S1 early: daily VWAP or close -> now 09:16 candle open + 1 tick (7.2 % dearer than the daily VWAP entry). S3: last traded close + 0.5 % (1 % wide). Live: ask at the next quote. Questionable: a fill at the first print of a minute whose median range is 16 % (S1).
- **Exit price.** S1: 15:20 sale -> -20 % stop -> v12 stop + trail, fills at min(level, candle open). G1: next session 15:29, 50 % stop on the minute close. Live: any second's bid. Questionable: candle-based fills assume liquidity at the level.
- **Stop-loss.** History checks on candle low (S1) or minute close (G1); live uses per-second bids. Documented difference, pinned by a test; effect on G1: stop on every minute's low improves the result (+6.44 %), which is counterintuitive and unexplained.
- **Trailing stop.** Only S1 v12 (on at +10 %, 2 % below peak). The trail on the activation candle is not tested (V4).
- **Slippage.** S1 none (backtest); S3 flat 0.5 % / 1 %. Corrected: none. Questionable: both.
- **Charges.** `server/charges.py`; STT dated for the S3 engine only; Rs 35.53 exchange charge unverified against 35.03. Charges are not the dominant risk (stress audit).
- **Candle resolution.** Daily -> 1-minute (Oct 2024 on); 1-second recorders from 26 Oct (stocks) and 2 Nov (index) are not yet used in any result.
- **Intrabar ordering.** Unknowable on 1-minute candles; S1 baseline assumes stop first (200 of 339 trades differ under the opposite assumption).
- **Live vs historical.** Listed above; plus: the index feed is frozen 15:15 to 15:28 since 3 Aug 2026; special sessions need a manual calendar entry.

## Known weaknesses to fix before any further strategy development (priority order)
1. Settle the S1 intrabar order and the entry-candle problem with the 1-second recorder (live era), and report S1 net of 1 to 2 % slippage as the headline.
2. Keep the prospective holdout clean: count only trades after the 13 Nov 17:48:58 freeze; review at 30 / 60 / 90 trades; never re-use reported trades.
3. Record live top-of-book at 09:16 and 15:29 so a future audit has real spreads.
4. Add a trial counter for every new S1 / G1 variant (registry row **before** the run) and apply Holm across families.
5. Verify STT and exchange-charge history against official documents; then decide whether to date-version the S1 backtests.
6. Remove or test the S1 strike-pick look-ahead (whole-day volume).
7. Walk-forward and a sealed holdout policy for G1 / G1-F; re-validate G1-F's filters on live trades only.
8. Deploy the later pushes at a quiet restart outside 09:00 to 15:40 IST.

## Documents that are stale or inconsistent (noted, not edited)
- `STRATEGY_AUDIT.md` (18 Oct) says no index options exist; true then, no longer.
- `HANDOFF.md` is the S1 handoff dated 8 Nov; `HANDOFF_INDEX_G1.md` is the index one (13 Nov).
- `DECISIONS.md` "S1 versions" table has v10 and v11 rows with long inline results; the v12 row is in the Orders section instead. The two near-identical dates of the loss-halt removals (21 / 22 Oct) appear in different sections.
- `docs/research/experiments.csv` is back-filled from 5 Nov; S1 history before that has no registry rows.
- The stress report's G1 "20 trade categories" (plan) vs 23 (actual) is noted in the report itself.
