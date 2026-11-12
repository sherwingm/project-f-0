# Research infrastructure (added 2026-11-12)

Two small files, nothing else to install.

- **`SOURCES.md`** is the central list of external sources: papers, NSE / BSE circulars, SEBI publications, data-provider docs, technical docs,
  practitioner posts. Each entry records title, issuer, URL, publication date, date accessed, topic, findings, official or secondary, and
  how it was evaluated. **A source is evidence to read, never a rule.** A finding becomes an experiment only through a pre-registered page
  (`strategies/*.md` or `g1_research/*_PREREG.md`); an article or an AI summary is never turned straight into a trading rule.
- **`experiments.csv`** is the run registry: one row per experiment, newest at the bottom. Add a row when a result is committed, never edit
  or delete an old row (append a correcting row instead). Columns:
  `run_id` (E-YYYYMMDD-NN), `run_datetime` (the time of the commit that stored the result, from git; the PC clock can be wrong, see
  `CLAUDE.md`), `git_commit` (short hash of that commit), `experiment`, `hypothesis`, `parameters`, `data_source`, `start_date`, `end_date`,
  `sample_size`, `charges_slippage`, `result_file`, `validation_status`, `prereg_ref` (file @ the commit that fixed the plan), `notes`.
  Unknown facts are written as `not recorded`, never guessed. Rows for work before 2026-11-12 were back-filled from the committed files and
  reports only; where the plan and the results went into one commit, `notes` says so.

How they fit the loop (`/research-loop`): read sources -> pre-register -> run -> result file -> row in `experiments.csv` -> verdict in
`DECISIONS.md` -> log in `PROGRESS.md`. The trial count of a study is the number of rows (and of rules inside them), which is what a
multiple-testing correction needs.
