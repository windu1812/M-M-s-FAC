# Implementation plan

Small slices, in order. Each slice is visible to a user or removes a real risk, takes one sitting, and ends with
checks and a commit. **Each member updates only the line of their own slice.**

## Slices

| # | Slice | GitHub issue | Owner | Acceptance criteria | Skills | Status |
|---|---|---|---|---|---|---|
| 1 | Walking skeleton: `app/` folder, Streamlit page with title, ticker field and Run button (no data yet), one passing `AppTest`, `app/README.md` | – (branch `docs/product-interview`) | Arthur | V2 | product-interview | done (2026-11-20, commit a665a3e; merged with PR #10) |
| 2 | **Data:** move PR #4 into `app/creditlens/data/`; add net income, the current portion of long-term debt, short-term borrowings (commercial paper) and operating and finance lease liabilities, without double counting leases already inside long-term debt (both debt versions need them); reconcile revenue, total assets and net income with the 10-K (AAPL, MSFT, NKE) | #3 | Arthur | AC4, E7–E10 | build-feature, integrate-api, test-and-check | done (2026-11-20, commits 7b9fba9, bd88239, 36cbe7d; merged with PR #4); E8 error: branch `fix/data-sec-unreachable` |
| 3 | **Ratios:** `compute_ratios` for the 9 numbers, the 4 debt-based ones in both versions (financial debt only / including leases and short-term borrowings), with the "not available" and "not meaningful" rules | #6 | Coco | AC5, CALC1–CALC11, CALC13, E1–E6b, E11 | build-feature, test-and-check | done (2026-11-25, commits 55cb7af, 21847a7); PR #13 to review |
| 4 | **Flags:** `thresholds.toml`, `apply_flags`, `overall_alert` (same thresholds for both debt versions) | #7 | Maiwenn | AC6, AC7, CALC12 | build-feature, test-and-check | done (2026-11-26); PR to review by Coco |
| 5 | **Dashboard:** ticker input and its checks, summary cards, ratio table with colours, "View underlying data", empty / loading / error states, debt definition selector | #8 | Marc | AC1–AC3, AC5b, AC7, V1–V3 | build-feature, design-interface | todo |
| 6 | **Charts and Excel:** comparison bars and 5-year lines with the ratio selector; Excel export with 4 sheets, both debt versions in the Ratios sheet | #9 | François | AC8, AC9 | build-feature, design-interface, test-and-check | todo |
| 7 | Integration and demo: run AAPL, MSFT and NKE end to end, browser check, warm the cache, update the root `README.md` (install, run, data, known limitations), merge the AI logs into `AI-USAGE.md` | – | Arthur (lead, end-to-end run and demo); Maiwenn (README, `AI-USAGE.md`); all test | AC1, V1 | test-and-check, review-changes, prepare-deploy | todo |

**Order and parallel work:**
- Slice 1 is merged first.
- Slices 3 to 6 can then start at the same time. Each member uses a small sample table that follows the contracts in
  `architecture.md`, so nobody waits for another member's code.
- Slice 2 has no dependency.

**Proposed dates `[to confirm]`:**
- slices 2 to 6 opened as pull requests by Thursday 26 November;
- integration (slice 7) on 27–29 November;
- demo rehearsal on 30 November;
- hand-in by Tuesday 1 December 2026, 23:59.

Status values: `todo`, `in progress`, `done (<date>, commit <short hash>)`, `blocked: <reason>`.

## Progress log

| Date | Slice | What changed | Checks run and results | Open problems |
|---|---|---|---|---|
| 2026-11-20 | 2 | PR #4: SEC client, XBRL extraction (13 items), 47 offline tests | pytest: 47 passed; real run on AAPL, MSFT and NKE | Built in `src/` before the starter: must move to `app/` |
| 2026-11-20 | 1 | Product documents agreed; issues #6–#9 created; walking skeleton in `app/` (Streamlit page, `app/.venv` with Python 3.12, `AppTest`) | pytest: 2 passed; Streamlit server started, `/_stcore/health` ok, page HTTP 200 on localhost | Browser check not installed (needs a ~150 MB download, the student's OK); page not yet seen in a browser |
| 2026-11-20 | 2 | Data module moved into `app/creditlens/data/`; 5 items added (net income, current portion of debt, short-term borrowings, operating and finance leases); lease-inclusive debt tag removed (double counting); revenue, total assets and net income reconciled with the 10-K of AAPL, MSFT, NKE | pytest: 73 passed (18 reconciliation checks; the fy/end bug makes all 18 fail); real run on AAPL, MSFT, NKE | None. Arthur checked the 10-K pages and the SEC access terms on 2026-11-20 |
| 2026-11-20 | 2 | E8 data part: `SecUnavailableError` with a readable message when a file is not in the cache and the SEC cannot provide it (no internet, timeout, error status, answer not JSON); nothing is written to the cache. Plan statuses updated after the merge of PR #10 and PR #4 | pytest: 79 passed (6 new tests, 5 seen failing first); real run with a refused connection and an empty cache: clear message, cache untouched | No retry. With `refresh=True` and the SEC down, the error is raised even if an older copy is in the cache |
| 2026-11-25 | 3 | `app/creditlens/ratios.py`: `compute_ratios` gives 13 rows per company and fiscal year (the 9 numbers, the 4 debt-based ones in both versions) with the "not available" / "not meaningful" rules and their reasons; sample `app/tests/fixtures/ratios_sample.csv` (SAMPLE DATA) | pytest: 129 passed (50 new in `test_ratios.py`, seen failing first: module missing); 8 deliberate bugs in the code each made 1 to 19 tests fail; known answers recomputed by a separate script that does not import the app | No real SEC run yet (needs `app/.env`). Units of the output to note for slices 4–6: see the decision of 2026-11-25 in `architecture.md` |
| 2026-11-26 | 4 | `app/config/thresholds.toml` (the agreed limits, editable without code), `app/creditlens/flags.py` (`load_thresholds`, `apply_flags`, `overall_alert`, `flagged_metrics`), sample `app/tests/fixtures/flags_sample.csv` (SAMPLE DATA, in the format of `compute_ratios`) | pytest: 141 passed, 1 skipped (63 new in `test_flags.py`: 62 passed, 1 skipped; seen failing first: module missing); the skipped test runs CALC12 through Coco's `compute_ratios` and passes once PR #13 is merged (checked: 192 passed with it); 7 deliberate bugs in `flags.py` each made 1 to 17 tests fail | The alert of a company with no flag at all is "No flag" (level empty), not green: to confirm by the team. Marc (slice 5) shows `alert.text` and colours the card with `alert.level` |

## Known problems and open questions

1. **Owners** (set on 2026-11-20 by Arthur; members may swap if they agree): Arthur #3 and slice 7, Coco #6,
   Maiwenn #7 and the hand-in documents of slice 7, Marc #8, François #9. Each member's branch already exists,
   linked to the issue and starting from `main`: `git switch <branch>`, never `gh issue develop` (see
   `docs/guide-equipe.md`, sections 1 and 4).
2. **Several headline ratios are "not available" for the demo companies.** The real run of PR #4 showed what the
   companies do not tag in standard XBRL:
   - MSFT tags no total D&A, so EBITDA, Net debt / EBITDA and EBITDA margin are not available;
   - NKE tags no operating income and no gross interest expense, so EBITDA, Net debt / EBITDA, interest coverage
     and EBITDA margin are not available;
   - AAPL tags no interest expense after FY2023, so interest coverage is not available for FY2024–FY2026.

   Decided on 2026-11-20: show "not available" with the reason, and derive nothing. The demo explains why.
3. **Net debt / EBITDA "including leases" is slightly conservative for companies with large leases.** Lease
   liabilities are added to debt, but the lease cost is not added back to EBITDA (see `product.md`). This is written as a known limitation
   in the root README in slice 7.
4. **The live demo depends on the network.** The cache is warmed before the demo (slice 7). The app then works
   offline from the cache.

Resolved on 2026-11-20:
- the 4 missing issues were created (#6 to #9);
- the LLM comment is dropped because no paid service is allowed;
- the thresholds, alert rule, "not meaningful" rule and rounding are agreed;
- total debt is computed in two versions, financial debt only (default) and including leases and short-term
  borrowings, with a selector. This replaces the earlier "leases always included" choice.
