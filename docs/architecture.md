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
| `display.display_table(flagged, financials)` | ticker × fiscal year × metric (all 13 metrics, both debt versions), the rows of `apply_flags` | `ticker, company, fiscal_year, period_end` (text `YYYY-MM-DD`)`, metric, label, unit, value` (rounded as on screen, empty when there is no number)`, text` (what the screen shows)`, status, flag, reason` (the note of an `ok` value, for example "short-term borrowings not reported"). Read by the page, `charts.py` and `export.py` |
| `display.underlying_table(financials)` | ticker × fiscal year × item ("View underlying data", Excel Financials sheet) | `ticker, company, fiscal_year, period_end, item, label, value` (USD m, 0 decimals, empty when not reported)`, text` ("6,000 USD m" or "not reported")`, xbrl_tag, accession, status` |
| `flags.overall_alert(flagged, ticker, incl_leases=False)` | one alert (an `Alert`), for the latest fiscal year and the selected debt version | `level` (`green` / `orange` / `red`, or empty when no ratio has a flag), `text` (for example "Red: 2 red flags, 1 not available"), `fiscal_year`, `green`, `orange`, `red`, `not_available`, `not_meaningful` |

**Errors from the data part.** `get_financials(ticker)` raises one of the following. Each message can be shown to
the user as it is. The page catches them for each ticker and still shows the other companies (V3).
- `sec_client.SecConfigError`: `SEC_USER_AGENT` is not set (E9).
- `sec_client.TickerNotFoundError`: the ticker is not in the SEC list.
- `sec_client.SecUnavailableError`: the SEC cannot be reached and nothing is in the cache (E8).
- `sec_client.NoFinancialDataError`: the SEC answers HTTP 404 for the company's file: it has no XBRL data for it (a 404 on the ticker list stays a `SecUnavailableError`).
- `sec_client.CacheFileError`: the cached file of the company is damaged; the message names the file to delete.
- `financials.NoAnnualDataError`: the company has no annual 10-K data (E10).

A `ValueError` from `compute_ratios` (an amount not in USD, a fiscal year given twice) is shown as "Data problem", and
any other error as "Unexpected problem", for that ticker only. `sec_client.cache_saved_on(ticker)` gives the date of
the cached company file (E7), without downloading.

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
| 2026-11-25 | Coco delegated slice 3 to Claude: plan, code, tests, documents, commits and push on the branch of issue #6 | Coco's request ("fais les miennes") | Coco |
| 2026-11-25 | Output of `compute_ratios`: amounts in USD m, not rounded; ratios in x; EBITDA margin in percent (20.0 means 20 %, so the margin thresholds are written 20 and 10). Rounding stays in `display.py`. The 13 metrics per year come in a fixed order: the 9 numbers with financial debt only, then the 4 `_incl_leases` ones | One unit per row, as the contract says; thresholds and display read the same numbers | Coco (proposed by Claude in slice 3) |
| 2026-11-25 | `reason` is an empty text when there is nothing to say. Several reasons are joined with "; " (for example "operating income not reported; D&A not reported"). A debt part counted as zero keeps status `ok`, with its note in `reason`, carried to the net debt and the ratios built on that total. Zero equity, revenue, interest expense or current liabilities give "not available: <item> is (are) zero"; EBITDA = 0 gives "not meaningful: EBITDA ≤ 0" (E3) | The page and the Excel file can show `status: reason` as it is, and say why a value is missing or was computed with a part counted as zero | Coco (proposed by Claude in slice 3) |
| 2026-11-25 | `compute_ratios` refuses (ValueError) an "ok" amount that is not in USD, and an item given twice for one fiscal year | A wrong number in a credit ratio is worse than no number | Coco (proposed by Claude in slice 3) |
| 2026-11-26 | `flags.py` compares each value as it is shown on screen (ratios 2 decimals, EBITDA margin 1 decimal, amounts 0 decimals), so a cell that reads "2.00x" is never orange when the limit is 2.0 | The colour and the number on screen must agree | Maiwenn (proposed by Claude in slice 4) |
| 2026-11-26 | Flags: only the 6 ratios get one (`flagged_metrics`); EBITDA, total debt and net debt get an empty flag, like "not available" and "not meaningful" rows. `thresholds.toml` has one section per ratio (`direction`, `green`, optional `orange`, `label`), used for both debt versions; a wrong file stops the app with a readable `ValueError` | Thresholds editable without code (AC6); a wrong flag is worse than no flag | Maiwenn (proposed by Claude in slice 4) |
| 2026-11-26 | `overall_alert(flagged, ticker, incl_leases=False)` returns an `Alert` (`level`, `text`, `fiscal_year` and the counts) for the latest fiscal year and the selected debt version. Text: "Orange: 1 orange flag", "Red: 2 red flags, 3 not available, 1 not meaningful". "Not meaningful" is counted apart from "not available". If no ratio has a flag at all, `level` is empty and the text is "No flag: 6 not available" | The card must never say "green" when nothing could be checked | Maiwenn (proposed by Claude in slice 4; to confirm by the team) |
| 2026-11-26 | Charts and Excel read one display table from `display.py`: one row per ticker, fiscal year and metric, columns `ticker, company, fiscal_year, period_end, metric, label, unit, value, text, status, flag`. `value` is already rounded as on screen and empty when there is no number; `text` is what the screen shows (for example "1.42x" or "not available: D&A not reported"). Sample: `app/tests/fixtures/charts_sample.csv`. The table holds all 13 metrics (both debt definitions), so the Excel Ratios sheet has both. The Excel file also reads the "View underlying data" table: one row per ticker, fiscal year and item, columns `ticker, company, fiscal_year, period_end, item, label, value` (USD m, 0 decimals)`, text, xbrl_tag, accession, status` (sample: `app/tests/fixtures/export_financials_sample.csv`), and the alert text of each company (`overall_alert(...).text`) | Charts, Excel and table then show the same numbers, and slices 5 and 6 can be built in parallel | François (proposed by Claude in slice 6; confirmed by Marc on 2026-11-27, slice 5) |
| 2026-11-27 | Marc delegated slice 5 to Claude: plan, code, tests, documents and commit on the branch of issue #8 | Marc's request ("fais la partie de Marc") | Marc |
| 2026-11-27 | The display table and the "View underlying data" table follow the format proposed by François on 2026-11-26 (slice 6), plus a `reason` column; `period_end` is a text. Checked: `charts.py` and `export.py` of branch 9 run unchanged on it | Confirms the open point of 2026-11-26; slices 5 and 6 show the same numbers | Marc (proposed by Claude in slice 5) |
| 2026-11-27 | Display rules: a missing value shows its status in the table cell ("not available") and its reason in a "Notes" column with the years; the card shows "not available" in bold and the reason under it. The change vs the prior fiscal year is computed on the rounded values shown ("+0.17x vs FY2025", margin in "pt"), only when both years have a number and the prior year is the fiscal year just before. A fiscal year a company does not have shows "no data". Tickers: commas or spaces, capitals, each once, 1 to 5 | Short, readable cells; the change agrees with the numbers on screen; never a filler value | Marc (proposed by Claude in slice 5) |
| 2026-11-27 | Page: light theme and a neutral blue (`#1f4e79`) for buttons and selectors in `app/.streamlit/config.toml`; the debt selector redraws the stored result without downloading again; each ticker's error is caught and shown alone | `product.md`: white background, colour only for flags; V3 | Marc (proposed by Claude in slice 5) |
| 2026-11-28 | The ratio table shows the 5 most recent fiscal years present (`display.TABLE_YEARS`), never a filler year; older years are named under the title; "Latest flag" names its year when it is not the last column. The Excel Ratios sheet and the 5-year chart keep every fiscal year | AC5 (5 columns) and E11 (only real years) both hold when year ends differ by company; the reader always knows which year a flag belongs to | Arthur (review of PR #16, proposed by Claude) |
| 2026-11-28 | Arthur asked Claude to fix every finding of the review of PR #16 ("Tout corriger"), on Marc's branch, including the data part (`sec_client.py`, `financials.py`, Arthur's) and the rounding of `flags.py` (Maiwenn's) | The demo is on 2026-11-30; the review found no blocker but many small problems | Arthur |
| 2026-11-28 | Rounding: halves up, away from zero, as Excel's ROUND (`flags.shown_value`, used by `display.round_value`); before, Python's `round()` gave 2,406 / 1,200 = 2.005 → "2.00x" green where an analyst or Excel gives 2.01x orange | One rule for the number and its colour, the same as the analyst's own Excel | Arthur (proposed by the code and test reviewers) |
| 2026-11-28 | Page: the ticker field and Run are a form (Enter runs); "Results for:" names the tickers of the results shown; the same error for several tickers is shown once; any unexpected error stops only its ticker; the progress box turns to an error when no company could be loaded | V3 and a safer live demo | Arthur (review of PR #16) |
| 2026-11-28 | Display words: ratio-table cells hold the number without its unit (the Unit column has it); "Notes" give each reason once with a year range, " \| " between year groups; "Latest flag" says "n/a" for a ratio with no value and "–" for amounts; the leases label is ", incl. leases" ("Net debt / EBITDA, incl. leases (x)"); card changes say "(better)" or "(worse)" from the threshold direction; the card says the alert covers all 6 flagged ratios | Shorter cells, no ambiguous words, no double brackets; the alert counts match what the reader can find | Arthur (review of PR #16) |
| 2026-11-28 | Not done: a "no data" column for a fiscal year that no company has (code review, minor) | E11 forbids filler years; the year labels already show the gap | Arthur |
| 2026-11-28 | Second review round: the table keeps the 5 most recent fiscal years present (`years[-5:]`, as decided above; the first fix kept a 5-year calendar window, which dropped a real year when a year was missing) and the caption names a company that has no year in it; `flags.shown_value` is the only rounding (unknown unit = error, infinite value kept); `display.grouped_errors` | The code now does what the decision says | Arthur (review of PR #16, round 2) |
| 2026-11-28 | Arthur did step 6c of slice 6 (page wiring of the charts and the Excel button) with Claude, on François's branch | François agreed (told to Arthur); François reviews the code and must be able to explain it | François |
| 2026-11-28 | Charts on the page: one selector of the 6 ratios (labels of `display.py`), turned into the selected debt version with `display.selected_metric`, so the chosen ratio stays when the debt definition changes; both charts full width, one under the other (the notes under the 5-year chart are long); the Excel file is built on each redraw from the same `display_tbl` as the screen, and the download does not redraw the page | One source for screen, charts and Excel; readable notes | Arthur for François (proposed by Claude in slice 6) |
