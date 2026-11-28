# AI log: 8-dashboard-ticker-input-summary-cards-and-5-year-ratio-table

Issue #8 "Dashboard: ticker input, summary cards and 5-year ratio table" (slice 5 of `docs/plan.md`). Tool: Claude
(Claude Opus 5.5), following the `build-feature`, `design-interface` and `test-and-check` skills of the project.
Marc asked Claude to do the whole slice (decision log of `docs/architecture.md`, 2026-11-27).

## Session 1 (2026-11-27)

### What the AI did
- Read the team guide, `docs/plan.md`, `docs/product.md` (visuals 1, 4 and 6, rules for missing values and rounding),
  `docs/architecture.md` (contracts, errors of the data part), `docs/acceptance.md` (AC1–AC3, AC5, AC5b, AC7, V1–V3,
  E7–E11), the code of slices 2 to 4, and François's branch 9 (`charts.py`, `export.py`, the display format he
  proposed and its samples), so the page and his charts read the same table.
- Brought the branch up to date with `main` (fast-forward to the merge of PR #14).
- Wrote `app/tests/synthetic_company.py`: SAMPLE DATA companies in the SEC companyfacts format, with figures chosen by
  hand. ALFA is the example company of `docs/acceptance.md` in FY2026; BETA tags no D&A and no interest expense, like
  NKE; FRGN files only 20-F reports. The page can therefore be tested offline, through the real data, ratio and flag
  code.
- Wrote the tests first: `app/tests/test_display.py` (35 tests). Expected values are worked out by hand in the
  comments (for example FY2025: EBITDA 900 + 200 = 1,100; net debt 2,300 − 500 = 1,800; 1,800 ÷ 1,100 = 1.64x, so the
  card shows "-0.22x vs FY2025"). They failed first, because the module did not exist.
- Wrote `app/creditlens/display.py`: rounding (the same rule as `flags.py`, never "-0"), screen texts, labels, the
  display table in François's format, the "View underlying data" table, the summary cards with the change vs the
  prior fiscal year, the wide ratio table with a "Notes" column, and the ticker checks.
- Wrote the page `app/streamlit_app.py` and its journey tests `app/tests/test_app.py` (13 tests, replacing the 2
  skeleton tests): empty state, 6 tickers refused without any download, cards, table, underlying data, cache date,
  the debt selector (cards and table switch, nothing downloaded again), and one error per ticker (not found, no 10-K,
  SEC unreachable, settings missing) while the other companies stay on the page.
- Full suite: 238 passed.
- Checked that the tests catch mistakes: 10 deliberate bugs, one at a time, each made at least one test fail (missing
  value shown as 0, "-0", 1 decimal for ratios, 6 tickers accepted, debt selector ignored, wrong prior year, missing
  year column dropped, wrong USD m conversion, one ticker's error stopping the page, 6 tickers downloaded anyway).
- Looked at the page in Chrome at 1280 px with 5 SAMPLE DATA companies, then with errors and the lease version. Fixed
  4 problems found on the screenshots:
  - the alert badge cut its text ("3 not avail…"): now a coloured line that wraps (AC7 needs the count);
  - the Run button and the radio were red (Streamlit default): a neutral blue in `config.toml`, so red means a flag
    only; the theme is set to light as `product.md` asks;
  - missing values in bold made the cards very tall: "not available" in bold, the reason under it;
  - the "Notes" column was cut off: the company name is hidden in the table (the cards give it).
  No sideways scrolling, no error in the browser console.
- Ran François's `charts.py` and `export.py` (branch 9, unchanged) on the real display table: both charts draw, BETA
  shows "n/a" without a bar, the Excel file has its 4 sheets. With his tests added on a copy: 275 passed.

### Mistakes caught
- A test expected `None` for a missing XBRL tag; pandas stores it as an empty value (NaN). The test was corrected
  (`export.py` already treats both as an empty cell).
- The first version of the page read the ticker list from the cache again on every redraw, to show the cache date; a
  test caught it (the debt selector must not touch the SEC files). The dates are now read once, at Run.
- AppTest does not give the keys of the tables; the tests find them by their order on the page.

### What remains for people
- Marc: read the plan, the code and the screenshots, open the page yourself (`app/README.md`), and approve.
- A real run on AAPL, MSFT and NKE needs `app/.env` (slice 7).
- François (step 6c): place the charts and the "Download Excel" button where `streamlit_app.py` says "Slice 6". They
  read `display_tbl`, `underlying`, `alerts` (`alerts[t].text` for `build_excel`) and `thresholds`.
- The project's own browser check is not installed (about 150 MB): a team decision.

## Session 2 (2026-11-28): review of PR #16 and a fix

### What the AI did
- Arthur reviewed PR #16 in place of François and ran three read-only reviewer agents (code, tests, interface)
  on commit ab83d3e, in an isolated checkout of that commit (238 passed there).
- The code reviewer found one major problem, reproduced with two SAMPLE DATA companies: when year ends differ
  (September and December), the ratio table showed 6 fiscal-year columns, against AC5, and "Latest flag" could
  sit next to a "no data" cell without saying its year.
- At Arthur's request, wrote 4 tests first (seen failing: 6 columns), with the SAMPLE DATA companies SEPT and DECM
  added to `tests/synthetic_company.py` and expected values worked out by hand (1,800 / 1,200 = 1.50x, green;
  900 / 1,200 = 0.75x, red). Then changed `display.py`: `table_years` keeps the 5 most recent fiscal years,
  `left_out_years_text` writes the sentence under the table title, and "Latest flag" names its year when it is
  not the last column ("red (FY2025)"). The page shows that sentence. 242 passed.

### The new functions, in simple words
- `table_years(display)`: lists the fiscal years of the table (at most the 5 most recent) and the older years
  left out.
- `left_out_years_text(display)`: the sentence "Only the 5 most recent fiscal years are shown; left out: FY2021.",
  or nothing when no year is left out.

- Then, at Arthur's request ("Tout corriger"), fixed every other finding in 5 commits, each with its tests seen
  failing first (except the last commit, which only adds tests for code that was already right):
  1. input and errors: the field and Run are a form (Enter runs), "Results for:", BRK.B = BRK-B, the input error
     escaped, an unexpected error stops only its ticker, the same error shown once, a progress box in error when
     nothing could be loaded, clearer messages (unknown ticker, no 10-K, HTTP 404, damaged cache file);
  2. clearer cards and table: what the alert covers, "(better)"/"(worse)", normal text colour instead of grey
     captions, the label ", incl. leases", numbers without unit in the table, shorter notes with year ranges, "n/a"
     and "–" in "Latest flag", a legend, headings, numeric values in the underlying data;
  3. rounding halves up as Excel's ROUND, one rule for screen and flags (`flags.shown_value`);
  4. shared names imported from `ratios.py` and `flags.py`, the cache date read by the data part
     (`sec_client.cache_saved_on`), a page test for AC6;
  5. the tests the test reviewer found missing, with 6 new SAMPLE DATA companies and their hand working in
     `docs/acceptance.md` ("Known answers of the SAMPLE DATA companies").
- Re-injected the 10 deliberate bugs that had passed the suite in the review: each now makes 1 to 12 tests fail.
- Ran the page offline on the cached SEC files of AAPL, MSFT and NKE: no error, 5 year columns, the new notes and
  alert line. 311 passed.

### The new functions, in simple words (session 2, continued)
- `years_text(years)`: writes years in short form, "FY2022–FY2025" for consecutive years.
- `table_caption(display, incl_leases)`: the legend under the table title (what "no data", "n/a", "–" and the
  colours mean).
- `cell_style(flag)`: the background colour of a table cell for its flag (the same colours as the Excel file).
- `_latest_flag_word(...)`: the word of the "Latest flag" column for one row.
- `flags.shown_value(value, unit)`: rounds a value as the screen shows it, halves up like Excel; the colours and the
  numbers both use it.
- `sec_client.cache_saved_on(ticker)`: the date the company's file was saved in the cache, or nothing.
- In the page: `grouped_errors(errors)` puts tickers with the same error in one box; `plural(count, word)` writes
  "1 company" / "2 companies".

### Mistakes caught (session 2)
- Removing the unit from the card label (to avoid "(incl. leases) (x)") left a "not available" value with no unit at
  all, against V1. An existing page test caught it; the unit is back and the label became ", incl. leases".
- A first version of the progress-box test ended with `or True`, so it could never fail. It was replaced before
  running, once the AI had checked how AppTest shows `st.status` (a `Status` block with `label` and `state`).
- A damaged-cache test used a 13-digit CIK file name; the test failed for that reason, not for the code. Fixed to the
  10-digit name.

### What remains for people
- Marc: read the fixes (`display.py`, the page, the tests, `docs/acceptance.md`) before merging PR #16.
- Arthur or Marc: look at the page at 1280 px with AAPL, MSFT and NKE, in both debt definitions (long notes, cards).
- The team: decide whether a company with leverage and coverage "not available" may be "Green" (AC7).
