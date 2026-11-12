---
name: research-loop
description: The project's research routine - pre-register a test, run it on history, write the result, register the run, record the verdict. Use when starting or finishing any strategy, signal or pattern study (G1, XP, expiry, S1, S2). Also use to check a study followed the rules.
---

# Research loop (history studies; paper only, no real orders)

The point is that no number is seen before the plan is fixed, and that every run is recorded. Read `CLAUDE.md` first for the layout and the Python path.

1. **Look before you start.** Search `docs/research/experiments.csv` and `DECISIONS.md` for the same idea so it is not repeated; read the relevant rule page in `strategies/`. If the idea comes from an article, forum or an AI summary, add it to `docs/research/SOURCES.md` first and judge it (official or secondary, what was actually read). A source is never a rule.
2. **Pre-register** a page BEFORE computing anything: `strategies/<name>.md` or `g1_research/<NAME>_PREREG.md`. It must fix: the question; data and period; the chronological split (discovery / validation, and a confirmation period if one exists); the outcome (**max up first**: share reaching +50 / +100 / +200 %, mean, median; then booked: win %, average, median, total, 1x and 2x costs); the exact rules and thresholds; the decision rule (including a multiple-testing correction when many rules are tried); and what was already seen (disclose any earlier look). `git add` that page, commit and push it alone, so its commit time precedes the results.
3. **Run** the script on history only (`INDEX_STORE=../fo-index-data/data/index`, Python from `CLAUDE.md`). No peeking at validation to choose rules. Features must be known at the decision time; check the outcome does not contain the information used to predict it (circular targets were found once already). Fit cut-points on discovery only.
4. **If the plan needs a change after seeing anything,** write an Amendment into the page that says exactly what was seen, and why, BEFORE the next number. Never tune after the result.
5. **Write the result** next to the plan (`*_RESULT.md`): the verdict in plain words, the numbers, what was hiding (by year, by half, without the largest trades, overlap between features), and the caveat that history is in-sample. A "no pattern" result is a valid result.
6. **Register the run:** append ONE row to `docs/research/experiments.csv` (never edit old rows): run id `E-YYYYMMDD-NN`, commit hash, hypothesis, parameters, data, dates, sample size, charges and slippage, result file, validation status, prereg reference, notes. Unknown = `not recorded`. Commit the result first, then add the row with its hash (a small follow-up commit is fine).
7. **Record:** the verdict in `DECISIONS.md`, a short log in `PROGRESS.md`. Commit and push every step; stage only your own files (other sessions edit this folder), `git pull --rebase --autostash`.
8. **Independent check (optional but recommended before a verdict is relied on):** run the `research-verifier` agent on the result file. It re-computes the key numbers without changing anything.
9. **Report** to the user: max up first, then the booked result, in lists not wide tables, ending with "Still running:" and the error-count line.

Never promote a strategy to live from a history result. A pass means "passed its paper gate"; only the user decides about real money.
