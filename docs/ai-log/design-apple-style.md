# AI log: design/apple-style

Local branch `design/apple-style`, from `design/compact-top`. Tool: Claude Code (Claude Opus 5.5), skill
`design-interface`. Not pushed: Arthur validates it first.

## What the AI did (2026-11-28)
- Arthur asked for a responsive page "in the style of Apple's website", without the Deploy button, without any visible
  Streamlit control and without the screencast recorder.
- The style is only inspired by clean product pages (white space, grey tiles, system font, one blue accent): no logo,
  name or image of another company.
- `app/.streamlit/config.toml`: theme colours, pill buttons, heading weights; `toolbarMode = "minimal"` removes the
  Deploy button and the whole menu (with "Record a screencast").
- `app/style.css` (new, loaded by the page): the computer's system font, grey card tiles, and hiding of Streamlit's
  top bar, running status, table toolbars and footer. Charts: Plotly toolbar off.
- Responsive cards: fixed-width tiles in a row that wraps (3 per row on a laptop, 2 at 1000 px, 1 on a phone).
- 4 tests written first; 379 passed. Screenshots looked at in a headless Chrome at 1440 × 900, 1280 × 800,
  1000 × 700 and 390 px.

## AI mistakes and how they were caught
- The style sheet was first added with `st.html`: AppTest saw it, but Chrome showed no style at all. The AI checked
  the page in Chrome (no `<style>` element, Source Sans still used), and switched to `st.markdown(...,
  unsafe_allow_html=True)`, which works; the test now checks that form.

## What the human decided or checked
- Arthur looked at the page and validated it ("c'est bon, commit et push"); merged with PR #18 on 2026-11-28.
