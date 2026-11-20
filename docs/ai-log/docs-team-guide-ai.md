# AI log: docs/team-guide-ai

Branch `docs/team-guide-ai`. Tool: Claude Code (Claude Opus 5.5).

## What the AI did
- Arthur asked whether the members' AI assistants would understand the work from the team guide. The AI checked
  what the assistants read on their own and found three problems:
  - `AGENTS.md` and `docs/plan.md` still told the assistant to run `gh issue develop <n> --checkout`, while the
    branches of issues #6 to #9 already exist. The guide says the opposite, and the command could create a second
    branch for an issue;
  - the assistants do not read `docs/guide-equipe.md` on their own. Some rules were written only there: who owns
    the shared files, how fixture files are named, merge commits only;
  - the guide gave only one example of a first prompt.
- Changes:
  - `AGENTS.md` (team rules), with Arthur's explicit agreement: the branch rule now says `git switch <branch>` and
    merge commits only. A new line sends the assistant to the guide;
  - `docs/plan.md` (Arthur's line on owners): same correction;
  - `docs/guide-equipe.md`: a ready-to-copy first prompt for each member (name, slice, issue, branch, files), and
    a short prompt for later sessions.

## What the human decided or checked
- Arthur agreed to the changes, including `AGENTS.md`, on 2026-11-20.
- *To do:* each member tries their first prompt and checks that the assistant proposes a plan for the right slice.
