# AI log: fix/search-row-responsive

Branch `fix/search-row-responsive`, from `main` after PR #19 (2026-11-28). Tool: Claude Code (Claude Opus 5.5), skills
`review-changes`, `debug-issue`, `design-interface`, `test-and-check`.

## What the AI did (2026-11-28)
- Arthur sent a screenshot: "Run" cut to "R..." and the leases option cut with "...". Reproduced on screenshots at
  700 px. Cause: the search panel used fixed-ratio `st.columns`, which Streamlit only stacks below 640 px. Replaced by
  a row that wraps; Run keeps the width of its word next to the field; a debt choice wraps on two lines on a phone.
  Test rewritten first (seen failing on the old page). Checked at 360, 390, 700, 1000, 1280 px, and that switching the
  debt definition works in Chrome.
- Ran the code, test and interface reviewer agents in parallel on the two commits of PR #19. No blocker, 3 major,
  25 minor. Arthur decided the rule questions: a known red flag stays "Red" even with 3 or more not available; "N/A"
  also when nothing could be flagged. Fixed every other finding but four (listed open in `docs/plan.md`).
- 389 passed; 3 deliberate bugs in the new rule each caught.

## AI mistakes and how they were caught
- The redesign was not looked at between 700 and 1000 px, so the cut "Run" button was missed; Arthur saw it.
- The first fix targeted every button of the debt control, including the "?" icon, which shifted its label 14 px down:
  found by measuring the boxes in Chrome. A second try used a selector that matched nothing (the option buttons have
  no test id): seen on the 390 px screenshot, where the text was cut again.
- The "N/A" rule hid known red flags behind grey; the AI had followed the wording of the request without raising it.
  The reviewers raised it and Arthur chose to keep red visible.

## What the human decided or checked
- Arthur: red stays visible; "N/A" replaces "No flag"; table toolbars stay hidden. Maiwenn and every member read
  `AI-USAGE.md` (told by Arthur).
- *To do:* Arthur looks at the page at a medium window width.
