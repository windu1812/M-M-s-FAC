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

## Reviewed by the student
- [ ] François read the code and this log.
