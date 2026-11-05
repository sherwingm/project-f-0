# Expiry calendar analysis

Built 2026-11-04 by `scripts/build_calendar.py` (stdout in `results/audit/build_calendar_stdout.txt`); checked
by `tests/test_calendar.py` (11 tests, all pass). Design: `reports/lld/audit_calendar.md`.

## Section 1: Calendar

### 1.1 How the calendar is built
- **NIFTY, BANKNIFTY:** from the bhavcopy. An expiry date is real when contracts with that `XpryDt` traded on a
  day whose `TradDt` equals the `XpryDt`. This holds for every date up to the last stored session except 35
  "ghost" dates: contracts the exchange re-dated, which trade under the old date until the re-dating day and
  under the new date from the next session (`data/expiry_relabels.csv`). Each ghost links to the date its
  contracts moved to; none is left unlinked.
- **SENSEX:** from the `options_1m/SENSEX` folder names (BSE bhavcopy is not stored). Real when the folder's
  last day file is the folder date. SENSEX history starts 2024-10-04.
- **kind:** monthly = the expiry on the last official monthly weekday of the month, moved back to the previous
  session if that day was a holiday; all others weekly. This matches futures presence on every one of the 212
  NSE monthlies (futures exist on monthlies only). The plain "last expiry of the month" rule fails in 3 months
  (BANKNIFTY 2024-01 and 2024-04, NIFTY 2025-04: a weekly falls after the monthly in the same month), so it is
  kept only as the column `last_in_month`. `is_quarterly` = monthly in Mar/Jun/Sep/Dec.
- **Shifted:** weekday differs from the official regime. Reason: *holiday* (the regime day is in no dataset, the
  expiry is the session before), *special session* (the regime day was a Diwali Muhurat session, so the expiry is
  the full session before), or *unexplained*. There are no unexplained shifts.

Files: `data/expiry_calendar.csv` (948 rows: 906 expired, 1 expired_unverified, 41 future_listed),
`data/sessions_{NIFTY,BANKNIFTY,SENSEX}.csv`, `data/special_sessions.csv`, `data/expiry_missing.csv`,
`results/audit/calendar_counts.csv`, `results/audit/calendar_checks.csv`.

### 1.2 Counts per year (`results/audit/calendar_counts.csv`)
| Year | NIFTY weekly | NIFTY monthly | BANKNIFTY weekly | BANKNIFTY monthly | SENSEX weekly | SENSEX monthly |
|---|---|---|---|---|---|---|
| 2018 | 0 | 12 | 40 | 12 | – | – |
| 2019 | 35 | 12 | 40 | 12 | – | – |
| 2020 | 41 | 12 | 41 | 12 | – | – |
| 2021 | 40 | 12 | 40 | 12 | – | – |
| 2022 | 40 | 12 | 40 | 12 | – | – |
| 2023 | 40 | 12 | 40 | 12 | – | – |
| 2024 | 40 | 12 | 36 | 12 | 10* | 2* |
| 2025 | 41 | 12 | 0 | 12 | 40 | 12 |
| 2026 (to 29 Oct) | 33 | 10 | 0 | 10 | 34 | 10 |

\* SENSEX 2024 covers 2024-10-04 → 12-27 only, and the 2024-10-25 expiry (weekly and October monthly) is not in
the store. The 2026 SENSEX monthly count includes 2026-10-29, whose folder lacks the expiry-day file.

Totals: NIFTY 310 weekly + 106 monthly; BANKNIFTY 277 weekly + 106 monthly; SENSEX 84 weekly + 24 monthly.

### 1.3 Weekday regimes, checked against official notices
"Re-dated in data" is the last `TradDt` of the old ghost dates, i.e. the evening the exchange changed the contract
file. O = official exchange/SEBI document read; S = secondary report (broker/news) only.

| Underlying | Kind | Expiry dates | Weekday | Source | Re-dated in data |
|---|---|---|---|---|---|
| NIFTY | monthly | → 2025-08-28 | last Thursday | contract spec; NSE/FAOP/68747 (O) | – |
| NIFTY | weekly | 2019-02-14 → 2025-08-21 | Thursday | NSE launch 11-Feb-2019 (S) | first weekly in data 2019-02-14 |
| NIFTY | weekly + monthly | 2025-09-02 → | Tuesday (monthly last Tuesday) | NSE/FAOP/68685, 23-Jun-2025 and 68747, 25-Jun-2025 (O); SEBI CIR/2025/76, 26-May-2025 (S) | long-dated re-dated 2025-07-31 EOD, as 68747 says |
| BANKNIFTY | weekly | → 2023-08-31 | Thursday | NSE/FAOP/57540 (O) | – |
| BANKNIFTY | weekly | 2023-09-06 → 2024-11-13 | Wednesday | NSE/FAOP/57540, 12-Jul-2023 (O) | 2023-09-01 EOD, as the circular says |
| BANKNIFTY | weekly | none after 2024-11-13 | – | SEBI CIR/2024/132, 1-Oct-2024 (O, number and date); NSE notice Oct-2024 (S) | last weekly 2024-11-13 |
| BANKNIFTY | monthly | → 2024-02-29 | last Thursday | NSE/FAOP/60011 (O) | – |
| BANKNIFTY | monthly | 2024-03-27 → 2024-12-24 | last Wednesday | NSE/FAOP/60011, 28-Dec-2023 (O) | 2024-02-29 EOD, as the circular says |
| BANKNIFTY | monthly | 2025-01-30 → 2025-08-28 | last Thursday | NSE/FAOP/65336, 29-Nov-2024 (O) | 2025-01-01 EOD, as the circular says |
| BANKNIFTY | monthly | 2025-09-30 → | last Tuesday | NSE/FAOP/68685 + 68747 (O) | 2025-07-31 EOD |
| SENSEX | weekly + monthly | 2024-10-04 → 2025-01-03 | Friday (monthly last Friday) | BSE notice 28-Nov-2024 (S) | – |
| SENSEX | weekly + monthly | 2025-01-07 → 2025-08-26 | Tuesday | BSE notice 28-Nov-2024 (S); 3-Jan-2025 kept Friday | first Tuesday in data 2025-01-07 |
| SENSEX | weekly + monthly | 2025-09-04 → | Thursday | SEBI CIR/2025/76 + BSE notice Jun-2025 (S) | first Thursday in data 2025-09-04 |

Not implemented: NSE/FAOP/66938 (4-Mar-2025, O) moved all NSE expiries to Monday from 4-Apr-2025. It was deferred
after the SEBI consultation of 27-Mar-2025 (S). The data agrees: April-May 2025 NIFTY expiries stay on Thursday
(Wednesday on holiday weeks) and no contract was re-dated to a Monday.

Every date in the annexures of 65336 and 68747 matches the data (e.g. BANKNIFTY 29-Jan-25 → 30-Jan-25,
31-Dec-25 → 24-Dec-25 → 30-Dec-25; NIFTY quarterly 25-Sep-25 → 30-Sep-25, 26-Mar-26 → 31-Mar-26).

### 1.4 Shifted expiries (all explained)
| Underlying | Holiday shifts | Muhurat shifts | Dates (examples) |
|---|---|---|---|
| NIFTY | 19 | 2 | 2023-03-29 (Wed, 30 Mar holiday), 2025-04-30 (Wed, 1 May), 2026-03-30 (Mon, 31 Mar), Muhurat 2021-11-03, 2025-10-20 |
| BANKNIFTY | 21 | 1 | 2018-11-06 (Tue: Wed 7 Nov Muhurat, Thu 8 Nov holiday), 2024-12-24 (Tue, Christmas), Muhurat 2021-11-03 |
| SENSEX | 6 | 1 | 2024-11-14 (Thu, 15 Nov), 2025-12-24 (Wed), Muhurat 2024-10-31 (Thu; Fri 1 Nov Muhurat) |

Full list: `calendar_checks.csv` rows "shifted expiries". Six future listed expiries are on a Monday
(e.g. NIFTY 2026-11-09, 2026-11-23); their holidays lie after the last stored session and are not verified.

Holiday re-datings seen in the bhavcopy (old date traded until the evening shown):
2023-03-30 → 03-29 (re-dated 2022-12-21), 2023-06-29 → 06-28 (re-dated 2023-06-27, a late holiday change),
2026-03-31 → 03-30 (re-dated 2025-12-26). A model that trades before such a re-dating sees the old date; the
calendar holds final dates only (see the decision-time note in the LLD).

### 1.5 Weekly vs monthly, structure
- NIFTY 2018: monthlies only. Weekly NIFTY from 2019-02-14; 4-5 per month ever since.
- BANKNIFTY: weekly until 2024-11-13, monthly only from then. From Sep 2023 to Feb 2024 the weekly was Wednesday
  and the monthly Thursday, and no weekly was listed in a monthly-expiry week.
- Gaps > 8 days between expiries occur only where no weekly exists (NIFTY 2018, BANKNIFTY from Nov 2024), at the
  2018 Muhurat week, at the SENSEX 2025 Tuesday → Thursday switch (26 Aug → 4 Sep), and at the SENSEX gap
  (2024-10-18 → 10-31).

### 1.6 Mismatches and gaps
| # | What | Effect |
|---|---|---|
| 1 | SENSEX 2024-10-25 (weekly + October monthly) not stored | `data/expiry_missing.csv`; SENSEX tags blank 2024-10-04 (first row) → 2024-11-29 for monthly, 2024-10-18 → 10-31 for any expiry (`calendar_gap = True`) |
| 2 | SENSEX 2026-10-29 folder has no expiry-day file | status `expired_unverified` |
| 3 | NIFTY 2026-10-27 folder ends 2026-10-23 | the bhavcopy confirms the expiry; option minutes missing for 26-27 Oct |
| 4 | Muhurat-day shifts are not in any circular read | the data shows the expiry on the full session before; consistent with the "previous trading day" rule |
| 5 | NSE/FAOP/68685 said all existing contracts move on 28-Aug-2025; 68747 (two days later) kept contracts expiring by 31-Aug | data follows 68747 (28-Aug-2025 stayed Thursday) |
| 6 | Official text not read for NIFTY weekly launch, BANKNIFTY weekly discontinuation notice, BSE notices, and the 66938 deferral | NSE PDF downloads timed out; these rows rely on secondary reports, and the data agrees with each |

### 1.7 Session tags (`data/sessions_<UL>.csv`)
One row per session: NIFTY and BANKNIFTY 2,181 rows (2018-01-01 → 2026-10-29), SENSEX 513 rows (2024-10-04 →).
Columns: `next_expiry`, `sessions_to_next_expiry` (0 on an expiry day), `next_weekly`, `sessions_to_next_weekly`,
`next_monthly`, `sessions_to_next_monthly`, `last_expiry` (strictly before today), `sessions_since_last_expiry`
(1 on the day after an expiry), `cal_days_to_next_expiry`, `is_expiry_any/weekly/monthly`, `next_expiry_kind`,
`is_special_session`, `calendar_gap`. Sessions are counted on full sessions only (Muhurat rows have blank counts).
`sessions_to_next_weekly` skips monthlies; use `sessions_to_next_expiry` for "nearest expiry of any kind".
Counts to an expiry after 2026-10-29 are blank (sessions after it are not stored).

Known-from rule (added 2026-11-05 after the verifier review): on day d the `next_*` pointers use only expiries known
on d. `known_from` in `expiry_calendar.csv` is the bhavcopy `first_listed_seen` (for a re-dated expiry, the first day
its original contract was listed); it is blank for SENSEX folders and expiries.parquet rows, whose first stored day is
not a listing day. `next_expiry_known_from`, `next_weekly_known_from`, `next_monthly_known_from` record it per row.
Effect: NIFTY rows 2018-01-01 → 2019-02-08 no longer count down to 2019-02-14, the first NIFTY weekly, listed
2019-02-11 (274 weekly counts now blank); on 2019-02-01 → 02-08 (6 rows) the next expiry is 2019-02-28 (monthly).
No other row changed. The launch circular's date was not read (gap 6 above), so the listing day is used.

Sources (official): NSE circulars
[FAOP57540](https://archives.nseindia.com/content/circulars/FAOP57540.pdf),
[FAOP60011](https://archives.nseindia.com/content/circulars/FAOP60011.pdf),
[FAOP65336](https://archives.nseindia.com/content/circulars/FAOP65336.pdf),
[FAOP66938](https://archives.nseindia.com/content/circulars/FAOP66938.pdf),
[FAOP68685](https://archives.nseindia.com/content/circulars/FAOP68685.pdf),
[FAOP68747](https://archives.nseindia.com/content/circulars/FAOP68747.pdf);
[SEBI circular 1-Oct-2024](https://www.sebi.gov.in/legal/circulars/oct-2024/measures-to-strengthen-equity-index-derivatives-framework-for-increased-investor-protection-and-market-stability_87208.html).
Secondary: [Business Standard, NIFTY weekly launch](https://www.business-standard.com/amp/article/pti-stories/nse-launches-trading-in-weekly-options-on-nifty-50-index-119021101158_1.html),
[Zerodha bulletin, weekly discontinuation](https://zerodha.com/marketintel/bulletin/392870/discontinuation-of-weekly-derivatives-contracts-from-november-2024),
[Business Standard, BSE Jan-2025 change](https://www.business-standard.com/amp/markets/stock-market-news/sensex-bankex-sensex-50-expiry-days-to-change-from-january-1-bse-124112801317_1.html),
[Moneylife, NSE Tuesday / BSE Thursday](https://moneylife.in/article/nse-equity-fo-contracts-to-expire-on-tuesdays-bse-on-thursdays-from-1st-september/77434.html),
[Business Standard, Monday change deferred](https://www.business-standard.com/amp/markets/news/nse-defers-switching-to-monday-expiry-after-sebi-s-consultation-paper-125032800183_1.html),
[Taxscan, SEBI CIR/2025/76](https://www.taxscan.in/sebi-notifies-uniform-expiry-days-for-equity-derivatives-to-enhance-market-stability/522117).

## Section 2: behaviour by expiry type
Filled 2026-11-05 by the `gaps` module (Agent 1). Code `scripts/gaps_behaviour.py` (tables) and `scripts/gaps_discovery.py`
(tests, group B in `results/gaps/hypotheses.csv`); design `reports/lld/gaps.md`; full report
`reports/GAP_TRANSITION_ANALYSIS.md`. **Discovery rows only (sessions 2018-01-02 → 2022-12-30)**; validation numbers
are shown only for the frozen candidates. SENSEX is **Untestable** here: its calendar starts 2024-10-04 (sealed period).

### 2.1 Definitions
- Each row is a session, tagged from the calendar: D0 = expiry day, D-k = k sessions before the next expiry, D+1 =
  first session after an expiry. "Ordinary" = not D0, D-1 or D+1. In discovery every weekly expiry is a Thursday,
  so D0 / D-1 / D+1 are Thursday / Wednesday / Friday and ordinary days are mostly Monday and Tuesday (Monday carries
  the weekend gap). NIFTY 2018 (monthly expiries only) is the only stretch with non-expiry Thursdays.
- Metrics of the session: range = (high − low) / previous close; |cc|, |oc|, |gap| in %; big move = max excursion from
  the previous close ≥ 1 %; realised vol = root sum of squared 1-minute returns (%); minute of the high / low after
  09:15. Minute metrics exist only from 2021-10-20 (63 expiry days per index in discovery, 15 of them monthly).

### 2.2 Mean values by context (`results/gaps/behaviour_by_context.csv`)
| NIFTY | n | range | \|cc\| | \|oc\| | \|gap\| | big move | n min | rv | high min | low min |
|---|---|---|---|---|---|---|---|---|---|---|
| D-3 (Mon) | 163 | 1.36 | 1.05 | 0.76 | 0.63 | 58 % | 46 | 0.75 | 179 | 106 |
| D-2 (Tue) | 212 | 1.31 | 0.86 | 0.68 | 0.50 | 47 % | 61 | 0.74 | 216 | 150 |
| D-1 (Wed) | 215 | 1.29 | 0.76 | 0.71 | 0.43 | 45 % | 61 | 0.69 | 175 | 179 |
| D0 weekly | 156 | 1.23 | 0.83 | 0.67 | 0.52 | 46 % | 48 | 0.68 | 110 | 208 |
| D0 monthly | 60 | 1.21 | 0.87 | 0.63 | 0.49 | 50 % | 15 | 0.72 | 190 | 196 |
| D+1 (Fri) | 215 | 1.37 | 0.85 | 0.73 | 0.52 | 52 % | 62 | 0.76 | 139 | 205 |
| ordinary | 583 | 1.21 | 0.82 | 0.65 | 0.48 | 44 % | 107 | 0.74 | 200 | 131 |

| BANKNIFTY | n | range | \|cc\| | \|oc\| | \|gap\| | big move | n min | rv | high min | low min |
|---|---|---|---|---|---|---|---|---|---|---|
| D-3 (Mon) | 193 | 1.90 | 1.38 | 1.11 | 0.76 | 71 % | 46 | 1.04 | 185 | 112 |
| D-2 (Tue) | 256 | 1.78 | 1.05 | 0.90 | 0.61 | 66 % | 61 | 1.00 | 183 | 160 |
| D-1 (Wed) | 260 | 1.81 | 1.01 | 0.95 | 0.50 | 67 % | 61 | 0.94 | 185 | 153 |
| D0 weekly | 201 | 1.72 | 1.05 | 0.88 | 0.59 | 65 % | 48 | 0.96 | 139 | 179 |
| D0 monthly | 60 | 1.92 | 1.11 | 0.95 | 0.57 | 73 % | 15 | 0.98 | 213 | 168 |
| D+1 (Fri) | 259 | 1.90 | 1.15 | 0.98 | 0.60 | 70 % | 62 | 1.04 | 130 | 170 |
| ordinary | 449 | 1.83 | 1.19 | 0.99 | 0.67 | 68 % | 107 | 1.01 | 184 | 139 |
NIFTY "ordinary" also holds the 208 calm 2018 non-expiry days (range 1.00); its D-3/D-2/D-1 rows are weekly-regime
plus 13 monthly-only rows each. Confidence intervals for every cell are in the CSV (`_lo`, `_hi` columns).

### 2.3 Tests: expiry type vs ordinary sessions (group B, 83 of the module's 239 tests)
- **Expiry day is not a bigger day for the index.** D0 vs ordinary: range +0.02 % (NIFTY, p 0.83) and −0.07 %
  (BANKNIFTY, p 0.50); |cc|, |oc|, |gap|, big-move rate, realised vol all within noise (p ≥ 0.14).
- **D-1 and D+1:** NIFTY D+1 has a slightly wider range (1.37 vs 1.21 %, p 0.11) and more big moves (52 vs 44 %,
  p 0.052); BANKNIFTY D-1 has smaller |cc| (1.01 vs 1.19 %, p 0.065) and a smaller gap (0.50 vs 0.67 %, p 0.0015, BH
  q 0.09). That gap result is the Wednesday-vs-Monday weekend effect: frozen, it failed validation (−0.01 %, p 0.38)
  once BANKNIFTY's D-1 moved off Wednesday.
- **Time of high / low (minute, thin):** on NIFTY expiry days the high came early (mean minute 131 vs 198 on ordinary
  days, p 0.006) and the low late (203 vs 130, p 0.0014, q 0.09); D+1 looked the same (low 205 vs 130, q 0.09). Both
  "low later" results were frozen and failed validation (+21 min, p 0.15; +4 min, p 0.41); they reflect the falling
  market of 2022 (robustness: +89 / +78 min in 2022, negative in 2024). BANKNIFTY: D+1 high earlier (130 vs 182,
  p 0.023), not significant after BH.
- **Weekly vs monthly expiry day:** no difference in range (NIFTY 1.21 vs 1.23 %, p 0.85; BANKNIFTY 1.92 vs 1.72 %,
  p 0.33), |cc|, gap or big moves. On monthly expiry days one extreme was made in the last hour on 13 of 15 NIFTY days
  (87 % vs 47 % on weekly, p 0.007, q 0.22): 15 days, thin, Observed only.
- **Weekday control (NIFTY 2018, monthly-only):** non-expiry Thursdays were, if anything, quieter than other ordinary
  days (range 0.92 vs 1.03 %, p 0.13; |oc| 0.44 vs 0.59 %, p 0.019, q 0.33), and the 13 monthly expiry days of 2018
  had a range of 0.87 %. No sign of an expiry-day range premium there either.
- **High / low time of day** (`results/gaps/extreme_time_hist.csv`): on NIFTY expiry days the high fell in the first
  30 minutes on 49 % of minute days (25 % on D-2); the low fell in the last hour on 30 % (D-2: 25 %).

### 2.4 By weekday regime (`results/gaps/behaviour_by_regime.csv`)
Discovery holds only Thursday regimes: NIFTY monthly-only 2018 (13 expiry days) and NIFTY Thursday weekly; BANKNIFTY
Thursday weekly. The BANKNIFTY Wednesday regimes (2023-09 →) lie in validation and were used only in the robustness of
frozen candidates (where the D-1 gap effect vanished: −0.07 % and −0.005 %, n 17 and 26). So "expiry day" and
"Thursday" cannot be separated in discovery except through the 2018 NIFTY control above.

### 2.5 Findings
| Finding | n (D0 or group) | Effect | Label |
|---|---|---|---|
| Expiry-day range vs ordinary, NIFTY / BANKNIFTY | 216 / 261 | +0.02 / −0.07 % | Observed (null) |
| Monthly vs weekly expiry-day range | 60 vs 156 / 60 vs 201 | −0.02 / +0.21 % | Observed (null) |
| NIFTY D+1 big-move rate | 215 | +7.7 pts | Observed (p 0.052, q 0.41) |
| NIFTY expiry-day low later than ordinary (minute) | 62 | +73 min | Rejected (validation) |
| NIFTY D+1 low later (minute) | 62 | +74 min | Rejected (validation) |
| BANKNIFTY D-1 gap smaller | 260 | −0.17 % | Rejected (validation) |
| Monthly expiry: extreme in last hour | 15 | +40 pts | Observed (thin) |
| SENSEX expiry behaviour | 0 | – | Untestable before the final stage |

What this does NOT show: option-price behaviour (premium decay, IV) on expiry days; anything after 2022 except the four
validated-and-rejected candidates; BANKNIFTY in its Wednesday or monthly-only eras; SENSEX.
