# AI log: design/modern-ui

Branch `design/modern-ui`, from `fix/alert-na-many-missing` (2026-11-28). Tool: Claude Code (Claude Opus 5.5), skills
`design-interface` and `test-and-check`. Asked by Arthur: "a more developed, modern and responsive app that adapts to
the window, with UI/UX effects", then his own end-to-end check (slice 7).

## What the AI did (2026-11-28)
- `app/style.css` rewritten in sections: colour tokens, a fixed frosted top bar, a gradient hero title that gets small
  once there are results (the cards stay on the first screen at 1280 × 800), the inputs in one white panel, cards with
  a line of their alert colour on top (the word is always written: colour is never the only sign), white panels for the
  charts and the table, rise-in and hover effects switched off when the computer asks for reduced motion, phone rules.
- `app/streamlit_app.py`: top bar (links to Summary, Charts, Ratios once there are results), hero, search panel, an
  empty state with three tiles and a "Try AAPL, MSFT, NKE" link that fills the field and runs, chart selector and
  Excel button on one line, ratio table column sizes (`ratio_table_columns`). Only fixed project text is written as
  HTML; nothing is computed in the page.
- 3 tests written (example link, top-bar links, column sizes); 4 deliberate bugs each made 1 test fail. The first
  column-size test used notes too short to catch a bug; it now injects a note as long as NKE's. 385 passed.
- Screenshots looked at in a headless Chrome at 1440 × 900, 1280 × 800, 1000 × 700 and 390 px, the empty state, 5
  SAMPLE DATA companies at 1280 px and the real NKE notes.
- End-to-end run of the real page on the cached SEC files of AAPL, MSFT, NKE with the internet blocked: no error, the
  6 chart ratios in both debt definitions, Excel with 4 sheets, 5 fiscal years.

## AI mistakes and how they were caught
- The card width rule was put on the card instead of the box around it: the cards were cut at the bottom. Seen on the
  first screenshot, cause found by measuring the boxes in Chrome.
- The two charts were first put side by side: the trend chart's "n/a (not drawn)" note was cut off. Seen on a
  screenshot; the charts are one under the other again.
- 16 rem cards would have put the 5th card on a second row at 1280 px (V1); worked out, changed to 13 rem, checked on
  a screenshot with 5 companies.

## What the human decided or checked
- *To do:* Arthur looks at the page (restart the app) and validates before the push.
