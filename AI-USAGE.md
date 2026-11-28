# AI usage

How AI tools were used in this project. During the project, each branch kept its own AI notes in
`docs/ai-log/<branch>.md`; this file gathers them for the hand-in (slice 7). The per-branch files stay in the
repository with every detail.

Merged by Maiwenn with Claude on 2026-11-28, from the 9 files of `docs/ai-log/`. 

## Summary

- **Tools:** Claude Code with the model Claude Opus 5.5, used by every member on their own computer, with the
  project's skills (`product-interview`, `build-feature`, `integrate-api`, `design-interface`, `test-and-check`,
  `review-changes`) and its read-only reviewer agents (code, tests, interface). Claude (same model, outside Claude Code)
  for the flags and dashboard slices, and for this file and the root `README.md`. No paid API or other AI service in the app itself: the
  optional LLM credit comment was dropped because the budget is 0 EUR (decision of 2026-11-20).
- **What AI did:**
  - turned the product interview into the four documents of `docs/` (product, architecture, acceptance, plan);
  - wrote most of the code: SEC client and XBRL extraction, ratios, flags, display and page, charts, Excel export;
  - wrote the tests first (385 offline tests at the end), with hand-worked expected values;
  - broke its own code on purpose to prove the tests catch mistakes (more than 50 deliberate bugs over the slices);
  - reviewed pull request #16 as reviewer agents (2 rounds), at Arthur's request, then fixed the findings;
  - wrote the team guide in French, and the root `README.md` and this file.
- **What we decided ourselves:**
  - the product: customer, problem, the 5 features, what is not in the MVP ;
  - the stack: Streamlit and Python 3.12, no database, SEC JSON in a local cache;
  - the thresholds of the flags and the overall alert rule;
  - which review findings of PR #16 to fix, and which to leave open (notes width, "Green" with missing ratios);
  - "not available" with the reason and nothing derived, even where it would be accounting-exact (MSFT D&A,
    NKE total liabilities);
  - total debt in two versions with a selector, replacing the AI's first "leases always included" proposal;
  - who owns which issue, the reviewer pairs, and every merge;
  - the compact page layout.
- **How we checked AI output:**
  - tests written before the code and seen failing first; expected values worked out by hand in
    `docs/acceptance.md` and re-computed by a separate script that does not import the app (ratios);
  - deliberate bugs, one at a time, to check that the tests fail;
  - revenue, total assets and net income of AAPL, MSFT and NKE (FY2025 and FY2026, 18 values) read in the
    10-K filings, page cited, and checked by `test_reconciliation_10k.py`;
  - two rounds of reviewer agents on pull request #16;
  - the page looked at in Chrome (screenshots at 1280 px and other widths) and the Excel file opened by François;
  - each member read the code of their slice and its decisions before the pull request.
- **One example where the AI was wrong, and how we caught it:** when year ends differ between companies, the first
  fix of the ratio table kept a 5-year calendar window (latest year minus 4), while the decision the AI wrote at
  the same time said "the 5 most recent fiscal years present". With a missing year, a real year disappeared from
  the table. Arthur ran a second review round of PR #16 with the code and test reviewer agents; they found the gap
  between the code and the decision, and Arthur had it fixed. The code now follows the decision, with a test.
  Other mistakes are listed below.

## Log

| Date | Who asked | What the AI contributed | How it was checked | Accepted / changed / rejected |
|---|---|---|---|---|
| 2026-11-20 | Arthur | Product interview: `docs/product.md`, `architecture.md`, `acceptance.md`, `plan.md`; proposed visuals, stack, thresholds and hand-worked answers CALC1–CALC13; raised 5 open points (missing issues, "not available" ratios, LLM vs budget, thresholds, leases); created issues #6–#9; walking skeleton in `app/` | 2 tests passed; server started, page HTTP 200 | Accepted; total debt changed by us to two versions; LLM comment rejected (paid) |
| 2026-11-20 | Arthur | Team guide `docs/guide-equipe.md` in French; checked branches and PRs; fixed the branch rule in `AGENTS.md` (`git switch`, not `gh issue develop`) and a first prompt per member | Arthur read and agreed the changes | Accepted; reviewer pairs proposed, to confirm by the team |
| 2026-11-20 | Arthur | Slice 2, data (#3, PR #4): SEC client (User-Agent, 10 requests/s, cache), XBRL tags for 13 items then 18, fiscal year from `end`, 350–380 day periods, latest filing wins; 47 then 79 offline tests; removed a lease-inclusive debt tag that counted leases twice | 5 deliberate bugs made tests fail; real run on AAPL, MSFT, NKE; 18 values reconciled with the 10-K by Arthur | Accepted; deriving missing items rejected (nothing derived) |
| 2026-11-20 | Arthur | Fix E8 (`fix/data-sec-unreachable`): readable `SecUnavailableError` when the SEC cannot be reached and nothing is cached; nothing written to the cache | 6 tests first (5 seen failing); real run with a refused connection | Accepted; no automatic retry |
| 2026-11-25 | Corentin | Slice 3, ratios (#6, PR #13): `compute_ratios`, 13 numbers per year in both debt versions, "not available" / "not meaningful" with reasons; 50 tests | Expected values re-computed by a separate script; 8 deliberate bugs made 1 to 19 tests fail; Corentin read the code and decisions | Accepted |
| 2026-11-26 | Maiwenn | Slice 4, flags (#7, PR #14): `thresholds.toml` editable without code, `apply_flags`, `overall_alert`; 63 tests (AC6, AC7, CALC12, every limit, bad files) | 7 deliberate bugs made 1 to 17 tests fail; CALC12 run through Corentin's real code (192 passed) | Accepted; "No flag" for a company with no ratio, and "not meaningful" not counted as red: proposals, to confirm by the team |
| 2026-11-26 | François | Slice 6a–6b, charts and Excel (#9, PR #15): comparison bars and 5-year lines (missing never drawn as 0, no line across gaps), Excel file with 4 sheets; proposed the display table format to Marc | 22 + 15 tests first; 4 deliberate bugs; charts looked at in Chrome (3 display fixes); Excel file opened and approved by François | Accepted |
| 2026-11-27 | Marc | Slice 5, dashboard (#8, PR #16): ticker checks, cards, coloured ratio table, "View underlying data", one error per ticker, light theme; SAMPLE DATA companies for page tests | 48 tests first; 10 deliberate bugs; page looked at in Chrome at 1280 px (4 fixes); François's charts run on the real table | Accepted |
| 2026-11-28 | Arthur | Review of PR #16 with code, test and interface reviewer agents (2 rounds); fixed every finding: 5 fiscal-year columns when year ends differ, form and errors, clearer cards and table, Excel-style rounding shared by screen and flags, 83 more tests | Each fix's tests seen failing first; the reviewer's surviving deliberate bugs now make tests fail; the test reviewer redid the new expected values by hand | Accepted, except the findings listed as open in `docs/plan.md` (notes width, "Green" with missing ratios) |
| 2026-11-28 | Arthur (with François's agreement) | Slice 6c: charts selector, the two charts and "Download Excel" in the real page; "Latest flag" words equal in Excel and on screen; a sentence when no company has a value for the chosen ratio | 9 + 5 page tests; 3 deliberate bugs; page run offline on the cached AAPL, MSFT, NKE files | Accepted; François to read the 6c lines before the merge |
| 2026-11-28 | Arthur | Compact top of page (`design/compact-top`): inputs on one aligned row, debt definition as two buttons, cards visible without scrolling at 1280 × 800 | 3 new tests (375 passed); screenshots at 4 widths and the empty and error states | Validated by Arthur; merged with PR #18 |
| 2026-11-28 | Arthur | Responsive, clean product-page look (`design/apple-style`): theme colours and pill buttons, system font, grey card tiles that wrap with the window, Deploy button, Streamlit menu (screencast recorder) and toolbars hidden, no Plotly toolbar | 4 new tests (379 passed); screenshots at 1440, 1280, 1000 and 390 px | Validated by Arthur; merged with PR #18 |
| 2026-11-28 | Arthur (team decision) | Overall alert "N/A" when 3 or more of the 6 flagged ratios are not available (`fix/alert-na-many-missing`); the AI first checked the real data and asked, because "N/A as soon as one is missing" would have made all 3 demo companies N/A | 3 tests first, 3 deliberate bugs caught; NKE now "N/A: 3 not available, 3 green flags" | Accepted by Arthur; Maiwenn to read the change of her module |
| 2026-11-28 | Arthur | Modern, responsive design (`design/modern-ui`): top bar, hero, panels, alert-colour lines, effects, empty-state tiles and example link; ratio table columns sized so notes are never cut. End-to-end run on the real cached AAPL, MSFT, NKE, offline | 3 new tests (385 passed), 4 deliberate bugs caught; screenshots at 4 widths; 2 layout mistakes seen on screenshots and fixed | Arthur's look pending |
| 2026-11-28 | Maiwenn | Slice 7 documents: root `README.md` (install, run, data, flags, known limitations) and this file, merged from `docs/ai-log/` (details: `docs/ai-log/docs-slice-7-readme-ai-usage.md`) | Every fact checked against `docs/product.md`, `plan.md`, `thresholds.toml`, the AI logs and the screen labels in the code; fresh-copy test (new Python 3.12 environment, install, 375 tests passed, app started on localhost); no secret found in the files | To be read by the team |

## AI mistakes and how they were caught

| Slice | Mistake | How it was caught |
|---|---|---|
| 1 | The first Streamlit run listened on the whole network, not only the laptop | The AI read the server log; restricted to `localhost` |
| 1 | The AI tried to move the `.env` file | The project's permission rules blocked it; Arthur moved it himself |
| 2 | `get_user_agent` read `.env` when the module was imported, so the tests could not isolate it | Seen while writing the tests; fixed in a separate commit |
| 2 | The AI reported "75 passed", but 2 tests came from an iCloud duplicate file | The count dropped to 73 after the copies were moved; the AI counted the tests per file and corrected the plan |
| 2 | The first 10-K parser found no MSFT income statement (title split in the HTML) | Found the page through the 10-K's own index |
| 2 | Shell commands that did nothing or failed (`sed` with zsh, `$M:refs` in a push) | Re-checked with `grep`; read the full error; nothing had changed on GitHub |
| 3 | A file written with Windows line endings; test names in `acceptance.md` that pytest did not use | Git's warning; re-reading the update |
| 4 | An unused import in `flags.py` | Seen by the AI while re-reading the file |
| 5 | The page read the cache again on every redraw | A test caught it (the debt selector must not touch the SEC files) |
| 5 | A test that could never fail (`or True`) | Replaced before running, after checking how AppTest shows a status box |
| 5 | Removing a unit from a card label left a "not available" value with no unit | An existing page test failed |
| 5 | A 5-year calendar window instead of the "5 most recent fiscal years present" | Code and test reviewer agents, second round of PR #16 |
| 5 | A broad `except Exception` on the page could hide a test that reached the internet | Code and test reviewer agents, second round; the test helper now refuses an "Unexpected problem" box |
| 6 | Three display mistakes in the charts (minus sign cut off, label overlap, grey notes on a dark page) | Only seen on screenshots, not by the tests; a test now covers the first one |
| Design | A blank first screenshot; a top padding that barely moved the title; a style sheet added with `st.html` that Chrome ignored; a card width rule on the wrong box that cut the cards at the bottom; charts side by side that cut the trend chart's "n/a" notes | All seen by looking at the screenshots or the page in Chrome |
