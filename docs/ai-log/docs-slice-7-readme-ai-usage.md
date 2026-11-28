# AI log: docs/slice-7-readme-ai-usage

Branch `docs/slice-7-readme-ai-usage` (slice 7 of `docs/plan.md`, Maiwenn's part: the hand-in documents). Tool:
Claude (Claude Opus 5.5), following the `prepare-deploy` and `test-and-check` skills of the project.

## Session 1 (2026-11-28)

### What the AI did
- Read `docs/plan.md`, `docs/acceptance.md`, `docs/product.md`, `docs/guide-equipe.md`, `AGENTS.md`, the
  `prepare-deploy` skill and the 9 files of `docs/ai-log/`, on the latest branch (`design/compact-top`, which holds
  slices 1 to 6), and listed what was left for Maiwenn.
- Re-read the changes made to `flags.py` since PR #14 (Excel-style rounding `shown_value`, unit names imported
  from `ratios.py`): same thresholds, same rules. `thresholds.toml` unchanged.
- Wrote the root `README.md`: what the app does, install, run, test, data and cache, the flag thresholds (copied
  from `app/config/thresholds.toml`), known limitations (from "Known problems" of `docs/plan.md` and
  `docs/product.md`). Every screen label in it was checked against the code (`streamlit_app.py`, `display.py`).
- Wrote `AI-USAGE.md`: the summary, one log line per slice, and the AI mistakes and how they were caught, merged
  from the 9 AI log files. The per-branch files are kept.
- Fresh-copy test (`prepare-deploy`): copied the repository to an empty folder, created a new `app/.venv` with
  Python 3.12, installed `requirements.txt` and `requirements-dev.txt`, ran the tests (375 passed), started the app:
  health check and page HTTP 200, listening on `localhost` only. `.env` was not created (the student's step).
- Searched the files for key-like strings (API keys, tokens, a filled `SEC_USER_AGENT`): none found. The git
  history was not searched (the AI worked on a zip copy without `.git`).
- Gave Maiwenn the Git and GitHub steps one by one (new branch from `main`, commit, push, draft pull request,
  merge commit), following sections 5 to 10 of `docs/guide-equipe.md`, and checked each result she sent back.

### What the human decided or checked
- Maiwenn asked for the work step by step, then asked the AI to check that every project instruction
  was respected. That check added this AI log, the fresh-copy test and Corentin as reviewer (team guide pairs).
- Maiwenn ran every command herself on her Mac and sent each result back before the next step

### AI mistakes and how they were caught
- The first `plan.md` given to Maiwenn was built on the `design/compact-top` branch. Copied onto a branch from
  `main`, it would have added other members' lines that are not merged yet. Seen while writing the GitHub steps;
  a version built on `main`, with only Maiwenn's lines changed, replaced it.
- Three figures of the first `AI-USAGE.md` draft were wrong or vague (number of review tests, number of deliberate
  bugs, which slices used Claude outside Claude Code). Caught by counting again in the AI logs before sending.
- The README first named the error "SEC unreachable"; the page says "SEC EDGAR unreachable". Caught by searching each label in the code.

### Open points for the team
- **Team:** may a company with leverage and coverage "not available" be "Green" (AC7)? The README describes the
  current rule; update its passage "The overall alert ignores missing ratios" if the rule changes.
- **Arthur (slice 7):** a full review before hand-in (`review-changes`, all four reviewers), the git history search
  for secrets (`git log -p`), and the demo checklist of `prepare-deploy`.