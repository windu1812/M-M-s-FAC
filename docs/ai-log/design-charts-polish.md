# AI log: design/charts-polish

Branch `design/charts-polish`, from `main` after PR #20 (2026-11-28). Tool: Claude Code (Claude Opus 5.5), skills
`design-interface` and `dataviz`. `app/creditlens/charts.py` is François's module: Claude asked first, Arthur said
François agreed.

## What the AI did (2026-11-28)
- Debt choices: the two pills overlapped (Streamlit joins segmented buttons with a -1 px margin for square corners).
  Measured in Chrome; now separate pills with an 8 px gap. A first selector (`:has()` inside `:has()`) is not valid
  CSS and did nothing: seen by measuring again.
- Charts, kept data oriented: slim bars with rounded ends in the flag colours of the cards and the flag word after the
  value; company lines in a colour set checked with a colour-blindness validator, with no green, orange or red (kept
  for the flags), dashes and markers kept; each line ends with its ticker and value (up to 4 companies); one tooltip
  per fiscal year; the flag limits also on the trend chart, but only near the data; the year axis fixed to the real
  years; every "n/a" reason on its own line. 6 tests written first; 395 passed.

## AI mistakes and how they were caught
- The limits on the trend chart first stretched the axis to 3.5x and flattened AAPL's line (0.24–0.66x): seen on a
  screenshot; limits now drawn only near the data.
- On a phone the year axis went to FY2032 (Plotly widened it to fit the end labels), and the legend and the two limit
  labels overlapped the titles: seen on 390 px screenshots, fixed.
- The "n/a (not drawn)" note was cut at the right edge with NKE's long reasons (this was already so before): now one
  line per company and reason.

## What the human decided or checked
- Arthur asked for the change; François agreed to changes in his module (told by Arthur).
- *To do:* Arthur looks at the charts; François reads the `charts.py` changes.
