# R TODO

The autonomous agent should complete concrete implementation work every run, not vague improvements.

## Next recommended tasks

1. Add richer collection reshaping helpers to Rustic, such as `chunk_count(array, n)` or `window_sum(array, n)`, with tests proving empty-array behavior, invalid-size diagnostics, composition with `drop(...)`/`take(...)`, and array-slot cleanup.
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
