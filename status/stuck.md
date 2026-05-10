# R Stuck / Blockers

## Active blockers

- 2026-05-10: `/usr/local/bin/r-bot-git-push ai/r/rustic-array-min-max` failed with GitHub 403 (`Permission to CesarPetrescu/R.git denied to r-hermes-bot[bot]`). Local branch `ai/r/rustic-array-min-max` is committed and verified, but cannot be pushed/opened as a PR until builder bot repository write permission is restored.

## Resolved blockers

- 2026-05-06: A CI workflow branch was not pushable via `/usr/local/bin/r-bot-git-push` because the builder GitHub App lacks `workflows` permission for `.github/workflows/ci.yml`. This is not an active blocker for non-workflow maintenance branches; avoid workflow-file work until the app permission changes or a maintainer pushes that file.
