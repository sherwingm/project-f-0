# Institutional, global, breadth and news conditions: draft (agent 4)

Written 17 Nov 2026 from `external_features.csv` / `external_tables.csv` / `external_tests.csv` / `external_consistency.csv` (all in this folder, built by the scripts here). Original recorded trade results only; nothing re-simulated; no prospective-holdout, sealed or VM data touched; no download. Percentages are net rupees (after slippage and charges) divided by the premium paid; rupees are separate. Raw p-values only: the coordinator applies the final Benjamini-Hochberg over the enlarged family.

## 1. Plain-words summary

- **No external condition separates better from worse G1-F trades in a way that survives scrutiny.** Of 19 pre-registered single-condition tests on G1-F (Kruskal-Wallis, whole sample), one has a raw p below 0.05 (USD/INR, p 0.042); about one in twenty would be expected by chance, and the FII/DII cash test (p 0.082) and the participant-OI level test (p 0.103) are also not significant.

- Pattern worth stating but NOT a finding: in G1-F **FII/DII cash, both buying the previous session** had 15 trades with 1 winner (mean -29.4 %) against 44 'diverge' trades (mean +34.3 %); Welch p 0.004 (KW p 0.082). The window is only Dec 2025 to Oct 2026 (September 2026 missing), the data are third-party and verified on one day, the cell is 15 trades, and the sign is the same for G1 (which contains G1-F) so it is not independent evidence. Descriptive only.

- The strongest single-strategy results are for the **secondary** strategies and are explained by time structure: G1-C and the FII futures long-share level (levels cut in 2024-25 move into another range later, so the 'high' class exists only in the discovery half); G1-C and the US VIX spike (23 trades, nominal p 0.006, same direction in both halves, small spike cell).

- Whether the strategies' periods differ because of institutional positioning, Asia, US, breadth or news **cannot be established** from 154 trades with these conditions: cells are small, the second half has already been seen, and level classes drift.

## 2. Data, alignment, publication times

See `availability_table.md` (variable, source, coverage, publication time, alignment). Key points: every predictor is dated before 09:16 IST of the trade day (Asian opens 05:30 / 07:00 IST; US and commodities closed overnight; breadth, sector, FII/DII and participant files are the previous session's, published that evening). Same-day versions are POST-ENTRY and were not used. **The Yahoo daily USD/INR close equals its open on most days and was rejected; the USD/INR variable uses the hourly series, which exists only from 2024-11-18 (13 of 154 G1-F trades missing).** Brent is quality-limited (daily vs hourly disagree by more than 2 % on 27 of 527 days; 3 G1-F trades sit on such days). DXY had 463 weekend rows with no price, dropped.

## 3. Method (all fixed in advance)

Classes and thresholds are exactly Amendment 1 of `PREREG_REGIME.md`; participant-level terciles come from the 248 session days of 2024-10-01 to 2025-09-30 (independent of any trade return); GDELT is the previous UTC day's tone against the median of the 250 earlier days. Per class: n, wins, losses, win rate, mean and median net %, total net Rs, average profit and loss, max up (mean, median, shares >= 50/100/200 %), top-5 % trades' share of gross profit, bootstrap 95 % interval of the mean (trading days resampled, 5000 draws, seed 20261117). Cells with n < 10 are marked TOO FEW and carry no conclusion. Tests: Kruskal-Wallis over classes with n >= 10 and a Welch difference between two named classes (named in advance in `analyse_external.py`). **Explanatory** = whole sample. **Predictive** = rules fixed in advance, discovery entries to 2025-09-30, then consistency in 2025-10-01 to 2026-10-28 (already seen descriptively, so a consistency check and not a pristine holdout) and by half-year (`external_tables.csv`, analyses `hy_*`). Full tables for all four strategies: `external_tables.csv`; tests: `external_tests.csv`; consistency: `external_consistency.csv`; confound check: `context_checks.csv`.

## 4. G1-F results, by hypothesis (primary)

**H12. Asia pre-entry: mean of Nikkei and Hang Seng opening gap (+/-0.3 %)**
- down - whole: n=37, win 38%, mean 13.7%, median -50.9%, Rs 31,415; 95% CI of mean -15.4 to 45.5; max up mean 95%, >=100%: 41% of trades; top-5% trades = 30% of gross profit
  - discovery: n=12, win 58%, mean 40.0%, median 33.0%, Rs 29,850
  - second half: n=25, win 28%, mean 1.1%, median -51.0%, Rs 1,565
- flat - whole: n=58, win 47%, mean 21.3%, median -11.0%, Rs 116,626; 95% CI of mean -2.5 to 47.2; max up mean 101%, >=100%: 40% of trades; top-5% trades = 29% of gross profit
  - discovery: n=35, win 46%, mean 8.8%, median -21.4%, Rs 48,022
  - second half: n=23, win 48%, mean 40.4%, median -0.0%, Rs 68,605
- up - whole: n=38, win 34%, mean 8.0%, median -15.0%, Rs 22,623; 95% CI of mean -15.7 to 34.6; max up mean 105%, >=100%: 45% of trades; top-5% trades = 47% of gross profit
  - discovery: n=18, win 39%, mean 12.8%, median -7.3%, Rs 15,265
  - second half: n=20, win 30%, mean 3.7%, median -22.0%, Rs 7,358
- Kruskal-Wallis p (raw): whole 0.849, discovery 0.590, second half 0.349. Welch up vs down: whole diff -5.7 pts p 0.783; discovery diff -27.3 p 0.446; second half diff 2.6 p 0.924 (blank = a class under 10 trades). Missing feature: 21 of 154 trades.

**H13. Global risk: risk-on = US up & Asia not down; risk-off = US down & Asia not up**
- risk_off - whole: n=40, win 38%, mean 18.3%, median -25.2%, Rs 48,075; 95% CI of mean -11.4 to 51.3; max up mean 101%, >=100%: 38% of trades; top-5% trades = 32% of gross profit
  - discovery: n=16, win 50%, mean 26.0%, median -15.2%, Rs 30,021
  - second half: n=24, win 29%, mean 13.2%, median -25.2%, Rs 18,053
- mixed - whole: n=54, win 41%, mean 14.0%, median -28.1%, Rs 71,961; 95% CI of mean -9.4 to 38.1; max up mean 105%, >=100%: 44% of trades; top-5% trades = 35% of gross profit
  - discovery: n=26, win 35%, mean 1.1%, median -34.2%, Rs 19,664
  - second half: n=28, win 46%, mean 26.0%, median -24.1%, Rs 52,297
- risk_on - whole: n=39, win 44%, mean 14.3%, median -10.4%, Rs 50,629; 95% CI of mean -9.5 to 40.8; max up mean 93%, >=100%: 41% of trades; top-5% trades = 35% of gross profit
  - discovery: n=23, win 57%, mean 24.9%, median 7.9%, Rs 43,451
  - second half: n=16, win 25%, mean -1.0%, median -27.5%, Rs 7,178
- Kruskal-Wallis p (raw): whole 0.775, discovery 0.461, second half 0.823. Welch risk_on vs risk_off: whole diff -4.0 pts p 0.848; discovery diff -1.1 p 0.971; second half diff -14.2 p 0.653 (blank = a class under 10 trades). Missing feature: 21 of 154 trades.

**X01. US overnight: S&P 500 previous US session (+/-0.3 %)**
- down - whole: n=53, win 38%, mean 20.0%, median -31.9%, Rs 84,440; 95% CI of mean -8.1 to 52.4; max up mean 101%, >=100%: 34% of trades; top-5% trades = 45% of gross profit
  - discovery: n=23, win 43%, mean 29.8%, median -51.4%, Rs 66,347
  - second half: n=30, win 33%, mean 12.4%, median -25.2%, Rs 18,093
- flat - whole: n=48, win 35%, mean 8.0%, median -46.8%, Rs 56,683; 95% CI of mean -16.6 to 34.9; max up mean 101%, >=100%: 42% of trades; top-5% trades = 43% of gross profit
  - discovery: n=24, win 33%, mean 3.9%, median -46.8%, Rs 31,123
  - second half: n=24, win 38%, mean 12.1%, median -41.0%, Rs 25,561
- up - whole: n=53, win 49%, mean 29.9%, median -2.0%, Rs 105,923; 95% CI of mean 4.8 to 57.9; max up mean 111%, >=100%: 47% of trades; top-5% trades = 28% of gross profit
  - discovery: n=28, win 61%, mean 39.8%, median 14.6%, Rs 65,449
  - second half: n=25, win 36%, mean 18.8%, median -26.1%, Rs 40,474
- Kruskal-Wallis p (raw): whole 0.260, discovery 0.221, second half 0.839. Welch up vs down: whole diff 9.9 pts p 0.629; discovery diff 10.0 p 0.757; second half diff 6.4 p 0.812 (blank = a class under 10 trades). Missing feature: 0 of 154 trades.

**X02. USD/INR previous Indian-session change, hourly (+/-0.2 %)**
- down - whole: n=15, win 40%, mean 36.3%, median -51.2%, Rs 46,113; 95% CI of mean -26.0 to 111.4; max up mean 140%, >=100%: 40% of trades; top-5% trades = 51% of gross profit
  - discovery: n=8 TOO FEW, win 25%, mean 26.0%, median -51.5%, Rs 24,996
  - second half: n=7 TOO FEW, win 57%, mean 48.1%, median 32.2%, Rs 21,117
- flat - whole: n=102, win 33%, mean 7.4%, median -39.4%, Rs 111,146; 95% CI of mean -9.8 to 26.2; max up mean 91%, >=100%: 35% of trades; top-5% trades = 39% of gross profit
  - discovery: n=44, win 39%, mean 7.8%, median -37.5%, Rs 71,449
  - second half: n=58, win 29%, mean 7.2%, median -43.5%, Rs 39,697
- up - whole: n=24, win 67%, mean 46.1%, median 20.8%, Rs 77,005; 95% CI of mean 13.1 to 80.7; max up mean 123%, >=100%: 54% of trades; top-5% trades = 36% of gross profit
  - discovery: n=11, win 82%, mean 64.3%, median 20.9%, Rs 52,776
  - second half: n=13, win 54%, mean 30.8%, median 11.9%, Rs 24,229
- Kruskal-Wallis p (raw): whole 0.042, discovery 0.070, second half 0.085. Welch up vs down: whole diff 9.8 pts p 0.814; discovery diff - p n/a; second half diff - p n/a (blank = a class under 10 trades). Missing feature: 13 of 154 trades.

**X03. Brent previous-day change (+/-1 %); quality-limited**
- down - whole: n=38, win 37%, mean 12.3%, median -29.2%, Rs 40,738; 95% CI of mean -18.6 to 49.9; max up mean 101%, >=100%: 32% of trades; top-5% trades = 50% of gross profit
  - discovery: n=17, win 53%, mean 19.5%, median 7.9%, Rs 38,097
  - second half: n=21, win 24%, mean 6.4%, median -51.4%, Rs 2,641
- flat - whole: n=74, win 45%, mean 30.6%, median -15.6%, Rs 174,820; 95% CI of mean 6.8 to 56.9; max up mean 115%, >=100%: 49% of trades; top-5% trades = 28% of gross profit
  - discovery: n=41, win 46%, mean 29.2%, median -12.6%, Rs 96,434
  - second half: n=33, win 42%, mean 32.5%, median -50.9%, Rs 78,387
- up - whole: n=41, win 39%, mean 8.4%, median -8.3%, Rs 37,695; 95% CI of mean -12.5 to 32.2; max up mean 91%, >=100%: 37% of trades; top-5% trades = 47% of gross profit
  - discovery: n=16, win 44%, mean 26.0%, median -16.9%, Rs 34,595
  - second half: n=25, win 36%, mean -2.8%, median -8.3%, Rs 3,100
- Kruskal-Wallis p (raw): whole 0.835, discovery 0.893, second half 0.750. Welch up vs down: whole diff -3.8 pts p 0.854; discovery diff 6.4 p 0.865; second half diff -9.2 p 0.713 (blank = a class under 10 trades). Missing feature: 1 of 154 trades.

**X04. US VIX previous-session rise >= +10 % (spike)**
- no_spike - whole: n=132, win 42%, mean 19.7%, median -15.6%, Rs 191,479; 95% CI of mean 3.4 to 37.4; max up mean 103%, >=100%: 41% of trades; top-5% trades = 33% of gross profit
  - discovery: n=68, win 47%, mean 20.5%, median -7.3%, Rs 99,465
  - second half: n=64, win 36%, mean 18.8%, median -27.5%, Rs 92,014
- spike - whole: n=13, win 23%, mean 0.3%, median -51.0%, Rs 13,174; 95% CI of mean -45.0 to 72.4; max up mean 85%, >=100%: 15% of trades; top-5% trades = 91% of gross profit
  - discovery: n=3 TOO FEW, win 33%, mean 98.4%, median -51.5%, Rs 34,653
  - second half: n=10, win 20%, mean -29.2%, median -50.9%, Rs -21,480
- Kruskal-Wallis p (raw): whole 0.449, discovery n/a, second half 0.591. Welch spike vs no_spike: whole diff -19.4 pts p 0.592; discovery diff - p n/a; second half diff -48.0 p 0.007 (blank = a class under 10 trades). Missing feature: 9 of 154 trades.

**X05. Dollar index previous-day direction (descriptive)**
- down - whole: n=58, win 43%, mean 13.6%, median -10.8%, Rs 101,434; 95% CI of mean -8.4 to 38.3; max up mean 96%, >=100%: 43% of trades; top-5% trades = 42% of gross profit
  - discovery: n=28, win 54%, mean 30.8%, median 8.4%, Rs 87,469
  - second half: n=30, win 33%, mean -2.5%, median -18.9%, Rs 13,964
- up - whole: n=93, win 40%, mean 22.0%, median -25.9%, Rs 138,736; 95% CI of mean 1.8 to 43.5; max up mean 105%, >=100%: 39% of trades; top-5% trades = 34% of gross profit
  - discovery: n=45, win 44%, mean 25.9%, median -12.6%, Rs 86,152
  - second half: n=48, win 35%, mean 18.4%, median -31.1%, Rs 52,584
- Kruskal-Wallis p (raw): whole 0.927, discovery 0.496, second half 0.633. Welch up vs down: whole diff 8.4 pts p 0.600; discovery diff -4.9 p 0.847; second half diff 20.9 p 0.305 (blank = a class under 10 trades). Missing feature: 3 of 154 trades.

**X06. US 10-year yield previous-day direction (descriptive)**
- down - whole: n=65, win 34%, mean 13.4%, median -36.2%, Rs 85,029; 95% CI of mean -10.9 to 40.7; max up mean 100%, >=100%: 38% of trades; top-5% trades = 47% of gross profit
  - discovery: n=31, win 39%, mean 12.5%, median -32.5%, Rs 51,262
  - second half: n=34, win 29%, mean 14.3%, median -43.5%, Rs 33,767
- up - whole: n=86, win 47%, mean 24.8%, median -1.9%, Rs 163,328; 95% CI of mean 4.8 to 46.5; max up mean 108%, >=100%: 42% of trades; top-5% trades = 33% of gross profit
  - discovery: n=43, win 53%, mean 35.4%, median 6.8%, Rs 112,425
  - second half: n=43, win 40%, mean 14.2%, median -11.7%, Rs 50,903
- Kruskal-Wallis p (raw): whole 0.265, discovery 0.366, second half 0.479. Welch up vs down: whole diff 11.4 pts p 0.504; discovery diff 22.9 p 0.353; second half diff -0.1 p 0.998 (blank = a class under 10 trades). Missing feature: 3 of 154 trades.

**H14. Breadth: advance share of previous session (<=p25 low, >=p75 high; cuts from 2021-10..2024-09)**
- low - whole: n=43, win 42%, mean 9.1%, median -21.4%, Rs 46,868; 95% CI of mean -13.5 to 32.3; max up mean 108%, >=100%: 51% of trades; top-5% trades = 40% of gross profit
  - discovery: n=21, win 48%, mean 16.0%, median -2.0%, Rs 42,044
  - second half: n=22, win 36%, mean 2.6%, median -51.2%, Rs 4,825
- mid - whole: n=79, win 44%, mean 33.7%, median -9.8%, Rs 168,051; 95% CI of mean 9.7 to 58.9; max up mean 113%, >=100%: 39% of trades; top-5% trades = 29% of gross profit
  - discovery: n=39, win 46%, mean 31.5%, median -12.6%, Rs 69,091
  - second half: n=40, win 42%, mean 35.9%, median -9.2%, Rs 98,959
- high - whole: n=31, win 32%, mean 0.7%, median -51.2%, Rs 37,013; 95% CI of mean -27.6 to 36.7; max up mean 83%, >=100%: 32% of trades; top-5% trades = 65% of gross profit
  - discovery: n=14, win 50%, mean 27.2%, median -24.8%, Rs 56,669
  - second half: n=17, win 18%, mean -21.2%, median -51.5%, Rs -19,656
- Kruskal-Wallis p (raw): whole 0.249, discovery 0.732, second half 0.254. Welch high vs low: whole diff -8.5 pts p 0.687; discovery diff 11.2 p 0.773; second half diff -23.8 p 0.258 (blank = a class under 10 trades). Missing feature: 1 of 154 trades.

**X07. Sector leadership: Nifty Bank minus Nifty 50 previous day (+/-0.3 pts)**
- bank_lags - whole: n=24, win 58%, mean 36.5%, median 12.9%, Rs 83,768; 95% CI of mean -0.7 to 76.7; max up mean 96%, >=100%: 42% of trades; top-5% trades = 39% of gross profit
  - discovery: n=14, win 71%, mean 49.2%, median 32.8%, Rs 64,289
  - second half: n=10, win 40%, mean 18.8%, median -29.8%, Rs 19,479
- in_line - whole: n=98, win 34%, mean 15.1%, median -31.1%, Rs 103,008; 95% CI of mean -4.7 to 36.9; max up mean 103%, >=100%: 41% of trades; top-5% trades = 33% of gross profit
  - discovery: n=45, win 36%, mean 10.6%, median -42.5%, Rs 36,809
  - second half: n=53, win 32%, mean 18.9%, median -29.0%, Rs 66,199
- bank_leads - whole: n=31, win 52%, mean 23.3%, median 7.6%, Rs 65,157; 95% CI of mean -6.6 to 60.0; max up mean 120%, >=100%: 42% of trades; top-5% trades = 50% of gross profit
  - discovery: n=15, win 60%, mean 51.9%, median 35.7%, Rs 66,707
  - second half: n=16, win 44%, mean -3.5%, median -34.4%, Rs -1,550
- Kruskal-Wallis p (raw): whole 0.519, discovery 0.178, second half 0.834. Welch bank_leads vs bank_lags: whole diff -13.3 pts p 0.622; discovery diff 2.7 p 0.946; second half diff -22.3 p 0.582 (blank = a class under 10 trades). Missing feature: 1 of 154 trades.

**H15. FII/DII cash previous session (third party, 2025-12..2026-10): diverge / both buying / both selling**
- diverge - whole: n=44, win 48%, mean 34.3%, median -5.1%, Rs 117,057; 95% CI of mean 2.3 to 70.1; max up mean 121%, >=100%: 41% of trades; top-5% trades = 35% of gross profit
  - discovery: n=0
  - second half: n=44, win 48%, mean 34.3%, median -5.1%, Rs 117,057
- both_buy - whole: n=15, win 7%, mean -29.4%, median -51.6%, Rs -29,621; 95% CI of mean -47.1 to -2.8; max up mean 82%, >=100%: 27% of trades; top-5% trades = 100% of gross profit
  - discovery: n=0
  - second half: n=15, win 7%, mean -29.4%, median -51.6%, Rs -29,621
- Kruskal-Wallis p (raw): whole 0.082, discovery n/a, second half 0.082. Welch both_buy vs diverge: whole diff -63.7 pts p 0.004; discovery diff - p n/a; second half diff -63.7 p 0.004 (blank = a class under 10 trades). Missing feature: 95 of 154 trades.

**X08. FII index-futures long share LEVEL (terciles of session days 2024-10..2025-09)**
- low - whole: n=100, win 36%, mean 8.7%, median -39.4%, Rs 79,625; 95% CI of mean -8.8 to 27.0; max up mean 91%, >=100%: 36% of trades; top-5% trades = 32% of gross profit
  - discovery: n=32, win 41%, mean 8.8%, median -51.2%, Rs 34,299
  - second half: n=68, win 34%, mean 8.7%, median -29.2%, Rs 45,326
- mid - whole: n=29, win 59%, mean 38.8%, median 8.9%, Rs 101,991; 95% CI of mean 5.4 to 78.3; max up mean 114%, >=100%: 38% of trades; top-5% trades = 33% of gross profit
  - discovery: n=18, win 67%, mean 32.2%, median 14.0%, Rs 63,189
  - second half: n=11, win 45%, mean 49.5%, median -8.5%, Rs 38,802
- high - whole: n=24, win 42%, mean 45.2%, median -13.2%, Rs 70,316; 95% CI of mean -3.5 to 102.5; max up mean 154%, >=100%: 67% of trades; top-5% trades = 60% of gross profit
  - discovery: n=24, win 42%, mean 45.2%, median -13.2%, Rs 70,316
  - second half: n=0
- Kruskal-Wallis p (raw): whole 0.103, discovery 0.236, second half 0.388. Welch high vs low: whole diff 36.5 pts p 0.217; discovery diff 36.4 p 0.259; second half diff - p n/a (blank = a class under 10 trades). Missing feature: 1 of 154 trades.

**X09. FII index-futures long share, 1-session change sign**
- down - whole: n=82, win 40%, mean 15.5%, median -23.7%, Rs 109,536; 95% CI of mean -5.4 to 38.0; max up mean 100%, >=100%: 39% of trades; top-5% trades = 45% of gross profit
  - discovery: n=40, win 50%, mean 30.4%, median 0.1%, Rs 104,805
  - second half: n=42, win 31%, mean 1.3%, median -43.6%, Rs 4,732
- up - whole: n=71, win 42%, mean 25.4%, median -13.8%, Rs 142,395; 95% CI of mean 2.9 to 49.6; max up mean 111%, >=100%: 44% of trades; top-5% trades = 32% of gross profit
  - discovery: n=34, win 44%, mean 21.4%, median -17.6%, Rs 63,000
  - second half: n=37, win 41%, mean 29.1%, median -10.4%, Rs 79,396
- Kruskal-Wallis p (raw): whole 0.448, discovery 0.922, second half 0.353. Welch up vs down: whole diff 9.9 pts p 0.549; discovery diff -9.0 p 0.710; second half diff 27.8 p 0.226 (blank = a class under 10 trades). Missing feature: 1 of 154 trades.

**X10. DII index-futures long share LEVEL (discovery-window terciles)**
- low - whole: n=29, win 55%, mean 33.6%, median 6.8%, Rs 62,042; 95% CI of mean 2.4 to 74.3; max up mean 112%, >=100%: 52% of trades; top-5% trades = 44% of gross profit
  - discovery: n=29, win 55%, mean 33.6%, median 6.8%, Rs 62,042
  - second half: n=0
- mid - whole: n=36, win 44%, mean 37.6%, median -3.9%, Rs 101,974; 95% CI of mean 6.0 to 73.9; max up mean 118%, >=100%: 44% of trades; top-5% trades = 26% of gross profit
  - discovery: n=19, win 42%, mean 29.7%, median -12.6%, Rs 55,171
  - second half: n=17, win 47%, mean 46.4%, median -0.0%, Rs 46,803
- high - whole: n=88, win 35%, mean 8.5%, median -49.2%, Rs 87,916; 95% CI of mean -10.7 to 30.0; max up mean 98%, >=100%: 36% of trades; top-5% trades = 44% of gross profit
  - discovery: n=26, win 42%, mean 15.6%, median -49.4%, Rs 50,592
  - second half: n=62, win 32%, mean 5.6%, median -43.5%, Rs 37,324
- Kruskal-Wallis p (raw): whole 0.133, discovery 0.600, second half 0.107. Welch high vs low: whole diff -25.1 pts p 0.250; discovery diff -18.0 p 0.534; second half diff - p n/a (blank = a class under 10 trades). Missing feature: 1 of 154 trades.

**X11. DII index-futures long share, 1-session change sign**
- down - whole: n=75, win 40%, mean 24.1%, median -17.3%, Rs 106,891; 95% CI of mean 0.4 to 48.9; max up mean 104%, >=100%: 40% of trades; top-5% trades = 34% of gross profit
  - discovery: n=35, win 49%, mean 36.6%, median -2.0%, Rs 75,614
  - second half: n=40, win 32%, mean 13.2%, median -31.1%, Rs 31,277
- up - whole: n=78, win 42%, mean 16.3%, median -22.0%, Rs 145,040; 95% CI of mean -4.0 to 37.8; max up mean 106%, >=100%: 42% of trades; top-5% trades = 37% of gross profit
  - discovery: n=39, win 46%, mean 17.0%, median -13.8%, Rs 92,190
  - second half: n=39, win 38%, mean 15.6%, median -26.1%, Rs 52,850
- Kruskal-Wallis p (raw): whole 0.603, discovery 0.420, second half 0.941. Welch up vs down: whole diff -7.9 pts p 0.635; discovery diff -19.7 p 0.425; second half diff 2.4 p 0.916 (blank = a class under 10 trades). Missing feature: 1 of 154 trades.

**X12. FII index-options stance (net puts minus net calls / option OI) LEVEL (terciles)**
- low - whole: n=15, win 47%, mean 61.2%, median -1.4%, Rs 50,832; 95% CI of mean -6.6 to 142.3; max up mean 172%, >=100%: 60% of trades; top-5% trades = 58% of gross profit
  - discovery: n=15, win 47%, mean 61.2%, median -1.4%, Rs 50,832
  - second half: n=0
- mid - whole: n=28, win 50%, mean 24.2%, median -6.1%, Rs 68,752; 95% CI of mean -7.0 to 56.0; max up mean 103%, >=100%: 46% of trades; top-5% trades = 36% of gross profit
  - discovery: n=26, win 54%, mean 30.1%, median 4.2%, Rs 75,230
  - second half: n=2 TOO FEW, win 0%, mean -52.0%, median -52.0%, Rs -6,477
- high - whole: n=110, win 38%, mean 13.5%, median -29.8%, Rs 132,347; 95% CI of mean -3.6 to 32.0; max up mean 97%, >=100%: 37% of trades; top-5% trades = 35% of gross profit
  - discovery: n=33, win 42%, mean 7.5%, median -47.6%, Rs 41,743
  - second half: n=77, win 36%, mean 16.1%, median -26.1%, Rs 90,605
- Kruskal-Wallis p (raw): whole 0.330, discovery 0.411, second half n/a. Welch high vs low: whole diff -47.7 pts p 0.266; discovery diff -53.7 p 0.226; second half diff - p n/a (blank = a class under 10 trades). Missing feature: 1 of 154 trades.

**X13. FII index-options stance, 1-session change sign (up = more put-heavy)**
- down - whole: n=93, win 35%, mean 19.0%, median -30.3%, Rs 149,562; 95% CI of mean -2.7 to 42.7; max up mean 106%, >=100%: 39% of trades; top-5% trades = 39% of gross profit
  - discovery: n=39, win 41%, mean 24.2%, median -21.4%, Rs 86,389
  - second half: n=54, win 31%, mean 15.3%, median -41.4%, Rs 63,173
- up - whole: n=60, win 50%, mean 21.8%, median 0.8%, Rs 102,370; 95% CI of mean 1.0 to 46.0; max up mean 104%, >=100%: 45% of trades; top-5% trades = 28% of gross profit
  - discovery: n=35, win 54%, mean 28.6%, median 6.8%, Rs 81,416
  - second half: n=25, win 44%, mean 12.3%, median -8.5%, Rs 20,955
- Kruskal-Wallis p (raw): whole 0.230, discovery 0.782, second half 0.191. Welch up vs down: whole diff 2.8 pts p 0.862; discovery diff 4.4 p 0.856; second half diff -2.9 p 0.887 (blank = a class under 10 trades). Missing feature: 1 of 154 trades.

**X14. GDELT tone of the previous UTC day vs trailing 250-day median (global machine score)**
- below_median - whole: n=80, win 41%, mean 18.3%, median -19.7%, Rs 130,723; 95% CI of mean -2.5 to 41.5; max up mean 104%, >=100%: 41% of trades; top-5% trades = 37% of gross profit
  - discovery: n=46, win 48%, mean 29.1%, median -1.7%, Rs 117,336
  - second half: n=34, win 32%, mean 3.7%, median -50.9%, Rs 13,387
- above_median - whole: n=68, win 43%, mean 26.2%, median -12.7%, Rs 136,495; 95% CI of mean 2.8 to 52.1; max up mean 110%, >=100%: 43% of trades; top-5% trades = 35% of gross profit
  - discovery: n=24, win 50%, mean 30.0%, median -6.1%, Rs 61,840
  - second half: n=44, win 39%, mean 24.2%, median -15.1%, Rs 74,655
- Kruskal-Wallis p (raw): whole 0.702, discovery 0.683, second half 0.676. Welch above_median vs below_median: whole diff 7.9 pts p 0.643; discovery diff 0.9 p 0.974; second half diff 20.5 p 0.357 (blank = a class under 10 trades). Missing feature: 6 of 154 trades.

**X15. Scheduled events (RBI / Budget / FOMC / US election) relative to the entry session**
- none - whole: n=128, win 41%, mean 21.9%, median -17.7%, Rs 226,784; 95% CI of mean 4.9 to 40.4; max up mean 109%, >=100%: 44% of trades; top-5% trades = 38% of gross profit
  - discovery: n=61, win 48%, mean 32.1%, median -2.0%, Rs 164,082
  - second half: n=67, win 36%, mean 12.6%, median -26.1%, Rs 62,702
- day_before - whole: n=6 TOO FEW, win 33%, mean -19.9%, median -21.2%, Rs -8,179; 95% CI of mean -43.0 to 2.7; max up mean 64%, >=100%: 17% of trades; top-5% trades = 52% of gross profit
  - discovery: n=4 TOO FEW, win 50%, mean -19.3%, median -21.1%, Rs -4,463
  - second half: n=2 TOO FEW, win 0%, mean -21.2%, median -21.2%, Rs -3,715
- event_day - whole: n=12, win 33%, mean -1.4%, median -29.6%, Rs 4,317; 95% CI of mean -37.0 to 39.3; max up mean 68%, >=100%: 25% of trades; top-5% trades = 38% of gross profit
  - discovery: n=5 TOO FEW, win 20%, mean -32.8%, median -51.4%, Rs -12,242
  - second half: n=7 TOO FEW, win 43%, mean 21.0%, median -29.0%, Rs 16,559
- day_after - whole: n=8 TOO FEW, win 50%, mean 44.5%, median -12.1%, Rs 24,123; 95% CI of mean -37.1 to 143.4; max up mean 113%, >=100%: 38% of trades; top-5% trades = 44% of gross profit
  - discovery: n=5 TOO FEW, win 60%, mean 34.8%, median 1.6%, Rs 15,542
  - second half: n=3 TOO FEW, win 33%, mean 60.7%, median -55.2%, Rs 8,582
- Kruskal-Wallis p (raw): whole 0.985, discovery n/a, second half n/a. Welch event_day vs none: whole diff -23.3 pts p 0.315; discovery diff - p n/a; second half diff - p n/a (blank = a class under 10 trades). Missing feature: 0 of 154 trades.

Supplementary (not in the main family): Brent excluding suspect days gives p 0.849; FII cash sign alone Welch p 0.098; DII cash sign alone cannot be tested (DII was a net buyer on every day with a G1-F trade).

## 5. Explanatory versus predictive, G1-F

- **Explanatory (whole sample).** Raw KW p-values: H12 0.849, H13 0.775, H14 0.249, H15 0.082, X01 0.260, X02 0.042, X03 0.835, X04 0.449, X05 0.927, X06 0.265, X07 0.519, X08 0.103, X09 0.448, X10 0.133, X11 0.603, X12 0.330, X13 0.230, X14 0.702, X15 0.985. Only X02 is below 0.05; no multiplicity correction is applied here.

- **Predictive (discovery, then consistency).** In discovery no G1-F hypothesis has a KW p below 0.05 (smallest: USD/INR 0.070, sector 0.178, S&P 500 0.221). The second half keeps the discovery order of best and worst class (by mean) in 5 hypotheses, reverses it in 8 and is 'too few' or not testable in 6 (`external_consistency.csv`, column `order_holds_h2_mean`; the best/worst class is simply the discovery extreme, not a rule that was set in advance). Examples: breadth 'mid' keeps beating 'low' (35.9 % vs 2.6 % in the second half), S&P 'up' keeps beating 'flat' (18.8 % vs 12.1 %), while Asia 'down' (the discovery best) turns to +1.1 % against +40.4 % for 'flat'. Half-year counts are tiny and are in the consistency file.

- **Same direction in discovery and the second half (G1-F), none significant:** breadth 'mid' above 'low'; S&P 500 'up' above 'flat'; USD/INR 'flat' weak (7.8 % and 7.2 %; the only nominal p below 0.05, whole sample); US VIX spike weak (discovery n 3, second half n 10). **Reversed:** Asia down/flat, high breadth (27.2 % discovery, -21.2 % second half), sector leadership. No condition is consistent and large enough to call a finding.

## 6. Secondary strategies (raw p; full cells in the CSV files)

**G1 puts (259)**

- H15 (FII/DII cash previous session (third party, 2025-12..2026-10): diverge / both buying / both selling): KW p whole 0.404, discovery n/a, second half 0.404; Welch both_buy vs diverge diff -33.6 pts (p 0.035; n 18 vs 84).

- X10 (DII index-futures long share LEVEL (discovery-window terciles)): KW p whole 0.034, discovery 0.457, second half 0.017; Welch high vs low diff -26.5 pts (p 0.137; n 143 vs 48).

- X13 (FII index-options stance, 1-session change sign (up = more put-heavy)): KW p whole 0.082, discovery 0.730, second half 0.046; Welch up vs down diff 10.5 pts (p 0.380; n 93 vs 164).

- 1 of 19 testable KW tests are below 0.05 in the whole sample (expected about 1.0 by chance).

**G1-C calls (235)**

- H13 (Global risk: risk-on = US up & Asia not down; risk-off = US down & Asia not up): KW p whole 0.093, discovery 0.436, second half 0.168; Welch risk_on vs risk_off diff -17.7 pts (p 0.231; n 69 vs 52).

- X04 (US VIX previous-session rise >= +10 % (spike)): KW p whole 0.006, discovery 0.116, second half 0.018; Welch spike vs no_spike diff 41.2 pts (p 0.036; n 23 vs 191).

- X07 (Sector leadership: Nifty Bank minus Nifty 50 previous day (+/-0.3 pts)): KW p whole 0.543, discovery 0.382, second half 0.977; Welch bank_leads vs bank_lags diff 34.0 pts (p 0.021; n 60 vs 55).

- X08 (FII index-futures long share LEVEL (terciles of session days 2024-10..2025-09)): KW p whole 0.003, discovery <0.001, second half 0.584; Welch high vs low diff -22.1 pts (p 0.009; n 37 vs 129).

- 2 of 19 testable KW tests are below 0.05 in the whole sample (expected about 1.0 by chance).

**XP straddle (107)**

- 0 of 16 testable KW tests are below 0.05 in the whole sample (expected about 0.8 by chance).

Notes on those: G1 puts, DII level p 0.034 is a time effect (the 'low' DII class exists only in discovery); G1 and G1-F share the both-buying signal (G1-F is a subset of G1); G1-C FII-level p 0.003 is likewise a time effect (the 'high' class has 37 trades, all in discovery, mean -37.5 %, and does not exist in the second half); G1-C VIX-spike: calls +25.9 % on 23 spike trades vs -15.3 % on 191 others, second half +43.2 % (n 12) vs -24.2 %: same direction in both halves, small cell, and the opposite sign to G1-F puts (spike: +0.3 % vs +19.7 %); XP: nothing.

## 7. Confounding checks

`context_checks.csv` gives the mean previous-session NIFTY return of each class (G1-F). Breadth is largely the previous-day market direction (high breadth classes follow +0.48 % NIFTY days, low breadth follows -0.46 % days), so a breadth result is a previous-day direction result. FII/DII both-buying does not follow a particularly up day (+0.07 % vs +0.02 %), so that cell is not explained by the previous day's direction. Sector leadership is unrelated to previous-day direction in size.

## 8. What is impossible or too weak to establish

- FII/DII cash: only 59 G1-F trades have a value, all in Dec 2025 to Oct 2026 (September 2026 missing at source); the data are third party and verified on a single day; 'both selling' never occurs for G1-F (0 trades), so only two classes can be compared.

- Participant-OI level classes drift: with terciles fixed on 2024-10..2025-09, the second half falls almost entirely into one class (e.g. FII option stance 77 of 79 'high'), so level consistency is untestable; changes (signs) are testable.

- Asia pre-entry needs both Nikkei and Hang Seng to be open: 21 G1-F trades are missing. USD/INR needs the hourly series (from 2024-11-18).

- Events: RBI (13), FOMC (16), Budget (2), one US election date; in G1-F the event cells hold 6, 12 and 8 trades whole and under 10 in each half. No other election, CPI, GDP or geopolitical date exists locally and none was invented. GDELT is a global machine score; whether the stored values equal what was visible at 05:30 IST is unknown.

- No hypothesis can say 'the cause' of good and bad periods: with 154 trades and several of the conditions moving together, these tests have little power; absence of significance is not evidence of no effect.

## 9. Files

`external_features.csv` (one row per strategy-trade, all features, class, publication note), `availability_table.md`, `external_tables.csv`, `external_tests.csv`, `external_consistency.csv`, `external_level_cuts.csv`, `context_checks.csv`, `data_checks.txt`, scripts `build_features.py`, `analyse_external.py`, `context_checks.py`, `build_draft.py`, `make_hashes.py`, `hashes.txt`. `superseded_v1/` holds an earlier run that used the older local files and different class definitions; it is not used.
