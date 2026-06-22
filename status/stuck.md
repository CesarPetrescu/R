# R Stuck / Blockers

## Active blockers

- None verified.

## Resolved blockers

- 2026-06-22: `/usr/local/bin/r-bot-git-push ai/r/rustic-band-span-gap-ratio` previously failed after local commit `d200d54` with GitHub 403 (`Permission to CesarPetrescu/R.git denied to r-hermes-bot[bot]`). A later retry successfully pushed the branch, so this is no longer an active blocker.
- 2026-05-10: `/usr/local/bin/r-bot-git-push ai/r/rustic-array-min-max` previously failed with GitHub 403 (`Permission to CesarPetrescu/R.git denied to r-hermes-bot[bot]`). A later retry successfully pushed the branch, so this is no longer an active blocker.
- 2026-05-06: A CI workflow branch was not pushable via `/usr/local/bin/r-bot-git-push` because the builder GitHub App lacks `workflows` permission for `.github/workflows/ci.yml`. This is not an active blocker for non-workflow maintenance branches; avoid workflow-file work until the app permission changes or a maintainer pushes that file.
