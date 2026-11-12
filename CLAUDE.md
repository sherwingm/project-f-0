# Project: F&O options research + paper trading (repo project-f-0)
Paper only, buy-only options. No real orders. No auto-promotion of any strategy to live.
Live: AWS VM (`ssh -o BatchMode=yes fo-scanner`, dir /home/ubuntu/fo_scanner), pages /index and /results.

**Read first:** `HANDOFF.md` (S1) or `HANDOFF_INDEX_G1.md` (index chat), the tail of `PROGRESS.md`, the rule sections of `DECISIONS.md`, and `strategies/<name>.md` for any rule. Never read `PROGRESS.md` whole (130 KB). Skills: `/deploy-vm`, `/research-loop`; agent: `research-verifier`.

**Layout:** `scanner/` research + backtests (`s3_*` = index options, engine `s3_engine.py`); `server/` live paper (`app.py` loop, `g1_live.py`, `g1c_live.py`, `xp_live.py`, `nt_live.py`, `charges.py`); `index_data/` 1-minute loader (data in ../fo-index-data via INDEX_STORE); `tests/`; `templates/`; `strategies/` rule pages; `g1_research/`, `expiry_research/` studies. Near Tighty (`near_tighty_research/`) is separate: never mix it with index work. Sources: `docs/research/SOURCES.md`; experiments: `docs/research/experiments.csv`.

**Research:** pre-register in `strategies/` or a `*_PREREG.md` and commit BEFORE any number. Discovery / validation split. Report max up first (share >= +50/+100/+200 %, mean, median), then the booked result. Verdicts in `DECISIONS.md`, log in `PROGRESS.md`, one row per run in `experiments.csv`. History is in-sample. Never turn an article or AI summary into a rule.

**Clock:** the PC clock is ~5.5 h behind IST. Read time from the VM: `ssh -o BatchMode=yes fo-scanner 'TZ=Asia/Kolkata date'`. Never restart the server 09:00-15:40 IST on a session day.

**Deploy / git:** see `/deploy-vm`. Other sessions edit this folder: stage only your own files, `git pull --rebase --autostash`, commit and push each step.

**Replies:** reader is on a phone: plain words, lists not wide tables; end with "Still running:" and the error-count line.
**Python:** `C:\Users\sherw\.venvs\fo\Scripts\python.exe`; tests: `pytest -q -p no:warnings tests`.
