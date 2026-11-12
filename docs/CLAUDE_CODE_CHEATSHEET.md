# Claude Code cheat sheet for this project (2026-11-12, Claude Code 2.1.309)

**Verified here:** the skill list of the session, `claude --help`, `claude mcp list`, `claude plugin list`, `~/.claude/` and `.claude/`.
**Documented only (not run here):** the interactive slash commands marked (doc). In the desktop app's Code tab, terminal-dialog commands
such as `/permissions`, `/config`, `/hooks` do not open; they work in a normal `claude` terminal.
"Auto" = the model may load the skill when your request matches; you can always type `/name`.

## Learn these first
1. `/context` (doc) then `/compact [what to keep]` (doc): check what fills the context; compact at about 60 % or at a natural break. Auto-compact is OFF (your choice), so this is your habit.
2. `/clear` (doc): new empty chat after a handoff is written (`HANDOFF*.md`).
3. `/code-review high` (bundled): before anything touching live trading, charges or the engine. Not `max` / `ultra` casually (costly).
4. `/run` (bundled): after a page or server change, to see it work in the real app.
5. `/deploy-vm` (project skill, manual): the safe VM update. `/research-loop` (project skill): the pre-register / run / register routine.
6. `/fewer-permission-prompts` (bundled): once, to cut approval prompts with a read-only allowlist.
7. `/loop 30m <check>` (bundled): a repeated live check during a session. Not for polling CI.
8. `claude --worktree <name>` (CLI): a risky experiment in its own git worktree, away from other chats.
9. `/explain-usage` (app): where tokens went.
10. `claude -c` or `claude --resume` (CLI): continue an old chat; `--fork-session` to branch it.

## If X then Y
- Chat is long or slow: `/context`, then `/compact`.
- New unrelated task: `/clear` (after the handoff).
- Before deploying live code: tests, `/code-review high`, then `/deploy-vm`.
- Changed a page or the server: `/run`.
- Where does X live in the code: ask in plain words; wide searches go to the `Explore` agent.
- Starting or checking a study: `/research-loop`; then the `research-verifier` agent to re-check numbers.
- Reading a source: add it to `docs/research/SOURCES.md` first; Reddit is blocked for every tool.
- Reply for the phone: lists, not wide tables.
- Excel report: `anthropic-skills:xlsx`. Charts or a page: `dashboard-design` (not the three overlapping chart skills).

## Capabilities by group
**Coding:** `/init` (CLAUDE.md starter, done by hand here), `/run`, `/simplify` (clean a finished diff; not for bugs), `/update-config` (settings, hooks), `/keybindings-help`, `/skill-creator`, `/plugin-authoring`, `/claude-api` (auto, Claude API code only).
**Debugging:** `claude doctor` (CLI), `/fewer-permission-prompts`, the `Explore` agent (read-only search), `/rewind` (doc), `/resume` (doc).
**Review and verification:** `/code-review [low|medium|high|xhigh|max|ultra] [target] [--fix] [--comment]`, `/security-review`, `claude ultrareview` (CLI, cloud, billed), the `research-verifier` agent (this project), `data:validate-data` (generic analyst QA, not backtest-aware).
**Research and analysis:** `web-fetch` agent and WebSearch (public pages; no Reddit), `claude-code-guide` agent (questions about Claude Code), `data:analyze` / `explore-data` / `statistical-analysis` (helpers only, they do not know our rules), `/graphify` (graph is stale: refresh before use), `anthropic-skills:pdf|docx|xlsx|pptx|docs`.
**Testing and backtesting:** no Claude skill; our `pytest` suite (`pytest -q -p no:warnings tests`) and `scanner/s3_engine.py`; new validation tests in `tests/test_validation_*.py`.
**Git and deployment:** `/deploy-vm`, `claude --worktree`, `/schedule` (cloud routines; not for the live server), `/loop`.
**Context and tokens:** `/context`, `/compact`, `/clear`, `/memory` (doc), `--autocompact <auto|tokens>` / `autoCompactEnabled` (off), `claude --bare` (minimal start, skips memory and hooks), the project `CLAUDE.md` (about 500 tokens), subagents (read a lot, return a summary).
**Agents and multi-agent:** `Agent` tool (`Explore`, `Plan`, `general-purpose`, `fork`, `web-fetch`, `claude-code-guide`, `research-verifier`), `/workflow-authoring` (needs your opt-in; overkill), `claude agents|attach|logs|stop` (background sessions), `--agent` / `--agents <json>`.

## Overlaps, redundant, unused (nothing was removed)
- Chart skills overlap: `dashboard-design`, `dataviz`, `data:create-viz`, `data:data-visualization`.
- Review skills overlap: `/simplify`, `/code-review`, `/security-review` (start with `/code-review`).
- Unused here: `finance:*`, `marketing:*`, `agentui-tools:*`, `cowork-plugin-management:*`, `data:sql-queries|write-query|data-context-extractor`, and the connectors Notion, Razorpay, dibsresearch, Pattern Intelligence, Figma. Gmail, Calendar and Drive are connected but not needed. Disconnect or disable them in claude.ai or the desktop app (not possible from a session).
- No hooks are configured, none are needed. Stale preview entries remain in `.claude/launch.json` (`ix-static`, `g1-preview`, `xp-preview` point at temporary scripts).
