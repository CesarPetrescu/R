# R TODO

The autonomous agent should complete concrete implementation work every run, not vague improvements.

## Next recommended tasks

1. After the authenticated review gate is restored, merge the existing product PR queue before selecting new work: #535 adds the `sentry`, `warden`, and `watch` helper pairs, #537 adds `keeper`, and #536 migrates the automation indexes. Do not duplicate those open PRs; `status/missing-features.md` has no unchecked item on `main`, so choose the next concrete interpreter feature only after this queue is resolved.
2. Migrate automation-facing docs and guard defaults from `docs/*automation*` paths into `automations/` behind compatibility tests, keeping Docker coverage green while paths move.
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
