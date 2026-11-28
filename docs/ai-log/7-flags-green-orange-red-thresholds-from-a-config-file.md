# AI log: 7-flags-green-orange-red-thresholds-from-a-config-file

Issue #7 "Flags: green / orange / red thresholds from a config file" (slice 4 of `docs/plan.md`). Tool: Claude
(Claude Opus 5.5), following the `build-feature` and `test-and-check` skills of the project.

## Session 1 (2026-11-26)

### What the AI did
- Read the team guide, `docs/plan.md`, `docs/product.md`, `docs/architecture.md` (contracts of `apply_flags` and
  `overall_alert`), `docs/acceptance.md` (thresholds table, overall alert rule, CALC12, AC6, AC7) and Coco's branch
  (PR #13: `ratios.py` and its notes for slice 4), so that the input is exactly what `compute_ratios` returns.
- Wrote `app/config/thresholds.toml` with the limits agreed on 2026-11-20, one section per ratio, with comments
  explaining how to change them.
- Wrote the sample table `app/tests/fixtures/flags_sample.csv`, marked SAMPLE DATA, in the columns of
  `compute_ratios`: the example company of `docs/acceptance.md` (FY2026), an older red year of the same company, and
  a company with gaps (not available, not meaningful, two red ratios). The slice therefore does not wait for PR #13.
- Wrote the tests first: `app/tests/test_flags.py`, 63 tests:
  - the thresholds file has the agreed values (written out in the test, not read from the code);
  - CALC12 in both debt versions, flag by flag, and the overall alert "Orange: 1 orange flag";
  - every limit: exactly on the limit takes the better colour, just past it takes the worse one, for the 6 ratios;
  - the flag follows the rounded value shown on screen (2.004 → "2.00x" → green);
  - AC6: changing the file changes the flag, without any code change;
  - errors in the file (wrong direction, missing limit, text instead of a number, limits in the wrong order, unknown
    key, missing ratio, file that is not TOML) give a readable message;
  - the overall alert: red / orange / green, counts of "not available" and "not meaningful", latest year only, the
    debt version, a company with no flag at all, an unknown ticker;
  - one test runs CALC12 through Coco's real `compute_ratios`. It is skipped until PR #13 is merged.

  They failed first, because the module did not exist yet.
- Wrote `app/creditlens/flags.py`. The full suite: 141 passed, 1 skipped. With Coco's `ratios.py` and its tests added
  on a copy, 192 passed (the skipped test passed too).
- Checked that the tests really catch mistakes. The AI broke the code on purpose in 7 ways, one at a time; each made
  between 1 and 17 tests fail:
  - a value on the green limit counted as orange;
  - no rounding before the comparison;
  - "not available" rows flagged;
  - the debt selector ignored by the alert;
  - "green" when no ratio has a flag;
  - the oldest year used instead of the latest;
  - limits in the wrong order accepted.

  The code was then restored and checked identical.
- Updated Maiwenn's line and the progress log of `docs/plan.md`, the criteria AC6, AC7 and CALC12 in
  `docs/acceptance.md`, the contract of `overall_alert` and three decisions in `docs/architecture.md`.

### The files and functions, in simple words
- `app/config/thresholds.toml`: the limits of the colours. One block per ratio: is lower or higher better, the green
  limit, the orange limit. To change a colour, change a number here and click Run again; no Python to touch.
- `load_thresholds(path)`: reads that file and checks it. If a number is missing or in the wrong order, it stops
  with a clear message rather than giving wrong colours.
- `flag_for(value, unit, rule)`: gives the colour of one number. It first rounds the number as the page shows it,
  then compares it with the limits. On the limit, the better colour wins.
- `apply_flags(ratios, thresholds)`: takes Coco's ratio table and adds a `flag` column. Only the 6 ratios get a
  colour; amounts (EBITDA, total debt, net debt) and "not available" / "not meaningful" rows get an empty flag.
  The same limits are used for both debt versions.
- `flagged_metrics(incl_leases)`: the list of the 6 ratios that get a colour, for the chosen debt version.
- `overall_alert(flagged, ticker, incl_leases)`: the alert of one company on its card, for its latest year. Red if
  one ratio is red, otherwise orange if one is orange, otherwise green. The text also counts the missing ratios,
  for example "Red: 2 red flags, 3 not available, 1 not meaningful".
- `Alert`: the small result of `overall_alert`: `level` (the colour), `text`, the year and the counts.

### What the human decided or checked
- Maiwenn asked the AI to do Maiwenn's part of the team guide and to explain step by step how to put it on GitHub
  (2026-11-26).
- To be checked by Maiwenn before the pull request: read `thresholds.toml`, `flags.py` and the three decisions of
  2026-11-26 in `docs/architecture.md`, and run the tests on her computer.

### AI mistakes and how they were caught
- The first version of `flags.py` imported a module it never used (`math`). The AI saw it while re-reading the
  file and removed it.

### Open points for the team
- **Team:** a company with no flag at all (every ratio "not available") gets the level "" and the text
  "No flag: 6 not available", not "green". This is a proposal; to confirm.
- **Team:** "not meaningful" (for example negative equity) is counted apart from "not available" in the alert
  text, and does not count as red. A company with negative equity can still be green overall. To confirm.
- **Marc (slice 5):** colour the card with `alert.level` and show `alert.text`; colour the table cells with the
  `flag` column and write the flag as a word in the "Latest flag" column. Use the same rounding as `flags.py`
  (2 decimals for x, 1 for %), otherwise a colour and its number may disagree.
- **François (slice 6):** the limits for the reference lines of the bar chart are in `load_thresholds()` (`green`,
  `orange`); free cash flow has no orange limit (`None`).
- **After PR #13 is merged:** E1 in `docs/acceptance.md` can say that "no flag" is passing (test:
  `test_e1_not_available_and_not_meaningful_get_no_flag`). It was not changed here, to avoid a conflict with
  Coco's line.
