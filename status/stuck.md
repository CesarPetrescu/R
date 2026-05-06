# R Stuck / Blockers

## Active blockers

- None verified.

## Resolved blockers

- 2026-05-06: A CI workflow branch was not pushable via `/usr/local/bin/r-bot-git-push` because the builder GitHub App lacks `workflows` permission for `.github/workflows/ci.yml`. This is not an active blocker for non-workflow maintenance branches; avoid workflow-file work until the app permission changes or a maintainer pushes that file.
