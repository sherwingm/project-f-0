# Research limitations, disclosures and reproducibility (coordinator, 17 Nov 2026)

## Sample size and power (Agent 5)
G1-F: 154 trades (discovery 75), standard deviation of net % 101.4 points, standard error of the mean 8.2 (mean +19.7 %, median -18.2 %). Smallest class difference detectable with 80 % power:
- cells of 10 trades: 127 points (alpha 0.05) / 173 points (alpha 0.003)
- cells of 20: 90 / 122; cells of 40: 64 / 86; cells of 80: 45 / 61.
Effects below about 45 points can never be seen; classes under 10 trades (high VIX, gap-up, sudden expansion, the strongest direction quintile) carry no conclusion. **"No evidence" is not "no effect."**

## Structural empties and small cells
G1-F has by its own filters no actual gap-up and no high-VIX trades; 2 sudden-expansion trades; 6 trades in the strongest direction quintile; 13 GIFT gap-up and 28 gap-down trades (all 13 gap-ups had a flat actual open). The second year is 71 of 79 low-VIX trades. Event cells are mostly under 10 trades.

## Concentration
The top 8 G1-F trades (5 %) earn 77 % of rupees; without them the mean is +5.8 % and the median -27.5 %. Class means without their 3 best trades are reported next to every class (`results_tables/`): bullish direction +59.5 % becomes +14.6 %; normal VIX +38.1 % becomes +20.2 %; FII-options "low" +61 % becomes 0 %; FII-futures "high" +45 % becomes +4 %; same-contract "stronger" +53.5 % becomes +18.0 %.

## Data limitations (full list in `DATA_INVENTORY.md`)
- **Not obtainable:** FII / DII cash before 2025-12 and for 2026-09 (NSE serves only the latest day; NSDL archive needs form scraping; no verified bulk source); the GIFT 09:00 level and intraday history; timestamped news and the rest of the economic calendar; NIFTY 50 constituents of earlier years; BANKNIFTY option minutes and trade records; SENSEX daily file.
- **Third-party FII / DII data:** one verified day (NSE's combined table on 2026-11-17); its own NIFTY and VIX columns differ from NSE's official files on some days (up to 0.38 % and 2.1 %), so only its FII / DII values were used; descriptive only.
- **USD/INR:** the Yahoo daily series is unusable; the hourly "previous Indian session" is an approximation (08:30 to 15:30 IST bars) and covers 141 of 154 trades.
- **Crude:** roll artefacts and daily / hourly disagreement (27 of 527 days flagged); treated as quality-limited.
- **GIFT:** daily settlement and the 06:30 open only. The 09:00 level, which a trader would see just before 09:15, is unavailable, so "GIFT as the pre-open indication" is only approximated by the 06:30 open.
- **Clock times:** the exact publication clock times of NSE, NSE IX and third-party files are not in the files; "evening after the close" is a stated convention.
- **Minute-bar stamps** in the store (start vs end of minute) were not verified; MAE uses option minute closes (last price carried forward up to 30 minutes), not intraminute lows; about 49 % of option-minute rows are zero-volume fillers.

## Definition issues found and how they were handled
- **GIFT overnight definition.** `PREREG_REGIME.md` Amendment 1 words it as "open / the previous trade date's GIFT settlement - 1 (GIFT-to-GIFT, so carry cancels)". The first implementation used the file's `prev_settle` column, which is not the previous row's settlement (it already holds US-hours movement; correlation with the actual NIFTY gap 0.50, 0.22 on G1-F's days). The previous-row settlement is contaminated on 23 monthly roll days. The faithful, same-contract version (correlation 0.75) was built afterwards at the coordinator's request and is **primary**; all three versions are shown, and all are counted in the multiple-comparison correction. This is a documented correction made after the first results were seen: the sequence is stated so nothing is presented as chosen in advance. The first-version VIX x GIFT hit (p 0.020) does not appear under the faithful version (p 0.164).
- **Class definitions differ between agents** even where the names match (Agent 2's 20-session class differs from Agent 3's in 20 of 154 trades, its VIX class in 25: store history from 2021-10 and signal-minute VIX vs 2018+ and previous close). The pre-registered classes (Agent 3) are used for every regime result; Agent 2's cuts are descriptive.
- **Asia pre-entry:** Agent 3b averaged whichever of Nikkei and Hang Seng was available (152 trades, 19 with one market); Agent 4 required both (133). Both results are shown; neither is significant.
- **S&P 500:** Agent 3 used a stale cache (20 NaN and 2 wrong values on 2026-09-29); Agent 4's complete series is used.
- **Win and top-5 % definitions** differed between agents; `scripts/consolidate_regime_stats.py` recomputes everything with one definition (win = net % > 0; top-5 % share of the class's net rupees).
- **VIX class edge:** one trade (2026-01-29, VIX 13.53) switches class on a 0.02-point difference between the VIX files. Three G1 / G1-C trades use a Muhurat or weekend special session as the previous session (2025-02-03, 2024-11-04, 2025-10-23, 2026-02-02 flagged by Agent 1).
- **Percent vs rupees:** class means in percent and totals in rupees can disagree in sign (G1 and G1-F 2025 Q4: mean +2.4 % but Rs -6.7k), because percent averages ignore premium size. Both are shown separately everywhere.
- **Costs:** the recorded replays used the undated 2026 STT table (G1 Rs 40,448 / G1-F Rs 247,046; the dated table gives Rs 41,309 / 247,602, a difference under 0.5 %); slippage is a flat 0.5 % / 1 % of premium; there is no bid-ask history.

## Process disclosures (compliance with the 12 restrictions)
- No strategy rule, parameter, dataset or existing research file was changed; no strategy was optimised; no new backtest or trading system was built (Agent 5 confirmed `git diff` empty for tracked files before the commit of this folder).
- The sealed expiry dataset and the live ledgers were not opened; the live server and VM were not touched.
- **Minor breach, disclosed:** Agent 1's `inventory_checks.py` (lines 163-167) read two 1-second NIFTY recorder files in the prospective window (`nifty_1s/2026-11-02.parquet`, `2026-11-17.parquet`) and printed row counts, kinds and time spans. Metadata only; nothing from them was used in any analysis.
- Side effect: `data/events.sqlite-shm` and `-wal` files were created by a read-only open of the stock-events database; the database itself is unchanged.
- Downloads were made only after the user's explicit approval (17 Nov, "download all the necessary data"); the agents performed none.
- The second half of the sample had been seen descriptively in earlier reports; it is used here only as a consistency check.
- An earlier partial run of Agent 4 (`interim/agent4_external/superseded_v1/`) and an older inventory folder (`interim/agent1_data_inventory/`) are superseded and not used.
- The two earlier stopped agents (inventory and external, stopped when the user approved downloading) produced no results used here.

## Reproducibility
- **Plan:** `PREREG_REGIME.md` (commit `fa8f11d5b`, before any agent output) and Amendment 1 (commit `7ef92eb31`, after the downloads and before any analysis of the new data). SHA-256 prefix of the first plan: `e819033d85ac6c40`.
- **Data:** `DATA_DOWNLOAD_MANIFEST.json` (25 files, sha256 prefixes, row counts, sources), `DOWNLOAD_QUALITY_CHECKS.md`, `scripts/fetch_external.py` (re-fetches the public files; the FII / DII file was extracted from the third-party page through its month selector and is saved as `external_data/fii_dii_cash_stockezee.csv`; raw data is git-ignored), `scripts/quality_checks.py`, `scripts/make_manifest.py`.
- **Trades:** `index_context_research/results/context_dataset.csv` (755 rows; G1 259, G1-F 154, G1-C 235, XP 107; hash in `index_context_research/EXPERIMENT_MANIFEST.json`), replay files named in `DATA_INVENTORY.md`.
- **Date ranges:** trades 2024-10-01 to 2026-10-28; discovery to 2025-09-30; GIFT 2023-07-03 to 2026-11-17; breadth 2021-10 to 2026-11; NSE indices 2018 to 2026-11; FII / DII cash 2025-12-01 to 2026-11-17; participant OI 2021-09 to 2026-11-06; boundaries 2018-01-01 to 2024-09-30 (Agent 2: store start 2021-10-20).
- **Configuration:** thresholds in `PREREG_REGIME.md` and `interim/agent3_regimes/boundaries.json`; bootstrap seed 20261117 (resampling trading days; 4,000 to 5,000 draws per agent; 2,000 in the consolidation script).
- **Scripts:** each agent's folder under `interim/` holds its scripts and `hashes.txt` (input and output sha256 prefixes): `agent1_inventory`, `agent2_anatomy`, `agent3_regimes`, `agent3b_gift_regimes`, `agent4_external`, `agent5_integrity` (audit scripts `audit_01` to `audit_09`, `consolidated_tests.csv`, `consolidated_summary.csv`); coordinator scripts `scripts/merge_mfe_mae.py`, `scripts/consolidate_regime_stats.py`. Run with `C:\Users\sherw\.venvs\fo\Scripts\python.exe`.
- **Agents:** five independent agents plus one resumed follow-up (3b, same-contract GIFT). Each wrote only inside its own `interim/` folder; the coordinator wrote the seven deliverables and reconciled the findings. No agent's work is claimed beyond what its report and files show.
