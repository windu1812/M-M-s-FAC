# AI log: 6-ratios-compute-ebitda-total-debt-net-debt-and-the-credit-ratios

Issue #6 "Ratios: compute EBITDA, total debt, net debt and the credit ratios" (slice 3 of `docs/plan.md`). Tool:
Claude Code (Claude Opus 5.5), skills `build-feature` and `test-and-check`.

## Session 1 (2026-11-25)

### What the AI did
- Read the team guide, issue #6, `docs/product.md` (formulas), `docs/architecture.md` (contract of
  `compute_ratios`), `docs/acceptance.md` (CALC1–CALC13, E1–E11) and the data module, so that the input is exactly
  what `get_financials` returns.
- Set up `app/.venv` with Python 3.12. Only Python 3.14 (Miniconda base) was on this computer. The AI created a
  separate conda environment with Python 3.12.16 from conda-forge (nothing installed in the Miniconda base), then
  `app/.venv` from it. The 79 existing tests passed before any change.
- Wrote the sample table `app/tests/fixtures/ratios_sample.csv`. It is the example company of `docs/acceptance.md`,
  marked SAMPLE DATA, in the same columns as `get_financials` (amounts in USD).
- Wrote the tests first: `app/tests/test_ratios.py`, 50 tests.
  - the contract: columns, 13 metrics per year, their units;
  - the known answers CALC1–CALC11 and CALC13;
  - the edge cases E1–E6b and E11;
  - a run on the real output of the data module (MSFT extract);
  - bad input: an amount not in USD, an item given twice.

  They failed first, because the module did not exist yet.
- Cross-checked every expected value with a separate small script that does not import the app (plain
  arithmetic). All values agreed with the hand working of `docs/acceptance.md`.
- Wrote `app/creditlens/ratios.py`. All 50 tests passed, then the full suite (129 passed).
- Checked that the tests really catch mistakes. The AI broke the code on purpose in 8 ways, one at a time; each
  made between 1 and 19 tests fail:
  - EBITDA without D&A;
  - the lease version forgets operating leases;
  - EBITDA = 0 accepted;
  - a missing value shown as 0;
  - the margin as a fraction;
  - no USD → USD m conversion;
  - negative equity not caught;
  - the "not reported" note not carried to net debt.

  The code was then restored and checked identical.
- Wrote the decisions on units and reasons in `docs/architecture.md`, and updated Coco's line and the progress log
  of `docs/plan.md` and the criteria of slice 3 in `docs/acceptance.md`.

### The functions of `ratios.py`, in simple words
- `compute_ratios(financials)`: the main function. It takes the table of the data module (one line per year and per
  item, in dollars). It gives back one line per company, per year and per ratio: the value, its unit, its status
  ("ok", "not available" or "not meaningful") and the reason.
- `ratios_for_year(values)`: computes the 13 numbers of one year from the inputs in USD millions.
- `usd_to_usd_m(value)`: divides by 1,000,000 (CALC10).
- Small helpers, one per number: `_ebitda`, `_total_debt` (used twice, once per debt version), `_net_debt`,
  `_net_debt_to_ebitda`, `_debt_to_equity`, `_ratio` (interest coverage and current ratio), `_ebitda_margin`,
  `_free_cash_flow`. Each one first checks that its inputs exist, then the denominator, then computes.
- `_inputs_in_usd_m`: reads one year of the data table. It stops with a clear error if an amount is not in dollars
  or if an item is given twice, so that a wrong number never goes into a ratio.

### What the human decided or checked
- Coco asked the AI to do Coco's tasks from the team guide, with commits and a push on a separate branch
  (2026-11-25). The delegation is written in the decision log of `docs/architecture.md`.
- Coco read the changes (`ratios.py`, the tests and the decisions of 2026-11-25 in `docs/architecture.md`) and
  asked to mark pull request #13 as ready for review (2026-11-25).

### AI mistakes and how they were caught
- The first version of the acceptance update was written by a Python script with Windows line endings (CRLF). Git
  warned about it, and the AI rewrote the file with LF before committing.
- The statuses in `docs/acceptance.md` cited test names like `test_known_answer[CALC1]`, but pytest named them
  `test_known_answer[CALC1-ebitda-1200-1e-09]`. The AI noticed it while re-reading the update and gave each case
  its CALC id, so that `pytest -k CALC4a` runs one case.

### Open points for the team
- **Maiwenn (slice 4):** the EBITDA margin is in percent (20.0), so its thresholds are 20 and 10, not 0.20 and
  0.10. "Not available" and "not meaningful" rows have an empty value (NaN): no flag.
- **Marc (slice 5):** the values are not rounded. `status` and `reason` can be shown as "not available: D&A not
  reported". A row with status `ok` can still have a note in `reason` (for example "short-term borrowings not
  reported").
- A negative interest expense would give a ratio with the wrong sign. The companies tag interest expense as a
  positive amount, so the AI did not add a rule; to be decided if it ever happens.
- No real run on AAPL, MSFT and NKE yet: it needs `app/.env` with `SEC_USER_AGENT`, which only Coco creates.
