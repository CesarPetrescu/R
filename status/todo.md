# R TODO

The autonomous agent should complete concrete implementation work every run, not vague improvements.

## Next recommended tasks

1. Once the isolated authenticated reviewer identity is available, merge the existing sentry/warden/watch PR #535, keeper PR #537, patrol PR #539, and this post-helper branch after fetching each live head and passing `/usr/local/bin/r-verify-ai-review`; do not open another dependent helper until those external gates resolve. After the chain lands, select the next unclaimed helper suffix only with a documented formula, identifier-length check, direct/composed/diagnostic cases, and 65-iteration cleanup coverage.
2. Migrate automation-facing docs and guard defaults from `docs/*automation*` paths into `automations/` behind compatibility tests, keeping Docker coverage green while paths move; existing PRs #536/#538 already cover related work and should be refreshed rather than duplicated.
3. Add CI workflow once the builder GitHub App has `workflows` permission, or ask a maintainer to push `.github/workflows/ci.yml`.

## Every-run checklist

- [ ] Pull latest `main` with `git checkout main && git pull --ff-only`
- [ ] Read README, plan, prompt, and all `status/` files
- [ ] Ideate candidate roadmap-completion tasks
- [ ] Choose the highest-impact finishable work package
- [ ] Write failing tests first for behavior changes
- [ ] Implement the selected work package fully enough to close backlog items
- [ ] Run verification
- [ ] Update status/backlog with completed and overflow ideas
- [ ] Commit and push verified changes
