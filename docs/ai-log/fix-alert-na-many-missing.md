# AI log: fix/alert-na-many-missing

Branch `fix/alert-na-many-missing`, from `main` (2026-11-28). Asked by Arthur (lead) for the team. Tool: Claude Code
(Claude Opus 5.5), skill `build-feature`. The code is Maiwenn's module (`flags.py`, slice 4).

## What the AI did (2026-11-28)
- Arthur passed on the team's decision on the open review finding "NKE is Green with 3 ratios not available":
  "N/A when ratios are not available". The AI checked the real cached data first: AAPL (1 missing), MSFT (2) and
  NKE (3) all have missing ratios, so "N/A as soon as one is missing" would have turned the whole demo into N/A.
  It asked; Arthur answered "with one or two N/A keep the rating; with many N/A put N/A, we cannot rate".
  Read as: 3 or more of the 6 "not available" → "N/A".
- Wrote the tests first (2 seen failing), then changed `overall_alert`: an empty level (grey card) and the title
  "N/A", with the flags that exist still counted ("N/A: 3 not available, 3 green flags"). Replaces "No flag".
- 3 deliberate bugs each made 1 test fail. 382 passed. Real data: AAPL and MSFT Orange, NKE N/A.
- Also ticked François's box in `docs/ai-log/9-charts-and-excel-export.md`: Arthur says François read the step 6c lines.

## What the human decided or checked
- Arthur: the rule (limit 3 of 6). Maiwenn: to read the change of her module.
