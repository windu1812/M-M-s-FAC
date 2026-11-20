# AI log: 3-data-fetch-and-clean-financial-data-from-sec-edgar

Issue #3 "Data: fetch and clean financial data from SEC EDGAR". Tool: Claude Code (Claude Opus 5.5).

## What the AI did
- Found that issue #3 did not exist yet. Asked the human, then created it and the linked branch (`gh issue develop 3`).
- Proposed a plan (files, functions, tests). The human approved it, including an extra `status` column ("ok" / "not available").
- Wrote `src/data/sec_client.py`: ticker to CIK, companyfacts download, User-Agent from `.env`, max 10 requests/s, cache in `data/cache/`.
- Wrote `src/data/xbrl_tags.py`: tags for the 13 items, in priority order. Before choosing the tags, it checked the real AAPL, MSFT and NKE data. Tags with a different meaning are left out on purpose: `Depreciation` alone, `LongTermDebt` (includes the current part), cash including restricted cash, and net interest.
- Wrote `src/data/financials.py`:
  - the fiscal year comes from the `end` date, never from `fy`;
  - flow items keep only periods of 350 to 380 days;
  - only 10-K filings are used;
  - when a period appears several times, the most recent filing wins;
  - the tag is chosen year by year;
  - missing values become NaN with status "not available".
- Wrote 47 offline pytest tests on a synthetic companyfacts fixture. `conftest.py` blocks `requests.get` and isolates the cache and `.env`.
- Checked that the tests really catch the pitfalls. It broke the code on purpose in 5 ways, one at a time: using `fy` instead of `end`, keeping the oldest filing, removing the 350-380 day filter, accepting 10-Q filings, reversing the tag priority. Every change made at least 2 tests fail.
- Ran the code on real data (AAPL, MSFT, NKE). For MSFT, it checked that `InterestExpense` and `InterestExpenseNonoperating` give the same values in the years where both exist (FY2023: 1,968 M$; FY2024: 2,935 M$).

## Real-run results to check against the 10-K (USD millions)
| Ticker | Item | FY-1 | FY (latest) |
|---|---|---|---|
| AAPL | Revenue | FY2025: 416,161 | FY2026: 478,834 |
| AAPL | Total assets | FY2025: 359,241 | FY2026: 404,548 |
| MSFT | Revenue | FY2025: 281,724 | FY2026: 331,839 |
| MSFT | Total assets | FY2025: 619,003 | FY2026: 758,376 |
| NKE | Revenue | FY2025: 46,309 | FY2026: 46,398 |
| NKE | Total assets | FY2025: 36,579 | FY2026: 38,410 |

Items reported as "not available" by the companies' own XBRL data. These are not bugs:
- **AAPL:** interest expense FY2024-2026. Apple stopped tagging it separately after FY2023.
- **MSFT:** D&A for all years. MSFT only tags `Depreciation` and `AmortizationOfIntangibleAssets` separately.
- **NKE:** operating income, total liabilities and interest expense for all years, and D&A for FY2022. Nike's statements have no such lines; it reports interest as a net amount.

## What the human checked
- Approved the plan, the creation of issue #3 and the `status` column.
- Created `.env` with `SEC_USER_AGENT`.
- *To complete:* comparison of the numbers above with the 10-K filings (AAPL, MSFT, NKE).

## AI mistakes and how they were caught
- `get_user_agent` first read the `.env` path when the module was imported. Because of that, tests could not stop it from reading the real `.env`. The AI caught this while writing the tests and fixed it in a separate commit.
- A test file first imported `tests/conftest.py` directly, which is bad practice with pytest. The AI caught this when reviewing its own code before running the tests, and replaced it with a fixture.
- A one-off inspection script failed with `ModuleNotFoundError: src` because the project root was not on the path. The error showed this immediately, and the script was re-run with `PYTHONPATH=.`.

## Open points for the team
- Should missing items be derived where it is accounting-exact? For example: total liabilities = total liabilities and equity minus equity (NKE), or D&A = depreciation + amortization (MSFT). Today nothing is derived (rule 9). This decision belongs to the analysis module.
