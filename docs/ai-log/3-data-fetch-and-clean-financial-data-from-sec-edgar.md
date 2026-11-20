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

---

## Session 2 (2026-11-20): move into `app/`, new items, 10-K reconciliation

### What the AI did
- Brought the course starter and the agreed documents into this branch by merging `docs/product-interview` (no
  history rewritten). Two conflicts were resolved:
  - `.gitignore` takes the starter version;
  - the root `requirements.txt` is removed, because its packages are in `app/requirements*.txt`.
- Moved the module and its tests with `git mv`, so their history is kept:
  - `src/data/` → `app/creditlens/data/`;
  - `tests/` → `app/tests/`.

  The cache is now in `app/cache/` and the settings in `app/.env`.
- Wrote 6 tests first and showed them failing, then added 5 items:
  - `net_income` (`NetIncomeLoss`, never `ProfitLoss`);
  - `long_term_debt_current`;
  - `short_term_borrowings` (the `ShortTermBorrowings` total, else `CommercialPaper`);
  - `operating_lease_liabilities`;
  - `finance_lease_liabilities`.
- Removed `LongTermDebtAndCapitalLeaseObligations` from long-term debt. That tag already includes finance leases,
  so the "including leases" total would count them twice. One of the new tests showed that the old list used it.
- Reconciled revenue, total assets and net income for FY2026 and FY2025 of AAPL, MSFT and NKE:
  - the values were read from the filed 10-K HTML documents (statements, page cited), independently of the app's
    XBRL extraction;
  - all 18 values are equal;
  - `test_reconciliation_10k.py` checks them offline on small extracts of the real SEC data;
  - injecting the fy/end bug makes all 18 fail.
- Found 44 untracked "… 2" copies in the working tree, plus `.git/index 2`. These are iCloud Desktop sync
  duplicates, not created by the AI. It compared each one with its original: 40 were identical, and 4 were older
  drafts of the docs. It moved them to a backup folder outside the project instead of deleting them, then checked
  `git status` (clean) and `git fsck` (no errors).
- Created the issue branches #6 to #9, starting from `docs/product-interview`.

### What the human checked
- *To do (Arthur):*
  - open the 6 statement pages cited in `docs/acceptance.md` (R1–R3) and confirm the 18 values;
  - read the SEC "Accessing EDGAR Data" page (fair access: User-Agent, 10 requests/s);
  - confirm the removal of the lease-inclusive debt tag.

### AI mistakes and how they were caught
- A `sed` command did nothing at first: zsh does not split a variable into several file names. The AI caught it by
  re-checking with `grep`, which still found the old imports, and re-ran it with an explicit file list.
- The first version of the missing User-Agent message read badly ("then add with a line like"). The AI caught it
  while reviewing the `sed` result and rewrote it.
- The first 10-K parser found no MSFT income statement. Microsoft's HTML splits the title ("INC OME STATEMENTS")
  and puts each cell on its own line. The AI found the page through the 10-K's own index (page 50) and read the
  rows from there.
