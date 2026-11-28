# AI log: design/compact-top

Local branch `design/compact-top`, from `9-charts-and-excel-export` (PR #16 and #15 not yet merged). Tool: Claude Code
(Claude Opus 5.5), skill `design-interface`. Not pushed: Arthur validates it first.

## What the AI did (2026-11-28)
- Arthur asked: the summary panel forces a scroll; align the ticker field and the debt definition; stay sober and
  professional.
- Took screenshots of the page with AAPL, MSFT and NKE: a headless Chrome (already on the Mac, separate profile)
  driven over its DevTools protocol by a throwaway script outside the project, on a second port; Arthur's app on
  port 8501 was not touched. At 1280 × 800 the cards started at mid-screen and were cut.
- Changes, with tests first where behaviour changed:
  - `app/.streamlit/config.toml`: a smaller top padding and smaller headings, from Streamlit's own theme options
    (no custom CSS);
  - `app/streamlit_app.py`: tickers, Run and the debt definition on one row with their labels aligned; the debt
    definition became a two-button `st.segmented_control` (one always selected; it wraps in a narrow window instead
    of being cut off); "Results for" and the cache date as two small lines under the inputs; the progress box is
    removed after a clean run (kept when a ticker failed); at least 3 card columns, and one line per ratio on the
    cards.
- Looked at screenshots at 1280 × 800, 1366 × 768, 1000 × 600 and 390 px, and the empty and error states. Fixed on the
  way: the label of the debt definition was 8 px lower than the ticker label (aligned by the top), and the second
  debt button was cut off at 1000 px (now wraps).
- 375 passed.

## What the human decided or checked
- Arthur asked for the change and for a local branch only. *To do:* look at the page (restart the app: the theme is
  read at start) and validate before anything is pushed.

## AI mistakes and how they were caught
- The first screenshot was blank: Chrome took it while Streamlit was still loading. The AI saw the grey placeholders
  in the image and switched to a script that waits for the page to finish.
- The theme's `paddingTop = "2.5rem"` barely moved the title: Streamlit adds its toolbar height on top. Seen on the
  second screenshot; set to 1rem.
