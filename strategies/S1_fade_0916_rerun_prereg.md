# S1 fade · 09:16 entry re-run: what counts as a real effect (pre-registered 30 Oct 2026)

Written 30 Oct 2026 during the session, after the first counterfactual
(`data/results/S1_fade_0916_counterfactual_2026-10-30_report.md`, 1ac0aa3b) and **before any 30 Oct fade trade or
record was looked at**. Approved by the user ("Do it", 30 Oct 2026). Read-only research: nothing here changes v12,
the entry, sizing, orders or deployment.

## Why this exists
The first run found a small 09:16 gain on fresh-book days (+2.4 pts of the premium a trade, 11 pairs, 2 days). It
avoided no stops, and it fell to +0.8 pts without LT. That is too little to decide either way. The rules below fix
in advance when the question is answered, so the answer cannot be picked after seeing more data.

## Population and timing
- **Pairs:** v12 fade signals bought on **fresh-book days**, trade day ≥ **2026-10-28** (the first-trade-today gate,
  32595932, live from 28 Oct). Each pair is the booked 09:15 trade and its 09:16 counterfactual, built exactly as in
  `strategies/S1_fade_0916_entry_counterfactual.md`. Pairs bought at or after 09:16 count as "unchanged", with a
  difference of 0. Signals whose 09:16 side is unavailable are counted and listed, never filled in.
- **Out of the decision:** 27 Oct (previous-day books, a bug fixed in 32595932) and 23 Oct ADANIENSOL. Both are
  still reported separately.
- **First look:** the pairs up to and including the first trade day on which the cumulative count of fresh-book pairs
  reaches **30**. The script finds that day itself, so a later run cannot move the look: it judges the same pairs.
  Runs before that day are for data checks only. They are labelled "NOT A DECISION", and nobody acts on them.
- **Second and last look:** only if the first is INCONCLUSIVE, judged on the pairs up to the day the count reaches
  **60**, under the same rules. There is no third look.

## The engine is fixed
`scanner/fade_entry_0916_cf.py` at the commit that adds this file. On the 29 Oct copies it gives a per-trade CSV
identical to 1ac0aa3b's. Only bug fixes are allowed. Each one is logged in the methodology's "Changes" section with
its reason, and the results are reported both before and after the fix.

## The primary measure (net % first)
**Δ = 09:16 net % − 09:15 net %** per pair, in points of the premium paid at each entry. Points, not rupees: the two
entries put different rupees at risk. On the first run most of the rupee gain was a smaller stake at a lower 09:16
price, not a better trade. Rupee totals are reported second, for information.

Statistic: the mean of Δ, with a t clustered by trade day (`scanner/stats.py` `clustered_t`, CR1). Same-day trades
share the market's move, so the day is the independent unit, not the trade.

## A real effect needs all four
| | Check | Pass when |
|---|---|---|
| P1 | Size | mean Δ ≥ **+5.0 pts** |
| P2 | Reliability | clustered t ≥ **max(2.0, the two-sided 5 % Student-t critical value with days − 1 df)**, on ≥ **6** trade days (with few days the plain 2.0 is too lenient: 2.57 at 6 days, 2.26 at 10) |
| P3 | Not one trade | without the pair with the largest positive Δ, mean Δ ≥ **+2.5 pts** |
| P4 | Mechanism | stops avoided (09:15 stopped, 09:16 did not) **minus** stops added (09:16 stopped, 09:15 did not) ≥ **3** |

P4 is the reason to look at 09:16 at all: the 09:15 buy is unprotected until 09:16, and 9 of 14 stops breached
before 09:16 (29 Oct checkpoint). A gain with no stops avoided does not support that explanation.

## Consistency checks (sign only)
A failing check turns a would-be PASS into INCONCLUSIVE. A check with too few pairs is reported as "too few" and
counts as neither a pass nor a fail.
| | Check | Pass when |
|---|---|---|
| C1 | Same strike | on changed pairs where the live walk would have bought the same strike at 09:16 (`walk_same` = yes, or from 2 Nov the recorded walk choice is the traded strike): mean Δ > 0; needs ≥ 5 pairs |
| C2 | Same engine | mean of (09:16 net % − the 09:15 trade replayed by the same engine, net %) > 0 on changed pairs; needs ≥ 2 pairs |
| C3 | Recorded walk choice | from 2 Nov (`strategies/S1_fade_0916_walk_choice_recorder.md`): mean of (walk-choice net % − booked 09:15 net %) > 0; needs ≥ 10 pairs |

### C3's replay (fixed now, before any walk_0916 data exists)
- Entry: the recorded choice's ask at its decision second; quantity = lot × lots.
- Exit: v12 on that contract's own follow rows (observation phase `walk_0916`, id `w0916:<date>:<symbol>`), on
  rows after the decision second and before 15:20:00. The stop applies at bid ≤ 0.80 × entry. The trail switches on
  at bid ≥ 1.10 × entry and sells at bid ≤ 0.98 × the highest bid since then. Each level is rounded to 4 dp, as
  live v12 does (`server/fade.py`), so a bid exactly on a level triggers as it would live.
- Neither fired: sold at 15:20 at the bid of the last follow row at or before 15:20:00, but only when the follow
  reached 15:20 (`follow.last` ≥ 15:20:00) and that row has a bid. Otherwise the outcome is unresolved and stays
  out.
- Charges: `server/charges.py` `round_trip` on both legs. Net % = net / (entry × quantity).
- Prices are observed quotes, not fills. A choice decided while prices came from Kotak (`kotak_polls` > 0) is
  flagged in the table.

## Verdict (computed by the script, `decision()`)
1. **NOT A DECISION:** fewer than 30 fresh-book pairs.
2. **PASS:** P1–P4 all pass and no consistency check fails. The evidence supports a **forward test** of a 09:16
   entry. That is a proposal for the user, not a change. Nothing live changes without their approval and a
   DECISIONS.md entry.
3. **CLOSE:** mean Δ < +2.0 pts, or clustered t < 1.0 (or not computable). There is no material 09:16 effect, the
   09:15 entry stays, and the question is closed. The walk-choice recorder can then be switched off, with the
   user's approval.
4. **INCONCLUSIVE:** anything else. One more run at 60 fresh-book pairs. If that is not a PASS, the verdict is CLOSE.

An independent review on 30 Oct, before this file was committed and before any 30 Oct data was seen, found five
problems. All were fixed before the commit:
- the looks were not pinned to a day;
- P3 dropped the largest absolute Δ, which could be a loss;
- C2's minimum was not written here;
- the engine compared unrounded levels and kept checking stops and trails after 15:20;
- an empty 15:20 bid fell back to an older bid.
The engine fix leaves the 29 Oct per-trade CSV unchanged.

The script prints the table with net % first and rupees after. The decision uses only P1–P4 and C1–C3. Everything
else in the report (comparable-quote subsets, the standing-book variant, exit timing) is description only.
