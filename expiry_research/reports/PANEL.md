# Daily panels (build report)

Written 2026-11-05; revised the same day after the verifier review (see "Revision" at the end). Code
`scripts/build_panel.py`, loader `scripts/panel_io.py` (design: `reports/lld/panel.md`), tests
`tests/test_panel_leakage.py`. Run log `results/panel_stdout.txt`, test log `results/panel_tests_stdout.txt`.
No expiry statistic is computed here: this module only builds the data.

## What was built
| Panel (open: discovery + validation) | Rows | Span | Columns |
|---|---|---|---|
| `data/panel_NIFTY.parquet` | 1,599 | 2018-01-01 → 2024-06-28 | 173 |
| `data/panel_BANKNIFTY.parquet` | 1,599 | 2018-01-01 → 2024-06-28 | 173 |
| `data/panel_SENSEX.parquet` | 663 | 2021-10-20 → 2024-06-28 | 109 (no futures / options) |

The final period (2024-07-01 → 2026-10-29, 577 rows per panel) is sealed in `data/sealed/panel_<UL>_final.parquet`
(578 rows: the 577 final rows plus the unblanked 2024-06-28 edge row). Only the coordinator opens it, once
(PREREGISTRATION). Research code reads panels with `panel_io.load_panel(ul)`, which refuses any final row or label.

One row per full session t. Diwali Muhurat sessions are not rows; `cal_special_between` marks the sessions whose gap
to t+1 spans one (3 in the open NIFTY / BANKNIFTY panels, 2 for SENSEX). Column meanings and availability: `data/panel_dictionary.csv`
(173 entries: 124 TCLOSE(t), 20 OUTCOME(t), 22 NEXT(t+1), 7 T1515(t)).

Rows per split (`results/panel_summary.csv`; its NaN shares cover discovery, validation and both, not final):
| Panel | Discovery | Validation | Final (sealed) |
|---|---|---|---|
| NIFTY, BANKNIFTY | 1,233 | 366 | 577 |
| SENSEX | 297 (from 2021-10-20) | 366 | 577 |

Split edge: on 2022-12-30 and 2024-06-28 the row is in one split and its label (t+1) in the next. Those rows keep
the split of t and carry `split_edge = True`; drop them when a test must keep labels inside one period. In the open
file the 2024-06-28 row has every `y_` value blank except `y_date`, because its t+1 is a final-period session.

## Prefixes (when a value is known)
- `f_`: after the official close of t, including that evening's bhavcopy. `f1515_`: at 15:15 of t (bars up to 15:14).
- `o_`: what happened in session t (known at its close). `y_`: what happens in session t+1. `y_X` is exactly `o_X`
  of the next row.
- `cal_` / `cal_next_`: expiry tags of t and t+1. They count only to expiries already listed on t (the calendar's
  `known_from`); a `cal_next_` tag that needs an expiry first listed after t is blank.

## Price source
- From 2021-10-20 the daily OHLC is built from minute bars 09:15–15:29 (`src = spot_1m`, 661 open NIFTY rows).
  Before that, and on 2 bad minute days (2021-11-10 short, 2022-03-07 bad high), it is `index_close_daily`.
- SENSEX has no official daily file. On 2021-11-10 it uses the short minute day (`spot_1m_short`); its minute
  outcomes that day are blank.
- Minute close vs official close (`results/panel_reconcile.csv`, 660 days, 2021-10-20 → 2024-06-28 only; the final
  period is not used): median gap 0.05 % (NIFTY) and 0.07 % (BANKNIFTY), 133 / 218 days over 0.1 %. Open matches
  exactly.
- So the source matters for gap labels: the up / down / flat gap label agrees on only about 89 % of days (NIFTY
  89.5 %, BANKNIFTY 88.5 %) between minute and official closes. That is because NSE's close is a 30-minute average and the
  flat band is only 0.1 %. Panels use the minute close (the price a trader could see); `px_close_official` is kept
  to 2025-09.
- VIX close in the open NIFTY panel: `vix_daily` on 1,582 rows, `index_close_daily` on 16 and the clean minute close
  on 1 (`f_vix_src`).

## Gaps (`results/panel_gaps.csv`, 9 rows, open period only)
- No bhavcopy, so futures and options features are blank on 2021-03-30 and 2024-01-20 (NIFTY and BANKNIFTY).
  The final period's input gaps (from `src`, `n_bars` and `f_` columns only; 4 rows, 2025-02-01 and 2026-02-01) are
  in `data/sealed/panel_gaps_final.csv` for the coordinator.
- Minute outcomes and `f1515_` are blank before 2021-10-20 (76 % of discovery rows) and on the bad minute days.
- NIFTY `cal_sessions_to_weekly` is blank before 2019-02-11, the day the first NIFTY weekly (2019-02-14) was listed.
- BANKNIFTY `cal_sessions_to_weekly` is blank after the last weekly (2024-11-13, sealed period). SENSEX calendar tags
  are blank before 2024-10-04, the first stored SENSEX expiry, so they are blank in the whole open SENSEX panel.
- Nothing is filled. Option features use only the strikes the bhavcopy lists; `n_strikes` and `n_strikes_oi` are
  recorded for each (NIFTY near expiry: 61 to 165 strikes).

## Leakage tests (all 8 pass, run by pytest; the 13 calendar tests also pass)
| Test | What it checks |
|---|---|
| a, TCLOSE | For 22 dates (16 fixed edge dates + 6 random), every raw input is cut at TCLOSE(t) and the panels rebuilt. Every `f_`, `o_`, `cal_`, `px_` value of row t is unchanged, in all 3 panels. For the 5 fixed dates in the sealed period only `f_` and `cal_` are compared (read with `panel_io.sealed_feature_columns`; `o_`, `y_`, `px_` stay unread). |
| a, T1515 | The same with the cut at 15:14 of t (no daily, VIX or bhavcopy rows of t). Every `f1515_` value is unchanged. |
| b, raw | 40 random rows per open panel. Each `y_` label is recomputed from raw t+1 data by separate test code and matches. |
| b, shift | `y_X` equals `o_X` of the next row, and the last open row (2024-06-28) has only `y_date` filled. |
| c | Every column has a dictionary entry, and its availability matches its prefix. |
| d | On the open panels, no feature column has \|correlation\| ≥ 0.9 with `y_gap_pct`, `y_cc`, `y_oc`, `y_ret15` or `y_range_pct`. |
| e, seal | Open files hold no final row or final label; the sealed file has the same columns, the final rows and the one edge row; open + final rows = every session; `load_sealed_final` refuses without the coordinator flag. |
| e, calendar | No `cal_` count of t and no `cal_next_` count points to an expiry first listed after t (open and sealed rows); NIFTY weekly counts are blank before 2019-02-11. |

Mutation check (not part of the suite): I injected two leaks by hand, `f_mom1` taken from the next day and
`f1515_rv` taken from the full day. Test a caught both.

## Caveats for users
- Calendar tags use final expiry dates. A re-dated contract counts as known from the day its original contract was
  listed, so a late holiday re-dating is assumed known early. The one late case is the 2023-06-29 → 06-28 move,
  re-dated on 2023-06-27, which affects a few late-June 2023 rows.
- The options expiry columns (`f_opt_*_expiry`) are the dates as listed on t. For a contract the exchange re-dated
  later, they show the old date.
- `f_fut_basis_pct` uses the futures' last-traded close against `px_close`, which is the minute close from 2021-10
  and the official close before then.
- Discovery has minute features only for 2021-10-20 → 2022-12-30 (about 300 rows).

## Revision 2026-11-05 (verifier review)
| Issue | Change | Evidence |
|---|---|---|
| NIFTY weekly countdown before the weekly existed | Calendar counts only to expiries listed on the day (`known_from`, `scripts/build_calendar.py`); `cal_next_` tags that need a later-listed expiry are blank | Old vs new open panels differ only in NIFTY 2018-01-01 → 2019-02-08 calendar columns (274 weekly counts now blank; 6 rows 2019-02-01 → 02-08 now point to 2019-02-28, monthly) and in the 2024-06-28 labels |
| Final period readable in the panel files | Final rows moved to `data/sealed/`; open files end 2024-06-28; shared loader `scripts/panel_io.py`; summary, reconcile and gap report use the open period only | Sealed rows equal the old final rows in every column (equality check only, no values read out); test e |

The NIFTY weekly launch announcement date was not confirmed from a primary source, so the listing day (2019-02-11) is
used as the first day it is known.
