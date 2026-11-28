# AI log: 9-charts-and-excel-export

Branch `9-charts-and-excel-export` (issue #9, slice 6). Owner: François. Tool: Claude Code (Claude Opus 5.5), skill
`build-feature`.

## What the AI did

### 2026-11-26, step 6a: the charts
- Read issue #9, `docs/guide-equipe.md`, the product, architecture and acceptance documents, and the open branches
  of Coco (#13) and Maiwenn (#14) to learn their output formats.
- Found that `display.py` (Marc, slice 5) does not exist yet. Proposed a format for the display table that the
  charts and the Excel file read, recorded in `docs/architecture.md` for Marc to confirm, and made a sample of it
  (`app/tests/fixtures/charts_sample.csv`, SAMPLE DATA).
- Created `app/.venv` on François's Windows machine from the Anaconda Python 3.12.4 (nothing installed into
  Anaconda itself).
- Wrote 22 tests first (`app/tests/test_charts.py`), seen failing (module missing), then wrote
  `app/creditlens/charts.py`. The tests check the honesty rules: missing is never drawn as 0, a real 0 is drawn,
  lines are not joined across gaps, only real years, the unit on every axis, the zero line, threshold lines, AC8.
- Checked that the tests catch real mistakes: two deliberate bugs (missing drawn as 0; lines joined across gaps)
  made 7 and 1 tests fail; the code was then restored.

### 2026-11-26, step 6b: the Excel file
- Proposed the layout of the 4 sheets (Summary, Ratios, Financials, Notes) and the format of the underlying-data
  table, added to the decision of 2026-11-26 in `docs/architecture.md` (to confirm by Marc).
- Wrote 15 tests first (`app/tests/test_export.py`), seen failing (module missing), then wrote
  `app/creditlens/export.py`. The main test reads the file back and compares every Ratios cell with the display
  table (AC9). Numbers stay numbers with an Excel format that shows the screen rounding; a missing value is written
  as its reason, never as 0.
- Two deliberate bugs (missing written as 0; Summary ignoring the debt definition) made 5 and 1 tests fail; the code
  was then restored.

### 2026-11-26, charts seen in the browser (trial page with the SAMPLE DATA)
- Wrote the lines for Marc's page and ran them in a throwaway trial page (`AppTest`, then Chrome at 1280 px).
- Looking at the screenshots showed 3 display mistakes that the tests had not caught: the minus sign of "-0.20x"
  was cut off at the edge of the bar chart, the "SAMPLE DATA" mark overlapped the orange threshold label, and the
  grey notes were hard to read on a dark page. Fixed in `charts.py`; a test now checks the first one.
- Checked AC8 by hand on the trial page: picking "Interest coverage" switches both charts; BETA has no bar and no
  point, with "n/a (not available: interest expense not reported)".
- François downloaded the Excel file from the trial page, opened it and approved the layout.

### 2026-11-28, step 6c: the charts and the Excel button in the real page (done by Arthur, with François's agreement)
- Arthur asked Claude to do François's step 6c; François had agreed. Claude asked first, because the team rules
  say not to touch another member's module without asking, and recorded the delegation in `docs/architecture.md`.
- Merged Marc's branch (PR #16, slice 5, not yet merged into `main`) into this branch, so the page exists here.
  Resolved the 2 conflicts (`docs/plan.md`, `docs/architecture.md`) by keeping every member's lines in date order.
- Wrote 9 page tests first (`app/tests/test_charts_page.py`, AppTest, SAMPLE DATA companies ALFA and BETA of
  Marc), with expected values worked out by hand in `docs/acceptance.md` (CALC4a, CALC4b, CALC6); 8 seen failing
  (selector, charts and button missing).
- Added the lines in the "Slice 6" part of `app/streamlit_app.py` only: the "Ratio shown in the charts" selector,
  the two charts and the "Download Excel" button. Nothing is computed in the page.
- Three deliberate bugs (charts ignoring the debt definition, Excel Summary ignoring it, 5-year chart stuck on
  one ratio) each made 1 test fail; the page was then restored.
- Ran the page offline on the cached SEC files of AAPL, MSFT and NKE: the 6 ratios with both debt definitions,
  no error; the missing values (MSFT D&A, NKE operating income, AAPL interest after FY2023) are "n/a", never 0;
  the Excel file has its 4 sheets.
- Not done by the AI: looking at the page in a browser (no browser tool in this session).

## Reviewed by the student
- [x] François read the code and this log (2026-11-26; `comparison_bar_chart`, `trend_line_chart` and `build_excel`
  explained to him function by function).
- [ ] François read the step 6c lines of `app/streamlit_app.py` and `app/tests/test_charts_page.py`, and can
  explain them (to do before the merge).
