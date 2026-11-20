# CLAUDE.md - Team rules for the CreditLens project

Context: EDHEC group project, "Programming and AI for Corporate Finance".
Product: CreditLens, a Python Streamlit app that fetches financial data from the free SEC EDGAR XBRL API, computes 5-year credit ratios, shows green / orange / red flags and exports to Excel.

## Git workflow
1. Never commit or push directly to main. Always work on a branch and open a pull request with `gh pr create`.
2. Never merge a pull request yourself: the human merges after reading it.
3. Never use `git push --force`, never rewrite history, never squash or delete other members' work.
4. Small commits with clear English messages saying what changed and why.
5. Only modify files related to the current task/issue. Do not touch other members' modules without asking.

## Secrets
6. Never commit secrets. API keys and the SEC User-Agent go in a local `.env` file (listed in `.gitignore`). Only `.env.example` with variable names and no values is committed. Read settings with python-dotenv.

## Data
7. Only free, public data sources.
8. SEC EDGAR: always send a User-Agent header read from `SEC_USER_AGENT`, max 10 requests per second, cache downloads in `data/cache/` (gitignored).
9. Never invent a number. If a value is missing, return a clear "not available" marker and show it in the UI.

## Tests and number checks
10. Every financial calculation has a pytest unit test.
11. Tests must not call the internet: use small saved sample files in `tests/fixtures/`.
12. Key numbers must be reconciled against the values reported in the 10-K filings.

## Working with the human
13. Before writing code, present a short plan and wait for the human to say OK.
14. After each task, explain in simple French what each new file and function does, so the human can explain it in the Q&A.
15. After each task, add a short entry to `docs/ai-log/<branch-name>.md`: what the AI did, what the human checked, any mistake the AI made and how it was caught. This feeds `AI-USAGE.md`.

## Project structure
- `src/` code (`src/data/`, `src/analysis/`, `app.py`)
- `tests/` tests and `tests/fixtures/` sample data
- `docs/` business plan, slides, `ai-log/`
- `data/` small sample data only
- `config/` red-flag thresholds
- `requirements.txt`, `.env.example`, `README.md`, `AI-USAGE.md`
