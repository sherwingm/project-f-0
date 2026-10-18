# S2 screen B · results

Stock-level screens, short direction (not trades). strategies/S2_put_screens_B.md + addendum 2026-10-18. Pass: N >= 100 and >= 60 dates, t >= 3 (smaller of date / week clustered), mean >= +0.6 %, positive in >= 5 of 6 years incl. 2025 and 2026 (§6: 4 of 5, 2022-26), robust without the 5 biggest dates, the largest stock, and the S2 step-1 signals. Because S2 step 2 failed, a pass needs a mean >= +1.0 % to get a put backtest.

Pass tests: 10 rows; passing: 0.

## Pass tests

| screen | cell | h | PASS | failed | N | G | mean | median | hit % | t (min of date / week) | years positive | 2021 mean | 2022 mean | 2023 mean | 2024 mean | 2025 mean | 2026 mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| §1 parent indicator | P1 k=1 |  |  | not run: external-series check failed |  |  |  |  |  |  |  |  |  |  |  |  |  |
| §1 parent indicator | P2 k=5 |  |  | not run: external-series check failed |  |  |  |  |  |  |  |  |  |  |  |  |  |
| §2 market backdrop | F1-F3 |  |  | not run: external-series check failed |  |  |  |  |  |  |  |  |  |  |  |  |  |
| §3 sector rotation | R1 R (W -2 %, R +8 %) | 1 |  | t >= 3, mean >= 0.6, years, robust | 139 | 120 | 0.184 | 0.316 | 57.6 | 1.057 | 3 | 0.298 | -0.293 | -0.159 | 0.448 | -0.214 | 0.567 |
| §3 sector rotation | R2 R (W -2 %, R +8 %) | 3 |  | t >= 3, mean >= 0.6, years, robust | 139 | 120 | -0.161 | -0.307 | 46.8 | -0.49 | 3 | -1.314 | 0.232 | -0.153 | 0.163 | -0.024 | 0.137 |
| §4 gap fill | G1 | 1 |  | t >= 3, mean >= 0.6, robust, 0.35 % haircut | 1,133 | 644 | 0.437 | 0.856 | 58.7 | 2.379 | 6 | 0.624 | 0.079 | 0.023 | 0.556 | 0.668 | 0.295 |
| §4 gap fill | G2 | 1 |  | t >= 3, mean >= 0.6, years, robust, 0.35 % haircut | 439 | 321 | 0.527 | 1.125 | 59.7 | 1.655 | 4 | 0.415 | -0.351 | -0.154 | 1.109 | 1.216 | 0.005 |
| §4 gap fill | G3 | 1 |  | t >= 3, years, robust, 0.35 % haircut | 299 | 228 | 0.633 | 1.415 | 59.2 | 1.464 | 5 | 1.02 | 0.648 | 0.461 | 0.417 | 0.726 | -0.314 |
| §5 weak results | W1 weak, not yet fallen (pre5 >= 0) | 3 |  | t >= 3, mean >= 0.6, years, robust | 191 | 146 | -0.566 | -0.699 | 45 | -1.723 | 1 |  | -0.071 | -1.013 | 0.609 | -0.729 | -1.051 |
| §5 weak results | W1 weak, not yet fallen (pre5 >= 0) | 5 |  | t >= 3, mean >= 0.6, years, robust | 190 | 145 | -0.528 | -0.452 | 45.8 | -1.371 | 2 |  | 0.851 | -1.155 | 0.445 | -0.525 | -1.218 |

## Run notes

```
{
 "\u00a71 and \u00a72": {
  "aborted": "the daily / 1h date check failed (spec: the run aborts)",
  "% of days within 0.5 %": {
   "BZ=F": 92.8,
   "HG=F": 82.1,
   "ALI=F": 42.2,
   "INFY": 100.0
  }
 },
 "\u00a73": {
  "R (W -2 %, R +8 %)": 139,
  "W -2 %, R +10 %": 99,
  "W -3 %, R +8 %": 86,
  "infrastructure, W -2 %, R +8 %": 102
 },
 "\u00a74": {
  "events (G >= 2 %)": 1179
 },
 "\u00a75": {
  "weak events": 456,
  "drops": {
   "period not parsed": 32,
   "period disagrees": 2,
   "as-filed rule": 47,
   "no numbers / base <= 0": 521,
   "not weak": 2186,
   "outside universe or prices": 97
  }
 },
 "\u00a76": {
  "order-win events": 761
 }
}
```

## Gate 4 recount (events, no returns)

| cell | N | dates | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | drops |
|---|---|---|---|---|---|---|---|---|---|
| §1 P1 k=1 (shock dates) | 1145 | 280 | 36 | 54 | 53 | 47 | 47 | 43 |  |
| §1 P2 k=5 (shock dates) | 859 | 152 | 21 | 28 | 22 | 30 | 26 | 25 |  |
| §2 F0 base | 943 | 579 | 109 | 177 | 163 | 178 | 178 | 138 |  |
| §2 F1 BRENT_UP5 (on) | 478 | 291 | 67 | 101 | 90 | 89 | 60 | 71 |  |
| §2 F2 US_OVERNIGHT_DOWN (on) | 444 | 273 | 52 | 109 | 72 | 72 | 75 | 64 |  |
| §2 F3 NIFTY_DOWNTREND (on) | 368 | 218 | 26 | 73 | 59 | 51 | 87 | 72 |  |
| §3 R1/R2 rotation | 139 | 120 | 27 | 26 | 8 | 25 | 19 | 34 |  |
| §4 G1 | 1139 | 647 | 253 | 122 | 170 | 223 | 247 | 124 |  |
| §4 G2 | 440 | 322 | 109 | 42 | 71 | 81 | 101 | 36 |  |
| §4 G3 | 299 | 228 | 103 | 21 | 47 | 65 | 40 | 23 |  |
| §5 W1 weak, pre5 >= 0 | 191 | 146 | 0 | 19 | 41 | 34 | 50 | 47 | {"period not parsed": 32, "period disagrees": 2, "as-filed rule": 47, "no numbers / base <= 0": 521, "not weak": 2186, "outside universe or prices": 97} |
| §6 O1 order hype (DIST20 >= 5 %, RUN20 >= 10 %) | 50 | 48 | 0 | 8 | 12 | 19 | 5 | 6 |  |
| §6 O2 order pile-up (N60 >= 3, DIST20 >= 5 %) | 36 | 36 | 0 | 4 | 7 | 17 | 6 | 2 |  |

## Every row (pass tests and descriptive)

| screen | cell | h | PASS | failed | N | G | mean | median | hit % | t (min of date / week) | years positive | 2021 mean | 2022 mean | 2023 mean | 2024 mean | 2025 mean | 2026 mean | role |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| §1 parent indicator | P1 k=1 |  |  | not run: external-series check failed |  |  |  |  |  |  |  |  |  |  |  |  |  | pass test |
| §1 parent indicator | P2 k=5 |  |  | not run: external-series check failed |  |  |  |  |  |  |  |  |  |  |  |  |  | pass test |
| §2 market backdrop | F1-F3 |  |  | not run: external-series check failed |  |  |  |  |  |  |  |  |  |  |  |  |  | pass test |
| §3 sector rotation | R1 R (W -2 %, R +8 %) | 1 |  | t >= 3, mean >= 0.6, years, robust | 139 | 120 | 0.184 | 0.316 | 57.6 | 1.057 | 3 | 0.298 | -0.293 | -0.159 | 0.448 | -0.214 | 0.567 | pass test |
| §3 sector rotation | R2 R (W -2 %, R +8 %) | 3 |  | t >= 3, mean >= 0.6, years, robust | 139 | 120 | -0.161 | -0.307 | 46.8 | -0.49 | 3 | -1.314 | 0.232 | -0.153 | 0.163 | -0.024 | 0.137 | pass test |
| §3 sector rotation | R (W -2 %, R +8 %) | 5 |  | t >= 3, mean >= 0.6, years, robust | 139 | 120 | -0.092 | 0.697 | 54.7 | -0.203 | 3 | -2.173 | 1.087 | -1.454 | -0.303 | 0.617 | 0.738 | descriptive |
| §3 sector rotation | W -2 %, R +10 % | 1 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 99 | 89 | 0.176 | 0.355 | 59.6 | 0.847 | 3 | 0.368 | -0.445 | -0.183 | 0.496 | -0.307 | 0.559 | descriptive |
| §3 sector rotation | W -2 %, R +10 % | 3 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 99 | 89 | -0.203 | -0.304 | 46.5 | -0.493 | 2 | -0.888 | 0.312 | -0.065 | -0.585 | -0.464 | 0.313 | descriptive |
| §3 sector rotation | W -2 %, R +10 % | 5 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 99 | 89 | -0.232 | 0.283 | 53.5 | -0.45 | 3 | -1.977 | 0.8 | -1.468 | -0.501 | 0.038 | 0.905 | descriptive |
| §3 sector rotation | W -3 %, R +8 % | 1 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 86 | 75 | -0.205 | 0.043 | 50 | -0.643 | 2 | 0.124 | -0.689 | -0.439 | -0.483 | -0.104 | 0.028 | descriptive |
| §3 sector rotation | W -3 %, R +8 % | 3 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 86 | 75 | -0.202 | 0.18 | 51.2 | -0.421 | 2 | -0.523 | -0.003 | -1.6 | -0.573 | 0.326 | 0.249 | descriptive |
| §3 sector rotation | W -3 %, R +8 % | 5 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 86 | 75 | 0.268 | 1.179 | 60.5 | 0.408 | 4 | -0.906 | 0.822 | 1.433 | -0.529 | 1.373 | 1.053 | descriptive |
| §3 sector rotation | infrastructure, W -2 %, R +8 % | 1 |  | t >= 3, mean >= 0.6, years, robust | 102 | 88 | -0.104 | 0.346 | 56.9 | -0.352 | 3 | 0.284 | 0.794 | -0.629 | -0.952 | -0.325 | 0.127 | descriptive |
| §3 sector rotation | infrastructure, W -2 %, R +8 % | 3 |  | t >= 3, mean >= 0.6, years, robust | 102 | 88 | -0.597 | -0.385 | 46.1 | -1.201 | 2 | 0.442 | 2.346 | -2.26 | -3.024 | -1.177 | -0.092 | descriptive |
| §3 sector rotation | infrastructure, W -2 %, R +8 % | 5 |  | t >= 3, mean >= 0.6, years, robust | 102 | 88 | -1.555 | -1.229 | 43.1 | -2.34 | 1 | -1.507 | 2.043 | -2.2 | -4.332 | -2.605 | -0.191 | descriptive |
| §4 gap fill | G1 | 0 |  | mean >= 0.6, robust | 1,134 | 645 | 0.537 | 0.878 | 60 | 3.451 | 6 | 0.744 | 0.001 | 0.206 | 0.877 | 0.704 | 0.147 | descriptive |
| §4 gap fill | G1 | 1 |  | t >= 3, mean >= 0.6, robust, 0.35 % haircut | 1,133 | 644 | 0.437 | 0.856 | 58.7 | 2.379 | 6 | 0.624 | 0.079 | 0.023 | 0.556 | 0.668 | 0.295 | pass test |
| §4 gap fill | G1 (cost 0.35 %) | 1 |  | t >= 3, mean >= 0.6, years, robust | 1,133 | 644 | 0.187 | 0.606 | 55.7 | 1.019 | 4 | 0.374 | -0.171 | -0.227 | 0.306 | 0.418 | 0.045 | haircut check |
| §4 gap fill | G1 | 3 |  | t >= 3, mean >= 0.6, robust | 1,133 | 644 | 0.354 | 0.544 | 54.6 | 1.445 | 6 | 0.498 | 0.083 | 0.132 | 0.331 | 0.309 | 0.761 | descriptive |
| §4 gap fill | G2 | 0 |  | t >= 3, years, robust | 439 | 321 | 0.603 | 1.257 | 62.4 | 1.966 | 4 | 0.326 | -0.58 | -0.513 | 1.901 | 1.245 | 0.341 | descriptive |
| §4 gap fill | G2 | 1 |  | t >= 3, mean >= 0.6, years, robust, 0.35 % haircut | 439 | 321 | 0.527 | 1.125 | 59.7 | 1.655 | 4 | 0.415 | -0.351 | -0.154 | 1.109 | 1.216 | 0.005 | pass test |
| §4 gap fill | G2 (cost 0.35 %) | 1 |  | t >= 3, mean >= 0.6, years, robust | 439 | 321 | 0.277 | 0.875 | 57.9 | 0.87 | 3 | 0.165 | -0.601 | -0.404 | 0.859 | 0.966 | -0.245 | haircut check |
| §4 gap fill | G2 | 3 |  | t >= 3, mean >= 0.6, robust | 439 | 321 | 0.564 | 0.762 | 55.6 | 1.291 | 5 | 0.246 | -0.784 | 0.355 | 1.166 | 1.336 | 0.01 | descriptive |
| §4 gap fill | G3 | 0 |  | t >= 3, robust | 299 | 228 | 0.776 | 1.259 | 64.2 | 2.603 | 6 | 0.911 | 0.658 | 0.459 | 0.798 | 1.178 | 0.159 | descriptive |
| §4 gap fill | G3 | 1 |  | t >= 3, years, robust, 0.35 % haircut | 299 | 228 | 0.633 | 1.415 | 59.2 | 1.464 | 5 | 1.02 | 0.648 | 0.461 | 0.417 | 0.726 | -0.314 | pass test |
| §4 gap fill | G3 (cost 0.35 %) | 1 |  | t >= 3, mean >= 0.6, years, robust | 299 | 228 | 0.383 | 1.165 | 57.2 | 0.886 | 5 | 0.77 | 0.398 | 0.211 | 0.167 | 0.476 | -0.564 | haircut check |
| §4 gap fill | G3 | 3 |  | t >= 3, robust | 299 | 228 | 0.758 | 1.144 | 58.9 | 1.351 | 5 | 1.429 | 0.13 | -0.266 | 0.649 | 0.474 | 1.217 | descriptive |
| §4 gap fill | G5 (descriptive) | 0 |  | t >= 3, mean >= 0.6, years, robust | 108 | 95 | 0.54 | 1.694 | 62 | 0.68 | 4 | -1.153 | -0.918 | 1.561 | 2.022 | 1.012 | 2.064 | descriptive |
| §4 gap fill | G5 (descriptive) | 1 |  | t >= 3, years, robust | 108 | 95 | 0.705 | 0.483 | 54.6 | 1.008 | 4 | -0.562 | -1.025 | 1.659 | 0.996 | 1.562 | 2.464 | descriptive |
| §4 gap fill | G5 (descriptive) | 3 |  | t >= 3, mean >= 0.6, years, robust | 108 | 95 | 0.35 | 0.064 | 50.9 | 0.511 | 4 | -1.3 | -1.863 | 1.713 | 1.054 | 1.075 | 2.607 | descriptive |
| §5 weak results | W1 weak, not yet fallen (pre5 >= 0) | 0 |  | t >= 3, mean >= 0.6, years, robust | 191 | 146 | -0.256 | -0.139 | 47.6 | -1.328 | 2 |  | 1.141 | -0.384 | 0.072 | -0.801 | -0.365 | descriptive |
| §5 weak results | W1 weak, not yet fallen (pre5 >= 0) | 1 |  | t >= 3, mean >= 0.6, years, robust | 191 | 146 | -0.391 | -0.011 | 49.7 | -1.701 | 2 |  | 0.465 | -0.754 | 0.386 | -0.846 | -0.498 | descriptive |
| §5 weak results | W1 weak, not yet fallen (pre5 >= 0) | 3 |  | t >= 3, mean >= 0.6, years, robust | 191 | 146 | -0.566 | -0.699 | 45 | -1.723 | 1 |  | -0.071 | -1.013 | 0.609 | -0.729 | -1.051 | pass test |
| §5 weak results | W1 weak, not yet fallen (pre5 >= 0) | 5 |  | t >= 3, mean >= 0.6, years, robust | 190 | 145 | -0.528 | -0.452 | 45.8 | -1.371 | 2 |  | 0.851 | -1.155 | 0.445 | -0.525 | -1.218 | pass test |
| §5 weak results | control: weak, already fell (pre5 < 0) | 0 |  | t >= 3, mean >= 0.6, years, robust | 256 | 168 | -0.785 | -0.911 | 36.3 | -3.556 | 0 |  | -1.29 | -0.438 | -0.742 | -0.737 | -0.818 | descriptive |
| §5 weak results | control: weak, already fell (pre5 < 0) | 1 |  | t >= 3, mean >= 0.6, years, robust | 256 | 168 | -0.92 | -1.044 | 43 | -2.836 | 0 |  | -1.594 | -0.196 | -0.751 | -1.094 | -1.05 | descriptive |
| §5 weak results | control: weak, already fell (pre5 < 0) | 3 |  | t >= 3, mean >= 0.6, years, robust | 253 | 167 | -1.185 | -1.292 | 36.8 | -3.123 | 0 |  | -1.727 | -0.336 | -1.109 | -1.562 | -1.186 | descriptive |
| §5 weak results | control: weak, already fell (pre5 < 0) | 5 |  | t >= 3, mean >= 0.6, years, robust | 256 | 168 | -1.319 | -1.423 | 37.9 | -3.173 | 1 |  | 0.14 | -0.874 | -1.512 | -2.354 | -1.528 | descriptive |
| §5 weak results | pre10 >= 0 | 3 |  | t >= 3, mean >= 0.6, years, robust | 182 | 137 | -0.372 | -0.335 | 47.3 | -1.102 | 1 |  | -0.821 | -0.271 | 0.61 | -0.75 | -0.661 | descriptive |
| §5 weak results | pre10 >= 0 | 5 |  | t >= 3, mean >= 0.6, years, robust | 181 | 136 | -0.463 | -0.23 | 46.4 | -1.205 | 1 |  | -0.51 | -0.479 | 0.747 | -0.882 | -1.001 | descriptive |
| §5 weak results | S1 v9 core (YoY < -10, QoQ < 0), pre5 >= 0 | 3 |  | t >= 3, mean >= 0.6, years, robust | 106 | 90 | -0.459 | -0.143 | 48.1 | -1.043 | 1 |  | -0.883 | -0.226 | 0.188 | -0.276 | -1.003 | descriptive |
| §5 weak results | S1 v9 core (YoY < -10, QoQ < 0), pre5 >= 0 | 5 |  | t >= 3, mean >= 0.6, years, robust | 105 | 89 | -0.244 | -0.637 | 46.7 | -0.498 | 3 |  | 0.088 | -0.331 | 0.326 | 0.542 | -1.177 | descriptive |
| §6 order-book hype | O1 order hype (DIST20 >= 5 %, RUN20 >= 10 %) | 0 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 50 | 48 | 0.309 | 0.404 | 62 | 0.963 | 3 |  | -0.037 | -0.221 | 0.443 | 0.965 | 0.862 | descriptive |
| §6 order-book hype | O1 order hype (DIST20 >= 5 %, RUN20 >= 10 %) | 1 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 50 | 48 | 0.055 | 0.334 | 56 | 0.106 | 2 |  | -0.141 | -1.456 | 1.067 | -0.386 | 0.505 | descriptive |
| §6 order-book hype | O1 order hype (DIST20 >= 5 %, RUN20 >= 10 %) | 3 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 50 | 48 | 0.396 | 0.184 | 54 | 0.569 | 3 |  | -0.545 | -1.762 | 2.146 | 0.508 | 0.332 | descriptive (below N 100 at the recount) |
| §6 order-book hype | O1 order hype (DIST20 >= 5 %, RUN20 >= 10 %) | 5 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 50 | 48 | -0.127 | 0.213 | 52 | -0.154 | 3 |  | -1.965 | -3.685 | 2.313 | 1.521 | 0.335 | descriptive (below N 100 at the recount) |
| §6 order-book hype | O2 order pile-up (N60 >= 3, DIST20 >= 5 %) | 0 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 36 | 36 | 0.325 | 0.403 | 58.3 | 1.042 | 4 |  | 0.316 | 0.937 | 0.098 | 0.375 | -0.023 | descriptive |
| §6 order-book hype | O2 order pile-up (N60 >= 3, DIST20 >= 5 %) | 1 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 36 | 36 | 0.165 | 0.044 | 50 | 0.273 | 2 |  | 1.11 | -0.487 | 0.445 | -0.191 | -0.76 | descriptive |
| §6 order-book hype | O2 order pile-up (N60 >= 3, DIST20 >= 5 %) | 3 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 36 | 36 | 0.319 | 0.014 | 50 | 0.428 | 2 |  | 0.569 | -0.557 | 1.243 | -0.201 | -3.409 | descriptive (below N 100 at the recount) |
| §6 order-book hype | O2 order pile-up (N60 >= 3, DIST20 >= 5 %) | 5 |  | N and dates, t >= 3, years, robust | 36 | 36 | 0.733 | 0.322 | 58.3 | 0.857 | 2 |  | -0.929 | -0.562 | 2.245 | 0.048 | -2.209 | descriptive (below N 100 at the recount) |
| §6 order-book hype | every order win (descriptive) | 0 |  | t >= 3, mean >= 0.6, years, robust | 563 | 427 | -0.075 | -0.058 | 49.4 | -0.924 | 2 |  | -0.245 | -0.156 | 0.033 | 0.128 | -0.474 | descriptive |
| §6 order-book hype | every order win (descriptive) | 1 |  | t >= 3, mean >= 0.6, years, robust | 563 | 427 | -0.021 | 0.164 | 53.8 | -0.159 | 2 |  | -0.133 | -0.4 | 0.172 | 0.237 | -0.452 | descriptive |
| §6 order-book hype | every order win (descriptive) | 3 |  | t >= 3, mean >= 0.6, years, robust | 561 | 426 | -0.133 | -0.02 | 49.7 | -0.727 | 2 |  | -0.68 | -0.592 | 0.224 | 0.193 | -0.508 | descriptive |
| §6 order-book hype | every order win (descriptive) | 5 |  | t >= 3, mean >= 0.6, years, robust | 563 | 427 | -0.348 | -0.293 | 46.7 | -1.517 | 2 |  | -0.527 | -1.279 | 0.054 | 0.171 | -0.708 | descriptive |
| §6 order-book hype | order value >= 5 % of revenue (descriptive) | 0 |  | N and dates, t >= 3, years, robust | 11 | 11 | 1.102 | 1.35 | 72.7 | 2.285 | 2 |  |  | 2.11 | -0.215 | 0.036 | -0.2 | descriptive |
| §6 order-book hype | order value >= 5 % of revenue (descriptive) | 1 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 11 | 11 | 0.418 | 1.636 | 54.5 | 0.38 | 2 |  |  | 1.991 | 1.636 | -1.12 | -3.373 | descriptive |
| §6 order-book hype | order value >= 5 % of revenue (descriptive) | 3 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 11 | 11 | -1.568 | -1.471 | 36.4 | -1.255 | 1 |  |  | -0.123 | 0.649 | -3.021 | -5.561 | descriptive |
| §6 order-book hype | order value >= 5 % of revenue (descriptive) | 5 |  | N and dates, t >= 3, mean >= 0.6, years, robust | 11 | 11 | -1.104 | -1.324 | 36.4 | -0.703 | 2 |  |  | 0.505 | 4.633 | -3.401 | -6.502 | descriptive |
| §6 order-book hype | every order win: NBCC | 5 |  | t >= 3, years, robust | 20 | 20 | 2.075 | 2.417 | 60 | 1.95 | 3 |  | 0.025 |  |  | 1.254 | 5.015 | descriptive |
| §6 order-book hype | every order win: LT | 5 |  | t >= 3, mean >= 0.6, years, robust | 68 | 68 | -0.327 | -0.33 | 45.6 | -0.731 | 1 |  | -0.324 | -1.006 | -0.207 | 0.699 |  | descriptive |
| §6 order-book hype | every order win: RVNL | 5 |  | t >= 3, years, robust | 1 | 1 | 2.722 | 2.722 | 100 |  | 1 |  |  |  |  | 2.722 |  | descriptive |
| §6 order-book hype | every order win: BEL | 5 |  | t >= 3, mean >= 0.6, years, robust | 21 | 21 | -2.226 | -2.921 | 33.3 | -1.967 | 0 |  | -5.874 | -0.541 | -1.141 | -3.335 | -6.064 | descriptive |
| §6 order-book hype | every order win: HAL | 5 |  | t >= 3, mean >= 0.6, years, robust | 18 | 18 | -0.962 | -1.101 | 50 | -0.979 | 1 |  | -0.347 | -1.816 | -2.39 |  | 2.643 | descriptive |
| §6 order-book hype | every order win: BHEL | 5 |  | t >= 3, mean >= 0.6, years, robust | 29 | 29 | -0.94 | 0.101 | 51.7 | -0.633 | 1 |  | -3.038 | -5.319 | 1.731 | -1.102 |  | descriptive |
| §6 order-book hype | every order win: SUZLON | 5 |  | t >= 3, mean >= 0.6, years, robust | 5 | 5 | -2.114 | -0.872 | 20 | -1.35 | 0 |  |  |  |  | -1.151 | -2.756 | descriptive |
