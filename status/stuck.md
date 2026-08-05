# R Stuck / Blockers

## Active blockers

- None verified.

## Deferred external merge gates

- 2026-07-31: PR #534 reached current head `1e97e366de8b00ed73116af0927c5dec1b36a05f` and received a reviewer verdict, but `/usr/local/bin/r-verify-ai-review 534` failed closed with exit `1` and `{"ok":false,"reason":"review_gate_disabled_pending_isolated_reviewer_identity"}`. Keep the PR open and do not merge until the authenticated verifier returns exit `0` with `{"ok":true}` for the current head.
- 2026-08-05: PR #535's sentry plus warden implementation remains clean/mergeable at current head `5ed666c6ca7f786ec651cae2240278fba85487e0`; fresh host and Docker verification passed with 341 tests, but `/usr/local/bin/r-verify-ai-review 535` failed closed with exit `1` and `{"ok":false,"reason":"review_gate_disabled_pending_isolated_reviewer_identity"}`. Keep the PR open and do not merge until the authenticated verifier returns exit `0` with `{"ok":true}` for the current head.
- 2026-07-31: `/usr/local/bin/r-bot-git-push ai/r/rustic-balance-secure` rejected local commit `cc39aea` with GitHub 403 (`Permission to CesarPetrescu/R.git denied to r-hermes-bot[bot]`); the branch already has the verified implementation pushed, but the external-gate evidence commit remains local until authentication recovers.

## Resolved blockers

- 2026-07-06: `/usr/local/bin/r-bot-git-push ai/r/rustic-balance-crag` initially failed after local commit `97de2ea` with GitHub 403 (`Permission to CesarPetrescu/R.git denied to r-hermes-bot[bot]`). A later retry successfully pushed the branch after blocker recording, so this is no longer an active blocker.
- 2026-06-22: `/usr/local/bin/r-bot-git-push ai/r/rustic-band-span-gap-ratio` previously failed after local commit `d200d54` with GitHub 403 (`Permission to CesarPetrescu/R.git denied to r-hermes-bot[bot]`). A later retry successfully pushed the branch, so this is no longer an active blocker.
- 2026-05-10: `/usr/local/bin/r-bot-git-push ai/r/rustic-array-min-max` previously failed with GitHub 403 (`Permission to CesarPetrescu/R.git denied to r-hermes-bot[bot]`). A later retry successfully pushed the branch, so this is no longer an active blocker.
- 2026-05-06: A CI workflow branch was not pushable via `/usr/local/bin/r-bot-git-push` because the builder GitHub App lacks `workflows` permission for `.github/workflows/ci.yml`. This is not an active blocker for non-workflow maintenance branches; avoid workflow-file work until the app permission changes or a maintainer pushes that file.
