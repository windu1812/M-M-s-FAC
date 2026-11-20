# AI log: docs/product-interview

Branch `docs/product-interview`. Tool: Claude Code (Claude Opus 5.5), skill `product-interview`.

## What the AI did
- Turned Arthur's answers to the 7 interview rounds into `docs/product.md`, `docs/architecture.md`,
  `docs/acceptance.md` and `docs/plan.md`, in English.
- Proposed 5 visuals (cards, comparison bars, 5-year lines, ratio table, Excel button) and a stack: Streamlit,
  Python 3.12. It chose Python 3.12 after checking the installed versions and PyPI support for Streamlit, pandas
  and Plotly.
- Wrote the hand-worked known answers (CALC1–CALC13) and proposed the thresholds, which Arthur then agreed.
- Raised 5 open points before writing code:
  - only 1 GitHub issue existed, not 5;
  - several headline ratios are "not available" for MSFT, NKE and AAPL, shown with the real SEC data;
  - the optional LLM comment conflicts with the zero budget;
  - the thresholds needed confirmation;
  - total debt left out commercial paper and leases.
- Checked in the cached SEC data which tags AAPL, MSFT and NKE use for commercial paper, short-term borrowings and
  leases. MSFT's finance lease liabilities alone are larger than its long-term debt.
- Created issues #6 to #9, and added a comment on #3 with the new scope of slice 2.
- Built the walking skeleton in `app/`:
  - Streamlit page with the ticker field and Run button;
  - `app/.venv` with Python 3.12, pinned dependencies;
  - 2 `AppTest` tests;
  - `app/README.md`, `app/.env.example` and `.streamlit/config.toml`;
  - the "This project" section of `AGENTS.md`.
- Ran the tests (2 passed) and started the real Streamlit server: health check ok, page HTTP 200.

## What the human decided or checked
- Arthur answered the interview and agreed the documents on 2026-11-20:
  - create the 4 missing issues;
  - keep "not available" and derive nothing;
  - no paid service, so no LLM comment;
  - the thresholds and rules as proposed;
  - add commercial paper and leases to total debt in slice 2.
- Arthur then replaced the last decision: total debt is computed in two versions (financial debt only, and
  including leases and short-term borrowings), with a selector in the dashboard. Arthur also set the owners of the
  issues: Arthur #3 and slice 7, Coco #6, Maiwenn #7, Marc #8, François #9.
- *To do:* look at the page in a browser (`.venv/bin/python -m streamlit run streamlit_app.py`).

## AI mistakes and how they were caught
- The first server run showed Streamlit listening on the whole network ("Network URL" and "External URL" in the
  log), which is not wanted for a laptop demo. The AI caught it by reading the server log and restricted the app to
  `localhost` in `app/.streamlit/config.toml`, then checked again.
- The AI tried to move the root `.env` to `app/.env` at Arthur's request, without reading it. The project's
  permission rules blocked it, because the assistant must never touch `.env` files. Arthur does the move instead.

## Team guide and branch clean-up (2026-11-20)
- At Arthur's request, the AI checked the state of the branches and of the GitHub repository:
  - PR #10 is not merged yet;
  - the branches of issues #6 to #9 started from a commit of PR #10 (not from `main`) and missed its last commit;
  - PR #4 would conflict with that commit on `docs/plan.md`;
  - three old branches were already merged;
  - Arthur is the only member with push access.
- The AI wrote `docs/guide-equipe.md` in French:
  - who does what (issue, branch, files, reviewer);
  - first install;
  - the routine of each session;
  - commits and pull requests;
  - conflicts and frequent errors.

  The reviewer pairs and the "author merges with a merge commit" rule are proposals for the team to confirm.
