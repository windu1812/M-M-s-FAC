# Architecture

Status: agreed on 2026-11-20 (Arthur, for the team)

## Path and stack

- **Path:** A, dashboard.
- **Stack:**
  - Python 3.12 and Streamlit for the interface;
  - Plotly for the charts;
  - pandas for tables;
  - requests and python-dotenv to call SEC EDGAR;
  - openpyxl for the Excel export;
  - JSON cache files instead of a database;
  - pytest and Streamlit's `AppTest` for tests.
- **Why:**
  1. It is a single-user tool shown on a laptop, with no accounts and nothing to save except a cache.
  2. Everything is plain Python, which the team already uses in the course.
  3. Streamlit gives a working page with inputs, cards, charts, a table and a download button within the first
     slice.
- **Alternative considered:** Django (path B). It would bring accounts and a database, which the product does not
  need. It would also cost about two extra slices before the first useful screen, with 15 hours per member.

## Parts of the application

| Part | Folder / file | Responsibility | Must not |
|---|---|---|---|
| Interface | `app/streamlit_app.py` | Ticker input, Run button, cards, charts, table, download button; it draws the values it receives | Compute, round or fill in financial numbers |
| Display layer (shared, tested) | `app/creditlens/display.py` | Display-ready values for cards, charts, table and Excel: USD → USD m, rounding, "not available" / "not meaningful" labels with reasons, flag words | Call APIs or read files |
| Ratios | `app/creditlens/ratios.py` | The 9 numbers of `product.md`, with their "not available" and "not meaningful" rules | Read files or call APIs |
| Flags | `app/creditlens/flags.py`, `app/config/thresholds.toml` | Read the thresholds, give each ratio green / orange / red and each company an overall alert | Hard-code thresholds in Python |
| Charts | `app/creditlens/charts.py` | Build the Plotly figures from display-ready values; the page only places them | Compute, round or decide that a value is missing |
| Excel export | `app/creditlens/export.py` | Build the `.xlsx` file from the display tables | Compute ratios |
| Data access | `app/creditlens/data/` (`sec_client.py`, `xbrl_tags.py`, `financials.py`, from PR #4) | SEC download, User-Agent, 10 requests/s, cache in `app/cache/`, extraction of annual 10-K values | Contain ratio or flag rules |
| Tests | `app/tests/`, samples in `app/tests/fixtures/` | Logic, data access and the main journey (`AppTest`) | Call the internet |
| Browser check | `app/checks/browser_check.py` (if installed, see `test-and-check`) | The dashboard in a real browser at laptop width | Replace tests or a person's look |

**Contracts between parts.** These let the 5 members work in parallel, each with sample tables.

| Function | Returns (pandas DataFrame, one row per ...) | Columns |
|---|---|---|
| `data.financials.get_financials(ticker)` | fiscal year × item (`revenue, operating_income, net_income, depreciation_amortization, interest_expense, total_assets, total_liabilities, stockholders_equity, current_assets, current_liabilities, cash, long_term_debt, long_term_debt_current, short_term_borrowings, operating_lease_liabilities, finance_lease_liabilities, operating_cash_flow, capex`) | `company, ticker, fiscal_year, period_end, item, value` (USD)`, unit, xbrl_tag, form, filed, accession, status` (`ok` / `not available`) |
| `ratios.compute_ratios(financials)` | fiscal year × metric (the 4 debt-based metrics exist twice: `total_debt`, `net_debt`, `net_debt_to_ebitda`, `debt_to_equity`, plus the same names ending in `_incl_leases`) | `ticker, fiscal_year, period_end, metric, value, unit` (`USD m`, `x`, `%`)`, status` (`ok` / `not available` / `not meaningful`)`, reason` |
| `flags.apply_flags(ratios, thresholds)` | same rows as `compute_ratios` | the columns above plus `flag` (`green` / `orange` / `red` / empty when there is no value) |
| `flags.overall_alert(flagged, ticker)` | one alert | `level` (`green` / `orange` / `red`), `text` (for example "Red: 2 red flags, 1 not available") |

**Errors from the data part.** `get_financials(ticker)` raises one of the following. Each message can be shown to
the user as it is. The page catches them for each ticker and still shows the other companies (V3).
- `sec_client.SecConfigError`: `SEC_USER_AGENT` is not set (E9).
- `sec_client.TickerNotFoundError`: the ticker is not in the SEC list.
- `sec_client.SecUnavailableError`: the SEC cannot be reached and nothing is in the cache (E8).
- `financials.NoAnnualDataError`: the company has no annual 10-K data (E10).

## Data model

No database.

| File | Fields | Who can read / change it |
|---|---|---|
| `app/cache/company_tickers.json`, `app/cache/CIK##########.json` (git-ignored) | Public SEC JSON, unchanged | The app writes them; deleting them only forces a new download |
| `app/config/thresholds.toml` (committed) | Per ratio: direction (`higher_is_better` / `lower_is_better`), green limit, orange limit | The team edits it; agreed starting values in `acceptance.md` |

## External services

| Service | Used for | Setting names (values in `app/.env`, never committed) | Free tier / cost | Terms checked |
|---|---|---|---|---|
| SEC EDGAR (`www.sec.gov`, `data.sec.gov`) | Ticker list, XBRL companyfacts | `SEC_USER_AGENT` (name and email of a team member) | Free | Checked by Arthur on 2026-11-20 (User-Agent required, max 10 requests/s) |

No paid service is used (decision of 2026-11-20).

## Security and privacy

- **Personal data stored:** none. The only personal value is the `SEC_USER_AGENT` name and email, kept in
  `app/.env`.
- **Who can see what:** single user on a laptop.
- **Secrets:** setting names are listed in `app/.env.example`; values live only in `app/.env` (git-ignored). Each
  member creates their own with `cp .env.example .env`.

## Run, test, preview

- **Python:** 3.12 in `app/.venv`.
  - Why 3.12: Streamlit 1.67, pandas 3.1 and Plotly 7.1 all list it on PyPI.
  - Others found on this machine:
    - 3.14.9 (Miniconda base; Plotly does not list it yet);
    - 3.12.4 (Anaconda);
    - 3.12.1 (python.org, used).
- **Settings:** the tests run without `app/.env`. Each member creates it with `cp .env.example .env`.
- **Install:** `cd app && python3.12 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt`
- **Run:** `cd app && .venv/bin/python -m streamlit run streamlit_app.py`, then open `http://localhost:8501`
- **Test:** `cd app && .venv/bin/python -m pytest`
- **Browser check:** not installed yet.

## Decision log

| Date | Decision | Reason | Agreed by |
|---|---|---|---|
| 2026-11-20 | Path A: Streamlit dashboard, Python 3.12 in `app/.venv` | Single-user laptop demo, all Python, fastest to a first screen | Arthur |
| 2026-11-20 | Thresholds in `app/config/thresholds.toml`, read with Python's built-in `tomllib`; values, overall alert rule, "not meaningful" rule and rounding as in `acceptance.md` / `product.md` | Editable without code, no extra library | Arthur |
| 2026-11-20 | The data module of PR #4 moves from `src/data/` to `app/creditlens/data/`; cache from `data/cache/` to `app/cache/`; settings from `.env` to `app/.env` | The course starter (PR #5) puts the application in `app/` | Arthur |
| 2026-11-20 | Missing data stays "not available" with its reason; no value is derived from other lines to fill a gap | Course rule "never invent a number"; honest output | Arthur |
| 2026-11-20 | No paid service: the optional LLM credit comment is dropped | The team must not pay anything | Arthur |
| 2026-11-20 | ~~Total debt always includes short-term borrowings and leases~~ (replaced by the next line) | – | Arthur |
| 2026-11-20 | Total debt in two versions: "financial debt only" (default) and "including leases and short-term borrowings". A dashboard selector switches the debt-based numbers; the Excel file holds both. The data for both is extracted in slice 2 | Lets the analyst see reported debt and lease-adjusted leverage side by side | Arthur |
| 2026-11-20 | Debt tags that already include leases (`LongTermDebtAndCapitalLeaseObligations`, `DebtCurrent`) are never used; for short-term borrowings the `ShortTermBorrowings` total comes before `CommercialPaper` | Avoids counting finance leases or commercial paper twice in the "including leases" total | Arthur (proposed by Claude in slice 2) |
| 2026-11-20 | Scope and architecture agreed (product, visuals, MVP, stack, acceptance criteria, plan) | Answers to the 5 open questions | Arthur |
| 2026-11-20 | Every failed SEC download (no internet, timeout, error status, answer not JSON) becomes `SecUnavailableError` with a readable message; nothing is written to the cache | The page needs one error type to catch per ticker (E8, V3) | Arthur (proposed by Claude) |
