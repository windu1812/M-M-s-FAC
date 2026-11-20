# AI log: fix/data-sec-unreachable

Branch `fix/data-sec-unreachable` (follow-up of issue #3, slice 2). Tool: Claude Code (Claude Opus 5.5), skills
`build-feature` and `integrate-api`.

## What the AI did
- Found that acceptance criterion E8 ("SEC unreachable, no cache") was still open. Without the cache, a failed
  download let a technical `requests` error escape, and no test covered this case.
- Wrote 6 tests first:
  - no internet;
  - no answer within 30 seconds;
  - HTTP status 503;
  - an answer that is not JSON;
  - `get_financials` with no internet and an empty cache;
  - a guard: the "no internet in tests" block of `conftest.py` must stay visible.

  The first 5 failed before the fix, as expected; the guard passed.
- Added `SecUnavailableError` in `app/creditlens/data/sec_client.py`. Every failed download now raises it with a
  readable message that says:
  - which SEC server failed;
  - why;
  - what to do.

  Nothing is written to the cache when a download fails.
- Listed the errors of `get_financials` in its docstring and in `docs/architecture.md`, so the dashboard (slice 5)
  knows what to catch for each ticker.
- Ran a real check with the real `requests` library: refused connection and empty cache. The message was clear and
  nothing was written to the cache.
- Updated Arthur's lines of `docs/plan.md`:
  - slices 1 and 2 marked as merged;
  - "slice 8" corrected to "slice 7";
  - one progress log row added.

## What the human decided or checked
- Arthur asked for this follow-up ("points 1 and 2") on 2026-11-20.
- *To do:* read the error message and decide whether the wording suits the dashboard.

## AI mistakes and how they were caught
- On 2026-11-20, while moving the branches of issues #6 to #9 to `main`, the AI wrote a push command that zsh
  misread: `$M:refs` is read as a zsh modifier. Three pushes failed with "src refspec ... does not match any".
  The AI read the full error, added braces (`${M}:refs/...`) and pushed again. Nothing had been changed on GitHub
  by the failed attempt.

## Open points
- No automatic retry after a failure. The user clicks Run again.
- With `refresh=True` and the SEC down, the error is raised even if an older copy is in the cache. This matters only
  if a "refresh" action is added. `docs/product.md` has no refresh button, but it says the ticker list is
  "refreshed on demand".
