# CreditLens app

Streamlit dashboard that turns SEC EDGAR 10-K data into a 5-year credit screen. Product and decisions: `../docs/`.

All commands are run from this `app/` folder.

## 1. Install (once per computer)

You need Python 3.12. Check with `python3.12 --version` (Windows: `py -0p`). Anaconda's Python 3.12 also works:
use its full path instead of `python3.12`, for example `/opt/anaconda3/bin/python`.

macOS / Linux:

```bash
cd app
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Windows (PowerShell or cmd):

```bat
cd app
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env
```

Then open `app/.env` in your editor. Write your name and email after `SEC_USER_AGENT=`, for example
`SEC_USER_AGENT=First Last first.last@edhec.com`. The SEC refuses requests without it. `.env` is git-ignored: never
commit it and never paste it into a chat.

## 2. Run

```bash
.venv/bin/python -m streamlit run streamlit_app.py          # Windows: .venv\Scripts\python -m streamlit run streamlit_app.py
```

Then open http://localhost:8501. Stop the app with `Ctrl+C` in the terminal.

- The first time, Streamlit may ask for an email in the terminal: just press Enter.
- The app only accepts connections from this computer (`.streamlit/config.toml`).

## 3. Test

```bash
.venv/bin/python -m pytest          # Windows: .venv\Scripts\python -m pytest
```

The tests never call the internet and do not need `.env`.

## 4. Checks

- Browser check: not installed yet (see `.claude/skills/test-and-check/browser-checks.md`).

## If something goes wrong

- **"Damaged cache file" on the page:** a file in `app/cache/` was cut during a download. Delete the file the
  message names and click Run again (the internet is needed to download it again).
- **"Port 8501 is already in use":** another Streamlit app is still running. Stop it with `Ctrl+C` in its terminal,
  or start on another port: `.venv/bin/python -m streamlit run streamlit_app.py --server.port 8502`, then open
  http://localhost:8502.
- **`python3.12: command not found`:** use the full path of a Python 3.12 (see step 1), or install Python 3.12 from
  python.org.
- **`ModuleNotFoundError`:** you used another Python. Always call `.venv/bin/python` (Windows `.venv\Scripts\python`).
